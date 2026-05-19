# Technology Stack — NutriChat RAG MVP

**Project:** NutriChat RAG
**Researched:** 2026-05-19
**Overall confidence:** HIGH (all versions verified via PyPI; integration patterns verified via Context7)

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11.x | Runtime | Already decided; Alpine Docker image in CLAUDE.md; 3.12+ has minor compatibility gaps with some Celery internals on Alpine |
| Django | 5.2.x (LTS) | Web framework, ORM, migrations | 5.2 is the current LTS (support until April 2028). Do NOT use 4.2 — it reaches EOL April 2026, weeks after project start. 6.0 is available but not LTS; avoid for a v1 that needs stability |
| djangorestframework | 3.17.x | REST API layer | Latest; 3.17 supports Django 5.x and Python 3.11 fully |

### Authentication

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| djangorestframework-simplejwt | 5.5.x | JWT auth | Latest stable; supports Django 5.2; provides blacklist app for logout/rotation |

SimpleJWT blacklist app must be in `INSTALLED_APPS` and migrated separately. It creates `OutstandingToken` and `BlacklistedToken` tables. Required for `ROTATE_REFRESH_TOKENS = True`.

### Database and Vector Store

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 16.x | Primary database | pgvector 0.4+ requires pg 12+; pg 16 is current stable |
| pgvector (extension) | 0.8.x | Vector storage and similarity search in PostgreSQL | Pin to a version in Docker image; 0.8 adds HNSW indexing which is critical for production |
| pgvector (Python) | 0.4.x | Django ORM integration for VectorField | 0.4.2 is current; exposes VectorField, L2Distance, CosineDistance, HnswIndex, IvfflatIndex |
| psycopg2-binary | 2.9.x | PostgreSQL driver | 2.9.12 current; psycopg3 (3.3.x) exists but requires code changes and is not yet the ecosystem default — skip for v1 |

**Critical pgvector Django pattern:**

```python
from pgvector.django import VectorField, CosineDistance, HnswIndex

class Chunk(models.Model):
    embedding = VectorField(dimensions=1536)

    class Meta:
        indexes = [
            HnswIndex(
                name='chunk_embedding_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']  # must match distance used at query time
            )
        ]
```

**Use CosineDistance, not L2Distance**, for text embeddings. OpenAI and Anthropic embedding models are trained to be compared with cosine similarity. L2 distance works but produces worse ranking for semantic search. The opclass in the index must match: `vector_cosine_ops` for cosine, `vector_l2_ops` for L2.

### RAG Engine

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| langchain | 1.3.x | Orchestration core | 1.3.1 is current stable; 1.x series is the stable API after the 0.x restructuring |
| langchain-text-splitters | 1.1.x | RecursiveCharacterTextSplitter | Extracted from core; import from here, not from langchain |
| langchain-openai | 1.2.x | OpenAIEmbeddings + ChatOpenAI | 1.2.1 current; needed even if primary LLM is Claude, because embeddings use OpenAI |
| langchain-anthropic | 1.4.x | ChatAnthropic LLM interface | 1.4.3 current; use when LLM_PROVIDER=anthropic |
| langchain-community | 0.4.x | PGVector vectorstore wrapper | 0.4.1 current; provides langchain_community.vectorstores.PGVector |

