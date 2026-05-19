# Pitfalls Research

**Domain:** Multi-tenant clinical nutrition SaaS — Django + DRF + pgvector + LangChain + Celery
**Researched:** 2026-05-19
**Confidence:** HIGH (stack-specific; verified against official Celery, LangChain, pgvector, and DRF documentation)

---

## Critical Pitfalls

### Pitfall 1: pgvector Retrieval Without Tenant Filter — Silent Cross-Tenant Data Leakage

**What goes wrong:**
`similarity_search()` on a shared pgvector table returns the globally closest vectors — not just the vectors belonging to the querying patient's nutritionist. A patient (or a misbehaving API caller) receives chunks from another nutritionist's documents. There is no error, no exception, and no log entry. The leak is invisible unless explicitly tested.

**Why it happens:**
LangChain's `PGVector` / `PGVectorStore` similarity search does not enforce any tenant boundary by default. Developers embed `nutritionist_id` in document metadata but forget to pass `filter={"nutritionist_id": str(nutritionist.id)}` at query time. The metadata is stored correctly but never applied as a WHERE clause during retrieval.

**How to avoid:**
- Always pass the tenant filter explicitly on every `similarity_search` call:
  ```python
  vector_store.similarity_search(
      query,
      k=5,
      filter={"nutritionist_id": str(request.user.perfil_nutricionista.id)}
  )
  ```
- Wrap the vector store in a `ScopedRetriever` class that injects the tenant filter automatically — never call the raw vector store from views or chat handlers:
  ```python
  class ScopedRetriever:
      def __init__(self, store, nutritionist_id):
          self._store = store
          self._filter = {"nutritionist_id": str(nutritionist_id)}
      def get_relevant_documents(self, query, k=5):
          return self._store.similarity_search(query, k=k, filter=self._filter)
  ```
- Add a pgvector-level partial index or row-level security policy as a defense-in-depth backstop (optional but recommended).
- Write an integration test that inserts documents for two different nutritionists, authenticates as one, and asserts that retrieved chunks never include the other's content.

**Warning signs:**
- No filter being passed to `similarity_search` anywhere in the codebase
- Vector store initialized once globally and reused across requests without re-scoping
- Tests that only use a single nutritionist's data

**Phase to address:** RAG pipeline implementation (Phase 4 / knowledge base + retrieval phase). Must be locked before any chat endpoint goes live.

---

### Pitfall 2: Celery Task Fired Before Database Transaction Commits

