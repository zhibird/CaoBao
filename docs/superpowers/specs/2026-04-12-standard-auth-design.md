# CaiBao Standard Auth Design

Date: 2026-04-12
Status: Proposed

## 1. Background

CaiBao currently does not have a complete standard login and authorization loop for the main workspace.

The existing main flow behaves like a workspace bootstrap:

- The frontend stores `teamId`, `teamName`, `userId`, and `displayName` in `localStorage`.
- The frontend calls `PUT /api/v1/teams/{id}` and `PUT /api/v1/users/{id}` to ensure a team and user exist.
- Subsequent API requests send `team_id` and `user_id` in request bodies or query params.
- Backend services validate that the provided `user_id` belongs to the provided `team_id`, but they still trust identity values supplied by the client.

This gives basic tenant isolation, but it is not authentication:

- There is no password-based login.
- There is no real session lifecycle.
- There is no token issuance, refresh, or logout.
- There is no unified `current user` dependency.
- A client can impersonate another user by sending a different `user_id` and `team_id`.

The admin page uses a separate developer-only `X-Dev-Admin-Token` flow. That flow is out of scope for this phase and remains unchanged.

## 2. Goals

Build a complete standard auth loop for the main user-facing workspace with:

- Account registration
- Username and password login
- Access token and refresh token lifecycle
- Authenticated session recovery on page load
- Logout
- Password change invalidation
- Unified backend authorization based on the authenticated user instead of client-supplied identity
- Frontend login state handling for normal expiry and refresh

## 3. Non-Goals

- Replacing the developer admin token flow in `/web/admin.html`
- Multi-tenant enterprise org management beyond the existing per-user workspace model
- OAuth, SSO, SMS login, email verification, or MFA in this phase
- Fine-grained RBAC redesign beyond preserving current `role`
- Cross-device session management UI

## 4. Product Decision

Use `HttpOnly` cookie-based auth with:

- Short-lived access JWT
- Rotating refresh token
- Refresh sessions stored in the database

This fits the current architecture because:

- The frontend is a static page served from the same FastAPI app.
- Cookies reduce token handling complexity in vanilla JS.
- `HttpOnly` cookies reduce exposure to XSS compared with storing bearer tokens in `localStorage`.
- Rotating refresh tokens support logout, invalidation, and future session management.

## 5. User Model and Workspace Model

The current product behaves like a personal workspace product where one user owns one default workspace.

Phase 1 keeps that model:

- `user_id` remains the unique account identifier used to log in.
- Registration automatically creates a personal team/workspace where `team_id = user_id`.
- The created user is attached to that workspace.
- Existing business data continues to be scoped by `team_id` and `user_id`.

This keeps business services stable while moving identity trust to the auth layer.

## 6. Data Model Changes

### 6.1 Update `users`

Add fields to `users`:

- `password_hash: str`
- `is_active: bool`
- `password_updated_at: datetime`

Behavior:

- `password_hash` stores a one-way password hash using `bcrypt`.
- `is_active` defaults to `true`.
- `password_updated_at` is set on registration and every password change.

### 6.2 Add refresh session table

Add a new table, for example `auth_refresh_sessions`, with fields similar to:

- `session_id: str` or UUID primary key
- `user_id: str` foreign key to `users.user_id`
- `refresh_token_hash: str`
- `issued_at: datetime`
- `expires_at: datetime`
- `rotated_at: datetime | null`
- `revoked_at: datetime | null`
- `replaced_by_session_id: str | null`
- `user_agent: str | null`
- `ip_address: str | null`
- `created_at: datetime`

Rules:

- Store only a hash or digest of the refresh token, never the raw value.
- Each refresh rotates to a new session/token pair.
- A revoked or rotated refresh token cannot be reused.

## 7. Config Changes

Add auth-related settings to `app/core/config.py`:

- `auth_access_token_ttl_minutes`
- `auth_refresh_token_ttl_days`
- `auth_jwt_secret`
- `auth_jwt_algorithm`
- `auth_cookie_secure`
- `auth_cookie_domain` optional
- `auth_cookie_samesite`
- `auth_access_cookie_name`
- `auth_refresh_cookie_name`

Defaults:

- Access TTL: 15 minutes
- Refresh TTL: 7 to 30 days, default 14 days
- Cookie names should be app-specific

`auth_cookie_secure` should be `False` for local HTTP dev and `True` in production.

## 8. Backend Architecture

### 8.1 New modules

Add a focused auth stack, for example:

- `app/models/auth_refresh_session.py`
- `app/schemas/auth.py`
- `app/services/auth_service.py`
- `app/api/routes/auth.py`

Potential utility modules if needed:

- `app/core/security.py`
- `app/core/auth.py`

