# Store Operations Knowledge Assistant

Locally-run RAG assistant for store operations knowledge (Procedures / Promotions / Safety),
with a versioned, date-aware knowledge base and citation-or-refusal answers. See `docs/` for
the BRD, PRD, and architecture that this build follows.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env    # then set GROQ_API_KEY (default provider)
```

## Run

Run from the project root, with the project root on `PYTHONPATH` (Streamlit puts
`app/`'s own folder on `sys.path`, not the repo root, which otherwise breaks the
`from app.* import ...` absolute imports with `ModuleNotFoundError: No module named 'app'`):

```bash
# macOS/Linux
PYTHONPATH=. streamlit run app/main.py
```

```powershell
# Windows PowerShell
$env:PYTHONPATH = "."
streamlit run app/main.py
```

## Demo logins

Defined in `credentials.json` (SHA-256 hashed; change before any real deployment):

| Username | Password | Role |
|---|---|---|
| admin | admin123 | admin |
| employee | employee123 | employee |

## Try it with sample data

```bash
python scripts/seed_sample_documents.py   # ingests sample_documents/ via the real pipeline
streamlit run app/main.py                 # log in as employee/employee123 and ask a question
python evaluation/run_evaluation.py       # runs the 18-question golden dataset, prints metrics
```

## Tests

```bash
pytest
```

## Status

- **Phase 0 (scaffolding)** — done: project structure, config/provider abstraction, SQLite schema,
  empty vector store, single login page with role-gated views.
- **Phase 1 (Admin ingestion pipeline)** — done: upload, validation (type/size/corruption),
  text extraction with section/page structure, rule-based + LLM metadata proposal, prompt-injection
  heuristic flagging, Admin review/edit/approve/reject screen, version-history view. Approved
  uploads are persisted as `document_versions` with `status='pending'`; versioning/supersede,
  chunking, and embedding run in Phase 2.

- **Phase 2 (Versioning/storage)** — done: on Approve, the pipeline chunks the extracted text,
  embeds it locally (Sentence-Transformers), writes chunks to SQLite and embeddings to Chroma,
  then flips the version to `active` — superseding any prior active version of the same document
  (`status='superseded'`, `effective_to` set to the day before the new version's effective date).
  If chunking/embedding fails, the version is marked `failed` and partial chunk rows are rolled
  back rather than left inconsistent with the vector store.

- **Phase 3 (Employee retrieval)** — done: intent classification + date detection (LLM),
  sub-corpus routing (Unknown searches all three corpora before falling back to refusal, FR-030),
  effective-date eligibility resolved against SQLite (current → active versions only; a stated
  past date → whichever version's range contains it, active or superseded), and hybrid retrieval
  (Chroma vector search + BM25 keyword search merged via reciprocal rank fusion), all scoped to
  the eligible document versions before ranking. Exposed as `orchestrator.retrieve_evidence()`
  for Phase 4 to consume.

Requires a real `GROQ_API_KEY` in `.env` for intent classification, metadata extraction, and
(later) answer-generation LLM calls — rule-based extraction covers version/date without it, but
category/description/intent still call the configured provider. Embedding, retrieval, and
Chroma/SQLite writes work fully offline.

- **Phase 4 (Generation)** — done: evidence evaluation (relevance, question-term coverage,
  a date-validity gate, source consistency), a documented default confidence formula
  (`app/generation/confidence.py`, weights tunable later against the golden dataset), the
  answer/refuse decision gate, citation assembly (deduped by document+version), and a refusal
  path that logs the question/routing/evidence signals (FR-044). Exposed as
  `response_generator.generate()` for the Phase 5 chat UI to call.

- **Phase 5 (Streaming, history, feedback)** — done: the Employee chat screen now calls
  `response_generator.generate()` directly, streaming the answer token-by-token via
  `st.write_stream`, showing citations + confidence (or the refusal message), and an optional
  "as of a past date" field that overrides LLM date-detection (PRD §38). Every user/assistant
  turn is persisted to `conversations`/`messages`, and 👍/👎 buttons write to `feedback`, linked
  by `message_id`.

- **Phase 6 (Sample content + golden dataset + evaluation harness)** — done: five sample
  documents in `sample_documents/` (a superseded/current Return Policy pair, Inventory & POS
  Procedures, Store Promotions, Store Safety Rules), seeded through the real pipeline by
  `scripts/seed_sample_documents.py`; `evaluation/golden_dataset.json` covering all 9 PRD §53
  categories (2 questions each); and `evaluation/run_evaluation.py`, which runs the dataset
  end-to-end, grades answer accuracy / refusal correctness / effective-date citation accuracy,
  measures TTFT and p95 latency, and stores the result as an `EvaluationRun` row.

  Run it yourself (after seeding, and with a real `GROQ_API_KEY` set):
  ```bash
  python scripts/seed_sample_documents.py
  python evaluation/run_evaluation.py
  ```

  Building this harness surfaced and fixed two real correctness bugs: retrieval's relevance
  score was rank-based (reciprocal rank fusion), so the top hit always normalized to ~1.0
  confidence *even when nothing in the KB was actually relevant* — unanswerable questions were
  getting answered instead of refused. Fixed by scoring relevance from actual vector cosine
  similarity (`hybrid_search.py`, Chroma collection now configured for cosine space). Separately,
  the evidence-coverage heuristic missed section headings and a document's own title entirely
  (an extraction quirk: a title heading immediately followed by a sub-heading never accrues body
  text — see `extraction.py`), causing legitimate answerable questions to under-score on
  coverage and refuse incorrectly; fixed by including section labels, document titles, and a
  light stemming pass in `evidence_evaluator.py`. With a deterministic keyword-based stub LLM
  (real embeddings/retrieval, no network), all 18 golden-dataset questions now grade correctly.

- **Phase 7 (Polish)** — done: upload/metadata-extraction and question-answering failures now
  show a plain-language message instead of a raw traceback (FR-050/FR-051 — check
  `GROQ_API_KEY`/connection), and the Admin screen has a KB Health dashboard (document counts,
  active/superseded/failed version counts, per-category counts — `documents_repo.get_kb_stats()`).

## Definition of Done (Development Readiness §10)

- [x] All MUST-HAVE features (MVP Feature List) implemented, each with passing tests (32/32).
- [x] Golden dataset executes end-to-end and produces a metrics report (demonstrated with a
      deterministic stub LLM; a live baseline run needs your own `GROQ_API_KEY` — no numeric
      pass/fail targets are invented, per PAC-02/NFR-016).
- [x] No golden-dataset "current policy" question is ever answered from a superseded version
      (enforced by `date_filter`/`list_eligible_version_ids`, covered by tests).
- [x] LLM provider switches between Groq and Ollama via `.env` only (`LLM_PROVIDER`), no code change.
- [x] Runs end-to-end from a fresh clone using only the steps above, no paid services required
      beyond a free-tier Groq key (or Ollama, fully offline).
- [x] BRD/PRD requirement IDs are cited in module docstrings throughout (`FR-*`, `BR*`, `NFR-*`)
      for manual traceability.
