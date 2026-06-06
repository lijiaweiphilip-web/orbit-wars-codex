from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import shutil
import sys
import tempfile
import time
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orbitwars.candidates import generate_candidate_missions
from orbitwars.env_loader import make_env
from orbitwars.eval_runner import _random_agent
from orbitwars.metrics import player_scores

AgentFn = Callable[[dict, dict], list[list[float | int]]]


def _clear_submission_modules() -> None:
    for name in list(sys.modules):
        if name == "agent" or name == "main" or name.startswith("orbitwars"):
            del sys.modules[name]


def _load_package_agent(spec: str, label: str) -> tuple[AgentFn, Path | None]:
    path = Path(spec)
    temp_dir: Path | None = None
    if path.suffix == ".zip":
        temp_dir = Path(tempfile.mkdtemp(prefix=f"orbit_{label}_"))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(temp_dir)
        package_root = temp_dir
    elif path.is_dir():
        package_root = path
    else:
        package_root = path.parent
    agent_path = package_root / "agent.py"
    if not agent_path.exists():
        agent_path = package_root / "main.py"
    if not agent_path.exists():
        raise RuntimeError(f"Cannot find agent.py or main.py in {spec}")
    _clear_submission_modules()
    sys.path.insert(0, str(package_root))
    try:
        module_name = f"agent_{label}_{abs(hash(str(path)))}"
        module_spec = importlib.util.spec_from_file_location(module_name, agent_path)
        if module_spec is None or module_spec.loader is None:
            raise RuntimeError(f"Unable to load {agent_path}")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        agent = getattr(module, "agent", None)
        if not callable(agent):
            raise RuntimeError(f"{agent_path} does not expose agent")
        return agent, temp_dir
    finally:
        if str(package_root) in sys.path:
            sys.path.remove(str(package_root))


def _snapshot(obs: dict[str, Any], num_players: int) -> dict[str, Any]:
    scores = player_scores(obs, num_players)
    production = {player: 0 for player in range(num_players)}
    planets = {player: 0 for player in range(num_players)}
    for planet in obs.get("planets", []):
        owner = int(planet[1])
        if 0 <= owner < num_players:
            production[owner] += int(planet[6])
            planets[owner] += 1
    return {"scores": scores, "production": production, "planets": planets}


def _run_paired_game(
    baseline: AgentFn,
    challenger: AgentFn,
    *,
    mode: str,
    seed: int,
    episode_steps: int,
) -> dict[str, Any]:
    num_agents = 2 if mode == "2p" else 4
    agents: list[AgentFn] = [challenger, baseline] if mode == "2p" else [challenger, baseline, _random_agent, _random_agent]
    env = make_env(num_agents=num_agents, seed=seed, episode_steps=episode_steps)
    start = time.perf_counter()
    env.run(agents)
    elapsed = time.perf_counter() - start
    final_obs = env.state[0].observation
    scores = player_scores(final_obs, num_agents)
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    ranks = {player: rank + 1 for rank, (player, _) in enumerate(ordered)}
    step100 = _snapshot(env.steps[min(100, len(env.steps) - 1)][0]["observation"], num_agents) if env.steps else {}
    mission_usage: Counter[str] = Counter()
    for idx in range(0, len(env.steps), 50):
        obs = env.steps[idx][0]["observation"]
        for candidate in generate_candidate_missions(obs, {"episodeSteps": episode_steps}, max_candidates=24):
            mission_usage[candidate.mission_type] += 1
    return {
        "mode": mode,
        "seed": seed,
        "challenger_score": scores.get(0, 0),
        "baseline_score": scores.get(1, 0),
        "score_delta": scores.get(0, 0) - scores.get(1, 0),
        "challenger_rank": ranks.get(0, num_agents),
        "baseline_rank": ranks.get(1, num_agents),
        "elapsed_sec": elapsed,
        "statuses": [entry.status for entry in env.state],
        "step100": step100,
        "mission_usage": dict(mission_usage),
    }


