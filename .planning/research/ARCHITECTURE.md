# Architecture Research

**Domain:** Django + pgvector + LangChain RAG SaaS (NutriChat)
**Researched:** 2026-05-19
**Confidence:** HIGH — verified against pgvector-python official docs, LangChain official docs, and project's own guia_implementacao.md

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          API Layer (Django + DRF)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────────┐  │
│  │  /api/accounts/ │  │  /api/pacientes/ │  │  /api/chat/mensagens/    │  │
│  │  (register,JWT) │  │  (CRUD,nutri-   │  │  (patient-only, triggers │  │
│  │                 │  │   only, scoped) │  │   RAG pipeline)          │  │
│  └────────┬────────┘  └────────┬────────┘  └───────────┬──────────────┘  │
├───────────┼────────────────────┼────────────────────────┼─────────────────┤
│           │            Service / Domain Layer            │                  │
│  ┌────────▼──────┐  ┌─────────▼────────┐  ┌────────────▼──────────────┐  │
│  │  accounts app │  │   knowledge app  │  │        chat app           │  │
│  │  User         │  │  indexer.py      │  │  rag_pipeline.py          │  │
│  │  PerfilNutri  │  │  retriever.py    │  │  prompt_builder.py        │  │
│  │  PerfilPacien │  │  llm_client.py   │  │  Conversa / Mensagem      │  │
│  └────────┬──────┘  └─────────┬────────┘  └────────────┬──────────────┘  │
├───────────┼────────────────────┼────────────────────────┼─────────────────┤
│           │            Async Layer (Celery + Redis)       │                 │
│           │      ┌─────────────▼────────────────┐        │                 │
│           │      │  knowledge/tasks.py           │        │                 │
│           │      │  indexar_documento_task()     │        │                 │
│           │      │  (chunking → embed → persist) │        │                 │
│           │      └─────────────┬────────────────┘        │                 │
├───────────┼────────────────────┼────────────────────────┼─────────────────┤
│           │                Data Layer                      │                 │
│  ┌────────▼────────────────────▼───────────────┐  ┌──────▼──────────────┐  │
│  │             PostgreSQL + pgvector            │  │    Redis            │  │
│  │  accounts_* tables (User, PerfilNutri,       │  │  Celery broker +    │  │
│  │             PerfilPaciente)                  │  │  result backend     │  │
│  │  chat_* tables (Conversa, Mensagem)          │  └─────────────────────┘  │
│  │  knowledge_* tables (Documento, Chunk)       │                           │
│  │  VectorField on Chunk.embedding (1536-dim)   │                           │
│  └──────────────────────────────────────────────┘                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `accounts` app | Users, JWT auth, profiles (nutritionist/patient) | Django AbstractUser + SimpleJWT + DRF permissions |
| `knowledge` app | Document ingestion, embedding, vector search, LLM orchestration | pgvector-python + LangChain embeddings + custom retriever |
| `chat` app | Conversation history, RAG entry point | DRF view calls `rag_pipeline.py`, persists Mensagem |
| `tasks.py` (knowledge) | Async indexing so API never blocks on embed calls | Celery worker — receives Documento.id, runs full pipeline |
| `llm_client.py` | Unified LLM facade — switches Claude/OpenAI via env var | Factory function dispatching to `anthropic` or `openai` SDK |
| `retriever.py` | Semantic search — embeds query, runs pgvector ORM query | `CosineDistance` ORM lookup on `Chunk.embedding` |
| `indexer.py` | Text split → embed → bulk insert Chunk rows | LangChain `RecursiveCharacterTextSplitter` + `OpenAIEmbeddings` |
| `prompt_builder.py` | Assemble final LLM messages list from chunks + patient profile + history | Pure Python function — no DB access |

---

## Recommended Project Structure

