"""Conversation/Message/Feedback persistence for session history and feedback (FR-046–FR-049)."""
from app.storage.sqlite_db import get_connection


def get_or_create_conversation(employee_session_id: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM conversations WHERE employee_session_id = ? ORDER BY id DESC LIMIT 1",
            (employee_session_id,),
        ).fetchone()
        if row:
            return row[0]
        cursor = conn.execute(
            "INSERT INTO conversations (employee_session_id) VALUES (?)", (employee_session_id,)
        )
        conn.commit()
        return cursor.lastrowid


def add_message(
    conversation_id: int,
    role: str,
    text: str,
    citations_json: str | None,
    confidence: float | None,
    is_refusal: bool,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO messages (conversation_id, role, text, citations, confidence, is_refusal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (conversation_id, role, text, citations_json, confidence, int(is_refusal)),
        )
        conn.commit()
        return cursor.lastrowid


def add_feedback(message_id: int, helpful: bool, comment: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO feedback (message_id, helpful, comment) VALUES (?, ?, ?)",
            (message_id, int(helpful), comment),
        )
        conn.commit()


def list_messages(conversation_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)
        ).fetchall()
        return [dict(r) for r in rows]
