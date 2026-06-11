from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import random
import signal
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Callable


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def bullets(obj: dict[str, Any]) -> str:
    return "\n".join(f"- {k}: `{v}`" for k, v in obj.items())


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def stable_id(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def ensure_l40s() -> dict[str, Any]:
    host = getattr(os, "uname", lambda: None)()
    host_name = host.nodename if host is not None else os.environ.get("COMPUTERNAME", "")
    if not str(host_name).startswith("TC2N"):
        return {"host": host_name, "device": "local_or_unknown", "cuda": False}
    if str(host_name).startswith(("TC2N01", "TC2N02")):
        raise SystemExit(f"Refusing non-L40S node: {host_name}")
    import torch

    cuda = bool(torch.cuda.is_available())
    device = torch.cuda.get_device_name(0) if cuda else "NO_CUDA"
    if not cuda or "L40S" not in device:
        raise SystemExit(f"Refusing non-L40S CUDA device: host={host_name} device={device}")
    print(f"SHA_X1_REAL_LABEL_ENV_OK torch={torch.__version__} device={device}")
    return {"host": host_name, "device": device, "cuda": cuda}


def clear_orbit_modules() -> None:
    for name in list(sys.modules):
        if name == "orbitwars" or name.startswith("orbitwars."):
            sys.modules.pop(name, None)


def load_agent(zip_path: Path) -> tuple[Callable[[dict[str, Any], dict[str, Any]], Any], tempfile.TemporaryDirectory[str]]:
    td = tempfile.TemporaryDirectory()
    tmp = Path(td.name)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp)
    candidates = list(tmp.rglob("agent.py")) + list(tmp.rglob("main.py"))
    if not candidates:
        td.cleanup()
        raise RuntimeError(f"No agent.py/main.py in {zip_path}")
    agent_file = candidates[0]
    clear_orbit_modules()
    sys.path.insert(0, str(agent_file.parent))
    try:
        spec = importlib.util.spec_from_file_location(f"agent_{stable_id(str(zip_path))}", agent_file)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load spec for {agent_file}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "agent", None) or getattr(mod, "main", None)
        if not callable(fn):
            raise RuntimeError(f"No callable agent/main in {agent_file}")
        return fn, td
    finally:
        try:
            sys.path.remove(str(agent_file.parent))
        except ValueError:
            pass


class AgentBank:
    def __init__(self, repo: Path, package_paths: dict[str, str]) -> None:
        self.repo = repo
        self.package_paths = package_paths
        self._agents: dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]] = {}
        self._temps: list[tempfile.TemporaryDirectory[str]] = []

    def get(self, name: str) -> Callable[[dict[str, Any], dict[str, Any]], Any]:
        if name in self._agents:
            return self._agents[name]
        path = self.repo / self.package_paths[name]
        fn, td = load_agent(path)
        self._agents[name] = fn
        self._temps.append(td)
        return fn

    def close(self) -> None:
        for td in self._temps:
            td.cleanup()
        self._temps.clear()


def make_env(nplayers: int, seed: int, episode_steps: int):
    from kaggle_environments import make

    last: Exception | None = None
    for env_name in ("orbit_wars", "orbit-wars"):
        for seed_key in ("seed", "randomSeed"):
            try:
                env = make(env_name, configuration={"episodeSteps": episode_steps, seed_key: seed}, debug=False)
                try:
                    env.num_agents = nplayers
                except Exception:
                    pass
                try:
                    env.configuration["agentCount"] = nplayers
                except Exception:
                    pass
                return env
            except Exception as exc:
                last = exc
    raise RuntimeError(f"Cannot create Orbit Wars env: {last}")


def obs_to_dict(obs: Any) -> dict[str, Any]:
    if isinstance(obs, dict):
        return obs
    if hasattr(obs, "to_dict"):
        try:
            return obs.to_dict()
        except Exception:
            pass
    return dict(getattr(obs, "__dict__", {}))


def make_obs_copy(obs: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(obs, default=str))


def action_from_candidate(candidate: dict[str, Any]) -> list[list[Any]]:
    actions: list[list[Any]] = []
    for source_id, angle, ships in zip(
        candidate.get("source_ids", []),
        candidate.get("angles", []),
        candidate.get("send_ships", []),
    ):
        send = max(0, int(ships))
        if send > 0:
            actions.append([int(source_id), float(angle), send])
    return actions


def player_stats(obs: dict[str, Any], nplayers: int, player_id: int = 0) -> dict[str, Any]:
    totals: dict[int, dict[str, float]] = {
        pid: {"planets": 0.0, "production": 0.0, "ships": 0.0, "fleet_ships": 0.0}
        for pid in range(nplayers)
    }
    for planet in obs.get("planets", []) or []:
        owner = int(planet[1])
        if owner >= 0:
            row = totals.setdefault(owner, {"planets": 0.0, "production": 0.0, "ships": 0.0, "fleet_ships": 0.0})
            row["planets"] += 1.0
            row["ships"] += float(planet[5])
            row["production"] += float(planet[6])
    for fleet in obs.get("fleets", []) or []:
        if len(fleet) < 3:
            continue
        owner = int(fleet[1])
        ships = float(fleet[-1])
        if owner >= 0:
            totals.setdefault(owner, {"planets": 0.0, "production": 0.0, "ships": 0.0, "fleet_ships": 0.0})["fleet_ships"] += ships

    def strength(row: dict[str, float]) -> float:
        return row["ships"] + row["fleet_ships"] + row["production"] * 18.0 + row["planets"] * 12.0

    scored = sorted(((pid, strength(row)) for pid, row in totals.items()), key=lambda item: item[1], reverse=True)
    rank = 1 + sum(score > dict(scored).get(player_id, 0.0) for _, score in scored)
    mine = totals.get(player_id, {"planets": 0.0, "production": 0.0, "ships": 0.0, "fleet_ships": 0.0})
    enemy_leader = next(((pid, score) for pid, score in scored if pid != player_id), (-1, 0.0))
    return {
        "planet_count": mine["planets"],
        "production": mine["production"],
        "ship_total": mine["ships"] + mine["fleet_ships"],
        "rank": float(rank),
        "top2": 1.0 if rank <= 2 else 0.0,
        "win_proxy": 1.0 - ((rank - 1.0) / max(1.0, nplayers - 1.0)),
        "strength": strength(mine),
        "leader_enemy_id": enemy_leader[0],
        "leader_enemy_strength": enemy_leader[1],
    }


