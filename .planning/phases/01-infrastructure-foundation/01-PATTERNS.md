# Phase 1: Infrastructure Foundation - Pattern Map

**Mapped:** 2026-05-28
**Files analyzed:** 10 (todos criados do zero — repositório greenfield)
**Analogs found:** 0 / 10 (repositório vazio de código; padrões extraídos de CLAUDE.md + RESEARCH.md)

> **Nota sobre projeto greenfield:** O repositório não contém código de aplicação. Não há arquivos análogos para copiar. Esta fase mapeia os **padrões canônicos** que cada arquivo DEVE seguir, extraídos de: CLAUDE.md (autoritativo), 01-RESEARCH.md (padrões verificados), guia_implementacao.md (referência de design) e `.planning/research/ARCHITECTURE.md`.

---

## File Classification

| Arquivo a Criar | Papel | Fluxo de Dados | Análogo Canônico | Qualidade do Match |
|-----------------|-------|----------------|------------------|--------------------|
| `docker-compose.yml` | config | event-driven (startup/shutdown) | RESEARCH.md Pattern 3 | canonical-doc |
| `Dockerfile` | config | build-time | RESEARCH.md Pattern 2 | canonical-doc |
| `entrypoint.sh` | utility | sequential-init | RESEARCH.md Pattern 1 | canonical-doc |
| `nutrihelp_app/pyproject.toml` | config | build-time | RESEARCH.md pyproject.toml completo | canonical-doc |
| `nutrihelp_app/manage.py` | utility | request-response (CLI) | Django standard | framework-standard |
| `nutrihelp_app/control/__init__.py` | config | event-driven | RESEARCH.md Pattern 5 | canonical-doc |
| `nutrihelp_app/control/celery.py` | config | event-driven | RESEARCH.md Pattern 5 | canonical-doc |
| `nutrihelp_app/control/settings.py` | config | CRUD (env → config) | RESEARCH.md Pattern 4 | canonical-doc |
| `nutrihelp_app/control/urls.py` | config | request-response | Django standard | framework-standard |
| `nutrihelp_app/control/wsgi.py` | config | request-response | Django standard | framework-standard |
| `dotenv_files/.env-example` | config | — | RESEARCH.md .env-example completo | canonical-doc |
| `dotenv_files/.env` | config | — | .env-example (gitignored) | gitignored |
| `.gitignore` | config | — | CLAUDE.md + RESEARCH.md | canonical-doc |

---

## Pattern Assignments

### `docker-compose.yml` (config, event-driven)

**Fonte canônica:** RESEARCH.md §Pattern 3 (linhas 356–440) + CLAUDE.md §Docker Configuration

**Regras críticas a seguir:**
- D-05: Seis serviços: `nutrihelp_django`, `nutrihelp_celery`, `nutrihelp_postgres`, `nutrihelp_redis`, `nutrihelp_chromadb`, `nutrihelp_ollama`
- D-06: Ollama é sempre ativo — sem `profiles:`
- D-07: ChromaDB incluído desde Phase 1
- D-08: Redis SEM `ports:` no host; PostgreSQL COM `ports: "3601:5432"`; Django COM `ports: "3600:3600"`

**Estrutura de serviços:**
```yaml
version: "3.9"

services:
  nutrihelp_django:
    build: .
    container_name: nutrihelp_django
    env_file: dotenv_files/.env
    ports:
      - "3600:3600"
    volumes:
      - ./nutrihelp_app:/nutrihelp_app
      - static_files:/nutrihelp_app/staticfiles
    depends_on:
      - nutrihelp_postgres
      - nutrihelp_redis
    networks:
      - nutrihelp_network
    restart: unless-stopped

  nutrihelp_celery:
    build: .
    container_name: nutrihelp_celery
    command: uv run celery -A control worker --loglevel=info
    env_file: dotenv_files/.env
    volumes:
      - ./nutrihelp_app:/nutrihelp_app
    depends_on:
      - nutrihelp_postgres
      - nutrihelp_redis
    networks:
      - nutrihelp_network
    restart: unless-stopped

  nutrihelp_postgres:
    image: pgvector/pgvector:0.8.2-pg17
    container_name: nutrihelp_postgres
    env_file: dotenv_files/.env
    ports:
      - "3601:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - nutrihelp_network
    restart: unless-stopped

  nutrihelp_redis:
    image: redis:7-alpine
    container_name: nutrihelp_redis
    # SEM ports: — Redis é interno apenas (D-08)
    volumes:
      - redis_data:/data
    networks:
      - nutrihelp_network
    restart: unless-stopped

  nutrihelp_chromadb:
    image: chromadb/chroma:0.6.3   # tag semântico estável, NÃO latest
    container_name: nutrihelp_chromadb
    volumes:
      - chroma_data:/chroma/chroma
    networks:
      - nutrihelp_network
    restart: unless-stopped

  nutrihelp_ollama:
    image: ollama/ollama:latest
    container_name: nutrihelp_ollama
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - nutrihelp_network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  chroma_data:
  ollama_data:
  static_files:

networks:
  nutrihelp_network:
    driver: bridge
```

