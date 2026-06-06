from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .candidates import CandidateMission, MISSION_TYPES
from .geometry import BOARD_CENTER, SUN_RADIUS, angle_between, crosses_sun, distance, estimate_eta, estimate_fleet_speed, point_segment_distance
from .heuristics import HeuristicParams, default_v1_params, nearby_enemy_pressure, reserve_for_planet
from .obs_parser import GameState, PlanetState, parse_observation


FEATURE_NAMES = [
    "step_norm", "remaining_steps_norm", "num_players", "my_planet_count", "my_total_ships_planets",
    "my_total_ships_fleets", "my_total_production", "enemy_best_total_strength", "enemy_best_production",
    "enemy_weakest_total_strength", "enemy_weakest_production", "leader_gap_strength", "my_rank_by_strength",
    "my_rank_by_production", "neutral_total_production", "neutral_high_prod_count", "is_2p", "is_4p",
    "phase_early", "phase_mid", "phase_late", "phase_endgame", "src_ships", "src_production", "src_radius",
    "src_is_home", "src_is_comet", "src_surplus_after_reserve", "src_reserve_required", "src_fraction_sent",
    "src_remaining_after_send", "src_nearest_enemy_planet_dist", "src_nearest_enemy_fleet_dist",
    "src_incoming_enemy_before_30", "src_incoming_friendly_before_30", "src_threat_margin",
    "src_defense_lost_by_sending", "num_sources", "combined_ships_sent", "combined_surplus",
    "min_source_surplus", "max_source_fraction_sent", "mean_source_fraction_sent", "target_exists",
    "target_owner_mine", "target_owner_neutral", "target_owner_enemy", "target_owner_leader",
    "target_owner_weakest_enemy", "target_ships_now", "target_production", "target_radius", "target_is_comet",
    "target_comet_remaining_steps", "target_high_prod_flag", "target_nearby_enemy_pressure",
    "target_nearby_friendly_pressure", "target_cluster_value", "target_dist_to_my_nearest_planet",
    "target_dist_to_enemy_nearest_planet", "send_ships_total", "send_fraction_total", "fleet_speed_est",
    "eta_min", "eta_max", "eta_spread", "distance_current", "distance_eta_projected", "angle_sin",
    "angle_cos", "sun_crossing_flag", "sun_path_margin", "board_exit_risk", "path_clearance_min",
    "accidental_collision_risk", "arrives_before_end", "target_owner_eta_mine", "target_owner_eta_neutral",
    "target_owner_eta_enemy", "target_ships_eta_est", "target_production_growth_to_eta",
    "friendly_incoming_before_eta", "enemy_incoming_before_eta", "enemy_incoming_near_eta",
    "largest_competing_owner_ships_eta", "second_competing_owner_ships_eta", "combat_margin_eta",
    "capture_success_proxy", "overkill_ratio", "underkill_gap", "third_party_steal_risk", "leader_help_risk",
    *[f"mt_{mission}" for mission in MISSION_TYPES],
]


def _zero_features() -> dict[str, float]:
    return {name: 0.0 for name in FEATURE_NAMES}


def _player_totals(state: GameState) -> dict[int, dict[str, float]]:
    totals = {player: {"ships": 0.0, "planets": 0.0, "production": 0.0} for player in range(state.num_players)}
    for planet in state.planets:
        if planet.owner >= 0:
            row = totals.setdefault(planet.owner, {"ships": 0.0, "planets": 0.0, "production": 0.0})
            row["ships"] += float(planet.ships)
            row["planets"] += 1.0
            row["production"] += float(planet.production)
    for fleet in state.fleets:
        if fleet.owner >= 0:
            totals.setdefault(fleet.owner, {"ships": 0.0, "planets": 0.0, "production": 0.0})["ships"] += float(fleet.ships)
    return totals


def _strength(row: dict[str, float]) -> float:
    return row["ships"] + row["production"] * 18.0 + row["planets"] * 12.0


def _nearest_distance(planets: list[PlanetState], x: float, y: float) -> float:
    if not planets:
        return 100.0
    return min(distance(x, y, planet.x, planet.y) for planet in planets)


def _primary_entities(state: GameState, candidate: CandidateMission) -> tuple[PlanetState | None, PlanetState | None]:
    planet_by_id = {planet.id: planet for planet in state.planets}
    source = planet_by_id.get(candidate.source_ids[0]) if candidate.source_ids else None
    target = planet_by_id.get(candidate.target_id) if candidate.target_id is not None else None
    return source, target