def planet_by_id(obs: dict[str, Any]) -> dict[int, list[Any]]:
    return {int(p[0]): p for p in obs.get("planets", []) or []}


def target_owner(obs: dict[str, Any], target_id: int | None) -> int | None:
    if target_id is None:
        return None
    planet = planet_by_id(obs).get(int(target_id))
    return None if planet is None else int(planet[1])


def target_ships(obs: dict[str, Any], target_id: int | None) -> float | None:
    if target_id is None:
        return None
    planet = planet_by_id(obs).get(int(target_id))
    return None if planet is None else float(planet[5])


def source_ship_map(obs: dict[str, Any], source_ids: list[int]) -> dict[str, float | None]:
    rows = planet_by_id(obs)
    out: dict[str, float | None] = {}
    for sid in source_ids:
        planet = rows.get(int(sid))
        out[str(sid)] = None if planet is None else float(planet[5])
    return out


def trace_snapshot(obs: dict[str, Any], candidate: dict[str, Any], nplayers: int) -> dict[str, Any]:
    stats = player_stats(obs, nplayers)
    source_ids = [int(x) for x in candidate.get("source_ids", [])]
    target_id = candidate.get("target_id")
    return {
        "step": int(obs.get("step", -1)),
        "state_id": str(obs.get("state_id", "")),
        "source_ships": source_ship_map(obs, source_ids),
        "target_owner": target_owner(obs, target_id),
        "target_ships": target_ships(obs, target_id),
        "fleet_count": len(obs.get("fleets", []) or []),
        "planet_count": stats["planet_count"],
        "production": stats["production"],
        "ship_total": stats["ship_total"],
        "rank": stats["rank"],
        "top2": stats["top2"],
        "win_proxy": stats["win_proxy"],
        "leader_enemy_strength": stats["leader_enemy_strength"],
    }


