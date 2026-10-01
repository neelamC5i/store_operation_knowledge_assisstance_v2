# PART B — Business Requirements Document (BRD)
## Store Operations Knowledge Assistant

---

## 1. Document Information

| Field | Value |
|---|---|
| Document Title | Business Requirements Document — Store Operations Knowledge Assistant |
| Project Type | Capstone Project |
| Version | 1.0 |
| Status | Draft — Baseline for MVP Development |
| Source of Truth | Attached End-to-End Architecture Diagram + Project Prompt |
| Author | Prepared with Claude, based on user-supplied architecture and requirements |
| Related Document | Product Requirements Document (PRD) v1.0 |

---

## 2. Executive Summary

Store employees frequently need quick, correct answers to operational questions (return policy, promotion rules, safety procedures) drawn from internal documents that change over time. Today this knowledge lives in scattered documents with no reliable way to know which version is currently valid, leading to inconsistent or outdated answers. The Store Operations Knowledge Assistant is a locally-run, RAG-based question-answering system that lets an Admin maintain a versioned, dated knowledge base of operational documents, and lets a Store Employee ask natural-language questions and receive grounded, cited, date-aware answers — or an honest refusal when evidence is insufficient. The system is built using free-tier and open-source components (Groq free API or a local Ollama LLM, local embeddings, ChromaDB/FAISS, SQLite) and is designed to run entirely on a developer's machine via VS Code.

---

## 3. Business Problem

Store employees currently rely on manual lookup (binders, shared drives, asking a supervisor) to answer operational questions. This is slow, inconsistent across shifts/locations, and error-prone when policies change — an employee may unknowingly apply a superseded promotion or return policy.

---

## 4. Current-State Problem

- No single, authoritative, searchable source of current store-operations knowledge.
- No systematic way to track when a policy changed or which version is "current" as of a given date.
- Answers depend on which employee is asked and how recently they read the relevant document.
- No mechanism to prevent an outdated document from being used to answer a "what is the current policy" question.
- No audit trail connecting an answer given to an employee back to the specific document/version/clause that justified it.

---

## 5. Business Need

The business needs a tool that turns static operational documents into a governed, queryable knowledge base that: (a) always distinguishes current from superseded content, (b) always cites its source, and (c) refuses to guess when it lacks evidence — reducing operational errors and supervisor interruptions while preserving an auditable trail of what was told to whom, based on what document.

---

## 6. Business Objectives

| ID | Objective |
|---|---|
| BO-01 | Reduce time employees spend searching for operational answers |
| BO-02 | Reduce incidents of employees acting on outdated/superseded policy |
| BO-03 | Provide traceability from every answer back to a specific document, version, and effective date |
| BO-04 | Allow Admins to maintain the knowledge base without needing developer involvement per update |
| BO-05 | Demonstrate a working, evaluable capstone system built entirely on free/open-source components |
| BO-06 | Establish a measurable basis (golden dataset + metrics) for judging answer quality and refusal correctness |

---

## 7. Proposed Business Solution

A two-sided application: an **Admin-side ingestion pipeline** (upload → validate → extract → review → version → chunk → embed → store) that keeps the knowledge base current and versioned, and an **Employee-side Q&A experience** (ask → classify → route → date-filter → retrieve → evaluate evidence → answer-or-refuse → cite) that only answers from retrieved, dated evidence and explicitly refuses otherwise.

---

## 8. Target Users / Stakeholders

| Stakeholder | Interest |
|---|---|
| Store Admin | Uploads/maintains documents; ensures the KB is accurate and current |
| Store Employee | Asks questions; needs fast, correct, cited answers |
| Store Supervisor (indirect) | Receives escalations when the system refuses to answer |
| Capstone Evaluator/Instructor | Assesses correctness, design quality, and evaluation rigor |
| Developer (project owner) | Builds and demonstrates the system in VS Code |

---

## 9. User Personas

**Persona 1 — "Priya," Store Admin**
Responsible for keeping operational documents current across store locations. Not a developer. Needs a simple upload-review-approve workflow and confidence that old documents are preserved, not lost, when replaced.

**Persona 2 — "Diego," Store Employee**
Works the sales floor; needs an answer in seconds on his phone/device, doesn't want to read a full policy document, and needs to trust that the answer reflects *today's* policy, with a way to know when to escalate to a supervisor instead of guessing.

---

## 10. Business Use Cases

| ID | Use Case |
|---|---|
| UC-01 | Admin uploads a new/updated policy document and the system supersedes the prior version |
| UC-02 | Employee asks about the current return policy and receives a cited, current answer |
| UC-03 | Employee asks what a policy was on a past date and receives the historically-effective version |
| UC-04 | Employee asks a question with insufficient evidence and receives a refusal directing them to a supervisor |
| UC-05 | Evaluator runs a golden dataset against the system to measure accuracy, refusal correctness, and latency |

---

## 11. Admin Business Journey

