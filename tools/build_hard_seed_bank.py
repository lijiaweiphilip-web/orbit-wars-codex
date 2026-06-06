from __future__ import annotations

import argparse
import csv
import json
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
            parsed["step100"] = json.loads(row["step100"])
            parsed["mission_usage"] = json.loads(row["mission_usage"])
            rows.append(parsed)
    return rows


def _leader_margin(row: dict) -> tuple[float, float]:
    scores = {int(k): float(v) for k, v in row["step100"].get("scores", {}).items()}
    production = {int(k): float(v) for k, v in row["step100"].get("production", {}).items()}
    if not scores:
        return 0.0, 0.0
    leader = max(scores, key=scores.get)
    return scores.get(leader, 0.0) - scores.get(0, 0.0), production.get(leader, 0.0) - production.get(0, 0.0)


def _seed_payload(row: dict, reason: str) -> dict[str, object]:
    return {
        "seed": int(row["seed"]),
        "mode": row["mode"],
        "variant": row["variant"],
        "score_delta": row["score_delta"],
        "challenger_rank": row["challenger_rank"],
        "reason": reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a hard seed bank from existing Orbit Wars validation artifacts.")
    parser.add_argument("--v2-results", default="experiments/nn_ranker_v1/phase4_full_validation/results.csv")
    parser.add_argument("--v3-results", default="experiments/nn_ranker_v1/phase4_rollout_repair/validation_v3/results.csv")
    parser.add_argument("--output-json", default="experiments/nn_ranker_v1/phase5_sidecar/hard_seed_bank.json")
    parser.add_argument("--output-report", default="experiments/nn_ranker_v1/phase5_sidecar/hard_seed_bank_report.md")
    args = parser.parse_args()

    rows = _load_rows(REPO_ROOT / args.v2_results, "v2") + _load_rows(REPO_ROOT / args.v3_results, "v3")
    rows_sorted = sorted(rows, key=lambda row: row["score_delta"])
    four_p_rows = [row for row in rows_sorted if row["mode"] == "4p"]
    two_p_rows = [row for row in rows_sorted if row["mode"] == "2p"]

    bank = {
        "4p_catastrophic_loss_seeds": [_seed_payload(row, "worst_4p_delta") for row in four_p_rows[:8]],
        "2p_reversal_seeds": [_seed_payload(row, "negative_2p_reversal") for row in two_p_rows if row["score_delta"] < 0][:8],
        "leader_snowball_seeds": [],
        "symmetric_deadlock_seeds": [],
        "high_comet_interference_seeds": [],
        "sun_geometry_dangerous_seeds": [],
        "weak_harvest_backfire_seeds": [],
        "snipe_overfit_seeds": [],
    }

    for row in four_p_rows:
        score_margin, prod_margin = _leader_margin(row)
        usage = row["mission_usage"]
        if len(bank["leader_snowball_seeds"]) < 8 and (score_margin >= 250 or prod_margin >= 8):
            bank["leader_snowball_seeds"].append(_seed_payload(row, "leader_margin_step100"))
        if len(bank["symmetric_deadlock_seeds"]) < 8:
            scores = {int(k): float(v) for k, v in row["step100"].get("scores", {}).items()}
            if scores and max(scores.values()) - min(scores.values()) <= 150:
                bank["symmetric_deadlock_seeds"].append(_seed_payload(row, "tight_step100_score_band"))
        if len(bank["weak_harvest_backfire_seeds"]) < 8 and usage.get("weak_harvest", 0) >= 10 and row["score_delta"] < 0:
            bank["weak_harvest_backfire_seeds"].append(_seed_payload(row, "high_weak_harvest_negative_delta"))
        if len(bank["snipe_overfit_seeds"]) < 8 and usage.get("snipe", 0) >= 30 and row["score_delta"] < 0:
            bank["snipe_overfit_seeds"].append(_seed_payload(row, "high_snipe_negative_delta"))

    output_json = REPO_ROOT / args.output_json
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(bank, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Phase 5 Sidecar Hard Seed Bank Report",
        "",
        f"- source_rows: `{len(rows)}`",
        f"- generated_categories: `{len(bank)}`",
        "",
        "| category | count | note |",
        "|---|---:|---|",
    ]
    notes = {
        "4p_catastrophic_loss_seeds": "Worst 4p deltas from existing v2/v3 validation.",
        "2p_reversal_seeds": "2p seeds where challenger lost despite being the candidate branch.",
        "leader_snowball_seeds": "Step-100 leader margin already large.",
        "symmetric_deadlock_seeds": "Step-100 score band stayed unusually tight.",
        "high_comet_interference_seeds": "Not inferable from current artifacts; placeholder category kept empty.",
        "sun_geometry_dangerous_seeds": "Not inferable from current CSV-only artifacts; placeholder category kept empty.",
        "weak_harvest_backfire_seeds": "Negative delta with high weak_harvest usage.",
        "snipe_overfit_seeds": "Negative delta with high snipe usage.",
    }
    for category, seeds in bank.items():
        lines.append(f"| {category} | {len(seeds)} | {notes[category]} |")
    lines.extend(
        [
            "",
            "## Validation Use",
            "",
            "- Future v4 validation should always include these seeds in addition to the broad 200-game and 100-game banks.",
            "- Empty categories are preserved intentionally so later telemetry can fill them without changing downstream tooling.",
        ]
    )
    output_report = REPO_ROOT / args.output_report
    output_report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output_json": str(output_json), "categories": len(bank)}, sort_keys=True))


if __name__ == "__main__":
    main()
