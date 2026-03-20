from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval recall metrics on real scenarios.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Service base URL.")
    parser.add_argument("--team-id", required=True, help="Team id used for retrieval scope.")
    parser.add_argument("--dataset", required=True, help="Path to evaluation dataset JSON.")
    parser.add_argument("--top-k", type=int, default=5, help="Search top_k for each query.")
    parser.add_argument("--conversation-id", default=None, help="Optional conversation scope.")
    parser.add_argument("--document-id", default=None, help="Optional document scope.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise SystemExit(f"Dataset file not found: {dataset_path}")

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("Dataset must be a JSON array.")

    total = 0
    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_5 = 0
    failures = 0

    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            print(f"[skip] case#{idx}: invalid object")
            continue

        query = str(item.get("query", "")).strip()
        expected_document_ids = item.get("expected_document_ids", [])
        if not query or not isinstance(expected_document_ids, list) or not expected_document_ids:
            print(f"[skip] case#{idx}: missing query or expected_document_ids")
            continue

        expected = {str(value) for value in expected_document_ids if str(value).strip()}
        if not expected:
            print(f"[skip] case#{idx}: empty expected_document_ids")
            continue

        payload = {
            "team_id": args.team_id,
            "query": query,
            "top_k": max(args.top_k, 1),
        }
        if args.conversation_id:
            payload["conversation_id"] = args.conversation_id
        if args.document_id:
            payload["document_id"] = args.document_id

        total += 1
        try:
            response = httpx.post(
                f"{args.base_url.rstrip('/')}/api/v1/retrieval/search",
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            body = response.json()
            hits = body.get("hits", [])
            if not isinstance(hits, list):
                hits = []
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[error] case#{idx}: {exc}")
            continue

        hit_ids = [str(hit.get("document_id", "")) for hit in hits if isinstance(hit, dict)]

        if any(doc_id in expected for doc_id in hit_ids[:1]):
            hit_at_1 += 1
        if any(doc_id in expected for doc_id in hit_ids[:3]):
            hit_at_3 += 1
        if any(doc_id in expected for doc_id in hit_ids[:5]):
            hit_at_5 += 1

    if total == 0:
        raise SystemExit("No valid cases found in dataset.")

    print("RAG Evaluation Summary")
    print(f"total_cases={total}")
    print(f"failed_cases={failures}")
    print(f"recall@1={hit_at_1 / total:.4f}")
    print(f"recall@3={hit_at_3 / total:.4f}")
    print(f"recall@5={hit_at_5 / total:.4f}")


if __name__ == "__main__":
    main()
