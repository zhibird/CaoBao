# CaiBao Chat Workbench Mixed Redesign Design

Date: 2026-04-17
Status: Proposed

## 1. Background

The current CaiBao web workspace already supports the core chat flow, attachments, retrieval-enhanced answers, favorites, settings, and auth.

The main frontend is implemented as a static FastAPI-served page centered in:

- `app/web/index.html`
- `app/web/styles.css`
- `app/web/app.js`

The current product direction is already clear:

- Chat is the primary job to be done.
- Retrieval and attachments should be enabled only when needed.
- Favorites and longer-term knowledge assets should live behind the main chat path.
- Developer-oriented settings should not dominate the normal user experience.

However, the current main workspace still has a few UX problems in the core chat path:

1. A new conversation starts with too much surrounding information and not enough guidance.
2. The always-visible sidebar competes with the message flow for attention.
3. The composer area mixes primary actions, mode state, attachment state, and helper text in one place.
4. Files, settings, and auth recovery are functional, but their placement still interrupts the chat-first experience.

This design focuses on fixing the main workbench interaction model before doing a broader brand or visual language upgrade.

## 2. Goals

Redesign the main chat workspace so that it feels clearer, calmer, and more direct to use.

Primary goals:

1. Make a new conversation easy to start.
2. Reduce visual noise once the user is actively chatting.
3. Reorganize sidebar, files, settings, and auth into on-demand surfaces instead of always-on blocks.
4. Simplify the composer so primary actions are obvious and secondary context is still visible.
5. Improve polish with small, purposeful motion that helps state transitions.

## 3. Non-Goals

This phase does not include:

1. A full brand refresh or new visual identity system.
2. A deep redesign of the Favorites workspace itself.
3. Major backend API changes or new product capabilities.
4. A complete rewrite into a new frontend framework.
5. Reworking admin-only flows in `app/web/admin.html`.

## 4. Product Direction Chosen

The selected direction is a mixed redesign:

- Use the "focus start" approach for new conversations.
- Use the "immersive chat" approach for the active conversation body.
- Use adaptive recall surfaces for conversations, files, and settings.

In practice this means:

1. New conversations begin in a lightweight launch state with clear starter actions.
2. As soon as the user sends the first message, the workspace collapses into a quiet, immersive chat view.
3. Conversations, files, and settings are no longer permanently expanded in the main layout.
4. Desktop keeps a narrow rail for recall; mobile uses overlay panels.

This direction matches the user's priorities for this phase:

- Improve the chat path first.
- Make files/settings/details feel more complete.
- Defer brand packaging until the interaction foundation is smoother.

## 5. Core Workspace States

The main workspace should behave as three explicit states instead of one overloaded screen.

### 5.1 Launch State

This is the default state when:

- the user first enters the workspace
- the user creates a new conversation
- the current conversation has no messages yet

The main panel should show:

1. A concise title that confirms the user can start immediately.
2. Two or three starter action cards, such as:
   - `Direct Chat`
   - `Plan Writing`
   - `Doc Assist`
3. A ready-to-type input field.

Rules:

- Keep explanatory copy short.
- Remove large metrics and secondary control clutter.
- Let users either click a starter card or type immediately.

Purpose:

- solve the "blank new conversation" problem
- make the first action obvious

### 5.2 Conversation State

This state begins immediately after the first user message is sent.

The workspace should transition into an immersive chat mode:

1. The launch panel exits.
2. The message list becomes the primary visual center.
3. The composer becomes a fixed bottom dock.
4. Secondary panels are hidden until recalled.

Rules:

- The message flow should visually dominate the screen.
- Non-essential descriptive content should disappear.
- The user should not feel like they are still inside a dashboard.

Purpose:

- reduce distraction during active chat
- center reading and writing

### 5.3 Recall State

This is not a standalone page. It is an overlay pattern used when the user needs secondary tools.

Recall surfaces include:

- conversation list
- file management
- profile and settings
- preview sheets

Rules:

1. These surfaces should appear only when requested.
2. They should not reset the current chat context.
3. Closing them should return the user to the same conversation position.

Purpose:

- keep the default chat experience quiet
- make secondary tools feel available but not intrusive

