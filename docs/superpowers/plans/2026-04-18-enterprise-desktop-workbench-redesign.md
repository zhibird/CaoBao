# Enterprise Desktop Workbench Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade CaiBao from the current chat-workbench branch into a desktop-first enterprise-grade workspace with an expandable rail, pattern-led launch/chat transitions, a dual-pane Favorites workspace, and an Admin console that shares the same design system.

**Architecture:** Build on top of the already-started 2026-04-17 chat-workbench shell/state branch instead of resetting it. Keep the FastAPI-served static frontend, add one shared visual-system stylesheet for cross-workspace tokens and motif utilities, and land the redesign in milestone-sized slices that each leave the product runnable and testable.

**Tech Stack:** FastAPI static asset serving, vanilla HTML/CSS/JavaScript, pytest, FastAPI `TestClient`

---

## Delivery Milestones

This plan is intentionally staged so you can track progress in checkpoints instead of one large front-end rewrite.

### Milestone 1: Shared Visual System Foundation

Outcome:

1. chat and admin entrypoints load the same `theme.css`
2. shared tokens, buttons, panels, soft-grid motif utilities, and reduced-motion rules exist in one place
3. future styling work stops duplicating the same primitives in multiple files

### Milestone 2: Adaptive Desktop Shell

Outcome:

1. the chat shell supports a persisted expanded/collapsed rail
2. the rail owns top-level navigation instead of the old sidebar body
3. the shell feels desktop-like before any brand/motion polish lands

### Milestone 3: Pattern-Led Chat Identity

Outcome:

1. the launch state uses the soft-grid motif instead of text-heavy explanation
2. launch-to-chat and dock/surface motion create visible product identity
3. the main chat stage feels premium and focused

### Milestone 4: Secondary Workspace Alignment

Outcome:

1. Favorites becomes a dual-pane sibling workspace
2. Admin shares the same design system while staying denser and more solid
3. the product feels like one family, not separate mini-apps

### Milestone 5: Hardening and Regression Lock

Outcome:

1. local surface errors replace fragile page-wide feedback
2. keyboard/focus flows are tightened
3. regression coverage locks the redesign before implementation continues

## File Map

- **Create:** `app/web/theme.css`
  - Shared design tokens, motion tokens, soft-grid motif utilities, shared buttons/chips/panel primitives, and reduced-motion rules used by both chat and admin.

- **Modify:** `app/web/index.html`
  - Load `theme.css`.
  - Rebuild the rail header/body so it can truly collapse and expand.
  - Move workspace switching into the rail.
  - Add the pattern field and leaner launch-state structure.
  - Replace the current single-column favorites view with a dual-pane shell.

- **Modify:** `app/web/styles.css`
  - Keep workspace-specific rules that depend on the chat/favorites shell.
  - Consume shared tokens from `theme.css`.
  - Add adaptive-rail, launch-stage, dock, favorites-pane, and local surface-status styles.

- **Modify:** `app/web/app.js`
  - Add persisted rail mode state.
  - Extend the shell state machine to drive launch/chat identity transitions.
  - Rebuild Favorites rendering around list/detail selection.
  - Add local surface-status helpers and focus-friendly close behavior.

- **Modify:** `app/web/admin.html`
  - Load `theme.css`.
  - Replace the current topbar/auth/panel stack with a command-bar + shared-panel structure.

- **Modify:** `app/web/admin.css`
  - Rebuild admin-specific layout on top of shared tokens.
  - Keep admin dense and solid while aligning its structure with the main product.

- **Modify:** `app/web/admin.js`
  - Keep current data/API behavior.
  - Add keyboard affordances and adjust selectors if the admin shell changes.

- **Modify:** `tests/test_web_assets.py`
  - Add asset-level regression checks for `theme.css`, adaptive rail behavior hooks, soft-grid identity, favorites dual-pane shell, admin asset structure, and local surface-status regions.

## Task 1: Add the Shared Visual-System Asset

**Milestone:** 1

**Stage Goal:** Create a single source of truth for tokens, panel primitives, motif utilities, and reduced-motion rules before touching the rest of the redesign.

**Files:**
- Create: `app/web/theme.css`
- Modify: `app/web/index.html`
- Modify: `app/web/admin.html`
- Modify: `tests/test_web_assets.py`

- [ ] **Step 1: Write the failing shared-theme asset tests**

Add these helpers and tests to `tests/test_web_assets.py` near the existing asset helpers:

```python
def _get_web_admin_html(client) -> str:
    response = client.get("/web/admin.html")
    assert response.status_code == 200
    return response.text


def _get_web_theme_styles(client) -> str:
    response = client.get("/web/theme.css")
    assert response.status_code == 200
    return response.text


def test_chat_and_admin_load_shared_theme_stylesheet(client) -> None:
    index_html = _get_web_index(client)
    admin_html = _get_web_admin_html(client)

    assert 'href="/web/theme.css' in index_html
    assert 'href="/web/theme.css' in admin_html


def test_theme_styles_define_tokens_soft_grid_and_shared_motion(client) -> None:
    css = _get_web_theme_styles(client)

    assert "--accent: #15695f;" in css
    assert ".soft-grid-field" in css
    assert ".surface-card" in css
    assert ".shared-pill" in css
    assert "@keyframes grid-drift" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
```

