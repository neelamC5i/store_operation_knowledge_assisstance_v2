# PART E — Development Readiness
## Store Operations Knowledge Assistant

---

## 1. Recommended VS Code Project Structure

```
store-ops-knowledge-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint
│   │   ├── api/
│   │   │   ├── admin.py             # /api/admin/* endpoints
│   │   │   └── employee.py          # /api/question, /api/history, /api/evaluation
│   │   ├── core/
│   │   │   ├── config.py            # env/config loading, provider selection
│   │   │   └── logging.py
│   │   ├── ingestion/
│   │   │   ├── validation.py
│   │   │   ├── extraction.py        # PyMuPDF / python-docx wrappers
│   │   │   ├── metadata_extraction.py
│   │   │   ├── versioning.py
│   │   │   ├── chunking.py
│   │   │   └── embedding.py
│   │   ├── retrieval/
│   │   │   ├── intent_router.py     # Intent Router component
│   │   │   ├── subcorpus_router.py
│   │   │   ├── date_filter.py
│   │   │   └── hybrid_search.py     # Retrieval/Evidence component
│   │   ├── generation/
│   │   │   ├── evidence_evaluator.py
│   │   │   ├── confidence.py
│   │   │   └── response_generator.py  # Response Generator component
│   │   ├── llm/
│   │   │   ├── provider_interface.py # abstract base
│   │   │   ├── groq_provider.py
│   │   │   └── ollama_provider.py
│   │   ├── storage/
│   │   │   ├── sqlite_db.py
│   │   │   ├── vector_store.py       # Chroma/FAISS wrapper
│   │   │   └── file_storage.py
│   │   └── models/                   # Pydantic + ORM models
│   └── tests/
├── frontend/
│   └── streamlit_app/
│       ├── admin_ui.py
│       └── employee_ui.py
├── data/
│   ├── originals/                    # local file storage
│   ├── sqlite/store_ops.db
│   └── vector_index/
├── evaluation/
│   ├── golden_dataset.json
│   └── run_evaluation.py
├── .env.example
├── requirements.txt
└── README.md
```

## 2. Recommended Implementation Phases

| Phase | Scope |
|---|---|
| Phase 0 | Project scaffolding, config/provider abstraction, SQLite schema, empty vector store |
| Phase 1 | Admin ingestion pipeline (upload → validate → extract → metadata → review → approve) |
| Phase 2 | Versioning, chunking, embedding, storage into Vector DB/SQLite/File Storage |
| Phase 3 | Employee flow: intent classification, sub-corpus routing, date filtering, hybrid retrieval |
| Phase 4 | Evidence evaluation, confidence scoring, grounded generation, citation, refusal |
| Phase 5 | Streaming response, conversation history, feedback |
| Phase 6 | Golden dataset + evaluation harness, metrics reporting |
| Phase 7 | UI polish (Streamlit Admin/Employee screens), error handling, demo readiness |

## 3. Database Entities

See PRD §41 Data Model: Document, DocumentVersion, Chunk, Metadata, Conversation, Message, Feedback, EvaluationRun.

## 4. API List

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/admin/upload | Upload a document |
| POST | /api/admin/approve | Approve reviewed metadata, trigger versioning/chunking/embedding |
| GET | /api/documents | List documents/versions |
| POST | /api/question | Submit an employee question, returns streamed answer or refusal |
| GET | /api/history | Retrieve session conversation history |
| GET | /api/evaluation | Trigger/retrieve golden-dataset evaluation results |
| POST | /api/feedback | Submit helpful/unhelpful feedback on a message |

## 5. LLM / Provider Interfaces

```python
class LLMProvider(ABC):
    def classify_intent(self, question: str) -> IntentResult: ...
    def extract_metadata(self, text: str) -> MetadataDraft: ...
    def generate_answer(self, question: str, evidence: list[Chunk]) -> Iterator[str]: ...
```
`GroqProvider` and `OllamaProvider` both implement `LLMProvider`; selection is via `LLM_PROVIDER` env var, read once in `core/config.py`.

## 6. Main Modules / Components

- **Intent Router** — classifies intent + detects date, routes to sub-corpus.
- **Retrieval/Evidence component** — date filtering, hybrid search, evidence evaluation, confidence calculation.
- **Response Generator** — grounded answer generation, citation assembly, refusal handling, streaming.

(Per prompt Step 6, no additional agents are introduced beyond these three plus the ingestion pipeline modules.)

## 7. Environment Variables Required

```
LLM_PROVIDER=groq            # or "ollama"
GROQ_API_KEY=<free-tier key>
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
VECTOR_DB_BACKEND=chroma     # or "faiss"
SQLITE_DB_PATH=./data/sqlite/store_ops.db
FILE_STORAGE_PATH=./data/originals
CONFIDENCE_THRESHOLD=0.6     # TBD, tuned via golden dataset
MAX_UPLOAD_SIZE_MB=20
```

## 8. Local Setup Prerequisites

- Python 3.10+ and VS Code with the Python extension.
- `pip install -r requirements.txt` (fastapi, uvicorn, streamlit, chromadb or faiss-cpu, sentence-transformers, pymupdf, python-docx, groq, requests).
- Ollama installed locally (optional, for local-LLM path) with a pulled model (e.g., `ollama pull llama3`).
- A free Groq API key (optional, for Groq path) set in `.env`.
- No GPU required; runs on CPU.

## 9. Test Strategy

| Level | Approach |
|---|---|
| Unit tests | Ingestion validators, metadata extraction parsing, date-range logic, confidence formula |
| Integration tests | Full ingestion pipeline (upload → KB Ready); full query pipeline (ask → answer/refusal) |
| Golden-dataset evaluation | Automated run of `evaluation/golden_dataset.json` against a running instance, producing the metrics in PRD §53 |
| Regression tests | Superseded-document exclusion test category run on every ingestion-pipeline change |

## 10. Definition of Done (MVP)

- All MUST-HAVE features (PART D) implemented and passing their linked test cases (PRD §57 traceability).
- Golden dataset executes end-to-end and produces a metrics report (accuracy, refusal correctness, effective-date citation accuracy, TTFT, p95 latency).
- No golden-dataset "current policy" question is ever answered from a superseded version.
- LLM provider is switchable between Groq and Ollama via `.env` only, with no code changes.
- Entire application runs from a fresh clone using only the steps in §8 above, with no paid services required.
- BRD and PRD requirement IDs are all reflected in code comments or module docstrings sufficient to trace back (manual spot-check acceptable for capstone scope).