**Anti-padrões a evitar (RESEARCH.md §Anti-Patterns):**
- NUNCA adicionar `ports:` ao serviço `nutrihelp_redis`
- NUNCA usar `chromadb/chroma:latest` — tag de desenvolvimento instável
- Usar volumes NOMEADOS, não bind mounts (`postgres_data:`, não `/data`)

**Decisão discricionária — GPU para Ollama (RESEARCH.md §Open Questions #3):**
Adicionar bloco de GPU ao `nutrihelp_ollama` se RTX 5070 disponível:
```yaml
  nutrihelp_ollama:
    # ... demais configs ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

### `Dockerfile` (config, build-time)

**Fonte canônica:** RESEARCH.md §Pattern 2 (linhas 314–345) + CLAUDE.md §Docker Configuration

**Restrições do CLAUDE.md:**
- Imagem base: `python:3.11-alpine`
- Usuário não-root: `duser`
- Gerenciador de pacotes: `uv` (não pip)
- Working directory: `/nutrihelp_app`

**Padrão completo:**
```dockerfile
FROM python:3.11-alpine

# Dependências de sistema para psycopg2, pdfplumber, Pillow
# pytesseract é instalado como lib Python mas o binário tesseract-ocr
# NÃO é incluído em Phase 1 (OCR fora de escopo — RESEARCH.md §A3)
RUN apk add --no-cache \
    gcc musl-dev postgresql-dev \
    libpq \
    libjpeg-turbo-dev zlib-dev \
    poppler-utils \
    && pip install uv

# Usuário não-root (CLAUDE.md: duser)
RUN addgroup -S dgroup && adduser -S duser -G dgroup

WORKDIR /nutrihelp_app

# Copia manifesto antes do código — aproveita cache de layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copia código e sincroniza projeto completo
COPY . .
RUN uv sync --frozen

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown duser:dgroup /entrypoint.sh

USER duser

ENTRYPOINT ["/entrypoint.sh"]
```

**Anti-padrão crítico (RESEARCH.md §Anti-Patterns):**
- `uv sync --frozen` é obrigatório — omitir `--frozen` permite atualizações silenciosas de deps

---

### `entrypoint.sh` (utility, sequential-init)

**Fonte canônica:** RESEARCH.md §Pattern 1 (linhas 253–306) + CLAUDE.md §Entrypoint

**Sequência obrigatória (ordem importa — RESEARCH.md §Pitfall 2):**
1. Aguarda PostgreSQL aceitar conexões (não apenas abrir porta TCP)
2. Ativa extensão `pgvector` (idempotente — `IF NOT EXISTS`)
3. Roda `migrate`
4. Roda `collectstatic`
5. Inicia `gunicorn`

```bash
#!/bin/sh
set -e  # CRÍTICO — falha imediatamente se qualquer comando falhar (RESEARCH.md §Anti-Patterns)

# Valida SECRET_KEY obrigatória (D-09)
if [ -z "$SECRET_KEY" ]; then
    echo "ERRO: SECRET_KEY não está definida. Configure dotenv_files/.env antes de subir."
    exit 1
fi

# 1. Aguarda PostgreSQL via psycopg2 (conectividade real, não só porta TCP)
echo "Aguardando banco de dados..."
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        port=os.environ['POSTGRES_PORT'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD'],
        dbname=os.environ['POSTGRES_DB'],
    )
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
    echo "Banco indisponível — aguardando 2s..."
    sleep 2
done
echo "Banco disponível."

# 2. Ativa pgvector (DEVE rodar antes de migrate — RESEARCH.md §Pitfall 2)
python -c "
import psycopg2, os
conn = psycopg2.connect(
    host=os.environ['POSTGRES_HOST'],
    port=os.environ['POSTGRES_PORT'],
    user=os.environ['POSTGRES_USER'],
    password=os.environ['POSTGRES_PASSWORD'],
    dbname=os.environ['POSTGRES_DB'],
)
conn.autocommit = True
cur = conn.cursor()
cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
conn.close()
print('Extensão pgvector ativada.')
"

# 3. Migrações
uv run manage.py migrate --noinput

# 4. Static files
uv run manage.py collectstatic --noinput

# 5. Servidor WSGI
exec uv run gunicorn control.wsgi:application \
    --bind 0.0.0.0:3600 \
    --workers 2 \
    --timeout 120
```

**Anti-padrões a evitar:**
- NUNCA omitir `set -e` — sem ele, falha no `migrate` não para o script
- NUNCA usar `nc -z host port` como wait-for-db — verifica porta TCP, não conectividade real do banco
- A validação de `SECRET_KEY` aqui é redundante com `config('SECRET_KEY')` no settings.py, mas serve como feedback imediato no log do container

---

### `nutrihelp_app/pyproject.toml` (config, build-time)

**Fonte canônica:** RESEARCH.md §pyproject.toml completo (linhas 130–178) + CLAUDE.md §Dependency Management

**Regra D-03/D-04:** Todas as dependências do projeto incluídas desde Phase 1. Fases seguintes NÃO modificam este arquivo.

```toml
[project]
name = "nutrihelp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Framework
    "django>=5.2,<6.0",
    "djangorestframework>=3.17,<4.0",
    "djangorestframework-simplejwt>=5.5,<6.0",

    # Database
    "psycopg2-binary>=2.9,<3.0",
    "pgvector>=0.4,<0.5",

    # RAG / LangChain (1.x — imports mudaram em relação ao 0.x)
    "langchain>=1.3,<2.0",
    "langchain-text-splitters>=1.1,<2.0",
    "langchain-openai>=1.2,<2.0",
    "langchain-anthropic>=1.4,<2.0",
    "langchain-community>=0.4,<0.5",

    # LLM SDKs (ambos instalados: embeddings sempre via OpenAI)
    "anthropic>=0.103,<1.0",
    "openai>=2.37,<3.0",

    # Tarefas assíncronas
    "celery>=5.6,<6.0",
    "redis>=7.4,<8.0",

    # Vectorstore local dev
    "chromadb>=0.5,<1.0",

    # Processamento de documentos
    "pdfplumber>=0.11,<0.12",
    "pytesseract>=0.3,<0.4",
    "pillow>=12,<13",

    # Configuração
    "python-decouple>=3.8",

    # Servidor e static files
    "whitenoise>=6.12,<7.0",
    "gunicorn>=26,<27",

    # API docs (Phase 7)
    "drf-spectacular>=0.29,<0.30",
]
```

**Nota sobre LangChain 1.x (RESEARCH.md §State of the Art):**
Fases seguintes DEVEM usar imports 1.x:
```python
# CORRETO (LangChain 1.x)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic

