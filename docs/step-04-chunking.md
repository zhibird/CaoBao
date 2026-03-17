# Step 04B - Chunking Documents for Retrieval

## Why this step exists

Vector search should not index full documents directly. We chunk documents into smaller pieces first.

If we skip this step, retrieval quality drops and token cost increases dramatically.

## What we added

1. `document_chunks` table (`app/models/document_chunk.py`).
2. Chunk API: `POST /api/v1/documents/{document_id}/chunk`.
3. Chunk query API: `GET /api/v1/documents/{document_id}/chunks?team_id=...`.
4. Team-scoped chunking: chunking only works when document belongs to the specified team.

## Runtime flow

1. API receives chunking params (`team_id`, `max_chars`, `overlap`).
2. `ChunkService` validates document ownership.
3. Existing chunks are replaced.
4. New chunks are generated and stored.

## Quick verification sequence

1. Import a long document.
2. Call chunk API with `max_chars=120`, `overlap=20`.
3. Confirm `total_chunks` is greater than 1.
4. Call list-chunks API and verify chunk count matches.