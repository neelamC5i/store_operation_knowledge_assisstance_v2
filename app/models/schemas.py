"""Shared data shapes passed between ingestion, retrieval, and generation modules."""
from dataclasses import dataclass, field
from datetime import date
from typing import Iterator, Literal

Category = Literal["Procedures", "Promotions", "Safety", "Unknown"]


@dataclass
class IntentResult:
    category: Category
    detected_date: date | None = None


@dataclass
class MetadataDraft:
    category: Category
    doc_type: str
    version: str
    effective_from: date
    description: str
    extracted_by: Literal["rule", "llm", "rule+llm"]
    low_confidence: bool = False
    prompt_injection_suspected: bool = False


@dataclass
class ChunkDraft:
    section: str | None
    page: int | None
    chunk_text: str


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_version_id: int
    document_title: str
    section: str | None
    version: str
    effective_from: date
    effective_to: date | None
    chunk_text: str
    relevance_score: float


@dataclass
class EvidenceEvaluation:
    relevance: float
    coverage: float
    date_validity: bool
    source_consistency: float
    confidence: float
    sufficient: bool


@dataclass
class Citation:
    document_title: str
    section: str | None
    version: str
    effective_from: date
    effective_to: date | None
    confidence: float


@dataclass
class AnswerResult:
    is_refusal: bool
    text_stream: Iterator[str] | None = None
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0
    refusal_reason: str | None = None
