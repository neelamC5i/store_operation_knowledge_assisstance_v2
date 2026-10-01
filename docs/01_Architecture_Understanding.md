# PART A — Architecture Understanding
## Store Operations Knowledge Assistant

**Source of truth:** Attached architecture diagram *"Store Operations Knowledge Assistant – End to End Architecture (Using Groq / Local LLM)"*, read together with the prompt's business-logic rules (Step 4).

---

## A.1 Architecture in Plain Language

The system is a **Retrieval-Augmented Generation (RAG) assistant** for store operations content (procedures, promotions, safety rules). It has two independent but connected flows that share the same Knowledge Base:

1. **Admin Flow** — a Store Admin uploads operational documents; the system validates, extracts, versions, chunks, embeds and indexes them so the Knowledge Base is always in a known, dated, versioned state.
2. **User Flow** — a Store Employee asks a natural-language question; the system classifies intent, routes to the right sub-corpus, filters by effective date, retrieves evidence, checks whether that evidence is sufficient, and either generates a grounded, cited answer or refuses.

Both flows depend on a common **Storage Layer** (Vector DB, SQLite, File Storage) and a common **Supporting Services** layer (embedding model, database, vector DB, Groq/local LLM), so the two flows are really two consumers of one knowledge platform, not two separate systems.

---

## A.2 Admin Flow — Step by Step

| # | Step | What happens | Notes / Ambiguity |
|---|------|---------------|--------------------|
| 1 | **Upload Document** | Admin uploads PDF/DOCX/TXT/CSV | File type list is fixed by diagram; no other formats implied |
| 2 | **File Processing & Text Extraction** | File size & type validated; corruption/empty check; text parsed (PDF parser), tables/images handled | **Assumption:** "handle tables/images" means extracting surrounding text context, not full OCR/vision unless stated — flagged as TBD |
| 3 | **Metadata Extraction (LLM + Rules)** | Category, type, version, effective dates, document description extracted using a mix of LLM inference and rule-based logic | **Assumption:** exact split between "LLM" vs "Rules" per field is an implementation decision, not fixed by diagram |
| 4 | **Admin Review & Confirmation** | Admin views extracted metadata, edits if needed, approves/rejects | This is the human-in-the-loop gate before anything enters the searchable KB |
| 5 | **Version Management** | Maintains versions, tracks superseded docs, keeps history | Confirms Step 4 business rule: old versions are never deleted, only superseded |
| 6 | **Chunking** | Splits into chunks by section/page/clause; attaches metadata to each chunk | Chunk-level metadata carries the document's version/effective-date forward — critical for date-aware retrieval later |
| 7 | **Generate Embeddings** | Uses local embedding model to create vector embeddings | Confirms "no GPU / no paid API" constraint applies here too |
| 8 | **Storage Layer** | Vector DB (Chroma/FAISS) for embeddings, SQLite for metadata & versions, File Storage for originals | Three storage destinations updated together — implies a transactional/consistency requirement, marked as an NFR |

Result: **Knowledge Base Ready** state — indexed, versioned, date-aware, organized into three sub-corpora (Procedures, Promotions, Safety Rules).

---

## A.3 User Flow — Step by Step

