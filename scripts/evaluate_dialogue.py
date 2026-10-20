#!/usr/bin/env python3
"""Compute offline quality metrics for adaptive-dialogue transcripts."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _percentile(values: List[float], fraction: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def evaluate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid = []
    invalid = 0
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("turns"), int) or record["turns"] < 0:
            invalid += 1
            continue
        if not isinstance(record.get("completed"), bool):
            invalid += 1
            continue
        if not isinstance(record.get("actions", []), list):
            invalid += 1
            continue
        valid.append(record)

    total = len(valid)
    completed = sum(1 for record in valid if record["completed"])
    turns = [float(record["turns"]) for record in valid]
    latencies = [
        float(record["latency_ms"])
        for record in valid
        if isinstance(record.get("latency_ms"), (int, float))
    ]

    action_total = 0
    duplicate_total = 0
    for record in valid:
        seen = Counter()
        for action in record.get("actions", []):
            if not isinstance(action, dict):
                continue
            key = (str(action.get("type", "")), str(action.get("target", "")))
            seen[key] += 1
            action_total += 1
        duplicate_total += sum(max(0, count - 1) for count in seen.values())

    premature = sum(
        1 for record in valid
        if not record["completed"]
        and isinstance(record.get("max_turns"), int)
        and record["turns"] < record["max_turns"]
    )
    max_turn_records = sum(1 for record in valid if isinstance(record.get("max_turns"), int))

    return {
        "conversations": total,
        "invalid_records": invalid,
        "completed": completed,
        "completion_rate": round(completed / total, 4) if total else 0.0,
        "average_turns": round(statistics.fmean(turns), 2) if turns else 0.0,
        "p50_turns": _percentile(turns, 0.50),
        "p95_turns": _percentile(turns, 0.95),
        "redundant_action_rate": round(duplicate_total / action_total, 4) if action_total else 0.0,
        "premature_stop_rate": round(premature / max_turn_records, 4) if max_turn_records else 0.0,
        "average_latency_ms": round(statistics.fmean(latencies), 2) if latencies else None,
    }


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                value.setdefault("_line", line_number)
            records.append(value)
    return records


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Evaluation transcript JSONL")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args(argv)

    report = evaluate(load_jsonl(args.input))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
