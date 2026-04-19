# Chat Workbench Mixed Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the mixed chat-workbench redesign so CaiBao launches new conversations with guided starter actions, shifts into an immersive chat stage after the first message, and recalls conversations/files/settings through adaptive surfaces instead of a permanently expanded sidebar.

**Architecture:** Keep the existing FastAPI-served static frontend and reuse working primitives such as `historyList`, `documentList`, `previewDrawer`, `settingsModal`, and `authModal`, but reshape the shell into explicit workspace stages and recall surfaces. Drive the redesign from a small state machine in `app/web/app.js`, back it with updated shell markup in `app/web/index.html`, and express layout/motion/responsive behavior in `app/web/styles.css` while locking the behavior with `pytest` asset tests in `tests/test_web_assets.py`.

**Tech Stack:** FastAPI static asset serving, vanilla HTML/CSS/JavaScript, pytest, FastAPI `TestClient`

---

## File Map

- **Modify:** `app/web/index.html`
  - Replace the always-open sidebar shell with a narrow rail plus dedicated conversation/file recall drawers.
  - Keep existing modal/drawer ids where possible, but add stage-aware shell ids for the new launch/chat layout.
  - Remove the current always-visible composer status row and replace it with a dock context row.

- **Modify:** `app/web/styles.css`
  - Add layout rules for `workspace-rail`, `surface-drawer`, `launch-panel`, and `composer-dock`.
  - Update responsive breakpoints so desktop uses a narrow rail and mobile uses overlay surfaces.
  - Add low-amplitude transition rules and a `prefers-reduced-motion` block.

- **Modify:** `app/web/app.js`
  - Add explicit workspace-stage and active-surface state.
  - Rewire existing conversation/document/settings/auth flows to open recall surfaces on demand.
  - Replace the current hero visibility toggle with a stage-aware launch/chat transition.
  - Render a composer context row from existing chat mode + document state instead of the current status pill row.

- **Modify:** `tests/test_web_assets.py`
  - Add shell assertions for rail/drawer/dock markup.
  - Add script assertions for the workspace-stage/surface state machine and Escape handling.
  - Add stylesheet assertions for rail/drawer/dock selectors and reduced-motion coverage.

## Task 1: Reshape the HTML Shell Around Rail, Drawers, and Dock

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/index.html`

- [ ] **Step 1: Write the failing shell tests**

Add these tests near the existing frontend shell assertions in `tests/test_web_assets.py`:

```python
def test_homepage_uses_workspace_rail_and_recall_drawers(client) -> None:
    html = _get_web_index(client)

    assert 'id="workspaceRail"' in html
    assert 'id="railNewChatBtn"' in html
    assert 'id="railConversationsBtn"' in html
    assert 'id="railFilesBtn"' in html
    assert 'id="railSettingsBtn"' in html
    assert 'id="conversationDrawer"' in html
    assert 'id="fileDrawer"' in html


def test_homepage_uses_launch_panel_and_dock_context_row(client) -> None:
    html = _get_web_index(client)

    assert 'id="heroPanel"' in html
    assert 'class="launch-panel"' in html
    assert 'id="composerContextRow"' in html
    assert 'class="composer-status-row"' not in html
```

- [ ] **Step 2: Run the shell tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "workspace_rail or launch_panel" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_homepage_uses_workspace_rail_and_recall_drawers
FAILED tests/test_web_assets.py::test_homepage_uses_launch_panel_and_dock_context_row
```

- [ ] **Step 3: Update `app/web/index.html` to introduce the new shell**

Replace the current sidebar shell with a narrow rail and move the existing conversation/file lists into dedicated recall drawers while preserving `historyList` and `documentList` ids:

```html
<div class="shell">
  <aside id="workspaceRail" class="workspace-rail" aria-label="Workspace navigation">
    <button id="railNewChatBtn" class="rail-btn rail-btn-primary" type="button" title="New chat">+</button>
    <button id="railConversationsBtn" class="rail-btn" type="button" title="Conversations">C</button>
    <button id="railFilesBtn" class="rail-btn" type="button" title="Files">F</button>
    <button id="railSettingsBtn" class="rail-btn rail-btn-bottom" type="button" title="Me / Settings">Me</button>
  </aside>

  <div class="workspace-shell">
    <aside id="conversationDrawer" class="surface-drawer conversation-drawer hidden" aria-hidden="true">
      <section class="surface-panel">
        <div class="surface-head">
          <p class="section-title">Conversations</p>
          <button id="drawerNewChatBtn" class="primary-btn compact-primary-btn" type="button">New chat</button>
        </div>
        <ul id="historyList" class="history-list"></ul>
      </section>
    </aside>

    <aside id="fileDrawer" class="surface-drawer file-drawer hidden" aria-hidden="true">
      <section class="surface-panel">
        <div class="surface-head">
          <p class="section-title">Files</p>
        </div>
        <ul id="documentList" class="document-list"></ul>
      </section>
    </aside>

    <main class="main-pane">
      <section id="heroPanel" class="hero-panel launch-panel">
        <div class="hero-copy">
          <div class="hero-kicker">CaiBao Assistant</div>
          <h2 id="heroTitle">Start with a question, then add files only when needed.</h2>
          <p id="heroSubtitle" class="hero-subtitle">Use a starter card below or type directly into the composer.</p>
        </div>
        <div id="scenarioCards" class="scenario-cards">
          <button class="scenario-card" type="button" data-scene="direct">
            <strong>Direct Chat</strong>
            <span>Ask immediately, brainstorm, or refine an expression.</span>
          </button>
          <button class="scenario-card" type="button" data-scene="plan">
            <strong>Plan Writing</strong>
            <span>Start from goals, milestones, risks, and acceptance criteria.</span>
          </button>
          <button class="scenario-card" type="button" data-scene="qa">
            <strong>Doc Assist</strong>
            <span>Use attached files only when grounding or retrieval is needed.</span>
          </button>
        </div>
      </section>

      <section class="composer-zone composer-dock">
        <div id="composerContextRow" class="composer-context-row hidden"></div>
        <div class="composer">
          <button id="toggleImportBtn" class="icon-btn" type="button" title="Add attachment">+</button>
          <div class="composer-input-shell">
            <textarea id="messageInput" rows="1" placeholder="Type your request. Press Enter to send, Shift+Enter for newline."></textarea>
            <div class="composer-footnote">
              <span id="composerHint">Use the dock to chat first; attach files only when needed.</span>
              <span class="composer-shortcut">Enter Send / Shift+Enter New line</span>
            </div>
          </div>
          <button id="sendBtn" class="send-btn" type="button">Send</button>
        </div>
      </section>
    </main>
  </div>
</div>
```

Delete the current:

```html
<div class="composer-status-row">
  <div id="composerPresence" class="composer-status-pill">Workspace not set</div>
  <div id="composerScope" class="composer-status-pill">Scope - 0 files</div>
  <div id="composerSession" class="composer-status-pill">Smart config - default</div>
</div>
```

- [ ] **Step 4: Run the shell tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "workspace_rail or launch_panel" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_homepage_uses_workspace_rail_and_recall_drawers
PASSED tests/test_web_assets.py::test_homepage_uses_launch_panel_and_dock_context_row
```

- [ ] **Step 5: Commit the HTML shell change**

Run:

```bash
git add tests/test_web_assets.py app/web/index.html
git commit -m "feat: add chat workspace rail shell"
```

## Task 2: Add an Explicit Workspace Stage and Recall-Surface State Machine

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/app.js`

- [ ] **Step 1: Write the failing script-state tests**

Append these tests to `tests/test_web_assets.py`:

```python
def test_frontend_tracks_workspace_stage_and_active_surface(client) -> None:
    script = _get_web_app_script(client)

    assert 'const WORKSPACE_STAGE_LAUNCH = "launch"' in script
    assert 'const WORKSPACE_STAGE_CHAT = "chat"' in script
    assert 'const ACTIVE_SURFACE_NONE = "none"' in script
    assert 'const ACTIVE_SURFACE_CONVERSATIONS = "conversations"' in script
    assert 'const ACTIVE_SURFACE_FILES = "files"' in script
    assert 'const ACTIVE_SURFACE_SETTINGS = "settings"' in script
    assert "workspaceStage:" in script
    assert "activeSurface:" in script
    assert "function setWorkspaceStage(stage)" in script
    assert "function setActiveSurface(surface)" in script
    assert "function syncWorkspaceStage()" in script
    assert "function syncActiveSurface()" in script


def test_frontend_supports_escape_to_close_recall_surfaces(client) -> None:
    script = _get_web_app_script(client)

    assert 'if (event.key === "Escape") {' in script
    assert "setActiveSurface(ACTIVE_SURFACE_NONE)" in script
```

