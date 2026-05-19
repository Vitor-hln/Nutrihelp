# NutriChat RAG

## What This Is

Plataforma web de nutrição com dois perfis: nutricionistas que criam e gerenciam pacientes com dados clínicos e planos alimentares, e pacientes que consultam seu plano e tiram dúvidas com um assistente de IA. O assistente usa RAG (Retrieval-Augmented Generation) — busca na base de conhecimento nutricional e combina com o perfil clínico do paciente para gerar respostas precisas e personalizadas. V1 entrega API REST completa + pipeline RAG, sem frontend.

## Core Value

Paciente faz uma pergunta sobre substituição ou dúvida nutricional e recebe uma resposta personalizada baseada no seu perfil clínico e na base de conhecimento — sem alucinações e sem ultrapassar o escopo nutricional.

## Current Milestone: v1.0 NutriChat RAG — MVP

**Goal:** Entregar API REST completa com autenticação JWT, gerenciamento de pacientes LGPD-compliant e pipeline RAG funcional com busca semântica em pgvector.

**Target features:**
- Autenticação de nutricionista (CRN, CPF, JWT access + refresh)
- CRUD de pacientes com isolamento por nutricionista
- Pipeline RAG: indexação de documentos + busca semântica via pgvector
- Assistente de IA com escopo restrito a nutrição
- Indexação assíncrona de documentos via Celery
- Conformidade LGPD (UUID como PK, CPF nunca em URLs, consentimento registrado)

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Nutricionista pode se cadastrar com CRN e CPF
- [ ] Nutricionista pode fazer login e receber JWT (access + refresh)
- [ ] Nutricionista pode criar, listar, editar e remover pacientes vinculados a si
- [ ] Paciente só acessa seus próprios dados (isolamento por nutricionista)
- [ ] Paciente pode iniciar conversas e enviar mensagens
- [ ] Assistente responde usando RAG: busca semântica em pgvector + perfil clínico do paciente
- [ ] Assistente respeita escopo restrito (apenas nutrição, substituições, plano alimentar)
- [ ] Documentos nutricionais podem ser indexados assincronamente via Celery
- [ ] Pipeline suporta Anthropic (Claude) e OpenAI — troca via variável de ambiente
- [ ] CPF nunca exposto em URLs ou listagens (LGPD Art. 11)
- [ ] Dados sensíveis (condições de saúde, histórico) não vazam entre pacientes
- [ ] Consentimento LGPD registrado no cadastro do paciente

### Out of Scope

- Frontend (React/Django Templates) — v1 é API-only; UI planejada para v2
- Autenticação de pacientes via OAuth/magic link — SimpleJWT é suficiente para v1
- Multi-tenancy com planos pagos/billing — fora do escopo do produto
- Cálculo automático de planos alimentares pelo sistema — nutricionista define manualmente
- Integração com wearables ou apps de saúde externos — complexidade desnecessária em v1

## Context

- Stack decidida: Django + DRF, SimpleJWT, PostgreSQL + pgvector, LangChain, Celery + Redis
- LLM: Claude (Anthropic) ou GPT-4o (OpenAI) — configurável via `LLM_PROVIDER` no `.env`
- Embedding: `text-embedding-ada-002` da OpenAI (1536 dimensões) — ajustável se trocar modelo
- Arquitetura modular com 3 apps Django: `accounts`, `chat`, `knowledge`
- Regra de isolamento crítica: toda query de paciente filtra por `nutricionista=request.user.perfil_nutricionista`
- PK de paciente é UUID (nunca CPF) para proteger dados em URLs e logs
- Tamanho do roadmap: Etapas 1-7 conforme `guia_implementacao(3).md` — Etapa 8 (frontend) fora de v1

## Constraints

- **Tech Stack**: Django + PostgreSQL + pgvector — decisão tomada, sem substituições
- **LGPD**: Dados de saúde (Art. 11) exigem UUID como PK, CPF nunca em URLs, logs sem dados pessoais
- **Escopo do assistente**: Apenas nutrição — qualquer desvio deve retornar mensagem padrão de redirecionamento
- **Isolamento de dados**: Nutricionista A nunca vê pacientes do nutricionista B — regra inegociável em todas as queries

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| pgvector no lugar de Pinecone/Weaviate | Evita dependência externa, integra nativamente ao Django ORM | — Pending |
| LangChain para orquestrar RAG | Abstrai complexidade do pipeline, facilita troca de embeddings/LLMs | — Pending |
| Celery + Redis para indexação | Indexação de documentos não bloqueia a API REST | — Pending |
| UUID como PK de PerfilPaciente | LGPD — não expõe dados sensíveis em URLs, logs ou FKs | — Pending |
| V1 API-only (sem frontend) | Reduz escopo, valida o backend e o pipeline RAG antes de investir em UI | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-19 — Milestone v1.0 started*
