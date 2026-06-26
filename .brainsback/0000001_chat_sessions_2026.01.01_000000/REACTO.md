# Proof of Mastery (REACTO)

> Explain it to prove you own it.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## R — Repeat (The Problem)
The user needs to have session management for the chatllm, so, he should be able to create new sessions, choose what session to use. Sessions can also be created automatically if the first message does not be sended inside a already existing session. Each session should have a separated context and history of messages.

## E — Examples
_Provide concrete inputs and expected outputs that demonstrate the correctness. Base them on observable behavior._

- **Happy Path Input**: user sends a new message outside a session
  **Output**: a new session is created

- **Happy Path Input**: user sends the first message of the session
  **Output**: after the model answer, is should rename the session to a name that is related to the session topic

- **Happy Path Input**: user change to another session
  **Output**: all the message history and context is changed from the old session to the new one.

- **Edge Case Input**: User creates many sessions but does not send any message on them
  **Output**: The session should only be persisted after sending a message. Only the current new session should be open in the frontend while the user does not send any message

  - **Edge Case Input**: User is outside a session
  **Output**: The session sidebar should have the name "new session" while the user does not send any message.

## A — Approach
I designed like each session is unique, having its own messages contained in itself, and the user can switch between them as needed.

## C — Code
In Backend:
The addition of session schemas in the backend/schemas/chat and the Session class model in models.py - It's the persistence and data transfer definitions. It connects the messages with the sessions so it keeps the sessions isolated.
The sessions router itself, in backend/routers/sessions - It routes the new requests related to sessions to perform the needed operations.
A table was used to store the sessions using a cascade delete FK, so when the user deletes the session, all messages related are deleted together, cleaning the db.
O título atualmente é extraido dos primeiros caracteres da primeira resposta de cada sessão.

In Frontend:
The addition of frontend/src/Sidebar.jsx and the modifications at api.js - They are needed to perform que requests to get the sessions and the messages that are now attached to the sessions and rendering on the screen.
The changes in App.jsx are critical too, because there is the code to handle the sessions itself.
needsMessageLoadReft é usado para controlar quando é preciso recarregar o histórico.

## T — Tests
there are three principal test files, one for the models of the db, one for the schemas of the data objects and one specific for the sessions. They test the paths that the user can have in the code:

test_models.py: sessions specific testes were added to test the session creation, the delete (with cascade) and the relation with messages

test_schemas.py: Tests to check the schema integrity, should be used to alert if a schema change is made, which can break frontend.

test_sessions_api.py: Tests all the api routes related to sessions.

Manual test were made: Creation of a new session using the button and automatically with the first message. Session title check. Refreshing page in any step to check behaviour.

## O — Optimize
Currently the session only runs if it is selected, it can be implemented to do background processing, but this can became slow if optimization is not taken into account.

The stream of message is a little slow, but this is because of the llm model itself, so it is out of control of the implementation.
