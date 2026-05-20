# Phase 1: Infrastructure Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** 01-infrastructure-foundation
**Areas discussed:** Profundidade do scaffold, Estratégia de dependências, Ollama no docker-compose, ChromaDB na Phase 1, Segurança da infraestrutura

---

## Profundidade do Scaffold

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Só o núcleo | Docker + Django funcionando: manage.py, control/settings.py, pyproject.toml. Apps criados nas fases seguintes. | ✓ |
| Scaffold completo dos apps | Cria accounts/, patients/, rag/, documents/, chat/ com arquivos placeholder. | |

**Escolha do usuário:** Só o núcleo  
**Notas:** Phase 1 mantém foco em infraestrutura. Apps serão scaffolded conforme necessário nas fases seguintes.

---

## Estratégia de Dependências

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Todas as deps do projeto agora | pyproject.toml completo com todas as deps. uv.lock gerado uma vez. | ✓ |
| Só o necessário para Phase 1 | Apenas Django, DRF, psycopg2. Cada fase adiciona suas deps. | |

**Escolha do usuário:** Todas as deps do projeto agora  
**Notas:** Evita modificar pyproject.toml em fases futuras. uv.lock completo desde o início.

---

## Ollama no docker-compose

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Serviço sempre ativo | Ollama como serviço padrão. Sobe sempre com docker compose up. | ✓ |
| Docker Compose profile opcional | Ollama só sobe com --profile local-llm. | |

**Escolha do usuário:** Serviço sempre ativo  
**Notas:** INFRA-01 exige stack completo. Simplicidade operacional preferida sobre granularidade de profiles.

---

## ChromaDB na Phase 1

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Incluir já na Phase 1 | nutrihelp_chromadb no docker-compose desde o início. Ambiente dev completo. | ✓ |
| Adiar para Phase 5 | ChromaDB só entra quando o RAG pipeline for implementado. | |

**Escolha do usuário:** Incluir já na Phase 1  
**Notas:** docker-compose reflete o ambiente real de dev desde o dia 1. Sem surpresas nas fases seguintes.

---

## Segurança da Infraestrutura

### Exposição de portas

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Apenas rede interna Docker | PostgreSQL e Redis sem ports: no host. Só containers se comunicam. | ✓ |
| Expostos no host (127.0.0.1) | Acessível por DBeaver, redis-cli para debug. | |

**Escolha do usuário:** Apenas rede interna Docker  
**Notas:** Elimina vetor de ataque externo. Dev usa docker exec para acesso direto se necessário.

### Variáveis de ambiente sensíveis

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| .env no .gitignore + .env-example | Padrão já documentado no CLAUDE.md. | ✓ |
| Docker secrets / vault | Mais seguro em produção, complexidade desnecessária para MVP. | |

**Escolha do usuário:** .env no .gitignore + .env-example  

### Ataques simulados / pentest

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Phase 7 — Quality & Hardening | Testes de segurança junto com INFRA-03, INFRA-04. | ✓ |
| Phase 1 já inclui baseline | Bandit, headers seguros, django-security-check na Phase 1. | |

**Escolha do usuário:** Phase 7  
**Notas:** Ataques simulados, pentest e hardening de headers HTTP adiados para Phase 7.

---

## Claude's Discretion

- Estratégia de healthcheck dos containers
- Configuração de recursos do Ollama (memória, CPU)
- Versão exata das imagens Docker base

## Deferred Ideas

- Testes de segurança simulados (pentest, SAST, headers HTTP) → Phase 7
- Docker secrets / Vault → fora de escopo v1.0
