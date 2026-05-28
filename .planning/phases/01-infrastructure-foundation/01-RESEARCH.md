# Phase 1: Infrastructure Foundation - Research

**Researched:** 2026-05-28
**Domain:** Docker Compose + Django scaffold + uv + PostgreSQL/pgvector + Redis + Celery + ChromaDB + Ollama
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 1 cria apenas o núcleo Django: `manage.py`, `control/settings.py`, `control/urls.py`, `control/wsgi.py`, `pyproject.toml`. Nenhum app de negócio é criado nesta fase.
- **D-02:** Apps (`accounts/`, `patients/`, `rag/`, `documents/`, `chat/`) são criados nas fases seguintes.
- **D-03:** `pyproject.toml` inclui **todas as dependências do projeto** desde a Phase 1 — `uv.lock` completo gerado de uma vez.
- **D-04:** Dependências: `django`, `djangorestframework`, `djangorestframework-simplejwt`, `psycopg2-binary`, `pgvector`, `langchain`, `langchain-community`, `langchain-anthropic`, `langchain-openai`, `chromadb`, `celery`, `redis`, `pdfplumber`, `pytesseract`, `pillow`, `drf-spectacular`.
- **D-05:** Todos os serviços do stack incluídos na Phase 1: `nutrihelp_django`, `nutrihelp_celery`, `nutrihelp_redis`, `nutrihelp_chromadb`, PostgreSQL/pgvector e Ollama.
- **D-06:** Ollama é **sempre ativo** (sem profile opcional). INFRA-01 exige o stack completo com Ollama.
- **D-07:** ChromaDB incluído na Phase 1.
- **D-08:** PostgreSQL e Redis ficam **apenas na rede interna Docker** — sem `ports:` expostos no host para Redis.
- **D-09:** `dotenv_files/.env` no `.gitignore`. `dotenv_files/.env-example` com placeholders. Entrypoint falha com mensagem clara se `SECRET_KEY` não estiver definida.
- **D-10:** Segurança avançada (pentest, SAST, rate limiting, headers) é responsabilidade da Phase 7.

### Claude's Discretion

- Estratégia de healthcheck dos containers (entrypoint wait-for-db vs Docker HEALTHCHECK formal) — Claude decide a abordagem mais simples que satisfaça os critérios de sucesso.
- Configuração exata do Ollama (modelo padrão, bind host) — usar `llama3.1:8b-instruct-q4_K_M`; configuração de recursos é discrição do Claude.
- Versão exata do Python e das imagens Docker base (Python 3.11-alpine conforme CLAUDE.md).

### Deferred Ideas (OUT OF SCOPE)

- Testes de segurança simulados (pentest, injection, headers HTTP seguros como HSTS, X-Frame-Options)
- SAST com Bandit
- Rate limiting (INFRA-04)
- Suite de testes de isolamento cross-tenant (INFRA-03)
- Docker secrets / HashiCorp Vault para gestão de segredos em produção
- Row-level security no PostgreSQL
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Docker Compose completo: Django + Celery + Redis + PostgreSQL/pgvector + Ollama | Seções Standard Stack (Docker images), Architecture Patterns (compose structure), Environment Availability |
| INFRA-02 | Ambiente local funcional com um único `docker compose up` | Seções entrypoint.sh pattern, healthcheck strategy, pyproject.toml completo |
</phase_requirements>

---

## Summary

Esta fase entrega o esqueleto operacional do projeto: um `docker compose up` que levanta seis serviços (Django, Celery, PostgreSQL+pgvector, Redis, ChromaDB, Ollama), persiste dados em volumes nomeados e expõe o Django admin em `localhost:3600/admin/`. Nenhum app de negócio (`accounts`, `patients`, etc.) é criado aqui — apenas o núcleo Django (`manage.py`, `control/`, `pyproject.toml`) e toda a infraestrutura de suporte.

O ponto mais crítico da fase é o `pyproject.toml` completo desde o início (D-03/D-04): o `uv.lock` é gerado uma vez e não é tocado nas fases seguintes. Isso significa que as versões de todas as dependências — incluindo LangChain, pgvector, Celery e SDKs de LLM — devem ser definidas corretamente agora. A pesquisa de versões foi feita via PyPI e está documentada abaixo.

O segundo ponto crítico é o `entrypoint.sh`: ele é o único lugar onde a extensão `pgvector` é ativada no banco, as migrações são aplicadas e o `collectstatic` é executado antes de o servidor subir. Um erro neste script bloqueia todos os critérios de sucesso da fase.

**Recomendação principal:** Priorizar a escrita do `entrypoint.sh` e do `docker-compose.yml` antes do `pyproject.toml` — se o stack não subir, o lockfile não pode ser gerado dentro do container.

---

## Architectural Responsibility Map

