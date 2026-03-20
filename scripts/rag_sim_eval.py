from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


@dataclass
class EvalCase:
    case_id: str
    scenario: str
    question: str
    expected_source_names: list[str]
    expected_document_ids: list[str]
    require_all_sources: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality for minimal real-world scenarios.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Service base URL.")
    parser.add_argument("--api-prefix", default="/api/v1", help="API prefix.")
    parser.add_argument("--team-id", required=True, help="Team ID.")
    parser.add_argument("--conversation-id", required=True, help="Conversation ID used for indexed corpus scope.")
    parser.add_argument("--dataset", default="docs/rag_simulation/dataset_minimal.json", help="Evaluation dataset JSON.")
    parser.add_argument("--manifest", default="docs/rag_simulation/run/manifest.json", help="Preparation manifest JSON.")
    parser.add_argument("--top-ks", default="1,3,5", help="Comma-separated k list, e.g. 1,3,5.")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout seconds.")
    parser.add_argument("--output-dir", default="docs/rag_simulation/run", help="Output directory.")
    parser.add_argument("--output-prefix", default="eval", help="Output file prefix.")
    parser.add_argument("--with-baseline", dest="with_baseline", action="store_true", default=True)
    parser.add_argument("--no-baseline", dest="with_baseline", action="store_false")
    return parser.parse_args()


def api_url(base_url: str, api_prefix: str, path: str) -> str:
    normalized_prefix = "/" + api_prefix.strip("/")
    normalized_path = "/" + path.strip("/")
    return f"{base_url.rstrip('/')}{normalized_prefix}{normalized_path}"


def parse_top_ks(raw: str) -> list[int]:
    values = []
    for item in raw.split(","):
        stripped = item.strip()
        if not stripped:
            continue
        try:
            value = int(stripped)
        except ValueError as exc:
            raise SystemExit(f"Invalid k value in --top-ks: {stripped}") from exc
        if value <= 0:
            raise SystemExit("All k values in --top-ks must be positive integers.")
        values.append(value)
    if not values:
        raise SystemExit("--top-ks cannot be empty.")
    return sorted(set(values))


def load_manifest(path: Path) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Manifest not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    source_to_doc = payload.get("source_name_to_document_id")
    if not isinstance(source_to_doc, dict):
        source_to_doc = {}
        for doc in payload.get("documents", []):
            if not isinstance(doc, dict):
                continue
            source_name = str(doc.get("source_name", "")).strip()
            document_id = str(doc.get("document_id", "")).strip()
            if source_name and document_id:
                source_to_doc[source_name] = document_id
    if not source_to_doc:
        raise SystemExit("Manifest does not contain source_name_to_document_id mapping.")
    doc_to_source = {doc_id: source_name for source_name, doc_id in source_to_doc.items()}
    return source_to_doc, doc_to_source, payload


