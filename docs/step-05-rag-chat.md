# Step 05B - RAG Chat Answer Generation

## Why this step exists

Index and retrieval only return relevant chunks. Users need a final natural-language answer.

If we skip this step, users must read raw chunks manually and the CaiBao experience is incomplete.


## What we added

1. Chat ask API: `POST /api/v1/chat/ask`.
2. `RagChatService`: user validation + retrieval + answer generation.
3. `LLMService`:
   - `mock` mode (default, no external dependency)
   - OpenAI-compatible mode (optional via env config)

## Runtime flow

1. Validate `user_id` belongs to `team_id`.
2. Retrieve TopK chunks from indexed data.
3. Build answer via LLM service.
4. Return final answer with retrieval hits.

## Quick verification sequence

1. Ensure document chunking and retrieval indexing are done.
2. Call `POST /api/v1/chat/ask`.
3. Verify `answer` and `hits` are both returned.