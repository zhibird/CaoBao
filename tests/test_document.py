import time
from io import BytesIO
from uuid import uuid4

from PIL import Image
from pypdf import PdfWriter


def _wait_document_terminal_status(client, *, team_id: str, document_id: str, max_attempts: int = 30) -> str:
    for _ in range(max_attempts):
        response = client.get(f"/api/v1/documents/{document_id}", params={"team_id": team_id})
        assert response.status_code == 200
        status = response.json()["status"]
        if status in {"ready", "failed"}:
            return status
        time.sleep(0.05)
    raise AssertionError("document did not reach terminal status in time")


def _build_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _build_png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), color=(255, 255, 255)).save(output, format="PNG")
    return output.getvalue()


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


def test_document_status_and_delete_flow(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_doc_status_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Doc Status Team",
            "description": "for document status",
        },
    )
    assert create_team.status_code == 201

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "status.md",
            "content_type": "md",
            "content": "# Status\n\nChunk and index me.",
        },
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["document_id"]
    assert import_response.json()["status"] == "uploaded"

    chunk_response = client.post(
        f"/api/v1/documents/{document_id}/chunk",
        json={
            "team_id": team_id,
            "max_chars": 100,
            "overlap": 10,
        },
    )
    assert chunk_response.status_code == 200

    after_chunk = client.get(f"/api/v1/documents/{document_id}", params={"team_id": team_id})
    assert after_chunk.status_code == 200
    assert after_chunk.json()["status"] == "uploaded"

    index_response = client.post(
        "/api/v1/retrieval/index",
        json={
            "team_id": team_id,
            "document_ids": [document_id],
        },
    )
    assert index_response.status_code == 200

    after_index = client.get(f"/api/v1/documents/{document_id}", params={"team_id": team_id})
    assert after_index.status_code == 200
    assert after_index.json()["status"] == "ready"

    delete_response = client.delete(
        f"/api/v1/documents/{document_id}",
        params={"team_id": team_id},
    )
    assert delete_response.status_code == 204

    list_response = client.get("/api/v1/documents", params={"team_id": team_id})
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_document_upload_supports_pdf_and_image(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_upload_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Upload Team",
            "description": "for upload test",
        },
    )
    assert create_team.status_code == 201

    pdf_upload = client.post(
        "/api/v1/documents/upload",
        data={
            "team_id": team_id,
            "auto_index": "true",
        },
        files={
            "file": ("report.pdf", _build_pdf_bytes(), "application/pdf"),
        },
    )
    assert pdf_upload.status_code == 201
    pdf_doc = pdf_upload.json()
    assert pdf_doc["content_type"] == "pdf"
    assert pdf_doc["mime_type"] == "application/pdf"

    pdf_status = _wait_document_terminal_status(
        client,
        team_id=team_id,
        document_id=pdf_doc["document_id"],
    )
    assert pdf_status == "ready"

    pdf_file = client.get(
        f"/api/v1/documents/{pdf_doc['document_id']}/file",
        params={"team_id": team_id},
    )
    assert pdf_file.status_code == 200
    assert "application/pdf" in pdf_file.headers.get("content-type", "")

    image_upload = client.post(
        "/api/v1/documents/upload",
        data={
            "team_id": team_id,
            "auto_index": "true",
        },
        files={
            "file": ("receipt.png", _build_png_bytes(), "image/png"),
        },
    )
    assert image_upload.status_code == 201
    image_doc = image_upload.json()
    assert image_doc["content_type"] == "png"
    assert image_doc["mime_type"] == "image/png"

    image_status = _wait_document_terminal_status(
        client,
        team_id=team_id,
        document_id=image_doc["document_id"],
    )
    assert image_status == "ready"