```
nutrichat/
├── config/
│   ├── settings/
│   │   ├── base.py          # shared: installed apps, JWT config, RAG constants
│   │   ├── development.py   # DEBUG=True, SQLite-optional, Ollama LLM_PROVIDER
│   │   └── production.py    # ALLOWED_HOSTS, HTTPS, cloud LLM_PROVIDER
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py            # Celery app instance — import in __init__.py
│
├── apps/
│   ├── accounts/
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # User(AbstractUser) with role field
│   │   │   ├── perfil_nutricionista.py
│   │   │   └── perfil_paciente.py   # UUID PK, consentimento_lgpd field
│   │   ├── managers.py              # PacienteManager.do_nutricionista()
│   │   ├── permissions.py           # IsNutricionista, IsPaciente, IsPacienteDoNutricionista
│   │   ├── serializers/
│   │   │   ├── register.py
│   │   │   ├── paciente_resumo.py   # list — no CPF
│   │   │   └── paciente_detalhe.py  # detail — with CPF
│   │   ├── views/
│   │   │   ├── register.py
│   │   │   └── paciente.py
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── model_test/
│   │       ├── serializer_test/
│   │       └── view_test/
│   │
│   ├── knowledge/
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── documento.py   # titulo, arquivo, conteudo_bruto, indexado
│   │   │   └── chunk.py       # VectorField(dimensions=1536), HNSW index in Meta
│   │   ├── indexer.py         # indexar_documento(documento) → int
│   │   ├── retriever.py       # buscar_chunks_relevantes(texto, limite) → list[str]
│   │   ├── rag_pipeline.py    # processar_mensagem_rag(paciente, conversa, texto) → str
│   │   ├── prompt_builder.py  # montar_prompt(...) → list[dict]
│   │   ├── llm_client.py      # chamar_llm(mensagens) → str
│   │   ├── tasks.py           # @shared_task indexar_documento_task(documento_id)
│   │   ├── urls.py            # POST /api/documentos/
│   │   └── tests/
│   │
│   └── chat/
│       ├── models/
│       │   ├── __init__.py
│       │   ├── conversa.py    # FK → PerfilPaciente
│       │   └── mensagem.py    # FK → Conversa, role in (user, assistant)
│       ├── serializers/
│       │   ├── conversa.py
│       │   └── mensagem.py
│       ├── views/
│       │   ├── conversa.py    # list/create, scoped to request.user.perfil_paciente
│       │   └── mensagem.py    # create → calls processar_mensagem_rag
│       ├── urls.py
│       └── tests/
│
├── manage.py
├── pyproject.toml             # uv dependency manifest
├── uv.lock
└── dotenv_files/
    ├── .env-example
    └── .env                   # gitignored
```

### Structure Rationale

- **`models/` as a package per app:** avoids God-models files; each model in its own module. Required because `accounts` has 3 related models and `knowledge` has 2.
- **`knowledge/` owns all RAG logic:** `indexer`, `retriever`, `rag_pipeline`, `prompt_builder`, `llm_client` all live here. `chat` app calls `rag_pipeline.processar_mensagem_rag` — it never knows which LLM or vector store is in use.
- **`chat/` is purely I/O:** it owns Conversa/Mensagem models and the HTTP view. All intelligence delegates to `knowledge`.
- **`config/celery.py` + `config/__init__.py`:** standard Django-Celery integration pattern. Worker process imports same settings as the web process.

---

## Architectural Patterns

### Pattern 1: Django ORM as the Vector Store

**What:** Use `pgvector.django.VectorField` directly on the `Chunk` model. All vector CRUD goes through Django migrations and the ORM — no separate vector DB process required.

**When to use:** Always in this project. pgvector runs inside the existing Postgres container.

**Trade-offs:** ACID transactions for free; no network hop to external vector store; migration-managed schema. Downside: raw SQL performance tuning needs to happen at the Postgres level (HNSW index config), not via a vector-DB dashboard.

**Integration point (Django ORM ↔ pgvector):**

```python
# knowledge/models/chunk.py
from pgvector.django import VectorField, HnswIndex

class Chunk(models.Model):
    EMBEDDING_DIMENSIONS = 1536  # text-embedding-ada-002

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='chunks')
    conteudo  = models.TextField()
    indice    = models.PositiveIntegerField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)

    class Meta:
        indexes = [
            HnswIndex(
                name='chunk_embedding_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],  # cosine distance for text
            )
        ]
```

The HNSW index is declared in `Meta.indexes` and created via a normal Django migration. `m=16, ef_construction=64` are the recommended defaults for recall/speed balance. Use `vector_cosine_ops` because OpenAI embeddings are cosine-normalized.

### Pattern 2: Custom Manager for Enforced Tenant Isolation

**What:** A custom Django Manager that injects the `nutricionista=` filter automatically, making it impossible to forget the scope.

**When to use:** Everywhere a nutritionist-scoped view accesses `PerfilPaciente`.

**Trade-offs:** Slightly more boilerplate upfront; pays off by making data leaks structurally impossible rather than relying on developer discipline.