- [ ] **Step 2: Run the script-state tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "workspace_stage or escape_to_close" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_frontend_tracks_workspace_stage_and_active_surface
FAILED tests/test_web_assets.py::test_frontend_supports_escape_to_close_recall_surfaces
```

- [ ] **Step 3: Implement the workspace-stage and active-surface state machine in `app/web/app.js`**

Add new constants next to the existing chat/workspace constants:

```javascript
const WORKSPACE_STAGE_LAUNCH = "launch";
const WORKSPACE_STAGE_CHAT = "chat";
const ACTIVE_SURFACE_NONE = "none";
const ACTIVE_SURFACE_CONVERSATIONS = "conversations";
const ACTIVE_SURFACE_FILES = "files";
const ACTIVE_SURFACE_SETTINGS = "settings";
```

Extend `state`:

```javascript
const state = {
  workspaceView: WORKSPACE_VIEW_CHAT,
  workspaceStage: WORKSPACE_STAGE_LAUNCH,
  activeSurface: ACTIVE_SURFACE_NONE,
};
```

Add stage/surface helpers near the current `setChatMode` / `setWorkspaceView` helpers:

```javascript
function setWorkspaceStage(stage) {
  state.workspaceStage = stage === WORKSPACE_STAGE_CHAT
    ? WORKSPACE_STAGE_CHAT
    : WORKSPACE_STAGE_LAUNCH;
  syncWorkspaceStage();
}

function setActiveSurface(surface) {
  state.activeSurface = surface || ACTIVE_SURFACE_NONE;
  syncActiveSurface();
}

function syncWorkspaceStage() {
  const isChatStage = state.workspaceStage === WORKSPACE_STAGE_CHAT;
  els.heroPanel?.classList.toggle("hidden", isChatStage);
  els.conversation?.classList.toggle("has-messages", isChatStage);
  els.shell?.classList.toggle("workspace-stage-chat", isChatStage);
}

function syncActiveSurface() {
  const current = state.activeSurface;
  els.conversationDrawer?.classList.toggle("hidden", current !== ACTIVE_SURFACE_CONVERSATIONS);
  els.fileDrawer?.classList.toggle("hidden", current !== ACTIVE_SURFACE_FILES);
  els.conversationDrawer?.setAttribute("aria-hidden", String(current !== ACTIVE_SURFACE_CONVERSATIONS));
  els.fileDrawer?.setAttribute("aria-hidden", String(current !== ACTIVE_SURFACE_FILES));
}
```

Replace the current `setHeroVisible()` usage:

```javascript
function clearConversation() {
  removePendingAssistantMessage();
  els.messageList.innerHTML = "";
  setWorkspaceStage(WORKSPACE_STAGE_LAUNCH);
}
```

Move the first-message transition into the send path:

```javascript
async function handleSend() {
  const question = els.messageInput.value.trim();
  if (!question || state.sending) {
    return;
  }
  if (!ensureIdentity()) {
    openAuthModal();
    showToast("Please log in first", true);
    return;
  }
  await ensureConversationReady();
  setWorkspaceStage(WORKSPACE_STAGE_CHAT);
  setActiveSurface(ACTIVE_SURFACE_NONE);
  state.sending = true;
  syncSendButtonState();
  appendMessage("user", question);
  appendPendingAssistantMessage("Generating response...");
  els.messageInput.value = "";
  autoGrowTextarea();
  await apiRequest("/chat/ask", {
    method: "POST",
    body: {
      user_id: state.userId,
      team_id: state.teamId,
      conversation_id: state.conversationId,
      question,
      top_k: 5,
      use_document_scope: state.chatMode === CHAT_MODE_DOCS,
      include_memory: false,
      include_library: false,
      embedding_model: state.selectedEmbedding || DEFAULT_EMBEDDING_ID,
    },
  });
}
```

Wire Escape at the end of `bindEvents()`:

```javascript
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setActiveSurface(ACTIVE_SURFACE_NONE);
    closePreviewDrawer();
    closeImageViewer();
  }
});
```

- [ ] **Step 4: Run the script-state tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "workspace_stage or escape_to_close" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_frontend_tracks_workspace_stage_and_active_surface
PASSED tests/test_web_assets.py::test_frontend_supports_escape_to_close_recall_surfaces
```