def _incoming_to_planet(state: GameState, target: PlanetState, eta: int, owner: int | None = None, window: int = 0) -> float:
    total = 0.0
    for fleet in state.fleets:
        if owner is not None and fleet.owner != owner:
            continue
        fleet_eta = estimate_eta(distance(fleet.x, fleet.y, target.x, target.y), max(fleet.ships, 1), 6.0)
        if fleet_eta <= eta + window:
            total += float(fleet.ships)
    return total


def _initial_planet_by_id(state: GameState) -> dict[int, list[Any]]:
    return {int(raw[0]): raw for raw in state.raw_observation.get("initial_planets", [])}


def _future_planet_position(state: GameState, planet: PlanetState, future_step: int) -> tuple[float, float]:
    if planet.id in state.comet_planet_ids:
        for group in state.raw_observation.get("comets", []):
            if planet.id not in group.get("planet_ids", []):
                continue
            idx = group.get("planet_ids", []).index(planet.id)
            path_index = int(group.get("path_index", 0)) + max(0, future_step - state.step)
            paths = group.get("paths", [])
            if idx < len(paths) and 0 <= path_index < len(paths[idx]):
                return float(paths[idx][path_index][0]), float(paths[idx][path_index][1])
        return planet.x, planet.y
    raw = _initial_planet_by_id(state).get(planet.id)
    if raw is None:
        return planet.x, planet.y
    initial_x = float(raw[2])
    initial_y = float(raw[3])
    radius = float(raw[4])
    dx = initial_x - BOARD_CENTER[0]
    dy = initial_y - BOARD_CENTER[1]
    orbital_radius = math.hypot(dx, dy)
    if orbital_radius + radius >= 50.0:
        return initial_x, initial_y
    initial_angle = math.atan2(dy, dx)
    angle = initial_angle + state.angular_velocity * future_step
    return (
        BOARD_CENTER[0] + orbital_radius * math.cos(angle),
        BOARD_CENTER[1] + orbital_radius * math.sin(angle),
    )


def _board_exit_risk(source: PlanetState, theta: float, speed: float, eta: int) -> float:
    # A cheap segment-level bound: if any sampled point on the intended segment leaves the
    # 100x100 board, the launch is unsafe even before collision checks.
    steps = max(2, min(12, int(eta)))
    start_x = source.x + math.cos(theta) * (source.radius + 0.1)
    start_y = source.y + math.sin(theta) * (source.radius + 0.1)
    for idx in range(1, steps + 1):
        t = idx / steps
        x = start_x + math.cos(theta) * speed * eta * t
        y = start_y + math.sin(theta) * speed * eta * t
        if x < 0.0 or x > 100.0 or y < 0.0 or y > 100.0:
            return 1.0
    return 0.0


def _path_clearance(state: GameState, source: PlanetState, target: PlanetState) -> tuple[float, float]:
    min_clearance = 999.0
    for planet in state.planets:
        if planet.id in (source.id, target.id):
            continue
        clearance = point_segment_distance(planet.x, planet.y, source.x, source.y, target.x, target.y) - planet.radius
        min_clearance = min(min_clearance, clearance)
    risk = 1.0 if min_clearance < 0.75 else 0.0
    return min_clearance if min_clearance != 999.0 else 100.0, risk


def _project_target_combat_owner(
    state: GameState,
    target: PlanetState,
    eta: int,
    total_send: float,
) -> tuple[int, float, float, float, float, float]:
    by_owner: Counter[int] = Counter()
    near_enemy = 0.0
    for fleet in state.fleets:
        fleet_eta = estimate_eta(distance(fleet.x, fleet.y, target.x, target.y), max(fleet.ships, 1), 6.0)
        if fleet_eta <= eta:
            by_owner[fleet.owner] += float(fleet.ships)
        if fleet.owner != state.my_id and abs(fleet_eta - eta) <= 8:
            near_enemy += float(fleet.ships)
    growth = float(target.production * eta) if target.owner >= 0 else 0.0
    owner_strength: Counter[int] = Counter(by_owner)
    if target.owner >= 0:
        owner_strength[target.owner] += float(target.ships) + growth
    else:
        owner_strength[-1] += float(target.ships)
    owner_strength[state.my_id] += total_send
    ordered = sorted(owner_strength.items(), key=lambda item: item[1], reverse=True)
    if not ordered:
        return -1, float(target.ships), growth, 0.0, 0.0, near_enemy
    winner, top = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else 0.0
    survivor = max(0.0, top - second)
    if top == second:
        winner = -1
        survivor = 0.0
    largest = ordered[0][1]
    second_largest = ordered[1][1] if len(ordered) > 1 else 0.0
    return int(winner), survivor, growth, largest, second_largest, near_enemy