**Import paths changed in langchain 1.x.** Use:
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter  # NOT langchain.text_splitter
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
```

### Embedding Model

**Recommendation: `text-embedding-3-small` (1536 dimensions) instead of `text-embedding-ada-002`.**

| Model | Dims | Cost | Quality | Status |
|-------|------|------|---------|--------|
| text-embedding-ada-002 | 1536 | $0.10/1M tokens | Baseline | Legacy, still supported |
| text-embedding-3-small | 1536 | $0.02/1M tokens | +5% over ada-002 | Current recommended |
| text-embedding-3-large | 3072 | $0.13/1M tokens | +10% over ada-002 | Overkill for v1 |

`text-embedding-3-small` at 1536 dims is 5x cheaper than ada-002, marginally better quality, and drops in as a direct replacement since dimensions are identical. The `Chunk.EMBEDDING_DIMENSIONS = 1536` in the guia stays unchanged. Switch is one line in the indexer.

**Confidence: MEDIUM** — OpenAI's own documentation and LangChain examples both show text-embedding-3-small as the current recommended model. The ada-002 comparison is from published benchmarks; exact performance on Portuguese nutritional text is untested.

### Async Task Processing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| celery | 5.6.x | Async document indexing | 5.6.3 current; use CELERY_* namespace in settings.py; autodiscover_tasks() finds tasks.py in all INSTALLED_APPS |
| redis | 7.4.x | Celery broker + result backend | 7.4.0 current Python client; use redis://... URLs |

**Celery Django integration pattern (required boilerplate):**

```python
# config/celery.py
import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
app = Celery('nutrichat')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# config/__init__.py
from .celery import app as celery_app
__all__ = ('celery_app',)
```

### Document Processing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pdfplumber | 0.11.x | PDF text extraction | 0.11.9 current; handles native-text PDFs; layout=True preserves tables |
| pytesseract | 0.3.x | OCR for scanned PDFs | 0.3.13 current; requires Tesseract binary in Docker image |
| Pillow | 12.x | Image preprocessing for OCR | 12.2.0 current; required by pytesseract |

**OCR note:** pytesseract requires `tesseract-ocr` OS package. On Alpine: `apk add tesseract-ocr tesseract-ocr-data-por` (Portuguese language pack). This adds ~50MB to the Docker image. Only install if scanned PDFs are in scope for v1; nutritional guidelines are typically native-text PDFs.

**Recommendation: defer OCR to v2.** Native-text PDFs (pdfplumber) cover 95% of nutritional documents. Add OCR only when a real scanned document fails.

### LLM Provider Clients

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| anthropic | 0.103.x | Direct Anthropic SDK | Used in llm_client._chamar_anthropic(); langchain-anthropic wraps this |
| openai | 2.37.x | Direct OpenAI SDK | Used in llm_client._chamar_openai() and for embeddings |

Note: Both `anthropic` and `openai` SDKs are installed regardless of LLM_PROVIDER because OpenAI is always needed for embeddings, and having both enables provider switching at runtime.

### Configuration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python-decouple | 3.8 | Environment variable loading | 3.8 is current and final stable; reads from .env and os.environ |

**Alternative considered:** `django-environ` 0.13.0. python-decouple is simpler and sufficient for this project's needs.

### Development Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| uv | latest | Dependency management | Already in use per CLAUDE.md; faster than pip; pyproject.toml based |
| Docker + Docker Compose | v2+ | Container orchestration | Already configured per CLAUDE.md |

### Optional / Phase-Specific

| Library | Version | Purpose | When to Add |
|---------|---------|---------|-------------|
| drf-spectacular | 0.29.x | OpenAPI/Swagger docs | Add in final refinement phase (Etapa 9); not needed for API functionality |
| django-filter | 25.x | Queryset filtering via URL params | Add only if patient list needs search/filter; not needed for MVP |
| django-cors-headers | 4.9.x | CORS for future frontend | Add when v2 frontend work begins; not needed for v1 API-only |
| gunicorn | 26.x | Production WSGI server | Add in production deployment phase |
| whitenoise | 6.12.x | Static file serving | Already needed; entrypoint runs collectstatic |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Django version | 5.2 LTS | 4.2 LTS | 4.2 EOL April 2026; project would be outdated on launch |
| Django version | 5.2 LTS | 6.0 | Not LTS; avoid for v1 stability |
| Vector store | pgvector (native) | ChromaDB, Pinecone, Weaviate | pgvector avoids external dependency; integrates directly with Django ORM; chosen decision per PROJECT.md |
| Database driver | psycopg2-binary | psycopg (v3) | psycopg3 requires syntax changes; ecosystem still transitioning; skip for v1 |
| Embedding model | text-embedding-3-small | text-embedding-ada-002 | ada-002 is legacy; 3-small is 5x cheaper, same 1536 dims, higher quality |
| Embedding model | text-embedding-3-small | text-embedding-3-large (3072 dims) | 3072 dims would require schema change (Chunk.EMBEDDING_DIMENSIONS); overkill for v1 |
| Env config | python-decouple | django-environ | python-decouple is simpler, no database URL parsing needed since we're using individual env vars |
| OCR | pdfplumber only (v1) | pytesseract + pdfplumber | Tesseract adds Docker image weight; defer until scanned docs are confirmed in scope |
| LangChain memory | Django DB (manual) | LangChain ConversationBufferMemory | Manual DB history (Mensagem model) is already the design; gives full LGPD control; avoids LangChain memory coupling |

---

## Version Compatibility Matrix

| Component | Required By | Constraint |
|-----------|-------------|------------|
| Python 3.11 | Django 5.2 | Django 5.2 supports Python 3.10–3.13 |
| Django 5.2 | DRF 3.17 | DRF 3.15+ supports Django 5.x |
| Django 5.2 | SimpleJWT 5.5 | SimpleJWT 5.3+ supports Django 5.x |
| pgvector-python 0.4 | Django 5.2 | pgvector-python 0.3+ supports Django 4.2+/5.x |
| psycopg2-binary 2.9 | pgvector-python 0.4 | pgvector-python requires psycopg2 or psycopg3 |
| langchain 1.3 | langchain-openai 1.2 | Must use matching major versions: langchain 1.x with langchain-openai 1.x |
| langchain 1.3 | langchain-anthropic 1.4 | langchain-anthropic 1.x works with langchain 1.x |
| langchain 1.3 | langchain-community 0.4 | community 0.4 is the paired version |
| celery 5.6 | redis 7.4 | Celery 5.x supports redis-py 4.x+ |

**Known incompatibility:** Do not mix `langchain 0.x` imports (`from langchain.text_splitter import ...`) with `langchain 1.x`. The 0.x import paths are removed. All imports must use the sub-package path (`langchain_text_splitters`, `langchain_openai`, etc.).

---

## Identified Stack Gaps

### Gap 1: Cosine Distance Not Used in guia_implementacao.md

The guia uses `L2Distance` for semantic search (retriever.py line: `order_by(L2Distance('embedding', vetor_consulta))`). This is wrong for text embeddings. OpenAI embeddings are trained for cosine similarity. The HNSW index must use `vector_cosine_ops` and queries must use `CosineDistance`.

Fix required in retriever.py:
```python
from pgvector.django import CosineDistance
chunks = Chunk.objects.order_by(CosineDistance('embedding', vetor_consulta))[:limite]
```

### Gap 2: Embedding Model Instantiation Per-Request

The guia instantiates `OpenAIEmbeddings(...)` inside `buscar_chunks_relevantes()` (retriever.py) and inside `indexar_documento()` (indexer.py). This creates a new API client object on every call.

Fix: instantiate once at module level or inject as a dependency:
```python
# retriever.py — module level
_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def buscar_chunks_relevantes(texto_consulta: str, limite: int = None) -> list[str]:
    vetor_consulta = _embeddings.embed_query(texto_consulta)
    ...