| Capability | Tier Primário | Tier Secundário | Rationale |
|------------|--------------|-----------------|-----------|
| Django admin / HTTP | Container `nutrihelp_django` (gunicorn/runserver) | — | Único ponto de entrada HTTP nesta fase |
| Gerenciamento de dependências Python | Build-time (uv no Dockerfile) | — | `uv sync` durante build gera o environment |
| Persistência de dados estruturados | Container PostgreSQL (`pgvector/pgvector`) | Volume `postgres_data` | Banco principal; extensão vector ativada no entrypoint |
| Broker de tarefas assíncronas | Container Redis (`redis:7-alpine`) | Volume `redis_data` | Broker do Celery; não exposto no host |
| Worker assíncrono | Container `nutrihelp_celery` | Compartilha código com `nutrihelp_django` | Mesmo Dockerfile, comando diferente |
| Armazenamento vetorial (dev) | Container ChromaDB | Volume `chroma_data` | Usado nas fases de RAG; presente desde Phase 1 |
| Modelo de linguagem local | Container Ollama | Volume `ollama_data` | Serve `llama3.1:8b-instruct-q4_K_M`; sempre ativo |
| Configuração de ambiente | `dotenv_files/.env` → `env_file:` no compose | — | Variáveis injetadas em todos os serviços |

---

## Standard Stack

### Core — Imagens Docker

| Serviço | Imagem | Versão Verificada | Notas |
|---------|--------|-------------------|-------|
| PostgreSQL + pgvector | `pgvector/pgvector` | `0.8.2-pg17` (mais recente pg17) | Imagem oficial com pgvector pré-instalado; pg17 é estável e tem suporte longo |
| Redis | `redis:7-alpine` | `7-alpine` (já cacheada) | Alpine para tamanho mínimo; versão 7.x estável |
| ChromaDB | `chromadb/chroma` | `1.5.10.dev56` (latest) | Tag de desenvolvimento — usar `latest` ou fixar num semver estável |
| Ollama | `ollama/ollama` | `latest` (0.30.x série) | Stable release; `0.30.0-rc28` verificado |
| Python (Dockerfile base) | `python:3.11-alpine` | `3.11-alpine3.23` (mais recente) | Conforme CLAUDE.md; Alpine para imagem mínima |

[VERIFIED: Docker Hub registry — 2026-05-28]

> **Nota sobre ChromaDB:** o tag `latest` do ChromaDB no Docker Hub estava num build de desenvolvimento (`1.5.10.dev56`). Para estabilidade, considere usar `0.6.x` ou verificar tags de release no GitHub. [ASSUMED: necessidade de checar releases estáveis antes de fixar]

### Core — Dependências Python

| Pacote | Versão PyPI Atual | Versão Recomendada (pyproject.toml) | Propósito |
|--------|-------------------|--------------------------------------|-----------|
| django | 5.2.14 (LTS) | `>=5.2,<6.0` | Framework; 5.2 é LTS (suporte até 2028); 6.0 existe mas não é LTS |
| djangorestframework | 3.17.1 | `>=3.17,<4.0` | API REST |
| djangorestframework-simplejwt | 5.5.x | `>=5.5,<6.0` | JWT auth |
| psycopg2-binary | 2.9.x | `>=2.9,<3.0` | Driver PostgreSQL |
| pgvector | 0.4.2 | `>=0.4,<0.5` | ORM integration para VectorField |
| langchain | 1.3.x | `>=1.3,<2.0` | Orchestration core |
| langchain-text-splitters | 1.1.x | `>=1.1,<2.0` | RecursiveCharacterTextSplitter |
| langchain-openai | 1.2.x | `>=1.2,<2.0` | OpenAIEmbeddings + ChatOpenAI |
| langchain-anthropic | 1.4.x | `>=1.4,<2.0` | ChatAnthropic |
| langchain-community | 0.4.x | `>=0.4,<0.5` | Integrações adicionais |
| anthropic | 0.103.x | `>=0.103,<1.0` | SDK Anthropic direto |
| openai | 2.37.x | `>=2.37,<3.0` | SDK OpenAI direto + embeddings |
| celery | 5.6.3 | `>=5.6,<6.0` | Tarefas assíncronas |
| redis | 7.4.x | `>=7.4,<8.0` | Cliente Redis (broker Celery) |
| chromadb | 0.6.x | `>=0.5,<1.0` | Vectorstore local dev |
| pdfplumber | 0.11.x | `>=0.11,<0.12` | Extração de texto PDF |
| pytesseract | 0.3.x | `>=0.3,<0.4` | OCR (dependência declarada, uso em v1.x) |
| pillow | 12.x | `>=12,<13` | Processamento de imagem para OCR |
| python-decouple | 3.8 | `>=3.8` | Carregamento de variáveis de ambiente |
| whitenoise | 6.12.0 | `>=6.12,<7.0` | Servir static files |
| gunicorn | 26.0.0 | `>=26,<27` | Servidor WSGI produção/dev |
| drf-spectacular | 0.29.x | `>=0.29,<0.30` | Documentação OpenAPI (usado em Phase 7) |