## 6. Layout and Information Architecture

### 6.1 Desktop Layout

Desktop should use:

1. A narrow left rail for primary recall actions.
2. A central conversation stage.
3. Overlay drawers or sheets for secondary content.

The left rail should replace the current full-height always-open sidebar.

Recommended primary rail actions:

1. `New Chat`
2. `Conversations`
3. `Files`
4. `Me / Settings`

This keeps system awareness without permanently occupying the conversation reading width.

### 6.2 Mobile Layout

Mobile should not preserve the narrow rail.

Instead:

1. Use a compact top entry point for navigation.
2. Open conversations, files, and settings as full-screen panels or bottom sheets.
3. Keep the message stage and composer as the primary visible structure.

### 6.3 Favorites Workspace

Favorites remains a separate workspace view.

Rules:

1. It should stay outside the core chat launch/conversation state machine.
2. Switching to Favorites is a workspace switch, not an inline chat overlay.
3. This phase should avoid redesigning the deeper Favorites information model.

## 7. Conversation Recall Design

The conversation drawer should do one job well: conversation management.

Recommended structure:

1. Fixed top area with a strong `New Chat` action.
2. Recent conversation list as the main body.
3. Current conversation clearly highlighted.
4. Existing actions like pin, rename, and delete kept inside per-item menus.

Rules:

1. Do not mix file management into the same drawer.
2. Do not keep long explanatory copy inside the drawer.
3. Preserve fast switching without making the drawer visually heavy.

Search can be considered later, but it is not required for the first pass of this redesign.

## 8. Composer Redesign

The composer should become a stable dock shared by both launch state and conversation state.

### 8.1 Primary Action Layer

The most prominent row should contain only:

1. attachment entry
2. main text input
3. send action

This keeps the main intent obvious:

- add context
- type
- send

### 8.2 Context Layer

Mode and context should move into a lighter layer above the primary composer row.

Examples:

- `Chat Only`
- `Doc Assist - 2 files`
- `1 attachment added`

Rules:

1. Context chips appear only when they are meaningful.
2. They should not compete with the main input affordance.
3. They should communicate active scope, not behave like a control panel.

### 8.3 Launch-to-Conversation Continuity

The launch state and the active conversation should share the same composer logic.

Rules:

1. Starter cards can preconfigure the conversation context.
2. Users can also ignore starter cards and type immediately.
3. After the first message, the layout changes, but the composer remains familiar.

This ensures that "starting a conversation" and "continuing a conversation" feel like one continuous interaction.

## 9. Files, Upload, and Retrieval Context

### 9.1 File Access Model

Files should move out of the always-visible sidebar and become a dedicated recall surface.

Users should have two entry paths:

1. the composer attachment button for immediate chat-context uploads
2. the rail file entry for focused file management

This separates:

- "I want to add something to this chat right now"
- "I want to inspect and manage the conversation's files"

### 9.2 File Surface Behavior

The file drawer should show:

1. file cards
2. processing state
3. preview action
4. remove action
5. retrieval readiness state

Files added to the current conversation should also surface as lightweight chips near the composer context layer.

### 9.3 Retrieval Context

Retrieval mode should not remain a large toggle competing with the composer.

Instead:

1. Retrieval is reflected as active context in the chip row.
2. If relevant files are attached or selected, show the current retrieval scope there.
3. If retrieval is not active, the composer remains visually minimal.

## 10. Preview Model

Two preview patterns should be used:

1. Text-like formats (`txt`, `md`, `pdf`, `docx`, `xlsx`) use a right-side preview sheet.
2. Images use a full-screen lightbox.

Rules:

1. Preview should feel temporary and non-destructive.
2. The user should return to the same chat context after closing.
3. Preview UI should prioritize file identity, status, snippet/preview, and a small set of actions.

Recommended key actions:

- preview
- download
- remove

## 11. Settings and Auth Placement

Settings should move behind the `Me / Settings` recall surface and become more clearly layered.

Recommended sections:

1. Account
   - current user
   - current workspace
   - switch account
   - logout
2. Workspace Preferences
   - default chat behavior
   - retrieval preferences
   - interface preferences
