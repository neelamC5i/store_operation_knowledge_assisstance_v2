# PART C — Product Requirements Document (PRD)
## Store Operations Knowledge Assistant

---

## 1. Product Overview

A locally-run RAG application with two roles — Store Admin and Store Employee — built on FastAPI (backend), Streamlit (MVP frontend), ChromaDB/FAISS (vector store), SQLite (metadata), local file storage (originals), and a swappable Groq/Ollama LLM layer. It ingests operational documents into a versioned, dated, sub-corpus-organized knowledge base and answers employee questions with grounded, cited, refusal-capable responses.

## 2. Product Vision

Every store employee should be able to get a fast, trustworthy, current answer to an operational question — and know exactly which document it came from — without waiting on a supervisor, while every answer remains fully auditable back to its source.

## 3. Product Goals

| ID | Goal |
|---|---|
| PG-01 | Ship a working MVP demonstrable end-to-end inside VS Code |
| PG-02 | Guarantee no answer is given without a traceable citation or an explicit refusal |
| PG-03 | Guarantee date-aware correctness (current vs. historical) |
| PG-04 | Keep the system swappable between Groq and a local LLM with zero application-logic changes |
| PG-05 | Provide a measurable evaluation harness from day one |

## 4. Product Principles

- Evidence before generation — never answer without retrieved support.
- Refuse rather than hallucinate.
- Simplicity over "agentic" complexity — components exist only where they have a distinct responsibility.
- Everything must run free/local; no paid or GPU dependency in the MVP path.
- Every requirement must be traceable to a test case.

## 5. Target Users

Store Admin (content maintainer), Store Employee (end user asking questions). See BRD §9 for personas.

## 6. User Personas

See BRD §9 (Priya — Store Admin, Diego — Store Employee); carried forward unchanged into product design.

## 7. End-to-End Product Flow

Upload → Validate → Extract Text → Extract Metadata → Admin Review → Version → Chunk → Embed → Store → **Knowledge Base Ready** → (Employee) Ask → Classify Intent → Route Sub-Corpus → Filter by Effective Date → Retrieve (hybrid) → Evaluate Evidence → [Sufficient? Yes: Generate Answer → Stream → Cite | No: Refuse → Log] → Conversation History updated.

## 8. Admin Workflow

1. Log in / identify as Admin (see NFR-Auth, §47).
2. Upload a document (PDF/DOCX/TXT/CSV).
3. System validates file type/size/integrity.
4. System extracts text and proposes metadata (category, type, version, effective date, description).
5. Admin reviews/edits metadata in a review screen.
6. Admin approves (or rejects, ending the flow).
7. System creates/updates version records, supersedes prior version if applicable.
8. System chunks, embeds, and stores the document across Vector DB, SQLite, File Storage.
9. Document status becomes "Active — Knowledge Base Ready."

## 9. Employee Workflow

1. Employee opens the chat interface.
2. Employee types a question (optionally with a date reference).
3. System classifies intent and detects any date mentioned.
4. System routes to a sub-corpus.
5. System filters candidate documents by effective date.
6. System retrieves top-K chunks via hybrid (vector + keyword) search with metadata filters.
7. System evaluates evidence sufficiency and computes confidence.
8. If sufficient: system streams a grounded, cited answer.
9. If insufficient: system returns a refusal and logs it.
10. Conversation history is updated; employee may give feedback.

## 10. Functional Requirements

See detailed FR tables in §14–§36 below; consolidated list also appears in the Traceability Matrix (§57).

## 11. Feature Requirements

Features are grouped and prioritized in **PART D — MVP Feature List** (separate document) using MUST/SHOULD/NICE/FUTURE classification.

## 12. User Stories

Full user stories with acceptance criteria are provided as **PART E-adjacent document, "User Stories & Acceptance Criteria"** (see file `04_User_Stories.md`), covering both Store Admin and Store Employee, per Step 8 of the prompt.