[VERIFIED: PyPI registry `pip index versions <package>` — 2026-05-28]

> **Importante:** `langchain-text-splitters` é um pacote separado em LangChain 1.x. O `guia_implementacao.md` usa o import antigo `from langchain.text_splitter import ...` — isso está ERRADO para LangChain 1.x. O import correto é `from langchain_text_splitters import RecursiveCharacterTextSplitter`.

**pyproject.toml completo:**

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

    # RAG / LangChain (1.x série estável)
    "langchain>=1.3,<2.0",
    "langchain-text-splitters>=1.1,<2.0",
    "langchain-openai>=1.2,<2.0",
    "langchain-anthropic>=1.4,<2.0",
    "langchain-community>=0.4,<0.5",

    # LLM SDKs diretos (ambos instalados — embeddings sempre OpenAI)
    "anthropic>=0.103,<1.0",
    "openai>=2.37,<3.0",

    # Tarefas assíncronas
    "celery>=5.6,<6.0",
    "redis>=7.4,<8.0",

    # Vectorstore local (dev)
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

    # API docs (usada na Phase 7)
    "drf-spectacular>=0.29,<0.30",
]
```

---

## Architecture Patterns

### System Architecture Diagram — Phase 1

```
┌─────────────────────────────────────────────────────────────────┐
│                      docker compose up                           │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────────┐ │
│  │  nutrihelp  │    │  nutrihelp  │    │   nutrihelp_chromadb │ │
│  │  _django    │    │  _celery    │    │   (chromadb/chroma)  │ │
│  │  port:3600  │    │  (worker)   │    │   port:8000 (intern) │ │
│  │             │    │             │    └──────────────────────┘ │
│  │  entrypoint │    │  same image │                              │
│  │  .sh:       │    │  cmd:celery │    ┌──────────────────────┐ │
│  │  wait-db →  │    │  worker     │    │   nutrihelp_ollama   │ │
│  │  pgvector → │    │             │    │   (ollama/ollama)    │ │
│  │  migrate →  │    └──────┬──────┘    │   port:11434(intern) │ │
│  │  static →   │           │           └──────────────────────┘ │
│  │  gunicorn   │           │                                     │
│  └──────┬──────┘           │                                     │
│         │                  │ (broker)                            │
│         │    ┌─────────────▼──────────────────────┐             │
│         │    │         nutrihelp_redis              │             │
│         │    │         (redis:7-alpine)             │             │
│         │    │         internal only (no host port) │             │
│         │    └────────────────────────────────────┘             │
│         │                                                         │
│         │    ┌────────────────────────────────────┐             │
│         └───►│         nutrihelp_postgres           │             │
│              │  (pgvector/pgvector:0.8.2-pg17)     │             │
│              │  host port: 3601 (dev access)        │             │
│              │  vector extension via entrypoint.sh  │             │
│              └────────────────────────────────────┘             │
│                                                                  │
│  Volumes: postgres_data, redis_data, chroma_data, ollama_data   │
│  Network: nutrihelp_network (bridge, interno)                    │
│  Config:  dotenv_files/.env → env_file: em cada serviço         │
└─────────────────────────────────────────────────────────────────┘
```

### Estrutura de Arquivos — Phase 1

```
nutrihelp_app/
├── control/                    # Configuração Django (WSGI root)
│   ├── __init__.py
│   ├── celery.py               # App Celery — importado em __init__.py
│   ├── settings.py             # Settings únicos (não split base/dev/prod em v1)
│   ├── urls.py                 # urls raiz mínimas (só admin por enquanto)
│   └── wsgi.py
├── manage.py
├── pyproject.toml              # Todas as dependências do projeto (D-03/D-04)
└── uv.lock                     # Gerado no build do container

dotenv_files/
├── .env                        # Gitignored — valores reais
└── .env-example                # Commitado — placeholders documentados

docker-compose.yml              # Seis serviços + volumes + rede
Dockerfile                      # python:3.11-alpine, uv, duser, entrypoint
entrypoint.sh                   # wait-db → pgvector → migrate → static → gunicorn
.gitignore                      # Adicionar dotenv_files/.env
```

### Pattern 1: entrypoint.sh — Sequência Obrigatória

**O que é:** Script de inicialização do container Django que garante que o banco esteja pronto antes de tentar conectar.

**Por que é crítico:** O container Django sobe em paralelo com o PostgreSQL. Sem `wait-for-db`, Django falha na conexão e o container morre. A ativação do `pgvector` também deve acontecer antes das migrações (o `VectorField` depende da extensão).

```bash
#!/bin/sh
set -e

# 1. Aguarda PostgreSQL aceitar conexões
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

# 2. Ativa extensão pgvector (idempotente — CREATE EXTENSION IF NOT EXISTS)
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

# 4. Collectstatic
uv run manage.py collectstatic --noinput

# 5. Servidor
exec uv run gunicorn control.wsgi:application \
    --bind 0.0.0.0:3600 \
    --workers 2 \
    --timeout 120