1. Admin receives an updated store-operations document (e.g., a revised return policy).
2. Admin uploads it to the system.
3. System validates and extracts text and proposed metadata (category, version, effective date).
4. Admin reviews and corrects metadata as needed, then approves.
5. System versions the document (marking the prior version superseded, not deleted), chunks it, embeds it, and stores it across the vector DB, SQLite, and file storage.
6. Knowledge base becomes queryable with the new content as "current" from its effective date forward.

---

## 12. Store Employee Business Journey

1. Employee has an operational question during a shift.
2. Employee types the question into the assistant.
3. System determines intent and which knowledge area (procedures/promotions/safety) applies.
4. System retrieves only currently-valid (or, if asked, historically-valid) evidence.
5. If evidence is sufficient, employee receives a streamed, cited answer with effective date and confidence.
6. If evidence is insufficient, employee receives a refusal and is directed to ask a supervisor.

---

## 13. Scope

### 13.1 In Scope
- Document upload, validation, text/metadata extraction, admin review, versioning
- Chunking, embedding, and indexing into a local vector DB
- Intent classification and sub-corpus routing (Procedures / Promotions / Safety / Unknown)
- Effective-date-aware retrieval (current vs. historical)
- Evidence-based answer generation with citation (document, section/clause, version, effective date, confidence)
- Refusal behavior when evidence is insufficient
- Streaming responses
- Conversation history within a session
- Basic feedback capture
- Evaluation framework with a golden dataset
- Local-only deployment via VS Code, using free-tier/open-source components

### 13.2 Out of Scope (MVP)
- Multi-tenant / multi-store-chain deployment
- Enterprise authentication/SSO
- GPU-based or paid cloud infrastructure
- Production-grade horizontal scaling / Kubernetes
- Real-time document collaboration or multi-admin concurrent editing workflows
- OCR of embedded images (Future Enhancement)
- Mobile native apps (a browser-accessible UI is sufficient)

---

## 14. Business Requirements

| ID | Requirement |
|---|---|
| BR-001 | The business shall have a way for an Admin to add new operational documents to a central knowledge base. |
| BR-002 | The business shall never lose historical versions of a document when it is updated. |
| BR-003 | The business shall ensure that questions about "current" policy are answered only from currently effective documents. |
| BR-004 | The business shall support answering questions about policy as of a specific past date. |
| BR-005 | The business shall ensure every answer given to an employee can be traced to a specific document, version, and effective date. |
| BR-006 | The business shall ensure the system does not fabricate answers when it lacks sufficient evidence, and instead refuses and directs the employee to a supervisor. |
| BR-007 | The business shall organize knowledge into distinct operational categories (Procedures, Promotions, Safety Rules) so questions are answered from the relevant category. |
| BR-008 | The business shall be able to measure system quality (accuracy, refusal correctness, latency) using a defined evaluation dataset. |
| BR-009 | The business shall be able to run and demonstrate the entire system locally without incurring paid infrastructure costs. |
| BR-010 | The business shall allow an Admin to correct extracted metadata before a document becomes part of the searchable knowledge base. |

---

## 15. Business Rules

| ID | Rule |
|---|---|
| BRULE-01 | A document is not searchable by employees until an Admin has reviewed and approved its metadata. |
| BRULE-02 | Superseded document versions are retained (never hard-deleted) and remain usable for historical questions, audits, and evaluation, but must never be used to answer "current" policy questions. |
| BRULE-03 | Every accepted answer must include: document name, section/clause, version, effective date, and a confidence/evidence score. |
| BRULE-04 | The system must refuse to answer rather than use unsupported world knowledge when retrieved evidence is insufficient. |
| BRULE-05 | Confidence must be derived from retrieval/evidence signals (relevance, coverage, date validity, source consistency) — not solely from the LLM's self-reported confidence. |
| BRULE-06 | A question must be routed to a sub-corpus (Procedures, Promotions, Safety, or Unknown) before retrieval is performed. |

---

## 16. Knowledge Base Requirements

The knowledge base shall be organized into three named sub-corpora (Procedures, Promotions, Safety Rules) plus an "Unknown" routing bucket for unclassifiable questions, shall track effective dates and versions at the document and chunk level, and shall be rebuildable/re-indexable from source documents stored in local file storage without data loss.

---

## 17. Document Versioning Requirements

Each new upload of a document that supersedes an existing one shall create a new version record linked to the prior version, mark the prior version as "superseded" (not deleted), and preserve the prior version's own effective-date range so historical queries can still resolve to it.

---

## 18. Effective-Date Requirements

Each document version shall carry an effective-from date (and effective-to date once superseded). Retrieval for "current" questions shall exclude any version whose effective-to date has passed or whose effective-from date is in the future. Retrieval for questions referencing a specific past date shall select the version whose effective-date range contains that date.

---

## 19. Grounded Answer Requirements

Answers shall be generated only from retrieved, evidence-backed chunks that passed effective-date filtering and evidence-evaluation; the LLM shall not supplement answers with unsupported general knowledge.

---

## 20. Refusal Requirements

