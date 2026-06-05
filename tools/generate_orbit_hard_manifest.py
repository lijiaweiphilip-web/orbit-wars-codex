from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.generate_orbit_followup_manifest import _mutate_parent
from tools.generate_orbit_search_manifest import sample_config


def _load_parents(path: Path, top_n: int) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    parents: list[dict[str, Any]] = []
    for row in rows[:top_n]:
        params = row.get("params", row)
        if isinstance(params, dict):
            parents.append(params)
    return parents


def _bucket_override(bucket: str) -> dict[str, int | float]:
    buckets: dict[str, dict[str, int | float]] = {
        "low_reserve_snowball": {
            "reserve_base": 5,
            "four_player_midgame_reserve_bonus": 2,
            "opening_4p_min_home_ships_left": 8,
            "opening_4p_neutral_max_eta": 10,
        },
        "launch_safety": {
            "reserve_base": 9,
            "four_player_midgame_reserve_bonus": 8,
            "opening_4p_min_home_ships_left": 14,
            "four_player_conversion_late_pressure_cap": 8.0,
        },
        "two_player_pressure": {
            "aggression_2p": 1.65,
            "early_max_eta": 20,
            "four_player_conversion_late_score_floor": -90.0,
        },
        "weak_harvest": {
            "recovery_4p_neutral_max_eta": 18,
            "four_player_conversion_late_source_margin": 1.35,
            "four_player_conversion_late_ship_ratio": 0.55,
        },
        "late_flush": {
            "four_player_conversion_late_score_floor": -90.0,
            "four_player_conversion_late_pressure_cap": 8.0,
            "four_player_conversion_late_source_margin": 1.45,
        },
    }
    return buckets[bucket]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate hard Orbit Wars validation/search manifest.")
    parser.add_argument("--parents", default="configs/orbit_hard_parents_20260605.json")
    parser.add_argument("--output", default="experiments/github_hard/manifest.jsonl")
    parser.add_argument("--count", type=int, default=30_000)
    parser.add_argument("--top-n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260605)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    parents = _load_parents(Path(args.parents), args.top_n)
    if not parents:
        raise SystemExit(f"No parent configs found in {args.parents}")

    buckets = ["low_reserve_snowball", "launch_safety", "two_player_pressure", "weak_harvest", "late_flush"]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        for idx, parent in enumerate(parents[: min(len(parents), 50)]):
            fh.write(json.dumps({"config_id": f"parent_{idx:03d}", "params": parent, "source": "hard_parent"}) + "\n")
        for idx in range(args.count):
            if rng.random() < 0.85:
                parent = rng.choice(parents)
                row = _mutate_parent(rng, parent, idx)
                bucket = rng.choice(buckets)
                row["params"].update(_bucket_override(bucket))
                row["config_id"] = f"hard_{idx:06d}"
                row["source"] = f"parent_perturb_{bucket}"
            else:
                row = sample_config(rng, idx)
                row["config_id"] = f"fresh_hard_{idx:06d}"
                row["source"] = "fresh_hard_random"
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(output.as_posix())


if __name__ == "__main__":
    main()
