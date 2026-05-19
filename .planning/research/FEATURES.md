# Feature Research

**Domain:** Clinical nutrition SaaS — AI assistant with RAG for nutritionist-patient workflows
**Researched:** 2026-05-19
**Confidence:** HIGH (stack confirmed via Context7 official docs; feature patterns drawn from established RAG production patterns)

---

## Category 1: Authentication & LGPD Compliance

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Nutritionist registration with CRN + CPF | Regulatory identity — CRN is the professional license number required to legally operate as a nutritionist | LOW | CPF must never appear in URLs or logs per LGPD Art. 11; store hashed or encrypted |
| Email + password login returning JWT access + refresh tokens | Industry standard for stateless REST APIs | LOW | SimpleJWT `TokenObtainPairView` handles this out of the box |
| JWT token refresh endpoint | Stateless sessions require client-side refresh; missing this = forced re-login every few minutes | LOW | SimpleJWT `TokenRefreshView`; set access=5min, refresh=1day per PROJECT.md |
| Token rotation + blacklisting on refresh | Security baseline: prevents replay attacks after logout | LOW | `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` in `SIMPLE_JWT` settings; requires `rest_framework_simplejwt.token_blacklist` app |
| Logout endpoint that blacklists the refresh token | Without this, JWTs are irrevocable until expiry | LOW | `TokenBlacklistView`; call `token.blacklist()` programmatically |
| UUID as patient PK — never CPF | LGPD Art. 11: health data is sensitive category; CPF in URLs or FKs is a compliance violation | LOW | Django `UUIDField(primary_key=True, default=uuid.uuid4)` |
| LGPD consent recorded at patient creation | Legal requirement for processing health data; must be timestamped | LOW | Boolean field `lgpd_consent` + `lgpd_consent_at` DateTimeField on `PerfilPaciente` |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Patient role with separate JWT claims | Patients log in and get scoped tokens; prevents nutritionist-patient role confusion at API layer | MEDIUM | Custom `TokenObtainPairSerializer` that injects `role` claim; `@patient_required` / `@nutritionist_required` decorators enforce at view level |
| CRN format validation on registration | Prevents garbage data; builds trust with nutritionist users | LOW | Django validator or regex on `PerfilNutricionista.crn` |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| OAuth / magic-link login | "Modern" auth UX | Adds external dependencies, OAuth providers, email infrastructure complexity that is out of scope for v1 API | SimpleJWT is sufficient; defer to v2 |
| CPF as primary key or in URLs | "Easy lookup" | Direct LGPD Art. 11 violation; exposes sensitive identifier in logs, HTTP logs, browser history | UUID as PK; CPF stored separately, never surfaced in URLs |
| Long-lived access tokens (hours/days) | Fewer refresh calls | Token compromise window is enormous; irrevocable until expiry | 5-minute access + 1-day refresh with rotation |

---

## Category 2: Nutritionist Patient Management

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| CRUD for patient profiles scoped to authenticated nutritionist | Core workflow — nutritionist creates and owns patients | LOW | All querysets: `Patient.objects.filter(nutritionist=request.user)`; never unscoped `.all()` |
| Clinical fields on patient profile | Nutritionist needs structured data to configure the AI context | MEDIUM | Fields: dietary type, health conditions, bariatric status, macros (kcal, protein, carb, fat), food restrictions, allergies |
| Patient list endpoint (no CPF exposed) | Nutritionist needs to see their patient roster | LOW | Serializer must exclude CPF from list response; use name + UUID |
| Patient detail endpoint with full profile | Nutritionist edits clinical data between consultations | LOW | Full profile visible to owning nutritionist only |
| Soft delete or deactivation of patients | LGPD right to erasure; clinical data retention requirements conflict with hard delete | MEDIUM | `is_active` boolean; actual deletion flow needs LGPD policy decision |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Macro targets stored per patient | Enables AI to give quantitative answers ("you've set 150g protein/day") | LOW | Structured fields vs free-text notes — machine-readable by the RAG system prompt |
| Bariatric status flag | Nutrition post-bariatric surgery is a distinct clinical protocol; AI must know | LOW | Boolean + surgery type enum |
| Cross-patient isolation enforced at queryset level | Prevents accidental data leaks between nutritionists | LOW | Critical; must be in every view, not just the UI — queryset override in manager or explicit filter |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Automatic meal plan calculation by the system | "AI does everything" | Nutritionist liability; meal plans require licensed professional judgment | Nutritionist inputs the plan manually; AI only answers questions about it |
| Bulk patient import from CSV | Convenience | LGPD consent must be recorded per-patient with timestamp; bulk import bypasses this | Manual creation with per-patient consent checkbox |
| Patient self-registration without nutritionist | "Patient portal" UX | Breaks the data model — patients must be created by and linked to their nutritionist | Nutritionist creates patient; patient receives credentials separately |

