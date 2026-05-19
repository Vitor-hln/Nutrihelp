# Requirements — NutriChat RAG v1.0

## Milestone v1.0: NutriChat RAG MVP

**Goal:** API REST completa com autenticação JWT, gerenciamento de pacientes LGPD-compliant e pipeline RAG funcional com busca semântica em pgvector.

---

## v1.0 Requirements

### AUTH — Autenticação e LGPD Baseline

- [ ] **AUTH-01**: Nutricionista pode se cadastrar com email, CRN e CPF
- [ ] **AUTH-02**: Nutricionista pode fazer login e receber JWT (access + refresh)
- [ ] **AUTH-03**: Nutricionista pode fazer logout com blacklist do refresh token
- [ ] **AUTH-04**: Access token pode ser renovado via refresh token
- [ ] **AUTH-05**: Paciente pode fazer login e receber JWT com role claim `paciente`
- [ ] **AUTH-06**: UUID é a PK do perfil de paciente — CPF nunca aparece em URLs ou FKs
- [ ] **AUTH-07**: CPF é `write_only=True` em todos os serializers — nunca exposto em respostas
- [ ] **AUTH-08**: `lgpd_consent` + timestamp registrado no cadastro do paciente (obrigatório)
- [ ] **AUTH-09**: Log scrubber remove CPF automaticamente de todos os logs Django
- [ ] **AUTH-10**: Permissões por role: `IsNutricionista`, `IsPaciente`, `IsPacienteDoNutricionista`

### PAT — Gerenciamento de Pacientes

- [ ] **PAT-01**: Nutricionista pode criar paciente vinculado a si com campos clínicos completos
- [ ] **PAT-02**: Nutricionista pode listar apenas seus próprios pacientes
- [ ] **PAT-03**: Nutricionista pode editar dados clínicos de seus pacientes
- [ ] **PAT-04**: Nutricionista pode desativar (soft delete) um paciente
- [ ] **PAT-05**: Acesso cross-tenant retorna 404 (não 403) — não revela existência do paciente
- [ ] **PAT-06**: Perfil clínico inclui tipo dietético, condições de saúde, status bariátrico, macros e restrições alimentares

### DOC — Pipeline de Documentos

- [ ] **DOC-01**: Nutricionista pode fazer upload de PDF
- [ ] **DOC-02**: Upload retorna `202 Accepted` imediatamente — processamento é assíncrono
- [ ] **DOC-03**: Indexação ocorre em background via Celery, disparado por `transaction.on_commit`
- [ ] **DOC-04**: Documento tem status rastreável: `pending → processing → indexed / failed`
- [ ] **DOC-05**: Texto extraído via pdfplumber (PDFs text-nativos; OCR adiado para v1.x)
- [ ] **DOC-06**: Cada chunk armazena `nutritionist_id` como metadado de isolamento de tenant
- [ ] **DOC-07**: Nutricionista pode consultar status de indexação dos seus documentos

### RAG — Pipeline de IA

- [ ] **RAG-01**: Busca semântica usa `CosineDistance` + `HnswIndex` no pgvector
- [ ] **RAG-02**: `ScopedRetriever` filtra por `nutritionist_id` em toda busca — nunca cruza tenants
- [ ] **RAG-03**: Classificador pré-retrieval verifica se a pergunta é sobre nutrição antes de buscar
- [ ] **RAG-04**: Perguntas fora de escopo retornam mensagem padrão de redirecionamento
- [ ] **RAG-05**: Prompt builder injeta perfil clínico do paciente + chunks recuperados no contexto
- [ ] **RAG-06**: LLM client suporta Ollama (dev local), Claude (Anthropic) e OpenAI via `LLM_PROVIDER`

### CHAT — Assistente de IA

- [ ] **CHAT-01**: Paciente pode enviar mensagem e receber resposta RAG
- [ ] **CHAT-02**: Cada paciente tem uma única conversa persistida
- [ ] **CHAT-03**: Histórico de conversa salvo no PostgreSQL — nunca em memória
- [ ] **CHAT-04**: `trim_messages` aplicado antes de cada chamada LLM para respeitar context window

### INFRA — Infraestrutura e Qualidade

- [ ] **INFRA-01**: Docker Compose completo: Django + Celery + Redis + PostgreSQL/pgvector + Ollama
- [ ] **INFRA-02**: Ambiente local funcional com um único `docker compose up`
- [ ] **INFRA-03**: Suite de testes de isolamento: cross-tenant 404 em todos os endpoints de paciente e chat
- [ ] **INFRA-04**: Rate limiting no endpoint de chat por paciente
- [ ] **INFRA-05**: Documentação de API via drf-spectacular (Swagger/OpenAPI)

---

## Future Requirements (v1.x)

- OCR para PDFs escaneados (Tesseract ou cloud Vision API)
- Visualização do histórico de conversas do paciente pelo nutricionista
- Validação de CRN contra base externa
- Atribuição de fonte/documento na resposta do assistente
- Agendamento de reindexação de documentos

## Out of Scope — v1.0

- **Frontend** (React/Django Templates) — v1 é API-only; UI planejada para v2
- **Múltiplas conversas por paciente** — paciente tem uma única conversa em v1
- **OAuth/magic link para paciente** — SimpleJWT é suficiente para v1
- **Streaming de respostas** — síncrono é aceitável para MVP; streaming avaliado em v1.x
- **Cálculo automático de planos alimentares** — nutricionista define manualmente
- **Integração com wearables** — complexidade desnecessária em v1
- **Multi-tenancy com billing** — fora do escopo do produto
- **Row-level security no PostgreSQL** — aplicação garante isolamento; RLS avaliado para v2
- **Criptografia de CPF em repouso** — hash/write-only é suficiente para v1; criptografia avaliada após orientação jurídica LGPD

---

## Traceability

*Filled by roadmapper — maps each REQ-ID to the phase that delivers it.*

| REQ-ID | Phase | Status |
|--------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| AUTH-06 | Phase 2 | Pending |
| AUTH-07 | Phase 2 | Pending |
| AUTH-08 | Phase 2 | Pending |
| AUTH-09 | Phase 2 | Pending |
| AUTH-10 | Phase 2 | Pending |
| PAT-01 | Phase 3 | Pending |
| PAT-02 | Phase 3 | Pending |
| PAT-03 | Phase 3 | Pending |
| PAT-04 | Phase 3 | Pending |
| PAT-05 | Phase 3 | Pending |
| PAT-06 | Phase 3 | Pending |
| DOC-01 | Phase 4 | Pending |
| DOC-02 | Phase 4 | Pending |
| DOC-03 | Phase 4 | Pending |
| DOC-04 | Phase 4 | Pending |
| DOC-05 | Phase 4 | Pending |
| DOC-06 | Phase 4 | Pending |
| DOC-07 | Phase 4 | Pending |
| RAG-01 | Phase 5 | Pending |
| RAG-02 | Phase 5 | Pending |
| RAG-03 | Phase 5 | Pending |
| RAG-04 | Phase 5 | Pending |
| RAG-05 | Phase 5 | Pending |
| RAG-06 | Phase 5 | Pending |
| CHAT-01 | Phase 6 | Pending |
| CHAT-02 | Phase 6 | Pending |
| CHAT-03 | Phase 6 | Pending |
| CHAT-04 | Phase 6 | Pending |
| INFRA-03 | Phase 7 | Pending |
| INFRA-04 | Phase 7 | Pending |
| INFRA-05 | Phase 7 | Pending |

---

*Last updated: 2026-05-19 — Traceability filled by roadmapper*