When evidence evaluation determines that sufficient, relevant, currently-valid evidence cannot be found, the system shall return a refusal message explaining that insufficient evidence was found and suggesting the employee contact a supervisor, and shall log the refusal for evaluation.

---

## 21. Citation Requirements

Every non-refusal answer shall display: source document name, section/clause reference, document version, effective date, and a confidence/evidence score.

---

## 22. Performance Expectations

The system shall stream partial responses to reduce perceived latency, shall target a measurable time-to-first-token, and shall be evaluated at the p95 latency level rather than only on average latency, given real store-floor usage is time-sensitive.

---

## 23. Success Metrics / KPIs

| KPI | Target Approach |
|---|---|
| Answer accuracy | Measured against golden dataset expected answers |
| Refusal correctness | Measured against golden dataset unanswerable/ambiguous questions |
| Effective-date citation accuracy | Measured against golden dataset historical/current questions |
| Time to first token | Measured directly during evaluation runs |
| p95 latency | Measured directly during evaluation runs |
| Intent-routing accuracy | Measured against golden dataset labeled by sub-corpus |

Numeric target thresholds are **TBD** — to be set after an initial baseline evaluation run, since no target numbers are specified in the source prompt or diagram (marked as assumption, not invented as fact).

---

## 24. Assumptions

See consolidated list in Architecture Understanding §A.9 (ASM-01 through ASM-07). Additionally:
- ASM-08: The store operates in a single time zone/locale for effective-date comparisons (MVP scope).
- ASM-09: A single Admin role is sufficient for MVP (no multi-level admin permissions).

---

## 25. Dependencies

- Availability of a Groq free-tier API key, or a locally installed Ollama runtime, for LLM calls.
- Availability of a local embedding model (e.g., a Sentence-Transformers model) that can run on CPU.
- Source operational documents being made available by the business in PDF/DOCX/TXT/CSV form.

---

## 26. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Free-tier Groq API rate limits interrupt demos | Provider abstraction allows fallback to local Ollama LLM |
| Poor text extraction from complex PDFs (tables/scans) | Scope OCR/complex-layout handling as a Future Enhancement; flag low-confidence extractions for Admin review |
| Confidence thresholds mis-tuned, causing over- or under-refusal | Treat threshold as configurable and validate/tune against the golden dataset before demo |
| Effective-date logic bugs causing superseded content to answer "current" questions | Cover explicitly with dedicated golden-dataset test category (superseded-policy questions) |
| Local-only infra limits concurrency during demo | Acceptable for capstone scope; documented as an intentional constraint, not a defect |

---

## 27. Constraints

- Must run locally via VS Code on a normal developer machine (no GPU, no paid cloud).
- Must use only free-tier/open-source components (Groq free API, Ollama, ChromaDB/FAISS, SQLite, Sentence Transformers).
- Must support switching between Groq and a local LLM without changing application architecture (provider abstraction).
- Must not introduce unnecessary microservices/agents; components should have single, clear responsibilities.

---

## 28. Future Enhancements

- OCR / vision-based extraction of embedded images and scanned documents.
- Multi-store / multi-tenant deployment.
- Enterprise SSO / role-based access control beyond Admin/Employee.
- Cloud-hosted, horizontally-scaled deployment.
- Multi-turn long-term conversational memory across sessions.
- Automated re-evaluation pipeline triggered on every knowledge-base update.

---

## 29. High-Level Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-BR-01 | Given a superseded document version exists, when an employee asks a "current policy" question, then the system must not cite the superseded version. |
| AC-BR-02 | Given a question referencing a specific past date, when that date falls within a prior version's effective range, then the system must cite that version, not the current one. |
| AC-BR-03 | Given insufficient evidence for a question, when the employee submits it, then the system must return a refusal (not a fabricated answer) and log it. |
| AC-BR-04 | Given any accepted answer, when it is returned to the employee, then it must include document name, section/clause, version, effective date, and confidence score. |

---

## 30. BRD Traceability Matrix

| Business Requirement | Related Business Rule(s) | Related PRD Section |
|---|---|---|
| BR-001 | BRULE-01 | PRD §14–19 (Ingestion) |
| BR-002 | BRULE-02 | PRD §19 (Versioning) |
| BR-003 | BRULE-02, BRULE-06 | PRD §20, §26 (Effective-Date, Routing) |
| BR-004 | BRULE-02 | PRD §26 (Date-Aware Retrieval) |
| BR-005 | BRULE-03 | PRD §31 (Citation Generation) |
| BR-006 | BRULE-04, BRULE-05 | PRD §28–32 (Evidence, Confidence, Refusal) |
| BR-007 | BRULE-06 | PRD §24–25 (Intent, Routing) |
| BR-008 | — | PRD §52–54 (Evaluation Framework) |
| BR-009 | — | PRD §42–46 (LLM/Embedding/Vector DB/SQLite/File Storage Requirements) |
| BR-010 | BRULE-01 | PRD §18 (Admin Metadata Review) |

Full requirement-to-test-case traceability is provided in the PRD (§57).
