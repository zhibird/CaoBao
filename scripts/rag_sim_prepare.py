from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare RAG simulation corpus: create scope, import docs, chunk docs, and rebuild index."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Service base URL.")
    parser.add_argument("--api-prefix", default="/api/v1", help="API prefix.")
    parser.add_argument("--team-id", default="rag-sim-team", help="Team ID for simulation.")
    parser.add_argument("--team-name", default="RAG Simulation Team", help="Team display name.")
    parser.add_argument("--user-id", default="rag-sim-user", help="User ID for simulation.")
    parser.add_argument("--user-name", default="RAG Simulator", help="User display name.")
    parser.add_argument("--conversation-id", default=None, help="Reuse existing conversation ID if provided.")
    parser.add_argument("--conversation-title", default="RAG Simulation", help="Conversation title prefix.")
    parser.add_argument(
        "--corpus-dir",
        default="docs/rag_simulation/corpus",
        help="Directory containing .md/.txt corpus files.",
    )
    parser.add_argument("--max-chars", type=int, default=500, help="Chunk max chars.")
    parser.add_argument("--overlap", type=int, default=80, help="Chunk overlap chars.")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout seconds.")
    parser.add_argument("--manifest-out", default="docs/rag_simulation/run/manifest.json", help="Manifest output path.")
    parser.add_argument("--rebuild", dest="rebuild", action="store_true", default=True, help="Rebuild vector index scope.")
    parser.add_argument("--no-rebuild", dest="rebuild", action="store_false", help="Skip index rebuild before indexing.")
    return parser.parse_args()


def api_url(base_url: str, api_prefix: str, path: str) -> str:
    normalized_prefix = "/" + api_prefix.strip("/")
    normalized_path = "/" + path.strip("/")
    return f"{base_url.rstrip('/')}{normalized_prefix}{normalized_path}"


def ensure_team(
    client: httpx.Client,
    *,
    base_url: str,
    api_prefix: str,
    team_id: str,
    team_name: str,
) -> None:
    response = client.post(
        api_url(base_url, api_prefix, "/teams"),
        json={
            "team_id": team_id,
            "name": team_name,
            "description": "Synthetic team for RAG simulation.",
        },
    )
    if response.status_code in (200, 201):
        return
    if response.status_code == 409:
        return
    raise SystemExit(f"Failed to ensure team: {response.status_code} {response.text}")


def ensure_user(
    client: httpx.Client,
    *,
    base_url: str,
    api_prefix: str,
    user_id: str,
    team_id: str,
    user_name: str,
) -> None:
    response = client.post(
        api_url(base_url, api_prefix, "/users"),
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": user_name,
            "role": "member",
        },
    )
    if response.status_code in (200, 201):
        return
    if response.status_code == 409:
        existing = client.get(api_url(base_url, api_prefix, f"/users/{user_id}"))
        if existing.status_code != 200:
            raise SystemExit(
                f"User conflict but cannot fetch existing user: {existing.status_code} {existing.text}"
            )
        body = existing.json()
        existing_team = str(body.get("team_id", ""))
        if existing_team != team_id:
            raise SystemExit(
                f"User '{user_id}' already exists in another team: {existing_team}. "
                f"Please use another --user-id."
            )
        return
    raise SystemExit(f"Failed to ensure user: {response.status_code} {response.text}")


def create_conversation(
    client: httpx.Client,
    *,
    base_url: str,
    api_prefix: str,
    team_id: str,
    user_id: str,
    title_prefix: str,
) -> str:
    stamped_title = f"{title_prefix} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    response = client.post(
        api_url(base_url, api_prefix, "/conversations"),
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": stamped_title,
        },
    )
    if response.status_code not in (200, 201):
        raise SystemExit(f"Failed to create conversation: {response.status_code} {response.text}")
    payload = response.json()
    conversation_id = str(payload.get("conversation_id", "")).strip()
    if not conversation_id:
        raise SystemExit("Create conversation response missing conversation_id.")
    return conversation_id


def list_corpus_files(corpus_dir: Path) -> list[Path]:
    if not corpus_dir.exists() or not corpus_dir.is_dir():
        raise SystemExit(f"Corpus directory not found: {corpus_dir}")
    files = [path for path in corpus_dir.iterdir() if path.is_file() and path.suffix.lower() in {".md", ".txt"}]
    files.sort(key=lambda item: item.name)
    if not files:
        raise SystemExit(f"No corpus files found in: {corpus_dir}")
    return files


