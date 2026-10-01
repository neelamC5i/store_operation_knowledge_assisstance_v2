"""Local filesystem storage for original uploaded documents (NFR-007)."""
import shutil
from pathlib import Path

from app.core.config import settings


def save_original(source_path: str, document_version_id: int, original_filename: str) -> str:
    dest_dir = Path(settings.file_storage_path)
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_filename).suffix
    dest_path = dest_dir / f"{document_version_id}{suffix}"
    shutil.copyfile(source_path, dest_path)
    return str(dest_path)