- [ ] **Step 5: Commit the state-machine change**

Run:

```bash
git add tests/test_web_assets.py app/web/app.js
git commit -m "feat: add workspace stage state machine"
```

## Task 3: Rewire Rail Actions, Drawers, and Composer Context to Existing Features

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/app.js`

- [ ] **Step 1: Write the failing rail/composer behavior tests**

Add these tests to `tests/test_web_assets.py`:

```python
def test_frontend_binds_rail_buttons_and_drawer_triggers(client) -> None:
    script = _get_web_app_script(client)

    assert 'els.railNewChatBtn = document.getElementById("railNewChatBtn")' in script
    assert 'els.railConversationsBtn = document.getElementById("railConversationsBtn")' in script
    assert 'els.railFilesBtn = document.getElementById("railFilesBtn")' in script
    assert 'els.railSettingsBtn = document.getElementById("railSettingsBtn")' in script
    assert 'els.conversationDrawer = document.getElementById("conversationDrawer")' in script
    assert 'els.fileDrawer = document.getElementById("fileDrawer")' in script
    assert 'els.composerContextRow = document.getElementById("composerContextRow")' in script
    assert "renderComposerContextRow()" in script


def test_frontend_uses_surface_transitions_for_files_and_settings(client) -> None:
    script = _get_web_app_script(client)

    assert "setActiveSurface(ACTIVE_SURFACE_CONVERSATIONS)" in script
    assert "setActiveSurface(ACTIVE_SURFACE_FILES)" in script
    assert "setActiveSurface(ACTIVE_SURFACE_SETTINGS)" in script
    assert "openSettingsModal();" in script
    assert "openDocumentPreview(doc)" in script
```

- [ ] **Step 2: Run the rail/composer behavior tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "rail_buttons or surface_transitions" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_frontend_binds_rail_buttons_and_drawer_triggers
FAILED tests/test_web_assets.py::test_frontend_uses_surface_transitions_for_files_and_settings
```

- [ ] **Step 3: Bind the new rail and drawer controls in `app/web/app.js`**

Extend `bindElements()`:

```javascript
els.workspaceRail = document.getElementById("workspaceRail");
els.railNewChatBtn = document.getElementById("railNewChatBtn");
els.railConversationsBtn = document.getElementById("railConversationsBtn");
els.railFilesBtn = document.getElementById("railFilesBtn");
els.railSettingsBtn = document.getElementById("railSettingsBtn");
els.drawerNewChatBtn = document.getElementById("drawerNewChatBtn");
els.conversationDrawer = document.getElementById("conversationDrawer");
els.fileDrawer = document.getElementById("fileDrawer");
els.composerContextRow = document.getElementById("composerContextRow");
```

Extend `bindEvents()`:

```javascript
els.railNewChatBtn.addEventListener("click", () => {
  createAndSwitchConversation()
    .then(() => {
      setWorkspaceStage(WORKSPACE_STAGE_LAUNCH);
      setActiveSurface(ACTIVE_SURFACE_NONE);
      els.messageInput.focus();
    })
    .catch((error) => showToast(error.message, true));
});

els.railConversationsBtn.addEventListener("click", () => {
  setActiveSurface(
    state.activeSurface === ACTIVE_SURFACE_CONVERSATIONS
      ? ACTIVE_SURFACE_NONE
      : ACTIVE_SURFACE_CONVERSATIONS
  );
});

els.railFilesBtn.addEventListener("click", () => {
  setActiveSurface(
    state.activeSurface === ACTIVE_SURFACE_FILES
      ? ACTIVE_SURFACE_NONE
      : ACTIVE_SURFACE_FILES
  );
});

els.railSettingsBtn.addEventListener("click", () => {
  setActiveSurface(ACTIVE_SURFACE_SETTINGS);
  openSettingsModal();
});

els.drawerNewChatBtn.addEventListener("click", () => {
  createAndSwitchConversation()
    .then(() => {
      setWorkspaceStage(WORKSPACE_STAGE_LAUNCH);
      setActiveSurface(ACTIVE_SURFACE_NONE);
      els.messageInput.focus();
    })
    .catch((error) => showToast(error.message, true));
});
```

