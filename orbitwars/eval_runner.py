from __future__ import annotations

import importlib.util
import json
import random
from pathlib import Path
from typing import Callable

from .env_loader import make_env
from .metrics import summarize_match

AgentFn = Callable[[dict, dict], list[list[float | int]]]


def _initial_home_planet_ids(steps: list[list[dict]], num_players: int) -> dict[int, int]:
    if not steps:
        return {}
    observation = steps[0][0]["observation"]
    home_ids: dict[int, int] = {}
    for raw in observation.get("planets", []):
        owner = int(raw[1])
        if 0 <= owner < num_players:
            home_ids[owner] = int(raw[0])
    return home_ids


def _snapshot_summary(observation: dict, num_players: int, home_ids: dict[int, int]) -> dict[int, dict[str, int | bool]]:
    planets_by_player = {player: 0 for player in range(num_players)}
    ships_by_player = {player: 0 for player in range(num_players)}
    home_alive = {player: False for player in range(num_players)}
    for planet in observation.get("planets", []):
        owner = int(planet[1])
        if 0 <= owner < num_players:
            planets_by_player[owner] += 1
            ships_by_player[owner] += int(planet[5])
            if home_ids.get(owner) == int(planet[0]):
                home_alive[owner] = True
    for fleet in observation.get("fleets", []):
        owner = int(fleet[1])
        if 0 <= owner < num_players:
            ships_by_player[owner] += int(fleet[6])
    return {
        player: {
            "planets": planets_by_player[player],
            "ships": ships_by_player[player],
            "home_alive": home_alive[player],
        }
        for player in range(num_players)
    }


def _collect_snapshots(steps: list[list[dict]], num_players: int, checkpoints: tuple[int, ...] = (50, 100)) -> dict[str, dict[int, dict[str, int | bool]]]:
    if not steps:
        return {}
    home_ids = _initial_home_planet_ids(steps, num_players)
    snapshots: dict[str, dict[int, dict[str, int | bool]]] = {}
    last_index = len(steps) - 1
    for checkpoint in checkpoints:
        index = min(checkpoint, last_index)
        observation = steps[index][0]["observation"]
        snapshots[f"step_{checkpoint}"] = _snapshot_summary(observation, num_players, home_ids)
    return snapshots


def _random_agent(observation: dict, configuration: dict) -> list[list[float | int]]:
    seed = f"{observation.get('step', 0)}-{observation.get('player', 0)}-{len(observation.get('planets', []))}"
    rng = random.Random(seed)
    owned = [planet for planet in observation.get("planets", []) if int(planet[1]) == int(observation.get("player", 0))]
    if not owned:
        return []
    planet = max(owned, key=lambda item: int(item[5]))
    if int(planet[5]) < 12 or rng.random() < 0.65:
        return []
    targets = [item for item in observation.get("planets", []) if int(item[1]) != int(observation.get("player", 0))]
    if not targets:
        return []
    target = min(targets, key=lambda item: abs(float(item[2]) - float(planet[2])) + abs(float(item[3]) - float(planet[3])))
    angle = __import__("math").atan2(float(target[3]) - float(planet[3]), float(target[2]) - float(planet[2]))
    send = max(1, int(int(planet[5]) * 0.45))
    return [[int(planet[0]), float(angle), send]]


def load_agent(spec: str) -> AgentFn:
    if spec == "random":
        return _random_agent
    path = Path(spec)
    if not path.is_absolute():
        path = Path.cwd() / path
    module_name = f"agent_{path.stem}_{abs(hash(str(path)))}"
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Unable to load agent from {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    agent = getattr(module, "agent", None)
    if not callable(agent):
        raise RuntimeError(f"{path} does not expose callable agent(observation, configuration)")
    return agent


def run_match(agent_specs: list[str], seed: int | None = None, episode_steps: int = 500) -> dict[str, object]:
    agents = [load_agent(spec) for spec in agent_specs]
    env = make_env(num_agents=len(agents), seed=seed, episode_steps=episode_steps)
    env.run(agents)
    statuses = [entry.status for entry in env.state]
    summary = summarize_match(statuses, env.state[0].observation, len(agents))
    summary["snapshots"] = _collect_snapshots(env.steps, len(agents))
    summary["seed"] = seed
    summary["agent_specs"] = agent_specs
    summary["json"] = json.dumps(summary, ensure_ascii=False)
    return summary
