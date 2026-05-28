---
phase: 01-infrastructure-foundation
plan: 01
subsystem: django-core
tags: [django, pyproject, celery, settings, gitignore, env, scaffold]
dependency_graph:
  requires: []
  provides:
    - nutrihelp_app/pyproject.toml (todas as deps D-03/D-04)
    - nutrihelp_app/control/ (núcleo Django: settings, celery, urls, wsgi)
    - dotenv_files/.env-example (fonte de verdade de variáveis de ambiente)
    - .gitignore (D-09: segredos excluídos, uv.lock incluído)
    - scripts/smoke_test.sh (Wave 0: validação dos 5 critérios de sucesso)
    - nutrihelp_app/control/tests.py (Wave 0: SimpleTestCase de smoke)
  affects:
    - Plan 02 (Docker stack consome pyproject.toml, control/, .env-example)
tech_stack:
  added:
    - django>=5.2,<6.0
    - djangorestframework>=3.17,<4.0
    - djangorestframework-simplejwt>=5.5,<6.0 (JWT access 5min, refresh 1 dia)
    - celery>=5.6,<6.0 (app nomeado 'nutrihelp')
    - redis>=7.4,<8.0
    - langchain>=1.3,<2.0 + langchain-text-splitters, langchain-openai, langchain-anthropic, langchain-community
    - anthropic>=0.103,<1.0 + openai>=2.37,<3.0
    - psycopg2-binary>=2.9,<3.0 + pgvector>=0.4,<0.5
    - chromadb>=0.5,<1.0
    - pdfplumber>=0.11,<0.12 + pytesseract>=0.3,<0.4 + pillow>=12,<13
    - python-decouple>=3.8
    - whitenoise>=6.12,<7.0 + gunicorn>=26,<27
    - drf-spectacular>=0.29,<0.30
  patterns:
    - SECRET_KEY sem default via python-decouple (D-09)
    - Celery app nomeado 'nutrihelp' com namespace CELERY_ no settings
    - Whitenoise logo após SecurityMiddleware no MIDDLEWARE
    - SIMPLE_JWT com ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION
key_files:
  created:
    - nutrihelp_app/pyproject.toml
    - nutrihelp_app/manage.py
    - nutrihelp_app/control/__init__.py
    - nutrihelp_app/control/celery.py
    - nutrihelp_app/control/settings.py
    - nutrihelp_app/control/urls.py
    - nutrihelp_app/control/wsgi.py
    - dotenv_files/.env-example
    - scripts/smoke_test.sh
    - nutrihelp_app/control/tests.py
  modified:
    - .gitignore (expandido com dotenv_files/.env, staticfiles, cache Python, IDEs, OS, logs)
    - .planning/phases/01-infrastructure-foundation/01-VALIDATION.md (wave_0_complete: true)
decisions:
  - "Celery app nomeado 'nutrihelp' (não 'nutrichat' nem 'control') — CLAUDE.md vence sobre guia_implementacao.md"
  - "Settings único control/settings.py (não split base/dev/prod) — simplidade em v1"
  - "SECRET_KEY sem default no código — falha imediata se ausente (D-09)"
  - "JWT: access 5min, refresh 1 dia (valores CLAUDE.md, mais conservadores que o guia)"
  - "uv.lock NÃO no .gitignore — deve ser commitado para builds reproduzíveis (Pitfall 3)"
metrics:
  duration_minutes: 4
  completed_date: "2026-05-28"
  tasks_completed: 4
  tasks_total: 4
  files_created: 10
  files_modified: 2
requirements_satisfied: [INFRA-01, INFRA-02]
---

# Phase 01 Plan 01: Django Core Scaffold Summary

**One-liner:** Scaffold Django 5.2 com pyproject.toml completo (23 deps D-03/D-04), núcleo control/ (settings via python-decouple sem default em SECRET_KEY), Celery 'nutrihelp' com autodiscover, JWT 5min/1dia com rotação, whitenoise e artefatos Wave 0 de validação.

## What Was Built

Criado o esqueleto completo do projeto Django sem nenhum app de negócio (D-01/D-02):

1. **`nutrihelp_app/pyproject.toml`** — 23 dependências declaradas de uma vez (D-03/D-04), cobrindo todo o stack: Django 5.2 LTS, DRF, SimpleJWT, LangChain 1.x (com pacotes separados do 1.x: `langchain-text-splitters`, `langchain-openai`, `langchain-anthropic`, `langchain-community`), Celery, Redis, ChromaDB, processamento de documentos (pdfplumber, pytesseract, pillow), python-decouple, whitenoise, gunicorn e drf-spectacular. Fases seguintes não precisam modificar este arquivo.

