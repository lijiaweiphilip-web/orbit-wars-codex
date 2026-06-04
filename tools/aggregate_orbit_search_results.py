from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_rows(shard_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(shard_dir.glob("results_*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _metric(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    return float(row.get("metrics", {}).get(key, default))


def _summarize(rows: list[dict[str, Any]], top_rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "# Orbit Wars Search Summary\n\nNo shard result rows were found.\n"

    fitness_values = [_metric(row, "fitness") for row in rows]
    error_rows = [row for row in rows if _metric(row, "error_rate") > 0]
    best = top_rows[0]
    lines = [
        "# Orbit Wars Search Summary",
        "",
        f"- Evaluated configs: {len(rows)}",
        f"- Error configs: {len(error_rows)}",
        f"- Best config: {best['config_id']}",
        f"- Best fitness: {_metric(best, 'fitness'):.4f}",
        f"- Median fitness: {statistics.median(fitness_values):.4f}",
        "",
        "## Top 20",
        "",
        "| rank | config_id | fitness | avg_rank | win_rate | avg_delta | worst_loss | p100 | ships100 | source |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, row in enumerate(top_rows[:20], start=1):
        metrics = row["metrics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    str(row["config_id"]),
                    f"{float(metrics.get('fitness', 0.0)):.4f}",
                    f"{float(metrics.get('avg_rank', 0.0)):.4f}",
                    f"{float(metrics.get('win_rate', 0.0)):.4f}",
                    f"{float(metrics.get('avg_delta', 0.0)):.4f}",
                    str(metrics.get("worst_loss", "")),
                    f"{float(metrics.get('step100_planets', 0.0)):.4f}",
                    f"{float(metrics.get('step100_ships', 0.0)):.4f}",
                    str(row.get("source", "")),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Next Decision")
    lines.append("")
    lines.append(
        "Promote the top configs to a larger-seed validation wave before using Kaggle submissions."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate Orbit Wars search shards.")
    parser.add_argument("--input-dir", default="experiments/search_wave1/shards")
    parser.add_argument("--output-dir", default="experiments/search_wave1")
    parser.add_argument("--top-k", type=int, default=100)
    args = parser.parse_args()

    shard_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = _load_rows(shard_dir)
    rows.sort(key=lambda row: _metric(row, "fitness", -1_000_000.0), reverse=True)
    top_rows = rows[: args.top_k]

    (output_dir / "top_configs.json").write_text(
        json.dumps(top_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "best_params.json").write_text(
        json.dumps(top_rows[0]["params"], indent=2, sort_keys=True) if top_rows else "{}\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(_summarize(rows, top_rows), encoding="utf-8")
    print(json.dumps({"evaluated": len(rows), "top_k": len(top_rows), "output_dir": str(output_dir)}))


if __name__ == "__main__":
    main()
