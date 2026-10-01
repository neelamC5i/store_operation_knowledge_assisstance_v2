"""Persists golden-dataset evaluation results (PRD §52–53, data model §41)."""
import json

from app.storage.sqlite_db import get_connection


def save_evaluation_run(metrics: dict, golden_dataset_version: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO evaluation_runs (metrics, golden_dataset_version) VALUES (?, ?)",
            (json.dumps(metrics, default=str), golden_dataset_version),
        )
        conn.commit()
        return cursor.lastrowid


def list_evaluation_runs() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM evaluation_runs ORDER BY id DESC").fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["metrics"] = json.loads(d["metrics"])
            results.append(d)
        return results
