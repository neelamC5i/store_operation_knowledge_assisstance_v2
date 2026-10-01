"""Hybrid retrieval: vector similarity (Chroma) + keyword (BM25), merged via reciprocal
rank fusion, restricted to the date/category-eligible document versions (FR-034, FR-035)."""
from datetime import datetime

from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.ingestion.embedding import embed_query
from app.models.schemas import RetrievedChunk
from app.storage import documents_repo, vector_store

_RRF_K = 60


def _reciprocal_rank_fusion(rank_lists: list[list[int]], k: int = _RRF_K) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranked_ids in rank_lists:
        for rank, chunk_id in enumerate(ranked_ids):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def _parse_date(value: str | None):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def retrieve(query: str, eligible_version_ids: list[int], top_k: int | None = None) -> list[RetrievedChunk]:
    top_k = top_k or settings.top_k
    if not eligible_version_ids:
        return []

    candidates = documents_repo.get_chunks_by_version_ids(eligible_version_ids)
    if not candidates:
        return []
    by_id = {c["chunk_id"]: c for c in candidates}

    query_embedding = embed_query(query)
    vector_result = vector_store.query(
        query_embedding=query_embedding,
        top_k=min(top_k * 3, len(candidates)),
        where={"document_version_id": {"$in": eligible_version_ids}},
    )
    vector_rank_ids = []
    vector_similarity: dict[int, float] = {}
    for raw_id, distance in zip(vector_result["ids"][0], vector_result["distances"][0]):
        chunk_id = int(raw_id.split("-", 1)[1])
        if chunk_id in by_id:
            vector_rank_ids.append(chunk_id)
            # Cosine distance is in [0, 2]; similarity in [0, 1] is a meaningful absolute
            # relevance signal (unlike RRF's rank-based fusion score, which always scales
            # its top hit to ~1.0 even when nothing in the KB is actually relevant).
            vector_similarity[chunk_id] = max(0.0, 1.0 - distance / 2.0)

    tokenized_corpus = [c["chunk_text"].lower().split() for c in candidates]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query.lower().split())
    max_bm25 = max(bm25_scores) if len(bm25_scores) else 0.0
    bm25_normalized = {
        c["chunk_id"]: (score / max_bm25 if max_bm25 > 0 else 0.0)
        for c, score in zip(candidates, bm25_scores)
    }
    keyword_rank_ids = [
        chunk_id
        for chunk_id, _ in sorted(
            zip((c["chunk_id"] for c in candidates), bm25_scores), key=lambda pair: -pair[1]
        )
    ][: top_k * 3]

    fused = _reciprocal_rank_fusion([vector_rank_ids, keyword_rank_ids])
    if not fused:
        return []
    ranked_ids = sorted(fused, key=lambda cid: -fused[cid])[:top_k]

    results = []
    for chunk_id in ranked_ids:
        c = by_id[chunk_id]
        # Prefer the absolute vector similarity; fall back to normalized BM25 for a chunk
        # that only surfaced via keyword search.
        relevance_score = vector_similarity.get(chunk_id, bm25_normalized.get(chunk_id, 0.0))
        results.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                document_version_id=c["document_version_id"],
                document_title=c["document_title"],
                section=c["section"],
                version=c["version"],
                effective_from=_parse_date(c["effective_from"]),
                effective_to=_parse_date(c["effective_to"]),
                chunk_text=c["chunk_text"],
                relevance_score=relevance_score,
            )
        )
    return results
