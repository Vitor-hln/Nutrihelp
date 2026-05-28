---
phase: 1
slug: infrastructure-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Django TestCase (nativo) + smoke tests de infra via shell/curl |
| **Config file** | `manage.py test` (integrado ao Django) |
| **Quick run command** | `docker compose up -d && docker compose ps` |
| **Full suite command** | `docker exec -it nutrihelp_django uv run manage.py test` |
| **Estimated runtime** | ~60 seconds (infra smoke) |

---

## Sampling Rate

- **After every task commit:** Run `docker compose up -d && docker compose ps` — todos os containers `Up`
- **After every plan wave:** curl para admin + pgvector check + Celery ping
- **Before `/gsd-verify-work`:** Todos os 5 critérios de sucesso verificados
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01 | T-1-01 | SECRET_KEY obrigatória — entrypoint falha se ausente | smoke | `docker compose config --quiet && echo OK` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | INFRA-01 | — | Todos os 6 serviços sobem sem erros | smoke/infra | `docker compose up -d && docker compose ps` — todos `Up` | N/A | ⬜ pending |
| 1-01-03 | 01 | 1 | INFRA-01 | — | pgvector extension ativa | smoke | `docker exec nutrihelp_postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dx" \| grep vector` | N/A | ⬜ pending |
| 1-01-04 | 01 | 1 | INFRA-01 | — | Celery conecta ao Redis | smoke | `docker exec nutrihelp_celery uv run celery -A control inspect ping` | N/A | ⬜ pending |
| 1-02-01 | 02 | 1 | INFRA-02 | — | Django admin responde em 3600 | smoke | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3600/admin/` == 200 | N/A | ⬜ pending |
| 1-02-02 | 02 | 1 | INFRA-02 | — | Dados persistem após restart | smoke/manual | `docker compose down && docker compose up -d` + verificar dados no banco | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `nutrihelp_app/control/tests.py` — `SimpleTestCase` que verifica `SECRET_KEY` presente e `DATABASES` configurado
- [ ] Smoke script `scripts/smoke_test.sh` — verifica todos os 5 critérios de sucesso via shell/curl

*Nota: Não há testes Django formais de aplicação nesta fase (nenhum app instalado ainda). Smoke tests são verificações de infra via shell/curl.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dados persistem após restart | INFRA-02 | Requer intervenção humana para verificar estado do banco | `docker compose down && docker compose up -d`, então `docker exec nutrihelp_postgres psql -U $USER -d $DB -c "SELECT * FROM django_migrations LIMIT 5;"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