def _load_seed_list(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = []
        for value in payload.values():
            if isinstance(value, list):
                items.extend(value)
    else:
        raise RuntimeError(f"Unsupported seed list payload in {path}")
    seeds: list[int] = []
    for item in items:
        if isinstance(item, int):
            seeds.append(item)
        elif isinstance(item, dict) and "seed" in item:
            seeds.append(int(item["seed"]))
    deduped: list[int] = []
    seen: set[int] = set()
    for seed in seeds:
        if seed not in seen:
            deduped.append(seed)
            seen.add(seed)
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(description="Package-vs-package hard validation for Orbit Wars submissions.")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--challenger", required=True)
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--episode-steps", type=int, default=500)
    parser.add_argument("--modes", default="2p,4p")
    parser.add_argument("--seed", type=int, default=20260605)
    parser.add_argument("--seed-list-file", default="")
    parser.add_argument("--output-dir", default="experiments/nn_ranker_v1/hard_validation")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_agent, baseline_tmp = _load_package_agent(args.baseline, "baseline")
    challenger_agent, challenger_tmp = _load_package_agent(args.challenger, "challenger")
    modes = [mode.strip() for mode in args.modes.split(",") if mode.strip()]
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    try:
        explicit_seeds = _load_seed_list(Path(args.seed_list_file)) if args.seed_list_file else []
        if explicit_seeds:
            seed_schedule = explicit_seeds
        else:
            seed_schedule = [args.seed + game_idx for game_idx in range(args.games)]
        for game_idx, scheduled_seed in enumerate(seed_schedule):
            mode = modes[game_idx % len(modes)]
            row = _run_paired_game(
                baseline_agent,
                challenger_agent,
                mode=mode,
                seed=scheduled_seed,
                episode_steps=args.episode_steps,
            )
            rows.append(row)
            if any(status not in ("DONE", "ACTIVE", "INACTIVE") for status in row["statuses"]):
                failures.append(row)
    finally:
        for temp_dir in (baseline_tmp, challenger_tmp):
            if temp_dir is not None:
                shutil.rmtree(temp_dir, ignore_errors=True)

    results_path = output_dir / "results.csv"
    with results_path.open("w", encoding="utf-8", newline="") as fh:
        fieldnames = ["mode", "seed", "challenger_score", "baseline_score", "score_delta", "challenger_rank", "baseline_rank", "elapsed_sec", "statuses", "step100", "mission_usage"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})
    with (output_dir / "failure_cases.jsonl").open("w", encoding="utf-8") as fh:
        for row in failures:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    two_p = [row for row in rows if row["mode"] == "2p"]
    four_p = [row for row in rows if row["mode"] == "4p"]
    two_p_win_rate = sum(1 for row in two_p if row["challenger_score"] > row["baseline_score"]) / max(1, len(two_p))
    four_p_avg_rank = sum(float(row["challenger_rank"]) for row in four_p) / max(1, len(four_p))
    four_p_top2 = sum(1 for row in four_p if int(row["challenger_rank"]) <= 2) / max(1, len(four_p))
    final_delta = sum(float(row["score_delta"]) for row in rows) / max(1, len(rows))
    mission_total: Counter[str] = Counter()
    for row in rows:
        mission_total.update(row["mission_usage"])
    worst = sorted(rows, key=lambda row: row["score_delta"])[:10]
    report = [
        "# Package-vs-Package Hard Validation",
        "",
        f"- baseline: `{args.baseline}`",
        f"- challenger: `{args.challenger}`",
        f"- games: {args.games}",
        f"- episode_steps: {args.episode_steps}",
        f"- modes: {modes}",
        f"- 2p_win_rate: {two_p_win_rate:.3f}",
        f"- 4p_avg_rank: {four_p_avg_rank:.3f}",
        f"- 4p_top2_rate: {four_p_top2:.3f}",
        f"- final_score_delta_mean: {final_delta:.3f}",
        f"- timeout_or_error_count: {len(failures)}",
        "",
        "## Mission Usage Frequency",
        "",
        "| mission | count |",
        "|---|---:|",
    ]
    for mission, count in mission_total.most_common():
        report.append(f"| {mission} | {count} |")
    report.extend(["", "## Worst 10 Losses", "", "| mode | seed | delta | challenger | baseline | rank |", "|---|---:|---:|---:|---:|---:|"])
    for row in worst:
        report.append(f"| {row['mode']} | {row['seed']} | {row['score_delta']} | {row['challenger_score']} | {row['baseline_score']} | {row['challenger_rank']} |")
    report.extend(["", "## Baseline vs Challenger Paired Seed Table", "", "| mode | seed | challenger_score | baseline_score | delta | step100 |", "|---|---:|---:|---:|---:|---|"])
    for row in rows[:50]:
        report.append(f"| {row['mode']} | {row['seed']} | {row['challenger_score']} | {row['baseline_score']} | {row['score_delta']} | `{json.dumps(row['step100'], sort_keys=True)}` |")
    (output_dir / "package_vs_package_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"games": len(rows), "2p_win_rate": two_p_win_rate, "4p_avg_rank": four_p_avg_rank, "final_score_delta_mean": final_delta, "errors": len(failures)}, sort_keys=True))


if __name__ == "__main__":
    main()
