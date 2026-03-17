# Step 04 - Document Import (txt/md)

## Why this step exists

RAG needs source documents. This step creates the minimum ingestion pipeline: save team-scoped raw text documents.

If we skip this step, retrieval has no data source and the assistant can only do generic chat.

## What we added

1. `documents` table (`app/models/document.py`).
2. Import API: `POST /api/v1/documents/import`.
3. Query APIs:
   - `GET /api/v1/documents?team_id=...`
   - `GET /api/v1/documents/{document_id}?team_id=...`
4. Team isolation: every document must belong to an existing team.

## Runtime flow

1. API receives document payload.
2. `DocumentService` validates that `team_id` exists.
3. Document is saved in SQLite.
4. Caller can list/get documents only within the same team scope.

## Quick verification sequence

1. Create team.
2. Import one `md` or `txt` document.
3. List documents by `team_id`.
4. Fetch single document with `document_id` and `team_id`.
5. Try importing with unknown `team_id` and observe `404`.