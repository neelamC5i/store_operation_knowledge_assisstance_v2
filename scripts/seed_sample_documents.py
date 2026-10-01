"""Seeds the knowledge base with the sample documents in sample_documents/ — bypasses the
Admin metadata-review UI (metadata is already known here) but runs the real versioning/
chunking/embedding pipeline, so the KB is ready for the golden-dataset evaluation run."""
from datetime import date

from app.ingestion import pipeline
from app.storage import documents_repo
from app.storage.sqlite_db import init_db

# Order matters: a document's versions must be seeded oldest-first so supersede logic
# (activate_version) marks earlier versions 'superseded' as later ones activate.
DOCUMENTS = [
    {
        "title": "Return Policy",
        "category": "Procedures",
        "version": "v1",
        "effective_from": date(2023, 1, 1),
        "description": "Original return policy (14-day window).",
        "file": "sample_documents/return_policy_v1_2023-01-01.txt",
    },
    {
        "title": "Return Policy",
        "category": "Procedures",
        "version": "v2",
        "effective_from": date(2024, 6, 1),
        "description": "Updated return policy (30-day window, defective exchanges).",
        "file": "sample_documents/return_policy_v2_2024-06-01.txt",
    },
    {
        "title": "Inventory and POS Procedures",
        "category": "Procedures",
        "version": "v1",
        "effective_from": date(2023, 3, 1),
        "description": "Cash reconciliation and inventory receiving procedures.",
        "file": "sample_documents/inventory_pos_procedures_v1_2023-03-01.txt",
    },
    {
        "title": "Store Promotions",
        "category": "Promotions",
        "version": "v1",
        "effective_from": date(2024, 1, 1),
        "description": "Current promotions and coupon combination rules.",
        "file": "sample_documents/promotions_v1_2024-01-01.txt",
    },
    {
        "title": "Store Safety Rules",
        "category": "Safety",
        "version": "v1",
        "effective_from": date(2023, 1, 1),
        "description": "Food handling, fire/emergency, and equipment safety rules.",
        "file": "sample_documents/safety_rules_v1_2023-01-01.txt",
    },
]


def seed() -> None:
    init_db()
    for d in DOCUMENTS:
        existing = documents_repo.get_document_by_title(d["title"])
        document_id = existing.id if existing else documents_repo.create_document(d["title"], d["category"])
        version_id = documents_repo.create_pending_version(
            document_id=document_id,
            version=d["version"],
            effective_from=d["effective_from"],
            description=d["description"],
            extracted_by="manual-seed",
            prompt_injection_flag=False,
        )
        documents_repo.set_version_file_path(version_id, d["file"])
        success, message = pipeline.process_pending_version(version_id)
        status = "OK" if success else "FAILED"
        print(f"[{status}] {d['title']} {d['version']}: {message}")


if __name__ == "__main__":
    seed()