| # | Step | What happens | Notes / Ambiguity |
|---|------|---------------|--------------------|
| 6 | **Ask a Question** | Employee enters text (optionally with device/date context) | Numbering continues from Admin flow (1–8) in the diagram, i.e., these are steps 6–14 of one continuous numbered sequence, confirming both flows are one pipeline |
| 7 | **Intent Classification (Groq LLM)** | Detects question type; detects a date if mentioned | Feeds Sub-Corpus Routing and Effective-Date Filtering |
| 8 | **Sub-Corpus Routing** | Routes to Procedures / Promotions / Safety (or "Unknown" per Step 4 business logic in the prompt — diagram doesn't show "Unknown" explicitly, so this is an **assumption** reconciling diagram + prompt) |
| 9 | **Effective-Date Filtering** | Checks current validity; excludes superseded docs; handles historical queries | This is where "current policy" vs "historical policy" business rules are enforced |
| 10 | **Semantic Retrieval** | Vector + keyword (hybrid) search; retrieves top-K chunks; applies metadata filters | "Hybrid" = vector + keyword per diagram label |
| 11 | **Evidence Evaluation** | Checks relevance, coverage, calculates confidence | Feeds the Yes/No decision gate |
| — | **Decision Gate: Sufficient evidence?** | Yes → Answer Generation. No → Refusal Response | Core of the "evidence-first / refuse rather than hallucinate" rule |
| 12 | **Answer Generation (Groq LLM)** | Grounded on evidence; includes source & date; explicit "no hallucination" | |
| 13 | **Streaming Response** | Token streaming; fast first response; low latency | Feeds NFR for Time-to-First-Token |
| 14 | **Final Response to User** | Answer/Refusal + citation + effective date + confidence score | |
| (Refusal path) | **Refusal Response** | Explains why no answer; suggests supervisor; logs for evaluation | Refusal is a first-class, logged outcome, not an error state |

A **Conversation History & Feedback** component sits below the whole User Flow, feeding back into the loop (context for follow-up questions, feedback for evaluation).

---

## A.4 Relationship Between Admin Flow and User Flow

- The Admin Flow is the **write path** into the shared Knowledge Base (Vector DB + SQLite + File Storage).
- The User Flow is the **read path** out of the same Knowledge Base.
- They never bypass each other: a document cannot be queried until it has passed through Admin Review & Confirmation and is marked "Knowledge Base Ready."
- Both flows call the same **Supporting Services** (Groq/local LLM abstraction, embedding model, SQLite, Vector DB) — this is why the diagram places "Supporting Services" as a shared box between the two flows rather than duplicating it.
- Document versioning (Admin Flow, step 5) and effective-date filtering (User Flow, step 9) are two halves of the same business rule: Admin Flow **creates** the version/date metadata; User Flow **consumes** it to decide what counts as "current" vs "historical."

---

## A.5 Knowledge Sub-Corpora

| Sub-corpus | Example content (from diagram) |
|---|---|
| Procedures | Store operations, Returns/Refunds, Inventory/POS |
| Promotions | Current promotions, Coupons/Discounts, Combination rules |
| Safety Rules | Food handling, Fire/Emergency, Equipment safety |

---

## A.6 Storage

| Store | Purpose |
|---|---|
| Vector Database (Chroma/FAISS) | Semantic search over chunk embeddings |
| SQLite (relational metadata DB) | Document/version/metadata/chunk records, logs |
| Local File Storage | Original uploaded documents |

---

## A.7 AI / LLM Components

| Component | Role |
|---|---|
| Groq API / Local LLM (Ollama) | Intent classification, metadata extraction assistance, grounded answer generation — behind one provider-abstraction interface |
| Embedding model (Sentence Transformers, local) | Chunk & query embeddings |
| Intent classification | Determines question type & routes to sub-corpus |
| Metadata extraction | Populates category/type/version/effective date at ingestion |
| Grounded answer generation | Produces final answer strictly from retrieved evidence |

---

## A.8 Evaluation (from diagram's "Evaluation & Golden Dataset" box)

| Metric | Measures |
|---|---|
| Answer accuracy | Correctness of generated answers vs golden answers |
| Refusal correctness | Whether the system refuses exactly when it should (and doesn't when it shouldn't) |
| Effective-date citation accuracy | Whether the cited date/version matches the question's temporal intent |
| Time to first token (TTFT) | Streaming responsiveness |
| p95 latency | End-to-end response time at the 95th percentile |
| Golden dataset | Contains current, superseded, and unanswerable questions (expanded further in the prompt's Step 7 into 9 categories — see PRD §53) |

---

## A.9 Consolidated List of Assumptions / TBDs Identified in This Step

| ID | Item | Disposition |
|---|---|---|
| ASM-01 | Exact split of rule-based vs. LLM-based metadata extraction per field | Assumption — left to design; documented in PRD §17 |
| ASM-02 | Handling of embedded images/tables in source docs (OCR vs. text-only) | Assumption — OCR treated as Future Enhancement, not MVP |
| ASM-03 | "Unknown" intent category not drawn in diagram but required by prompt Step 4.4 | Reconciled: Unknown is included as a 4th routing outcome |
| ASM-04 | Confidence score formula/thresholds | Marked TBD — configurable, tuned via golden dataset (per prompt Step 4.8) |
| ASM-05 | Whether embeddings/metadata/file writes are atomic across the 3 stores | Assumption — treated as an NFR requiring an ingestion-transaction pattern, not a hard architectural mandate from the diagram |
| ASM-06 | Multi-turn conversation memory depth | TBD — MVP assumes short session-scoped history only |
| ASM-07 | Authentication/authorization model for Admin vs Employee roles | Not shown in diagram — treated as an assumption (simple role flag) since diagram has no auth component drawn |

These items are carried forward and never silently resolved — each appears again in the BRD "Assumptions" section and PRD "Assumptions," and drives either an explicit requirement or a Future Enhancement entry.
