"""Splits extracted sections into chunks aligned to section/page boundaries (FR-021, FR-022)."""
import re

from app.ingestion.extraction import ExtractedDocument
from app.models.schemas import ChunkDraft

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_into_pieces(text: str) -> list[str]:
    pieces = _SENTENCE_SPLIT.split(text)
    return [p.strip() for p in pieces if p.strip()]


def chunk_sections(extracted: ExtractedDocument, max_chars: int = 800) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    for section in extracted.sections:
        pieces = _split_into_pieces(section.text)
        current = ""
        for piece in pieces:
            candidate = f"{current} {piece}".strip() if current else piece
            if len(candidate) > max_chars and current:
                chunks.append(ChunkDraft(section=section.label, page=section.page, chunk_text=current))
                current = piece
            else:
                current = candidate
        if current:
            chunks.append(ChunkDraft(section=section.label, page=section.page, chunk_text=current))
    return chunks
