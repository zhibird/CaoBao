# Migration Strategy Notes (SQLite Now, PostgreSQL Ready)

This project continues to run on SQLite in this phase. We add Alembic now so schema upgrades are versioned and repeatable.

## Scope in this phase
- Runtime database stays SQLite.
- Alembic is added for schema evolution.
- New migration creates `memory_cards` and `memory_card_embeddings`.

## PostgreSQL compatibility constraints
- Keep primary and foreign keys as `VARCHAR` to match current IDs.
- Use `TEXT` for JSON-like payloads (`vector_json`) for cross-dialect safety.
- Use `DateTime(timezone=True)` for timestamp columns.
- Use `CHECK` constraints for enum-like fields (`status`, `scope_level`) instead of dialect-specific enums.
- Avoid SQLite-specific SQL in Alembic revisions.

## Planned switch checklist (future)
1. Add PostgreSQL `DATABASE_URL` in environment and compose override.
2. Run `python -m alembic upgrade head` against PostgreSQL.
3. Validate app startup and CRUD smoke tests.
4. Validate index usage and query plans for retrieval/memory workloads.
5. Keep SQLite path available for local/offline dev.
