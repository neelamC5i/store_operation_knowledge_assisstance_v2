# PART D — MVP Feature List
## Store Operations Knowledge Assistant

Classification is based strictly on whether a feature is required to satisfy the attached architecture diagram and the capstone objectives in the prompt — not personal preference.

## MUST HAVE
(Directly drawn in the architecture diagram or explicitly mandated as business logic in the prompt.)

| Feature | Source |
|---|---|
| Document upload (PDF/DOCX/TXT/CSV) | Diagram step 1 |
| File validation (type/size/corruption) | Diagram step 2 |
| Text extraction | Diagram step 2 |
| Metadata extraction (category/type/version/effective date) | Diagram step 3 |
| Admin review & approval | Diagram step 4 |
| Version management / supersede handling | Diagram step 5; prompt Step 4 |
| Chunking with attached metadata | Diagram step 6 |
| Local embedding generation | Diagram step 7 |
| Vector DB + SQLite + File Storage | Diagram box 8 |
| Sub-corpus organization (Procedures/Promotions/Safety) | Diagram Knowledge Base box |
| Intent classification | Diagram step 7 (user flow) |
| Sub-corpus routing | Diagram step 8 (user flow) |
| Effective-date filtering (current vs historical) | Diagram step 9; prompt Step 4.1–4.3 |
| Hybrid semantic + keyword retrieval | Diagram step 10 |
| Evidence evaluation & confidence calculation | Diagram step 11; prompt Step 4.8 |
| Answer generation grounded in evidence | Diagram step 12; prompt Step 4.5 |
| Refusal when evidence insufficient | Diagram decision gate + refusal box; prompt Step 4.6 |
| Citation (doc, section, version, date, confidence) | Diagram step 14; prompt Step 4.7 |
| Streaming response | Diagram step 13 |
| Groq + local LLM provider abstraction | Prompt "LLM layer" requirement |
| Golden dataset + evaluation metrics | Diagram "Evaluation & Golden Dataset" box; prompt Step 7 |
| Conversation history (session-scoped) | Diagram "Conversation History & Feedback" box |

## SHOULD HAVE
(Supports the architecture but with some implementation latitude.)

| Feature |
|---|
| Feedback capture (helpful/unhelpful) |
| Document version-history admin screen |
| Configurable confidence threshold via config file |
| Structured logging of routing/evidence/outcome per query |

## NICE TO HAVE
(Improves quality/usability, not required to satisfy the diagram.)

| Feature |
|---|
| Table/basic layout-aware text extraction |
| Admin dashboard summarizing KB health (doc counts, superseded counts) |
| Simple keyword-highlighting in citations |

## FUTURE
(Explicitly deferred per BRD/PRD Future Enhancements; must not be built in MVP.)

| Feature |
|---|
| OCR / vision extraction of scanned or image-embedded content |
| Multi-store / multi-tenant deployment |
| Enterprise SSO / fine-grained RBAC |
| Cloud-hosted, horizontally scaled deployment |
| Long-term cross-session conversational memory |
| Automated re-evaluation pipeline triggered on every KB update |
