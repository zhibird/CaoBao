from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two RAG eval summary files and render uplift report.")
    parser.add_argument("--before", required=True, help="Path to baseline summary JSON.")
    parser.add_argument("--after", required=True, help="Path to optimized summary JSON.")
    parser.add_argument("--out-md", default="docs/rag_simulation/run/compare_report.md", help="Output markdown path.")
    parser.add_argument("--out-json", default="docs/rag_simulation/run/compare_summary.json", help="Output JSON path.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Invalid JSON object: {path}")
    return payload


def get_metric(summary: dict[str, Any], block: str, sub_block: str, key: str) -> float | None:
    root = summary.get(block, {})
    if not isinstance(root, dict):
        return None
    node = root.get(sub_block, {})
    if not isinstance(node, dict):
        return None
    value = node.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def metric_bar(value: float | None, width: int = 20) -> str:
    if value is None:
        return "-" * width
    clipped = max(0.0, min(1.0, value))
    filled = int(round(clipped * width))
    return "█" * filled + "░" * (width - filled)


def fmt(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"


def delta(new_value: float | None, old_value: float | None) -> float | None:
    if new_value is None or old_value is None:
        return None
    return round(new_value - old_value, 4)


def fmt_delta(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.4f}"


def build_report(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], str]:
    ks = ["1", "3", "5"]
    overall_rows: list[dict[str, Any]] = []
    for k in ks:
        before_any = get_metric(before, "dense_overall", "recall_any", k)
        after_any = get_metric(after, "dense_overall", "recall_any", k)
        before_multi = get_metric(before, "dense_overall", "recall_all_sources", k)
        after_multi = get_metric(after, "dense_overall", "recall_all_sources", k)
        overall_rows.append(
            {
                "metric": f"Recall@{k} (any)",
                "before": before_any,
                "after": after_any,
                "delta": delta(after_any, before_any),
            }
        )
        overall_rows.append(
            {
                "metric": f"Multi-source Recall@{k} (all)",
                "before": before_multi,
                "after": after_multi,
                "delta": delta(after_multi, before_multi),
            }
        )

    before_scenarios = before.get("dense_by_scenario", {})
    after_scenarios = after.get("dense_by_scenario", {})
    scenario_names = sorted(set(before_scenarios.keys()) | set(after_scenarios.keys()))
    scenario_rows: list[dict[str, Any]] = []
    for scenario in scenario_names:
        before_node = before_scenarios.get(scenario, {})
        after_node = after_scenarios.get(scenario, {})
        if not isinstance(before_node, dict) or not isinstance(after_node, dict):
            continue
        b1 = get_metric({"dense_overall": before_node}, "dense_overall", "recall_any", "1")
        a1 = get_metric({"dense_overall": after_node}, "dense_overall", "recall_any", "1")
        b3 = get_metric({"dense_overall": before_node}, "dense_overall", "recall_any", "3")
        a3 = get_metric({"dense_overall": after_node}, "dense_overall", "recall_any", "3")
        b5 = get_metric({"dense_overall": before_node}, "dense_overall", "recall_any", "5")
        a5 = get_metric({"dense_overall": after_node}, "dense_overall", "recall_any", "5")
        scenario_rows.append(
            {
                "scenario": scenario,
                "before_r1": b1,
                "after_r1": a1,
                "delta_r1": delta(a1, b1),
                "before_r3": b3,
                "after_r3": a3,
                "delta_r3": delta(a3, b3),
                "before_r5": b5,
                "after_r5": a5,
                "delta_r5": delta(a5, b5),
            }
        )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "before_summary": before.get("generated_at"),
        "after_summary": after.get("generated_at"),
        "overall": overall_rows,
        "by_scenario": scenario_rows,
    }

    lines: list[str] = []
    lines.append("# RAG Improvement Comparison")
    lines.append("")
    lines.append(f"- Generated at: `{payload['generated_at']}`")
    lines.append(f"- Before run: `{payload['before_summary']}`")
    lines.append(f"- After run: `{payload['after_summary']}`")
    lines.append("")
    lines.append("## Overall Delta")
    lines.append("")
    lines.append("| Metric | Before | After | Delta |")
    lines.append("|---|---:|---:|---:|")
    for row in overall_rows:
        lines.append(
            f"| {row['metric']} | {fmt(row['before'])} | {fmt(row['after'])} | {fmt_delta(row['delta'])} |"
        )
    lines.append("")
    lines.append("## Visual Delta (Dense)")
    lines.append("")
    for row in overall_rows:
        if "any" not in row["metric"]:
            continue
        lines.append(f"- {row['metric']} before: `{metric_bar(row['before'])}` {fmt(row['before'])}")
        lines.append(f"- {row['metric']} after:  `{metric_bar(row['after'])}` {fmt(row['after'])}")
    lines.append("")
    lines.append("## Scenario Delta")
    lines.append("")
    lines.append("| Scenario | R@1 Δ | R@3 Δ | R@5 Δ |")
    lines.append("|---|---:|---:|---:|")
    for row in scenario_rows:
        lines.append(
            f"| {row['scenario']} | {fmt_delta(row['delta_r1'])} | {fmt_delta(row['delta_r3'])} | {fmt_delta(row['delta_r5'])} |"
        )

    return payload, "\n".join(lines)


def main() -> None:
    args = parse_args()
    before_path = Path(args.before)
    after_path = Path(args.after)
    out_md = Path(args.out_md)
    out_json = Path(args.out_json)

    before = load_json(before_path)
    after = load_json(after_path)
    payload, markdown = build_report(before, after)

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown, encoding="utf-8")
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Comparison report generated.")
    print(f"markdown={out_md.as_posix()}")
    print(f"json={out_json.as_posix()}")


if __name__ == "__main__":
    main()
