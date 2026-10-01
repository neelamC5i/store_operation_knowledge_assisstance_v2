"""Confidence formula (ASM-04 resolved): a weighted combination of retrieval/evidence
signals — never the LLM's self-reported confidence alone (BRULE-05). Weights are a
documented default, meant to be tuned against the golden dataset in Phase 6."""

WEIGHTS = {
    "relevance": 0.4,
    "coverage": 0.3,
    "date_validity": 0.2,
    "source_consistency": 0.1,
}


def compute_confidence(
    relevance: float, coverage: float, date_validity: bool, source_consistency: float
) -> float:
    date_gate = 1.0 if date_validity else 0.0
    return (
        WEIGHTS["relevance"] * relevance
        + WEIGHTS["coverage"] * coverage
        + WEIGHTS["date_validity"] * date_gate
        + WEIGHTS["source_consistency"] * source_consistency
    )
