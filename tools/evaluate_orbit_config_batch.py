from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orbitwars.env_loader import make_env
from orbitwars.heuristics import HeuristicParams, default_v0_params, default_v1_params, make_agent
from orbitwars.metrics import summarize_match
from orbitwars.eval_runner import _random_agent, load_agent


def _score_value(values: dict, key: int) -> int:
    return int(values.get(str(key), values.get(key, 0)))


def _variant_agent(**overrides):
    params = default_v1_params()
    for key, value in overrides.items():
        setattr(params, key, value)
    return make_agent(params)


def _eval_sets(agent0, opponent_pool: str):
    heuristic_v0 = load_agent("agents/heuristic_v0.py")
    if opponent_pool == "hard":
        low_reserve = _variant_agent(
            reserve_base=5,
            four_player_midgame_reserve_bonus=2,
            aggression_2p=1.65,
            opening_4p_min_home_ships_left=8,
            opening_4p_neutral_max_eta=10,
            recovery_4p_neutral_max_eta=18,
        )
        conservative = _variant_agent(
            reserve_base=9,
            four_player_midgame_reserve_bonus=8,
            aggression_2p=1.2,
            opening_4p_min_home_ships_left=14,
            four_player_conversion_late_pressure_cap=8.0,
        )
        pressure = _variant_agent(
            reserve_base=7,
            aggression_2p=1.8,
            early_max_eta=20,
            four_player_conversion_late_score_floor=-90.0,
            four_player_conversion_late_source_margin=1.35,
        )
        v0_agent = make_agent(default_v0_params())
        return [
            ("2p_random", [agent0, _random_agent]),
            ("2p_v0", [agent0, v0_agent]),
            ("2p_pressure", [agent0, pressure]),
            ("4p_mixed_a", [agent0, _random_agent, heuristic_v0, low_reserve]),
            ("4p_mixed_b", [agent0, conservative, pressure, v0_agent]),
        ]
    return [
        ("2p", [agent0, _random_agent]),
        ("4p", [agent0, _random_agent, _random_agent, heuristic_v0]),
    ]


def evaluate_config(params_payload: dict, seeds: list[int], opponent_pool: str = "standard") -> dict[str, float | int]:
    params = HeuristicParams.from_mapping(params_payload)
    agent0 = make_agent(params)
    eval_sets = _eval_sets(agent0, opponent_pool)
    ranks: list[int] = []
    wins: list[int] = []
    deltas: list[int] = []
    planets100: list[int] = []
    ships100: list[int] = []
    errors = 0
    for mode, agents in eval_sets:
        for seed in seeds:
            try:
                env = make_env(num_agents=len(agents), seed=seed, episode_steps=120)
                env.run(agents)
                summary = summarize_match(
                    [entry.status for entry in env.state],
                    env.state[0].observation,
                    len(agents),
                )
                rank0 = _score_value(summary["ranks"], 0)
                score0 = _score_value(summary["scores"], 0)
                best_other = max(_score_value(summary["scores"], player) for player in range(1, len(agents)))
                obs = env.steps[min(100, len(env.steps) - 1)][0]["observation"]
                p100 = sum(1 for planet in obs.get("planets", []) if int(planet[1]) == 0)
                s100 = sum(int(planet[5]) for planet in obs.get("planets", []) if int(planet[1]) == 0)
                s100 += sum(int(fleet[6]) for fleet in obs.get("fleets", []) if int(fleet[1]) == 0)
                ranks.append(rank0)
                wins.append(int(rank0 == 1))
                deltas.append(score0 - best_other)
                planets100.append(p100)
                ships100.append(s100)
            except Exception:
                errors += 1
    if not ranks:
        return {"fitness": -1_000_000.0, "error_rate": 1.0}
    error_rate = errors / max(1, errors + len(ranks))
    avg_rank = statistics.mean(ranks)
    win_rate = statistics.mean(wins)
    avg_delta = statistics.mean(deltas)
    worst_loss = min(deltas)
    step100_planets = statistics.mean(planets100)
    step100_ships = statistics.mean(ships100)
    fitness = (
        -250.0 * avg_rank
        + 0.35 * avg_delta
        + 35.0 * win_rate
        + 12.0 * step100_planets
        + 0.02 * step100_ships
        - 0.20 * abs(worst_loss)
        - 1000.0 * error_rate
    )
    return {
        "fitness": round(fitness, 4),
        "avg_rank": round(avg_rank, 4),
        "win_rate": round(win_rate, 4),
        "avg_delta": round(avg_delta, 4),
        "worst_loss": int(worst_loss),
        "step100_planets": round(step100_planets, 4),
        "step100_ships": round(step100_ships, 4),
        "error_rate": round(error_rate, 4),
    }


def iter_shard(manifest: Path, shard_index: int, shard_count: int):
    with manifest.open(encoding="utf-8") as fh:
        for row_index, line in enumerate(fh):
            if row_index % shard_count == shard_index:
                yield json.loads(line)


def _evaluate_entry(payload: tuple[dict, list[int], str]) -> dict:
    entry, seeds, opponent_pool = payload
    metrics = evaluate_config(entry["params"], seeds, opponent_pool=opponent_pool)
    return {**entry, "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one shard of Orbit Wars configs.")
    parser.add_argument("--manifest", default="experiments/search_wave1/manifest.jsonl")
    parser.add_argument("--output-dir", default="experiments/search_wave1")
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--seeds", default="1,2,3,4,5,6,7,8")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--opponent-pool", choices=["standard", "hard"], default="standard")
    args = parser.parse_args()

    seeds = [int(part) for part in args.seeds.split(",") if part.strip()]
    output_dir = Path(args.output_dir)
    shard_dir = output_dir / "shards"
    shard_dir.mkdir(parents=True, exist_ok=True)
    result_path = shard_dir / f"results_{args.shard_index:04d}.jsonl"
    top_path = shard_dir / f"top_{args.shard_index:04d}.json"
    entries = []
    for idx, entry in enumerate(iter_shard(Path(args.manifest), args.shard_index, args.shard_count)):
        if args.limit and idx >= args.limit:
            break
        entries.append(entry)

    results = []
    with result_path.open("w", encoding="utf-8") as out:
        if args.workers <= 1:
            for entry in entries:
                row = _evaluate_entry((entry, seeds, args.opponent_pool))
                out.write(json.dumps(row, sort_keys=True) + "\n")
                results.append(row)
        else:
            with ProcessPoolExecutor(max_workers=args.workers) as pool:
                futures = [pool.submit(_evaluate_entry, (entry, seeds, args.opponent_pool)) for entry in entries]
                for future in as_completed(futures):
                    row = future.result()
                    out.write(json.dumps(row, sort_keys=True) + "\n")
                    results.append(row)
    results.sort(key=lambda row: row["metrics"]["fitness"], reverse=True)
    top_path.write_text(json.dumps(results[:20], indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"result_path": str(result_path), "top_path": str(top_path), "evaluated": len(results)}))


if __name__ == "__main__":
    main()
