from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .eval_runner import run_match


def parse_seeds(raw: str, games: int) -> list[int | None]:
    if not raw:
        return list(range(1, games + 1))
    if ":" in raw:
        start, end = raw.split(":", 1)
        return list(range(int(start), int(end) + 1))
    return [int(item) for item in raw.split(",") if item]


def parse_checkpoints(raw: str) -> tuple[int, ...]:
    if not raw:
        return (50, 100)
    values = [int(item) for item in raw.split(",") if item.strip()]
    if not values:
        return (50, 100)
    return tuple(sorted(set(values)))


def append_results(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tag",
        "mode",
        "seed",
        "agents",
        "winner",
        "ranks",
        "scores",
        "statuses",
        "snapshots",
    ]
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", required=True)
    parser.add_argument("--mode", choices=["2p", "4p"], default="2p")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seeds", default="")
    parser.add_argument("--episode-steps", type=int, default=200)
    parser.add_argument("--checkpoints", default="50,100")
    parser.add_argument("--tag", default="manual")
    parser.add_argument("--results-path", default="experiments/results.csv")
    args = parser.parse_args()

    agent_specs = [item.strip() for item in args.agents.split(",") if item.strip()]
    needed = 2 if args.mode == "2p" else 4
    if len(agent_specs) != needed:
        raise SystemExit(f"{args.mode} requires exactly {needed} agents, got {len(agent_specs)}")

    seeds = parse_seeds(args.seeds, args.games)
    checkpoints = parse_checkpoints(args.checkpoints)
    rows = []
    aggregate_rank_sum = 0.0
    aggregate_wins = 0
    for seed in seeds[: args.games]:
        result = run_match(agent_specs, seed=seed, episode_steps=args.episode_steps, checkpoints=checkpoints)
        my_rank = result["ranks"][0]
        aggregate_rank_sum += my_rank
        aggregate_wins += 1 if my_rank == 1 else 0
        rows.append(
            {
                "tag": args.tag,
                "mode": args.mode,
                "seed": seed,
                "agents": "|".join(agent_specs),
                "winner": min(result["ranks"], key=result["ranks"].get),
                "ranks": json.dumps(result["ranks"], ensure_ascii=False),
                "scores": json.dumps(result["scores"], ensure_ascii=False),
                "statuses": json.dumps(result["statuses"], ensure_ascii=False),
                "snapshots": json.dumps(result.get("snapshots", {}), ensure_ascii=False),
            }
        )
    append_results(Path(args.results_path), rows)
    games_played = max(1, min(len(seeds), args.games))
    summary = {
        "games": games_played,
        "win_rate_agent0": round(aggregate_wins / games_played, 4),
        "avg_rank_agent0": round(aggregate_rank_sum / games_played, 4),
        "agents": agent_specs,
        "mode": args.mode,
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