# ERRADO (LangChain 0.x — guia_implementacao.md usa este padrão; IGNORAR)
from langchain.text_splitter import RecursiveCharacterTextSplitter  # removido em 1.x
```

**Geração do uv.lock (RESEARCH.md §Pitfall 3):**
O lockfile DEVE ser commitado. Gerar via:
```bash
docker run --rm -v $(pwd)/nutrihelp_app:/app -w /app python:3.11-alpine \
  sh -c "pip install uv && uv lock"
```

---

### `nutrihelp_app/manage.py` (utility, request-response)

**Fonte canônica:** Django standard — gerado por `django-admin startproject`

**Padrão Django 5.2 (configuração de módulo):**
```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

**Nota CLAUDE.md:** Todos os comandos Django dentro do container usam `uv run manage.py` — nunca `python manage.py` direto.

---

### `nutrihelp_app/control/celery.py` (config, event-driven)

**Fonte canônica:** RESEARCH.md §Pattern 5 (linhas 497–509) + CLAUDE.md §Running Celery Workers

**Regra do RESEARCH.md §Pitfall 5:** O nome `Celery('nutrihelp')` DEVE corresponder ao projeto, não ao módulo de configuração `control`. O `DJANGO_SETTINGS_MODULE` DEVE apontar para `control.settings`.

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control.settings')

