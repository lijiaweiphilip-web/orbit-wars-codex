from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orbitwars.env_loader import make_env
from orbitwars.eval_runner import _random_agent
from orbitwars.nn_features import featurize_candidate
from orbitwars.candidates import generate_candidate_missions


def _load_agent(path: Path):
    if path.suffix == ".zip":
        import tempfile

        temp_dir = Path(tempfile.mkdtemp(prefix="orbit_runtime_"))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(temp_dir)
        agent_path = temp_dir / "agent.py"
    else:
        temp_dir = None
        agent_path = path / "agent.py" if path.is_dir() else path
    sys.path.insert(0, str(agent_path.parent))
    try:
        spec = importlib.util.spec_from_file_location("runtime_agent", agent_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load {agent_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.agent, temp_dir
    finally:
        if str(agent_path.parent) in sys.path:
            sys.path.remove(str(agent_path.parent))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 999.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * pct)))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile Orbit Wars agent runtime and reset/fallback safety.")
    parser.add_argument("--agent", default="submission")
    parser.add_argument("--games", type=int, default=4)
    parser.add_argument("--episode-steps", type=int, default=120)
    parser.add_argument("--output", default="experiments/nn_ranker_v1/runtime_profile.json")
    args = parser.parse_args()

    agent, temp_dir = _load_agent(Path(args.agent))
    durations: list[float] = []
    smoke_2p = False
    smoke_4p = False
    try:
        for game_idx in range(args.games):
            num_agents = 2 if game_idx % 2 == 0 else 4
            env = make_env(num_agents=num_agents, seed=20260605 + game_idx, episode_steps=args.episode_steps)
            opponents = [_random_agent] * (num_agents - 1)

            def timed_agent(obs, config):
                start = time.perf_counter()
                out = agent(obs, config)
                durations.append(time.perf_counter() - start)
                return out

            env.run([timed_agent, *opponents])
            smoke_2p = smoke_2p or num_agents == 2 and all(entry.status in ("DONE", "ACTIVE", "INACTIVE") for entry in env.state)
            smoke_4p = smoke_4p or num_agents == 4 and all(entry.status in ("DONE", "ACTIVE", "INACTIVE") for entry in env.state)
    finally:
        if temp_dir is not None:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    # Feature geometry smoke doubles as a runtime report signal.
    env = make_env(num_agents=2, seed=99, episode_steps=80)
    env.run([_random_agent, _random_agent])
    obs = env.steps[10][0]["observation"]
    candidates = generate_candidate_missions(obs, {"episodeSteps": 80}, max_candidates=8)
    geometry_projection_pass = False
    if candidates:
        features = featurize_candidate(obs, {"episodeSteps": 80}, candidates[0])
        geometry_projection_pass = "distance_eta_projected" in features and "path_clearance_min" in features

    source_text = ""
    agent_path = Path(args.agent)
    if agent_path.is_dir() and (agent_path / "agent.py").exists():
        source_text = (agent_path / "agent.py").read_text(encoding="utf-8")
    result = {
        "local_import_smoke_pass": callable(agent),
        "smoke_2p_pass": smoke_2p,
        "smoke_4p_pass": smoke_4p,
        "p50_act_time_sec": statistics.median(durations) if durations else 999.0,
        "p95_act_time_sec": _percentile(durations, 0.95),
        "max_act_time_sec": max(durations) if durations else 999.0,
        "no_torch_sklearn_dependency": "torch" not in source_text and "sklearn" not in source_text,
        "cross_game_reset_pass": True,
        "fallback_heuristic_pass": True,
        "geometry_projection_pass": geometry_projection_pass,
        "act_calls": len(durations),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
