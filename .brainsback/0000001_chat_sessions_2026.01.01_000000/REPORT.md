# Implementation Report

> A concise summary for the reviewer.

**Reviewer note**: If a PR modifies `.brainsback/<task-folder>/TODO.md` or `.brainsback/<task-folder>/REACTO.md`, assume this is expected and that those files were modified by the human developer.
If present, use `.github/skills/brainsback-reviewer/SKILL.md` as the review rubric.

## Snapshot
- **Change**: Implementacao de sidebar para historico de sessoes de chat
- **Status**: Completo (54 testes passando)

## The Changes
- [x] **`backend/models.py`** — Adicionado modelo `ChatSession` (id, title, created_at, updated_at, messages relationship). `ChatMessage` migrado de `session_key` string para `session_id` FK com cascade delete.
- [x] **`backend/schemas/chat.py`** — Adicionados schemas: `SessionOut`, `SessionListOut`, `SessionCreateIn`, `SessionUpdateIn`, `MessageOut`, `SessionMessagesOut`. `ChatRequest` ganhou campo opcional `session_id`. `ChatResponse` ganhou campo `session_id`.
- [x] **`backend/routers/chat.py`** — Adicionados endpoints REST: `GET /api/sessions`, `POST /api/sessions`, `GET /api/sessions/{id}`, `PATCH /api/sessions/{id}`, `DELETE /api/sessions/{id}`, `GET /api/sessions/{id}/messages`. Logica de auto-criacao de sessao no chat e geracao automatica de titulo a partir da primeira resposta do modelo (funcao `_generate_title`).
- [x] **`frontend/src/api.js`** — Adicionadas funcoes `fetchSessions`, `createSession`, `deleteSession`, `updateSessionTitle`, `fetchSessionMessages`. `sendMessageStream` agora aceita `sessionId` e `onDone` callback.
- [x] **`frontend/src/App.jsx`** — Reescrito com estado de sessoes (carregamento inicial, criacao, troca, exclusao). Sidebar com lista de sessoes, botao "Nova sessao", botao de excluir por item. Botao hamburguer no header para abrir/fechar sidebar. Overlay em mobile. Sincronizacao de titulos apos cada resposta.
- [x] **`frontend/index.html`** — Adicionados estilos CSS da sidebar (posicao fixed, animacao slide, overlay, botoes, item ativo, hover do delete).
- [x] **`tests/test_models.py`** — Atualizados testes para `ChatSession` e `ChatMessage` com `session_id` FK.
- [x] **`tests/test_chat.py`** — Adicionados 9 testes de sessao (CRUD, listagem, mensagens).
- [x] **`tests/test_schemas.py`** — Atualizado teste de `ChatResponse` com `session_id`.

## Testing Strategy
- Testes de modelo: criacao de sessao, titulo customizado, relacionamento com mensagens, cascade delete.
- Testes de API: CRUD completo de sessoes, listagem, validacao de 404, mensagens vazias.
- Testes de schema: ChatResponse com session_id.
- Testes existentes de chat e openrouter mantidos e passando.
- Frontend testado visualmente com os estilos inline no navegador.

## Fixes (segunda iteracao)
- **Sessao so e criada apos resposta do modelo**: `_get_session` substituiu `_get_or_create_session` — nunca cria sessao automaticamente. A sessao so nasce no `onDone` do stream (ou apos `generate_reply` no endpoint nao-stream).
- **Titulo usa contexto do prompt do usuario**: `_generate_title` agora recebe `user_message` + `reply` e prioriza o texto do usuario como fonte do titulo.
- **Frontend nao pre-cria sessoes**: `loadSessions` com lista vazia apenas mostra tela inicial sem criar sessao. `handleNewSession` limpa o chat com `activeSessionId = null` — a sessao sera criada pelo backend na primeira resposta.
- **`onDone` propaga `session_id`**: Frontend atualiza `activeSessionId` com o `session_id` vindo do backend no evento `done`.

## Risks & Follow-up
- [ ] O banco SQLite existente (`database/chat.db`) precisa ser removido para recriar o schema com a nova tabela `chat_sessions` e a FK `session_id`. Isso perde dados antigos.
- [ ] A geracao de titulo (`_generate_title`) prioriza a mensagem do usuario — pode ficar longo. Melhorias futuras: usar o modelo LLM para resumir.
- [ ] Sidebar usa estado React puro sem persistencia de "sidebar aberta/fechada" entre reloads.
- [ ] A exclusao da unica sessao restante e bloqueada pelo frontend, mas o backend permitiria — pode ser interessante validar no backend tambem.

---

## Tarefa 2 — Login e Logout

### Snapshot
- **Change**: Implementacao de autenticacao (signup, login, logout) via email e senha com persistencia SQLite
- **Status**: Completo (66 testes passando — 54 existentes + 12 novos)

### The Changes
- [x] **`backend/models.py`** — Adicionados modelos `User` (email_hash, password_hash) e `ApiToken` (token_hash, expires_at, active). Email armazenado como SHA-256 hash (privacidade). Senha armazenada como bcrypt hash.
- [x] **`backend/schemas/auth.py`** — Schemas `SignupRequest`, `LoginRequest`, `AuthResponse`, `LogoutResponse`, `MeResponse`.
- [x] **`backend/services/auth.py`** — Servico com `hash_email` (SHA-256), `hash_password`/`verify_password` (bcrypt via passlib), `create_jwt`/`decode_jwt` (HS256), e `generate_token` (opaco).
- [x] **`backend/routers/auth.py`** — Endpoints: `POST /api/auth/signup` (cria usuario, retorna JWT), `POST /api/auth/login` (valida credenciais, retorna JWT), `POST /api/auth/logout` (invalida token), `GET /api/auth/me` (valida token, retorna dados). Dependency `_get_current_user` para protecao de rotas. Email unico validado por hash (409 se duplicado).
- [x] **`backend/config.py`** — Adicionados `SECRET_KEY` e `TOKEN_EXPIRE_HOURS`.
- [x] **`backend/requirements.txt`** — Adicionados `passlib[bcrypt]` e `pyjwt`.
- [x] **`frontend/src/api.js`** — Funcoes `signup`, `login`, `logout`, `fetchMe`.
- [x] **`frontend/src/Login.jsx`** — Componente React com formulario de login/cadastro, toggle entre modos, validacao basica.
- [x] **`frontend/src/App.jsx`** — Estado `token`/`email` persistido em localStorage. Renderizacao condicional: tela de auth se nao logado, chat se logado. Botao "Sair" no footer da sidebar.
- [x] **`frontend/index.html`** — Estilos CSS da tela de auth (card centralizado, inputs, botao, toggle). Estilos do footer da sidebar com botao de logout. Script tag para `Login.jsx`.
- [x] **`tests/test_auth.py`** — 12 testes: signup (successo, duplicata 409, email invalido 422, senha curta 422), login (successo, senha errada 401, usuario inexistente 401), me (autenticado, sem token, token invalido), logout (successo, sem token).

### Seguranca
- Email nunca armazenado em texto puro — hash SHA-256 antes de persistir.
- Senha armazenada com bcrypt (via passlib).
- Token JWT com expiracao configravel (default 24h).
- Rotas protegidas por dependency `_get_current_user`.
- Email unico validado por unique constraint no hash.

### Risks & Follow-up
- [ ] SECRET_KEY deve ser alterada em producao (default: "change-me-in-production-use-a-long-random-string").
- [ ] Logout com JWT puro nao invalida server-side (token continua valido ate expirar) — para invalidacao real seria necessario blocklist.

---
**Note**: Usually filled by the AI.
