# Proof of Mastery (REACTO)

> Explain it to prove you own it.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## R — Repeat (The Problem)

previously the application lacked the option to store the user chat history in sessions that he could go back to read or restart the conversation where it stopped and also delete the session completly if required

## E — Examples

_Provide concrete inputs and expected outputs that demonstrate the correctness. Base them on observable behavior._

- **Happy Path Input**: user clicks the "Nova conversa" button
  **Output**: a new chat session will be created with an auto generated title where the user can talk without mixing with previous chats exchanges

- **Edge Case Input**: the user starts chatting without clicking the "Nova conversa" button when the page loads the first time
  **Output**: when the page loads the first time a new session should be ready to be initialized without the need to click on the "Nova conversa" button

## A — Approach

the solution was thought based on the expected behavior I was already familiar with from similar applications

## C — Code

on the backend a new class was added in models.py to represent the session, then the schema for the chats was updated on schemas/chat.py in a way it would be able to support the features planned in adition to that a entire crud was created for sessions routers/sessions.py so the frontend would be able to request the backend to list the sessions and also get one specific session as well as delete one session, the router of the chat was also modified routers/chat.py so the code could perform the functions to generate the title, indentify in which session it was and know when a new session started and ended. The changes on the frontend included the adition of function to access the new endpoints the backend created src/api.js, the creation of the component to display all the available session and now keeping track of the current session id so the requests to the backend could send this information

## T — Tests

The feature was validated by manually testing the planned flows previous described to the chat directly on the browser interface and also by the automated tests on the project, which was able to initially find some errors made by the model and in sequence correct by them, the automated tests were in the tests folder and validated the whole flow including the frontend payload sent and the api returns, they were important to make sure the new feature did not break anything that was already working and in adition to them the model also generated new tests to cover the new flows added

## O — Optimize

_Address Big(O) complexity, note that sometimes it doesn't apply, trade-offs, constraints, and opportunities for future improvement._