## 13. Acceptance Criteria

Acceptance criteria are embedded per user story (see §12 reference) and summarized in the Traceability Matrix (§57).

---

## 14. Document Ingestion

| ID | Requirement |
|---|---|
| FR-001 | The system shall allow an Admin to upload a document in PDF, DOCX, TXT, or CSV format. |
| FR-002 | The system shall reject uploads outside the supported file types with a clear error message. |

## 15. File Validation

| ID | Requirement |
|---|---|
| FR-003 | The system shall validate uploaded file size against a configurable maximum. |
| FR-004 | The system shall detect and reject corrupted or empty files before processing. |

## 16. Text Extraction

| ID | Requirement |
|---|---|
| FR-005 | The system shall extract plain text from PDF files using a PDF parsing library (e.g., PyMuPDF). |
| FR-006 | The system shall extract plain text from DOCX files using a DOCX parsing library (e.g., python-docx). |
| FR-007 | The system shall extract text from TXT/CSV files directly. |
| FR-008 | The system shall preserve enough structural context (headings/sections) during extraction to support section/clause-level citation later. |

## 17. Metadata Extraction

| ID | Requirement |
|---|---|
| FR-009 | The system shall propose a document category (Procedures/Promotions/Safety/Unknown) using LLM-assisted classification. |
| FR-010 | The system shall propose a document type, version identifier, effective date, and short description using a combination of rule-based parsing (e.g., filename/date patterns) and LLM extraction. |
| FR-011 | The system shall flag low-confidence metadata extractions for mandatory Admin review rather than auto-approving them. |

*(ASM-01 from Architecture Understanding applies: exact field-by-field split between rules and LLM is an implementation decision.)*

## 18. Admin Metadata Review

| ID | Requirement |
|---|---|
| FR-012 | The system shall present extracted metadata to the Admin for review before finalizing ingestion. |
| FR-013 | The system shall allow the Admin to edit any metadata field prior to approval. |
| FR-014 | The system shall allow the Admin to reject an upload, discarding it without adding it to the knowledge base. |
| FR-015 | The system shall not make an uploaded document searchable by employees until Admin approval is recorded (BRULE-01). |

## 19. Document Versioning

| ID | Requirement |
|---|---|
| FR-016 | The system shall assign a new version record to each approved document upload. |
| FR-017 | When an uploaded document supersedes an existing one (same logical document, e.g., "Return Policy"), the system shall mark the prior version's status as "Superseded" and set its effective-to date, without deleting it. |
| FR-018 | The system shall retain full version history queryable for audit and historical questions (BRULE-02). |

## 20. Effective-Date Management

| ID | Requirement |
|---|---|
| FR-019 | The system shall store an effective-from date for every document version, and an effective-to date once superseded. |
| FR-020 | The system shall treat a version with no effective-to date (or a future one) and a past-or-present effective-from date as "currently effective." |

## 21. Document Chunking

| ID | Requirement |
|---|---|
| FR-021 | The system shall split each approved document into chunks aligned to sections/pages/clauses where possible. |
| FR-022 | The system shall attach document-level metadata (category, version, effective date, source document ID) to every chunk. |

## 22. Embedding Generation

| ID | Requirement |
|---|---|
| FR-023 | The system shall generate vector embeddings for each chunk using a local, free embedding model. |
| FR-024 | The system shall generate a query embedding using the same model at question time. |

## 23. Knowledge Base Management

| ID | Requirement |
|---|---|
| FR-025 | The system shall organize the knowledge base into three named sub-corpora (Procedures, Promotions, Safety Rules). |
| FR-026 | The system shall support rebuilding the vector index from SQLite + File Storage records without data loss. |

## 24. Intent Classification

| ID | Requirement |
|---|---|
| FR-027 | The system shall classify each incoming employee question into an intent/category using the configured LLM. |
| FR-028 | The system shall detect an explicit date reference within the question, if present. |