app = Celery('nutrihelp')

# Namespace 'CELERY' — todas as configs no settings.py prefixadas com CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover encontra tasks.py em todos os apps em INSTALLED_APPS
app.autodiscover_tasks()
```

**Conflito resolvido (RESEARCH.md §Conflicts table):**
- `guia_implementacao.md` usa `config/celery.py` com `Celery('nutrichat')` — IGNORAR
- `CLAUDE.md` usa `control/celery.py` — SEGUIR
- Nome do app Celery: `'nutrihelp'` (não `'nutrichat'`, não `'control'`)

---

### `nutrihelp_app/control/__init__.py` (config, event-driven)

**Fonte canônica:** RESEARCH.md §Pattern 5 (linhas 507–509)

**Propósito:** Garante que o app Celery é carregado quando Django inicia — necessário para que `@shared_task` funcione corretamente.

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

---

### `nutrihelp_app/control/settings.py` (config, CRUD env→config)

**Fonte canônica:** RESEARCH.md §Pattern 4 (linhas 446–493) + CLAUDE.md §Environment Variables

**Regras críticas:**
- D-09: `SECRET_KEY = config('SECRET_KEY')` SEM default — falha imediatamente se ausente
- Whitenoise DEVE estar logo após `SecurityMiddleware` no MIDDLEWARE
- `rest_framework_simplejwt.token_blacklist` em INSTALLED_APPS (necessário para logout/rotation nas fases seguintes)
- CLAUDE.md: access token 5min, refresh 1 dia (valores mais conservadores que o guia)

```python
from decouple import config, Csv
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# CRÍTICO: sem default — container falha com mensagem clara (D-09)
SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:3600', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # DRF
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    # API docs (usada na Phase 7, mas app registrada desde Phase 1)
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # DEVE ficar logo após SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'control.urls'

WSGI_APPLICATION = 'control.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST', default='nutrihelp_postgres'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    }
}

# Celery — namespace CELERY_ no settings (pattern de RESEARCH.md)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://nutrihelp_redis:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://nutrihelp_redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'

# JWT — valores do CLAUDE.md (mais conservadores que o guia)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# DRF — preparado para fases seguintes
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Static files (whitenoise)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Variáveis de LLM (usadas a partir da Phase 5)
LLM_PROVIDER = config('LLM_PROVIDER', default='ollama')
OLLAMA_BASE_URL = config('OLLAMA_BASE_URL', default='http://nutrihelp_ollama:11434')
OLLAMA_MODEL = config('OLLAMA_MODEL', default='llama3.1:8b-instruct-q4_K_M')
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Vector store (usado a partir da Phase 4/5)
VECTOR_STORE = config('VECTOR_STORE', default='chroma')
CHROMA_HOST = config('CHROMA_HOST', default='nutrihelp_chromadb')
CHROMA_PORT = config('CHROMA_PORT', default=8000, cast=int)

# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

**Conflito resolvido (RESEARCH.md §Conflicts table):**
- `guia_implementacao.md` usa `config/settings/base.py` (split) — IGNORAR
- `CLAUDE.md` usa `control/settings.py` (único) — SEGUIR

**Anti-padrão crítico (RESEARCH.md §Anti-Patterns):**
```python
# ERRADO — nunca adicionar default à SECRET_KEY
SECRET_KEY = config('SECRET_KEY', default='minha-chave-insegura')

# CORRETO — falha imediatamente se ausente
SECRET_KEY = config('SECRET_KEY')
```

---

### `nutrihelp_app/control/urls.py` (config, request-response)

**Fonte canônica:** Django standard + CLAUDE.md §API Structure

