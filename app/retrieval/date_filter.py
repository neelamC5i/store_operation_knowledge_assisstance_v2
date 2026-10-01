"""Resolves which document versions are eligible before retrieval runs (FR-031–FR-033).
Eligibility is resolved against SQLite (the source of truth for versioning), not against
stale vector-store metadata, since a version's effective_to is only known after supersede."""
from datetime import date

from app.storage import documents_repo


def eligible_version_ids(categories: list[str], as_of: date | None) -> list[int]:
    return documents_repo.list_eligible_version_ids(categories, as_of)
