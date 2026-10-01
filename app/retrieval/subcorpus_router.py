"""Routes a classified question to one sub-corpus, or all of them for 'Unknown' (FR-029, FR-030)."""
from app.models.schemas import IntentResult

ALL_CATEGORIES = ["Procedures", "Promotions", "Safety"]


def route(intent: IntentResult) -> list[str]:
    if intent.category == "Unknown":
        return ALL_CATEGORIES
    return [intent.category]