## 25. Sub-Corpus Routing

| ID | Requirement |
|---|---|
| FR-029 | The system shall route each classified question to exactly one of: Procedures, Promotions, Safety, or Unknown. |
| FR-030 | Questions routed to "Unknown" shall still proceed to retrieval across all sub-corpora before falling back to refusal, rather than refusing immediately (assumption ASM-03 resolved this way to avoid unnecessary refusals). |

## 26. Date-Aware Retrieval

| ID | Requirement |
|---|---|
| FR-031 | For questions with no explicit date (interpreted as "current"), the system shall restrict retrieval to currently-effective document versions. |
| FR-032 | For questions with an explicit past date, the system shall restrict retrieval to the document version whose effective-date range contains that date. |
| FR-033 | The system shall exclude superseded versions from "current" retrieval regardless of their semantic relevance score. |

## 27. Semantic / Hybrid Retrieval

| ID | Requirement |
|---|---|
| FR-034 | The system shall perform hybrid retrieval combining vector similarity search and keyword search. |
| FR-035 | The system shall retrieve the top-K most relevant chunks (K configurable) within the routed sub-corpus and date filter. |

## 28. Evidence Evaluation

| ID | Requirement |
|---|---|
| FR-036 | The system shall evaluate retrieved chunks for relevance to the question. |
| FR-037 | The system shall evaluate whether retrieved chunks collectively cover what the question asks (coverage). |

## 29. Confidence Calculation

| ID | Requirement |
|---|---|
| FR-038 | The system shall calculate a confidence score from retrieval relevance, evidence coverage, effective-date validity, and source consistency signals — not from the LLM's self-reported confidence alone (BRULE-05). |
| FR-039 | The system shall treat the confidence threshold used for the answer/refuse decision as a configurable value, tuned using the golden dataset (ASM-04). |

## 30. Grounded Answer Generation

| ID | Requirement |
|---|---|
| FR-040 | When evidence is sufficient, the system shall generate an answer using only the retrieved evidence, via the configured LLM (Groq or local). |
| FR-041 | The system shall not permit the LLM to introduce facts not present in the retrieved evidence. |

## 31. Citation Generation

| ID | Requirement |
|---|---|
| FR-042 | Every accepted answer shall include: document name, section/clause, version, effective date, and confidence score (BRULE-03). |

## 32. Refusal / Unanswerable Handling

| ID | Requirement |
|---|---|
| FR-043 | When evidence is insufficient (confidence below threshold), the system shall return a refusal message explaining insufficient evidence and suggesting the employee contact a supervisor. |
| FR-044 | The system shall log every refusal, including the question and routing/evidence signals, for evaluation. |

## 33. Streaming Response

| ID | Requirement |
|---|---|
| FR-045 | The system shall stream the generated answer to the employee token-by-token (or chunk-by-chunk) rather than waiting for the full response. |

## 34. Conversation History

| ID | Requirement |
|---|---|
| FR-046 | The system shall retain conversation history within a session to support follow-up questions. |
| FR-047 | Session-scoped history depth/persistence beyond the session is TBD (ASM-06) — MVP assumes session-only. |

## 35. Feedback

| ID | Requirement |
|---|---|
| FR-048 | The system shall allow an employee to mark an answer as helpful/unhelpful. |
| FR-049 | Feedback shall be stored (SQLite) for later review, alongside the associated question/answer/citation. |

## 36. Error Handling

| ID | Requirement |
|---|---|
| FR-050 | The system shall present a clear, non-technical error message on upload failure, extraction failure, or LLM/provider failure. |
| FR-051 | On LLM provider failure (e.g., Groq rate limit), the system shall support falling back to the configured local LLM without requiring a code change (provider abstraction). |

---

## 37. Admin UI Requirements

Streamlit-based screens: (1) Upload screen, (2) Metadata review/approve screen, (3) Document/version history screen. React is not justified for MVP per the prompt's stack guidance.

