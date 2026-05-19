# Project State

## Project Reference

**What This Is:** Plataforma web de nutrição com assistente de IA via RAG — nutricionistas gerenciam pacientes, pacientes tiram dúvidas nutricionais com respostas personalizadas e sem alucinações. V1 é API REST completa + pipeline RAG, sem frontend.

**Core Value:** Paciente faz uma pergunta e recebe resposta personalizada baseada no perfil clínico + base de conhecimento nutricional — sem alucinações, sem sair do escopo.

## Current Position

- **Milestone:** v1.0 — NutriChat RAG MVP
- **Phase:** Not started (defining requirements)
- **Plan:** —
- **Status:** Defining requirements
- **Last activity:** 2026-05-19 — Milestone v1.0 started

## Progress

```
[░░░░░░░░░░] 0% — Milestone v1.0 initialized, roadmap pending
```

## Recent Decisions

- Stack defined: Django + DRF, SimpleJWT, PostgreSQL + pgvector, LangChain, Celery + Redis
- LLM: Claude (Anthropic) or GPT-4o (OpenAI) — switchable via `LLM_PROVIDER`
- Embedding: `text-embedding-ada-002` from OpenAI (1536 dims)
- Patient PK: UUID (never CPF) for LGPD compliance
- V1: API-only, no frontend

## Pending Todos

(None captured yet)

## Blockers / Concerns

(None)

## Session Continuity

Last session: 2026-05-19
Stopped at: STATE.md reconstructed from PROJECT.md — no phases exist yet
Resume file: None

---
*Reconstructed from PROJECT.md on 2026-05-19 — STATE.md was absent*
