from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_VARIANTS = {
    "baseline": None,
    "candidate_only": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_ablation" / "candidate_only",
    "neural_top8": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_full_validation",
    "neural_top16": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_ablation" / "top16",
    "neural_no_safety": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_ablation" / "no_penalty",
    "neural_with_safety": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_full_validation",
    "proxy_only": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_full_validation",
    "rollout_assisted": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_rollout_repair" / "validation_v3",
    "tail_aware": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_rollout_repair" / "validation_v3",
}


def _parse_report(path: Path) -> dict[str, str]:
    if not path.exists():
        return {"missing": "true"}
    out: dict[str, str] = {"missing": "false"}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            out[key.strip()] = value.strip()
    return out


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                {
                    **row,
                    "score_delta": float(row["score_delta"]),
                    "challenger_rank": int(row["challenger_rank"]),
                    "mission_usage": json.loads(row["mission_usage"]),
                }
            )
    return rows


def _mission_summary(rows: list[dict]) -> str:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(row["mission_usage"])
    return ", ".join(f"{name}={count}" for name, count in counter.most_common(5))


def _run_validation(label: str, package_path: Path, output_dir: Path, games: int, seed: int, modes: str) -> None:
    baseline = REPO_ROOT / "experiments" / "nn_ranker_v1" / "frozen_baseline" / "submission_10_swarm_surplus_arrival_v1.zip"
    command = [
        sys.executable,
        "tools/validate_orbit_packages.py",
        "--baseline",
        str(baseline),
        "--challenger",
        str(package_path),
        "--games",
        str(games),
        "--episode-steps",
        "500",
        "--modes",
        modes,
        "--seed",
        str(seed),
        "--output-dir",
        str(output_dir / label),
    ]
    subprocess.run(command, cwd=REPO_ROOT, text=True, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reusable ablation harness for Orbit Wars neural scorer experiments.")
    parser.add_argument("--games", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260606)
    parser.add_argument("--modes", default="2p,4p")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", default="experiments/nn_ranker_v1/phase5_sidecar/ablation_harness_report.md")
    parser.add_argument("--work-dir", default="experiments/nn_ranker_v1/phase5_sidecar/ablation_runs")
    args = parser.parse_args()

    work_dir = REPO_ROOT / args.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)
    rows_for_report = []
    for label, source_dir in DEFAULT_VARIANTS.items():
        if label == "baseline":
            rows_for_report.append({"label": label, "report": {"note": "control only"}, "rows": []})
            continue
        if args.run:
            package_map = {
                "candidate_only": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_ablation" / "candidate_only" / "submission_candidate_only.zip",
                "neural_top8": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_neural_branch" / "submission_neural_ranker_v2.zip",
                "neural_top16": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_ablation" / "top16" / "submission_top16.zip",
                "neural_no_safety": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_ablation" / "no_penalty" / "submission_no_penalty.zip",
                "neural_with_safety": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_neural_branch" / "submission_neural_ranker_v2.zip",
                "proxy_only": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_neural_branch" / "submission_neural_ranker_v2.zip",
                "rollout_assisted": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_rollout_repair" / "submission_neural_ranker_v3.zip",
                "tail_aware": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_rollout_repair" / "submission_neural_ranker_v3.zip",
            }
            _run_validation(label, package_map[label], work_dir, args.games, args.seed, args.modes)
            source_dir = work_dir / label
        assert source_dir is not None
        report = _parse_report(source_dir / "package_vs_package_report.md")
        result_rows = _read_rows(source_dir / "results.csv")
        rows_for_report.append({"label": label, "report": report, "rows": result_rows})

    lines = [
        "# Phase 5 Sidecar Ablation Harness Report",
        "",
        f"- run_mode: `{'fresh_validation' if args.run else 'reuse_existing_reports'}`",
        f"- reusable_cli: `python tools/run_neural_ablation_suite.py --games {args.games} --seed {args.seed} --modes {args.modes}`",
        "",
        "| variant | 2p_win_rate | 4p_avg_rank | 4p_top2_rate | final_score_delta_mean | runtime_note |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows_for_report:
        report = row["report"]
        if row["label"] == "baseline":
            lines.append("| baseline | n/a | n/a | n/a | n/a | control only |")
            continue
        if report.get("missing") == "true":
            lines.append(f"| {row['label']} | n/a | n/a | n/a | n/a | missing report |")
            continue
        runtime_note = "report-backed"
        if row["label"] in ("neural_top8", "neural_with_safety", "proxy_only"):
            runtime_note = "paired with phase4 runtime profile"
        lines.append(
            f"| {row['label']} | {report.get('2p_win_rate', 'n/a')} | {report.get('4p_avg_rank', 'n/a')} | {report.get('4p_top2_rate', 'n/a')} | {report.get('final_score_delta_mean', 'n/a')} | {runtime_note} |"
        )
    lines.extend(["", "## Worst 10 Loss Snapshots", ""])
    for row in rows_for_report:
        if not row["rows"]:
            continue
        worst = sorted(row["rows"], key=lambda item: item["score_delta"])[:3]
        lines.append(f"### {row['label']}")
        for item in worst:
            lines.append(
                f"- seed `{item['seed']}` mode `{item['mode']}` delta `{item['score_delta']}` rank `{item['challenger_rank']}`"
            )
        lines.append(f"- mission_usage_top5: `{_mission_summary(row['rows'])}`")
        lines.append("")
    lines.extend(
        [
            "## Harness Notes",
            "",
            "- `candidate_only` vs `neural_with_safety` remains the key test for neural scorer contribution.",
            "- `neural_no_safety` isolates the value of the conservative safety layer.",
            "- `neural_top8` vs `neural_top16` stays relevant for runtime versus safer-action coverage.",
        ]
    )
    output = REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "run_mode": "fresh" if args.run else "reuse"}, sort_keys=True))


if __name__ == "__main__":
    main()