### 8.2 Auth service responsibilities

`AuthService` should own:

- Password hashing and verification
- Access JWT creation and verification
- Refresh token generation, hashing, storage, rotation, and revocation
- Login
- Registration
- Session refresh
- Logout
- Password change invalidation
- Loading the current authenticated user

### 8.3 Route-level auth dependencies

Add unified dependencies in `app/api/deps.py`, such as:

- `get_auth_service`
- `require_current_user`
- `require_current_active_user`
- `require_current_admin` for future reuse if needed

Rules:

- Main protected routes depend on `require_current_active_user`.
- Route handlers derive `team_id` and `user_id` from `current_user`.
- Route handlers stop trusting `team_id` and `user_id` supplied by the client.

## 9. API Design

### 9.1 Auth endpoints

Add:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`

### 9.2 Endpoint behavior

#### `POST /auth/register`

Request:

- `user_id`
- `display_name`
- `password`
- `confirm_password`

Behavior:

- Validate unique `user_id`
- Create personal team/workspace with `team_id = user_id`
- Create user with hashed password, default role, active status
- Optionally issue login cookies immediately after registration

Recommendation:

- Registration should also log the user in immediately to simplify the UX

#### `POST /auth/login`

Request:

- `user_id`
- `password`

Behavior:

- Verify user exists, active, and password matches
- Create access token
- Create refresh session
- Set access and refresh cookies
- Return a lightweight auth payload and current user info

#### `POST /auth/refresh`

Behavior:

- Read refresh cookie
- Validate session, expiry, revocation state, and user status
- Rotate refresh token
- Mint new access token
- Reset cookies
- Reject reused or revoked refresh tokens

#### `POST /auth/logout`

Behavior:

- Revoke current refresh session if present
- Clear auth cookies even if the session is already invalid

#### `GET /auth/me`

Behavior:

- Read and validate access token from cookie
- Return current user identity and workspace info

Suggested response fields:

- `user_id`
- `display_name`
- `team_id`
- `team_name`
- `role`
- `is_active`

#### `POST /auth/change-password`

Request:

- `current_password`
- `new_password`
- `confirm_new_password`

Behavior:

- Require logged-in user
- Verify current password
- Update password hash
- Update `password_updated_at`
- Revoke all refresh sessions for the user
- Clear current cookies or force re-login

Recommendation:

- Force re-login after password change for a clean and predictable security boundary

## 10. Protected Business API Migration

### 10.1 Migration strategy

Minimize service-layer churn by changing route handlers first.

Current pattern:

- Request schema includes `team_id` and `user_id`
- Route forwards those values into services

New pattern:

- Route depends on `current_user`
- Route ignores client-supplied `team_id` and `user_id`
- Route injects `current_user.team_id` and `current_user.user_id` into services

### 10.2 Compatibility rule

Phase 1 should preserve compatibility to reduce diff size:

- Existing request schemas may temporarily keep `team_id` and `user_id`
- Server ignores those values for authenticated main-workspace routes
- Once all frontend calls are migrated and stable, those schema fields can be removed in a cleanup pass

### 10.3 Routes affected

This applies to the main workspace routes, including:

- conversations
- chat
- documents
- retrieval
- memory
- favorites
- conclusions
- spaces
- library
- llm models
- embedding models

Team and user bootstrap endpoints will no longer be used by the main frontend login flow after auth is added.

## 11. Frontend Design

### 11.1 Auth entry flow

Replace the current workspace bootstrap modal with a standard auth modal:

- Login mode:
  - `账号 ID`
  - `密码`
- Register mode:
  - `账号 ID`
  - `显示名称`
  - `密码`
  - `确认密码`

The UI may still describe the resulting personal workspace, but authentication becomes the source of truth.

### 11.2 App bootstrap

Current behavior:

- App loads local identity from `localStorage`
- If missing, opens auth modal

New behavior:

1. App loads
2. Call `GET /api/v1/auth/me`
3. If success:
   - hydrate identity from server response
   - load business data
4. If `401`:
   - show login modal
   - do not treat `localStorage` identity as authenticated

### 11.3 Local storage changes

Keep only non-sensitive local state:

- selected model
- selected embedding model
- current conversation id
- UI view state

Stop using `localStorage` as the source of identity trust.

### 11.4 Request behavior

Because cookies are same-origin, frontend requests do not need manual bearer token headers.

Frontend should:

- Call APIs normally
- On `401`, attempt one silent `POST /api/v1/auth/refresh`
- If refresh succeeds, replay the failed request once
- If refresh fails, clear local workspace state and open login modal

### 11.5 Logout behavior

On logout:

- Call `POST /api/v1/auth/logout`
- Clear local app state tied to the current user session
- Return to login modal

## 12. Security Rules

### 12.1 Password storage

Use `passlib[bcrypt]`.

Rules:

- Never store plaintext passwords
- Never log plaintext passwords
- Compare using the password hasher's verify function

### 12.2 Cookie settings

Auth cookies should be:

- `HttpOnly = true`
- `SameSite = Lax` by default
- `Secure = true` in production

Recommendation:

- Access cookie and refresh cookie use separate names
- Cookie path can be constrained if helpful, but keeping both app-wide is acceptable for this phase

CSRF boundary for Phase 1:

- The main app and API remain same-origin under the current FastAPI-served deployment model.
- `SameSite=Lax` is the baseline CSRF mitigation in this phase.
- If the frontend is later split to a different origin or cross-site embedding is introduced, add an explicit CSRF defense such as a synchronizer token or double-submit cookie pattern before keeping cookie auth.

### 12.3 Token claims

Access JWT should include enough data to identify and validate the session, such as:

- subject `sub = user_id`
- team id
- role
- issued at
- expiry
- token version metadata if needed later

Do not place secrets or sensitive mutable profile data in the JWT.

### 12.4 Error semantics

Use:

- `401 Unauthorized` for missing, expired, invalid, or revoked auth
- `403 Forbidden` for authenticated but disallowed actions

For login failure, return a generic error like:

- `Invalid credentials`

Do not reveal whether the account exists.

### 12.5 Session invalidation

On password change:

- Revoke all refresh sessions for the user
- Force re-login

On deactivation:

- `is_active = false`
- block login
- reject refresh
- reject protected routes

## 13. Admin Flow Boundary

The existing developer admin token flow remains separate in Phase 1:

- `/web/admin.html`
- `X-Dev-Admin-Token`
- `require_dev_admin`

Reason:

- It is a developer-only control plane
- Mixing it into the first user auth rollout adds risk and scope

Future work may unify admin auth, but not in this phase.

## 14. Testing Strategy

### 14.1 Backend tests

Add auth-focused tests covering:

- registration success
- duplicate registration conflict
- login success
- login with wrong password fails
- unauthenticated access to protected routes returns `401`
- authenticated access to existing business routes succeeds
- refresh rotates tokens
- reused old refresh token fails
- logout revokes refresh session
- password change revokes all refresh sessions
- inactive user cannot log in or refresh

### 14.2 Regression tests for existing routes

Update selected existing tests so protected routes use authenticated cookies instead of passing only `team_id` and `user_id`.

Keep business-behavior assertions intact.

### 14.3 Frontend behavior checks

Verify:

- first load with valid session enters workspace automatically
- first load without session shows login modal
- expired access token can recover through refresh
- refresh failure returns the user to login
- logout clears visible session state

## 15. Migration Plan

### Phase 1

- Add auth schema and tables
- Add auth service and routes
- Add cookies, JWT handling, and refresh rotation
- Add frontend login/register/logout/me/refresh flow
- Protect main workspace routes using current user dependency
- Ignore client-supplied `team_id` and `user_id` on protected routes

### Phase 2

- Remove obsolete identity fields from frontend requests where possible
- Remove unused workspace bootstrap logic from the main UI
- Simplify request schemas that still carry redundant identity fields

### Phase 3

- Optional session management UI
- Optional admin auth unification
- Optional multi-workspace membership model

## 16. Risks and Mitigations

### Risk: Large diff across many routes

Mitigation:

- Keep service layer mostly unchanged
- Migrate route handlers first
- Reuse a single auth dependency pattern

### Risk: Existing tests assume anonymous identity bootstrap

Mitigation:

- Add auth fixtures
- Update tests incrementally around the new login flow

### Risk: Frontend stale identity state

Mitigation:

- Treat `/auth/me` as the only trusted identity source
- Clear stale local state on refresh failure and logout

### Risk: Refresh replay bugs

Mitigation:

- Centralize API request retry-once logic
- Keep refresh attempts single-shot per failing request

## 17. Acceptance Criteria

This design is complete when all of the following are true:

- A new user can register and immediately enter their workspace
- An existing user can log in with password
- Main workspace APIs reject anonymous access
- Main workspace APIs derive identity from server auth, not client-supplied IDs
- Access token expiry is recoverable through refresh
- Logout invalidates the refresh session
- Password change invalidates all sessions
- The admin developer token flow still works unchanged

## 18. Recommended Implementation Order

1. Add auth dependencies and config
2. Add password fields and refresh session model plus migration
3. Implement auth service
4. Implement auth routes
5. Add backend tests for auth flow
6. Protect one representative route group and verify pattern
7. Migrate remaining main workspace routes
8. Update frontend modal and bootstrap logic
9. Add refresh retry logic
10. Run full verification
