from uuid import uuid4


def test_retrieval_index_and_search(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_retrieval_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Retrieval Team",
            "description": "for retrieval test",
        },
    )
    assert create_team.status_code == 201

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "kb.md",
            "content_type": "md",
            "content": (
                "# Ops Playbook\n\n"
                "Always check alerts first. Escalate production incidents quickly. "
                "Keep incident channels updated every 10 minutes. "
                "Record timeline details for postmortem review."
            ),
        },
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["document_id"]

    chunk_response = client.post(
        f"/api/v1/documents/{document_id}/chunk",
        json={
            "team_id": team_id,
            "max_chars": 100,
            "overlap": 10,
        },
    )
    assert chunk_response.status_code == 200
    assert chunk_response.json()["total_chunks"] >= 2

    index_response = client.post(
        "/api/v1/retrieval/index",
        json={
            "team_id": team_id,
            "document_id": document_id,
        },
    )
    assert index_response.status_code == 200
    assert index_response.json()["indexed_chunks"] >= 2

    search_response = client.post(
        "/api/v1/retrieval/search",
        json={
            "team_id": team_id,
            "query": "alerts",
            "top_k": 3,
            "document_id": document_id,
        },
    )
    assert search_response.status_code == 200

    body = search_response.json()
    assert len(body["hits"]) >= 1
    assert body["hits"][0]["team_id"] == team_id


def test_retrieval_search_requires_indexing_first(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_retrieval_empty_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "No Index Team",
            "description": "search before index",
        },
    )
    assert create_team.status_code == 201

    search_response = client.post(
        "/api/v1/retrieval/search",
        json={
            "team_id": team_id,
            "query": "alerts",
            "top_k": 5,
        },
    )

    assert search_response.status_code == 404