Keep the settings surface state consistent by pairing the existing modal helpers with `activeSurface`:

```javascript
function openSettingsModal() {
  updateIdentityCard();
  refreshWorkspaceUi();
  setActiveSurface(ACTIVE_SURFACE_SETTINGS);
  els.settingsModal?.classList.remove("hidden");
}

function closeSettingsModal() {
  els.settingsModal?.classList.add("hidden");
  setActiveSurface(ACTIVE_SURFACE_NONE);
}
```

Update the existing shared auth-success path so both login and registration land in the launch stage:

```javascript
async function finalizeAuthSuccess(session, toastMessage) {
  applyAuthSession(session, { resetConversation: true });
  setWorkspaceStage(WORKSPACE_STAGE_LAUNCH);
  setActiveSurface(ACTIVE_SURFACE_NONE);
  closeSettingsModal();
  closeAuthModal();
  updateIdentityCard();
  clearConversation();
  await loadAllData();
  els.messageInput.focus();
  if (toastMessage) {
    showToast(toastMessage);
  }
}
```

Implement the composer context row using existing mode/document state:

```javascript
function renderComposerContextRow() {
  if (!els.composerContextRow) {
    return;
  }

  const chips = [];
  if (state.chatMode === CHAT_MODE_DOCS) {
    const selectedCount = state.selectedDocumentIds.length || getReadyDocumentCount();
    chips.push(`Doc Assist - ${selectedCount} files`);
  } else {
    chips.push("Chat Only");
  }

  if (state.documents.length) {
    chips.push(`${state.documents.length} attachment(s) in conversation`);
  }

  els.composerContextRow.innerHTML = chips.map((label) => (
    `<span class="composer-context-chip">${escapeHtml(label)}</span>`
  )).join("");
  els.composerContextRow.classList.toggle("hidden", chips.length === 0);
}
```

Add a single helper and use it instead of calling `renderAttachmentStrip()` directly in `setChatMode()`, `renderDocuments()`, `setDocumentStatusLocal()`, and the upload/delete branches:

```javascript
function refreshComposerChrome() {
  renderAttachmentStrip();
  renderComposerContextRow();
}
```

Then replace direct calls such as:

```javascript
renderAttachmentStrip();
```

with:

```javascript
refreshComposerChrome();
```

- [ ] **Step 4: Run the rail/composer behavior tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "rail_buttons or surface_transitions" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_frontend_binds_rail_buttons_and_drawer_triggers
PASSED tests/test_web_assets.py::test_frontend_uses_surface_transitions_for_files_and_settings
```

- [ ] **Step 5: Commit the recall/dock behavior change**

Run:

```bash
git add tests/test_web_assets.py app/web/app.js
git commit -m "feat: wire recall drawers and dock context"
```

## Task 4: Restyle the Workspace for Launch, Chat, Recall, and Motion

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/styles.css`

- [ ] **Step 1: Write the failing stylesheet tests**

First add a stylesheet helper if it does not already exist:

```python
def _get_web_styles(client) -> str:
    response = client.get("/web/styles.css")
    assert response.status_code == 200
    return response.text
```

Then add these tests:

```python
def test_styles_define_workspace_rail_drawers_and_dock(client) -> None:
    css = _get_web_styles(client)

    assert ".workspace-rail" in css
    assert ".surface-drawer" in css
    assert ".surface-panel" in css
    assert ".composer-dock" in css
    assert ".composer-context-row" in css


def test_styles_define_motion_and_reduced_motion_rules(client) -> None:
    css = _get_web_styles(client)

    assert ".launch-panel" in css
    assert ".workspace-stage-chat" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "transition:" in css
```

- [ ] **Step 2: Run the stylesheet tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "workspace_rail_drawers_and_dock or reduced_motion_rules" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_styles_define_workspace_rail_drawers_and_dock
FAILED tests/test_web_assets.py::test_styles_define_motion_and_reduced_motion_rules
```

- [ ] **Step 3: Implement the new workspace shell styles in `app/web/styles.css`**

Add shell and rail rules near the current `.shell`, `.sidebar`, and `.main-pane` blocks:

```css
.workspace-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-height: 0;
}

.workspace-rail {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px 12px;
  border-right: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.72);
}

.rail-btn {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  border: 1px solid rgba(20, 41, 52, 0.08);
  background: rgba(255, 255, 255, 0.9);
}

