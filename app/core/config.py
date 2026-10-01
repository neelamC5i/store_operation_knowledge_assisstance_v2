"""Central config loading — reads .env once; every module reads settings from here."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3")

    embedding_model_name: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    vector_db_backend: str = os.getenv("VECTOR_DB_BACKEND", "chroma")

    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "data" / "sqlite" / "store_ops.db"))
    file_storage_path: str = os.getenv("FILE_STORAGE_PATH", str(BASE_DIR / "data" / "originals"))
    vector_index_path: str = os.getenv("VECTOR_INDEX_PATH", str(BASE_DIR / "data" / "vector_index"))

    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
    top_k: int = int(os.getenv("TOP_K", "5"))

    credentials_file: str = os.getenv("CREDENTIALS_FILE", str(BASE_DIR / "credentials.json"))


settings = Settings()
