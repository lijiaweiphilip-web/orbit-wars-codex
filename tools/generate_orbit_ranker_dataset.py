from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orbitwars.env_loader import make_env
from orbitwars.eval_runner import _random_agent
from orbitwars.geometry import distance, estimate_eta
from orbitwars.heuristics import HeuristicParams, default_v0_params, default_v1_params, make_agent, nearby_enemy_pressure
from orbitwars.obs_parser import GameState, PlanetState, parse_observation


FEATURE_NAMES = [
    "step_norm",
    "num_players",
    "own_planets",
    "enemy_planets",
    "neutral_planets",
    "own_ships",
    "enemy_ships",
    "source_ships",
    "source_production",
    "source_pressure",
    "target_owner_kind",
    "target_ships",
    "target_production",
    "target_pressure",
    "distance",
    "eta",
    "required_ships",
    "available_after_send",
    "prod_per_eta",
    "ship_margin",
]


def _variant_agent(**overrides):
    params = default_v1_params()
    for key, value in overrides.items():
        setattr(params, key, value)
    return make_agent(params)


def _opponent_pool():
    return [
        _random_agent,
        make_agent(default_v0_params()),
        _variant_agent(reserve_base=5, aggression_2p=1.65, four_player_midgame_reserve_bonus=2),
        _variant_agent(reserve_base=9, aggression_2p=1.2, four_player_midgame_reserve_bonus=8),
    ]


def _required(target: PlanetState, eta: float, owner_kind: int) -> float:
    growth = target.production * max(0.0, eta) if owner_kind >= 0 else 0.0
    weight = 0.55 if owner_kind < 0 else 0.85
    return target.ships * weight + growth + 3.0


def _totals(state: GameState) -> tuple[float, float]:
    own = sum(p.ships for p in state.my_planets) + sum(f.ships for f in state.fleets if f.owner == state.my_id)
    enemy = sum(p.ships for p in state.enemy_planets) + sum(f.ships for f in state.fleets if f.owner != state.my_id)
    return float(own), float(enemy)


def _candidate_rows(state: GameState, rng: random.Random, max_targets: int) -> list[tuple[list[float], float, int]]:
    if not state.my_planets:
        return []
    own_ships, enemy_ships = _totals(state)
    targets = [p for p in state.planets if p.owner != state.my_id and not p.is_comet]
    rng.shuffle(targets)
    targets = targets[:max_targets]
    rows: list[tuple[list[float], float, int]] = []
    for source in sorted(state.my_planets, key=lambda p: p.ships, reverse=True)[:3]:
        source_pressure = nearby_enemy_pressure(state, source)
        available = max(0.0, source.ships - 8.0 - source.production * 0.7 - source_pressure)
        for target in targets:
            gap = distance(source.x, source.y, target.x, target.y)
            eta = estimate_eta(gap, max(available, 1.0), 6.0)
            if eta > 36:
                continue
            owner_kind = -1 if target.owner == -1 else 1
            required = _required(target, eta, owner_kind)
            target_pressure = nearby_enemy_pressure(state, target)
            margin = available - required
            prod_per_eta = target.production / max(1.0, eta)
            score = (
                18.0 * target.production
                + 9.0 * prod_per_eta
                + (10.0 if owner_kind < 0 else 18.0)
                + 0.55 * margin
                - 0.7 * eta
                - 2.0 * target_pressure
            )
            mission = 0 if owner_kind < 0 else 1
            features = [
                state.step / max(1.0, state.episode_steps),
                float(state.num_players),
                float(len(state.my_planets)),
                float(len(state.enemy_planets)),
                float(len(state.neutral_planets)),
                own_ships,
                enemy_ships,
                float(source.ships),
                float(source.production),
                float(source_pressure),
                float(owner_kind),
                float(target.ships),
                float(target.production),
                float(target_pressure),
                float(gap),
                float(eta),
                float(required),
                float(margin),
                float(prod_per_eta),
                float(margin / max(1.0, required)),
            ]
            rows.append((features, float(score), mission))
    return rows


def _load_parent_params(path: Path, limit: int) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [row.get("params", row) for row in rows[:limit]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Orbit Wars candidate-action ranker examples.")
    parser.add_argument("--parents", default="configs/orbit_hard_parents_20260605.json")
    parser.add_argument("--output", default="experiments/ranker_dataset/orbit_ranker_examples.npz")
    parser.add_argument("--count", type=int, default=1_000_000)
    parser.add_argument("--seed-start", type=int, default=1001)
    parser.add_argument("--sample-every", type=int, default=5)
    parser.add_argument("--max-targets", type=int, default=8)
    parser.add_argument("--parent-limit", type=int, default=30)
    args = parser.parse_args()

    rng = random.Random(args.seed_start)
    params_pool = _load_parent_params(Path(args.parents), args.parent_limit)
    opponents = _opponent_pool()
    xs: list[list[float]] = []
    ys: list[float] = []
    missions: list[int] = []
    seed = args.seed_start
    while len(xs) < args.count:
        params = HeuristicParams.from_mapping(rng.choice(params_pool))
        agents = [make_agent(params), opponents[seed % len(opponents)], opponents[(seed + 1) % len(opponents)], opponents[(seed + 2) % len(opponents)]]
        env = make_env(num_agents=4, seed=seed, episode_steps=120)
        env.run(agents)
        for index in range(0, len(env.steps), args.sample_every):
            obs = env.steps[index][0]["observation"]
            state = parse_observation(obs, {"episodeSteps": 120})
            for features, score, mission in _candidate_rows(state, rng, args.max_targets):
                xs.append(features)
                ys.append(score)
                missions.append(mission)
                if len(xs) >= args.count:
                    break
            if len(xs) >= args.count:
                break
        seed += 1
        if seed % 25 == 0:
            print(json.dumps({"examples": len(xs), "last_seed": seed}))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(xs, dtype=np.float32)
    y = np.asarray(ys, dtype=np.float32)
    mission_arr = np.asarray(missions, dtype=np.int64)
    np.savez_compressed(output, x=x, y=y, mission=mission_arr, feature_names=np.asarray(FEATURE_NAMES))
    print(json.dumps({"output": str(output), "examples": int(x.shape[0]), "features": int(x.shape[1])}))


if __name__ == "__main__":
    main()
