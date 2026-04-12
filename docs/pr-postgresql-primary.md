# PR: Promote PostgreSQL To Primary Database

## Summary
- make PostgreSQL the default runtime database for local and Docker workflows
- require explicit `DATABASE_URL` instead of silently falling back to SQLite
- keep SQLite only as a legacy compatibility and backup/debug path
- add PostgreSQL smoke coverage around Alembic-driven test setup and migrations

## Why
- SQLite was a good prototype default, but the project now needs a more production-shaped database setup
- PostgreSQL better matches the architecture expected from a long-running backend service
- this change upgrades the project story from local prototype persistence to a real client/server database workflow

## Main changes
- add `psycopg[binary]` to support PostgreSQL connections
- remove implicit SQLite defaulting from runtime settings
- restrict legacy bootstrap behavior so it only applies to SQLite URLs
- add a `postgres` service and PostgreSQL-first environment wiring in `docker-compose.yml`
- update `.env.example` and project docs to document PostgreSQL as the standard path
- update test bootstrap and migration tests to support PostgreSQL smoke validation

## Validation
- `python -m pytest -q`
- local result: `110 passed, 1 skipped`

## Out of scope
- no SQLite historical data import in this PR
- no dual write
- no zero-downtime cutover

## Follow-up
- run `docker compose up --build` on a machine with Docker installed to verify the Compose path end to end
- if historical data becomes important later, implement a one-off SQLite to PostgreSQL import with row-count and integrity checks
