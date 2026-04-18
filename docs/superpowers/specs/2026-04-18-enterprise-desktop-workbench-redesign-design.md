# CaiBao Enterprise Desktop Workbench Redesign Design

Date: 2026-04-18
Status: Proposed

## 1. Context and Relationship to Previous Work

This design extends the earlier workbench redesign in:

- `docs/superpowers/specs/2026-04-17-chat-workbench-mixed-redesign-design.md`
- `docs/superpowers/plans/2026-04-17-chat-workbench-mixed-redesign.md`

The 2026-04-17 spec established the core interaction shift:

1. chat-first workflow
2. launch state vs active conversation state
3. recall-style secondary surfaces
4. simplified composer

That direction remains valid and should be preserved.

This 2026-04-18 design is an upgrade, not a restart.

It adds the missing layer that the earlier spec deliberately deferred:

1. stronger enterprise-grade visual language
2. clearer desktop information architecture
3. explicit desktop shell redesign
4. shared design system across chat, favorites, and admin
5. more intentional motion language

In practical terms:

- keep the chat-first product strategy from 2026-04-17
- replace the current shell and visual treatment with a more mature desktop workbench system
- use the older spec as the functional and interaction baseline
- use this new spec as the new product/visual/system baseline

## 2. Product Direction Confirmed

The direction confirmed with the user is:

1. primarily a high-frequency personal workbench
2. desktop-first for the first implementation pass
3. calm and professional rather than flashy
4. immersive and focused rather than dashboard-heavy
5. animated in a noticeable but refined way
6. visually recognizable through pattern and motion, not through heavy explanatory copy

The product should feel closer to a mature desktop AI workspace than to:

- a generic SaaS dashboard
- a concept-brand landing page
- a developer console disguised as a chat app

## 3. Goals

Primary goals:

1. raise the interface from "functional demo" to "ship-ready product surface"
2. make the desktop chat experience feel focused, premium, and stable under heavy use
3. create a recognizable CaiBao desktop identity through repeatable visual and motion motifs
4. unify chat, favorites, and admin under one design system without making them feel identical
5. reduce interface clutter by clarifying what belongs in the main stage vs recall surfaces

## 4. Non-Goals

This phase does not include:

1. a frontend framework rewrite
2. backend contract changes
3. a mobile-first redesign
4. deep information-model redesign inside favorites content itself
5. major admin feature expansion beyond layout/system alignment

## 5. Visual Identity Direction

### 5.1 Core Mood

The visual tone should be:

1. calm
2. professional
3. precise
4. slightly warm
5. quietly premium

It should not feel:

1. playful
2. noisy
3. glossy in a consumer-app way
4. dark and dramatic by default
5. dependent on marketing-style copy blocks

### 5.2 Primary Visual Formula

The main visual system should use:

1. cool gray-blue background fields
2. white to near-white structured surfaces
3. a single deep green action color
4. very light warm haze as atmospheric support
5. glass treatment only where it helps hierarchy and mood

Interpretation:

- the background carries calm
- the structure carries enterprise trust
- the green carries action and system identity
- the warmth prevents the product from feeling sterile

### 5.3 Glass Usage Rules

Glass should be used selectively.

Allowed use:

1. desktop chat shell
2. composer dock
3. lightweight launch-state hero surfaces
4. selected recall surfaces where depth matters

Reduced or removed:

1. admin tables and filters
2. dense management surfaces
3. repeated nested panels

Rule:

Glass is a mood layer, not the default answer for every container.

## 6. Brand Recognition Through Pattern and Motion

The product identity should rely more on recurring visual motifs and motion than on large text explanations.

### 6.1 Primary Motif Chosen

The primary CaiBao motif should be:

`Soft Grid`

Why this motif fits:

1. it communicates system, order, and enterprise confidence
2. it scales across chat, favorites, and admin without feeling decorative
3. it can remain subtle in dense views and expressive in empty states
4. it pairs well with calm motion

### 6.2 Motif Usage Rules

The soft grid should appear in:

1. launch-state background and empty-state backdrops
2. selected recall surfaces
3. loading / transition atmospherics
4. visual accents around major workspace transitions

The soft grid should be weaker or nearly absent in:

1. active reading/writing message areas
2. dense settings panels
3. admin tables

Rule:

The motif establishes identity at entry and transition moments, then recedes during focused work.

## 7. Workspace-Level Information Architecture

The product should use three stable first-level workspaces:

1. `Chat`
2. `Favorites`
3. `Admin`

These are true top-level spaces.