- [ ] **Step 2: Run the theme asset tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "shared_theme or theme_styles_define_tokens" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_chat_and_admin_load_shared_theme_stylesheet
FAILED tests/test_web_assets.py::test_theme_styles_define_tokens_soft_grid_and_shared_motion
```

- [ ] **Step 3: Implement `theme.css` and load it in both HTML entrypoints**

Create `app/web/theme.css` with the shared token and motif layer:

```css
:root {
  --bg: #edf1f3;
  --bg-soft: #f6f8f9;
  --ink: #17242c;
  --ink-soft: #5a6c77;
  --line: rgba(23, 36, 44, 0.1);
  --line-strong: rgba(23, 36, 44, 0.16);
  --accent: #15695f;
  --accent-strong: #0f544b;
  --warm-haze: rgba(226, 208, 189, 0.34);
  --cool-haze: rgba(204, 221, 232, 0.42);
  --panel: rgba(255, 255, 255, 0.74);
  --panel-strong: rgba(255, 255, 255, 0.9);
  --radius-xl: 34px;
  --radius-lg: 26px;
  --radius-md: 20px;
  --radius-sm: 14px;
  --shadow-soft: 0 14px 34px rgba(17, 30, 38, 0.05);
  --shadow-strong: 0 28px 70px rgba(17, 30, 38, 0.08);
}

body {
  color: var(--ink);
  background:
    radial-gradient(circle at top left, var(--warm-haze), transparent 28%),
    radial-gradient(circle at top right, var(--cool-haze), transparent 34%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg-soft) 100%);
}

.surface-card {
  border: 1px solid rgba(255, 255, 255, 0.72);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.76) 0%, rgba(255, 255, 255, 0.68) 100%);
  box-shadow: var(--shadow-strong);
  backdrop-filter: blur(22px);
}

.shared-pill {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(23, 36, 44, 0.08);
  background: rgba(255, 255, 255, 0.82);
}

