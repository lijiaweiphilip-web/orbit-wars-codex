from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orbitwars.heuristics import default_v1_params
from tools.generate_orbit_search_manifest import SEARCH_SPACE, sample_config


def _load_parents(path: Path, top_n: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return []
    return [row["params"] for row in rows[:top_n] if "params" in row]


def _mutate_value(rng: random.Random, key: str, value: Any) -> Any:
    values = SEARCH_SPACE.get(key)
    if not values:
        return value
    if rng.random() < 0.55 and value in values:
        idx = values.index(value)
        lo = max(0, idx - 1)
        hi = min(len(values) - 1, idx + 1)
        return values[rng.randint(lo, hi)]
    return rng.choice(values)


def _mutate_parent(rng: random.Random, parent: dict[str, Any], config_id: int) -> dict[str, Any]:
    params = dict(parent)
    changed = 0
    for key in SEARCH_SPACE:
        if rng.random() < 0.35:
            params[key] = _mutate_value(rng, key, params.get(key))
            changed += 1
    if changed == 0:
        key = rng.choice(list(SEARCH_SPACE))
        params[key] = _mutate_value(rng, key, params.get(key))
    return {
        "config_id": f"follow_{config_id:05d}",
        "params": params,
        "source": "top_config_perturbation",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a follow-up Orbit Wars manifest around top configs.")
    parser.add_argument("--parents", default="experiments/search_wave1/top_configs.json")
    parser.add_argument("--output", default="experiments/search_wave2/manifest.jsonl")
    parser.add_argument("--count", type=int, default=30_000)
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260606)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    parents = _load_parents(Path(args.parents), args.top_n)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    base = asdict(default_v1_params())
    with output.open("w", encoding="utf-8") as fh:
        for idx, parent in enumerate(parents[: min(25, len(parents))]):
            fh.write(
                json.dumps(
                    {"config_id": f"parent_{idx+1:03d}", "params": parent, "source": "wave1_parent"},
                    sort_keys=True,
                )
                + "\n"
            )
        for idx in range(args.count):
            if parents and rng.random() < 0.8:
                parent = rng.choice(parents[: min(args.top_n, len(parents))])
                row = _mutate_parent(rng, parent, idx)
            else:
                row = sample_config(rng, idx)
                row["config_id"] = f"fresh_{idx:05d}"
                row["source"] = "fresh_random_near_reserve_light"
            # Keep a small safety anchor in every long wave.
            if idx == 0:
                row = {"config_id": "anchor_current_default", "params": base, "source": "anchor"}
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(output.as_posix())


if __name__ == "__main__":
    main()
