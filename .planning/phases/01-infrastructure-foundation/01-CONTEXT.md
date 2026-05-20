# Phase 1: Infrastructure Foundation - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Criar o stack Docker Compose completo do zero — todos os serviços sobem com um único `docker compose up`, o Django admin responde, o pgvector está ativo, o Celery conecta ao Redis e os dados persistem entre reinicializações.

Esta fase entrega **infraestrutura funcionando**, não código de negócio. Nenhuma app Django (accounts, patients, rag, documents, chat) é implementada aqui — só o esqueleto do projeto que as fases seguintes preencherão.

</domain>

<decisions>
## Implementation Decisions

### Scaffold do Projeto Django
- **D-01:** Phase 1 cria apenas o núcleo Django: `manage.py`, `control/settings.py`, `control/urls.py`, `control/wsgi.py`, `pyproject.toml`. Nenhum app de negócio é criado nesta fase.
- **D-02:** Apps (`accounts/`, `patients/`, `rag/`, `documents/`, `chat/`) são criados nas fases seguintes, conforme necessário.

### Dependências (pyproject.toml)
- **D-03:** `pyproject.toml` inclui **todas as dependências do projeto** desde a Phase 1 — `uv.lock` completo gerado de uma vez. Fases seguintes não precisam modificar `pyproject.toml`.
- **D-04:** Dependências a incluir: `django`, `djangorestframework`, `djangorestframework-simplejwt`, `psycopg2-binary`, `pgvector`, `langchain`, `langchain-community`, `langchain-anthropic`, `langchain-openai`, `chromadb`, `celery`, `redis`, `pdfplumber`, `pytesseract`, `pillow`, `drf-spectacular`.

### Serviços Docker Compose
- **D-05:** Todos os serviços do stack são incluídos na Phase 1: `nutrihelp_django`, `nutrihelp_celery`, `nutrihelp_redis`, `nutrihelp_chromadb`, PostgreSQL/pgvector e Ollama.
- **D-06:** Ollama é um serviço **sempre ativo** (não usa profile opcional). INFRA-01 exige o stack completo com Ollama.
- **D-07:** ChromaDB (`nutrihelp_chromadb`) é incluído na Phase 1 — o docker-compose reflete o ambiente de dev completo desde o início.

### Segurança da Infraestrutura
- **D-08:** PostgreSQL e Redis ficam **apenas na rede interna Docker** — sem `ports:` expostos no host. Django e Celery acessam via nome de serviço (`nutrihelp_postgres`, `nutrihelp_redis`). Elimina vetor de ataque externo.
- **D-09:** `dotenv_files/.env` adicionado ao `.gitignore`. `dotenv_files/.env-example` com placeholders documentados. Entrypoint falha com mensagem clara se `SECRET_KEY` não estiver definida.
- **D-10:** Testes de segurança (pentest, SAST, rate limiting, headers HTTP) são responsabilidade da **Phase 7 — Quality & Hardening**, não desta fase.

### Claude's Discretion
- Estratégia de healthcheck dos containers (entrypoint wait-for-db vs Docker HEALTHCHECK formal) — Claude decide a abordagem mais simples que satisfaça os critérios de sucesso.
- Configuração exata do Ollama (modelo padrão, bind host) — deve usar `llama3.1:8b-instruct-q4_K_M` conforme CLAUDE.md, mas configuração de recursos é discrição do Claude.
- Versão exata do Python e das imagens Docker base (Python 3.11-alpine conforme CLAUDE.md).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Instructions (authoritative)
- `CLAUDE.md` — Define nomes de containers, portas, estrutura de diretórios, comandos de gestão, padrão de uv, usuário duser, entrypoint.sh. **CLAUDE.md tem precedência sobre qualquer outro documento.**

### Implementation Guide
- `guia_implementacao.md` §4 — Configuração do ambiente, variáveis de ambiente, dependências de referência.
- `guia_implementacao.md` §3 — Estrutura de pastas (referência; adaptar para o padrão do CLAUDE.md onde houver conflito).

### Requirements
- `.planning/REQUIREMENTS.md` — INFRA-01 (Docker Compose completo) e INFRA-02 (ambiente local com um único comando).
- `.planning/ROADMAP.md` §Phase 1 — Critérios de sucesso da fase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Nenhum — repositório vazio. Phase 1 cria tudo do zero.

### Established Patterns
- `CLAUDE.md` define o padrão de uso de `uv` (não pip), estrutura `nutrihelp_app/`, e o fluxo do `entrypoint.sh`. Esses padrões devem ser respeitados em todas as fases.

### Integration Points
- `entrypoint.sh` é o ponto de entrada do container Django — responsável por: esperar o banco, ativar `pgvector`, rodar migrações, `collectstatic`, e iniciar o servidor.
- `dotenv_files/.env` é carregado pelo docker-compose para injetar variáveis nos containers.

</code_context>

<specifics>
## Specific Ideas

- Portas mapeadas conforme CLAUDE.md: Django em `:3600`, PostgreSQL em `:3601` (host, para acesso dev), Redis **não exposto** no host.
- Container `duser` (usuário não-root) já definido no CLAUDE.md — deve ser usado no Dockerfile.
- `uv run manage.py` é o padrão para todos os comandos Django dentro do container (ver CLAUDE.md).

</specifics>

<deferred>
## Deferred Ideas

### Segurança avançada → Phase 7
- Testes de segurança simulados (pentest, injection, headers HTTP seguros como HSTS, X-Frame-Options)
- SAST com Bandit
- Rate limiting (INFRA-04)
- Suite de testes de isolamento cross-tenant (INFRA-03)

### Fora de escopo v1.0
- Docker secrets / HashiCorp Vault para gestão de segredos em produção
- Row-level security no PostgreSQL

</deferred>

---

*Phase: 01-infrastructure-foundation*
*Context gathered: 2026-05-20*
