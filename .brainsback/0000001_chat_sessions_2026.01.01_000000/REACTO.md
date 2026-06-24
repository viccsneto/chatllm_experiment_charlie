# Proof of Mastery (REACTO)

> Explain it to prove you own it.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## R — Repeat (The Problem)
- The system must support multiple independent chat sessions per user.
- Each session must store its own message history.
- A session is automatically created when the model generates the first response.
- The session title must be generated based on the first model response context.
- The user must be able to:
  - View all sessions in a sidebar
  - Create a new session manually
  - Switch between sessions
  - Hide/show the sidebar
  - When switching sessions, the correct history must be loaded without mixing messages.

## E — Examples
SessionOut
Represents a single chat session returned from the API.

{
  "id": 1,
  "title": "Discussing React architecture",
  "created_at": "2026-06-22T14:10:00Z",
  "updated_at": "2026-06-22T14:35:00Z"
}

SessionListOut
Represents the sidebar response containing all sessions for a user.

{
  "sessions": [
    {
      "id": 3,
      "title": "Debugging authentication error",
      "created_at": "2026-06-22T13:00:00Z",
      "updated_at": "2026-06-22T13:40:00Z"
    },
    {
      "id": 2,
      "title": "Planning sidebar feature",
      "created_at": "2026-06-21T18:20:00Z",
      "updated_at": "2026-06-21T19:10:00Z"
    }
  ]
}

SessionCreateIn
Payload used when creating a new session manually.

{
  "title": "Nova sessao"
}

MessageOut
Represents a single message inside a session.

{
  "id": 10,
  "session_id": 1,
  "role": "assistant",
  "content": "To implement a sidebar, you need to manage session state...",
  "model": "gpt-4.1-mini",
  "created_at": "2026-06-22T14:12:30Z"
}

Example user message:

{
  "id": 9,
  "session_id": 1,
  "role": "user",
  "content": "How do I structure chat sessions in a database?",
  "model": "user",
  "created_at": "2026-06-22T14:12:00Z"
}

SessionMessagesOut
Represents the full message history of a session.

{
  "messages": [
    {
      "id": 9,
      "session_id": 1,
      "role": "user",
      "content": "How do I structure chat sessions in a database?",
      "model": "user",
      "created_at": "2026-06-22T14:12:00Z"
    },
    {
      "id": 10,
      "session_id": 1,
      "role": "assistant",
      "content": "You should create a sessions table and link messages via session_id...",
      "model": "gpt-4.1-mini",
      "created_at": "2026-06-22T14:12:30Z"
    }
  ]
}

## A — Approach
The system is designed around the concept of independent chat sessions, where each session contains its own isolated message history. When a user starts interacting with the system, a session is automatically created if one does not already exist, and all subsequent messages are attached to that session through a session_id.

Sessions are stored in the database with basic metadata such as id, title, created_at, and updated_at. Messages are stored separately and linked to their respective session using session_id, ensuring complete separation between different conversations.

On the backend, there are simple operations for creating sessions, listing them, and retrieving messages for a specific session. A default title is assigned when a session is created, and it can later be updated, typically after the first assistant response, which is used to generate a more meaningful name.

On the frontend, the sidebar is responsible for displaying all user sessions and allowing the user to switch between them. When a session is selected, the application fetches and renders only the messages belonging to that session. Creating a new chat simply initializes a new empty session and sets it as active.

Overall, the approach ensures clear separation of concerns: sessions manage context, messages store conversation data, and the UI only reflects the currently active session without mixing states between different conversations.

## C — Code
_backend/routers/chat.py_

Two critical design decisions here:

_get_session (line 215) never creates a session. The old pattern would have been _get_or_create_session. The inversion is intentional: sessions only exist if the model replied. Ghost sessions from aborted requests are impossible.

In both /api/chat and /api/chat/stream, session creation happens via db.flush() (not db.commit()) before the ChatMessage inserts. This keeps the whole write — session + both messages — in a single transaction. If the commit fails, no partial state is persisted.

backend/services/openrouter.py

generate_title_from_context keeps a hard 15s timeout and silently returns "Nova sessao" on any error. The fallback chain in _generate_title (router) is: LLM title → first sentence of user message (10–80 chars) → truncated input → literal "Nova sessao". The title never blocks the response path — it runs before the messages are persisted but the title failure is non-fatal.

## T — Tests
tests/test_models.py — TestChatSession (4 tests)

test_create_session_defaults — asserts default title, created_at, updated_at are populated
test_create_session_custom_title — round-trips a custom title through the DB
test_session_has_messages_relationship — verifies the bidirectional ORM relationship
test_delete_session_cascades_messages — the most important: deletes a session and asserts ChatMessage count is zero. Validates both ORM cascade and that no messages are left as orphans
All existing TestChatMessage tests were updated to require a real ChatSession FK — this is correct and prevents the test suite from running against a schema that doesn't match production.

tests/test_chat.py — TestSessionEndpoints (9 tests)

Covers full CRUD: list (empty), create (with/without title), get, get-404, patch, delete (+ confirms 404 after), messages list (empty), messages-404. The delete test does a follow-up GET to confirm the row is gone — not just asserting 204.

tests/test_schemas.py

test_valid_response updated to include session_id=1 — catches schema regressions where session_id is dropped from ChatResponse.

Frontend manually validated (visually).

## O — Optimize
Complexity is not a concern here — session counts are small (tens, not millions), message counts are bounded by LLM context limits (~hundreds per session).