---

## Category 3: Document Indexing Pipeline

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| PDF upload endpoint for nutritional documents | Nutritionists need to load their knowledge base (dietary guidelines, clinical protocols) | LOW | `multipart/form-data`; store file in Django `MEDIA_ROOT` or S3 |
| Async indexing via Celery task | Indexing can take seconds to minutes per document; blocking the API request is unacceptable | MEDIUM | Celery task receives `document_id`; fetches file, processes, stores vectors; returns task ID to caller |
| Text extraction from text-native PDFs | Most clinical PDFs are text-native (not scanned) | LOW | `pdfplumber` handles this; produces clean text per page |
| Text chunking with overlap | LLMs have context window limits; chunks need overlap to prevent context loss at boundaries | LOW | `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` — standard LangChain default is well-proven |
| Embedding generation and storage in pgvector | Chunks must be stored as vectors for semantic retrieval | MEDIUM | `OpenAIEmbeddings(model="text-embedding-ada-002")` → 1536 dimensions; store in pgvector with `HNSW` index using cosine ops |
| Document metadata stored with vectors | Required to filter retrieval by patient or nutritionist scope | MEDIUM | Metadata: `nutritionist_id`, `patient_id` (if patient-specific doc), `document_id`, `source_file`, `page_number`; enables `similarity_search(..., filter={"nutritionist_id": uuid})` |
| Indexing status tracking | Client needs to know when a document is ready for queries | LOW | `status` field: `pending` → `processing` → `indexed` / `failed`; poll or webhook |
| Task retry on transient failure | LLM API calls and DB writes can fail transiently | LOW | Celery `self.retry(countdown=60, max_retries=3)` |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| OCR fallback for scanned PDFs | Many nutritionist documents are scanned (lab reports, old protocols) | MEDIUM | `pytesseract` via `TesseractBlobParser` integrated into LangChain's `PyMuPDFLoader`; only invoked if text extraction yields < N characters per page |
| Per-patient document scoping | Some documents are patient-specific (e.g., their own lab results); retrieval should scope to patient + nutritionist knowledge base | MEDIUM | Metadata filter in retrieval: `patient_id=X OR (patient_id IS NULL AND nutritionist_id=Y)` — patient docs + nutritionist general docs |
| HNSW index on vector column | Dramatically faster ANN search at query time vs sequential scan | LOW | `CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)` — do this after initial data load; tune `ef_search` at query time if recall degrades |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Synchronous indexing in the API request | "Simpler code" | Blocks the HTTP response for seconds to minutes; timeouts on mobile; terrible UX | Celery async task always; return `202 Accepted` with task ID |
| Re-embedding all documents on model change | "Keep vectors current" | Extremely costly API call; all old vectors become invalid simultaneously | Pin embedding model version; document which model version produced each chunk in metadata; re-embed only on explicit migration |
| Storing raw file content in the vector DB | "Everything in one place" | Vector DBs are not blob stores; wastes storage, complicates retrieval | Store raw file in Django MEDIA_ROOT or S3; only chunks + embeddings go to pgvector |
| Semantic chunking with LLM | "Better chunks" | Expensive: requires LLM API call per chunk to determine boundaries; slows indexing massively | `RecursiveCharacterTextSplitter` is adequate for clinical text; semantic chunking is a v2+ optimization |

---

