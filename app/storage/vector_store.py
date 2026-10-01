"""Chroma-backed vector store wrapper. FAISS remains a config option (VECTOR_DB_BACKEND)
but Chroma is implemented first since it persists metadata alongside embeddings natively."""
import chromadb

from app.core.config import settings

_COLLECTION_NAME = "store_ops_chunks"

_client = chromadb.PersistentClient(path=settings.vector_index_path)


def get_collection():
    # Cosine distance makes the returned distance a meaningful, bounded relevance signal
    # (needed so evidence_evaluator can tell "no good match" from "best of a bad set" —
    # see hybrid_search.py) rather than Chroma's default unbounded squared-L2.
    return _client.get_or_create_collection(
        name=_COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def add_chunks(ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]) -> None:
    get_collection().add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query(query_embedding: list[float], top_k: int, where: dict | None = None) -> dict:
    return get_collection().query(query_embeddings=[query_embedding], n_results=top_k, where=where)


def delete_by_document_version(document_version_id: int) -> None:
    get_collection().delete(where={"document_version_id": document_version_id})
