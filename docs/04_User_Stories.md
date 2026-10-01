# User Stories & Acceptance Criteria
## Store Operations Knowledge Assistant

---

## Store Admin Stories

**US-001 — Upload a document**
As a Store Admin, I want to upload a policy document, so that it can become part of the knowledge base.

Acceptance Criteria (AC-001):
- Given a valid PDF/DOCX/TXT/CSV file, When the Admin uploads it, Then the file is accepted and moves to processing.
- Given an unsupported file type, When the Admin uploads it, Then the system rejects it with a clear message.
- Given a corrupted or empty file, When the Admin uploads it, Then the system rejects it before extraction.

**US-002 — Review and approve extracted metadata**
As a Store Admin, I want to review and edit extracted metadata before approving a document, so that only accurate information enters the knowledge base.

Acceptance Criteria (AC-002):
- Given a processed upload, When the Admin opens the review screen, Then extracted category/type/version/effective date/description are shown.
- Given incorrect metadata, When the Admin edits a field, Then the corrected value is saved.
- Given reviewed metadata, When the Admin approves, Then the document proceeds to versioning/chunking/embedding; When the Admin rejects, Then the document is discarded and not indexed.

**US-003 — Version and supersede documents**
As a Store Admin, I want the system to version a document instead of overwriting it, so that historical versions are preserved.

Acceptance Criteria (AC-003):
- Given an existing "Return Policy" document, When a newer version is approved, Then the prior version's status becomes "Superseded" and its effective-to date is set.
- Given a superseded version, When queried directly for audit/history, Then it remains retrievable.
- Given a superseded version, When a "current policy" question is asked, Then it is excluded from the answer.

**US-004 (Admin-adjacent) — Maintain sub-corpus organization**
As a Store Admin, I want documents automatically categorized into Procedures/Promotions/Safety, so that employee questions route correctly.

Acceptance Criteria (AC-004):
- Given an approved document, When categorization is ambiguous, Then it is flagged for Admin confirmation rather than silently defaulting.

---

## Store Employee Stories

**US-005 — Ask a current-policy question**
As a Store Employee, I want to ask what the current return policy is, so that I can act correctly without waiting for a supervisor.

Acceptance Criteria (AC-005):
- Given a currently effective "Return Policy" version exists, When I ask "What is the current return policy?", Then the answer cites that version's document, section, version, and effective date.
- Given a superseded version also exists, When I ask the same question, Then the superseded version is never cited as the answer.

**US-006 — Ask a historical-policy question**
As a Store Employee, I want to ask what a policy was on a specific past date, so that I can resolve a dispute about a past transaction.

Acceptance Criteria (AC-006):
- Given a date is mentioned in my question, When the date falls within a specific version's effective range, Then that version is retrieved and cited, not the current version.

**US-007 — Receive a refusal when evidence is insufficient**
As a Store Employee, I want the system to tell me when it doesn't know, rather than guess, so that I don't act on wrong information.

Acceptance Criteria (AC-007):
- Given no sufficient evidence is retrieved, When I submit my question, Then I receive a refusal message suggesting I contact a supervisor.
- Given a refusal occurs, When it is returned, Then it is logged with the question and evidence signals for evaluation.

**US-008 — See a cited answer**
As a Store Employee, I want every answer to show its source and how confident the system is, so that I can judge whether to trust it.

Acceptance Criteria (AC-008):
- Given a sufficient-evidence answer, When it is displayed, Then it includes document name, section/clause, version, effective date, and confidence score.

**US-009 — See the answer stream in**
As a Store Employee, I want the answer to start appearing quickly, so that I'm not left waiting on a busy sales floor.

Acceptance Criteria (AC-009):
- Given a question with sufficient evidence, When the answer is generated, Then tokens are streamed to the UI rather than delivered only at completion.

**US-010 (Evaluator) — Run the golden dataset**
As a capstone evaluator, I want to run a predefined set of golden questions against the system, so that I can measure accuracy, refusal correctness, and latency.

Acceptance Criteria (AC-010):
- Given the golden dataset (9 categories per PRD §53), When it is executed against the system, Then per-category and overall metrics (accuracy, refusal correctness, effective-date citation accuracy, TTFT, p95 latency) are produced and stored as an EvaluationRun.

**US-011 (Developer) — Swap LLM providers without code changes**
As the developer, I want to switch between Groq and a local Ollama model via configuration, so that the demo is resilient to API rate limits.

Acceptance Criteria (AC-011):
- Given the provider is set to "groq" in configuration, When the app runs, Then Groq is used for intent classification, metadata extraction, and answer generation.
- Given the provider is changed to "ollama" in configuration only, When the app is restarted, Then the same features work unchanged using the local model.

---

## Additional Supporting Stories (MVP completeness)

**US-012** — As a Store Employee, I want to give feedback (helpful/unhelpful) on an answer, so that answer quality can be improved over time. (AC-012: feedback is stored linked to the message.)

**US-013** — As a Store Employee, I want to ask a follow-up question in the same session, so that I don't have to repeat context. (AC-013: prior turns in the session are available to the intent/answer components.)

**US-014** — As a Store Admin, I want to see version history for a document, so that I can audit what changed and when. (AC-014: version history screen lists all versions with status and effective dates.)