The following should not be treated as top-level pages:

1. files
2. settings
3. preview
4. image viewer

Those are recall surfaces attached to the current workspace.

### 7.1 Core Hierarchy Rule

The system should feel like:

- left side = where I go
- center = what I am doing now
- right side / overlays = what I need temporarily

In short:

`left handles navigation, right handles assistance, center handles the active task`

## 8. Desktop Shell Redesign

### 8.1 Shell Model

The recommended shell is:

`Focus Canvas` as the primary desktop architecture, with some structural discipline borrowed from the earlier "Studio Stack" direction.

This means:

1. strong central stage
2. reduced default chrome
3. adaptive recall surfaces
4. clear desktop transitions

### 8.2 Expandable Rail

The left rail should not remain a permanently tiny icon strip.

It should be an adaptive rail that supports:

1. collapsed state
2. expanded state
3. state persistence per user preference

Behavior:

1. on launch state, expanded should be more acceptable as the default
2. during active chat, collapsed should be favored by default
3. users can explicitly expand it and keep it expanded
4. it should not auto-expand on hover

The rail should feel closer to a mature desktop AI app such as ChatGPT desktop than to a classic web sidebar.

### 8.3 Rail Content Rules

The rail may contain:

1. new chat
2. conversations
3. files
4. favorites
5. settings
6. current workspace indicator

The rail should not contain:

1. long explanation copy
2. large stats blocks
3. stacked management panels
4. multiple independent attention-grabbing widgets

Expanded rail goal:

Provide orientation and fast access without turning back into the old heavy sidebar.

## 9. Chat Workspace

### 9.1 Launch State

The launch state should:

1. feel immediate
2. feel premium
3. avoid overwhelming the user

It should include:

1. concise product headline
2. minimal supporting text
3. 2 to 3 starter actions
4. the main dock ready for input
5. visible but subtle pattern field

It should avoid:

1. dense dashboard metrics
2. large blocks of instructional copy
3. heavy settings/configuration exposure

### 9.2 Active Conversation State

After the first message:

1. the launch content should visibly collapse away
2. the message stage should become the dominant visual anchor
3. the pattern field should reduce in intensity
4. the dock should remain stable and visually grounded

The conversation reading column should have a controlled width.

It should not sprawl edge-to-edge across the entire stage.

### 9.3 Composer Dock

The dock is one of the core product-signature surfaces.

Its job:

1. make writing feel immediate
2. make attachment/retrieval context legible
3. stay visually stable across launch and active chat

Primary row:

1. attachment entry
2. text input
3. send action

Secondary context layer:

1. selected document scope
2. chat/doc mode
3. relevant lightweight status chips

The dock should feel elevated but quiet, not oversized or gadget-like.

## 10. Recall Surfaces

Recall surfaces should be the standard pattern for secondary capability.

### 10.1 Surface Types

Main recall surfaces:

1. conversation switcher
2. file manager
3. settings
4. document preview
5. image viewer

### 10.2 Behavior Rules

Rules:

1. only one main recall surface should be active at a time
2. opening a surface must not destroy current chat position
3. closing a surface must return the user to the same context
4. surfaces should feel summoned, not abruptly spawned

### 10.3 Visual Rules

Conversation/file/settings surfaces may use light translucency.

Preview and admin-like dense surfaces should use more solid, structured panels.

## 11. Favorites Workspace

Favorites should become a proper sibling workspace, not a secondary tab feeling bolted onto chat.

Recommended structure:

1. left side for flow, grouping, or saved-item listing
2. right side for details and follow-up actions

The favorites workspace should:

1. inherit the same shell and motion system
2. be more organized and slightly denser than chat
3. feel quieter and more archival

It should not reuse the launch-state emotional emphasis from chat.

## 12. Admin Workspace

Admin should remain a separate route, but it should no longer look like a different product.

### 12.1 Shared System

Admin should share:

1. color logic
2. border radius system
3. button language
4. spacing rhythm
5. motion timing
6. soft-grid system restraint

### 12.2 Admin-Specific Differences

Admin should be:

1. more solid
2. more structured
3. denser
4. less atmospheric

This means:

1. weaker glass treatment
2. stronger table/panel structure
3. clearer filter bars
4. more explicit information grouping

The user should perceive:

"same product family, different operational mode"

## 13. Motion Language

The motion system must be noticeable, but disciplined.

It should create product recognition through repeated behavior patterns.

### 13.1 Signature Motions

The four most important signature motions are:

1. rail expand / collapse
2. launch-to-chat transition
3. surface recall
4. dock float / settle

