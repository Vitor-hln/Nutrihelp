# Roadmap: NutriChat RAG v1.0

## Overview

Starting from an empty repository, this milestone delivers a complete REST API with JWT authentication, LGPD-compliant patient management, asynchronous document indexing, and a RAG-powered nutritional assistant backed by pgvector. Each phase unblocks the next: infrastructure enables auth, auth enables patient isolation, patient isolation enables safe document indexing, indexed documents enable RAG retrieval, RAG retrieval enables the chat endpoint, and the final phase hardens everything for real use.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Infrastructure Foundation** - Docker Compose stack running with a single command
- [ ] **Phase 2: Auth & LGPD Baseline** - JWT authentication, role permissions, and LGPD safeguards
- [ ] **Phase 3: Patient Management** - Nutritionist-scoped patient CRUD with enforced tenant isolation
- [ ] **Phase 4: Document Pipeline** - Async document upload, pdfplumber extraction, and Celery indexing
- [ ] **Phase 5: RAG Pipeline** - Scoped semantic retrieval, scope classifier, prompt builder, and LLM client
- [ ] **Phase 6: Chat Endpoint** - Patient-facing AI assistant with persisted conversation history
- [ ] **Phase 7: Quality & Hardening** - Isolation test suite, rate limiting, and OpenAPI documentation

## Phase Details

### Phase 1: Infrastructure Foundation
**Goal**: The development environment runs fully with a single `docker compose up` and persists data across restarts
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02
**Success Criteria** (what must be TRUE):
  1. `docker compose up` starts all services (Django, Celery, Redis, PostgreSQL, Ollama) without manual steps
  2. Django admin is reachable at `localhost:3600/admin/` and responds with a login page
  3. PostgreSQL is reachable on port 3601 and the `vector` extension is enabled (verified via `\dx`)
  4. Redis is reachable on port 6379 and Celery worker connects successfully (visible in worker logs)
  5. Stopping and restarting the stack preserves all database data (volumes persist)
**Plans**: 2 plans
  - [ ] 01-01-PLAN.md — Django scaffold, dependencies, and environment config
  - [ ] 01-02-PLAN.md — Docker orchestration, stack bring-up, and verification

### Phase 2: Auth & LGPD Baseline
**Goal**: Nutritionists and patients can authenticate via JWT, all LGPD safeguards are active from day one
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10
**Success Criteria** (what must be TRUE):
  1. `POST /api/accounts/register/` creates a nutritionist account with CRN and CPF; response never includes CPF
  2. `POST /api/accounts/token/` returns access + refresh JWT; access token encodes `role` claim
  3. Refresh token is blacklisted after `POST /api/accounts/token/blacklist/`; subsequent refresh attempts return 401
  4. Patient profile row uses a UUID primary key; `GET /api/patients/{uuid}/` works but CPF never appears in the URL or response body
  5. `lgpd_consent` field and its timestamp are required on patient creation; omitting them returns 400
  6. Django log output contains no CPF strings — the log scrubber filters them automatically
**Plans**: TBD
**UI hint**: no

### Phase 3: Patient Management
**Goal**: Nutritionists can fully manage their patient roster and tenant isolation is structurally enforced
**Depends on**: Phase 2
**Requirements**: PAT-01, PAT-02, PAT-03, PAT-04, PAT-05, PAT-06
**Success Criteria** (what must be TRUE):
  1. `POST /api/patients/` creates a patient linked to the authenticated nutritionist with all clinical fields (diet type, health conditions, bariatric status, macros, dietary restrictions)
  2. `GET /api/patients/` returns only the authenticated nutritionist's patients — a second nutritionist's patients are invisible
  3. Nutritionist A attempting `GET /api/patients/{uuid-owned-by-B}/` receives 404, not 403 — existence is not revealed
  4. `PATCH /api/patients/{uuid}/` updates clinical fields and persists changes
  5. `DELETE /api/patients/{uuid}/` soft-deletes the patient (record exists with `is_active=False`); patient no longer appears in list
**Plans**: TBD

### Phase 4: Document Pipeline
**Goal**: Nutritionists can upload PDF documents and the system indexes them asynchronously without blocking the API
**Depends on**: Phase 1, Phase 2
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07
**Success Criteria** (what must be TRUE):
  1. `POST /api/documents/` with a PDF file returns `202 Accepted` immediately — the response arrives before indexing completes
  2. After the Celery task finishes, document status transitions from `pending` → `processing` → `indexed`; a failed task transitions to `failed`
  3. `GET /api/documents/{id}/` shows the current indexing status (nutritionist can poll or check asynchronously)
  4. The indexed `Chunk` rows in the database each carry `nutritionist_id` as a metadata field
  5. Text-native PDFs are extracted via pdfplumber without error; the extracted text is present in the Chunk records
**Plans**: TBD

### Phase 5: RAG Pipeline
**Goal**: Semantic retrieval is scoped to the nutritionist's knowledge base, out-of-scope questions are rejected before any LLM call, and the full pipeline produces a grounded response
**Depends on**: Phase 4
**Requirements**: RAG-01, RAG-02, RAG-03, RAG-04, RAG-05, RAG-06
**Success Criteria** (what must be TRUE):
  1. A semantic search query returns the top-k chunks ranked by cosine distance; chunks from a different nutritionist's documents are never included in results
  2. A question clearly outside nutrition scope (e.g., "what is the weather today?") is classified as out-of-scope and returns the standard redirection message without ever calling the LLM
  3. A nutrition question returns a response that cites content present in the indexed chunks and includes clinical fields from the patient profile (diet type, conditions) in the assembled prompt
  4. Switching `LLM_PROVIDER` env var between `ollama`, `claude`, and `openai` routes the call to the correct backend without code changes
  5. The HNSW index on `Chunk.embedding` is present in the database schema (confirmed via `\d chunk`)
**Plans**: TBD
**UI hint**: no

### Phase 6: Chat Endpoint
**Goal**: Patients can send nutritional questions and receive RAG-grounded responses, with all conversation history persisted in PostgreSQL
**Depends on**: Phase 5
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04
**Success Criteria** (what must be TRUE):
  1. `POST /api/chat/messages/` as an authenticated patient returns a nutrition-grounded response generated by the RAG pipeline
  2. A second call to the same endpoint returns a response that has access to the prior exchange in the conversation history
  3. Conversation history is stored in the `Mensagem` table in PostgreSQL — restarting the server does not erase it
  4. A patient attempting to access another patient's conversation receives 404
  5. Long conversation histories are trimmed before the LLM call so the payload never exceeds the model's context window
**Plans**: TBD
**UI hint**: no

### Phase 7: Quality & Hardening
**Goal**: The API is safe against cross-tenant probing, protected from chat abuse, and fully documented for consumers
**Depends on**: Phase 6
**Requirements**: INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. The isolation test suite passes: every patient and chat endpoint returns 404 when accessed cross-tenant (all combinations covered)
  2. Sending more than the configured rate limit of chat requests from a single patient within a time window returns 429
  3. `GET /api/schema/swagger-ui/` renders a Swagger UI with all endpoints documented including request/response schemas
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure Foundation | 0/2 | Not started | - |
| 2. Auth & LGPD Baseline | 0/TBD | Not started | - |
| 3. Patient Management | 0/TBD | Not started | - |
| 4. Document Pipeline | 0/TBD | Not started | - |
| 5. RAG Pipeline | 0/TBD | Not started | - |
| 6. Chat Endpoint | 0/TBD | Not started | - |
| 7. Quality & Hardening | 0/TBD | Not started | - |