```

[ASSUMED: uso de `python -c "psycopg2..."` para wait-for-db é funcional mas pode ser substituído por `pg_isready` se disponível na imagem Alpine. A abordagem com psycopg2 é preferível pois não requer pacote adicional no Alpine.]

### Pattern 2: Dockerfile com uv e duser

**O que é:** Dockerfile que segue os padrões do CLAUDE.md: Python 3.11-alpine, uv, usuário não-root `duser`.

```dockerfile
FROM python:3.11-alpine

# Dependências de sistema para psycopg2, pdfplumber, Pillow, pytesseract
RUN apk add --no-cache \
    gcc musl-dev postgresql-dev \
    libpq \
    libjpeg-turbo-dev zlib-dev \
    poppler-utils \
    && pip install uv

# Usuário não-root (CLAUDE.md: duser)
RUN addgroup -S dgroup && adduser -S duser -G dgroup

WORKDIR /nutrihelp_app

# Copia manifesto e instala dependências antes do código (cache layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copia código
COPY . .
RUN uv sync --frozen

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown duser:dgroup /entrypoint.sh

USER duser

ENTRYPOINT ["/entrypoint.sh"]
```

> **Nota:** `pytesseract` requer o binário `tesseract-ocr` para funcionar. Na Alpine: `apk add tesseract-ocr tesseract-ocr-data-por`. Para Phase 1, o pacote Python é instalado mas o binário **não precisa** estar na imagem — o OCR está fora de escopo em v1. Apenas a dependência Python é listada (D-04). [ASSUMED: incluir o pacote Python sem o binário é aceitável para Phase 1 pois não há runtime OCR nesta fase]

### Pattern 3: docker-compose.yml — Estrutura de Serviços

**Regras críticas do D-08:**
- Redis: sem `ports:` no host
- PostgreSQL: com `ports: "3601:5432"` para acesso dev
- Django: com `ports: "3600:3600"`

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
      - "3601:5432"          # Exposto no host para acesso dev
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - nutrihelp_network
    restart: unless-stopped

  nutrihelp_redis:
    image: redis:7-alpine
    container_name: nutrihelp_redis
    # Sem ports: — interno apenas (D-08)
    volumes:
      - redis_data:/data
    networks:
      - nutrihelp_network
    restart: unless-stopped

  nutrihelp_chromadb:
    image: chromadb/chroma:latest
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

### Pattern 4: settings.py Mínimo para Phase 1

**O que inclui:** banco de dados, apps instalados, JWT (preparado), Celery, chave secreta via python-decouple, whitenoise.

```python
from decouple import config, Csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')  # falha imediatamente se não definida (D-09)
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
]

# Celery
CELERY_BROKER_URL = config('REDIS_URL', default='redis://nutrihelp_redis:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://nutrihelp_redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

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

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ... resto do middleware padrão Django
]
```

### Pattern 5: Celery Integration Boilerplate

```python
# control/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control.settings')
app = Celery('nutrihelp')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# control/__init__.py
from .celery import app as celery_app
__all__ = ('celery_app',)
```

### .env-example Completo

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

# Redis (broker Celery)
REDIS_URL=redis://nutrihelp_redis:6379/0

# LLM
LLM_PROVIDER=ollama
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Ollama
OLLAMA_BASE_URL=http://nutrihelp_ollama:11434
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M

# Vector store
VECTOR_STORE=chroma
CHROMA_HOST=nutrihelp_chromadb
CHROMA_PORT=8000

# OCR
OCR_PROVIDER=tesseract
```

### Anti-Patterns a Evitar

