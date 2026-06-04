from __future__ import annotations

import argparse
import json
from pathlib import Path

from .eval_runner import run_match
from .replay_tools import load_rows, summarize
from .tournament import append_results


def load_pool(path: Path, pool_name: str) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    pools = payload if isinstance(payload, list) else payload.get(pool_name, [])
    if not pools:
        raise SystemExit(f"no sparring pool named '{pool_name}' in {path}")
    return pools


def run_pool(pool: list[dict[str, object]], tag_prefix: str, results_path: Path) -> list[dict[str, object]]:
    all_rows: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for matchup in pool:
        agents = [str(item) for item in matchup["agents"]]
        games = int(matchup.get("games", 6))
        episode_steps = int(matchup.get("episode_steps", 120))
        name = str(matchup["name"])
        mode = str(matchup["mode"])
        tag = f"{tag_prefix}_{name}"
        rows: list[dict[str, object]] = []
        wins = 0
        rank_sum = 0.0
        for seed in range(1, games + 1):
            result = run_match(agents, seed=seed, episode_steps=episode_steps)
            my_rank = result["ranks"][0]
            rank_sum += my_rank
            wins += 1 if my_rank == 1 else 0
            rows.append(
                {
                    "tag": tag,
                    "mode": mode,
                    "seed": seed,
                    "agents": "|".join(agents),
                    "winner": min(result["ranks"], key=result["ranks"].get),
                    "ranks": json.dumps(result["ranks"], ensure_ascii=False),
                    "scores": json.dumps(result["scores"], ensure_ascii=False),
                    "statuses": json.dumps(result["statuses"], ensure_ascii=False),
                    "snapshots": json.dumps(result.get("snapshots", {}), ensure_ascii=False),
                }
            )
        append_results(results_path, rows)
        all_rows.extend(rows)
        summaries.append(
            {
                "tag": tag,
                "mode": mode,
                "games": games,
                "win_rate_agent0": round(wins / max(games, 1), 4),
                "avg_rank_agent0": round(rank_sum / max(games, 1), 4),
                "agents": agents,
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", default="default")
    parser.add_argument("--config", default="configs/sparring_pool.json")
    parser.add_argument("--tag-prefix", default="sparring")
    parser.add_argument("--results-path", default="experiments/results.csv")
    parser.add_argument("--summary-path", default="")
    args = parser.parse_args()

    results_path = Path(args.results_path)
    pool = load_pool(Path(args.config), args.pool)
    matchup_summaries = run_pool(pool, args.tag_prefix, results_path)
    matching_tags = [item["tag"] for item in matchup_summaries]
    filtered_rows = [row for row in load_rows(results_path) if row["tag"] in matching_tags]
    combined = summarize(filtered_rows)
    payload = {
        "pool": args.pool,
        "tag_prefix": args.tag_prefix,
        "matchups": matchup_summaries,
        "combined": combined,
        "results_path": str(results_path),
    }
    if args.summary_path:
        summary_path = Path(args.summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
