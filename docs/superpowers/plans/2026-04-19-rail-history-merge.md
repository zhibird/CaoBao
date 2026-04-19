# Rail History Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the conversation history list into the existing left workspace rail so the chat UI uses a single sidebar instead of a rail plus a separate conversation column.

**Architecture:** Keep the current rail expand/collapse state machine and persistence intact. Move the history DOM into the rail, collapse the workspace shell back to a single main column, and simplify the frontend state so conversation history no longer behaves like a separate recall surface.

**Tech Stack:** FastAPI static assets, vanilla HTML/CSS/JavaScript, pytest

---

### Task 1: Lock the single-sidebar structure with web asset tests

**Files:**
- Modify: `tests/test_web_assets.py`

- [ ] Update the asset tests so they expect the history list inside `#workspaceRail` and no longer expect a standalone `#conversationDrawer`.
- [ ] Run the focused web asset tests and confirm the new expectations fail before implementation.

### Task 2: Move history markup into the rail

**Files:**
- Modify: `app/web/index.html`

- [ ] Add a dedicated history section inside `#workspaceRail` that contains the section title, status region, and `#historyList`.
- [ ] Remove the standalone conversation sidebar markup from the workspace shell.

### Task 3: Rebuild the desktop layout around one sidebar

**Files:**
- Modify: `app/web/styles.css`

- [ ] Collapse `workspace-shell` back to a single main column.
- [ ] Add rail-internal history section styles, compact history row styles, and expanded-only visibility for the history list.
- [ ] Remove desktop-specific styling that assumes a persistent second conversation column.

### Task 4: Simplify rail behavior in frontend logic

**Files:**
- Modify: `app/web/app.js`

- [ ] Remove conversation drawer element bindings and event handlers.
- [ ] Make the rail conversation button expand/focus the in-rail history section instead of toggling a separate conversation surface.
- [ ] Keep file/settings surface behavior intact.

### Task 5: Verify the merge

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/index.html`
- Modify: `app/web/styles.css`
- Modify: `app/web/app.js`

- [ ] Run focused `tests/test_web_assets.py` coverage for the sidebar merge.
- [ ] Run the broader web asset suite to catch accidental regressions.
