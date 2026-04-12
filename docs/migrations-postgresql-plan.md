# PostgreSQL Primary Database Notes

This project now treats PostgreSQL as the primary runtime database. SQLite remains available only as a legacy compatibility and backup/debug path.

## Current runtime policy
- `DATABASE_URL` must be provided explicitly.
- PostgreSQL is the default target for local development and Docker Compose.
- Alembic is the source of truth for schema changes.
- SQLite legacy bootstrap stays available only for SQLite URLs and non-production compatibility flows.

## What changed in this upgrade
- Added `psycopg[binary]` so SQLAlchemy and Alembic can talk to PostgreSQL directly.
- Removed the implicit SQLite default from runtime configuration.
- Updated `docker-compose.yml` to start a `postgres` service and wire the API container to it.
- Updated `.env.example` and related docs so the standard developer path is PostgreSQL-first.
- Added PostgreSQL-oriented test bootstrap and migration smoke coverage.

## What is intentionally out of scope
- No SQLite to PostgreSQL historical data import in this branch.
- No dual write between SQLite and PostgreSQL.
- No zero-downtime production cutover design.

## Verification status
- Full local pytest suite passes for this upgrade.
- Docker-based runtime verification still needs to be run on a machine with Docker installed.

## Related docs
- See [sqlite-backup-and-future-migration.md](./sqlite-backup-and-future-migration.md) for how to preserve SQLite as a historical backup and what a later full migration should cover.
- See [pr-postgresql-primary.md](./pr-postgresql-primary.md) for a ready-to-paste pull request description for this branch.