**What goes wrong:**
A document upload view creates a `Document` record inside a `transaction.atomic()` block (or Django's implicit per-request transaction) and immediately calls `process_document.delay(document_id)`. The Celery worker picks up the task, does `Document.objects.get(pk=document_id)`, and raises `DoesNotExist` because the transaction has not committed yet. The task fails, goes to FAILURE state, and the document is never indexed.

**Why it happens:**
`task.delay()` puts the message on Redis immediately — it does not wait for the current database transaction to commit. This is a classic Django + Celery timing bug. It is especially common in greenfield projects where developers do not yet know about `transaction.on_commit`.

**How to avoid:**
Use `delay_on_commit()` (Celery 5.4+) or the explicit `transaction.on_commit` pattern:
```python
# Celery 5.4+ shortcut (preferred)
transaction.on_commit(lambda: process_document.delay_on_commit(document.pk))

# Or explicit (works on any Celery version)
from django.db import transaction
transaction.on_commit(lambda: process_document.delay(str(document.id)))
```
Never call `.delay()` directly inside a view that creates the object being processed.

**Warning signs:**
- `DoesNotExist` errors appearing in Celery task logs immediately after the task starts
- Pattern `obj = Model.objects.create(...); task.delay(obj.pk)` without `on_commit`
- Task failures that disappear when the view is called a second time (race condition)

**Phase to address:** Async document ingestion phase (Phase 5 / Celery integration). Must be in the initial task implementation, not retrofitted.

---

### Pitfall 3: DRF Queryset Scoping Applied in `list()` but Not in `retrieve()`, `update()`, `destroy()`

**What goes wrong:**
The nutritionist's patient list endpoint is properly filtered (`queryset = Patient.objects.filter(nutritionist=request.user)`), but the detail endpoint uses `get_object_or_404(Patient, pk=pk)` or does `Patient.objects.get(pk=pk)` directly. A nutritionist who guesses another patient's UUID can retrieve, edit, or delete a patient they do not own. No permission error is raised.

**Why it happens:**
Developers scope the `list` view but overlook that DRF's `get_object()` by default uses the view's `queryset` attribute for lookups — only safe if the queryset is already scoped. When developers write custom `retrieve()`, `update()`, or `destroy()` methods and call the ORM directly, they bypass the scoped queryset.

**How to avoid:**
- Always scope at the `get_queryset()` level, not at the queryset attribute level, and never bypass it in action methods:
  ```python
  class PatientViewSet(viewsets.ModelViewSet):
      def get_queryset(self):
          return Patient.objects.filter(nutritionist=self.request.user)
  ```
- Never call `Patient.objects.get(pk=...)` inside a ViewSet action — always use `self.get_object()` which applies the scoped queryset and calls `check_object_permissions`.
- Add an object-level permission check as defense-in-depth:
  ```python
  class IsOwnedByNutritionist(permissions.BasePermission):
      def has_object_permission(self, request, view, obj):
          return obj.nutritionist == request.user
  ```
- Write explicit tests: authenticate as Nutritionist A, attempt to `GET /api/patients/<nutritionist_B_patient_uuid>/`, assert 404 (not 403 — 404 leaks less information about existence).

**Warning signs:**
- `Patient.objects.get(pk=pk)` appearing in any ViewSet method
- `get_object_or_404(Patient, pk=pk)` without additional `nutritionist=request.user` kwarg
- Tests that do not attempt cross-tenant access at the detail endpoint level

**Phase to address:** Patient management phase (Phase 2). Must be verified with cross-tenant test coverage before any other feature is built on top.

---

### Pitfall 4: Storing LLM Objects or Django ORM Objects Inside Celery Tasks

**What goes wrong:**
A Celery task is passed a `Document` model instance (or a LangChain `LLMChain` object) as an argument instead of a primitive ID. Celery serializes the argument with pickle (or JSON), the serialization fails or produces a stale object, and the task either crashes or operates on out-of-date data.

**Why it happens:**
Developers pass the model instance directly for convenience: `process_document.delay(document_obj)`. Django ORM objects are not safely serializable across process boundaries. LangChain objects (chains, retrievers, LLMs) hold open connections and are not serializable at all.

**How to avoid:**
Pass only primitive IDs and re-fetch inside the task:
```python
# WRONG
process_document.delay(document_instance)

# CORRECT
process_document.delay(str(document.id))

# Inside the task
@shared_task(bind=True, max_retries=3)
def process_document(self, document_id: str):
    document = Document.objects.get(pk=document_id)
    # Instantiate LangChain objects fresh inside the task
    embeddings = OpenAIEmbeddings()
    ...
```
Instantiate LangChain components (embeddings, text splitters, LLM clients) inside the task function, not at module level or passed as arguments.

**Warning signs:**
- `process_document.delay(doc)` with a model instance argument
- `PicklingError` or `SerializationError` in Celery logs
- Module-level LangChain client instantiation in `tasks.py`

**Phase to address:** Async document ingestion phase (Phase 5). Set this pattern at task creation time.

---

### Pitfall 5: Embedding Dimension Mismatch Between Indexing and Retrieval

**What goes wrong:**
Documents are indexed with one embedding model (e.g., `text-embedding-ada-002`, 1536 dimensions), then the environment variable is changed to a different model (e.g., `text-embedding-3-small`, also 1536 but different vector space, or a Hugging Face model with 768 dimensions). Retrieval silently returns semantically wrong results or pgvector raises a dimension mismatch error. All previously indexed documents become garbage.

**Why it happens:**
The pgvector column dimension is set at migration time and is immutable without dropping and recreating the column. Developers switch embedding models during development without realizing they need to re-index all documents.

**How to avoid:**
- Pin the embedding model name and dimension in a Django setting constant (not just `.env`), and write a startup check that validates the configured model matches the stored column dimension.
- Record the embedding model name in document metadata at ingestion time:
  ```python
  metadata={"nutritionist_id": ..., "embedding_model": "text-embedding-ada-002"}
  ```
- Any change to the embedding model requires a data migration: create a new column with the new dimension, re-embed all documents, then cut over. Never hot-swap the model in `.env` on a live database.
- The `LangchainPGVector` integration creates its own table with the dimension baked into the schema — verify this matches before going to production.

**Warning signs:**
- `LLM_PROVIDER` or embedding model name in `.env` only (no hard assertion in code)
- No check that verifies existing indexed documents match current model
- Changing `.env` values between development sessions without a re-index step

**Phase to address:** RAG pipeline setup (Phase 3 / vector store initialization). Must be decided and locked before first document is indexed.

---

### Pitfall 6: Scope Guardrail Implemented as a Post-Hoc String Filter

**What goes wrong:**
The assistant's scope restriction (nutrition-only) is implemented by checking if the LLM's response contains certain keywords, or by checking the user's input against a keyword blocklist. The LLM can still reason about out-of-scope topics (medical prescriptions, legal advice, psychological counseling) and return an answer — the filter then strips it and returns the generic deflection message. This means: (a) tokens are wasted on the out-of-scope response, (b) partial out-of-scope content may slip through, and (c) the filter is brittle against rephrased prompts.

**Why it happens:**
Post-filtering is simple to implement. Developers add it as an afterthought. Pre-filtering (classifying the intent before invoking the RAG chain) requires more upfront design.

**How to avoid:**
Implement scope restriction as a pre-retrieval intent classifier, not a post-generation filter:
```python
SCOPE_SYSTEM_PROMPT = """You are a scope classifier. The user message is in scope if it
is about: nutrition, food substitutions, dietary plans, macros, food preparation, hydration,
or supplementation. Out of scope: medical diagnosis, medication, psychological support,
legal matters, anything unrelated to nutrition.
Respond with ONLY 'IN_SCOPE' or 'OUT_OF_SCOPE'."""

def classify_scope(user_message: str, llm) -> bool:
    result = llm.invoke([
        {"role": "system", "content": SCOPE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ])
    return result.content.strip() == "IN_SCOPE"
```
If `OUT_OF_SCOPE`, return the deflection message immediately without calling the RAG chain. This saves tokens and prevents any partial leakage.

**Warning signs:**
- Scope logic applied to the LLM's output rather than the user's input
- Scope check implemented as `if any(kw in response for kw in banned_keywords)`
- No test cases for rephrased out-of-scope queries (e.g., "what medication should I take with my diet plan?")

**Phase to address:** Chat assistant phase (Phase 6). Must be built into the pipeline entry point, not the output stage.

---

### Pitfall 7: CPF Exposed in Logs, Error Messages, or Serializer `repr()`

**What goes wrong:**
LGPD Art. 11 classifies health data and personal identifiers (CPF) as sensitive. Despite using UUID as the primary key, CPF appears in: Django's default error logging (which logs request data), DRF's browsable API debug output, exception tracebacks (`repr(patient)` includes CPF), and Celery task argument logs if a patient object is serialized. A production log dump becomes a LGPD compliance incident.

**Why it happens:**
Django and DRF log request bodies and serializer data in DEBUG mode by default. Developers replicate this behavior to production. The `__str__` or `__repr__` of the `Patient` model includes CPF for readability during development.

**How to avoid:**
- Set `DEBUG=False` in production and never log request bodies.
- Override `__repr__` and `__str__` on `PerfilPaciente` to use UUID only:
  ```python
  def __repr__(self):
      return f"<PerfilPaciente id={self.id}>"
  ```
- Use a custom log filter that scrubs CPF-pattern strings from all log records before emission:
  ```python
  import re
  class ScrubCPFFilter(logging.Filter):
      CPF_PATTERN = re.compile(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}')
      def filter(self, record):
          record.msg = self.CPF_PATTERN.sub('[CPF_REDACTED]', str(record.msg))
          return True
  ```
- Exclude `cpf` from all DRF serializer `list_serializer_fields` and ensure it is write-only in registration serializers (`write_only=True`).
- Assert in CI that no URL route contains a CPF-shaped segment.

**Warning signs:**
- `cpf` field appears in any serializer without `write_only=True`
- `str(patient)` or `repr(patient)` includes CPF in development
- No log scrubbing filter configured
- `LOGGING` configuration uses `DEBUG` level in production settings

**Phase to address:** Authentication and accounts phase (Phase 1). CPF handling must be correct from the first model definition; retrofitting is fragile.

---

### Pitfall 8: HNSW Index Not Created — Sequential Scan on Embedding Table

**What goes wrong:**
The `LangchainEmbedding` table accumulates thousands of vectors. Every `similarity_search()` performs a sequential scan (exact nearest-neighbor search) across all rows. At 10,000+ vectors, query latency spikes to seconds. The system appears to work correctly in development with 50 test documents but degrades catastrophically in production.

**Why it happens:**
LangChain's `PGVector` integration creates the table and column but does NOT create an HNSW or IVFFlat index automatically. Developers assume the vector store handles indexing. pgvector does exact search by default (no index required for correctness, only for performance).

**How to avoid:**
Create the HNSW index in a Django migration after the LangChain table creation step:
```sql
CREATE INDEX ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
Also add a B-tree index on the metadata column used for tenant filtering so the `WHERE` clause does not full-scan before the ANN search:
```sql
CREATE INDEX ON langchain_pg_embedding ((cmetadata->>'nutritionist_id'));
```
For tenant-filtered queries with few matching rows, also set `hnsw.iterative_scan = strict_order` to improve recall.

**Warning signs:**
- No HNSW/IVFFlat index visible in `\d langchain_pg_embedding` or `pg_indexes`
- `EXPLAIN ANALYZE` shows `Seq Scan` on the embedding table
- Similarity search latency measured only in dev with <100 documents

**Phase to address:** RAG pipeline setup (Phase 3 / vector store initialization). Create the index in the same migration that creates the table.

---

### Pitfall 9: Conversation History Grows Without Bound — Context Window Overflow

**What goes wrong:**
The chat endpoint passes the full conversation history to the LLM on every turn. After 30–50 messages, the context window is exceeded. Claude 3.x raises a `BadRequestError: context_length_exceeded`. The conversation becomes permanently broken for that patient — every subsequent message also overflows.

**Why it happens:**
Developers store messages in the database (correctly) but retrieve all of them without pagination or trimming. `ConversationHistory.objects.filter(patient=patient).order_by('created_at')` returns every message ever. Passing all to the LLM works for short conversations in testing.

**How to avoid:**
Apply LangChain's `trim_messages` utility with a token budget, keeping only the most recent messages within a safe limit:
```python
from langchain_core.messages.utils import trim_messages, count_tokens_approximately

messages = trim_messages(
    all_messages,
    strategy="last",
    token_counter=count_tokens_approximately,
    max_tokens=4096,  # leave room for system prompt + RAG context
    start_on="human",
    include_system=True,
)
```
Reserve tokens for: system prompt (~500), RAG context chunks (~2000), conversation history (~4096), response headroom (~1000). Set `max_tokens` accordingly for the chosen model's context window.

**Warning signs:**
- No `trim_messages` or message count limit before LLM invocation
- `ConversationHistory.objects.filter(patient=patient)` without `.order_by('-created_at')[:N]` limit
- No test with a conversation longer than 20 messages

**Phase to address:** Chat assistant phase (Phase 6). Build trimming into the message preparation step before the first production conversation.

---

### Pitfall 10: Celery Task Idempotency — Duplicate Document Indexing

**What goes wrong:**
A document upload triggers a Celery task. The worker crashes mid-processing (e.g., OOM, network error to OpenAI Embeddings API). Celery retries the task. The task re-embeds all chunks and calls `vectorstore.add_documents()` again, creating duplicate vectors. Retrieval now returns the same content twice, inflating results and degrading answer quality. With `max_retries=3`, a single document may be indexed 3–4 times.

**Why it happens:**
`vectorstore.add_documents()` appends — it does not upsert. Retried tasks re-run the full ingestion pipeline without checking whether embeddings already exist for this document. Developers focus on making the happy path work and do not design for partial failure.

**How to avoid:**
Track indexing state on the `Document` model with a status field (`pending` / `processing` / `indexed` / `failed`). Before adding chunks to the vector store, check if any chunk with this `document_id` already exists in the metadata:
```python
# Use document_id in metadata to detect duplicates
existing = vectorstore.similarity_search(
    "", k=1, filter={"document_id": str(document.id)}
)
if existing:
    return  # already indexed, skip
```
Or delete existing chunks for this document before re-adding (safer upsert pattern):
```python
# Delete stale chunks, then re-add
vectorstore.delete(filter={"document_id": str(document.id)})
vectorstore.add_documents(chunks)
```
Use `transition_to_processing = Document.objects.filter(pk=pk, status='pending').update(status='processing')` as a compare-and-swap to prevent two workers from processing the same document simultaneously.

**Warning signs:**
- No `status` field on the Document model
- Task has `autoretry_for=(Exception,)` without idempotency guard
- `vectorstore.add_documents()` called without checking for existing entries
- Retrieval returns duplicate chunks for the same content

**Phase to address:** Async document ingestion phase (Phase 5). Must be designed into the task from day one, not patched after observing duplicates.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Global `PGVector` instance in `settings.py` | Easy setup | Not re-scoped per request; tenant filter must always be passed manually; connection leak risk | Never — always wrap in a factory or `ScopedRetriever` |
| Hardcoding `Patient.objects.filter(nutritionist=request.user)` inline in every view | Simple, explicit | One missed call = data leak; no single point to audit | Never — centralize in `get_queryset()` on ViewSet |
| Skipping HNSW index creation until "we have real data" | Faster initial setup | Exact scan silently degrades; adding the index later requires a lock on the table | MVP is acceptable if data volume is <1000 vectors and you commit to adding it before beta |
| Using `autoretry_for=(Exception,)` on ingestion tasks | Less boilerplate | Retries on non-recoverable errors (invalid PDF, wrong API key); burns API credits; may duplicate indexing | Never for LLM API calls; acceptable only for transient network errors with specific exception types |
| Passing all conversation history to LLM | Simpler code | Context overflow on long conversations; cost scales linearly with history length | Acceptable for Phase 1 smoke testing with 3-message conversations only |
| `write_only=False` on CPF field in serializers | Easier debugging | LGPD violation; CPF appears in API responses and logs | Never — CPF must always be `write_only=True` |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LangChain `PGVector.from_documents()` | Calling this in a view or task without passing `connection_string` per invocation — causes shared connection state across requests | Always instantiate `PGVector` with an explicit connection string; never store as a module-level singleton |
| LangChain `PGVector` + metadata filter | Using `filter={"nutritionist_id": nutritionist_id}` where `nutritionist_id` is an integer — pgvector stores metadata as JSONB, integer comparison may fail | Always cast to `str`: `filter={"nutritionist_id": str(nutritionist.id)}` |
| Celery + Django ORM | Calling ORM queries at module import time in `tasks.py` (e.g., to load settings) — fails on worker startup before Django is fully initialized | All ORM access must be inside the task function body, never at module level |
| OpenAI Embeddings API | Not handling `RateLimitError` or `APITimeoutError` in the Celery task — task goes to FAILURE with no retry | Use `autoretry_for=(openai.RateLimitError, openai.APITimeoutError)` with exponential backoff |
| pgvector HNSW index + tenant filter | HNSW index scan with a `WHERE` clause on metadata may miss results if `ef_search` is too low — retrieval appears to work but has poor recall | Set `hnsw.iterative_scan = strict_order` for filtered queries, or add a partial index per nutritionist |
| SimpleJWT token blacklist | Not running `python manage.py migrate` after adding `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS` — refresh token rotation silently fails or raises DB errors | Include token blacklist migration in the accounts phase migration sequence |
| LangChain + Anthropic (Claude) | Using `langchain_anthropic.ChatAnthropic` with `streaming=True` in a synchronous Django view — blocks the response until full completion | Use async views (`async def`) or disable streaming for the MVP synchronous API |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential scan on embedding table (no HNSW index) | Similarity search latency >500ms; `EXPLAIN ANALYZE` shows `Seq Scan` | Create HNSW index in migration | ~5,000 vectors (~50 documents at typical chunk sizes) |
| Unbounded conversation history in LLM context | `context_length_exceeded` errors; cost spikes; slow responses | `trim_messages` with token budget | ~30 messages for Claude Sonnet (200k window but each RAG context also consumes tokens) |
| N+1 ORM query in patient list with related profiles | Patient list endpoint slow as patient count grows | `select_related('perfil_paciente')` on queryset | ~500 patients |
| Re-embedding entire document on every retry | OpenAI API cost multiplied by retry count; slow task queue | Idempotency guard before `add_documents()` | First production document with a network error during embedding |
| Synchronous embedding call inside the API request cycle | API response time includes full embedding latency (200–2000ms) | Always embed asynchronously via Celery; never in the API view | Single user with slow network to OpenAI |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| 200 response on cross-tenant patient access instead of 404 | Confirms UUID existence to attacker; enables enumeration | Return 404 (not 403) for cross-tenant access — existence itself is sensitive data |
| JWT access token TTL set to 24h or longer | Stolen token valid for a full day; no revocation possible for access tokens | Keep access token at 5 minutes (as specified); refresh token at 1 day with rotation + blacklist |
| CPF stored in plaintext in `Patient.cpf` without field-level encryption | Database dump exposes all CPF values | Encrypt at-rest using `django-encrypted-fields` or store hashed CPF with `bcrypt` for uniqueness checks |
| Patient health data (conditions, restrictions) returned in error responses | Condition data leaks in 4xx/5xx error bodies | Custom DRF exception handler that strips model data from error responses |
| Document files stored with predictable URLs (e.g., `/media/documents/patient_123.pdf`) | Any authenticated user can access any document by guessing the URL | Use UUIDs in file paths and add a permission check before serving files; never use Django's default `MEDIA_URL` for sensitive files |
| No rate limiting on the chat endpoint | Patient or attacker can generate unlimited LLM API calls | Apply `django-ratelimit` or DRF throttling on `/api/chat/` endpoint |

---

## "Looks Done But Isn't" Checklist

- [ ] **Data isolation:** Cross-tenant API test exists and asserts 404 (not 200) for Nutritionist A accessing Nutritionist B's patient. Verified at `retrieve`, `update`, and `destroy` — not just `list`.
- [ ] **Vector retrieval isolation:** A test indexes documents for two nutritionists, queries as one, and asserts zero chunks from the other's documents are returned.
- [ ] **CPF protection:** A test calls the patient list and detail endpoints and asserts CPF is absent from every response field. No URL in the API contains a CPF-shaped string.
- [ ] **Celery on_commit:** A test creates a document and asserts the task is NOT enqueued until the transaction commits (use `transaction_testcase` + `celery.task_always_eager=False`).
- [ ] **LGPD consent field:** Patient creation serializer requires `consent_given=True`; creation without it returns 400. Consent timestamp is stored.
- [ ] **Scope guardrail:** A test sends an out-of-scope message (e.g., "what medication should I take?") and asserts the response is the deflection string — not an LLM-generated medical answer.
- [ ] **Conversation token limit:** A test sends 50 messages and asserts the 51st message still succeeds (no context overflow exception).
- [ ] **Idempotent document indexing:** A test processes the same document twice and asserts the vector store contains exactly N chunks (not 2N).
- [ ] **HNSW index exists:** `pg_indexes` query in a migration test or CI check confirms the index is present.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Cross-tenant vector leak discovered post-launch | HIGH | Audit all similarity_search calls; add filter; re-run integration tests; notify DPA under LGPD Art. 48 if data was exposed |
| Duplicate embeddings from non-idempotent tasks | MEDIUM | Write a one-time script to deduplicate chunks by `document_id` + `chunk_index` metadata; delete duplicates; re-run failed documents |
| Wrong embedding model used (dimension mismatch) | HIGH | Drop and recreate the embedding column with correct dimension; re-embed all documents (API cost + time); no shortcut |
| CPF exposed in logs | HIGH | Rotate all tokens; audit log storage; apply log scrubbing retroactively; review LGPD notification obligation |
| No HNSW index on live database | LOW | `CREATE INDEX CONCURRENTLY` on pgvector table (no table lock); monitor `pg_stat_progress_create_index`; takes minutes to hours depending on data volume |
| Celery task race condition causes double-processing | MEDIUM | Add status field + compare-and-swap update; manually clean duplicated vectors; no data loss but quality degradation |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| pgvector retrieval without tenant filter | Phase 4 — RAG pipeline | Integration test: two-nutritionist vector isolation test |
| Celery task fired before transaction commits | Phase 5 — Async ingestion | Unit test with `on_commit` hook assertion |
| DRF queryset scoping not applied to detail endpoints | Phase 2 — Patient management | Cross-tenant 404 test for retrieve/update/destroy |
| Celery task receives ORM objects as arguments | Phase 5 — Async ingestion | Code review checklist: no model instances as task args |
| Embedding dimension mismatch | Phase 3 — Vector store setup | Migration test: assert column dimension matches configured model |
| Scope guardrail as post-hoc string filter | Phase 6 — Chat assistant | Test: out-of-scope query returns deflection before RAG chain runs |
| CPF in logs or serializer responses | Phase 1 — Authentication/accounts | Test: patient endpoints return no CPF-shaped strings; log scrubber in CI |
| Missing HNSW index | Phase 3 — Vector store setup | `pg_indexes` assertion in migration smoke test |
| Unbounded conversation history | Phase 6 — Chat assistant | Test: 50-message conversation does not raise context overflow |
| Non-idempotent Celery ingestion task | Phase 5 — Async ingestion | Test: same document processed twice yields exactly N vectors |

---

## Sources

- Celery official docs — database transactions and `on_commit`: https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
- Celery official docs — task states and retry patterns: https://docs.celeryq.dev/en/stable/userguide/tasks.html
- LangChain PGVector integration — metadata filtering: https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector
- LangChain guardrails — scope and safety middleware: https://docs.langchain.com/oss/python/langchain/guardrails
- LangChain memory — `trim_messages` for context window management: https://docs.langchain.com/oss/python/langgraph/add-memory
- pgvector official README — HNSW indexing and filtered search: https://github.com/pgvector/pgvector/blob/master/README.md
- DRF official docs — object-level permissions and `get_object()`: https://github.com/encode/django-rest-framework/blob/main/docs/api-guide/permissions.md
- LGPD Art. 11 (Lei 13.709/2018) — treatment of sensitive personal data including health data and personal identifiers
- pgvector Context7 docs — filtered nearest neighbor search with HNSW iterative scan

---
*Pitfalls research for: multi-tenant clinical nutrition SaaS — Django + DRF + pgvector + LangChain + Celery*
*Researched: 2026-05-19*