- **SECRET_KEY com valor padrão no código:** Se `settings.py` tiver `SECRET_KEY = config('SECRET_KEY', default='...')`, o entrypoint nunca falhará por falta de chave — viola D-09. Use `config('SECRET_KEY')` sem default.
- **Redis com `ports:` no host:** Viola D-08. Redis nunca deve ter a linha `ports:` no docker-compose.
- **`uv run` sem `--frozen` no build:** O `uv sync --frozen` garante reprodutibilidade usando exatamente o que está no `uv.lock`. Omitir `--frozen` permite que o `uv` atualize dependências silenciosamente.
- **Entrypoint sem `set -e`:** Sem `set -e`, uma falha no `migrate` não interrompe o script — o servidor sobe com banco em estado inconsistente.
- **Volume sem nome (bind mount como `/data`):** Usar volumes nomeados (`postgres_data:`) em vez de bind mounts garante que os dados persistam corretamente entre `docker compose down` e `docker compose up` (critério de sucesso #5).

---

## Don't Hand-Roll

| Problema | Não Construir | Usar | Por quê |
|----------|--------------|------|---------|
| Esperar banco estar pronto | Loop shell com `sleep` e `nc` | psycopg2.connect em loop ou `pg_isready` | Verificação de conectividade real, não só de porta TCP |
| Ativar extensão pgvector | Script SQL externo | `CREATE EXTENSION IF NOT EXISTS vector` no entrypoint (idempotente) | Deve rodar toda vez que o container sobe; `IF NOT EXISTS` garante idempotência |
| Carregar variáveis de ambiente | `os.environ` manual | `python-decouple` com `config()` | Suporte a `.env` + `os.environ` com cast de tipos; falha limpa se variável obrigatória ausente |
| Servir static files | Nginx separado | `whitenoise` + `collectstatic` | Zero dependência externa; perfeito para dev e produção simples |
| Configuração de projetos uv | Edição manual de requirements.txt | `pyproject.toml` + `uv sync --frozen` | O `uv.lock` garante builds reprodutíveis; `uv sync --frozen` falha se `pyproject.toml` foi alterado sem rodar `uv lock` |

**Insight chave:** O stack Docker Compose é infraestrutura declarativa — toda a complexidade de orquestração (ordem de subida, restart policies, volumes nomeados, rede interna) é resolvida pelo Compose, não por scripts customizados.

---

## Common Pitfalls

### Pitfall 1: Container Django sobe antes do PostgreSQL aceitar conexões

**O que dá errado:** Django tenta conectar ao banco durante o import das settings ou durante `migrate` e falha com `connection refused`. O container para com erro.

**Por que acontece:** `depends_on:` no Docker Compose garante apenas que o container iniciou, não que o serviço dentro dele está pronto. PostgreSQL demora alguns segundos para aceitar conexões após o container subir.

**Como evitar:** O `entrypoint.sh` deve ter um loop `until psycopg2.connect(...)` antes de executar qualquer comando Django. O container Celery também deve esperar — ele usa a mesma lógica via o mesmo entrypoint (ou um script separado equivalente).

**Sinais de alerta:** `django.db.utils.OperationalError: could not connect to server` nos logs do container Django imediatamente após `docker compose up`.

---

### Pitfall 2: pgvector extension não existe quando migrations rodam

**O que dá errado:** Nas fases seguintes, quando o modelo `Chunk` com `VectorField` for adicionado, a migration falhará com `type "vector" does not exist` se a extensão não foi ativada antes.

**Por que acontece:** A extensão `pgvector` precisa ser criada explicitamente no banco. A imagem `pgvector/pgvector` tem o binário instalado mas não ativa a extensão automaticamente.

**Como evitar:** O `entrypoint.sh` ativa a extensão com `CREATE EXTENSION IF NOT EXISTS vector;` antes de rodar `manage.py migrate`. É idempotente — rodar múltiplas vezes não causa erro.

**Sinais de alerta:** Erro `type "vector" does not exist` ao rodar migrações que incluem `VectorField`.

---

### Pitfall 3: uv.lock não commitado ou desatualizado

**O que dá errado:** O Dockerfile roda `uv sync --frozen` e falha com `lockfile does not exist` ou `lockfile is outdated` se `uv.lock` não existe no repositório ou não corresponde ao `pyproject.toml`.

**Por que acontece:** `uv lock` precisa ser rodado localmente ou dentro do container antes do build. Se o lockfile não for commitado, cada build pode usar versões diferentes.

**Como evitar:** Gerar o `uv.lock` uma vez (rodando `uv lock` dentro do container de build ou via `docker run --rm python:3.11-alpine sh -c "pip install uv && uv lock"`) e commitar o lockfile junto com o `pyproject.toml`. O Dockerfile usa `--frozen` para garantir reprodutibilidade.

---

### Pitfall 4: Ollama com modelo não baixado — container sobe mas serve erro

**O que dá errado:** O container `nutrihelp_ollama` sobe com sucesso, mas quando Django (nas fases seguintes) tentar chamar `llama3.1:8b-instruct-q4_K_M`, o Ollama responde com erro pois o modelo não está baixado.

**Por que acontece:** A imagem Ollama não inclui modelos. O pull do modelo (`ollama pull llama3.1:8b-instruct-q4_K_M`) é um passo manual ou deve ser feito via healthcheck/init container.

**Como evitar para Phase 1:** Documentar no README e no `.env-example` que o modelo precisa ser baixado manualmente: `docker exec nutrihelp_ollama ollama pull llama3.1:8b-instruct-q4_K_M`. Esta fase só verifica que o container Ollama está rodando — o modelo é necessário apenas nas fases RAG/Chat.

**Sinais de alerta:** `Error: model "llama3.1:8b-instruct-q4_K_M" not found` nos logs do Django/Celery nas fases de RAG.

---

### Pitfall 5: Django project name e Celery app name incompatíveis

**O que dá errado:** CLAUDE.md define a estrutura como `control/` (não `config/` como o `guia_implementacao.md`). Se `celery.py` usar `Celery('nutrichat')` mas o `DJANGO_SETTINGS_MODULE` for `control.settings`, as tasks não são autodiscoveries corretamente.

**Por que acontece:** Conflito entre o nome do módulo Celery e o `DJANGO_SETTINGS_MODULE`. Se o nome passado para `Celery('...')` não corresponder ao namespace do projeto, o autodiscover pode falhar silenciosamente.

**Como evitar:** `Celery('nutrihelp')` + `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control.settings')` — usar o nome do projeto, não do módulo de configuração. O `app.autodiscover_tasks()` encontra `tasks.py` em todos os apps listados em `INSTALLED_APPS`.

---

### Pitfall 6: ChromaDB tag instável no docker-compose

**O que dá errado:** `chromadb/chroma:latest` pode apontar para uma versão de desenvolvimento que quebra a API entre builds.

**Por que acontece:** O Docker Hub do ChromaDB mostrou `1.5.10.dev56` como tag mais recente em 2026-05-28 — claramente um build de desenvolvimento.

**Como evitar:** Usar uma tag de release semântica estável (ex: `chromadb/chroma:0.6.3` se disponível) em vez de `latest`. Verificar releases no GitHub antes de fixar. [ASSUMED: a versão estável atual do ChromaDB é 0.6.x — verificar antes de commitar o docker-compose]

---

## Code Examples

### Verificação do pgvector após `docker compose up`

```bash
# Verificar extensão ativada
docker exec -it nutrihelp_postgres psql -U nutrihelp_user -d nutrihelp -c "\dx"
# Deve mostrar: vector | ... | pgvector: vector data type and ivfflat and hnsw access methods

# Verificar Celery conectado ao Redis
docker exec -it nutrihelp_celery uv run celery -A control inspect ping
# Deve responder: {'nutrihelp_celery@...': {'ok': 'pong'}}

# Verificar Django admin
curl -I http://localhost:3600/admin/
# Deve responder: HTTP/1.1 200 OK
```

### Gerar uv.lock dentro do container (se necessário)

```bash
# Opção 1: build temporário para gerar lockfile
docker run --rm -v $(pwd)/nutrihelp_app:/app -w /app python:3.11-alpine \
  sh -c "pip install uv && uv lock"

# Opção 2: após primeiro build sem --frozen
docker exec -it nutrihelp_django uv lock
docker cp nutrihelp_django:/nutrihelp_app/uv.lock ./nutrihelp_app/uv.lock
```

### Smoke test completo (Phase 1 validation)

```python
# Rodar dentro do container:
# docker exec -it nutrihelp_django uv run manage.py shell

import psycopg2, os, django
from django.conf import settings

# Verifica banco
conn = psycopg2.connect(
    host=settings.DATABASES['default']['HOST'],
    user=settings.DATABASES['default']['USER'],
    password=settings.DATABASES['default']['PASSWORD'],
    dbname=settings.DATABASES['default']['NAME'],
)
cur = conn.cursor()
cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
assert cur.fetchone() is not None, "pgvector NAO ATIVO"
print("pgvector: OK")
conn.close()

# Verifica Redis
from django.core.cache import caches
import redis
r = redis.from_url(settings.CELERY_BROKER_URL)
assert r.ping(), "Redis nao responde"
print("Redis: OK")
```

---

## State of the Art

| Abordagem Antiga | Abordagem Atual | Quando Mudou | Impacto |
|------------------|-----------------|--------------|---------|
| `pip` + `requirements.txt` | `uv` + `pyproject.toml` + `uv.lock` | 2023-2024 | Builds 10-100x mais rápidos; lockfile reproduzível |
| `docker-compose.yml` v2 syntax | `docker compose` v2 CLI (sem hífen) | Docker Compose v2 (2022) | O comando é `docker compose` (plugin), não `docker-compose` (standalone) |
| Django 4.2 LTS | Django 5.2 LTS | Abril 2025 (4.2 EOL aprox) | 4.2 chega ao EOL em abril 2026; projeto já nasce em 5.2 |
| `ankane/pgvector` Docker image | `pgvector/pgvector` Docker image | 2023 | `pgvector/pgvector` é a imagem oficial; `ankane/pgvector` é o maintainer pessoal do mesmo projeto |
| LangChain 0.x imports (`from langchain.text_splitter`) | LangChain 1.x imports (`from langchain_text_splitters`) | LangChain 1.0 (2024) | Imports 0.x são removidos; `guia_implementacao.md` usa o padrão antigo — corrigir |
| `waitress` / `runserver` em produção | `gunicorn` + `whitenoise` | Padrão consolidado | `gunicorn` para WSGI; `whitenoise` elimina necessidade de Nginx para static files |

---

## Assumptions Log

| # | Afirmação | Seção | Risco se Errada |
|---|-----------|-------|-----------------|
| A1 | ChromaDB versão estável atual é 0.6.x — usar em vez de `latest` | Standard Stack | Tag instável pode causar falha de build |
| A2 | `python -c "psycopg2.connect(...)"` funciona na Alpine sem pacotes extras além de `libpq` | Pattern entrypoint.sh | Se libpq não estiver disponível, o wait-for-db quebra |
| A3 | `pytesseract` sem o binário `tesseract-ocr` na Alpine não causa erro de import, apenas de uso | Standard Stack (Dockerfile) | Se `import pytesseract` falhar no startup, o Django não sobe |
| A4 | `ollama pull` é necessário manualmente após o container subir — não há init automático de modelo | Pitfall 4 | Se houver forma de auto-pull, o Pitfall 4 não se aplica |

---

## Open Questions

1. **ChromaDB tag estável**
   - O que sabemos: Docker Hub mostra `1.5.10.dev56` como latest (build dev)
   - O que não está claro: qual é o último tag de release semântico estável do ChromaDB
   - Recomendação: verificar `https://github.com/chroma-core/chroma/releases` antes de fixar o tag no docker-compose
   - **RESOLVED:** fixar tag semântico estável `chromadb/chroma:0.6.3` no docker-compose; nunca `:latest` (decidido em 01-02-PLAN Task 2 / Pitfall 6). Se 0.6.3 não existir no registry, usar o tag estável mais próximo verificado nos releases.

2. **pytesseract sem binário Tesseract**
   - O que sabemos: `pytesseract` é uma wrapper Python para o binário `tesseract-ocr`
   - O que não está claro: se `import pytesseract` falha ou apenas emite warning quando o binário está ausente
   - Recomendação: testar no Dockerfile com `python -c "import pytesseract"` após o build; se falhar, adicionar `tesseract-ocr` ao `apk add` ou remover `pytesseract` do `pyproject.toml` e deixar para v1.x
   - **RESOLVED:** `import pytesseract` NÃO requer o binário (a wrapper só falha em runtime ao chamar `image_to_string`). Binário tesseract fica fora do Dockerfile na Phase 1 (OCR fora de escopo). Verificação adicionada ao checkpoint do 01-02-PLAN (Task 3, passo 5): `docker exec nutrihelp_django uv run python -c "import pytesseract"`.

3. **Ollama GPU pass-through**
   - O que sabemos: CLAUDE.md menciona RTX 5070 12GB; o modelo `llama3.1:8b-instruct-q4_K_M` roda bem em GPU
   - O que não está claro: se o compose deve incluir `deploy.resources.reservations.devices` para NVIDIA GPU
   - Recomendação: adicionar o bloco de GPU ao serviço `nutrihelp_ollama` se a GPU estiver disponível; tornar opcional via `.env` ou comentário no compose
   - **RESOLVED:** bloco GPU NVIDIA permanece OPCIONAL e comentado no docker-compose (01-02-PLAN Task 2); CPU fallback é aceitável para a verificação de infra da Phase 1. Habilitar o bloco fica a critério do executor se a RTX 5070 estiver disponível.

---

## Environment Availability

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|--------------|-----------|--------|---------|
| Docker Engine | `docker compose up` | Sim | 29.4.0 | — |
| Docker Compose | Orquestração | Sim | v5.1.1 | — |
| Python 3.11 (Alpine image) | Dockerfile base | Sim (imagem `3.11-alpine3.23`) | 3.11 | — |
| pgvector/pgvector Docker image | PostgreSQL + pgvector | Sim (`0.8.2-pg17` disponível) | pg17 | — |
| redis:7-alpine | Redis broker | Sim (cacheada localmente) | 7-alpine | — |
| ollama/ollama | Inference local | Sim (latest disponível) | latest | — |
| chromadb/chroma | Vectorstore dev | Sim (latest disponível; tag dev) | 1.5.x-dev | Tag semântico estável |
| uv | Gerenciamento deps Python | Sim (instalado no container) | 0.11.16 | — |
| GPU NVIDIA (host) | Performance Ollama | [ASSUMED] disponível (RTX 5070) | — | CPU fallback (lento para LLM) |

**Dependências sem fallback crítico:**
- Nenhuma — todos os serviços têm imagens disponíveis no Docker Hub.

**Dependências com ressalva:**
- ChromaDB: tag `latest` é instável; verificar tag semântico estável antes do build.

---

## Validation Architecture

### Test Framework

| Propriedade | Valor |
|-------------|-------|
| Framework | Django TestCase (nativo) |
| Config | `manage.py test` (integrado ao Django) |
| Comando rápido | `docker exec -it nutrihelp_django uv run manage.py test --keepdb` |
| Comando completo | `docker exec -it nutrihelp_django uv run manage.py test` |

### Phase Requirements → Test Map

| REQ ID | Comportamento | Tipo | Comando Automatizado | Arquivo Existe? |
|--------|--------------|------|----------------------|-----------------|
| INFRA-01 | Todos os 6 serviços sobem sem erros | smoke / infra | `docker compose up -d && docker compose ps` — todos `Up` | N/A (verificação de infra) |
| INFRA-01 | pgvector extension ativa | smoke | `docker exec nutrihelp_postgres psql -U $USER -d $DB -c "\dx" \| grep vector` | N/A |
| INFRA-01 | Celery conecta ao Redis | smoke | `docker exec nutrihelp_celery uv run celery -A control inspect ping` | N/A |
| INFRA-02 | Django admin responde em 3600 | smoke | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3600/admin/` == 200 | N/A |
| INFRA-02 | Dados persistem após restart | smoke manual | `docker compose down && docker compose up -d` + verificar dados no banco | N/A |

### Sampling Rate

- **Por commit:** `docker compose up -d && docker compose ps` — todos os containers `Up`
- **Por wave:** curl para admin + pgvector check + Celery ping
- **Phase gate:** todos os 5 critérios de sucesso verificados antes de `gsd-verify-work`

### Wave 0 Gaps

- [ ] Não há testes Django formais nesta fase (nenhum app instalado ainda)
- [ ] Smoke tests são verificações de infra via shell/curl, não `manage.py test`
- [ ] `control/tests.py` pode ser criado com um `SimpleTestCase` que verifica configurações básicas (SECRET_KEY, DATABASES)

---

## Security Domain

### Aplicáveis nesta fase

| Categoria ASVS | Aplica | Controle |
|---------------|--------|---------|
| V2 Autenticação | Não | Sem endpoints de auth nesta fase |
| V3 Sessões | Não | Sem sessões em uso |
| V4 Controle de Acesso | Parcial | Admin Django protegido por padrão |
| V5 Validação de Input | Não | Sem forms/endpoints |
| V6 Criptografia | Sim | `SECRET_KEY` obrigatória e não exposta (D-09) |

### Controles de segurança desta fase

| Padrão | Controle | Implementação |
|--------|---------|---------------|
| Secret management | `SECRET_KEY` nunca tem valor default no código | `config('SECRET_KEY')` sem default — falha se ausente |
| Segredos não commitados | `.env` no `.gitignore` | D-09 explícito |
| Usuário não-root | Container roda como `duser` | Dockerfile: `USER duser` |
| Rede isolada | Redis e serviços internos sem `ports:` | D-08: Redis não exposto no host |

---

## Projeto Existente — Estado Atual

**O repositório está vazio de código** — apenas arquivos de planejamento (`.planning/`, `CLAUDE.md`, `guia_implementacao.md`). Phase 1 cria tudo do zero. Não há código a reutilizar, migrar ou refatorar.

O `.gitignore` atual contém apenas `guia_implementacao.md`. Precisará ser expandido para incluir:
- `dotenv_files/.env`
- `nutrihelp_app/staticfiles/`
- `__pycache__/`
- `*.pyc`
- `uv.lock` (NÃO — o lockfile DEVE ser commitado para builds reproduzíveis)

---

## Conflitos entre CLAUDE.md e guia_implementacao.md

| Ponto | CLAUDE.md (autoritativo) | guia_implementacao.md | Resolução |
|-------|--------------------------|-----------------------|-----------|
| Diretório do projeto Django | `nutrihelp_app/` | `nutrichat/` | Usar `nutrihelp_app/` |
| Módulo de configuração Django | `control/` | `config/` | Usar `control/` |
| Estrutura de settings | Settings único `control/settings.py` | Split `settings/base.py`, `dev.py`, `prod.py` | Usar settings único para v1 (mais simples) |
| Gerenciador de dependências | `uv` + `pyproject.toml` | `pip` + `requirements/base.txt` | Usar `uv` |
| Nome do container Django | `nutrihelp_django` | não especificado | Usar `nutrihelp_django` |
| Import LangChain text splitter | (não especificado) | `from langchain.text_splitter import ...` (0.x) | Usar `from langchain_text_splitters import ...` (1.x) |

---

## Sources

### Primárias (HIGH confidence)

- PyPI registry `pip index versions <package>` — versões de todas as dependências Python (verificado 2026-05-28)
- Docker Hub registry API — tags das imagens Docker (verificado 2026-05-28)
- CLAUDE.md do projeto — nomes de containers, portas, estrutura, padrão uv, duser
- `.planning/research/STACK.md` — versões e padrões verificados em 2026-05-19
- `.planning/research/ARCHITECTURE.md` — padrões de arquitetura verificados em 2026-05-19

### Secundárias (MEDIUM confidence)

- `guia_implementacao.md` — referência de design (adaptada para CLAUDE.md onde há conflito)
- `.planning/research/PITFALLS.md` — armadilhas verificadas em 2026-05-19

---

## Metadata

**Breakdown de confiança:**

- Stack (imagens Docker, versões Python): HIGH — verificado via PyPI e Docker Hub em 2026-05-28
- Padrões de arquitetura (entrypoint, compose, settings): HIGH — padrões estabelecidos da documentação oficial Django/Celery + CLAUDE.md
- Pitfalls: HIGH — derivados de padrões conhecidos de falha em Docker+Django, verificados em pesquisa anterior

**Data da pesquisa:** 2026-05-28
**Válido até:** 2026-06-28 (versões das imagens Docker mudam frequentemente; re-verificar antes de builds críticos)