```python
# accounts/managers.py
class PacienteManager(models.Manager):
    def do_nutricionista(self, nutricionista_profile):
        """Always scoped. Never call .all() directly."""
        return self.get_queryset().filter(nutricionista=nutricionista_profile)

# In view get_queryset():
def get_queryset(self):
    return PerfilPaciente.objects.do_nutricionista(
        self.request.user.perfil_nutricionista
    ).select_related('user')
```

The `Conversa` model has an analogous pattern: `Conversa.objects.filter(paciente=request.user.perfil_paciente)`.

### Pattern 3: LangChain for Embeddings Only, pgvector ORM for Storage

**What:** Use LangChain's `OpenAIEmbeddings` class to generate vectors (its main value: provider abstraction and batching). Do NOT use LangChain's `PGVector` vector store class — that requires its own connection string and maintains its own schema, which conflicts with Django's ORM ownership of the database.

**When to use:** During indexing (embed_documents) and retrieval (embed_query). The resulting float list is stored via the Django ORM's `Chunk.embedding` field.

**Trade-offs:** Slight duplication (LangChain embedding + Django ORM storage instead of all-LangChain). But this keeps Django as the single source of truth for the DB schema and gives full ORM query composability for isolation filters.

```python
# knowledge/indexer.py — indexing path
from langchain_openai import OpenAIEmbeddings

def indexar_documento(documento: Documento) -> int:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    textos = splitter.split_text(documento.conteudo_bruto)

    model = OpenAIEmbeddings(model="text-embedding-ada-002")
    vetores = model.embed_documents(textos)   # returns list[list[float]]

    Chunk.objects.bulk_create([
        Chunk(documento=documento, conteudo=t, indice=i, embedding=v)
        for i, (t, v) in enumerate(zip(textos, vetores))
    ])
    documento.indexado = True
    documento.save(update_fields=['indexado'])
    return len(textos)

# knowledge/retriever.py — query path
from pgvector.django import CosineDistance

def buscar_chunks_relevantes(texto_consulta: str, limite: int = 5) -> list[str]:
    model = OpenAIEmbeddings(model="text-embedding-ada-002")
    vetor = model.embed_query(texto_consulta)   # returns list[float]

    chunks = (
        Chunk.objects
        .annotate(distancia=CosineDistance('embedding', vetor))
        .order_by('distancia')[:limite]
    )
    return [c.conteudo for c in chunks]
```

Use `CosineDistance` (not `L2Distance`) because OpenAI embeddings are designed for cosine similarity. The annotated `distancia` field can also be used for a relevance threshold filter (`filter(distancia__lt=0.3)`) to avoid returning irrelevant chunks.

### Pattern 4: Celery Task as the Indexing Entry Point

**What:** The API endpoint for document upload returns 202 immediately. A Celery `shared_task` receives `documento_id`, re-fetches the `Documento` from the DB, and runs the full indexing pipeline.

**When to use:** Any document ingestion — this is the only acceptable flow because embedding API calls can take 2-30s depending on document size.

**Trade-offs:** Slightly more complex error handling (task failures must be monitored). The `Documento.indexado` flag acts as the status signal.

```python
# knowledge/tasks.py
from celery import shared_task
from .models import Documento
from .indexer import indexar_documento

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def indexar_documento_task(self, documento_id: int):
    try:
        doc = Documento.objects.get(id=documento_id)
        if doc.indexado:
            return  # idempotent — already processed
        indexar_documento(doc)
    except Exception as exc:
        raise self.retry(exc=exc)
```

The upload view calls `indexar_documento_task.delay(documento.id)` after saving. The task is idempotent: if it runs twice (e.g., after a retry), it exits early.

---

## Data Flow

### Flow 1: Document Ingestion (Async)

```
POST /api/documentos/
    ↓
DocumentoCreateView (permission: IsNutricionista)
    ↓ saves Documento(indexado=False)
    ↓ calls indexar_documento_task.delay(documento.id)
    → returns HTTP 202

[Celery worker picks up task]
    ↓
indexar_documento_task(documento_id)
    ↓
Documento.objects.get(id=documento_id)
    ↓
RecursiveCharacterTextSplitter → list of text chunks
    ↓
OpenAIEmbeddings.embed_documents(textos) → list[list[float]]
    ↓
Chunk.objects.bulk_create([...]) — each row has VectorField
    ↓
Documento.indexado = True → save()
```

### Flow 2: Patient Chat (Synchronous RAG)

