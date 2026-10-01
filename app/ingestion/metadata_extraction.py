"""Metadata proposal: rule-based first pass (filename/date patterns) for version and
effective date, LLM used only for category + description (ASM-01 recommendation) — reduces
Groq free-tier call volume since rules alone resolve the fields regex can reliably parse."""
import re
from datetime import date, datetime

from app.llm.provider_interface import LLMProvider
from app.models.schemas import MetadataDraft

_VERSION_PATTERN = re.compile(
    r"(?:^|[_\s-])v(?:ersion)?[\s_-]?(\d+(?:\.\d+)?)(?!\d)", re.IGNORECASE
)

_DATE_PATTERNS = [
    (re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})(?!\d)"), "%Y-%m-%d"),
    (re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b"), "%m/%d/%Y"),
    (
        re.compile(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
            re.IGNORECASE,
        ),
        None,
    ),
]

_INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard the system prompt",
    "you are now",
    "act as",
    "override your instructions",
    "forget everything above",
]


def extract_version_from_text(filename: str, text: str) -> str | None:
    for source in (filename, text[:500]):
        match = _VERSION_PATTERN.search(source)
        if match:
            return f"v{match.group(1)}"
    return None


def extract_date_from_text(filename: str, text: str) -> date | None:
    for source in (filename, text[:1000]):
        for pattern, fmt in _DATE_PATTERNS:
            match = pattern.search(source)
            if not match:
                continue
            try:
                if fmt == "%Y-%m-%d":
                    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                if fmt == "%m/%d/%Y":
                    return date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
                # Month name pattern
                return datetime.strptime(
                    f"{match.group(1)} {match.group(2)} {match.group(3)}", "%B %d %Y"
                ).date()
            except ValueError:
                continue
    return None


def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _INJECTION_PHRASES)


def propose_metadata(full_text: str, filename: str, provider: LLMProvider) -> MetadataDraft:
    rule_version = extract_version_from_text(filename, full_text)
    rule_date = extract_date_from_text(filename, full_text)

    llm_draft = provider.extract_metadata(full_text, filename)

    version = rule_version or llm_draft.version
    effective_from = rule_date or llm_draft.effective_from
    extracted_by = "rule+llm" if (rule_version or rule_date) else "llm"

    low_confidence = (
        llm_draft.low_confidence
        or rule_version is None
        or rule_date is None
        or llm_draft.category == "Unknown"
    )

    return MetadataDraft(
        category=llm_draft.category,
        doc_type=llm_draft.doc_type,
        version=version,
        effective_from=effective_from,
        description=llm_draft.description,
        extracted_by=extracted_by,
        low_confidence=low_confidence,
        prompt_injection_suspected=detect_prompt_injection(full_text),
    )