### 13.2 Motion Characteristics

The motion language should be:

1. smooth
2. deliberate
3. low-bounce
4. desktop-like
5. layered in sequence

It should avoid:

1. playful springiness
2. noisy hover theatrics
3. simultaneous competing animations
4. long decorative float loops in work-critical areas

### 13.3 Recommended Behavior by Motion

#### Rail Expand / Collapse

Sequence:

1. width changes first
2. labels fade/slide in after width is established
3. nearby content shifts lightly

Intent:

This should feel like the workspace redistributing space, not a drawer slamming open.

#### Launch to Chat

Sequence:

1. launch content softens and retracts upward
2. message stage settles into focus
3. dock becomes slightly more anchored

Intent:

The user should feel that they have moved from "entry" into "work".

#### Surface Recall

Sequence:

1. surface slides/fades in
2. main stage remains legible underneath
3. focus moves into the temporary surface

Intent:

The user should feel assistance was recalled, not that context was replaced.

#### Local UI Feedback

Use short, crisp feedback for:

1. buttons
2. active list items
3. attachment chips
4. send button states
5. image open/close

## 14. State Model

The frontend state should be modeled explicitly across four layers:

1. workspace layer
2. stage layer
3. navigation layer
4. recall layer

### 14.1 Workspace Layer

Values:

1. `chat`
2. `favorites`
3. `admin`

### 14.2 Stage Layer

Values:

1. `launch`
2. `active-chat`

This only applies to the chat workspace.

### 14.3 Navigation Layer

Values:

1. `rail-collapsed`
2. `rail-expanded`

### 14.4 Recall Layer

Values:

1. `none`
2. `conversations`
3. `files`
4. `settings`
5. `preview`
6. `image-viewer`

Rule:

At any given time there should be:

1. one active workspace
2. one active stage for chat
3. one rail mode
4. at most one primary recall surface

This prevents overlapping UI authority and unclear transitions.

## 15. Error Handling and Feedback

### 15.1 Error Handling Principle

Failures should be local, recoverable, and visible in context.

Examples:

1. upload failure stays inside file management UI with retry/remove
2. auth failure remains inline in auth modal without clearing fields
3. preview failure preserves file metadata and alternative actions
4. conversation-switch failure should not blank the stage
5. settings failure should stay within the relevant settings group

### 15.2 Feedback Layering

Feedback should be separated into:

1. page-level feedback through layout/state changes
2. region-level feedback through skeletons, chips, inline states
3. action-level feedback through restrained toast usage

The redesign should reduce toast dependence.

Users should understand state from the interface structure first.

## 16. Accessibility and Responsiveness

### 16.1 Desktop Priority

Desktop is the primary target in this phase.

The design must feel strong at:

1. 1440px
2. 1280px
3. 1024px

### 16.2 Mobile and Narrow Layout

Mobile does not need equal ambition in this phase.

It does need:

1. clean fallback layout
2. usable overlays
3. preserved interaction correctness

### 16.3 Accessibility Rules

Required:

1. `Esc` closes temporary surfaces
2. focus enters temporary surfaces when they open
3. focus returns appropriately on close
4. states are not color-only
5. `prefers-reduced-motion` is respected

## 17. Implementation Surface

Expected primary implementation files:

- `app/web/index.html`
- `app/web/styles.css`
- `app/web/app.js`
- `app/web/admin.html`
- `app/web/admin.css`
- `app/web/admin.js`
- `tests/test_web_assets.py`

This redesign should build on the existing 2026-04-17 shell/state changes rather than replacing them blindly.

The likely implementation shape is:

1. refine or extend the current state machine
2. rebuild shell structure and rail behavior
3. unify desktop surface patterns across chat/favorites/admin
4. upgrade the motion system and pattern rendering
5. update regression tests to lock the new shell and state behaviors

## 18. Acceptance Criteria

This design is successful when:

1. the first-load desktop UI looks productized, not experimental
2. the chat stage feels obviously more focused after the first message
3. the rail can expand and collapse smoothly without feeling like a legacy sidebar
4. recall surfaces feel coherent and non-disruptive
5. the soft-grid motif becomes recognizable without distracting from work
6. favorites and admin clearly belong to the same product family
7. motion is noticeable enough to feel premium, but restrained enough for daily use

## 19. Deferred Work

The following work remains intentionally deferred:

1. advanced mobile-first shell redesign
2. deeper favorites information-model redesign
3. new backend capabilities
4. broader marketing/brand packaging outside the product UI
