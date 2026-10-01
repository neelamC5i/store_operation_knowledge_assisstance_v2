"""Ollama-backed LLM provider — config-only fallback (NFR-002), same interface as GroqProvider."""
import json
from datetime import date, datetime
from typing import Iterator

import requests

from app.core.config import settings
from app.llm.provider_interface import LLMProvider
from app.models.schemas import IntentResult, MetadataDraft, RetrievedChunk
from app.llm.groq_provider import _INTENT_PROMPT, _METADATA_PROMPT, _ANSWER_SYSTEM_PROMPT, _VALID_CATEGORIES


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model

    def _generate(self, prompt: str, system: str | None = None, stream: bool = False):
        payload = {
            "model": self._model,
            "prompt": prompt,
            "system": system,
            "stream": stream,
        }
        response = requests.post(f"{self._base_url}/api/generate", json=payload, stream=stream)
        response.raise_for_status()
        return response

    def classify_intent(self, question: str) -> IntentResult:
        response = self._generate(_INTENT_PROMPT.format(question=question))
        data = json.loads(response.json()["response"])
        category = data.get("category") if data.get("category") in _VALID_CATEGORIES else "Unknown"
        detected_date = None
        if data.get("detected_date"):
            try:
                detected_date = datetime.strptime(data["detected_date"], "%Y-%m-%d").date()
            except ValueError:
                detected_date = None
        return IntentResult(category=category, detected_date=detected_date)

    def extract_metadata(self, text: str, filename: str) -> MetadataDraft:
        response = self._generate(_METADATA_PROMPT.format(filename=filename, text=text[:6000]))
        data = json.loads(response.json()["response"])
        category = data.get("category") if data.get("category") in _VALID_CATEGORIES else "Unknown"
        try:
            effective_from = datetime.strptime(data.get("effective_from", ""), "%Y-%m-%d").date()
            low_confidence = False
        except ValueError:
            effective_from = date.today()
            low_confidence = True
        return MetadataDraft(
            category=category,
            doc_type=data.get("doc_type", "Unknown"),
            version=data.get("version", "v1"),
            effective_from=effective_from,
            description=data.get("description", ""),
            extracted_by="llm",
            low_confidence=low_confidence or category == "Unknown",
        )

    def generate_answer(self, question: str, evidence: list[RetrievedChunk]) -> Iterator[str]:
        evidence_block = "\n\n".join(
            f"[Source: {c.document_title}, section {c.section}, version {c.version}, "
            f"effective {c.effective_from}]\n{c.chunk_text}"
            for c in evidence
        )
        response = self._generate(
            prompt=f"Evidence:\n{evidence_block}\n\nQuestion: {question}",
            system=_ANSWER_SYSTEM_PROMPT,
            stream=True,
        )
        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            token = data.get("response", "")
            if token:
                yield token
