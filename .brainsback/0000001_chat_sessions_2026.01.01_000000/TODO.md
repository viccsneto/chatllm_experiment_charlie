# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem

I need to implement a new sessions feature on the application. The sessions should be visible on the sidebar (like chatgpt), and the user can create and change sessions as needed. This will be used to have multiple conversations with different contexts. Each session should have its own title and history, and the title should be derived from the first llm answer.

## Steps
- [ ] Read the current repository to get the current patterns and technologies used.
- [ ] Implement the creation of sessions, it should have a button to create a new session, and when the app is open, it should start on a new session by default.
- [ ] Implement the session switching feature. The user should be able to switch sessions using the sidebar anytime he wants.
- [ ] Implements the session history. Each session should be self contained and have its own context.
- [ ] Implements automatic session title, it should be derived from the first llm model answer.
- [ ] Keep every new code aligned with the current code and folders patterns.
- [ ] For each implementation, write tests to make sure that everything is working.

## Success Looks Like
- [ ] The user can create and switch sessions effortless
- [ ] When the app is first open, if the user does not choose a existing section, the first message should create a new session
- [ ] When the user switch sessions, it should only shows the history of the session and nothing more
- [ ] When the model answer for the first time, the session should be persisted on the sidebar with a meaningful title

## Notes
- [ ] Maybe multithreading is needed to keep running background prompts when user switchs session. Be careful with that.

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
