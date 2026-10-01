"""Runs golden_dataset.json against the live system and reports the PRD §53 metrics.
No numeric pass/fail thresholds are invented here (NFR-016) — this produces the first
baseline for the KB seeded by scripts/seed_sample_documents.py.

Categories G (ambiguous) and I (cross-sub-corpus) use a softer expected_outcome
("refusal_or_clarify" / "answer_or_refusal_acceptable") and are intentionally excluded
from strict accuracy scoring — they're logged in full for manual review instead."""
import json
import math
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.generation.response_generator import generate  # noqa: E402
from app.llm.provider_interface import get_provider  # noqa: E402
from app.storage.evaluation_repo import save_evaluation_run  # noqa: E402

_DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "golden_dataset.json"
_STRICT_OUTCOMES = {"answer", "refusal"}


def _parse_date(value):
    from datetime import datetime as dt

    return dt.strptime(value, "%Y-%m-%d").date() if value else None


def _percentile(data: list[float], pct: float) -> float | None:
    if not data:
        return None
    data = sorted(data)
    k = (len(data) - 1) * pct
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return data[int(k)]
    return data[f] + (data[c] - data[f]) * (k - f)


def _grade(question: dict, result, elapsed: float, ttft: float | None) -> dict:
    expected_outcome = question["expected_outcome"]
    actual_outcome = "refusal" if result.is_refusal else "answer"
    graded = expected_outcome in _STRICT_OUTCOMES

    correct = None
    date_citation_correct = None
    if graded:
        if expected_outcome == "refusal":
            correct = actual_outcome == "refusal"
        else:
            title_ok = not question.get("expected_document_title") or any(
                c.document_title == question["expected_document_title"] for c in result.citations
            )
            version_ok = not question.get("expected_version") or any(
                c.version == question["expected_version"] for c in result.citations
            )
            correct = actual_outcome == "answer" and title_ok and version_ok
            if question.get("expected_version"):
                date_citation_correct = actual_outcome == "answer" and version_ok

    return {
        "id": question["id"],
        "test_category": question["test_category"],
        "question": question["question"],
        "expected_outcome": expected_outcome,
        "actual_outcome": actual_outcome,
        "confidence": result.confidence,
        "citations": [f"{c.document_title} {c.version}" for c in result.citations],
        "graded": graded,
        "correct": correct,
        "date_citation_correct": date_citation_correct,
        "ttft_seconds": ttft,
        "latency_seconds": elapsed,
    }


def run(golden_dataset_path: str | Path = _DEFAULT_DATASET_PATH, provider=None) -> dict:
    provider = provider or get_provider()
    with open(golden_dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results = []
    for question in dataset["questions"]:
        as_of_date = _parse_date(question.get("as_of_date"))
        start = time.perf_counter()
        result = generate(question["question"], provider, override_date=as_of_date)

        ttft = None
        if not result.is_refusal:
            for i, _token in enumerate(result.text_stream):
                if i == 0:
                    ttft = time.perf_counter() - start
        elapsed = time.perf_counter() - start

        results.append(_grade(question, result, elapsed, ttft))

    graded = [r for r in results if r["graded"]]
    answer_results = [r for r in graded if r["expected_outcome"] == "answer"]
    refusal_results = [r for r in graded if r["expected_outcome"] == "refusal"]
    date_cited = [r for r in graded if r["date_citation_correct"] is not None]

    def _rate(items: list[dict], key: str = "correct") -> float | None:
        return sum(1 for r in items if r[key]) / len(items) if items else None

    ttft_values = [r["ttft_seconds"] for r in results if r["ttft_seconds"] is not None]
    latency_values = [r["latency_seconds"] for r in results]

    by_category = {}
    for category in sorted({r["test_category"] for r in results}):
        category_graded = [r for r in graded if r["test_category"] == category]
        by_category[category] = {
            "total": len([r for r in results if r["test_category"] == category]),
            "graded": len(category_graded),
            "accuracy": _rate(category_graded),
        }

    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "golden_dataset_version": dataset.get("version", "unknown"),
        "total_questions": len(results),
        "overall": {
            "answer_accuracy": _rate(answer_results),
            "refusal_correctness": _rate(refusal_results),
            "date_citation_accuracy": _rate(date_cited, key="date_citation_correct"),
            "avg_ttft_seconds": statistics.mean(ttft_values) if ttft_values else None,
            "p95_latency_seconds": _percentile(latency_values, 0.95),
        },
        "by_category": by_category,
        "results": results,
    }

    run_id = save_evaluation_run(metrics, dataset.get("version", "unknown"))
    metrics["evaluation_run_id"] = run_id
    return metrics


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, default=str))