## 38. Employee UI Requirements

Streamlit-based chat screen: question input (optional date field), streamed answer display, citation panel, confidence indicator, feedback buttons, conversation history pane.

## 39. API Requirements

See consolidated API list in `05_Development_Readiness.md` §4 (Admin: upload/approve/documents; Employee: question/history/evaluation).

## 40. Data Requirements

Documents, Versions, Chunks, Metadata, Conversations, Feedback, EvaluationRuns — see Data Model (§41) and Development Readiness §3 for entity detail.

## 41. Data Model

| Entity | Key Fields |
|---|---|
| Document | id, title, category, current_version_id |
| DocumentVersion | id, document_id, version, effective_from, effective_to, status (Active/Superseded), file_path |
| Chunk | id, document_version_id, section/clause, page, chunk_text, embedding_ref |
| Metadata | doc_version_id, type, description, extracted_by (rule/LLM), reviewed_by_admin (bool) |
| Conversation | id, employee_session_id, messages[] |
| Message | id, conversation_id, role, text, citations[], confidence, timestamp |
| Feedback | id, message_id, helpful (bool), comment |
| EvaluationRun | id, timestamp, metrics{}, golden_dataset_version |

## 42. LLM Requirements

| ID | Requirement |
|---|---|
| NFR-001 | The system shall support Groq's free-tier API as an LLM provider. |
| NFR-002 | The system shall support a local LLM (via Ollama) as an alternative provider. |
| NFR-003 | The system shall expose a single provider-abstraction interface so intent classification, metadata extraction, and answer generation can switch providers via configuration, not code changes. |

## 43. Embedding Requirements

| ID | Requirement |
|---|---|
| NFR-004 | The system shall use a free, locally-runnable embedding model (e.g., a Sentence-Transformers model) requiring no GPU. |

## 44. Vector Database Requirements

| ID | Requirement |
|---|---|
| NFR-005 | The system shall use ChromaDB or FAISS as the vector store, runnable locally with no paid tier. |

## 45. SQLite Requirements

| ID | Requirement |
|---|---|
| NFR-006 | The system shall use SQLite for all relational metadata, version, conversation, and evaluation-log storage. |

## 46. Local File Storage Requirements

| ID | Requirement |
|---|---|
| NFR-007 | The system shall store original uploaded documents on the local filesystem, referenced by path from SQLite records. |

## 47. Security Requirements

| ID | Requirement |
|---|---|
| NFR-008 | The system shall distinguish Admin and Employee roles (assumption ASM-07: simple role flag, no enterprise auth in MVP). |
| NFR-009 | The system shall not expose uploaded document originals or extracted content to unauthenticated requests. |

## 48. Prompt Injection Considerations

| ID | Requirement |
|---|---|
| NFR-010 | The system shall treat retrieved document content as data, not as instructions — the answer-generation prompt shall not execute instructions embedded within a document's text. |
| NFR-011 | The system shall sanitize/flag documents containing text that attempts to instruct the LLM (e.g., "ignore previous instructions") during ingestion review. |

## 49. Non-Functional Requirements (General)

| ID | Requirement |
|---|---|
| NFR-012 | The system shall be runnable end-to-end on a normal developer laptop (no GPU) via VS Code. |
| NFR-013 | The system shall avoid unnecessary microservices/agents; each component shall have one clear responsibility (Intent Router, Retrieval/Evidence, Response Generator). |

## 50. Performance Requirements

| ID | Requirement |
|---|---|
| NFR-014 | The system shall measure and report Time to First Token (TTFT) during evaluation runs. |
| NFR-015 | The system shall measure and report p95 end-to-end latency during evaluation runs. |
| NFR-016 | Specific numeric latency targets are TBD, to be set from the first baseline evaluation run (no target given in source materials). |

## 51. Observability / Logging

