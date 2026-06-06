from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            parsed = dict(row)
            parsed["score_delta"] = float(row["score_delta"])
            parsed["challenger_rank"] = int(row["challenger_rank"])
            parsed["baseline_rank"] = int(row["baseline_rank"])
            rows.append(parsed)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate GitHub Actions sidecar validation shards.")
    parser.add_argument("--input-dir", default="experiments/nn_ranker_v1/phase5_sidecar/github_actions_validation")
    parser.add_argument("--output-dir", default="experiments/nn_ranker_v1/phase5_sidecar/github_actions_validation")
    parser.add_argument("--expected-shards", type=int, default=4)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.glob("shard_*.csv"))
    json_files = sorted(input_dir.glob("shard_*.json"))
    rows: list[dict] = []
    for csv_file in csv_files:
        rows.extend(_load_rows(csv_file))

    missing = sorted(set(range(args.expected_shards)) - {int(path.stem.split("_")[1]) for path in csv_files})
    failures = [row for row in rows if row["score_delta"] < 0]
    worst = sorted(rows, key=lambda row: row["score_delta"])[:10]
    with (output_dir / "failure_cases.jsonl").open("w", encoding="utf-8") as fh:
        for row in failures:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    two_p = [row for row in rows if row["mode"] == "2p"]
    four_p = [row for row in rows if row["mode"] == "4p"]
    delta_mean = sum(row["score_delta"] for row in rows) / max(1, len(rows))
    four_p_avg_rank = sum(row["challenger_rank"] for row in four_p) / max(1, len(four_p))
    lines = [
        "# GitHub Actions Sidecar Aggregate Validation Report",
        "",
        f"- shard_csv_count: `{len(csv_files)}`",
        f"- shard_json_count: `{len(json_files)}`",
        f"- expected_shards: `{args.expected_shards}`",
        f"- missing_shards: `{missing}`",
        f"- total_rows: `{len(rows)}`",
        f"- final_score_delta_mean: `{delta_mean:.3f}`",
        f"- four_p_avg_rank: `{four_p_avg_rank:.3f}`",
        "",
        "## Worst 10 Losses",
        "",
        "| mode | seed | delta | rank |",
        "|---|---:|---:|---:|",
    ]
    for row in worst:
        lines.append(f"| {row['mode']} | {row['seed']} | {row['score_delta']} | {row['challenger_rank']} |")
    (output_dir / "aggregate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "missing_shards": missing}, sort_keys=True))


if __name__ == "__main__":
    main()
