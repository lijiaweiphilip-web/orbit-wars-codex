from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orbitwars.heuristics import default_v1_params


SEARCH_SPACE: dict[str, list[int | float]] = {
    "reserve_base": [5, 6, 7, 8, 9],
    "four_player_midgame_reserve_bonus": [2, 4, 5, 6, 8],
    "aggression_2p": [1.2, 1.35, 1.5, 1.65],
    "early_max_eta": [16, 18, 20],
    "opening_4p_expand_steps": [40, 48, 55, 62],
    "opening_4p_neutral_max_eta": [10, 12, 13, 15],
    "opening_4p_min_home_ships_left": [8, 10, 12, 14],
    "recovery_4p_neutral_max_eta": [14, 16, 18],
    "four_player_conversion_late_score_floor": [-90.0, -105.0, -115.0, -125.0, -140.0],
    "four_player_conversion_late_pressure_cap": [8.0, 10.0, 12.0, 14.0],
    "four_player_conversion_late_source_margin": [1.35, 1.45, 1.6],
    "four_player_conversion_late_ship_ratio": [0.45, 0.5, 0.55, 0.62],
}


ANCHORS: list[dict[str, int | float]] = [
    {
        "reserve_base": 8,
        "four_player_midgame_reserve_bonus": 6,
    },
    {
        "reserve_base": 8,
        "four_player_midgame_reserve_bonus": 6,
        "aggression_2p": 1.35,
        "early_max_eta": 18,
    },
]


def sample_config(rng: random.Random, config_id: int) -> dict[str, object]:
    params = asdict(default_v1_params())
    for key, values in SEARCH_SPACE.items():
        params[key] = rng.choice(values)
    # Keep the search near the branch that scored best today.
    if rng.random() < 0.35:
        params["reserve_base"] = rng.choice([7, 8])
        params["four_player_midgame_reserve_bonus"] = rng.choice([4, 5, 6])
    return {
        "config_id": f"cfg_{config_id:05d}",
        "params": params,
        "source": "random_near_reserve_light",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Orbit Wars parameter-search manifest.")
    parser.add_argument("--output", default="experiments/search_wave1/manifest.jsonl")
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260605)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    base = asdict(default_v1_params())
    with output.open("w", encoding="utf-8") as fh:
        for idx, overrides in enumerate(ANCHORS):
            params = {**base, **overrides}
            fh.write(json.dumps({"config_id": f"anchor_{idx+1:02d}", "params": params, "source": "anchor"}) + "\n")
        for idx in range(args.count):
            fh.write(json.dumps(sample_config(rng, idx), sort_keys=True) + "\n")
    print(output.as_posix())


if __name__ == "__main__":
    main()