def _comet_remaining(state: GameState, target: PlanetState | None) -> float:
    if target is None or target.id not in state.comet_planet_ids:
        return 0.0
    for group in state.raw_observation.get("comets", []):
        if target.id in group.get("planet_ids", []):
            idx = int(group.get("path_index", 0))
            paths = group.get("paths", [])
            if paths:
                return float(max(0, len(paths[0]) - idx))
    return 0.0


def _is_initial_home(state: GameState, planet: PlanetState) -> bool:
    initial_ids = {int(raw[0]) for raw in state.raw_observation.get("initial_planets", [])}
    if planet.id not in initial_ids:
        return False
    # Official observations copy initial_planets before assigning homes, so the
    # initial owner is usually neutral. Approximate home by the symmetric group
    # assignment used by the environment: 4p uses base+j, 2p uses base/base+3.
    group_base = (planet.id // 4) * 4
    expected_ids = {group_base + state.my_id} if state.num_players >= 4 else {group_base, group_base + 3}
    return planet.owner == state.my_id and planet.id in expected_ids


def featurize_candidate(
    obs: dict[str, Any],
    config: dict[str, Any],
    candidate: CandidateMission,
    params: HeuristicParams | None = None,
) -> dict[str, float]:
    params = params or default_v1_params()
    state = parse_observation(obs, config)
    features = _zero_features()
    source, target = _primary_entities(state, candidate)
    totals = _player_totals(state)
    mine = totals.get(state.my_id, {"ships": 0.0, "planets": 0.0, "production": 0.0})
    enemies = [(pid, row) for pid, row in totals.items() if pid != state.my_id]
    enemy_sorted = sorted(enemies, key=lambda item: _strength(item[1]), reverse=True)
    enemy_weak = sorted(enemies, key=lambda item: _strength(item[1]))[0] if enemies else (None, {"ships": 0.0, "planets": 0.0, "production": 0.0})
    my_strength = _strength(mine)
    strengths = sorted([_strength(row) for row in totals.values()], reverse=True)
    prods = sorted([row["production"] for row in totals.values()], reverse=True)
    features.update({
        "step_norm": state.step / max(1.0, state.episode_steps),
        "remaining_steps_norm": max(0.0, state.episode_steps - state.step) / max(1.0, state.episode_steps),
        "num_players": float(state.num_players),
        "my_planet_count": mine["planets"],
        "my_total_ships_planets": sum(float(p.ships) for p in state.my_planets),
        "my_total_ships_fleets": sum(float(f.ships) for f in state.fleets if f.owner == state.my_id),
        "my_total_production": mine["production"],
        "enemy_best_total_strength": _strength(enemy_sorted[0][1]) if enemy_sorted else 0.0,
        "enemy_best_production": enemy_sorted[0][1]["production"] if enemy_sorted else 0.0,
        "enemy_weakest_total_strength": _strength(enemy_weak[1]),
        "enemy_weakest_production": enemy_weak[1]["production"],
        "leader_gap_strength": (strengths[0] - my_strength) if strengths else 0.0,
        "my_rank_by_strength": float(1 + sum(value > my_strength for value in strengths)),
        "my_rank_by_production": float(1 + sum(value > mine["production"] for value in prods)),
        "neutral_total_production": sum(float(p.production) for p in state.neutral_planets),
        "neutral_high_prod_count": float(sum(1 for p in state.neutral_planets if p.production >= 4)),
        "is_2p": 1.0 if state.num_players <= 2 else 0.0,
        "is_4p": 1.0 if state.num_players >= 4 else 0.0,
        "phase_early": 1.0 if state.step < 100 else 0.0,
        "phase_mid": 1.0 if 100 <= state.step < 350 else 0.0,
        "phase_late": 1.0 if 350 <= state.step < state.episode_steps - 40 else 0.0,
        "phase_endgame": 1.0 if state.episode_steps - state.step <= 40 else 0.0,
    })
    total_send = float(sum(candidate.send_ships))
    planet_by_id = {p.id: p for p in state.my_planets}
    source_rows = [planet_by_id[source_id] for source_id in candidate.source_ids if source_id in planet_by_id]
    send_by_source: dict[int, float] = {}
    for source_id, sent in zip(candidate.source_ids, candidate.send_ships):
        send_by_source[source_id] = send_by_source.get(source_id, 0.0) + float(sent)
    source_surpluses = [float(p.ships - reserve_for_planet(state, p, params)) for p in source_rows]
    if source is not None:
        reserve = float(reserve_for_planet(state, source, params))
        sent0 = float(candidate.send_ships[0]) if candidate.send_ships else 0.0
        features.update({
            "src_ships": float(source.ships),
            "src_production": float(source.production),
            "src_radius": float(source.radius),
            "src_is_home": 1.0 if _is_initial_home(state, source) else 0.0,
            "src_is_comet": 1.0 if source.id in state.comet_planet_ids else 0.0,
            "src_surplus_after_reserve": float(source.ships - reserve),
            "src_reserve_required": reserve,
            "src_fraction_sent": sent0 / max(1.0, float(source.ships)),
            "src_remaining_after_send": float(source.ships) - sent0,
            "src_nearest_enemy_planet_dist": _nearest_distance(state.enemy_planets, source.x, source.y),
            "src_nearest_enemy_fleet_dist": min([distance(source.x, source.y, f.x, f.y) for f in state.fleets if f.owner != state.my_id] or [100.0]),
            "src_incoming_enemy_before_30": sum(float(f.ships) for f in state.fleets if f.owner != state.my_id and estimate_eta(distance(f.x, f.y, source.x, source.y), max(f.ships, 1), 6.0) <= 30),
            "src_incoming_friendly_before_30": sum(float(f.ships) for f in state.fleets if f.owner == state.my_id and estimate_eta(distance(f.x, f.y, source.x, source.y), max(f.ships, 1), 6.0) <= 30),
            "src_threat_margin": float(source.ships) - sum(float(f.ships) for f in state.fleets if f.owner != state.my_id and estimate_eta(distance(f.x, f.y, source.x, source.y), max(f.ships, 1), 6.0) <= 30),
            "src_defense_lost_by_sending": sent0,
        })
    features.update({
        "num_sources": float(len(candidate.source_ids)),
        "combined_ships_sent": total_send,
        "combined_surplus": sum(source_surpluses),
        "min_source_surplus": min(source_surpluses) if source_surpluses else 0.0,
        "max_source_fraction_sent": max([min(1.0, send_by_source.get(src.id, 0.0) / max(1.0, float(src.ships))) for src in source_rows] or [0.0]),
        "mean_source_fraction_sent": sum([min(1.0, send_by_source.get(src.id, 0.0) / max(1.0, float(src.ships))) for src in source_rows] or [0.0]) / max(1, len(source_rows)),
    })
    if target is not None:
        leader_id = enemy_sorted[0][0] if enemy_sorted else None
        weakest_id = enemy_weak[0]
        features.update({
            "target_exists": 1.0,
            "target_owner_mine": 1.0 if target.owner == state.my_id else 0.0,
            "target_owner_neutral": 1.0 if target.owner == -1 else 0.0,
            "target_owner_enemy": 1.0 if target.owner not in (-1, state.my_id) else 0.0,
            "target_owner_leader": 1.0 if target.owner == leader_id else 0.0,
            "target_owner_weakest_enemy": 1.0 if target.owner == weakest_id else 0.0,
            "target_ships_now": float(target.ships),
            "target_production": float(target.production),
            "target_radius": float(target.radius),
            "target_is_comet": 1.0 if target.id in state.comet_planet_ids else 0.0,
            "target_comet_remaining_steps": _comet_remaining(state, target),
            "target_high_prod_flag": 1.0 if target.production >= 4 else 0.0,
            "target_nearby_enemy_pressure": nearby_enemy_pressure(state, target),
            "target_nearby_friendly_pressure": sum(max(0.0, p.ships / max(1.0, distance(target.x, target.y, p.x, p.y))) for p in state.my_planets if distance(target.x, target.y, p.x, p.y) <= 24),
            "target_cluster_value": sum(float(p.production) for p in state.planets if distance(target.x, target.y, p.x, p.y) <= 18),
            "target_dist_to_my_nearest_planet": _nearest_distance(state.my_planets, target.x, target.y),
            "target_dist_to_enemy_nearest_planet": _nearest_distance(state.enemy_planets, target.x, target.y),
        })
    if source is not None and target is not None:
        gap = distance(source.x, source.y, target.x, target.y)
        speed = estimate_fleet_speed(max(int(total_send), 1), 6.0)
        eta = candidate.eta_max
        future_x, future_y = _future_planet_position(state, target, state.step + eta)
        projected_gap = distance(source.x, source.y, future_x, future_y)
        growth = float(target.production * eta) if target.owner != -1 else 0.0
        friendly_in = _incoming_to_planet(state, target, eta, owner=state.my_id)
        enemy_in = sum(_incoming_to_planet(state, target, eta, owner=pid) for pid in range(state.num_players) if pid != state.my_id)
        owner_eta, target_ships_eta, projected_growth, largest_owner, second_owner, enemy_near_eta = _project_target_combat_owner(
            state,
            target,
            eta,
            total_send,
        )
        required_eta = float(target.ships) + growth + enemy_in
        margin = total_send + friendly_in - required_eta
        theta = angle_between(source.x, source.y, target.x, target.y)
        clearance, accidental_risk = _path_clearance(state, source, target)
        sun_margin = point_segment_distance(BOARD_CENTER[0], BOARD_CENTER[1], source.x, source.y, target.x, target.y) - SUN_RADIUS
        features.update({
            "send_ships_total": total_send,
            "send_fraction_total": total_send / max(1.0, sum(float(p.ships) for p in source_rows) or float(source.ships)),
            "fleet_speed_est": speed,
            "eta_min": float(candidate.eta_min),
            "eta_max": float(candidate.eta_max),
            "eta_spread": float(candidate.eta_max - candidate.eta_min),
            "distance_current": gap,
            "distance_eta_projected": projected_gap,
            "angle_sin": math.sin(theta),
            "angle_cos": math.cos(theta),
            "sun_crossing_flag": 1.0 if crosses_sun(source.x, source.y, target.x, target.y) else 0.0,
            "sun_path_margin": sun_margin,
            "board_exit_risk": max(1.0 if candidate.safety_flags.get("board_exit_risk") else 0.0, _board_exit_risk(source, theta, speed, eta)),
            "path_clearance_min": clearance,
            "accidental_collision_risk": max(1.0 if candidate.safety_flags.get("accidental_collision_risk") else 0.0, accidental_risk),
            "arrives_before_end": 1.0 if state.step + candidate.eta_max < state.episode_steps else 0.0,
            "target_owner_eta_mine": 1.0 if owner_eta == state.my_id else 0.0,
            "target_owner_eta_neutral": 1.0 if owner_eta == -1 else 0.0,
            "target_owner_eta_enemy": 1.0 if owner_eta not in (-1, state.my_id) else 0.0,
            "target_ships_eta_est": target_ships_eta,
            "target_production_growth_to_eta": projected_growth,
            "friendly_incoming_before_eta": friendly_in,
            "enemy_incoming_before_eta": enemy_in,
            "enemy_incoming_near_eta": enemy_near_eta,
            "largest_competing_owner_ships_eta": largest_owner,
            "second_competing_owner_ships_eta": second_owner,
            "combat_margin_eta": margin,
            "capture_success_proxy": 1.0 if margin > 0 else 0.0,
            "overkill_ratio": max(0.0, margin) / max(1.0, required_eta),
            "underkill_gap": max(0.0, -margin),
            "third_party_steal_risk": min(1.0, enemy_in / max(1.0, total_send + friendly_in)),
            "leader_help_risk": 1.0 if target is not None and target.owner == enemy_weak[0] and enemy_sorted and enemy_sorted[0][0] != enemy_weak[0] else 0.0,
        })
    for mission in MISSION_TYPES:
        features[f"mt_{mission}"] = 1.0 if candidate.mission_type == mission else 0.0
    for key, value in list(features.items()):
        if not math.isfinite(float(value)):
            features[key] = 0.0
    return features


def feature_vector(features: dict[str, float]) -> list[float]:
    return [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