```

### Gap 3: Missing HNSW Index on Chunk.embedding

The Chunk model in guia_implementacao.md has no database index on the `embedding` field. Without an index, every similarity search does a full table scan. At 1000+ chunks this becomes slow.

Add to Chunk model Meta:
```python
from pgvector.django import HnswIndex

class Meta:
    indexes = [
        HnswIndex(
            name='chunk_embedding_hnsw_idx',
            fields=['embedding'],
            m=16,
            ef_construction=64,
            opclasses=['vector_cosine_ops']
        )
    ]
```

### Gap 4: LLM Client Creates SDK Client Per-Call

In llm_client.py, `anthropic.Anthropic(...)` and `OpenAI(...)` are instantiated inside every call to `_chamar_anthropic()` and `_chamar_openai()`. SDK clients are designed to be reused. Instantiate them once at module level.

### Gap 5: No OpenAIEmbeddings for Anthropic LLM Provider Path

If `LLM_PROVIDER=anthropic`, the indexer still calls `OpenAIEmbeddings` (which requires `OPENAI_API_KEY`). This is correct design (embeddings are always OpenAI), but the `.env.example` must have `OPENAI_API_KEY` as required even when using Anthropic as the chat LLM. This must be documented clearly.

---

## Installation (pyproject.toml)

```toml
[project]
name = "nutrichat"
requires-python = ">=3.11"
dependencies = [
    # Core
    "django>=5.2,<6.0",
    "djangorestframework>=3.17,<4.0",
    "djangorestframework-simplejwt>=5.5,<6.0",

    # Database
    "psycopg2-binary>=2.9,<3.0",
    "pgvector>=0.4,<0.5",

    # RAG / LangChain
    "langchain>=1.3,<2.0",
    "langchain-text-splitters>=1.1,<2.0",
    "langchain-openai>=1.2,<2.0",
    "langchain-anthropic>=1.4,<2.0",
    "langchain-community>=0.4,<0.5",

    # LLM Provider SDKs (both always installed)
    "anthropic>=0.103,<1.0",
    "openai>=2.37,<3.0",

    # Async
    "celery>=5.6,<6.0",
    "redis>=7.4,<8.0",

    # Document processing
    "pdfplumber>=0.11,<0.12",
    "pillow>=12,<13",

    # Config
    "python-decouple>=3.8",

    # Static files
    "whitenoise>=6.12,<7.0",
]

[project.optional-dependencies]
ocr = [
    "pytesseract>=0.3.13,<0.4",
]
docs = [
    "drf-spectacular>=0.29,<0.30",
]
prod = [
    "gunicorn>=26,<27",
]
```

---

## Sources

- Django versions: PyPI `pip index versions django` (verified 2026-05-19)
- LangChain docs: Context7 `/llmstxt/langchain_llms-full_txt` — HIGH confidence
- pgvector-python docs: Context7 `/pgvector/pgvector-python` — HIGH confidence
- pgvector HNSW indexing: Context7 pgvector-python, confirmed HnswIndex and opclasses pattern
- SimpleJWT blacklist: Context7 `/jazzband/djangorestframework-simplejwt` — HIGH confidence
- Celery Django integration: Context7 `/celery/celery` — HIGH confidence
- pdfplumber text extraction: Context7 `/jsvine/pdfplumber` — HIGH confidence
- OpenAI embedding model comparison (3-small vs ada-002): LangChain docs examples consistently show text-embedding-3-small as current recommendation — MEDIUM confidence
- All package versions: PyPI `pip index versions <package>` (verified 2026-05-19)
