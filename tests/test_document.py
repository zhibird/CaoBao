from uuid import uuid4


def test_document_import_and_query_in_team(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_doc_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Doc Team",
            "description": "for doc import",
        },
    )
    assert create_team.status_code == 201

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "ops-guide.md",
            "content_type": "md",
            "content": "# Ops Guide\n\nAlways check alerts first.",
        },
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["document_id"]

    list_response = client.get("/api/v1/documents", params={"team_id": team_id})
    assert list_response.status_code == 200
    listed_ids = [item["document_id"] for item in list_response.json()]
    assert document_id in listed_ids

    get_response = client.get(
        f"/api/v1/documents/{document_id}",
        params={"team_id": team_id},
    )
    assert get_response.status_code == 200
    assert get_response.json()["source_name"] == "ops-guide.md"


def test_document_chunking_and_list_chunks(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_chunk_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Chunk Team",
            "description": "for chunk test",
        },
    )
    assert create_team.status_code == 201

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "long.txt",
            "content_type": "txt",
            "content": "A" * 420,
        },
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["document_id"]

    chunk_response = client.post(
        f"/api/v1/documents/{document_id}/chunk",
        json={
            "team_id": team_id,
            "max_chars": 120,
            "overlap": 20,
        },
    )
    assert chunk_response.status_code == 200
    body = chunk_response.json()
    assert body["total_chunks"] >= 3

    list_chunks_response = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        params={"team_id": team_id},
    )
    assert list_chunks_response.status_code == 200
    assert len(list_chunks_response.json()) == body["total_chunks"]


def test_document_chunking_rejects_invalid_overlap(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_chunk_invalid_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Chunk Invalid Team",
            "description": "for invalid overlap test",
        },
    )
    assert create_team.status_code == 201

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "short.txt",
            "content_type": "txt",
            "content": "short content for testing",
        },
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["document_id"]

    chunk_response = client.post(
        f"/api/v1/documents/{document_id}/chunk",
        json={
            "team_id": team_id,
            "max_chars": 100,
            "overlap": 100,
        },
    )
    assert chunk_response.status_code == 400


def test_document_import_requires_existing_team(client) -> None:
    response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": "team_not_exists",
            "source_name": "faq.txt",
            "content_type": "txt",
            "content": "Q: Who handles incidents?",
        },
    )

    assert response.status_code == 404