def import_and_chunk_documents(
    client: httpx.Client,
    *,
    base_url: str,
    api_prefix: str,
    team_id: str,
    conversation_id: str,
    files: list[Path],
    max_chars: int,
    overlap: int,
) -> list[dict[str, Any]]:
    imported: list[dict[str, Any]] = []
    for path in files:
        content = path.read_text(encoding="utf-8")
        content_type = "md" if path.suffix.lower() == ".md" else "txt"

        import_resp = client.post(
            api_url(base_url, api_prefix, "/documents/import"),
            json={
                "team_id": team_id,
                "conversation_id": conversation_id,
                "source_name": path.name,
                "content_type": content_type,
                "content": content,
            },
        )
        if import_resp.status_code not in (200, 201):
            raise SystemExit(
                f"Failed importing {path.name}: {import_resp.status_code} {import_resp.text}"
            )
        import_body = import_resp.json()
        document_id = str(import_body.get("document_id", "")).strip()
        if not document_id:
            raise SystemExit(f"Import response missing document_id for {path.name}")

        chunk_resp = client.post(
            api_url(base_url, api_prefix, f"/documents/{document_id}/chunk"),
            json={
                "team_id": team_id,
                "conversation_id": conversation_id,
                "max_chars": max_chars,
                "overlap": overlap,
            },
        )
        if chunk_resp.status_code != 200:
            raise SystemExit(
                f"Failed chunking {path.name}: {chunk_resp.status_code} {chunk_resp.text}"
            )
        chunk_body = chunk_resp.json()
        imported.append(
            {
                "source_name": path.name,
                "document_id": document_id,
                "content_type": content_type,
                "content_chars": len(content),
                "chunk_count": int(chunk_body.get("total_chunks", 0)),
            }
        )
    return imported


def rebuild_index(
    client: httpx.Client,
    *,
    base_url: str,
    api_prefix: str,
    team_id: str,
    conversation_id: str,
    rebuild: bool,
) -> int:
    response = client.post(
        api_url(base_url, api_prefix, "/retrieval/index"),
        json={
            "team_id": team_id,
            "conversation_id": conversation_id,
            "rebuild": rebuild,
        },
    )
    if response.status_code != 200:
        raise SystemExit(f"Failed indexing chunks: {response.status_code} {response.text}")
    body = response.json()
    return int(body.get("indexed_chunks", 0))


def main() -> None:
    args = parse_args()
    corpus_dir = Path(args.corpus_dir)
    manifest_path = Path(args.manifest_out)

    files = list_corpus_files(corpus_dir)

    with httpx.Client(timeout=args.timeout) as client:
        ensure_team(
            client,
            base_url=args.base_url,
            api_prefix=args.api_prefix,
            team_id=args.team_id,
            team_name=args.team_name,
        )
        ensure_user(
            client,
            base_url=args.base_url,
            api_prefix=args.api_prefix,
            user_id=args.user_id,
            team_id=args.team_id,
            user_name=args.user_name,
        )

        conversation_id = args.conversation_id
        if not conversation_id:
            conversation_id = create_conversation(
                client,
                base_url=args.base_url,
                api_prefix=args.api_prefix,
                team_id=args.team_id,
                user_id=args.user_id,
                title_prefix=args.conversation_title,
            )

        imported = import_and_chunk_documents(
            client,
            base_url=args.base_url,
            api_prefix=args.api_prefix,
            team_id=args.team_id,
            conversation_id=conversation_id,
            files=files,
            max_chars=args.max_chars,
            overlap=args.overlap,
        )
        indexed_chunks = rebuild_index(
            client,
            base_url=args.base_url,
            api_prefix=args.api_prefix,
            team_id=args.team_id,
            conversation_id=conversation_id,
            rebuild=args.rebuild,
        )

    source_to_document = {item["source_name"]: item["document_id"] for item in imported}
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "api_prefix": args.api_prefix,
        "team_id": args.team_id,
        "user_id": args.user_id,
        "conversation_id": conversation_id,
        "indexed_chunks": indexed_chunks,
        "documents": imported,
        "source_name_to_document_id": source_to_document,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("RAG simulation preparation complete.")
    print(f"team_id={args.team_id}")
    print(f"user_id={args.user_id}")
    print(f"conversation_id={conversation_id}")
    print(f"documents_imported={len(imported)}")
    print(f"indexed_chunks={indexed_chunks}")
    print(f"manifest={manifest_path.as_posix()}")


if __name__ == "__main__":
    main()