.soft-grid-field,
.soft-grid-plane {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.soft-grid-plane {
  background:
    linear-gradient(rgba(21, 105, 95, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(21, 105, 95, 0.12) 1px, transparent 1px);
  background-size: 28px 28px;
  opacity: 0.24;
  animation: grid-drift 12s linear infinite;
}

@keyframes grid-drift {
  from { transform: translateX(0); }
  to { transform: translateX(-28px); }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Load it before the workspace-specific stylesheet in both HTML entrypoints:

```html
<link rel="stylesheet" href="/web/theme.css?v=0.16.0&build=enterprise-desktop-1" />
<link rel="stylesheet" href="/web/styles.css?v=0.16.0&build=enterprise-desktop-1" />
```

```html
<link rel="stylesheet" href="/web/theme.css?v=0.16.0&build=enterprise-desktop-1" />
<link rel="stylesheet" href="/web/admin.css?v=0.16.0&build=enterprise-desktop-1" />
```

- [ ] **Step 4: Run the theme asset tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "shared_theme or theme_styles_define_tokens" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_chat_and_admin_load_shared_theme_stylesheet
PASSED tests/test_web_assets.py::test_theme_styles_define_tokens_soft_grid_and_shared_motion
```

- [ ] **Step 5: Commit the shared-theme foundation**

Run:

```bash
git add tests/test_web_assets.py app/web/theme.css app/web/index.html app/web/admin.html
git commit -m "feat: add shared enterprise theme asset"
```

## Task 2: Rebuild the Chat Shell Around a Persisted Expandable Rail

**Milestone:** 2

**Stage Goal:** Land the new desktop shell first, with a persisted expandable/collapsible rail and workspace switching owned by the rail instead of the old sidebar body.

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/index.html`
- Modify: `app/web/styles.css`
- Modify: `app/web/app.js`

- [ ] **Step 1: Write the failing adaptive-rail tests**

Add these tests to `tests/test_web_assets.py`:

```python
def test_homepage_uses_expandable_workspace_rail(client) -> None:
    html = _get_web_index(client)

    assert 'id="railToggleBtn"' in html
    assert 'data-rail-mode="collapsed"' in html
    assert 'id="chatWorkspaceBtn"' in html
    assert 'id="favoritesWorkspaceBtn"' in html
    assert 'class="workspace-link" href="/web/admin.html"' in html
    assert 'class="workspace-rail-label"' in html


def test_frontend_tracks_persisted_rail_mode(client) -> None:
    script = _get_web_app_script(client)

    assert 'const RAIL_MODE_COLLAPSED = "collapsed";' in script
    assert 'const RAIL_MODE_EXPANDED = "expanded";' in script
    assert 'railMode: RAIL_MODE_COLLAPSED' in script
    assert 'railMode: "caibao.railMode"' in script
    assert "function setRailMode(mode) {" in script
    assert "function toggleRailMode() {" in script
    assert 'els.railToggleBtn = document.getElementById("railToggleBtn");' in script
    assert 'els.railToggleBtn.addEventListener("click", toggleRailMode);' in script


def test_styles_define_collapsed_and_expanded_rail_states(client) -> None:
    css = _get_web_styles(client)

    assert '.shell[data-rail-mode="collapsed"]' in css
    assert '.shell[data-rail-mode="expanded"]' in css
    assert ".rail-toggle-btn" in css
    assert ".workspace-rail-label" in css
```

- [ ] **Step 2: Run the adaptive-rail tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "expandable_workspace_rail or persisted_rail_mode or expanded_rail_states" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_homepage_uses_expandable_workspace_rail
FAILED tests/test_web_assets.py::test_frontend_tracks_persisted_rail_mode
FAILED tests/test_web_assets.py::test_styles_define_collapsed_and_expanded_rail_states
```

- [ ] **Step 3: Implement the adaptive rail in HTML, CSS, and JS**

Update the shell root in `app/web/index.html` so the current stage and rail mode are both explicit:

```html
<div class="shell workspace-stage-launch" data-rail-mode="collapsed">
  <aside id="workspaceRail" class="workspace-rail" aria-label="Workspace navigation" aria-expanded="false">
    <div class="workspace-rail-top">
      <button id="railToggleBtn" class="rail-toggle-btn" type="button" aria-label="Toggle navigation"></button>
      <button id="railNewChatBtn" class="rail-btn rail-btn-primary" type="button">
        <span class="rail-btn-icon">+</span>
        <span class="workspace-rail-label">New chat</span>
      </button>
    </div>

    <div class="rail-workspace-switch">
      <button id="chatWorkspaceBtn" class="workspace-switch-btn active" type="button">Chat</button>
      <button id="favoritesWorkspaceBtn" class="workspace-switch-btn" type="button">Favorites</button>
      <a class="workspace-link" href="/web/admin.html">Admin</a>
    </div>

    <nav class="workspace-rail-nav" aria-label="Workspace tools">
      <button id="railConversationsBtn" class="rail-btn" type="button">
        <span class="rail-btn-icon">C</span>
        <span class="workspace-rail-label">Conversations</span>
      </button>
      <button id="railFilesBtn" class="rail-btn" type="button">
        <span class="rail-btn-icon">F</span>
        <span class="workspace-rail-label">Files</span>
      </button>
      <button id="railSettingsBtn" class="rail-btn rail-btn-bottom" type="button">
        <span class="rail-btn-icon">Me</span>
        <span class="workspace-rail-label">Settings</span>
      </button>
    </nav>
  </aside>
```

Extend `STORAGE_KEYS` and `state` in `app/web/app.js`:

```javascript
const RAIL_MODE_COLLAPSED = "collapsed";
const RAIL_MODE_EXPANDED = "expanded";

const STORAGE_KEYS = {
  conversationId: "caibao.conversationId",
  railMode: "caibao.railMode",
};

const state = {
  railMode: RAIL_MODE_COLLAPSED,
};
```

Add the rail helpers:

```javascript
function loadRailModeFromStorage() {
  const value = localStorage.getItem(STORAGE_KEYS.railMode);
  return value === RAIL_MODE_EXPANDED ? RAIL_MODE_EXPANDED : RAIL_MODE_COLLAPSED;
}

function persistRailMode() {
  localStorage.setItem(STORAGE_KEYS.railMode, state.railMode);
}

function setRailMode(mode) {
  state.railMode = mode === RAIL_MODE_EXPANDED ? RAIL_MODE_EXPANDED : RAIL_MODE_COLLAPSED;
  persistRailMode();
  syncRailMode();
}

function toggleRailMode() {
  setRailMode(state.railMode === RAIL_MODE_EXPANDED ? RAIL_MODE_COLLAPSED : RAIL_MODE_EXPANDED);
}

function syncRailMode() {
  els.shell?.setAttribute("data-rail-mode", state.railMode);
  els.workspaceRail?.setAttribute("aria-expanded", String(state.railMode === RAIL_MODE_EXPANDED));
}
```

Bind and hydrate the new control:

```javascript
els.railToggleBtn = document.getElementById("railToggleBtn");
state.railMode = loadRailModeFromStorage();
syncRailMode();
els.railToggleBtn.addEventListener("click", toggleRailMode);
```

Add the workspace-shell sizing rules in `app/web/styles.css`:

```css
.shell[data-rail-mode="collapsed"] {
  grid-template-columns: 92px minmax(0, 1fr);
}

.shell[data-rail-mode="expanded"] {
  grid-template-columns: 230px minmax(0, 1fr);
}

.rail-toggle-btn {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  border: 1px solid rgba(23, 36, 44, 0.08);
  background: rgba(255, 255, 255, 0.88);
}

.workspace-rail-label {
  white-space: nowrap;
  opacity: 0;
  transform: translateX(-8px);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.shell[data-rail-mode="expanded"] .workspace-rail-label {
  opacity: 1;
  transform: translateX(0);
}
```

- [ ] **Step 4: Run the adaptive-rail tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "expandable_workspace_rail or persisted_rail_mode or expanded_rail_states" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_homepage_uses_expandable_workspace_rail
PASSED tests/test_web_assets.py::test_frontend_tracks_persisted_rail_mode
PASSED tests/test_web_assets.py::test_styles_define_collapsed_and_expanded_rail_states
```

- [ ] **Step 5: Commit the adaptive desktop shell**

Run:

```bash
git add tests/test_web_assets.py app/web/index.html app/web/styles.css app/web/app.js
git commit -m "feat: add adaptive desktop rail shell"
```

## Task 3: Add the Soft-Grid Launch Field and Signature Motion System

**Milestone:** 3

**Stage Goal:** Replace text-heavy launch identity with a visible product motif and make the rail, launch-to-chat transition, dock, and recall surfaces feel unmistakably CaiBao.

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/index.html`
- Modify: `app/web/styles.css`
- Modify: `app/web/app.js`

- [ ] **Step 1: Write the failing launch-identity and motion tests**

Add these tests to `tests/test_web_assets.py`:

```python
def test_homepage_uses_soft_grid_pattern_field_for_launch_identity(client) -> None:
    html = _get_web_index(client)

    assert 'id="workspacePatternField"' in html
    assert 'class="soft-grid-field workspace-pattern-field"' in html
    assert 'class="soft-grid-plane"' in html
    assert 'id="heroPanel" class="hero-panel launch-panel"' in html


def test_styles_define_signature_motion_keyframes(client) -> None:
    css = _get_web_styles(client)

    assert "@keyframes hero-collapse" in css
    assert "@keyframes dock-settle" in css
    assert "@keyframes surface-recall" in css
    assert ".workspace-pattern-field" in css
    assert ".shell.workspace-stage-chat .workspace-pattern-field" in css


def test_frontend_syncs_workspace_stage_into_shell_and_pattern_visibility(client) -> None:
    script = _get_web_app_script(client)

    assert "function syncWorkspaceStage() {" in script
    assert 'els.shell?.classList.toggle("workspace-stage-chat", isChatStage);' in script
    assert 'els.shell?.classList.toggle("workspace-stage-launch", !isChatStage);' in script
    assert 'els.workspacePatternField = document.getElementById("workspacePatternField");' in script
```

- [ ] **Step 2: Run the launch-identity and motion tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "soft_grid_pattern_field or signature_motion_keyframes or pattern_visibility" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_homepage_uses_soft_grid_pattern_field_for_launch_identity
FAILED tests/test_web_assets.py::test_styles_define_signature_motion_keyframes
FAILED tests/test_web_assets.py::test_frontend_syncs_workspace_stage_into_shell_and_pattern_visibility
```

- [ ] **Step 3: Add the pattern field and signature motion hooks**

Insert the soft-grid pattern field at the top of the stage in `app/web/index.html`:

```html
<main class="main-pane">
  <div id="workspacePatternField" class="soft-grid-field workspace-pattern-field" aria-hidden="true">
    <div class="soft-grid-plane"></div>
  </div>

  <div class="workspace-intro">
    <div id="workspaceEyebrow" class="workspace-eyebrow">Personal AI Workspace</div>
    <h1 class="workspace-title">Stay focused first, then recall tools and knowledge on demand.</h1>
    <p id="workspaceDescription" class="workspace-description">Pattern, motion, and structure carry the product identity so the copy can stay quiet.</p>
  </div>
```

Extend `bindElements()` in `app/web/app.js`:

```javascript
els.workspacePatternField = document.getElementById("workspacePatternField");
```

Tighten `syncWorkspaceStage()` so the shell always knows which state it is in:

```javascript
function syncWorkspaceStage() {
  const isChatStage = state.workspaceStage === WORKSPACE_STAGE_CHAT;
  els.heroPanel?.classList.toggle("hidden", isChatStage);
  els.shell?.classList.toggle("workspace-stage-chat", isChatStage);
  els.shell?.classList.toggle("workspace-stage-launch", !isChatStage);
  els.workspacePatternField?.classList.toggle("is-muted", isChatStage);
}
```

Add the signature motion rules to `app/web/styles.css`:

```css
.workspace-pattern-field {
  position: absolute;
  inset: 18px 18px auto 18px;
  height: 190px;
  border-radius: 28px;
  overflow: hidden;
  opacity: 0.94;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.88) 0%, rgba(0, 0, 0, 0.18) 72%, transparent 100%);
}

.shell.workspace-stage-chat .workspace-pattern-field {
  opacity: 0.22;
  transition: opacity 0.22s ease;
}

.shell.workspace-stage-chat .launch-panel {
  animation: hero-collapse 0.24s ease both;
}

.surface-drawer:not(.hidden) .surface-panel {
  animation: surface-recall 0.18s ease both;
}

.composer-dock {
  animation: dock-settle 0.24s ease both;
}

@keyframes hero-collapse {
  from { opacity: 1; transform: translateY(0) scale(1); }
  to { opacity: 0; transform: translateY(-18px) scale(0.985); }
}

@keyframes dock-settle {
  from { transform: translateY(10px); opacity: 0.84; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes surface-recall {
  from { transform: translateX(24px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
```

- [ ] **Step 4: Run the launch-identity and motion tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "soft_grid_pattern_field or signature_motion_keyframes or pattern_visibility" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_homepage_uses_soft_grid_pattern_field_for_launch_identity
PASSED tests/test_web_assets.py::test_styles_define_signature_motion_keyframes
PASSED tests/test_web_assets.py::test_frontend_syncs_workspace_stage_into_shell_and_pattern_visibility
```

- [ ] **Step 5: Commit the launch identity and motion system**

Run:

```bash
git add tests/test_web_assets.py app/web/index.html app/web/styles.css app/web/app.js
git commit -m "feat: add soft-grid launch identity and signature motion"
```

## Task 4: Rebuild Favorites as a Dual-Pane Workspace

**Milestone:** 4

**Stage Goal:** Make Favorites feel like a real sibling workspace instead of a bolted-on panel, while staying within the current data model.

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/index.html`
- Modify: `app/web/styles.css`
- Modify: `app/web/app.js`

- [ ] **Step 1: Write the failing Favorites workspace tests**

Add these tests to `tests/test_web_assets.py`:

```python
def test_homepage_uses_dual_pane_favorites_workspace(client) -> None:
    html = _get_web_index(client)

    assert 'id="favoritesPanel"' in html
    assert 'id="favoritesListPane"' in html
    assert 'id="favoriteDetailPane"' in html
    assert 'id="favoriteEmptyState"' in html


def test_styles_define_favorites_list_and_detail_panes(client) -> None:
    css = _get_web_styles(client)

    assert ".favorites-layout" in css
    assert ".favorites-list-pane" in css
    assert ".favorites-detail-pane" in css
    assert ".favorite-empty-state" in css


def test_frontend_tracks_selected_favorite_and_renders_detail_pane(client) -> None:
    script = _get_web_app_script(client)

    assert "selectedFavoriteId:" in script
    assert "function setSelectedFavoriteId(favoriteId) {" in script
    assert "function renderFavoriteWorkspace() {" in script
    assert "function renderFavoriteDetailPane() {" in script
```

- [ ] **Step 2: Run the Favorites workspace tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "dual_pane_favorites_workspace or selected_favorite" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_homepage_uses_dual_pane_favorites_workspace
FAILED tests/test_web_assets.py::test_styles_define_favorites_list_and_detail_panes
FAILED tests/test_web_assets.py::test_frontend_tracks_selected_favorite_and_renders_detail_pane
```

- [ ] **Step 3: Implement the dual-pane Favorites workspace**

Replace the current Favorites body in `app/web/index.html` with a list/detail shell:

```html
<section id="favoritesPanel" class="workspace-panel favorites-panel hidden">
  <div class="favorites-layout">
    <aside id="favoritesListPane" class="favorites-list-pane">
      <div class="favorites-panel-head">
        <div>
          <div class="hero-kicker">Favorites Workspace</div>
          <h2 class="favorites-panel-title">Capture first, then refine into long-term knowledge.</h2>
        </div>
      </div>
      <div id="favoriteList" class="favorite-list"></div>
    </aside>

    <section id="favoriteDetailPane" class="favorites-detail-pane">
      <div id="favoriteEmptyState" class="favorite-empty-state">
        Select a saved item to view details and follow-up actions.
      </div>
      <div id="favoriteDetailContent" class="favorite-detail-content hidden"></div>
    </section>
  </div>
</section>
```

Extend `state` and add the detail render path in `app/web/app.js`:

```javascript
const state = {
  selectedFavoriteId: "",
};

function setSelectedFavoriteId(favoriteId) {
  state.selectedFavoriteId = favoriteId || "";
  renderFavoriteWorkspace();
}

function renderFavoriteWorkspace() {
  renderFavoriteList();
  renderFavoriteDetailPane();
}

function renderFavoriteDetailPane() {
  const detailEl = document.getElementById("favoriteDetailContent");
  const emptyEl = document.getElementById("favoriteEmptyState");
  if (!detailEl || !emptyEl) {
    return;
  }

  const selected = state.favoriteItems.find((item) => item.favorite_id === state.selectedFavoriteId);
  if (!selected) {
    emptyEl.classList.remove("hidden");
    detailEl.classList.add("hidden");
    detailEl.innerHTML = "";
    return;
  }

  emptyEl.classList.add("hidden");
  detailEl.classList.remove("hidden");
  detailEl.innerHTML = `
    <article class="favorite-detail-card">
      <h3>${escapeHtml(selected.title || "Untitled favorite")}</h3>
      <p>${escapeHtml(selected.note || "No note yet.")}</p>
      <div class="favorite-detail-actions">
        <button class="ghost-btn compact-btn" type="button" data-favorite-action="memory">Save to memory</button>
        <button class="ghost-btn compact-btn" type="button" data-favorite-action="conclusion">Turn into conclusion</button>
        <button class="ghost-btn compact-btn" type="button" data-favorite-action="library">Add to library</button>
      </div>
    </article>
  `;
}
```

Add the Favorites layout styles to `app/web/styles.css`:

```css
.favorites-layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.92fr) minmax(0, 1.08fr);
  gap: 16px;
  min-height: 0;
}

.favorites-list-pane,
.favorites-detail-pane {
  border-radius: 24px;
  border: 1px solid rgba(23, 36, 44, 0.08);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78);
  padding: 18px;
}

.favorite-empty-state {
  display: grid;
  place-items: center;
  min-height: 240px;
  color: var(--ink-soft);
  text-align: center;
}
```

- [ ] **Step 4: Run the Favorites workspace tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "dual_pane_favorites_workspace or selected_favorite" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_homepage_uses_dual_pane_favorites_workspace
PASSED tests/test_web_assets.py::test_styles_define_favorites_list_and_detail_panes
PASSED tests/test_web_assets.py::test_frontend_tracks_selected_favorite_and_renders_detail_pane
```

- [ ] **Step 5: Commit the Favorites workspace redesign**

Run:

```bash
git add tests/test_web_assets.py app/web/index.html app/web/styles.css app/web/app.js
git commit -m "feat: rebuild favorites as dual-pane workspace"
```

## Task 5: Align the Admin Console with the Shared Desktop System

**Milestone:** 4

**Stage Goal:** Make admin feel like the same product family while preserving its denser, more operational character.

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/admin.html`
- Modify: `app/web/admin.css`
- Modify: `app/web/admin.js`

- [ ] **Step 1: Write the failing admin asset tests**

Add these helpers and tests to `tests/test_web_assets.py`:

```python
def _get_web_admin_styles(client) -> str:
    response = client.get("/web/admin.css")
    assert response.status_code == 200
    return response.text


def _get_web_admin_script(client) -> str:
    response = client.get("/web/admin.js")
    assert response.status_code == 200
    return response.text


def test_admin_uses_enterprise_command_bar_and_panel_grid(client) -> None:
    html = _get_web_admin_html(client)

    assert 'class="admin-shell admin-enterprise-shell"' in html
    assert 'id="adminCommandBar"' in html
    assert 'class="admin-panel-grid"' in html
    assert 'class="admin-table-panel"' in html


def test_admin_styles_define_command_bar_and_shared_panels(client) -> None:
    css = _get_web_admin_styles(client)

    assert ".admin-enterprise-shell" in css
    assert ".admin-command-bar" in css
    assert ".admin-panel-grid" in css
    assert ".admin-table-panel" in css


def test_admin_script_supports_escape_to_close_document_modal(client) -> None:
    script = _get_web_admin_script(client)

    assert 'document.addEventListener("keydown", (event) => {' in script
    assert 'if (event.key === "Escape") {' in script
    assert "closeDocModal();" in script
```

- [ ] **Step 2: Run the admin asset tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "admin_uses_enterprise_command_bar or admin_script_supports_escape" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_admin_uses_enterprise_command_bar_and_panel_grid
FAILED tests/test_web_assets.py::test_admin_styles_define_command_bar_and_shared_panels
FAILED tests/test_web_assets.py::test_admin_script_supports_escape_to_close_document_modal
```

- [ ] **Step 3: Rebuild the admin shell on top of the shared theme**

Update `app/web/admin.html`:

```html
<body>
  <div class="admin-shell admin-enterprise-shell">
    <header id="adminCommandBar" class="admin-command-bar surface-card">
      <div class="admin-command-copy">
        <div class="shared-pill">CaiBao Admin</div>
        <h1>Developer Admin Console</h1>
        <p class="subtitle">A denser control surface built from the same shared design system.</p>
      </div>
      <div class="admin-command-actions">
        <a class="ghost-btn" href="/">Back to chat</a>
      </div>
    </header>

    <section class="auth-card admin-auth-card">
      <div class="field">
        <label for="adminTokenInput">X-Dev-Admin-Token</label>
        <input id="adminTokenInput" type="password" placeholder="Enter admin token" />
      </div>
      <div class="auth-actions">
        <button id="adminLoginBtn" class="primary-btn" type="button">Sign in</button>
        <button id="adminLogoutBtn" class="ghost-btn" type="button">Sign out</button>
      </div>
      <p id="authHint" class="auth-hint">Not signed in.</p>
    </section>

    <main id="adminMain" class="admin-main hidden">
      <section class="admin-panel-grid">
        <article class="stat-card admin-stat-card">
          <span class="stat-label">Teams</span>
          <strong id="statTeams">0</strong>
        </article>
        <article class="stat-card admin-stat-card">
          <span class="stat-label">Users</span>
          <strong id="statUsers">0</strong>
        </article>
        <article class="stat-card admin-stat-card">
          <span class="stat-label">Conversations</span>
          <strong id="statConversations">0</strong>
        </article>
        <article class="stat-card admin-stat-card">
          <span class="stat-label">Documents</span>
          <strong id="statDocuments">0</strong>
        </article>
        <article class="stat-card admin-stat-card">
          <span class="stat-label">Messages</span>
          <strong id="statMessages">0</strong>
        </article>
      </section>

      <section class="panel admin-table-panel">
        <div class="panel-head">
          <h2>Teams</h2>
          <button id="refreshTeamsBtn" class="ghost-btn compact" type="button">Refresh</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>team_id</th>
                <th>name</th>
                <th>users</th>
                <th>conversations</th>
                <th>documents</th>
                <th>created_at</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody id="teamsTableBody"></tbody>
          </table>
        </div>
      </section>

      <section class="panel admin-table-panel">
        <div class="panel-head">
          <h2>Users</h2>
          <div class="inline-actions">
            <label class="inline-field">
              <span>team</span>
              <select id="usersTeamFilter"></select>
            </label>
            <button id="refreshUsersBtn" class="ghost-btn compact" type="button">Refresh</button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>user_id</th>
                <th>team_id</th>
                <th>name</th>
                <th>role</th>
                <th>conversations</th>
                <th>documents</th>
                <th>created_at</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody id="usersTableBody"></tbody>
          </table>
        </div>
      </section>

      <section class="panel admin-table-panel">
        <div class="panel-head">
          <h2>Conversations</h2>
          <div class="inline-actions">
            <label class="inline-field">
              <span>team</span>
              <select id="conversationsTeamFilter"></select>
            </label>
            <label class="inline-field">
              <span>user</span>
              <select id="conversationsUserFilter"></select>
            </label>
            <button id="refreshConversationsBtn" class="ghost-btn compact" type="button">Refresh</button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>conversation_id</th>
                <th>title</th>
                <th>team_id</th>
                <th>user_id</th>
                <th>messages</th>
                <th>documents</th>
                <th>created_at</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody id="conversationsTableBody"></tbody>
          </table>
        </div>
      </section>

      <section class="panel admin-table-panel">
        <div class="panel-head">
          <h2>Documents</h2>
          <div class="inline-actions">
            <label class="inline-field">
              <span>team</span>
              <select id="documentsTeamFilter"></select>
            </label>
            <label class="inline-field">
              <span>user</span>
              <select id="documentsUserFilter"></select>
            </label>
            <label class="inline-field">
              <span>conversation</span>
              <input id="documentsConversationFilter" type="text" placeholder="conversation_id" />
            </label>
            <button id="refreshDocumentsBtn" class="ghost-btn compact" type="button">Refresh</button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>document_id</th>
                <th>source_name</th>
                <th>team_id</th>
                <th>conversation_id</th>
                <th>status</th>
                <th>chars</th>
                <th>preview</th>
                <th>created_at</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody id="documentsTableBody"></tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
```

Add the admin-specific structure in `app/web/admin.css`:

```css
.admin-enterprise-shell {
  width: min(1460px, calc(100vw - 40px));
  margin: 20px auto 28px;
  display: grid;
  gap: 14px;
}

.admin-command-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px;
  border-radius: 28px;
}

.admin-panel-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.admin-table-panel {
  border-radius: 24px;
  background: rgba(252, 252, 252, 0.96);
  box-shadow: var(--shadow-soft);
}
```

Add Escape-to-close in `app/web/admin.js`:

```javascript
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDocModal();
  }
});
```

- [ ] **Step 4: Run the admin asset tests to verify they pass**

Run:

```bash
pytest tests/test_web_assets.py -k "admin_uses_enterprise_command_bar or admin_script_supports_escape" -v
```

Expected:

```text
PASSED tests/test_web_assets.py::test_admin_uses_enterprise_command_bar_and_panel_grid
PASSED tests/test_web_assets.py::test_admin_styles_define_command_bar_and_shared_panels
PASSED tests/test_web_assets.py::test_admin_script_supports_escape_to_close_document_modal
```

- [ ] **Step 5: Commit the admin alignment**

Run:

```bash
git add tests/test_web_assets.py app/web/admin.html app/web/admin.css app/web/admin.js
git commit -m "feat: align admin console with desktop design system"
```

## Task 6: Add Local Surface Status Regions and Lock the Redesign with Regression Coverage

**Milestone:** 5

**Stage Goal:** Replace fragile page-wide status handling with local surface feedback, tighten close/focus flows, and freeze the redesign with regression tests and smoke checks.

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `app/web/index.html`
- Modify: `app/web/styles.css`
- Modify: `app/web/app.js`
- Modify: `app/web/admin.js`

- [ ] **Step 1: Write the failing local-status and regression tests**

Add these tests to `tests/test_web_assets.py`:

```python
def test_homepage_exposes_local_surface_status_regions(client) -> None:
    html = _get_web_index(client)
    script = _get_web_app_script(client)
    css = _get_web_styles(client)

    assert 'id="conversationDrawerStatus"' in html
    assert 'id="fileDrawerStatus"' in html
    assert 'id="settingsStatus"' in html
    assert "function setSurfaceStatus(targetEl, message, isError = false) {" in script
    assert "function clearSurfaceStatus(targetEl) {" in script
    assert ".surface-status" in css


def test_frontend_keeps_recall_surfaces_mutually_exclusive(client) -> None:
    script = _get_web_app_script(client)

    assert "state.activeSurface = surface || ACTIVE_SURFACE_NONE;" in script
    assert 'els.conversationDrawer?.classList.toggle("hidden", current !== ACTIVE_SURFACE_CONVERSATIONS);' in script
    assert 'els.fileDrawer?.classList.toggle("hidden", current !== ACTIVE_SURFACE_FILES);' in script
    assert "closeSettingsModal();" in script
```

- [ ] **Step 2: Run the local-status and regression tests to verify they fail**

Run:

```bash
pytest tests/test_web_assets.py -k "local_surface_status_regions or recall_surfaces_mutually_exclusive" -v
```

Expected:

```text
FAILED tests/test_web_assets.py::test_homepage_exposes_local_surface_status_regions
FAILED tests/test_web_assets.py::test_frontend_keeps_recall_surfaces_mutually_exclusive
```

- [ ] **Step 3: Add local status regions and use them in surface-level flows**

Add the status regions to `app/web/index.html`:

```html
<aside id="conversationDrawer" class="surface-drawer conversation-drawer hidden" aria-hidden="true">
  <section class="surface-panel">
    <p id="conversationDrawerStatus" class="surface-status hidden" role="status"></p>
    <div class="surface-head">
      <p id="historySectionTitle" class="section-title">Conversations</p>
      <button id="drawerNewChatBtn" class="primary-btn compact-primary-btn" type="button">New chat</button>
    </div>
    <ul id="historyList" class="history-list"></ul>
  </section>
</aside>

<aside id="fileDrawer" class="surface-drawer file-drawer hidden" aria-hidden="true">
  <section class="surface-panel">
    <p id="fileDrawerStatus" class="surface-status hidden" role="status"></p>
    <div class="surface-head">
      <p id="documentSectionTitle" class="section-title">Files</p>
    </div>
    <ul id="documentList" class="document-list"></ul>
  </section>
</aside>

<div class="settings-grid">
  <p id="settingsStatus" class="surface-status hidden" role="status"></p>
  <section class="settings-section">
    <div class="settings-section-head">
      <div>
        <h3>Current account</h3>
        <p id="settingsWorkspaceSummary" class="settings-note">Signed in and ready to switch context.</p>
      </div>
      <div class="settings-inline-actions">
        <button id="switchAccountBtn" class="ghost-btn compact-btn" type="button">Switch account</button>
        <button id="logoutBtn" class="ghost-btn compact-btn danger-btn" type="button">Sign out</button>
      </div>
    </div>
  </section>
</div>
```

Add the shared helper logic in `app/web/app.js`:

```javascript
function setSurfaceStatus(targetEl, message, isError = false) {
  if (!targetEl) {
    return;
  }
  targetEl.textContent = message;
  targetEl.classList.remove("hidden", "error");
  if (isError) {
    targetEl.classList.add("error");
  }
}

function clearSurfaceStatus(targetEl) {
  if (!targetEl) {
    return;
  }
  targetEl.textContent = "";
  targetEl.classList.add("hidden");
  targetEl.classList.remove("error");
}
```

Use the helpers in at least the two surface loaders:

```javascript
async function loadConversations() {
  clearSurfaceStatus(els.conversationDrawerStatus);
  try {
    const response = await apiRequest(`/conversations?limit=100&space_id=${encodeURIComponent(state.spaceId || "")}`);
    state.conversations = Array.isArray(response) ? response : (response.items || []);
    renderHistory();
  } catch (error) {
    setSurfaceStatus(els.conversationDrawerStatus, error.message, true);
    throw error;
  }
}

async function loadDocuments() {
  clearSurfaceStatus(els.fileDrawerStatus);
  try {
    const query = new URLSearchParams();
    if (state.conversationId) {
      query.set("conversation_id", state.conversationId);
    }
    const response = await apiRequest(`/documents?${query.toString()}`);
    state.documents = Array.isArray(response) ? response : (response.items || []);
    renderDocuments();
    refreshComposerChrome();
  } catch (error) {
    setSurfaceStatus(els.fileDrawerStatus, error.message, true);
    throw error;
  }
}
```

Add the visual treatment to `app/web/styles.css`:

```css
.surface-status {
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid rgba(23, 36, 44, 0.08);
  background: rgba(255, 255, 255, 0.84);
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.6;
}

.surface-status.error {
  border-color: rgba(187, 71, 55, 0.18);
  background: rgba(255, 237, 233, 0.9);
  color: #9b3a2d;
}
```

Also preserve Escape behavior in admin and chat so temporary surfaces always clear cleanly:

```javascript
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDocModal();
  }
});
```

- [ ] **Step 4: Run the focused and broad regression suites**

Run the focused asset suite:

```bash
pytest tests/test_web_assets.py -q
```

Expected:

```text
pytest exits 0 with no FAIL or ERROR lines for tests/test_web_assets.py
```

Run the broader product regression suite:

```bash
pytest tests/test_web_assets.py tests/test_admin.py tests/test_auth.py tests/test_document.py tests/test_favorites_and_conclusions.py -q
```

Expected:

```text
pytest exits 0 with no FAIL or ERROR lines for the selected suite
```

Run this manual smoke checklist after the automated suite:

```text
1. Load "/" and confirm the rail starts collapsed but can be expanded.
2. Expand the rail, switch to Favorites, then back to Chat.
3. Open conversations, files, and settings one at a time and verify only one primary surface is visible.
4. Send the first message and confirm the launch field collapses while the dock stays anchored.
5. Upload or inspect a file and confirm drawer-local errors appear inside the file surface, not only as a toast.
6. Open "/web/admin.html" and confirm it uses the new command bar + shared panel system.
7. Open a document in admin and press Escape to close the modal.
8. Resize to a narrow viewport and confirm the shell still remains usable.
```

- [ ] **Step 5: Commit the hardening pass**

Run:

```bash
git add tests/test_web_assets.py app/web/index.html app/web/styles.css app/web/app.js app/web/admin.js
git commit -m "test: lock enterprise desktop workbench redesign"
```