def snapshot_diff(
    control: dict[str, Any],
    forced: dict[str, Any],
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    for key in (
        "target_owner",
        "target_ships",
        "fleet_count",
        "planet_count",
        "production",
        "ship_total",
        "rank",
        "top2",
        "win_proxy",
        "leader_enemy_strength",
    ):
        cv = control.get(key)
        fv = forced.get(key)
        if is_number(cv) and is_number(fv):
            diff[key] = fv - cv
        else:
            diff[key] = {"control": cv, "forced": fv}
    diff["source_ships"] = {
        sid: None if control["source_ships"].get(sid) is None or forced["source_ships"].get(sid) is None else forced["source_ships"][sid] - control["source_ships"][sid]
        for sid in set(control.get("source_ships", {})) | set(forced.get("source_ships", {}))
    }

    control_target_owner = control.get("target_owner")
    forced_target_owner = forced.get("target_owner")
    if control_target_owner is None or forced_target_owner is None:
        owner_changed = None
    else:
        owner_changed = control_target_owner != forced_target_owner
    diff["owner_change"] = owner_changed

    source_ship_changed = any(
        is_number(v) and abs(float(v)) > 1e-9
        for v in diff.get("source_ships", {}).values()
        if v is not None
    )
    target_ship_delta = diff.get("target_ships")
    target_ships_delta = (
        (target_ship_delta["forced"] - target_ship_delta["control"])
        if isinstance(target_ship_delta, dict)
        and is_number(target_ship_delta.get("forced"))
        and is_number(target_ship_delta.get("control"))
        else 0.0
    )
    if candidate is not None and candidate.get("send_ships"):
        eta_min = candidate.get("eta_min")
        eta_event = is_number(eta_min) and eta_min <= 1.0
        arrival = bool(
            source_ship_changed
            or owner_changed is True
            or (is_number(target_ships_delta) and abs(target_ships_delta) > 1e-9)
            or eta_event
        )
    else:
        arrival = False
    diff["arrival_event"] = bool(arrival)
    return diff


def shaped_reward(
    before_obs: dict[str, Any],
    control_obs: dict[str, Any],
    forced_obs: dict[str, Any],
    candidate: dict[str, Any],
    nplayers: int,
) -> dict[str, float]:
    control = player_stats(control_obs, nplayers)
    forced = player_stats(forced_obs, nplayers)
    target_id = candidate.get("target_id")
    control_target_owner = target_owner(control_obs, target_id)
    forced_target_owner = target_owner(forced_obs, target_id)
    source_overdrain = 0.0
    rows = planet_by_id(before_obs)
    for sid, sent in zip(candidate.get("source_ids", []), candidate.get("send_ships", [])):
        planet = rows.get(int(sid))
        if planet is None:
            continue
        source_ships = max(1.0, float(planet[5]))
        source_overdrain += max(0.0, (float(sent) / source_ships) - 0.72)
    leader_help = max(0.0, forced["leader_enemy_strength"] - control["leader_enemy_strength"]) / 50.0
    components = {
        "planet_count_delta": forced["planet_count"] - control["planet_count"],
        "production_delta": forced["production"] - control["production"],
        "ship_delta": forced["ship_total"] - control["ship_total"],
        "target_capture": 1.0 if forced_target_owner == 0 and control_target_owner != 0 else 0.0,
        "source_overdrain_penalty": -source_overdrain,
        "rank_delta": control["rank"] - forced["rank"],
        "top2_delta": forced["top2"] - control["top2"],
        "win_proxy": forced["win_proxy"] - control["win_proxy"],
        "leader_help_penalty": -leader_help,
    }
    components["win_proxy_delta"] = components["win_proxy"]
    reward = (
        components["planet_count_delta"] * 20.0
        + components["production_delta"] * 8.0
        + components["ship_delta"] * 0.20
        + components["target_capture"] * 16.0
        + components["rank_delta"] * 24.0
        + components["top2_delta"] * 18.0
        + components["win_proxy_delta"] * 14.0
        + components["source_overdrain_penalty"] * 8.0
        + components["leader_help_penalty"] * 10.0
    )
    components["delta_reward"] = reward
    return {key: float(value) for key, value in components.items()}


def generate_candidates(repo: Path, obs: dict[str, Any], config: dict[str, Any], max_candidates: int) -> list[dict[str, Any]]:
    sys.path.insert(0, str(repo))
    try:
        clear_orbit_modules()
        from orbitwars.candidates import generate_candidate_missions

        rows = [c.to_dict() for c in generate_candidate_missions(obs, config, max_candidates=max_candidates)]
    finally:
        try:
            sys.path.remove(str(repo))
        except ValueError:
            pass
    return rows


def angle_between(source: list[Any], target: list[Any]) -> float:
    return math.atan2(float(target[3]) - float(source[3]), float(target[2]) - float(source[2]))


def make_candidate_from_planets(
    mission_type: str,
    profile: str,
    source: list[Any],
    target: list[Any],
    send: int,
    score: float,
) -> dict[str, Any]:
    theta = angle_between(source, target)
    dist = math.hypot(float(target[2]) - float(source[2]), float(target[3]) - float(source[3]))
    eta = int(math.ceil(dist / 6.0))
    return {
        "mission_type": mission_type,
        "mission_profile": profile,
        "source_ids": [int(source[0])],
        "target_id": int(target[0]),
        "send_ships": [max(1, min(int(send), int(source[5])))],
        "angles": [float(theta)],
        "eta_min": eta,
        "eta_max": eta,
        "heuristic_score": float(score),
        "safety_flags": {"safe": True, "valid_send": True, "angle_finite": True},
        "debug": {
            "source_ships": int(source[5]),
            "target_owner": int(target[1]),
            "target_ships": int(target[5]),
            "target_production": int(target[6]),
            "profile": profile,
        },
    }


def _scaled_candidate_by_factor(
    base: dict[str, Any],
    factor: float,
    source: list[Any],
    target: list[Any],
) -> dict[str, Any] | None:
    mission_type = str(base.get("mission_type", "capture_enemy"))
    profile = str(base.get("mission_profile", mission_type))
    base_send = int(base.get("send_ships", [0])[0]) if base.get("send_ships") else 0
    if base_send <= 0:
        return None
    scaled_send = max(1, int(math.ceil(base_send * factor)))
    max_send = max(1, int(source[5]))
    scaled_send = min(scaled_send, max_send)
    score = float(base.get("heuristic_score", 0.0)) * factor
    return make_candidate_from_planets(mission_type, profile, source, target, scaled_send, score)


def augment_candidates(obs: dict[str, Any], candidates: list[dict[str, Any]], nplayers: int, limit: int) -> list[dict[str, Any]]:
    required_profiles = [
        "obvious_good",
        "obvious_bad",
        "overdrain",
        "high_production_capture",
        "leader_help_trap",
        "third_party_steal",
        "2p_snowball",
    ]
    planets = obs.get("planets", []) or []
    my_sources = sorted([p for p in planets if int(p[1]) == 0], key=lambda p: (int(p[5]), int(p[6])), reverse=True)
    targets = [p for p in planets if int(p[1]) != 0]
    high_prod = sorted(targets, key=lambda p: (int(p[6]), -int(p[5])), reverse=True)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(c: dict[str, Any], profile: str | None = None) -> None:
        if profile is not None:
            c = {**c, "mission_profile": profile}
        c.setdefault("mission_profile", c.get("mission_type", "unknown"))
        key = stable_id([c.get("mission_type"), c.get("mission_profile"), c.get("source_ids"), c.get("target_id"), c.get("send_ships")])
        if key not in seen:
            seen.add(key)
            rows.append(c)

    def ensure_scale_variants(base_candidates: list[dict[str, Any]]) -> None:
        if len(rows) >= limit or not base_candidates:
            return
        scales = [0.65, 0.8, 1.0, 1.2, 1.4]
        by_id = planet_by_id(obs)
        i = 0
        while len(rows) < limit and base_candidates:
            base = base_candidates[i % len(base_candidates)]
            i += 1
            source_id = int((base.get("source_ids") or [])[0]) if base.get("source_ids") else None
            target_id = int(base.get("target_id")) if base.get("target_id") is not None else None
            if source_id is None or target_id is None:
                continue
            source = by_id.get(source_id)
            target = by_id.get(target_id)
            if source is None or target is None:
                continue
            scaled = _scaled_candidate_by_factor(base, scales[i % len(scales)], source, target)
            if scaled is None:
                continue
            add(scaled, scaled.get("mission_profile"))

    for c in candidates:
        mt = str(c.get("mission_type", "unknown"))
        profile = {
        "capture_neutral": "obvious_good",
        "capture_enemy": "high_production_capture",
        "snipe": "third_party_steal",
        "weak_harvest": "leader_help_trap",
        "leader_bash": "leader_help_trap",
        "swarm": "2p_snowball" if nplayers == 2 else "high_production_capture",
        "hold": "obvious_bad",
        "rescue": "leader_help_trap",
        "recapture": "obvious_bad",
    }.get(mt, mt)
        add(c, profile)
    if my_sources and high_prod:
        source = my_sources[0]
        target = high_prod[0]
        need = int(target[5]) + int(target[6]) * 4 + 3
        add(make_candidate_from_planets("capture_enemy" if int(target[1]) >= 0 else "capture_neutral", "high_production_capture", source, target, need, 100.0))
        add(make_candidate_from_planets("capture_enemy" if int(target[1]) >= 0 else "capture_neutral", "obvious_bad", source, target, 1, -100.0))
        add(make_candidate_from_planets("capture_enemy" if int(target[1]) >= 0 else "capture_neutral", "overdrain", source, target, int(float(source[5]) * 0.9), -20.0))
    if nplayers == 2 and len(my_sources) >= 1 and len(high_prod) >= 2:
        add(make_candidate_from_planets("capture_neutral" if int(high_prod[1][1]) < 0 else "capture_enemy", "2p_snowball", my_sources[0], high_prod[1], int(high_prod[1][5]) + 6, 80.0))
    if nplayers >= 4 and my_sources and len(high_prod) >= 2:
        weakest_owned = [p for p in high_prod if int(p[1]) not in (-1, 0)]
        if weakest_owned:
            add(make_candidate_from_planets("weak_harvest", "leader_help_trap", my_sources[0], weakest_owned[-1], max(1, int(weakest_owned[-1][5]) // 2), -30.0))
        add(make_candidate_from_planets("snipe", "third_party_steal", my_sources[0], high_prod[0], max(1, int(high_prod[0][5]) // 2), 40.0))
    ensure_scale_variants(list(rows))

    present = {str(r.get("mission_profile", "")) for r in rows}
    if my_sources and high_prod:
        fallback_src = my_sources[0]
        fallback_target = high_prod[0]
        for missing in required_profiles:
            if missing in present:
                continue
            if missing == "obvious_good":
                add(make_candidate_from_planets("capture_neutral" if int(fallback_target[1]) < 0 else "capture_enemy", missing, fallback_src, fallback_target, max(1, int(fallback_target[5]) // 2), 90.0))
            elif missing == "obvious_bad":
                add(make_candidate_from_planets("capture_neutral" if int(fallback_target[1]) < 0 else "capture_enemy", missing, fallback_src, fallback_target, 1, -90.0))
            elif missing == "overdrain":
                add(make_candidate_from_planets("capture_neutral" if int(fallback_target[1]) < 0 else "capture_enemy", missing, fallback_src, fallback_target, max(1, int(float(fallback_src[5]) * 0.9)), -10.0))
            elif missing == "high_production_capture" and high_prod:
                add(make_candidate_from_planets("capture_enemy" if int(high_prod[0][1]) >= 0 else "capture_neutral", missing, fallback_src, high_prod[0], int(high_prod[0][5]) + 6, 95.0))
            elif missing == "leader_help_trap" and len(high_prod) >= 2:
                add(make_candidate_from_planets("weak_harvest", missing, fallback_src, high_prod[-1], max(1, int(high_prod[-1][5]) // 2), -25.0))
            elif missing == "third_party_steal" and high_prod:
                add(make_candidate_from_planets("snipe", missing, fallback_src, high_prod[0], max(1, int(high_prod[0][5]) // 2), 35.0))
            elif missing == "2p_snowball" and nplayers == 2 and len(high_prod) >= 2:
                add(make_candidate_from_planets("capture_neutral" if int(high_prod[1][1]) < 0 else "capture_enemy", missing, fallback_src, high_prod[1], int(high_prod[1][5]) + 5, 75.0))
    ensure_scale_variants(list(rows))
    return rows[:limit]


class RecordingAgent:
    def __init__(
        self,
        base: Callable[[dict[str, Any], dict[str, Any]], Any],
        repo: Path,
        source_policy: str,
        nplayers: int,
        seed: int,
        sample_steps: list[int],
        max_states: int,
        missions_per_state: int,
        sink: list[dict[str, Any]],
    ) -> None:
        self.base = base
        self.repo = repo
        self.source_policy = source_policy
        self.nplayers = nplayers
        self.seed = seed
        self.sample_steps = sample_steps
        self.max_states = max_states
        self.missions_per_state = missions_per_state
        self.sink = sink
        self.recorded_steps: set[int] = set()
        self.errors: list[str] = []

    def __call__(self, obs: dict[str, Any], config: dict[str, Any]) -> Any:
        obs_dict = obs_to_dict(obs)
        try:
            step = int(obs_dict.get("step", 0))
            player = int(obs_dict.get("player", 0))
            eligible = any(step >= target for target in self.sample_steps)
            if player == 0 and len(self.sink) < self.max_states and eligible and step not in self.recorded_steps:
                candidates = generate_candidates(self.repo, obs_dict, config, self.missions_per_state * 3)
                candidates = augment_candidates(obs_dict, candidates, self.nplayers, self.missions_per_state)
                if candidates:
                    self.recorded_steps.add(step)
                    state_id = stable_id({"seed": self.seed, "step": step, "source": self.source_policy, "n": self.nplayers, "obs": obs_dict})
                    self.sink.append(
                        {
                            "state_id": state_id,
                            "seed": self.seed,
                            "step": step,
                            "nplayers": self.nplayers,
                            "source_policy": self.source_policy,
                            "obs": make_obs_copy(obs_dict),
                            "config": dict(config),
                            "baseline_proxy": player_stats(obs_dict, self.nplayers),
                            "candidate_count": len(candidates),
                            "candidates": candidates,
                        }
                    )
        except Exception as exc:
            self.errors.append(f"record_step_error:{type(exc).__name__}:{exc}")
        return self.base(obs, config)


class ForcedAgent:
    def __init__(
        self,
        base: Callable[[dict[str, Any], dict[str, Any]], Any],
        force_step: int,
        candidate: dict[str, Any] | None,
    ) -> None:
        self.base = base
        self.force_step = force_step
        self.candidate = candidate
        self.applied = False
        self.action: Any = None

    def __call__(self, obs: dict[str, Any], config: dict[str, Any]) -> Any:
        obs_dict = obs_to_dict(obs)
        step = int(obs_dict.get("step", 0))
        player = int(obs_dict.get("player", 0))
        if player == 0 and self.candidate is not None and step == self.force_step:
            self.applied = True
            self.action = action_from_candidate(self.candidate)
            return self.action
        return self.base(obs, config)


def run_replay(
    bank: AgentBank,
    policy: str,
    nplayers: int,
    seed: int,
    episode_steps: int,
    force_step: int | None = None,
    candidate: dict[str, Any] | None = None,
) -> tuple[Any, ForcedAgent | None]:
    base = bank.get(policy)
    forced_agent = ForcedAgent(base, force_step if force_step is not None else -1, candidate) if force_step is not None else None
    agent0 = forced_agent if forced_agent is not None else base
    agents = [agent0] + [base for _ in range(nplayers - 1)]
    env = make_env(nplayers, seed, episode_steps)
    env.run(agents)
    return env, forced_agent


def get_obs_at_or_before(env: Any, step: int, player: int = 0) -> dict[str, Any]:
    idx = min(max(0, step), len(env.steps) - 1)
    return obs_to_dict(env.steps[idx][player]["observation"])


def build_pairwise(
    label_rows: list[dict[str, Any]],
    eps: float = 1e-6,
    top_quantile: float = 0.20,
    bottom_quantile: float = 0.20,
) -> tuple[list[dict[str, Any]], list[str]]:
    by_state: dict[str, list[dict[str, Any]]] = {}
    for row in label_rows:
        by_state.setdefault(str(row["state_id"]), []).append(row)
    pairs: list[dict[str, Any]] = []
    low_signal: list[str] = []
    for state_id, rows in by_state.items():
        rows = sorted(rows, key=lambda r: float(r["delta_reward"]))
        if len(rows) < 2 or float(rows[-1]["delta_reward"]) - float(rows[0]["delta_reward"]) <= eps:
            low_signal.append(state_id)
            continue
        bottom_count = max(1, math.ceil(len(rows) * bottom_quantile))
        top_count = max(1, math.ceil(len(rows) * top_quantile))
        top_start = max(0, len(rows) - top_count)
        bottom_end = min(len(rows), bottom_count)
        if top_start <= bottom_end:
            split_needed = bottom_end - top_start + 1
            top_start = min(len(rows), max(1, top_start + split_needed))
            top_start = min(len(rows), top_start)
        bottom_rows = rows[:bottom_end]
        top_rows = rows[top_start:]
        if not bottom_rows or not top_rows:
            low_signal.append(state_id)
            continue

        state_pairs = 0
        for winner in top_rows:
            for loser in bottom_rows:
                if float(winner["delta_reward"]) <= float(loser["delta_reward"]) + eps:
                    continue
                delta = float(winner["delta_reward"]) - float(loser["delta_reward"])
                pairs.append(
                    {
                        "state_id": state_id,
                        "winner_label_id": winner["label_id"],
                        "loser_label_id": loser["label_id"],
                        "winner_reward": winner["delta_reward"],
                        "loser_reward": loser["delta_reward"],
                        "winner_state_id": winner["state_id"],
                        "loser_state_id": loser["state_id"],
                        "delta": delta,
                        "top2_delta": float(winner["top2_delta"]) - float(loser["top2_delta"]),
                    }
                )
                state_pairs += 1
        if state_pairs == 0:
            low_signal.append(state_id)
    return pairs, low_signal


def build_dry_run_plan(out: Path) -> None:
    write(
        out / "standard_dry_run_plan.md",
        """# Standard-RealLabel Dry Run Plan

Status: `NOT_STARTED`

The smoke job only repairs label signal. Full Standard-RealLabel remains locked
until the user explicitly approves it.
""",
    )


def label_one_candidate(
    bank: AgentBank,
    state: dict[str, Any],
    candidate: dict[str, Any],
    horizon_steps: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    force_step = int(state["step"])
    episode_steps = force_step + horizon_steps
    policy = str(state["source_policy"])
    nplayers = int(state["nplayers"])
    seed = int(state["seed"])
    control_env, _ = run_replay(bank, policy, nplayers, seed, episode_steps)
    forced_env, forced_agent = run_replay(bank, policy, nplayers, seed, episode_steps, force_step=force_step, candidate=candidate)
    before_obs = make_obs_copy(state["obs"])
    control_t1 = get_obs_at_or_before(control_env, force_step + 1)
    forced_t1 = get_obs_at_or_before(forced_env, force_step + 1)
    control_final = get_obs_at_or_before(control_env, episode_steps - 1)
    forced_final = get_obs_at_or_before(forced_env, episode_steps - 1)
    components = shaped_reward(before_obs, control_final, forced_final, candidate, nplayers)
    trace = {
        "state_id": state["state_id"],
        "step": force_step,
        "candidate": {
            "mission_type": candidate.get("mission_type"),
            "mission_profile": candidate.get("mission_profile"),
            "source_ids": candidate.get("source_ids"),
            "target_id": candidate.get("target_id"),
            "send_ships": candidate.get("send_ships"),
        },
        "forced_applied": bool(forced_agent and forced_agent.applied),
        "forced_action": forced_agent.action if forced_agent else None,
        "t1_control": trace_snapshot(control_t1, candidate, nplayers),
        "t1_forced": trace_snapshot(forced_t1, candidate, nplayers),
        "t1_diff": snapshot_diff(
            trace_snapshot(control_t1, candidate, nplayers),
            trace_snapshot(forced_t1, candidate, nplayers),
            candidate=candidate,
        ),
        "final_control": trace_snapshot(control_final, candidate, nplayers),
        "final_forced": trace_snapshot(forced_final, candidate, nplayers),
        "final_diff": snapshot_diff(
            trace_snapshot(control_final, candidate, nplayers),
            trace_snapshot(forced_final, candidate, nplayers),
            candidate=candidate,
        ),
    }
    label = {
        "label_id": stable_id({"state": state["state_id"], "candidate": candidate}),
        "state_id": state["state_id"],
        "seed": seed,
        "step": force_step,
        "nplayers": nplayers,
        "source_policy": policy,
        "mission_type": candidate.get("mission_type"),
        "mission_profile": candidate.get("mission_profile", candidate.get("mission_type")),
        "source_ids": json.dumps(candidate.get("source_ids", [])),
        "target_id": candidate.get("target_id"),
        "send_ships": json.dumps(candidate.get("send_ships", [])),
        "eta_min": candidate.get("eta_min"),
        "eta_max": candidate.get("eta_max"),
        "forced_applied": bool(forced_agent and forced_agent.applied),
        **components,
    }
    return label, trace


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="SHA-X1 RealLabel smoke / smoke-v2 signal repair.")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--max-states", type=int, default=None)
    ap.add_argument("--missions-per-state", type=int, default=None)
    ap.add_argument("--horizon-steps", type=int, default=None)
    ap.add_argument("--max-forced-labels", type=int, default=None)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    start = time.time()
    repo = Path(args.repo_root).resolve()
    cfg = json.loads((repo / args.config).read_text(encoding="utf-8"))
    out = repo / (args.output_dir or cfg.get("output_dir", "experiments/sha_x1_real_label_v1_smoke"))
    out.mkdir(parents=True, exist_ok=True)
    gpu = ensure_l40s()
    random.seed(int(cfg.get("random_seed", 20260610)))

    max_states = int(args.max_states or cfg.get("max_states", 64))
    state_min_missions = int(cfg.get("state_min_missions", 16))
    state_max_missions = int(cfg.get("state_max_missions", 32))
    missions_per_state = int(args.missions_per_state or cfg.get("missions_per_state", state_min_missions))
    missions_per_state = max(state_min_missions, min(state_max_missions, missions_per_state))
    horizon_cfg = args.horizon_steps or cfg.get("horizon_steps", 360)
    if isinstance(horizon_cfg, list):
        horizon_choices = [int(x) for x in horizon_cfg]
    else:
        horizon_choices = [int(horizon_cfg)]
    if not horizon_choices:
        horizon_choices = [360]
    max_forced_labels = int(args.max_forced_labels or cfg.get("max_forced_labels", max_states * missions_per_state))
    episode_steps = int(cfg.get("episode_steps", 520))
    sample_steps = [int(x) for x in cfg.get("sample_steps", [0, 20, 60, 100, 160, 220])]
    policies = list(cfg.get("source_policies", ["old_s1"]))
    players = [int(x) for x in cfg.get("players", [2, 4])]
    seeds = [int(x) for x in cfg.get("seeds", [2026061001, 2026061002])]
    pairwise_top_quantile = float(cfg.get("pairwise_top_quantile", 0.20))
    pairwise_bottom_quantile = float(cfg.get("pairwise_bottom_quantile", 0.20))
    state_resample_bonus_states = int(cfg.get("state_resample_bonus_states", 0))
    state_resample_rounds = int(cfg.get("state_resample_rounds", 0))
    target_state_count = max_states + max(0, state_resample_bonus_states)

    states: list[dict[str, Any]] = []
    errors: list[str] = []
    label_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    state_signal_status: dict[str, str] = {}
    bank = AgentBank(repo, dict(cfg["package_paths"]))
    partial_checkpoint_every_states = int(cfg.get("partial_checkpoint_every_states", 2))
    last_partial_state_count = -1
    partial_write_in_progress = False

    def write_partial_checkpoint(reason: str) -> None:
        nonlocal last_partial_state_count, partial_write_in_progress
        if partial_write_in_progress:
            return
        partial_write_in_progress = True
        try:
            partial_pair_rows, partial_low_signal_states = build_pairwise(
                label_rows,
                eps=1e-6,
                top_quantile=pairwise_top_quantile,
                bottom_quantile=pairwise_bottom_quantile,
            )
            rewards = [float(r["delta_reward"]) for r in label_rows]
            mean_delta = sum(rewards) / len(rewards) if rewards else 0.0
            label_std = math.sqrt(sum((r - mean_delta) ** 2 for r in rewards) / len(rewards)) if rewards else 0.0
            forced_rate = (sum(1 for r in label_rows if r["forced_applied"]) / len(label_rows)) if label_rows else 0.0
            nonzero_delta_rate = (sum(1 for r in rewards if abs(r) > 1e-6) / len(rewards)) if rewards else 0.0
            mission_profiles = sorted({str(r.get("mission_profile")) for r in label_rows})
            mission_types = sorted({str(r.get("mission_type")) for r in label_rows})
            partial_summary = {
                "status": "PARTIAL",
                "reason": reason,
                "states_collected": len(states),
                "real_labels": len(label_rows),
                "trace_rows": len(trace_rows),
                "pairwise_rows": len(partial_pair_rows),
                "forced_applied_rate": forced_rate,
                "nonzero_delta_rate": nonzero_delta_rate,
                "mean_delta_reward": mean_delta,
                "label_std": label_std,
                "mission_types": mission_types,
                "mission_profiles": mission_profiles,
                "low_signal_states": len(partial_low_signal_states),
                "elapsed_sec": time.time() - start,
                "errors": errors[-50:],
                "full_standard": "not_started",
                "kaggle_submission": "not_started",
                "head_node_python": "not_used_by_this_job",
            }
            save_json(out / "partial_checkpoint.json", partial_summary)
            save_json(out / "real_label_smoke_partial_report.json", partial_summary)
            write(out / "real_label_smoke_partial_report.md", "# RealLabel Smoke Partial Report\n\n" + bullets(partial_summary) + "\n")
            write_csv(out / "real_label_sample_partial.csv", label_rows)
            write(out / "real_label_sample_partial.jsonl", "\n".join(json.dumps(r, sort_keys=True) for r in label_rows) + ("\n" if label_rows else ""))
            write_csv(out / "pairwise_sample_partial.csv", partial_pair_rows)
            write(out / "trace_diff_audit_partial.jsonl", "\n".join(json.dumps(r, sort_keys=True) for r in trace_rows) + ("\n" if trace_rows else ""))
            trace_summary = {
                "status": "PARTIAL",
                "reason": reason,
                "trace_rows": len(trace_rows),
                "forced_applied_count": sum(1 for t in trace_rows if t["forced_applied"]),
                "t1_nonempty_diff_count": sum(1 for t in trace_rows if any(v not in (0, {}, None) for v in t["t1_diff"].values())),
                "final_nonempty_diff_count": sum(1 for t in trace_rows if any(v not in (0, {}, None) for v in t["final_diff"].values())),
            }
            write(out / "trace_diff_audit_partial.md", "# Trace Diff Audit Partial\n\n" + bullets(trace_summary) + "\n\nSee `trace_diff_audit_partial.jsonl` for partial trace snapshots.\n")
            label_report = {
                "status": "PARTIAL",
                "reason": reason,
                "real_label_count": len(label_rows),
                "states": len(states),
                "mission_types": mission_types,
                "mission_profiles": mission_profiles,
                "forced_applied_count": sum(1 for r in label_rows if r["forced_applied"]),
                "forced_applied_rate": forced_rate,
                "error_count": len(errors),
                "mean_delta_reward": mean_delta,
                "std_delta_reward": label_std,
            }
            write(out / "label_quality_partial.md", "# Label Quality Partial\n\n" + bullets(label_report) + "\n")
            pair_report = {
                "status": "PARTIAL",
                "reason": reason,
                "pairwise_rows": len(partial_pair_rows),
                "states_with_labels": len({r["state_id"] for r in label_rows}),
                "states_with_pairs": len({r["state_id"] for r in partial_pair_rows}),
                "low_signal_states": len(partial_low_signal_states),
                "non_tie_pairs": len(partial_pair_rows),
                "pairwise_top_quantile": pairwise_top_quantile,
                "pairwise_bottom_quantile": pairwise_bottom_quantile,
            }
            write(out / "pairwise_quality_partial.md", "# Pairwise Quality Partial\n\n" + bullets(pair_report) + "\n")
            last_partial_state_count = len(state_signal_status)
        finally:
            partial_write_in_progress = False

    def handle_partial_signal(signum: int, _frame: Any) -> None:
        errors.append(f"partial_signal:{signum}")
        write_partial_checkpoint(f"signal_{signum}")
        raise SystemExit(124)

    signal.signal(signal.SIGTERM, handle_partial_signal)
    signal.signal(signal.SIGINT, handle_partial_signal)

    def collect_states(state_cap: int, seed_offset: int = 0) -> None:
        for policy in policies:
            for nplayers in players:
                for seed in seeds:
                    if len(states) >= state_cap:
                        return
                    adjusted_seed = int(seed + seed_offset)
                    recorder = RecordingAgent(
                        bank.get(policy),
                        repo,
                        policy,
                        nplayers,
                        adjusted_seed,
                        sample_steps,
                        state_cap - len(states),
                        missions_per_state,
                        states,
                    )
                    try:
                        env = make_env(nplayers, adjusted_seed, episode_steps)
                        agents = [recorder] + [bank.get(policy) for _ in range(nplayers - 1)]
                        env.run(agents)
                        errors.extend(recorder.errors)
                    except Exception as exc:
                        errors.append(f"sample:{policy}:{nplayers}:{adjusted_seed}:{type(exc).__name__}:{exc}")

    try:
        for resample_round in range(max(1, state_resample_rounds + 1)):
            collect_states(target_state_count, seed_offset=resample_round * 10000)
            if len(states) >= target_state_count:
                break

        progress_every = int(cfg.get("progress_every_labels", 12))
        for state in states[:target_state_count]:
            if len(label_rows) >= max_forced_labels:
                break
            before_count = len(label_rows)
            state_horizon = random.choice(horizon_choices)
            for idx, candidate in enumerate(state["candidates"][:missions_per_state]):
                if len(label_rows) >= max_forced_labels:
                    break
                try:
                    label, trace = label_one_candidate(bank, state, candidate, state_horizon)
                    label["candidate_index"] = idx
                    trace["candidate_index"] = idx
                    label_rows.append(label)
                    trace_rows.append(trace)
                    if progress_every > 0 and len(label_rows) % progress_every == 0:
                        print(
                            "REAL_LABEL_SMOKE_V2_PROGRESS "
                            + json.dumps({"labels": len(label_rows), "state_id": state["state_id"], "step": state["step"]}, sort_keys=True),
                            flush=True,
                        )
                except Exception as exc:
                    errors.append(f"forced:{state['state_id']}:{idx}:{type(exc).__name__}:{exc}")
            rewards = [float(r["delta_reward"]) for r in label_rows[before_count:] if r["state_id"] == state["state_id"]]
            state_signal_status[state["state_id"]] = "LOW_SIGNAL_STATE" if len(rewards) < 2 or max(rewards) - min(rewards) <= 1e-6 else "SIGNAL_STATE"
            processed_states = len(state_signal_status)
            if partial_checkpoint_every_states > 0 and processed_states != last_partial_state_count:
                if processed_states % partial_checkpoint_every_states == 0:
                    write_partial_checkpoint(f"processed_states_{processed_states}")

        pair_rows, low_signal_states = build_pairwise(
            label_rows,
            eps=1e-6,
            top_quantile=pairwise_top_quantile,
            bottom_quantile=pairwise_bottom_quantile,
        )
        forced_rate = (sum(1 for r in label_rows if r["forced_applied"]) / len(label_rows)) if label_rows else 0.0
        rewards = [float(r["delta_reward"]) for r in label_rows]
        nonzero_delta_rate = (sum(1 for r in rewards if abs(r) > 1e-6) / len(rewards)) if rewards else 0.0
        mean_delta = sum(rewards) / len(rewards) if rewards else 0.0
        label_std = math.sqrt(sum((r - mean_delta) ** 2 for r in rewards) / len(rewards)) if rewards else 0.0
        mission_profiles = sorted({str(r.get("mission_profile")) for r in label_rows})
        mission_types = sorted({str(r.get("mission_type")) for r in label_rows})

        for row in label_rows:
            row["state_signal_status"] = state_signal_status.get(str(row["state_id"]), "UNKNOWN")

        write_csv(out / "real_label_sample.csv", label_rows)
        write(out / "real_label_sample.jsonl", "\n".join(json.dumps(r, sort_keys=True) for r in label_rows) + ("\n" if label_rows else ""))
        write_csv(out / "pairwise_sample.csv", pair_rows)
        write(out / "trace_diff_audit.jsonl", "\n".join(json.dumps(r, sort_keys=True) for r in trace_rows) + ("\n" if trace_rows else ""))
        save_json(out / "sampled_states.json", states)

        output_gb = sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) / 1e9
        pass_gate = (
            bool(trace_rows)
            and nonzero_delta_rate >= float(cfg.get("min_nonzero_delta_rate", 0.30))
            and len(pair_rows) >= int(cfg.get("min_pairwise_rows", 500))
            and label_std > float(cfg.get("min_label_std", 1e-6))
            and len(mission_profiles) >= int(cfg.get("min_mission_profiles", 5))
            and output_gb < float(cfg.get("max_output_gb", 3.0))
        )
        status = "REAL_LABEL_SMOKE_V2_PASS" if pass_gate else "REAL_LABEL_SMOKE_V2_BLOCKED_SIGNAL"
        summary = {
            "status": status,
            "host": gpu["host"],
            "device": gpu["device"],
            "states": len(states),
            "target_state_count": target_state_count,
            "real_labels": len(label_rows),
            "pairwise_rows": len(pair_rows),
            "forced_applied_rate": forced_rate,
            "nonzero_delta_rate": nonzero_delta_rate,
            "mean_delta_reward": mean_delta,
            "label_std": label_std,
            "mission_types": mission_types,
            "mission_profiles": mission_profiles,
            "low_signal_states": len(low_signal_states),
            "pairwise_top_quantile": pairwise_top_quantile,
            "pairwise_bottom_quantile": pairwise_bottom_quantile,
            "output_gb": output_gb,
            "elapsed_sec": time.time() - start,
            "errors": errors[:50],
            "kaggle_submission": "not_started",
            "full_standard": "not_started",
            "full_v4_training": "not_started",
            "new_rollout": "not_started",
            "head_node_python": "not_used_by_this_job",
        }
        save_json(out / "real_label_smoke_v2_report.json", summary)
        save_json(out / "real_label_smoke_report.json", summary)

        write(out / "real_label_smoke_v2_report.md", "# RealLabel Smoke v2 Report\n\n" + bullets(summary) + "\n")
        write(out / "real_label_smoke_report.md", "# RealLabel Smoke Report\n\n" + bullets(summary) + "\n")
        trace_summary = {
            "trace_rows": len(trace_rows),
            "forced_applied_count": sum(1 for t in trace_rows if t["forced_applied"]),
            "t1_nonempty_diff_count": sum(1 for t in trace_rows if any(v not in (0, {}, None) for v in t["t1_diff"].values())),
            "final_nonempty_diff_count": sum(1 for t in trace_rows if any(v not in (0, {}, None) for v in t["final_diff"].values())),
        }
        write(out / "trace_diff_audit.md", "# Trace Diff Audit\n\n" + bullets(trace_summary) + "\n\nSee `trace_diff_audit.jsonl` for per-candidate trace snapshots.\n")
        reward_report = {
            "real_label_count": len(label_rows),
            "nonzero_delta_rate": nonzero_delta_rate,
            "mean_delta_reward": mean_delta,
            "label_std": label_std,
            "components": [
                "planet_count_delta",
                "production_delta",
                "ship_delta",
                "target_capture",
                "source_overdrain_penalty",
                "rank_delta",
                "top2_delta",
                "win_proxy",
                "leader_help_penalty",
            ],
        }
        write(out / "reward_component_report.md", "# Reward Component Report\n\n" + bullets(reward_report) + "\n")
        label_report = {
            "real_label_count": len(label_rows),
            "states": len(states),
            "mission_types": mission_types,
            "mission_profiles": mission_profiles,
            "forced_applied_count": sum(1 for r in label_rows if r["forced_applied"]),
            "forced_applied_rate": forced_rate,
            "error_count": len(errors),
            "mean_delta_reward": mean_delta,
            "std_delta_reward": label_std,
        }
        write(out / "label_quality_report.md", "# Label Quality Report\n\n" + bullets(label_report) + "\n")
        pair_report = {
            "pairwise_rows": len(pair_rows),
            "states_with_labels": len({r["state_id"] for r in label_rows}),
            "states_with_pairs": len({r["state_id"] for r in pair_rows}),
            "low_signal_states": len(low_signal_states),
            "non_tie_pairs": len(pair_rows),
            "pairwise_top_quantile": pairwise_top_quantile,
            "pairwise_bottom_quantile": pairwise_bottom_quantile,
            "state_target_count": target_state_count,
        }
        write(out / "pairwise_quality_report.md", "# Pairwise Quality Report\n\n" + bullets(pair_report) + "\n")
        blockers = []
        if nonzero_delta_rate < float(cfg.get("min_nonzero_delta_rate", 0.30)):
            blockers.append("nonzero_delta_rate below threshold")
        if len(pair_rows) < int(cfg.get("min_pairwise_rows", 500)):
            blockers.append("pairwise_rows below threshold")
        if label_std <= float(cfg.get("min_label_std", 1e-6)):
            blockers.append("label_std too small")
        if len(mission_profiles) < int(cfg.get("min_mission_profiles", 5)):
            blockers.append("mission profile coverage too narrow")
        if len(low_signal_states) > 0:
            blockers.append(f"low_signal_states={len(low_signal_states)}")
        write(
            out / "go_no_go_for_standard.md",
            "# Go / No-Go For Standard-RealLabel\n\n"
            f"- verdict: `{'GO_SMOKE_SIGNAL_REPAIRED' if pass_gate else 'NO_GO_STANDARD'}`\n"
            f"- blockers: `{blockers}`\n"
            "- full_standard: `not_started`\n"
            "- kaggle_submission: `not_started`\n"
            "- head_node_python: `not_used_by_this_job`\n",
        )
        write(out / "tiny_train_report.md", "# Tiny Train Report\n\nStatus: `not_started_in_v2_signal_repair_smoke`\n")
        write(out / "export_report.md", "# Export Report\n\nStatus: `not_started_in_v2_signal_repair_smoke`\n")
        write(out / "storage_check_report.md", f"# Storage Check Report\n\n- output_gb: `{output_gb}`\n- limit_gb: `{cfg.get('max_output_gb', 3.0)}`\n")
        build_dry_run_plan(out)
        print(status, json.dumps(summary, sort_keys=True))
    finally:
        bank.close()


if __name__ == "__main__":
    main()