## Category 4: Scoped AI Assistant (Nutrition-Only Guardrails)

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Patient sends a message, receives an AI-generated answer | Core product value | MEDIUM | `POST /api/chat/` with `{"message": "..."}` |
| RAG retrieval: semantic search over indexed documents | Without retrieval, LLM hallucinates clinical facts | MEDIUM | `vector_store.similarity_search(query, k=4, filter={"nutritionist_id": ..., ...})` → top-k chunks injected into system prompt |
| Patient clinical profile injected into system prompt | Personalized answers require knowing the patient's macros, restrictions, conditions | LOW | Profile serialized as structured text block at top of system prompt before retrieved chunks |
| Scope enforcement: refuse off-topic questions | Clinical context — nutritionist and patient must trust the assistant stays in lane | MEDIUM | System prompt rule: "Only answer questions about nutrition, dietary plans, food substitutions, and eating habits. For any other topic, respond with the standard redirect message."; classify intent before answering |
| Standard redirect message for out-of-scope queries | Graceful degradation; patients need to know what the assistant can and cannot help with | LOW | Fixed string: "Sou um assistente focado em nutrição. Para outras dúvidas, consulte o profissional adequado." |
| Streaming or synchronous response | API must return the answer | LOW | Synchronous (blocking) is fine for v1; streaming is a differentiator for v2 |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Conversation history included in context | Multi-turn coherence: patient can say "what about that substitution you mentioned?" | MEDIUM | Persist messages to DB; load last N turns; use `trim_messages(strategy="last", max_tokens=2000)` to stay within context window; session ID = patient UUID |
| Source attribution in response | Clinical trust: patient (and nutritionist) can see which document/guideline the answer came from | MEDIUM | Return `sources` list alongside `answer`; include doc name + page number from metadata |
| LLM provider switching via env var | Dev uses Ollama locally; production uses Claude or GPT-4o; no code changes | LOW | Unified interface: `settings.LLM_PROVIDER` → factory returns appropriate `ChatAnthropic` / `ChatOpenAI` / `ChatOllama` instance |
| Intent pre-classification for scope check | More reliable guardrail than relying solely on system prompt | MEDIUM | Lightweight classification prompt: "Is this question about nutrition, food, or dietary plans? Yes/No" before invoking full RAG chain; short-circuit on No |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Unlimited conversation history in context | "Full context" | Context window overflow: Claude Sonnet has 200K tokens but cost scales; old turns dilute relevance | `trim_messages(strategy="last", max_tokens=2000)` keeps recent turns; summarization is a v2 optimization |
| LLM generating meal plans autonomously | "Complete automation" | Nutritionist legal liability; CFN (Brazilian nutrition council) regulations require professional sign-off on plans | AI answers questions about the plan; plan is authored by nutritionist |
| Exposing raw retrieved chunks to patient | "Transparency" | Clinical documents may contain information not meant for patient (other patients' data if misconfigured, internal notes) | Return curated AI response; optionally return sanitized source citations |
| One-size-fits-all system prompt | "Simplicity" | Cannot personalize without patient context; generic nutrition advice may conflict with patient's specific restrictions | Per-request system prompt construction: base prompt + patient profile + retrieved context |

---

## Category 5: Conversation History (Patient-Facing)

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Messages persisted to DB per patient | Without persistence, every session starts cold; patient cannot refer back | LOW | `Message` model: `patient`, `role` (user/assistant), `content`, `created_at`; FK to patient |
| Load last N messages on new request | Multi-turn context requires history | LOW | `Message.objects.filter(patient=patient).order_by('-created_at')[:20]` then reverse |
| Patient can only see their own conversation | Data isolation — same pattern as patient management | LOW | `Message.objects.filter(patient__nutritionist=request.user.patient_profile.nutritionist)` or simpler ownership check |
| Conversation grouped by session or chronological | Patient needs to make sense of their history | LOW | Simple chronological ordering is sufficient for v1; sessions are a v2 feature |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Token-aware history trimming before LLM call | Prevents context window overflow without arbitrary message count limits | LOW | LangChain `trim_messages(strategy="last", token_counter=count_tokens_approximately, max_tokens=2000)` |
| Message timestamps visible in API response | Patient (and nutritionist reviewing) can see when questions were asked | LOW | Always include `created_at` in `MessageSerializer` |
| Nutritionist can view patient's conversation history | Quality review, clinical oversight | LOW | `GET /api/patients/{uuid}/chat/` scoped to nutritionist's patients |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| In-memory conversation store (dict-based) | LangChain `InMemoryChatMessageHistory` examples look appealing | Data is lost on server restart; multi-worker deployments (Celery) share no memory | Always persist to PostgreSQL; load from DB per request |
| WebSocket streaming for chat | "Real-time feel" | Adds Django Channels infrastructure complexity; not needed for v1 API | Synchronous HTTP POST returning complete answer; streaming via SSE or WebSocket is v2 |
| Full conversation history in LLM context | "Total recall" | Token cost grows unbounded; old irrelevant turns degrade answer quality | Window of last 20 messages + token trim |

---

## Feature Dependencies

```
JWT Auth (nutritionist)
    └──required by──> Patient CRUD
                          └──required by──> Document Upload (scoped to nutritionist)
                          └──required by──> Chat (patient linked to nutritionist)

JWT Auth (patient)
    └──required by──> Chat endpoint

Document Upload
    └──required by──> Celery Async Indexing
                          └──required by──> pgvector Storage with Metadata
                                                └──required by──> RAG Retrieval
                                                                      └──required by──> AI Assistant Response

Patient Clinical Profile
    └──enhances──> AI Assistant Response (injected into system prompt)

Conversation History (DB-persisted)
    └──enhances──> AI Assistant Response (multi-turn coherence)

Scope Guardrail (system prompt)
    └──required by──> AI Assistant Response (safety)

LGPD Consent field
    └──required by──> Patient CRUD (legal baseline)

UUID as PK
    └──required by──> All patient-related endpoints (LGPD)
```

### Dependency Notes

- **JWT Auth required by Patient CRUD:** Nutritionist must be authenticated and identified before any patient query can be scoped correctly.
- **Document Upload required by RAG Retrieval:** Without indexed documents, semantic search returns empty; the assistant has no knowledge base.
- **Patient Clinical Profile enhances AI Response:** Profile is not strictly required for the RAG pipeline to function, but without it, answers are generic — which defeats the product's core value proposition. Build together.
- **DB-persisted conversation history required before multi-turn chat:** In-memory history fails in multi-worker or restart scenarios; persistence must be the first implementation, not a later refactor.
- **LGPD Consent field required by Patient CRUD:** Cannot create a patient record without recording consent timestamp — this is a legal baseline, not a feature to add later.

---

## MVP Definition

### Launch With (v1)

- [x] Nutritionist JWT auth (register, login, refresh, logout/blacklist) — gateway to all other features
- [x] UUID-based patient CRUD scoped to authenticated nutritionist — core data model
- [x] LGPD consent field + CPF never in URLs — compliance baseline, cannot defer
- [x] Document upload endpoint returning `202 Accepted` + task ID — triggers async pipeline
- [x] Celery task: extract text (pdfplumber) → chunk → embed → store in pgvector with nutritionist-scoped metadata — knowledge base
- [x] Indexing status tracking (`pending` / `processing` / `indexed` / `failed`) — client needs to know when docs are ready
- [x] Patient JWT auth — patient must be able to authenticate to use the assistant
- [x] Chat endpoint: load patient profile + recent history + RAG retrieval → LLM → persist response — core product value
- [x] Scope guardrail: system prompt rules + standard redirect message — clinical safety, non-negotiable
- [x] Conversation history persisted to DB (last 20 messages, token-trimmed) — multi-turn coherence
- [x] LLM provider switching via `LLM_PROVIDER` env var — dev/prod parity

### Add After Validation (v1.x)

- [ ] OCR fallback for scanned PDFs (Tesseract) — add when nutritionists report scanned documents failing
- [ ] Source attribution in chat responses (which document/page answered the question) — add when nutritionists ask for auditability
- [ ] Intent pre-classification before full RAG chain — add if scope guardrail bypasses appear in production logs
- [ ] Nutritionist view of patient conversation history — add when nutritionists request clinical oversight feature
- [ ] HNSW index tuning (`ef_search` at query time) — add when retrieval latency becomes a complaint

### Future Consideration (v2+)

- [ ] Frontend (React) — out of scope for v1 per PROJECT.md; validate backend first
- [ ] WebSocket / SSE streaming responses — adds Django Channels complexity; not justified until latency is a real complaint
- [ ] Conversation summarization for long histories — optimization; token trimming is sufficient for v1
- [ ] Semantic chunking (LLM-assisted) — costly; `RecursiveCharacterTextSplitter` is adequate for clinical text
- [ ] Patient OAuth / magic-link login — infrastructure complexity; SimpleJWT sufficient for v1
- [ ] Multi-tenancy billing — out of scope per PROJECT.md
- [ ] Wearable / external health app integration — out of scope per PROJECT.md

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Nutritionist JWT auth | HIGH | LOW | P1 |
| Patient CRUD (nutritionist-scoped) | HIGH | LOW | P1 |
| LGPD compliance (UUID PK, consent, no CPF in URLs) | HIGH | LOW | P1 |
| Document upload + Celery async indexing | HIGH | MEDIUM | P1 |
| pgvector storage with metadata filtering | HIGH | MEDIUM | P1 |
| Patient JWT auth | HIGH | LOW | P1 |
| Chat endpoint with RAG + patient profile injection | HIGH | MEDIUM | P1 |
| Scope guardrail (nutrition-only system prompt) | HIGH | LOW | P1 |
| DB-persisted conversation history (multi-turn) | HIGH | LOW | P1 |
| LLM provider switching (env var) | HIGH | LOW | P1 |
| Indexing status tracking | MEDIUM | LOW | P1 |
| Token-aware history trimming | MEDIUM | LOW | P1 |
| HNSW vector index | MEDIUM | LOW | P2 |
| OCR fallback for scanned PDFs | MEDIUM | MEDIUM | P2 |
| Source attribution in responses | MEDIUM | MEDIUM | P2 |
| Intent pre-classification for scope | MEDIUM | MEDIUM | P2 |
| Nutritionist view of patient chat | MEDIUM | LOW | P2 |
| Token blacklist / logout endpoint | HIGH | LOW | P1 |
| CRN format validation | LOW | LOW | P2 |
| Streaming responses (SSE/WS) | MEDIUM | HIGH | P3 |
| Semantic chunking | LOW | HIGH | P3 |
| Conversation summarization | LOW | MEDIUM | P3 |

---

## Competitor Feature Analysis

| Feature | Typical SaaS (e.g., Nutrium, Practice Better) | Our Approach |
|---------|----------------------------------------------|--------------|
| Patient management | Full web UI, appointment scheduling, billing | API-only v1; no scheduling/billing |
| AI assistant | None or generic chatbot without RAG | RAG-grounded, personalized by clinical profile |
| Document ingestion | Manual entry, no semantic search | Async pipeline → pgvector semantic retrieval |
| Scope guardrail | N/A (no AI) | System prompt + optional intent classifier |
| Data isolation | Multi-tenant SaaS (shared DB with row-level security) | Same pattern: queryset-level isolation enforced in every view |
| LGPD compliance | Varies; Brazilian platforms typically implement basics | UUID PK, CPF exclusion from URLs, consent timestamp — explicit and auditable |

---

## Sources

- LangChain RAG pipeline documentation: Context7 `/llmstxt/langchain_llms-full_txt` (HIGH confidence)
- LangChain conversation history (`RunnableWithMessageHistory`, `trim_messages`): Context7 `/llmstxt/langchain_llms-full_txt` (HIGH confidence)
- LangChain guardrails and system prompt patterns: Context7 `/llmstxt/langchain_llms-full_txt` (HIGH confidence)
- LangChain pgvector metadata filtering: Context7 `/llmstxt/langchain_llms-full_txt` (HIGH confidence)
- pgvector HNSW vs IVFFlat indexing: Context7 `/pgvector/pgvector` (HIGH confidence)
- SimpleJWT token rotation and blacklisting: Context7 `/jazzband/djangorestframework-simplejwt` (HIGH confidence)
- Celery task retry patterns: Context7 `/websites/celeryq_dev_en_stable` (HIGH confidence)
- LangChain Tesseract OCR integration: Context7 `/llmstxt/langchain_llms-full_txt` (HIGH confidence)
- OpenAI `text-embedding-ada-002` / `text-embedding-3-small` 1536 dimensions: Context7 `/llmstxt/langchain_llms-full_txt` (HIGH confidence)
- LGPD Art. 11 (health data as sensitive category): Domain knowledge, MEDIUM confidence — validate with Brazilian legal counsel before launch

---

*Feature research for: Clinical nutrition SaaS — NutriChat RAG MVP*
*Researched: 2026-05-19*
