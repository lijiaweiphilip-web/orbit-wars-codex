from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_rows(path: Path, variant: str) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            parsed = dict(row)
            parsed["variant"] = variant
            parsed["score_delta"] = float(row["score_delta"])
            parsed["challenger_rank"] = int(row["challenger_rank"])
            parsed["baseline_rank"] = int(row["baseline_rank"])
            parsed["step100"] = json.loads(row["step100"])
            parsed["mission_usage"] = json.loads(row["mission_usage"])
            rows.append(parsed)
    return rows


def _step_leader(row: dict) -> tuple[int | None, float, float]:
    scores = {int(k): float(v) for k, v in row["step100"].get("scores", {}).items()}
    production = {int(k): float(v) for k, v in row["step100"].get("production", {}).items()}
    if not scores:
        return None, 0.0, 0.0
    leader = max(scores, key=scores.get)
    return leader, scores.get(leader, 0.0), production.get(leader, 0.0)


def _risk_flags(row: dict) -> dict[str, bool]:
    usage = Counter(row["mission_usage"])
    scores = {int(k): float(v) for k, v in row["step100"].get("scores", {}).items()}
    production = {int(k): float(v) for k, v in row["step100"].get("production", {}).items()}
    challenger_score = scores.get(0, 0.0)
    challenger_prod = production.get(0, 0.0)
    leader, leader_score, leader_prod = _step_leader(row)
    flags = {
        "leader_help_risk": row["mode"] == "4p" and leader not in (None, 0) and (leader_score - challenger_score >= 250 or leader_prod - challenger_prod >= 8),
        "third_party_steal_risk": row["mode"] == "4p" and usage.get("snipe", 0) >= 20 and row["challenger_rank"] >= 2,
        "snipe_spam": usage.get("snipe", 0) >= 30,
        "weak_harvest_helping_leader": row["mode"] == "4p" and usage.get("weak_harvest", 0) >= 10 and leader not in (None, 0),
        "reinforce_overuse": usage.get("reinforce", 0) >= 35,
        "home_source_overdrain": (usage.get("capture_enemy", 0) + usage.get("snipe", 0) >= 45) and challenger_score <= max(1.0, leader_score * 0.6),
        "early_collapse_before_step100": leader not in (None,) and challenger_score <= max(80.0, leader_score * 0.35),
        "late_wasted_travel": challenger_score >= max(200.0, leader_score * 0.7) and row["score_delta"] <= -4000,
    }
    return flags


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze existing Orbit Wars failure cases for Phase 5 sidecar.")
    parser.add_argument("--v2-results", default="experiments/nn_ranker_v1/phase4_full_validation/results.csv")
    parser.add_argument("--v3-results", default="experiments/nn_ranker_v1/phase4_rollout_repair/validation_v3/results.csv")
    parser.add_argument("--output-report", default="experiments/nn_ranker_v1/phase5_sidecar/failure_case_taxonomy.md")
    parser.add_argument("--output-json", default="experiments/nn_ranker_v1/phase5_sidecar/failure_case_clusters.json")
    args = parser.parse_args()

    rows = _load_rows(REPO_ROOT / args.v2_results, "v2") + _load_rows(REPO_ROOT / args.v3_results, "v3")
    failures = sorted([row for row in rows if row["score_delta"] < 0], key=lambda row: row["score_delta"])
    worst_4p = [row for row in failures if row["mode"] == "4p"][:16]
    cluster_counts: dict[str, int] = defaultdict(int)
    cluster_examples: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in worst_4p:
        flags = _risk_flags(row)
        for key, enabled in flags.items():
            if enabled:
                cluster_counts[key] += 1
                if len(cluster_examples[key]) < 4:
                    cluster_examples[key].append(
                        {
                            "variant": row["variant"],
                            "seed": int(row["seed"]),
                            "score_delta": row["score_delta"],
                            "challenger_rank": row["challenger_rank"],
                            "mission_usage": row["mission_usage"],
                        }
                    )

    clusters = {
        key: {
            "count": cluster_counts.get(key, 0),
            "examples": cluster_examples.get(key, []),
        }
        for key in [
            "leader_help_risk",
            "third_party_steal_risk",
            "snipe_spam",
            "weak_harvest_helping_leader",
            "reinforce_overuse",
            "home_source_overdrain",
            "early_collapse_before_step100",
            "late_wasted_travel",
        ]
    }
    output_json = REPO_ROOT / args.output_json
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(clusters, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Phase 5 Sidecar Failure Case Taxonomy",
        "",
        f"- source_rows: `{len(rows)}`",
        f"- negative_rows: `{len(failures)}`",
        f"- inspected_worst_4p_rows: `{len(worst_4p)}`",
        "",
        "## Main Risks",
        "",
        f"1. `leader_help_risk`: {cluster_counts.get('leader_help_risk', 0)} / {len(worst_4p)} of the worst 4p rows",
        f"2. `third_party_steal_risk`: {cluster_counts.get('third_party_steal_risk', 0)} / {len(worst_4p)}",
        f"3. `snipe_spam`: {cluster_counts.get('snipe_spam', 0)} / {len(worst_4p)}",
        f"4. `weak_harvest_helping_leader`: {cluster_counts.get('weak_harvest_helping_leader', 0)} / {len(worst_4p)}",
        f"5. `reinforce_overuse`: {cluster_counts.get('reinforce_overuse', 0)} / {len(worst_4p)}",
        f"6. `home_source_overdrain`: {cluster_counts.get('home_source_overdrain', 0)} / {len(worst_4p)}",
        f"7. `early_collapse_before_step100`: {cluster_counts.get('early_collapse_before_step100', 0)} / {len(worst_4p)}",
        f"8. `late_wasted_travel`: {cluster_counts.get('late_wasted_travel', 0)} / {len(worst_4p)}",
        "",
        "## Patch Suggestions",
        "",
        "- Increase `neural_safety` penalties for `leader_help_risk` and `third_party_steal_risk` before trusting a new rollout-aware scorer.",
        "- Add stronger candidate pruning for `weak_harvest` when the step-100 leader is not the challenger and leader production margin is already large.",
        "- Add or upweight a feature for `home/source overdrain`, especially when `capture_enemy + snipe` is high and home production is behind at step 100.",
        "- Run a targeted ablation on `top8` versus `top16` over the hard seed bank because current evidence is suggestive, not conclusive.",
        "- Add a v4 feature or penalty for `late_wasted_travel`, especially missions that launch while already behind and cannot arrive before the endgame closes.",
        "",
        "## Concrete Examples",
        "",
        "| risk | variant | seed | delta | rank | note |",
        "|---|---|---:|---:|---:|---|",
    ]
    for risk, payload in clusters.items():
        for example in payload["examples"][:2]:
            lines.append(
                f"| {risk} | {example['variant']} | {example['seed']} | {example['score_delta']} | {example['challenger_rank']} | `{json.dumps(example['mission_usage'], sort_keys=True)}` |"
            )
    lines.extend(
        [
            "",
            "## Top8 vs Top16",
            "",
            "- Existing Phase 4 ablation says `top16` improved `2p_win_rate` to `1.000`, but `4p_top2_rate` fell to `0.800` versus `0.840` for `neural_v2`.",
            "- That means `top8 vs top16 missed safer actions` is still an open question and should be re-run on the future hard seed bank rather than treated as settled.",
        ]
    )
    output_report = REPO_ROOT / args.output_report
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output_report": str(output_report), "negative_rows": len(failures)}, sort_keys=True))


if __name__ == "__main__":
    main()
