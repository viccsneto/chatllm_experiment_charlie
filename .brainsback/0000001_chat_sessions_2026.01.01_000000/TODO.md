# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem

I want to add a feature on my application so everytime the user starts chatting on a new chat a new session will be created already with a default session title based on what he is requesting, the user will be then be able to access at any time any previous session he already used and also create a new one by going into a new chat

## Steps

- [ ] create a button that allows the user to start a new chat from scratch
- [ ] add a scrollable component besides the chat window where the user will be able to see its old session
- [ ] everytime the user starts a new chat a session will be created for it and it will be placed on the scrollable component
- [ ] the information shared in each chat should be restricted to its own session
- [ ] the user should be able to see the whole history of message exchange on the session

## Success Looks Like

- [ ] The endpoint returns 200 OK with the user object, NOT Code compiles
- [ ] All chats sessions are being correctly stored on the databased and returned to the client
- [ ] User is able to request information of different session and have a successfull return from the backend
- [ ] A new session will be created everytime the user starts a new chat

## Notes

- [ ] _Any specific edge cases, libraries to consider, or potential pitfalls._

---

**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
