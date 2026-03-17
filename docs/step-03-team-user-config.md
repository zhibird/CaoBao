# Step 03 - Team and User Configuration

## Why this step exists

Chat messages must be bound to real users and teams. This is the minimum requirement for an enterprise scenario.

If we skip this step, cross-team data confusion will happen and later RAG/tool permissions cannot be enforced safely.

## What we added

1. SQLite persistence (`app/db/session.py`).
2. Team/User models (`app/models/team.py`, `app/models/user.py`).
3. Team/User APIs (`/api/v1/teams`, `/api/v1/users`).
4. Chat validation: user must belong to the specified team.

## Runtime flow for chat

1. Request enters `POST /api/v1/chat/echo`.
2. `ChatService.echo` calls `UserService.ensure_user_in_team`.
3. If user/team mapping is valid, service returns echo response.
4. If mapping is invalid, API returns `400` or `404`.

## Quick verification sequence

1. Create team.
2. Create user under this team.
3. Call chat echo with matching `user_id` and `team_id`.
4. Try a wrong `team_id` and observe validation error.
