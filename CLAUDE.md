# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NutriHelp** is a Django REST Framework SaaS platform that connects nutritionists and patients through an AI assistant powered by RAG (Retrieval-Augmented Generation). Nutritionists manage patient profiles with clinical details, and patients interact with a personalized AI assistant for dietary guidance.

The project uses PostgreSQL + pgvector for semantic search, LangChain as the RAG engine, ChromaDB (local dev) or pgvector (production) as the vector store, and Celery + Redis for async task processing. Authentication is JWT-based via SimpleJWT.

**Two user roles:**
- **Nutritionist (Nutricionista):** Creates and manages patient profiles, uploads documents, configures dietary plans.
- **Patient (Paciente):** Consults their dietary plan and interacts with the AI assistant.

> ⚠️ **Data isolation is non-negotiable:** every query must be scoped to the authenticated nutritionist's patients. Never expose cross-tenant data.

## Development Setup

### Environment Configuration

1. Copy the environment template:
   ```bash
   cp dotenv_files/.env-example dotenv_files/.env
   ```

2. Start the application with Docker:
   ```bash
   docker compose up
   ```

The application runs on port **3600**, PostgreSQL on port **3601**, Redis on port **6379**.

### Running Django Commands

All Django commands must be run through `uv` inside the Django container:

```bash
docker exec -it nutrihelp_django uv run manage.py <command>
```

Common commands:
- Create migrations: `docker exec -it nutrihelp_django uv run manage.py makemigrations`
- Apply migrations: `docker exec -it nutrihelp_django uv run manage.py migrate`
- Create superuser: `docker exec -it nutrihelp_django uv run manage.py createsuperuser`
- Run shell: `docker exec -it nutrihelp_django uv run manage.py shell`
- Run tests: `docker exec -it nutrihelp_django uv run manage.py test`
- Run specific test: `docker exec -it nutrihelp_django uv run manage.py test accounts.tests.model_test.test_custom_user_model`
- Collect static files: `docker exec -it nutrihelp_django uv run manage.py collectstatic --noinput`

### Running Celery Workers

```bash
docker exec -it nutrihelp_celery uv run celery -A control worker --loglevel=info
```

## Project Structure

### Application Architecture

The Django project is located in `nutrihelp_app/` with the main configuration in `control/`:

- **control/**: Main Django project configuration
  - `settings.py`: Core settings with environment-based configuration
  - `urls.py`: Root URL configuration

- **accounts/**: Custom user authentication and management
  - Custom User model extending `AbstractUser` with a `role` field (`nutritionist` | `patient`)
  - Email-based authentication
  - JWT token authentication via `djangorestframework-simplejwt`
  - Separate profile models: `PerfilNutricionista`, `PerfilPaciente`
  - Custom permission decorators per role

- **patients/**: Patient profile management (scoped to authenticated nutritionist)
  - Clinical fields: dietary type, health conditions, bariatric status, macros, restrictions
  - All querysets filtered by `nutritionist=request.user`

- **rag/**: RAG engine and AI assistant
  - LangChain pipeline integration
  - Vector store abstraction (ChromaDB local / pgvector production)
  - Unified LLM interface (Ollama local / Claude or GPT-4o production)
  - Document ingestion: pdfplumber (text PDFs), Tesseract OCR (scanned), cloud Vision APIs (complex)

- **documents/**: Document upload and processing pipeline
  - Async processing via Celery tasks
  - Supports PDF, images, and scanned documents

- **chat/**: Patient-facing AI assistant
  - Conversation history per patient
  - RAG-augmented responses

### Key Architectural Patterns

**Custom User Model**: `accounts.models.User`
- Extends `AbstractUser` with a `role` field (`nutritionist` | `patient`)
- Email-based authentication
- Separate profile models linked via OneToOne
- Located in: `nutrihelp_app/accounts/models/`

**Authentication System**:
- JWT tokens via SimpleJWT
- Access token: 5 minutes | Refresh token: 1 day
- Token rotation enabled with blacklisting
- Custom permission decorators: `@nutritionist_required`, `@patient_required`

**Data Isolation Pattern**:
- All patient querysets must be scoped: `Patient.objects.filter(nutritionist=request.user)`
- Never use unscoped `Patient.objects.all()` in nutritionist-facing views
- Enforced at the queryset level, not just the UI

**Unified LLM Interface**:
- A single Django-side abstraction switches between Ollama (local dev) and cloud APIs (production)
- No environment-specific code outside this interface — all views and RAG chains call the same method
- Configured via environment variable `LLM_PROVIDER` (`ollama` | `claude` | `openai`)

**RAG Pipeline**:
1. Document ingested → chunked → embedded → stored in vector DB
2. Patient query → semantic search → top-k chunks retrieved
3. Chunks + patient context + query → LLM → response

**Code Organization Pattern**:
- Models split into separate files within `models/` directory
- Views organized in `views/` directory by functionality
- Serializers in nested `api/serializers/` structure
- Tests organized by type: `model_test/`, `serializer_test/`, `view_test/`
- Celery tasks in `tasks.py` per app

**API Structure**:
- All account endpoints: `/api/accounts/`
  - Registration: `POST /api/accounts/register/`
  - Login: `POST /api/accounts/token/`
  - Token refresh: `POST /api/accounts/token/refresh/`
- Patient management (nutritionist only): `/api/patients/`
- Document upload: `/api/documents/`
- Chat (patient only): `/api/chat/`

### Environment Variables

Critical settings loaded from `.env`:
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (`0` or `1`)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `CSRF_TRUSTED_ORIGINS`: Comma-separated list of trusted origins
- Database: `DB_ENGINE`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- Redis: `REDIS_URL`
- LLM: `LLM_PROVIDER` (`ollama` | `claude` | `openai`), `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- Ollama: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- Vector store: `VECTOR_STORE` (`chroma` | `pgvector`), `CHROMA_HOST`, `CHROMA_PORT`
- OCR: `OCR_PROVIDER` (`tesseract` | `claude` | `openai`)

### Docker Configuration

- **Container name**: `nutrihelp_django`
- **Base image**: Python 3.11-alpine with uv package manager
- **Working directory**: `/nutrihelp_app`
- **User**: Non-root user `duser` for security
- **Dependencies**: Managed via uv with `pyproject.toml` and `uv.lock`
- **Entrypoint**: `entrypoint.sh` handles database wait, pgvector extension setup, migrations, collectstatic, and server startup
- **Additional containers**: `nutrihelp_celery` (worker), `nutrihelp_redis`, `nutrihelp_chromadb`

### Dependency Management

This project uses **uv** (not pip) for Python dependency management:
- Dependencies defined in `nutrihelp_app/pyproject.toml`
- Lock file: `nutrihelp_app/uv.lock`
- To add dependencies: modify `pyproject.toml` and run `uv lock`

Key dependencies:
- `djangorestframework`, `djangorestframework-simplejwt`
- `langchain`, `langchain-community`, `langchain-anthropic`, `langchain-openai`
- `chromadb`, `pgvector`, `psycopg2-binary`
- `celery`, `redis`
- `pdfplumber`, `pytesseract`, `pillow`

## Testing

Tests are located per app in `tests/` organized by:
- `model_test/`: Model and queryset tests (including isolation assertions)
- `serializer_test/`: Serializer tests
- `view_test/`: View/API endpoint tests
- `utils_test/`: Utility and permission tests

Run all tests:
```bash
docker exec -it nutrihelp_django uv run manage.py test
```

Run specific app tests:
```bash
docker exec -it nutrihelp_django uv run manage.py test accounts
docker exec -it nutrihelp_django uv run manage.py test patients
docker exec -it nutrihelp_django uv run manage.py test rag
```

## Important Notes

- **Data isolation is enforced at the queryset level** — always scope patient queries to `request.user`
- All Django management commands must be prefixed with `uv run`
- The unified LLM interface must be used for all AI calls — never instantiate LLM clients directly in views or tasks
- The RAG pipeline was chosen over fine-tuning specifically to minimize hallucinations in a clinical nutrition context
- LGPD compliance (Brazilian data protection law) applies — patient health data is sensitive and must be handled accordingly
- Static files are collected to `/nutrihelp_app/staticfiles`
- The entrypoint script automatically enables the `pgvector` extension, runs migrations, and collectstatic on startup
- Local dev runs Ollama with Llama 3.1 8B (Q4_K_M quantization) on RTX 5070 12GB; production uses cloud LLM APIs