3. Advanced
   - model selection
   - embedding selection
   - developer-facing configuration

This keeps developer-oriented controls available without letting them dominate the default chat flow.

### 11.1 Auth Experience

The auth modal remains a focused dialog, but should become lighter:

1. show only the fields needed for the current auth mode
2. keep errors inline
3. preserve user input on failure
4. on success, transition smoothly into the launch state instead of dumping the user into an overpopulated workspace

## 12. Motion and Interaction Polish

Motion should support comprehension, not decoration.

Recommended motion moments:

1. Launch entry
   - starter cards softly rise and fade in
   - input receives focus emphasis
2. First-message transition
   - launch panel gently collapses away
   - message stage takes over without a jarring hard cut
3. Drawer and sheet recall
   - short slide-in motion
   - subtle background softening or dimming
4. Local control feedback
   - attachment chip entry
   - upload state changes
   - send button feedback
   - preview open/close

Recommended timing:

- short UI feedback: about 150ms
- drawer/sheet recall: about 180ms to 220ms
- avoid slow, floaty transitions

Avoid:

1. gratuitous ambient motion
2. heavy scroll-based animation
3. multiple simultaneous animations competing for attention

Respect `prefers-reduced-motion` by reducing or disabling non-essential transitions.

## 13. State Feedback and Error Handling

The redesign should make state legible at three levels.

### 13.1 Page-Level State

Examples:

- launch state
- empty conversation
- active chat state
- drawer open state

These should be communicated primarily by layout, not by toast messages.

### 13.2 Region-Level State

Examples:

- conversation list loading
- file upload in progress
- parsing/indexing state
- preview loading
- settings saving

These should be expressed inside the relevant surface using:

- skeletons
- loading text
- status chips
- inline busy states

### 13.3 Action-Level Feedback

Examples:

- send success
- upload failure
- delete success
- login failure

Rules:

1. Use toast sparingly for lightweight action confirmation.
2. Show failures close to the failing action whenever possible.
3. Do not let small local failures block the whole workspace.

### 13.4 Failure Cases to Explicitly Support

1. Upload failure
   - file card stays visible in failed state
   - allow retry or remove
2. Retrieval enabled with no usable files
   - explain the problem inline or gracefully fall back
3. Login/register failure
   - keep entered values
   - show inline error in the auth card
4. Conversation switching or refresh failure
   - provide local retry entry points
5. Preview failure
   - keep download/remove actions available

## 14. Responsive and Accessibility Rules

The redesign should explicitly support:

1. desktop narrow rail + drawer recall
2. tablet reduced-width recall surfaces
3. mobile overlay navigation patterns

Accessibility requirements:

1. `Esc` closes drawers and preview surfaces.
2. Focus moves into dialogs and drawers when they open.
3. Focus returns to the trigger when they close.
4. Interactive targets remain touch-friendly.
5. Current state is not communicated by color alone.
6. Reduced-motion preference is respected.

## 15. Implementation Surfaces

The first implementation pass is expected to be concentrated in:

- `app/web/index.html`
- `app/web/styles.css`
- `app/web/app.js`

Likely change areas:

1. layout structure and state-specific sections in HTML
2. rail, drawer, sheet, and dock styling in CSS
3. state machine and recall-surface orchestration in JS
4. auth modal and file/preview interaction polish in JS and CSS

No backend contract change is required to adopt this first-pass redesign.

## 16. Acceptance Criteria

This redesign is successful when:

1. A new conversation immediately shows a clear way to start.
2. After the first message, the UI becomes visibly more focused on the conversation.
3. The user can open conversations, files, and settings on demand without losing chat context.
4. The composer feels simpler because the main row only emphasizes attach, type, and send.
5. Retrieval scope and attachment state are visible without cluttering the primary controls.
6. Preview and file management no longer compete with the conversation list in one sidebar.
7. Settings and auth feel integrated but secondary to the main chat workflow.
8. Motion improves clarity without making the interface feel busy or artificial.

## 17. Deferred Work

The following should be deferred until after this foundation is stable:

1. broader brand and art-direction upgrade
2. deeper Favorites workspace redesign
3. more ambitious visual-system changes
4. larger information architecture expansion beyond the main chat path