2. **`nutrihelp_app/control/`** — Núcleo Django completo:
   - `settings.py`: `SECRET_KEY = config('SECRET_KEY')` sem default (D-09), middleware com whitenoise logo após SecurityMiddleware, INSTALLED_APPS com `rest_framework_simplejwt.token_blacklist` e `drf_spectacular`, SIMPLE_JWT com access 5min/refresh 1 dia + rotação + blacklist, REST_FRAMEWORK com JWTAuthentication e drf-spectacular AutoSchema, DATABASES e Celery via config(), variáveis LLM/Vector store via config().
   - `celery.py`: app `Celery('nutrihelp')` com autodiscover — nome do projeto, não do módulo de configuração (Pitfall 5).
   - `__init__.py`: importa `celery_app` para carregamento automático quando Django inicia.
   - `urls.py`: apenas `admin/` em Phase 1 (prefixos de API comentados para guia das fases seguintes).
   - `wsgi.py`: ponto de entrada WSGI padrão Django 5.2.
   - `tests.py`: `SimpleTestCase` que verifica SECRET_KEY presente e DATABASES configurado (Wave 0).

3. **`.gitignore`** — Expandido: `dotenv_files/.env` excluído (D-09), `nutrihelp_app/staticfiles/` excluído, cache Python, venvs, IDEs, OS, logs. `uv.lock` deliberadamente fora da exclusão (Pitfall 3).

4. **`dotenv_files/.env-example`** — Todas as variáveis documentadas com placeholders usando nomes de serviço Docker (D-08): `nutrihelp_postgres`, `nutrihelp_redis`, `nutrihelp_chromadb`, `nutrihelp_ollama`. Instrução de pull manual do modelo Ollama documentada nos comentários.

5. **`scripts/smoke_test.sh`** — Cobre os 5 critérios de sucesso da fase: `docker compose ps`, `curl admin`, `\dx | grep vector`, `celery inspect ping`, instrução de persistência (Wave 0).

## Commits

| Task | Commit | Descrição |
|------|--------|-----------|
| Task 1 | 69c9adc | feat(01-01): criar pyproject.toml completo e expandir .gitignore |
| Task 2 | 03c5671 | feat(01-01): criar nucleo Django (manage.py, control/) |
| Task 3 | cb71192 | feat(01-01): criar dotenv_files/.env-example documentado |
| Task 4 | c6ef4ad | feat(01-01): criar artefatos Wave 0 (control/tests.py, scripts/smoke_test.sh) |

## Deviations from Plan

None - plan executed exactly as written.

Os padrões canônicos do PATTERNS.md foram seguidos verbatim. Os conflitos entre `guia_implementacao.md` e `CLAUDE.md` já estavam resolvidos no plano (CLAUDE.md sempre vence): diretório `nutrihelp_app/`, módulo `control/`, settings único, Celery app `'nutrihelp'`, JWT 5min/1dia.

## Security Controls Implemented

| Controle | Implementação | Verificação |
|----------|--------------|-------------|
| SECRET_KEY obrigatória (T-01-02) | `config('SECRET_KEY')` sem default | `grep -q "config('SECRET_KEY', default" settings.py` retorna não-zero |
| Segredos não commitados (T-01-01) | `dotenv_files/.env` no .gitignore (D-09) | `grep -q 'dotenv_files/.env' .gitignore` |
| uv.lock commitado (T-01-04) | `uv.lock` ausente do .gitignore | `grep -q '^uv.lock' .gitignore` retorna não-zero |
| Nomes de serviço Docker (D-08) | POSTGRES_HOST=nutrihelp_postgres, REDIS_URL=redis://nutrihelp_redis | .env-example usa nomes de serviço internos |

## Known Stubs

Nenhum — este plano é puramente scaffolding de configuração, sem dados ou componentes de UI. Nenhum stub de dados foi introduzido.

## Threat Flags

Nenhum — nenhuma superfície de rede, endpoint ou caminho de auth novo além do que está no threat_model do plano.

## Self-Check: PASSED

Todos os 10 arquivos criados existem no filesystem. Todos os 4 commits (69c9adc, 03c5671, cb71192, c6ef4ad) presentes no histórico git. Nenhuma deleção acidental detectada em nenhum dos commits de task.