**Phase 1 inclui apenas admin.** Fases seguintes adicionam os prefixos de API:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Fases seguintes adicionarão:
    # path('api/accounts/', include('accounts.urls')),
    # path('api/patients/', include('patients.urls')),
    # path('api/documents/', include('documents.urls')),
    # path('api/chat/', include('chat.urls')),
]
```

**Nota CLAUDE.md §API Structure:** os prefixos estão documentados — respeitar exatamente ao adicionar nas fases seguintes.

---

### `nutrihelp_app/control/wsgi.py` (config, request-response)

**Fonte canônica:** Django standard — gerado por `django-admin startproject`

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control.settings')

application = get_wsgi_application()
```

---

### `dotenv_files/.env-example` (config, documentação)

**Fonte canônica:** RESEARCH.md §.env-example completo (linhas 514–548) + CLAUDE.md §Environment Variables

```bash
# Django
SECRET_KEY=troque-por-uma-chave-segura-e-longa
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:3600

# Banco de dados
DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=nutrihelp
POSTGRES_USER=nutrihelp_user
POSTGRES_PASSWORD=trocar-senha-segura
POSTGRES_HOST=nutrihelp_postgres
POSTGRES_PORT=5432

# Redis (broker Celery) — interno, sem porta exposta no host
REDIS_URL=redis://nutrihelp_redis:6379/0

# LLM
LLM_PROVIDER=ollama
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
# NOTA: OPENAI_API_KEY é obrigatória para embeddings mesmo quando LLM_PROVIDER=anthropic
# (RESEARCH.md §Gap 5 / STACK.md §Gap 5)

# Ollama (dev local — modelo deve ser baixado manualmente após docker compose up)
# docker exec nutrihelp_ollama ollama pull llama3.1:8b-instruct-q4_K_M
OLLAMA_BASE_URL=http://nutrihelp_ollama:11434
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M

# Vector store
VECTOR_STORE=chroma
CHROMA_HOST=nutrihelp_chromadb
CHROMA_PORT=8000

# OCR (binário tesseract não incluído no Docker em Phase 1)
OCR_PROVIDER=tesseract
```

---

### `.gitignore` (config)

**Fonte canônica:** CLAUDE.md + RESEARCH.md §Existing Project State (linhas 830–836)

**Regra D-09:** `dotenv_files/.env` DEVE estar no `.gitignore`.
**Nota RESEARCH.md:** `uv.lock` DEVE ser commitado (não no .gitignore).

```gitignore
# Secrets — nunca commitar
dotenv_files/.env

# Static files coletados
nutrihelp_app/staticfiles/

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Virtual environments
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
.dockerignore

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# uv.lock NÃO está aqui — DEVE ser commitado para builds reproduzíveis
# (RESEARCH.md §Pitfall 3)
```

---

## Shared Patterns

### Padrão: Carregamento de Variáveis de Ambiente

**Fonte:** RESEARCH.md §Don't Hand-Roll + STACK.md §Configuration
**Aplicar a:** `control/settings.py` — único arquivo que carrega `.env` diretamente

```python
from decouple import config, Csv

# Variável obrigatória — falha se ausente:
SECRET_KEY = config('SECRET_KEY')

# Variável com default e cast:
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

# Variável com default de string:
POSTGRES_HOST = config('POSTGRES_HOST', default='nutrihelp_postgres')
```

---

### Padrão: Nomenclatura de Containers e Serviços

**Fonte:** CLAUDE.md §Docker Configuration (autoritativo)
**Aplicar a:** `docker-compose.yml` — todos os `container_name:` e `depends_on:`

| Container | Nome canônico |
|-----------|--------------|
| Django web | `nutrihelp_django` |
| Celery worker | `nutrihelp_celery` |
| PostgreSQL | `nutrihelp_postgres` |
| Redis | `nutrihelp_redis` |
| ChromaDB | `nutrihelp_chromadb` |
| Ollama | `nutrihelp_ollama` |

---

### Padrão: Comandos Django no Container

**Fonte:** CLAUDE.md §Running Django Commands
**Aplicar a:** Qualquer documentação, scripts ou CI que execute comandos Django

```bash
# Formato obrigatório:
docker exec -it nutrihelp_django uv run manage.py <comando>

# ERRADO — nunca:
docker exec -it nutrihelp_django python manage.py <comando>
docker exec -it nutrihelp_django manage.py <comando>
```

---

### Padrão: Isolamento de Dados (preparação para fases seguintes)

