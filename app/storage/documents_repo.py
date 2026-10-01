"""Document/DocumentVersion read-write helpers used by the Admin ingestion flow."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.storage.sqlite_db import get_connection


@dataclass
class DocumentRow:
    id: int
    title: str
    category: str
    current_version_id: int | None


@dataclass
class DocumentVersionRow:
    id: int
    document_id: int
    version: str
    effective_from: str
    effective_to: str | None
    status: str
    file_path: str | None
    description: str | None = None
    extracted_by: str | None = None
    reviewed_by_admin: int = 0
    prompt_injection_flag: int = 0
    created_at: str | None = None


@dataclass
class ChunkRow:
    id: int
    document_version_id: int
    section: str | None
    page: int | None
    chunk_text: str
    embedding_ref: str | None


def get_document(document_id: int) -> DocumentRow | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return DocumentRow(**dict(row)) if row else None


def get_document_by_title(title: str) -> DocumentRow | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE lower(title) = lower(?)", (title,)
        ).fetchone()
        return DocumentRow(**dict(row)) if row else None


def get_active_version(document_id: int) -> DocumentVersionRow | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM document_versions WHERE document_id = ? AND status = 'active' "
            "ORDER BY effective_from DESC LIMIT 1",
            (document_id,),
        ).fetchone()
        return DocumentVersionRow(**dict(row)) if row else None


def create_document(title: str, category: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO documents (title, category) VALUES (?, ?)", (title, category)
        )
        conn.commit()
        return cursor.lastrowid


def create_pending_version(
    document_id: int,
    version: str,
    effective_from: date,
    description: str,
    extracted_by: str,
    prompt_injection_flag: bool,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO document_versions
               (document_id, version, effective_from, status, description,
                extracted_by, reviewed_by_admin, prompt_injection_flag)
               VALUES (?, ?, ?, 'pending', ?, ?, 1, ?)""",
            (
                document_id,
                version,
                effective_from.isoformat(),
                description,
                extracted_by,
                int(prompt_injection_flag),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_version(document_version_id: int) -> DocumentVersionRow | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM document_versions WHERE id = ?", (document_version_id,)
        ).fetchone()
        return DocumentVersionRow(**dict(row)) if row else None


def update_version_status(document_version_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE document_versions SET status = ? WHERE id = ?", (status, document_version_id)
        )
        conn.commit()


def activate_version(document_id: int, new_version_id: int, effective_from: str) -> None:
    """Supersedes any other active version of this document and promotes the new one.
    Runs as a single connection/transaction so the flip is all-or-nothing."""
    new_from_date = datetime.fromisoformat(effective_from).date()
    prior_day = (new_from_date - timedelta(days=1)).isoformat()
    with get_connection() as conn:
        conn.execute(
            """UPDATE document_versions SET status = 'superseded', effective_to = ?
               WHERE document_id = ? AND status = 'active' AND id != ?""",
            (prior_day, document_id, new_version_id),
        )
        conn.execute(
            "UPDATE document_versions SET status = 'active' WHERE id = ?", (new_version_id,)
        )
        conn.execute(
            "UPDATE documents SET current_version_id = ? WHERE id = ?", (new_version_id, document_id)
        )
        conn.commit()


def insert_chunk(
    document_version_id: int, section: str | None, page: int | None, chunk_text: str
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO chunks (document_version_id, section, page, chunk_text)
               VALUES (?, ?, ?, ?)""",
            (document_version_id, section, page, chunk_text),
        )
        conn.commit()
        return cursor.lastrowid


def set_chunk_embedding_ref(chunk_id: int, embedding_ref: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE chunks SET embedding_ref = ? WHERE id = ?", (embedding_ref, chunk_id))
        conn.commit()


def list_chunks(document_version_id: int) -> list[ChunkRow]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE document_version_id = ?", (document_version_id,)
        ).fetchall()
        return [ChunkRow(**dict(r)) for r in rows]


def delete_chunks_for_version(document_version_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM chunks WHERE document_version_id = ?", (document_version_id,))
        conn.commit()


def set_version_file_path(document_version_id: int, file_path: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE document_versions SET file_path = ? WHERE id = ?",
            (file_path, document_version_id),
        )
        conn.commit()


def list_versions(document_id: int) -> list[DocumentVersionRow]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM document_versions WHERE document_id = ? ORDER BY effective_from DESC",
            (document_id,),
        ).fetchall()
        return [DocumentVersionRow(**dict(r)) for r in rows]


def list_eligible_version_ids(categories: list[str], as_of: date | None) -> list[int]:
    """Current-policy questions (as_of=None) resolve only to 'active' versions (FR-031, FR-033).
    Historical questions resolve to whichever version's effective range contains the date (FR-032),
    whether that version is now active or already superseded."""
    if not categories:
        return []
    placeholders = ",".join("?" for _ in categories)
    with get_connection() as conn:
        if as_of is None:
            rows = conn.execute(
                f"""SELECT dv.id FROM document_versions dv
                    JOIN documents d ON dv.document_id = d.id
                    WHERE d.category IN ({placeholders}) AND dv.status = 'active'""",
                categories,
            ).fetchall()
        else:
            as_of_str = as_of.isoformat()
            rows = conn.execute(
                f"""SELECT dv.id FROM document_versions dv
                    JOIN documents d ON dv.document_id = d.id
                    WHERE d.category IN ({placeholders})
                      AND dv.status IN ('active', 'superseded')
                      AND dv.effective_from <= ?
                      AND (dv.effective_to IS NULL OR dv.effective_to >= ?)""",
                [*categories, as_of_str, as_of_str],
            ).fetchall()
        return [r[0] for r in rows]


def get_chunks_by_version_ids(version_ids: list[int]) -> list[dict]:
    if not version_ids:
        return []
    placeholders = ",".join("?" for _ in version_ids)
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT c.id as chunk_id, c.document_version_id, c.section, c.page, c.chunk_text,
                       dv.version, dv.effective_from, dv.effective_to, d.title as document_title
                FROM chunks c
                JOIN document_versions dv ON c.document_version_id = dv.id
                JOIN documents d ON dv.document_id = d.id
                WHERE c.document_version_id IN ({placeholders})""",
            version_ids,
        ).fetchall()
        return [dict(r) for r in rows]


def list_all_documents() -> list[DocumentRow]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY title").fetchall()
        return [DocumentRow(**dict(r)) for r in rows]


def get_kb_stats() -> dict:
    """Admin dashboard basics: document/version counts by category and status."""
    with get_connection() as conn:
        total_documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        status_counts = dict(
            conn.execute(
                "SELECT status, COUNT(*) FROM document_versions GROUP BY status"
            ).fetchall()
        )
        category_counts = dict(
            conn.execute("SELECT category, COUNT(*) FROM documents GROUP BY category").fetchall()
        )
        return {
            "total_documents": total_documents,
            "status_counts": status_counts,
            "category_counts": category_counts,
        }