def load_dataset(path: Path, source_to_doc: dict[str, str]) -> list[EvalCase]:
    if not path.exists():
        raise SystemExit(f"Dataset not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("Dataset must be a JSON array.")

    cases: list[EvalCase] = []
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Dataset item #{idx} is not an object.")

        case_id = str(item.get("case_id", "")).strip() or f"case-{idx}"
        scenario = str(item.get("scenario", "")).strip() or "unknown"
        question = str(item.get("question", "")).strip()
        expected_source_names = item.get("expected_source_names", [])
        require_all = bool(item.get("require_all_sources", False))

        if not question:
            raise SystemExit(f"{case_id}: empty question.")
        if not isinstance(expected_source_names, list) or not expected_source_names:
            raise SystemExit(f"{case_id}: expected_source_names must be a non-empty list.")

        cleaned_sources: list[str] = []
        expected_doc_ids: list[str] = []
        for value in expected_source_names:
            source = str(value).strip()
            if not source:
                continue
            doc_id = source_to_doc.get(source)
            if not doc_id:
                raise SystemExit(
                    f"{case_id}: expected source '{source}' not found in manifest mapping."
                )
            cleaned_sources.append(source)
            expected_doc_ids.append(doc_id)

        if not expected_doc_ids:
            raise SystemExit(f"{case_id}: no valid expected source mapping after normalization.")

        if len(expected_doc_ids) > 1:
            require_all = True

        cases.append(
            EvalCase(
                case_id=case_id,
                scenario=scenario,
                question=question,
                expected_source_names=cleaned_sources,
                expected_document_ids=expected_doc_ids,
                require_all_sources=require_all,
            )
        )
    return cases


def search_dense(
    client: httpx.Client,
    *,
    base_url: str,
    api_prefix: str,
    team_id: str,
    conversation_id: str,
    question: str,
    top_k: int,
) -> list[dict[str, Any]]:
    response = client.post(
        api_url(base_url, api_prefix, "/retrieval/search"),
        json={
            "team_id": team_id,
            "conversation_id": conversation_id,
            "query": question,
            "top_k": top_k,
        },
    )
    response.raise_for_status()
    body = response.json()
    hits = body.get("hits", [])
    if not isinstance(hits, list):
        return []
    clean_hits: list[dict[str, Any]] = []
    for hit in hits:
        if isinstance(hit, dict):
            clean_hits.append(hit)
    return clean_hits


def tokenize(text: str) -> set[str]:
    lowered = text.lower()
    return set(re.findall(r"[0-9a-zA-Z_]+|[\u4e00-\u9fff]+", lowered))


def fetch_chunks_for_baseline(
    client: httpx.Client,
    *,
    base_url: str,
    api_prefix: str,
    team_id: str,
    conversation_id: str,
    document_ids: list[str],
) -> dict[str, list[set[str]]]:
    result: dict[str, list[set[str]]] = {}
    for document_id in document_ids:
        response = client.get(
            api_url(base_url, api_prefix, f"/documents/{document_id}/chunks"),
            params={
                "team_id": team_id,
                "conversation_id": conversation_id,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            result[document_id] = []
            continue

        chunks_tokens: list[set[str]] = []
        for chunk in payload:
            if not isinstance(chunk, dict):
                continue
            content = str(chunk.get("content", ""))
            chunks_tokens.append(tokenize(content))
        result[document_id] = chunks_tokens
    return result


def lexical_rank_documents(
    query: str,
    *,
    chunks_by_document: dict[str, list[set[str]]],
) -> list[tuple[str, float]]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return [(doc_id, 0.0) for doc_id in chunks_by_document]

    ranked: list[tuple[str, float]] = []
    for document_id, chunk_tokens_list in chunks_by_document.items():
        best = 0.0
        for tokens in chunk_tokens_list:
            if not tokens:
                continue
            overlap = len(query_tokens & tokens)
            if overlap == 0:
                continue
            score = overlap / math.sqrt(len(query_tokens) * len(tokens))
            if score > best:
                best = score
        ranked.append((document_id, round(best, 6)))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def best_rank(hit_doc_ids: list[str], expected_doc_ids: list[str]) -> int | None:
    expected_set = set(expected_doc_ids)
    for idx, doc_id in enumerate(hit_doc_ids, start=1):
        if doc_id in expected_set:
            return idx
    return None


def compute_hit_flags(
    hit_doc_ids: list[str],
    expected_doc_ids: list[str],
    top_ks: list[int],
    *,
    require_all_sources: bool,
) -> tuple[dict[int, bool], dict[int, bool | None]]:
    expected_set = set(expected_doc_ids)
    any_hit_at: dict[int, bool] = {}
    all_hit_at: dict[int, bool | None] = {}
    for k in top_ks:
        top_ids = set(hit_doc_ids[:k])
        any_hit_at[k] = bool(top_ids & expected_set)
        if require_all_sources:
            all_hit_at[k] = expected_set.issubset(top_ids)
        else:
            all_hit_at[k] = None
    return any_hit_at, all_hit_at


def summarize_metrics(
    records: list[dict[str, Any]],
    top_ks: list[int],
    *,
    prefix: str,
) -> dict[str, Any]:
    total = len(records)
    metrics: dict[str, Any] = {
        "total_cases": total,
        "recall_any": {},
        "recall_all_sources": {},
    }
    if total == 0:
        return metrics

    for k in top_ks:
        hit_count = sum(1 for record in records if record[f"{prefix}_any_hit_at"][str(k)])
        metrics["recall_any"][str(k)] = round(hit_count / total, 4)

    multi_cases = [record for record in records if record["require_all_sources"]]
    if not multi_cases:
        for k in top_ks:
            metrics["recall_all_sources"][str(k)] = None
        return metrics

    for k in top_ks:
        hit_count = sum(
            1
            for record in multi_cases
            if record[f"{prefix}_all_hit_at"][str(k)] is True
        )
        metrics["recall_all_sources"][str(k)] = round(hit_count / len(multi_cases), 4)
    return metrics


def group_by_scenario(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["scenario"])].append(record)
    return dict(grouped)


def format_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"


def format_delta(new_value: float | None, old_value: float | None) -> str:
    if new_value is None or old_value is None:
        return "-"
    return f"{new_value - old_value:+.4f}"


def metric_bar(value: float | None, width: int = 20) -> str:
    if value is None:
        return "-" * width
    clipped = max(0.0, min(1.0, value))
    filled = int(round(clipped * width))
    return "█" * filled + "░" * (width - filled)


def build_report_markdown(
    *,
    generated_at: str,
    team_id: str,
    conversation_id: str,
    dataset_path: Path,
    manifest_path: Path,
    top_ks: list[int],
    dense_overall: dict[str, Any],
    baseline_overall: dict[str, Any] | None,
    dense_by_scenario: dict[str, dict[str, Any]],
    baseline_by_scenario: dict[str, dict[str, Any]] | None,
    source_hit_rows: list[dict[str, Any]],
    failures_top10: list[dict[str, Any]],
    failure_at_k: int,
) -> str:
    lines: list[str] = []
    lines.append("# RAG Simulation Evaluation Report")
    lines.append("")
    lines.append(f"- Generated at: `{generated_at}`")
    lines.append(f"- Team ID: `{team_id}`")
    lines.append(f"- Conversation ID: `{conversation_id}`")
    lines.append(f"- Dataset: `{dataset_path.as_posix()}`")
    lines.append(f"- Manifest: `{manifest_path.as_posix()}`")
    lines.append("")

    lines.append("## Overall Recall")
    lines.append("")
    lines.append("| Metric | Baseline | Dense | Uplift |")
    lines.append("|---|---:|---:|---:|")
    for k in top_ks:
        dense_value = dense_overall["recall_any"].get(str(k))
        baseline_value = baseline_overall["recall_any"].get(str(k)) if baseline_overall else None
        lines.append(
            f"| Recall@{k} (any source) | {format_ratio(baseline_value)} | {format_ratio(dense_value)} | {format_delta(dense_value, baseline_value)} |"
        )
    for k in top_ks:
        dense_value = dense_overall["recall_all_sources"].get(str(k))
        baseline_value = baseline_overall["recall_all_sources"].get(str(k)) if baseline_overall else None
        lines.append(
            f"| Multi-source Recall@{k} (all sources) | {format_ratio(baseline_value)} | {format_ratio(dense_value)} | {format_delta(dense_value, baseline_value)} |"
        )
    lines.append("")

    lines.append("## Visual Uplift")
    lines.append("")
    for k in top_ks:
        dense_value = dense_overall["recall_any"].get(str(k))
        baseline_value = baseline_overall["recall_any"].get(str(k)) if baseline_overall else None
        lines.append(f"- Recall@{k} baseline: `{metric_bar(baseline_value)}` {format_ratio(baseline_value)}")
        lines.append(f"- Recall@{k} dense:    `{metric_bar(dense_value)}` {format_ratio(dense_value)}")
    lines.append("")

    lines.append("## Scenario Breakdown")
    lines.append("")
    lines.append("| Scenario | Cases | Baseline R@1 | Dense R@1 | Baseline R@3 | Dense R@3 | Baseline R@5 | Dense R@5 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for scenario in sorted(dense_by_scenario):
        dense_metrics = dense_by_scenario[scenario]
        baseline_metrics = baseline_by_scenario.get(scenario) if baseline_by_scenario else None
        lines.append(
            "| {scenario} | {cases} | {b1} | {d1} | {b3} | {d3} | {b5} | {d5} |".format(
                scenario=scenario,
                cases=dense_metrics["total_cases"],
                b1=format_ratio(
                    baseline_metrics["recall_any"].get("1") if baseline_metrics else None
                ),
                d1=format_ratio(dense_metrics["recall_any"].get("1")),
                b3=format_ratio(
                    baseline_metrics["recall_any"].get("3") if baseline_metrics else None
                ),
                d3=format_ratio(dense_metrics["recall_any"].get("3")),
                b5=format_ratio(
                    baseline_metrics["recall_any"].get("5") if baseline_metrics else None
                ),
                d5=format_ratio(dense_metrics["recall_any"].get("5")),
            )
        )
    lines.append("")

    lines.append("## Source Hit Coverage (Dense @5)")
    lines.append("")
    lines.append("| Source | Expected Cases | Hit@5 Cases | Hit Rate | Top1 Wins |")
    lines.append("|---|---:|---:|---:|---:|")
    for row in source_hit_rows:
        lines.append(
            f"| {row['source_name']} | {row['expected_cases']} | {row['hit_at_5_cases']} | {row['hit_rate']} | {row['top1_wins']} |"
        )
    lines.append("")

    lines.append("## Failure Top10 (Dense)")
    lines.append("")
    lines.append("| Case | Scenario | Best Rank | Expected Sources | Retrieved Top3 |")
    lines.append("|---|---|---:|---|---|")
    for failure in failures_top10:
        lines.append(
            "| {case_id} | {scenario} | {best_rank} | {expected} | {retrieved} |".format(
                case_id=failure["case_id"],
                scenario=failure["scenario"],
                best_rank=failure["best_rank"] if failure["best_rank"] is not None else "miss",
                expected=", ".join(failure["expected_source_names"]),
                retrieved=", ".join(failure["retrieved_top3_sources"]),
            )
        )
    lines.append("")
    lines.append(
        f"Note: `miss` means none of expected source documents appeared within top-{failure_at_k} retrieval results."
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    top_ks = parse_top_ks(args.top_ks)
    max_k = max(top_ks)

    dataset_path = Path(args.dataset)
    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_to_doc, doc_to_source, manifest_payload = load_manifest(manifest_path)
    cases = load_dataset(dataset_path, source_to_doc)

    source_expected_cases: dict[str, int] = defaultdict(int)
    source_hit_at_5: dict[str, int] = defaultdict(int)
    source_top1_wins: dict[str, int] = defaultdict(int)

    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    with httpx.Client(timeout=args.timeout) as client:
        for case in cases:
            for source_name in case.expected_source_names:
                source_expected_cases[source_name] += 1

            try:
                dense_hits = search_dense(
                    client,
                    base_url=args.base_url,
                    api_prefix=args.api_prefix,
                    team_id=args.team_id,
                    conversation_id=args.conversation_id,
                    question=case.question,
                    top_k=max_k,
                )
                dense_error = None
            except Exception as exc:  # noqa: BLE001
                dense_hits = []
                dense_error = str(exc)
                errors.append({"case_id": case.case_id, "error": dense_error})

            dense_doc_ids = [str(hit.get("document_id", "")) for hit in dense_hits]
            dense_rank = best_rank(dense_doc_ids, case.expected_document_ids)
            dense_any_hit, dense_all_hit = compute_hit_flags(
                dense_doc_ids,
                case.expected_document_ids,
                top_ks,
                require_all_sources=case.require_all_sources,
            )

            top5_ids = set(dense_doc_ids[:5])
            expected_doc_set = set(case.expected_document_ids)
            if expected_doc_set & top5_ids:
                for source_name, document_id in zip(case.expected_source_names, case.expected_document_ids):
                    if document_id in top5_ids:
                        source_hit_at_5[source_name] += 1

            top1_doc = dense_doc_ids[0] if dense_doc_ids else None
            if top1_doc in expected_doc_set:
                source_name = doc_to_source.get(top1_doc, top1_doc)
                source_top1_wins[source_name] += 1

            retrieved_entries = []
            for rank, hit in enumerate(dense_hits, start=1):
                document_id = str(hit.get("document_id", ""))
                retrieved_entries.append(
                    {
                        "rank": rank,
                        "document_id": document_id,
                        "source_name": doc_to_source.get(document_id, document_id),
                        "score": float(hit.get("score", 0.0)),
                        "is_expected": document_id in expected_doc_set,
                    }
                )

            record = {
                "case_id": case.case_id,
                "scenario": case.scenario,
                "question": case.question,
                "expected_source_names": case.expected_source_names,
                "expected_document_ids": case.expected_document_ids,
                "require_all_sources": case.require_all_sources,
                "dense_error": dense_error,
                "dense_best_rank": dense_rank,
                "dense_any_hit_at": {str(k): dense_any_hit[k] for k in top_ks},
                "dense_all_hit_at": {str(k): dense_all_hit[k] for k in top_ks},
                "dense_hits": retrieved_entries,
            }
            records.append(record)

        baseline_overall: dict[str, Any] | None = None
        baseline_by_scenario: dict[str, dict[str, Any]] | None = None
        if args.with_baseline:
            unique_document_ids = list({doc_id for case in cases for doc_id in case.expected_document_ids})
            chunks_by_document = fetch_chunks_for_baseline(
                client,
                base_url=args.base_url,
                api_prefix=args.api_prefix,
                team_id=args.team_id,
                conversation_id=args.conversation_id,
                document_ids=unique_document_ids,
            )
            for record in records:
                ranked = lexical_rank_documents(record["question"], chunks_by_document=chunks_by_document)
                ranked_doc_ids = [doc_id for doc_id, _ in ranked]
                baseline_rank = best_rank(ranked_doc_ids, record["expected_document_ids"])
                baseline_any_hit, baseline_all_hit = compute_hit_flags(
                    ranked_doc_ids,
                    record["expected_document_ids"],
                    top_ks,
                    require_all_sources=record["require_all_sources"],
                )
                record["baseline_best_rank"] = baseline_rank
                record["baseline_any_hit_at"] = {str(k): baseline_any_hit[k] for k in top_ks}
                record["baseline_all_hit_at"] = {str(k): baseline_all_hit[k] for k in top_ks}
                record["baseline_hits"] = [
                    {
                        "rank": idx + 1,
                        "document_id": doc_id,
                        "source_name": doc_to_source.get(doc_id, doc_id),
                        "score": score,
                        "is_expected": doc_id in set(record["expected_document_ids"]),
                    }
                    for idx, (doc_id, score) in enumerate(ranked[:max_k])
                ]

            baseline_overall = summarize_metrics(records, top_ks, prefix="baseline")
            baseline_by_scenario = {}
            scenario_groups = group_by_scenario(records)
            for scenario, scenario_records in scenario_groups.items():
                baseline_by_scenario[scenario] = summarize_metrics(
                    scenario_records, top_ks, prefix="baseline"
                )

    dense_overall = summarize_metrics(records, top_ks, prefix="dense")
    dense_by_scenario = {}
    scenario_groups = group_by_scenario(records)
    for scenario, scenario_records in scenario_groups.items():
        dense_by_scenario[scenario] = summarize_metrics(scenario_records, top_ks, prefix="dense")

    worst_rank_sort_value = lambda record: record["dense_best_rank"] if record["dense_best_rank"] is not None else 9999
    sorted_records = sorted(records, key=worst_rank_sort_value, reverse=True)
    failures_top10: list[dict[str, Any]] = []
    failure_key = str(max_k)
    for record in sorted_records:
        if record["dense_any_hit_at"].get(failure_key):
            continue
        retrieved_top3 = [hit["source_name"] for hit in record["dense_hits"][:3]]
        failures_top10.append(
            {
                "case_id": record["case_id"],
                "scenario": record["scenario"],
                "question": record["question"],
                "best_rank": record["dense_best_rank"],
                "expected_source_names": record["expected_source_names"],
                "retrieved_top3_sources": retrieved_top3,
                "error": record["dense_error"],
            }
        )
        if len(failures_top10) >= 10:
            break

    source_hit_rows: list[dict[str, Any]] = []
    for source_name in sorted(source_expected_cases):
        expected_count = source_expected_cases[source_name]
        hit_count = source_hit_at_5.get(source_name, 0)
        top1_count = source_top1_wins.get(source_name, 0)
        source_hit_rows.append(
            {
                "source_name": source_name,
                "expected_cases": expected_count,
                "hit_at_5_cases": hit_count,
                "hit_rate": format_ratio(round(hit_count / expected_count, 4) if expected_count else 0.0),
                "top1_wins": top1_count,
            }
        )
    source_hit_rows.sort(key=lambda row: row["hit_at_5_cases"], reverse=True)

    generated_at = datetime.now().isoformat(timespec="seconds")
    report_markdown = build_report_markdown(
        generated_at=generated_at,
        team_id=args.team_id,
        conversation_id=args.conversation_id,
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        top_ks=top_ks,
        dense_overall=dense_overall,
        baseline_overall=baseline_overall,
        dense_by_scenario=dense_by_scenario,
        baseline_by_scenario=baseline_by_scenario,
        source_hit_rows=source_hit_rows,
        failures_top10=failures_top10,
        failure_at_k=max_k,
    )

    summary_payload = {
        "generated_at": generated_at,
        "team_id": args.team_id,
        "conversation_id": args.conversation_id,
        "dataset": dataset_path.as_posix(),
        "manifest": manifest_path.as_posix(),
        "top_ks": top_ks,
        "dense_overall": dense_overall,
        "baseline_overall": baseline_overall,
        "dense_by_scenario": dense_by_scenario,
        "baseline_by_scenario": baseline_by_scenario,
        "source_hit_rows": source_hit_rows,
        "failures_top10": failures_top10,
        "errors": errors,
        "manifest_meta": {
            "indexed_chunks": manifest_payload.get("indexed_chunks"),
            "documents_count": len(manifest_payload.get("documents", []))
            if isinstance(manifest_payload.get("documents"), list)
            else None,
        },
    }

    summary_path = output_dir / f"{args.output_prefix}_summary.json"
    trace_path = output_dir / f"{args.output_prefix}_traces.json"
    report_path = output_dir / f"{args.output_prefix}_report.md"

    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    trace_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path.write_text(report_markdown, encoding="utf-8")

    print("RAG simulation evaluation complete.")
    print(f"cases={len(records)}")
    print(f"dense_recall@1={dense_overall['recall_any'].get('1')}")
    print(f"dense_recall@3={dense_overall['recall_any'].get('3')}")
    print(f"dense_recall@5={dense_overall['recall_any'].get('5')}")
    if baseline_overall:
        print(f"baseline_recall@1={baseline_overall['recall_any'].get('1')}")
        print(f"baseline_recall@3={baseline_overall['recall_any'].get('3')}")
        print(f"baseline_recall@5={baseline_overall['recall_any'].get('5')}")
    print(f"summary={summary_path.as_posix()}")
    print(f"traces={trace_path.as_posix()}")
    print(f"report={report_path.as_posix()}")


if __name__ == "__main__":
    main()
