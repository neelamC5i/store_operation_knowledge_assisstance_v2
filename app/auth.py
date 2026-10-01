"""Login against the local JSON credentials file (NFR-008: simple role flag, no enterprise auth)."""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class AuthenticatedUser:
    username: str
    role: str  # "admin" or "employee"


def _load_users() -> list[dict]:
    path = Path(settings.credentials_file)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("users", [])


def authenticate(username: str, password: str) -> AuthenticatedUser | None:
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    for user in _load_users():
        if user.get("username") == username and user.get("password_sha256") == password_hash:
            return AuthenticatedUser(username=username, role=user.get("role", "employee"))
    return None