```
POST /api/chat/mensagens/
    { "conversa_id": UUID, "conteudo": "posso substituir arroz por batata?" }
    ↓
MensagemCreateView (permission: IsPaciente)
    ↓ verifies conversa.paciente == request.user.perfil_paciente
    ↓
processar_mensagem_rag(paciente, conversa, texto)
    │
    ├─ retriever.buscar_chunks_relevantes(texto, limite=5)
    │      ↓ embed_query(texto) → float[1536]
    │      ↓ Chunk.objects.annotate(CosineDistance).order_by()[:5]
    │      → list[str]  (top-k chunk texts)
    │
    ├─ Mensagem.objects.filter(conversa=conversa).order_by('-timestamp')[:10]
    │      → historico (reversed to chronological)
    │
    ├─ prompt_builder.montar_prompt(paciente, texto, chunks, historico)
    │      → list[dict]  [{role, content}, ...]
    │
    ├─ llm_client.chamar_llm(mensagens)
    │      → str  (LLM response text)
    │
    └─ Mensagem.objects.bulk_create([user_msg, assistant_msg])

    → HTTP 200 { "resposta": "..." }
```

### Flow 3: Nutritionist Creates Patient

```
POST /api/pacientes/
    { "cpf": "...", "nome": "...", "tipo_dieta": "vegana", ... }
    ↓
PacienteListCreateView (permission: IsNutricionista)
    ↓
get_queryset(): PerfilPaciente.objects.do_nutricionista(request.user.perfil_nutricionista)
    ↓
perform_create(): serializer.save(nutricionista=request.user.perfil_nutricionista)
    → UUID assigned automatically, CPF stored but never in URL
    → HTTP 201 { "id": "UUID", ... }  // CPF omitted from resumo serializer
```

---

## Multi-Tenancy: Data Isolation Architecture

This is not a SaaS multi-tenancy at the database schema level (no separate schemas per tenant). It is **row-level isolation** enforced at every queryset.

### Isolation Rules

| Model | Isolation Rule | Enforcement Point |
|-------|---------------|-------------------|
| `PerfilPaciente` | `filter(nutricionista=request.user.perfil_nutricionista)` | `get_queryset()` in every view + `PacienteManager` |
| `Conversa` | `filter(paciente=request.user.perfil_paciente)` | `get_queryset()` in chat views |
| `Mensagem` | Implicit via `Conversa` FK (cascade filter) | ORM join through `Conversa` |
| `Chunk` | Global knowledge base — NOT per-nutritionist | Intentional: nutrition knowledge is shared |
| `Documento` | Global knowledge base — NOT per-nutritionist | Intentional: nutrition knowledge is shared |

The knowledge base (`Documento` + `Chunk`) is **intentionally global** — nutritional science docs apply to all patients. If per-nutritionist documents are needed in the future, add a nullable `nutricionista` FK to `Documento` and filter on it in `buscar_chunks_relevantes`.

### Object-Level Permission Check

For `GET /api/pacientes/{uuid}/`, both queryset-level and object-level checks run:

1. `get_queryset()` via `PacienteManager.do_nutricionista()` — SQL WHERE clause
2. `IsPacienteDoNutricionista.has_object_permission()` — Python-level double-check

This defense in depth means a misconfigured queryset cannot accidentally expose another nutritionist's patient.

---

## Integration Points

### Django ORM ↔ pgvector

| Concern | Integration | Notes |
|---------|-------------|-------|
| Schema | `VectorField(dimensions=1536)` in `Chunk` model | Migration-managed, `CREATE EXTENSION vector` must run first |
| Index | `HnswIndex(..., opclasses=['vector_cosine_ops'])` in `Meta.indexes` | Created by Django migration after `Chunk` table exists |
| Write | `Chunk.objects.bulk_create([...])` with `embedding=list[float]` | pgvector-python converts list to vector type automatically |
| Read/Search | `Chunk.objects.annotate(distancia=CosineDistance('embedding', vetor)).order_by('distancia')[:k]` | Pushes cosine distance computation into Postgres; HNSW index used automatically |
| Threshold filter | `.alias(d=CosineDistance(...)).filter(d__lt=0.35)` | Optional: drops irrelevant chunks before returning |

### LangChain ↔ Django