.rail-btn-bottom {
  margin-top: auto;
}

.surface-drawer {
  position: absolute;
  inset: 0 auto 0 0;
  width: min(320px, calc(100vw - 96px));
  padding: 18px 0 18px 12px;
  pointer-events: none;
}

.surface-panel {
  height: 100%;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: var(--shadow-soft);
  transform: translateX(-12px);
  opacity: 0;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.surface-drawer:not(.hidden) {
  pointer-events: auto;
}

.surface-drawer:not(.hidden) .surface-panel {
  transform: translateX(0);
  opacity: 1;
}
```

Add launch/chat and dock rules near the current hero/composer blocks:

```css
.launch-panel {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.workspace-stage-chat .launch-panel {
  opacity: 0;
  transform: translateY(-8px);
  pointer-events: none;
}

.composer-dock {
  position: sticky;
  bottom: 0;
  backdrop-filter: blur(18px) saturate(130%);
}

.composer-context-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.composer-context-chip {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(13, 127, 112, 0.08);
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 600;
}
```

Add responsive + reduced motion near the media query section:

```css
@media (max-width: 980px) {
  .workspace-rail {
    display: none;
  }

  .surface-drawer {
    width: 100%;
    padding: 0;
  }

  .surface-panel {
    border-radius: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation: none !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

- [ ] **Step 4: Run the stylesheet tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "workspace_rail_drawers_and_dock or reduced_motion_rules" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_styles_define_workspace_rail_drawers_and_dock
PASSED tests/test_web_assets.py::test_styles_define_motion_and_reduced_motion_rules
```

- [ ] **Step 5: Commit the style and motion change**

Run:

```bash
git add tests/test_web_assets.py app/web/styles.css
git commit -m "feat: restyle chat workbench shell"
```

## Task 5: Run Regression Coverage and Close the Loop

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/app.js`
- Modify: `app/web/index.html`
- Modify: `app/web/styles.css`

- [ ] **Step 1: Add the final regression assertions for preserved preview/settings/auth surfaces**

Add this test to `tests/test_web_assets.py`:

```python
def test_homepage_keeps_preview_auth_and_settings_surfaces_while_using_recall_shell(client) -> None:
    html = _get_web_index(client)
    script = _get_web_app_script(client)

    assert 'id="previewDrawer"' in html
    assert 'id="imageViewer"' in html
    assert 'id="authModal"' in html
    assert 'id="settingsModal"' in html
    assert "openDocumentPreview(doc)" in script
    assert "openSettingsModal()" in script
    assert "openAuthModal(AUTH_MODE_LOGIN)" in script
    assert 'showToast("当前还没有可用资料，先上传并等待文件处理完成。", true);' in script
    assert "doc.error_message || doc.error_code" in script
```

- [ ] **Step 2: Run the final focused frontend asset regression**

Run:

```bash
pytest tests/test_web_assets.py -q
```

Expected:

```text
pytest exits 0 and prints no FAIL or ERROR lines for tests/test_web_assets.py
```

- [ ] **Step 3: Run the broader regression set that covers the touched user-facing flows**

Run:

```bash
pytest tests/test_web_assets.py tests/test_auth.py tests/test_document.py tests/test_favorites_and_conclusions.py -q
```

Expected:

```text
pytest exits 0 and prints no FAIL or ERROR lines for the selected auth/document/favorites/web-asset tests
```

- [ ] **Step 4: Perform a manual smoke checklist in the browser**

Verify these exact flows against a local server:

```text
1. Load "/" and confirm the launch panel appears before any message is sent.
2. Click "New chat" from the rail and confirm focus returns to the composer.
3. Open and close the conversations drawer; press Escape to close it.
4. Open and close the files drawer; preview one uploaded file.
5. Send the first message and confirm the launch panel exits and the chat stage remains focused.
6. Open settings from the rail and confirm auth/settings surfaces still work.
7. Switch to Favorites and back to Chat without breaking the new shell.
8. Resize to a narrow viewport and confirm rail actions move to overlay-style surfaces.
```

- [ ] **Step 5: Commit the regression lock and final polish**

Run:

```bash
git add tests/test_web_assets.py app/web/index.html app/web/styles.css app/web/app.js
git commit -m "test: lock mixed chat workbench redesign"
```