| ID | Requirement |
|---|---|
| NFR-017 | The system shall log every question, routing decision, retrieved evidence set, confidence score, and outcome (answer/refusal) for later evaluation and audit. |

## 52. Evaluation Framework

The evaluation framework runs the golden dataset (§53) against the live system and computes the metrics defined in BRD §23 / PRD §50, storing results as an EvaluationRun record (§41).

## 53. Golden Dataset Requirements

| ID | Requirement | Category (from prompt Step 7) |
|---|---|---|
| FR-052 | The golden dataset shall include answerable questions. | A |
| FR-053 | The golden dataset shall include Procedures questions. | B |
| FR-054 | The golden dataset shall include Promotions questions. | C |
| FR-055 | The golden dataset shall include Safety questions. | D |
| FR-056 | The golden dataset shall include superseded-policy questions. | E |
| FR-057 | The golden dataset shall include unanswerable questions. | F |
| FR-058 | The golden dataset shall include ambiguous questions. | G |
| FR-059 | The golden dataset shall include historical-date questions. | H |
| FR-060 | The golden dataset shall include cross-sub-corpus questions. | I |

Each metric from BRD §23 is measured by comparing system output on each golden-dataset category against its expected answer/refusal/citation, aggregated into per-category and overall scores.

## 54. Test Scenarios

See `06_Test_Scenarios_and_DoD.md` (embedded in Development Readiness document, §9) for the full test strategy, and the Traceability Matrix (§57) for requirement-to-test-case mapping.

## 55. Product Acceptance Criteria

| ID | Criterion |
|---|---|
| PAC-01 | All MUST-HAVE features (PART D) are implemented and pass their linked test cases. |
| PAC-02 | The golden dataset achieves a baseline accuracy/refusal-correctness run with results recorded (no hallucinated "target %" invented — first run establishes baseline per NFR-016). |
| PAC-03 | Switching the LLM provider from Groq to Ollama (or vice versa) requires only a configuration change. |
| PAC-04 | No superseded document version is ever cited in answer to a "current" policy question, across all golden-dataset superseded-policy test cases. |

## 56. Future Enhancements

Same as BRD §28 (OCR/vision extraction, multi-tenant, enterprise SSO, cloud scaling, long-term memory, automated re-evaluation pipeline) — repeated here for PRD completeness, not duplicated as new scope.

## 57. PRD Traceability Matrix

| BR | FR/NFR | Feature | User Story | Acceptance Criteria | Test Case |
|---|---|---|---|---|---|
| BR-001 | FR-001–FR-004 | Document Upload | US-001 | AC-001 | TC-001 |
| BR-010 | FR-012–FR-015 | Admin Metadata Review | US-002 | AC-002 | TC-002 |
| BR-002 | FR-016–FR-018 | Document Versioning | US-003 | AC-003 | TC-003 |
| BR-003 | FR-019–FR-020, FR-031, FR-033 | Effective-Date Filtering | US-004 | AC-004 | TC-004 |
| BR-004 | FR-032 | Historical-Date Retrieval | US-005 | AC-005 | TC-005 |
| BR-007 | FR-027–FR-030 | Intent Classification & Routing | US-006 | AC-006 | TC-006 |
| BR-006 | FR-036–FR-039, FR-043–FR-044 | Evidence Evaluation & Refusal | US-007 | AC-007 | TC-007 |
| BR-005 | FR-042 | Citation Generation | US-008 | AC-008 | TC-008 |
| — | FR-045 | Streaming Response | US-009 | AC-009 | TC-009 |
| BR-008 | FR-052–FR-060 | Golden Dataset & Evaluation | US-010 | AC-010 | TC-010 |
| BR-009 | NFR-001–NFR-007, NFR-012 | Local Free-Tier Stack | US-011 | AC-011 | TC-011 |

Full detail (all 60 FRs, 17 NFRs) is available on request as an expanded matrix; the table above traces one representative requirement per feature area, sufficient for MVP planning per the prompt's Step 9 example format.