| Concern | Integration | Notes |
|---------|-------------|-------|
| Embeddings | `OpenAIEmbeddings` from `langchain_openai` | Used only for vector math; result stored via Django ORM |
| Text splitting | `RecursiveCharacterTextSplitter` from `langchain_text_splitters` | Pure Python, no DB interaction |
| LLM calls | Direct `anthropic`/`openai` SDK in `llm_client.py` | LangChain NOT used as LLM orchestrator in this project — too much overhead for a single-chain use case |
| Settings | `settings.OPENAI_API_KEY`, `settings.LLM_PROVIDER` | LangChain reads from Django settings, not its own config |

**Key decision:** LangChain's `PGVector` vector store class is NOT used. It manages its own DB tables and connection, bypassing Django migrations. Instead, LangChain provides only embedding utilities; Django ORM owns the schema.

### Django ↔ Celery

| Concern | Integration | Notes |
|---------|-------------|-------|
| Task definition | `@shared_task` in `knowledge/tasks.py` | Discovers via `CELERY_AUTODISCOVER_TASKS` |
| Task invocation | `indexar_documento_task.delay(documento.id)` | Non-blocking — returns immediately |
| DB access in task | Normal Django ORM inside the task | Celery worker imports Django settings; ORM works identically |
| Error handling | `self.retry(exc=exc, max_retries=3)` | Retries on embedding API failures |

### Internal App Boundaries

| Boundary | Communication | Rule |
|----------|---------------|------|
| `chat` → `knowledge` | Direct Python import of `rag_pipeline.processar_mensagem_rag` | Acceptable: one-way dependency, `chat` consumes `knowledge` |
| `knowledge` → `accounts` | Direct Python import of `PerfilPaciente` model | Acceptable: `knowledge` needs patient context for prompt |
| `chat` → `accounts` | Direct Python import of `PerfilPaciente` model | Acceptable: `chat` models FK to patient |
| `knowledge` → `chat` | FORBIDDEN | `knowledge` must never import from `chat` |
| `accounts` → `chat` or `knowledge` | FORBIDDEN | `accounts` is the base layer |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 nutritionists / 0-1k patients | Current monolith is correct. Single Postgres, single Celery worker, synchronous chat responses are fine. |
| 1k-10k patients | Add Celery concurrency (`-c 4`). Add HNSW index if not yet created. Consider pgBouncer for connection pooling. Chat endpoint may need async Django (ASGI). |
| 10k+ patients, 1M+ chunks | Partition `Chunk` table by document type. Add read replica for vector search. Consider moving embedding API calls to a dedicated microservice to avoid blocking Celery queue. |

### Scaling Priorities

1. **First bottleneck:** Embedding API latency during indexing. Fix: increase Celery worker concurrency; batch documents per task rather than one doc per task.
2. **Second bottleneck:** `CosineDistance` full-table scan if HNSW index is not created. Fix: ensure migration for `HnswIndex` runs. HNSW search degrades gracefully with data volume.
3. **Third bottleneck:** LLM response time in synchronous chat (2-10s per call). Fix: streaming responses via SSE or WebSocket; move chat endpoint to async view.

---

## Anti-Patterns

### Anti-Pattern 1: Using LangChain's PGVector Class

**What people do:** `from langchain_postgres import PGVector; vector_store = PGVector(connection=..., ...)` to store and retrieve chunks.

**Why it's wrong:** LangChain's `PGVector` creates its own `langchain_pg_embedding` and `langchain_pg_collection` tables outside Django's migration system. It cannot be queried with Django ORM filters — meaning the isolation rule (`filter(nutricionista=...)`) cannot compose with a LangChain retriever. Schema drift becomes a maintenance problem.

**Do this instead:** Use LangChain only for `OpenAIEmbeddings` (vector math). Store results in `Chunk` via Django ORM. Query via `CosineDistance` ORM lookup.

### Anti-Pattern 2: Unscoped Patient Querysets

**What people do:** `PerfilPaciente.objects.all()` or `PerfilPaciente.objects.get(id=uuid)` without filtering by nutritionist.

**Why it's wrong:** Returns patients from all nutritionists. A nutritionist with a valid token can access another nutritionist's patient data by guessing a UUID.

**Do this instead:** Every view's `get_queryset()` must use `PacienteManager.do_nutricionista(request.user.perfil_nutricionista)`. Object-level permission `IsPacienteDoNutricionista` provides a second guard on detail views.

### Anti-Pattern 3: CPF or Clinical Data in Logs or Prompts

**What people do:** `logger.info(f"Patient {paciente.cpf} asked: {texto}")` or including `paciente.cpf` in the LLM prompt context.

