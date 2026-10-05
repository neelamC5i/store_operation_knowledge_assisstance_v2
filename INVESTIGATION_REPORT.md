# Document Upload & Retrieval Pipeline Investigation

## Current Situation
- Admin uploads document → saved as "Pending" status in the Knowledge Base UI
- When employee asks a question about that document, no response is generated from it
- The document appears in "Pending" state but never becomes "Active"

---

## Root Cause Analysis

### 1. **DOCUMENT UPLOAD FLOW (Original Implementation)**

The flow from original codebase (git 5d8dd47) was:

```
Step 1: Upload File → _process_upload()
  ├─ Save to temp file
  ├─ Validate file (validate_upload)
  ├─ Extract text (extraction.extract_text)
  ├─ Propose metadata (using Groq LLM)
  └─ Store in session state (pending_upload)

Step 2: Review Metadata → _render_review_form()
  ├─ Display extracted metadata for admin review
  ├─ Admin approves or rejects
  │
  └─ ON APPROVE:
     ├─ Create document in SQLite (documents_repo.create_document)
     ├─ Create pending version (documents_repo.create_pending_version)
     ├─ Save original file to disk (save_original)
     ├─ Store file path in DB (documents_repo.set_version_file_path)
     │
     └─ **CRITICAL STEP: Call pipeline.process_pending_version(version_id)**
        ├─ Extract text from saved file
        ├─ Split into chunks (chunking.chunk_sections)
        ├─ Embed chunks to vectors (embedding.embed_texts)
        ├─ Insert chunks into SQLite (documents_repo.insert_chunk)
        ├─ Add embeddings to Vector DB (vector_store.add_chunks)
        └─ **FLIP STATUS: 'pending' → 'active'** ← KEY STEP
```

### 2. **DOCUMENT RETRIEVAL FLOW**

When employee asks a question:

```
Employee Question → retrieve_evidence()
  ├─ Classify question intent
  ├─ Route by category (subcorpus_router.route)
  ├─ Filter eligible versions → documents_repo.list_eligible_version_ids()
  │  
  │  **KEY SQL QUERY:**
  │  SELECT dv.id FROM document_versions dv
  │  WHERE dv.status = 'active'  ← ← ← ONLY active versions!
  │
  ├─ Hybrid search across chunks (hybrid_search.retrieve)
  └─ Return relevant chunks with citations
```

---

## Why Pending Documents Can't Be Retrieved

### The Retrieval Filter (app/storage/documents_repo.py - list_eligible_version_ids)

```sql
-- For current questions (as_of = None):
SELECT dv.id FROM document_versions dv
JOIN documents d ON dv.document_id = d.id
WHERE d.category IN (...) 
  AND dv.status = 'active'    ← ← ← ONLY active versions!
```

**Result:** Pending documents are intentionally excluded from retrieval because:
- They don't have chunks indexed yet
- They don't have vectors in the vector database
- Status filtering ensures consistency between SQLite and Chroma

---

## Why Current Admin UI Shows "Pending" But Never Becomes "Active"

### The Problem: Current Admin UI is a Mock/Dummy Implementation

The current `app/ui/admin_view.py` (created during recent UI refactor) is a **UI-only mockup** that:

❌ Does NOT save files to disk  
❌ Does NOT create documents in SQLite  
❌ Does NOT create versions in SQLite  
❌ Does NOT call `pipeline.process_pending_version()`  
✅ Only stores dummy data in `st.session_state.admin_documents` (session-only in-memory)

**Code snippet (admin_view.py lines 167-183):**
```python
if submitted:
    if not uploaded_file or not title.strip():
        st.error("Please choose a file...")
    else:
        suffix = uploaded_file.name.rsplit(".", 1)[-1].upper()
        st.session_state.admin_documents.insert(0, {
            "title": title.strip(),
            "type": suffix,
            "category": category,
            "version": "v1.0",
            "uploaded_on": datetime.now().strftime("%b %d, %Y %I:%M %p"),
            "status": "Pending",  # ← Just adds to session dict
        })
        st.success(f"'{title.strip()}' uploaded...")
```

### What This Means:

Session-only data that:
- ❌ Never reaches the database
- ❌ Never triggers the ingestion pipeline
- ❌ Never calls `process_pending_version()`
- ❌ Never flips status from pending → active
- ❌ Disappears when the page refreshes (session ends)
- ❌ Never gets chunks indexed
- ❌ Never gets embeddings computed and stored in vector DB

---

## The Complete Chunking, Embedding, Retrieval, Storage Pipeline

### When `pipeline.process_pending_version(version_id)` is called:

```
process_pending_version(version_id)
│
├─ VALIDATION
│  └─ Get version from SQLite
│  └─ Verify status = 'pending'
│  └─ Verify file_path exists
│
├─ STATUS UPDATE
│  └─ Change status: pending → processing
│
├─ EXTRACTION PHASE (app/ingestion/extraction.py)
│  └─ extraction.extract_text(file_path)
│     ├─ For PDF: uses PyMuPDF (pymupdf library)
│     ├─ For DOCX: uses python-docx library
│     ├─ For TXT: plain text read
│     └─ Returns extracted text + page/section info
│
├─ CHUNKING PHASE (app/ingestion/chunking.py)
│  └─ chunking.chunk_sections(extracted)
│     ├─ Splits text into logical sections
│     ├─ Chunks approximately 256 tokens per chunk
│     ├─ Preserves section/page metadata
│     └─ Returns list[Chunk{chunk_text, page, section}]
│
├─ EMBEDDING PHASE (app/ingestion/embedding.py)
│  └─ embedding.embed_texts(texts)
│     ├─ Uses SentenceTransformers (model: all-MiniLM-L6-v2)
│     ├─ Generates 384-dimensional embeddings for each chunk
│     └─ Returns list[list[float]] (384-dim vectors)
│
├─ STORAGE PHASE - SQLite (app/storage/documents_repo.py)
│  └─ For each chunk:
│     ├─ documents_repo.insert_chunk(
│         document_version_id, section, page, chunk_text
│       )
│     └─ documents_repo.set_chunk_embedding_ref(chunk_id, vector_id)
│
├─ STORAGE PHASE - Vector DB (app/storage/vector_store.py)
│  └─ vector_store.add_chunks(
│       ids=["chunk-123", "chunk-124", ...],
│       embeddings=[vec1, vec2, ...],    # 384-dim vectors
│       documents=[text1, text2, ...],   # original chunk texts
│       metadatas=[{doc_id, title, version, ...}, ...]
│     )
│     ├─ Adds vectors to Chroma vector database
│     ├─ Stores alongside metadata for filtering
│     └─ Enables semantic similarity search
│
└─ ACTIVATION PHASE (app/storage/documents_repo.py)
   ├─ documents_repo.activate_version(document_id, version_id, effective_from)
   ├─ Changes status: processing → active
   ├─ Marks any prior active version as superseded
   └─ Document is now searchable!
```

### On Retrieval (when employee asks question):

```
retrieve_evidence(question, provider, override_date=None)
│
├─ INTENT CLASSIFICATION (app/retrieval/intent_router.py)
│  └─ intent_router.classify(question, provider)
│     ├─ Uses Groq LLM to detect:
│     │  ├─ Question category (Procedures/Promotions/Safety)
│     │  └─ Date reference (if any)
│     └─ Returns IntentResult{category, detected_date}
│
├─ SUBCORPUS ROUTING (app/retrieval/subcorpus_router.py)
│  └─ subcorpus_router.route(intent)
│     ├─ Maps category to document categories
│     └─ Returns list of relevant categories
│
├─ VERSIONING FILTER (app/retrieval/date_filter.py)
│  └─ documents_repo.list_eligible_version_ids(categories, date)
│     │
│     ├─ For current questions (date=None):
│     │  └─ SELECT version_ids WHERE status='active'
│     │     ← Pending documents EXCLUDED here!
│     │
│     └─ Returns list of version_ids eligible for search
│
└─ SEMANTIC SEARCH (app/retrieval/hybrid_search.py)
   └─ hybrid_search.retrieve(question, eligible_version_ids)
      ├─ Embed question using same model (all-MiniLM-L6-v2)
      ├─ Query Chroma with question embedding
      ├─ Filter results to only eligible version_ids
      ├─ Combine vector similarity + BM25 scoring
      └─ Return top-K chunks with citations

Final: Response generation sees only chunks from 'active' versions
```

---

## Summary Table

| Aspect | Current (Mock) UI | Original (Real) Implementation |
|--------|---------|---------|
| **File Storage** | Session-only (lost on refresh) | Saved to disk permanently |
| **Database Write** | Never writes to SQLite | Creates document + version rows |
| **Pipeline Trigger** | ❌ Never called | ✅ Called after admin approval |
| **Chunking** | ❌ Not done | ✅ Splits document into chunks |
| **Embedding** | ❌ Not done | ✅ Generates 384-dim vectors |
| **Vector DB** | ❌ Empty | ✅ Populated with embeddings |
| **Status Flow** | Pending (stuck) | Pending → Processing → Active |
| **Retrieval Access** | ❌ Can't find (not in DB) | ✅ Found via status='active' filter |
| **Questions Work?** | ❌ No (no chunks to retrieve) | ✅ Yes (chunks in DB + vectors in Chroma) |

---

## Key Insights

### Insight #1: Retrieval System Works Correctly
The retrieval filtering is **not broken** — it's working as designed:
- ✅ Correctly filters for status='active' versions only
- ✅ Correctly queries Chroma vector database
- ✅ Correctly returns relevant chunks

### Insight #2: The Bottleneck is Upstream
Documents never reach "Active" status because:
- Current mock admin UI **never triggers `pipeline.process_pending_version()`**
- Without this pipeline call:
  - ❌ No chunks are created
  - ❌ No embeddings are computed
  - ❌ No vectors are stored in Chroma
  - ❌ Status never flips from pending → active
  - ❌ Retrieval filtering excludes them

### Insight #3: The Pipeline is Sound
When `process_pending_version()` IS called (in original implementation):
- ✅ Extracts text reliably (uses PyMuPDF, python-docx, etc.)
- ✅ Chunks text logically (preserves sections)
- ✅ Embeds chunks consistently (384-dim vectors)
- ✅ Stores in both SQLite AND Chroma (dual consistency)
- ✅ Only flips status to active after BOTH succeed

---

## Conclusion

**Why pending documents can't be retrieved:**

1. Current admin_view.py is a mock UI that doesn't call the real backend
2. Documents are never sent through `pipeline.process_pending_version()`
3. Without the pipeline, documents stay in "Pending" state in session memory (lost on refresh)
4. The retrieval system correctly filters for `status='active'` only
5. Pending documents are invisible to retrieval by design (they have no chunks/vectors anyway)

**To fix this:** Restore the original admin_view.py implementation which:
- Validates files
- Extracts metadata
- Shows approval form
- **Calls `pipeline.process_pending_version()` on approval**
- Flips status to active
- Document then appears in retrieval results
