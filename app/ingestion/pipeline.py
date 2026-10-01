"""Versioning → chunking → embedding → storage pipeline, run right after Admin approval.

Consistency strategy (ASM-05): the version starts 'pending' (Phase 1), flips to 'processing'
here, and only flips to 'active' — superseding any prior active version — once chunks are
written to SQLite AND embeddings are written to the vector store. If either storage write
fails, the version is marked 'failed' and any partial chunk rows are rolled back, so a failed
embedding step never leaves a document that SQLite/Chroma disagree about."""
from pathlib import Path

from app.core.logging import get_logger
from app.ingestion import chunking, embedding, extraction
from app.storage import documents_repo, vector_store

logger = get_logger(__name__)


def process_pending_version(document_version_id: int) -> tuple[bool, str]:
    version = documents_repo.get_version(document_version_id)
    if version is None:
        return False, "Document version not found."
    if version.status != "pending":
        return False, f"Version is '{version.status}', expected 'pending'."
    if not version.file_path:
        return False, "Version has no stored file to process."

    document = documents_repo.get_document(version.document_id)
    if document is None:
        return False, "Parent document not found."

    documents_repo.update_version_status(document_version_id, "processing")

    try:
        extracted = extraction.extract_text(version.file_path, Path(version.file_path).name)
        chunks = chunking.chunk_sections(extracted)
        if not chunks:
            raise ValueError("No chunks could be produced from the extracted text.")

        texts = [c.chunk_text for c in chunks]
        vectors = embedding.embed_texts(texts)

        chunk_ids = [
            documents_repo.insert_chunk(document_version_id, c.section, c.page, c.chunk_text)
            for c in chunks
        ]
        vector_ids = [f"chunk-{chunk_id}" for chunk_id in chunk_ids]
        for chunk_id, vector_id in zip(chunk_ids, vector_ids):
            documents_repo.set_chunk_embedding_ref(chunk_id, vector_id)

        metadatas = [
            {
                "document_version_id": document_version_id,
                "document_id": version.document_id,
                "document_title": document.title,
                "category": document.category,
                "version": version.version,
                "effective_from": version.effective_from,
                "section": c.section or "",
            }
            for c in chunks
        ]

        vector_store.add_chunks(
            ids=vector_ids, embeddings=vectors, documents=texts, metadatas=metadatas
        )
    except Exception as exc:  # noqa: BLE001 — surfaced to the Admin, version marked failed
        logger.exception("Ingestion pipeline failed for version %s", document_version_id)
        documents_repo.delete_chunks_for_version(document_version_id)
        documents_repo.update_version_status(document_version_id, "failed")
        return False, f"Ingestion failed: {exc}"

    documents_repo.activate_version(version.document_id, document_version_id, version.effective_from)
    logger.info("Version %s activated with %d chunks", document_version_id, len(chunks))
    return True, f"Indexed {len(chunks)} chunks and activated version {version.version}."
