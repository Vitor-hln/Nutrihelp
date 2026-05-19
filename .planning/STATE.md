# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** Paciente faz uma pergunta e recebe resposta personalizada baseada no perfil clínico + base de conhecimento nutricional — sem alucinações, sem sair do escopo.
**Current focus:** Phase 1 — Infrastructure Foundation

## Current Position

Phase: 1 of 7 (Infrastructure Foundation)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-05-19 — Roadmap created, 7 phases defined for v1.0

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Stack: Django + DRF, SimpleJWT, PostgreSQL + pgvector, LangChain, Celery + Redis
- LLM: Claude or GPT-4o via `LLM_PROVIDER`; Ollama for local dev
- Embedding: `text-embedding-ada-002` (1536 dims) — VectorField dimensions set at migration time, not changeable without dropping column
- Patient PK: UUID (LGPD — CPF never in URLs or FKs)
- LangChain used for embeddings only; LangChain PGVector class NOT used (bypasses Django ORM/migrations)
- Knowledge base (`Documento` + `Chunk`) is intentionally global — not per-nutritionist in v1

### Pending Todos

None yet.

### Blockers/Concerns

None.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-19
Stopped at: Roadmap written — 7 phases, 30/30 requirements mapped
Resume file: None