**Why it's wrong:** LGPD Art. 11 — health data logs become a liability. CPF in LLM prompts means health + identity data is sent to a third-party API (Anthropic/OpenAI), violating data minimization.

**Do this instead:** Log only `paciente.id` (UUID). In `prompt_builder.py`, include only clinical fields needed for nutritional context: `tipo_dieta`, `bariatrico`, `condicoes`, `observacoes`. Never include `cpf`, `nome`, `email`.

### Anti-Pattern 4: Blocking the API on Embedding Calls

**What people do:** Calling `indexar_documento(doc)` synchronously in the upload view.

**Why it's wrong:** Embedding a PDF can take 5-30 seconds. The HTTP request times out. Under concurrent uploads, all API workers are blocked.

**Do this instead:** Return HTTP 202 immediately, dispatch `indexar_documento_task.delay(doc.id)`. The `Documento.indexado` flag tells the UI when processing is complete.

### Anti-Pattern 5: Knowledge App Importing from Chat App

**What people do:** `from apps.chat.models import Mensagem` inside `knowledge/rag_pipeline.py`.

**Why it's wrong:** Creates a circular dependency (`chat` imports `knowledge`, `knowledge` imports `chat`). Breaks app-level separation of concerns.

**Do this instead:** Pass `historico` (already-fetched Mensagem list) as a parameter into `processar_mensagem_rag`. The `chat` view fetches history and passes it in; `knowledge` never needs to import from `chat`.

---

## Build Order (Phase Dependencies)

The build order is a strict dependency graph. Each phase depends on the previous.

```
Phase 1 — Project scaffold
    Docker + settings (base/dev) + PostgreSQL connection verified
    pgvector extension enabled in entrypoint.sh

Phase 2 — Data models + migrations
    accounts: User, PerfilNutricionista, PerfilPaciente (UUID PK)
    chat:     Conversa, Mensagem
    knowledge: Documento, Chunk (VectorField + HnswIndex)
    Requires: Phase 1 (Postgres ready, pgvector extension)

Phase 3 — Authentication
    SimpleJWT config, register endpoint, IsNutricionista/IsPaciente permissions
    Requires: Phase 2 (User model must exist)

Phase 4 — Patient CRUD with isolation
    PacienteListCreateView, PacienteRetrieveUpdateView
    PacienteManager.do_nutricionista(), IsPacienteDoNutricionista
    Tests: nutritionist A cannot read nutritionist B's patients
    Requires: Phase 3 (auth must work to scope by request.user)

Phase 5 — Document ingestion + indexing
    Upload endpoint (POST /api/documentos/)
    indexer.py: text split → embed → bulk_create Chunk
    Celery task: indexar_documento_task
    Requires: Phase 2 (Chunk model with VectorField must exist)

Phase 6 — RAG retrieval + LLM
    retriever.py with CosineDistance ORM query
    prompt_builder.py assembling patient context
    llm_client.py dispatching to Claude/OpenAI
    rag_pipeline.py orchestrating all of the above
    Requires: Phase 5 (chunks must be indexed to test retrieval)

Phase 7 — Chat endpoint
    MensagemCreateView calling processar_mensagem_rag
    Conversa list/create views (patient-scoped)
    End-to-end test: question → RAG → answer → history persisted
    Requires: Phase 6 (full RAG pipeline must work)
```

**Rationale for this order:**
- Auth before CRUD because all patient views need `request.user.perfil_nutricionista`
- Models before everything because migrations must be stable before writing service logic
- Indexing before retrieval because you cannot test semantic search without indexed chunks
- RAG pipeline before the chat endpoint because the endpoint is just HTTP wrapping around the pipeline

---

## Sources

- pgvector-python official README: `VectorField`, `HnswIndex`, `CosineDistance` ORM integration — HIGH confidence
  https://github.com/pgvector/pgvector-python/blob/master/README.md
- LangChain official docs: `OpenAIEmbeddings.embed_documents/embed_query`, `RecursiveCharacterTextSplitter` — HIGH confidence
  https://docs.langchain.com/oss/python/integrations/embeddings/openai
  https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter
- LangChain PGVector docs (referenced to understand why NOT to use it): https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector
- Project's own guia_implementacao.md — design decisions already validated by the team
- LGPD Art. 11 (dados sensíveis de saúde) — legal requirement driving UUID PK and CPF handling

---
*Architecture research for: Django + pgvector + LangChain RAG (NutriChat)*
*Researched: 2026-05-19*
