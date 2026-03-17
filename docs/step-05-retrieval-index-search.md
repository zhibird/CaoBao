# Step 05A - Retrieval Index and TopK Search (No LLM Yet)

## Why this step exists

RAG requires two parts before generation:
1. Chunk embeddings (index)
2. Similarity search (retrieve)

If we skip this step, the assistant cannot ground answers in knowledge base content.

## What we added

1. `chunk_embeddings` table (`app/models/chunk_embedding.py`).
2. Index API: `POST /api/v1/retrieval/index`.
3. Search API: `POST /api/v1/retrieval/search`.
4. Deterministic local embedding service for MVP (`app/services/embedding_service.py`).

## Runtime flow

1. Chunking stores `document_chunks`.
2. Index API computes vector per chunk and saves `chunk_embeddings`.
3. Search API embeds query text and computes cosine similarity.
4. TopK chunks are returned as retrieval hits.

## Quick verification sequence

1. Import a document and chunk it.
2. Call index API for the team/document.
3. Call search API with a query and inspect `hits`.