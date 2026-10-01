"""Upload validation: file type, size, and corruption/empty checks (FR-002, FR-003, FR-004)."""
from dataclasses import dataclass
from pathlib import Path

import docx
import pymupdf as fitz

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}


@dataclass
class ValidationResult:
    ok: bool
    error: str | None = None


def validate_upload(file_path: str, filename: str) -> ValidationResult:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return ValidationResult(
            ok=False,
            error=f"Unsupported file type '{suffix}'. Allowed types: PDF, DOCX, TXT, CSV.",
        )

    size_mb = Path(file_path).stat().st_size / (1024 * 1024)
    if size_mb == 0:
        return ValidationResult(ok=False, error="The uploaded file is empty.")
    if size_mb > settings.max_upload_size_mb:
        return ValidationResult(
            ok=False,
            error=f"File is {size_mb:.1f} MB, which exceeds the {settings.max_upload_size_mb} MB limit.",
        )

    try:
        if suffix == ".pdf":
            with fitz.open(file_path) as doc:
                if doc.page_count == 0:
                    return ValidationResult(ok=False, error="The PDF has no pages.")
        elif suffix == ".docx":
            document = docx.Document(file_path)
            if not document.paragraphs:
                return ValidationResult(ok=False, error="The DOCX file appears to be empty.")
        else:  # .txt / .csv
            with open(file_path, "r", encoding="utf-8", errors="strict") as f:
                content = f.read()
            if not content.strip():
                return ValidationResult(ok=False, error="The file appears to be empty.")
    except Exception as exc:  # noqa: BLE001 — surfaced to the Admin as a validation failure
        return ValidationResult(ok=False, error=f"The file appears to be corrupted: {exc}")

    return ValidationResult(ok=True)