**Fonte:** CLAUDE.md §Data Isolation Pattern + ARCHITECTURE.md §Multi-Tenancy
**Aplicar a:** Toda view com acesso a pacientes (Phase 3+)

Este padrão NÃO é implementado na Phase 1, mas deve ser planejado desde o início:

```python
# CORRETO — sempre escopo por nutricionista autenticado
Patient.objects.filter(nutritionist=request.user)

# ERRADO — NUNCA em código de produção
Patient.objects.all()
```

---

### Padrão: Sequência de Inicialização do Container

**Fonte:** RESEARCH.md §Pattern 1 + §Pitfall 1 + §Pitfall 2
**Aplicar a:** `entrypoint.sh` e qualquer script de inicialização futuro

Ordem obrigatória e razões:
1. **Validar SECRET_KEY** → falha rápida, mensagem clara
2. **wait-for-db** → psycopg2.connect em loop, não `nc` nem `depends_on` sozinho
3. **CREATE EXTENSION IF NOT EXISTS vector** → antes de migrate (o VectorField precisa do tipo)
4. **migrate** → antes de collectstatic (migrations podem afetar static)
5. **collectstatic** → antes de gunicorn (whitenoise precisa dos arquivos)
6. **exec gunicorn** → `exec` substitui o processo shell (PID 1 limpo para sinais Docker)

---

## No Analog Found

**Todos os arquivos desta fase** não têm análogo no repositório (greenfield). A tabela abaixo indica a fonte canônica alternativa usada para cada um:

| Arquivo | Fonte de Padrão | Confiança |
|---------|-----------------|-----------|
| `docker-compose.yml` | RESEARCH.md §Pattern 3 | HIGH — padrão verificado |
| `Dockerfile` | RESEARCH.md §Pattern 2 | HIGH — padrão verificado |
| `entrypoint.sh` | RESEARCH.md §Pattern 1 | HIGH — padrão verificado |
| `nutrihelp_app/pyproject.toml` | RESEARCH.md §pyproject.toml completo | HIGH — versões verificadas via PyPI 2026-05-28 |
| `nutrihelp_app/manage.py` | Django 5.2 framework standard | HIGH — template padrão do framework |
| `nutrihelp_app/control/celery.py` | RESEARCH.md §Pattern 5 | HIGH — padrão oficial Django-Celery |
| `nutrihelp_app/control/__init__.py` | RESEARCH.md §Pattern 5 | HIGH — boilerplate obrigatório |
| `nutrihelp_app/control/settings.py` | RESEARCH.md §Pattern 4 + CLAUDE.md | HIGH — padrão verificado |
| `nutrihelp_app/control/urls.py` | Django 5.2 framework standard | HIGH — template padrão |
| `nutrihelp_app/control/wsgi.py` | Django 5.2 framework standard | HIGH — template padrão |
| `dotenv_files/.env-example` | RESEARCH.md §.env-example | HIGH — todas as vars documentadas |
| `.gitignore` | CLAUDE.md D-09 + RESEARCH.md | HIGH — regras explícitas |

---

## Conflicts Resolved

Conflitos identificados entre `guia_implementacao.md` e `CLAUDE.md` (CLAUDE.md sempre vence):

| Ponto de Conflito | guia_implementacao.md | CLAUDE.md (usar) |
|-------------------|-----------------------|------------------|
| Diretório do projeto | `nutrichat/` | `nutrihelp_app/` |
| Módulo de configuração | `config/` | `control/` |
| Settings | split `settings/base.py` | único `settings.py` |
| Gerenciador de deps | `pip` + `requirements/` | `uv` + `pyproject.toml` |
| Import text splitter | `from langchain.text_splitter` (0.x) | `from langchain_text_splitters` (1.x) |
| Access token lifetime | 1 hora | 5 minutos |
| Refresh token lifetime | 7 dias | 1 dia |

---

## Metadata

**Escopo de busca de análogos:** repositório inteiro — nenhum arquivo de código encontrado
**Arquivos escaneados:** 13 (CLAUDE.md, guia_implementacao.md, README.md, .claude/skills/*, .planning/**)
**Data do mapeamento:** 2026-05-28
**Fontes primárias:** CLAUDE.md (autoritativo), 01-RESEARCH.md (HIGH confidence), ARCHITECTURE.md, STACK.md
