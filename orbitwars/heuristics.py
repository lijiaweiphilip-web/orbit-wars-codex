from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from .geometry import angle_between, crosses_sun, distance, estimate_eta
from .obs_parser import GameState, PlanetState, parse_observation


@dataclass
class HeuristicParams:
    aggression_2p: float = 1.35
    aggression_4p: float = 0.8
    reserve_base: int = 8
    reserve_pressure_factor: float = 1.0
    reserve_value_factor: float = 0.7
    neutral_priority: float = 1.2
    enemy_denial_bonus: float = 0.5
    travel_penalty: float = 0.7
    third_party_risk: float = 1.1
    min_send_margin: int = 2
    max_actions_per_turn: int = 5
    planet_value_factor: float = 1.8
    enemy_pressure_radius: float = 24.0
    max_target_candidates: int = 8
    final_step_horizon: int = 30
    ignore_comets: bool = True
    early_game_steps: int = 90
    early_max_eta: int = 18
    mid_max_eta: int = 28
    post_capture_buffer: float = 1.25
    home_guard_bias: float = 1.4
    neutral_ship_weight: float = 0.45
    enemy_ship_weight: float = 0.8
    reinforcement_bonus: float = 0.5
    opening_expand_steps: int = 60
    opening_expand_max_actions: int = 1
    opening_neutral_max_eta: int = 14
    opening_neutral_buffer: int = 2
    opening_min_home_ships_left: int = 8
    opening_4p_expand_steps: int = 40
    opening_4p_neutral_max_eta: int = 10
    opening_4p_min_home_ships_left: int = 14
    opening_4p_enemy_pressure_cap: float = 1.6
    recovery_4p_expand_steps: int = 90
    recovery_4p_planet_cap: int = 1
    recovery_4p_neutral_max_eta: int = 14
    recovery_4p_min_home_ships_left: int = 12
    four_player_regroup_steps: int = 110
    four_player_safe_planet_cap: int = 3
    four_player_enemy_attack_margin: float = 1.25
    four_player_caution_steps: int = 140
    four_player_caution_enemy_count: int = 3
    four_player_caution_enemy_risk: float = 0.45
    four_player_midgame_reserve_start: int = 50
    four_player_midgame_reserve_end: int = 110
    four_player_midgame_reserve_bonus: int = 8
    four_player_conversion_start: int = 50
    four_player_conversion_end: int = 110
    four_player_conversion_planet_floor: int = 3
    four_player_conversion_neutral_bonus: float = 0.75
    four_player_conversion_enemy_bonus: float = 0.65
    four_player_conversion_enemy_ship_ratio: float = 0.65
    four_player_conversion_far_enemy_penalty: float = 0.55
    four_player_conversion_lead_ship_margin: float = 0.98
    four_player_conversion_lead_neutral_bonus: float = 1.3
    four_player_conversion_lead_enemy_bonus: float = 1.0
    four_player_conversion_target_max_eta: int = 14
    four_player_conversion_send_buffer: float = 1.15
    four_player_conversion_target_pressure_penalty: float = 2.0
    four_player_conversion_safe_pressure_cap: float = 2.4
    four_player_conversion_safe_target_bonus: float = 1.0
    four_player_conversion_enemy_closer_penalty: float = 1.2
    four_player_conversion_me_closer_bonus: float = 0.8
    four_player_conversion_break_even_end: int = 75
    four_player_conversion_break_even_score_floor: float = -55.0
    four_player_conversion_break_even_min_production: int = 4
    four_player_conversion_break_even_source_margin: float = 1.2
    four_player_conversion_deny_score_floor: float = -115.0
    four_player_conversion_deny_min_production: int = 4
    four_player_conversion_deny_source_margin: float = 1.8
    four_player_conversion_deny_ship_ratio: float = 0.45
    four_player_conversion_deny_pressure_cap: float = 8.0
    four_player_conversion_late_end: int = 100
    four_player_conversion_late_score_floor: float = -110.0
    four_player_conversion_late_min_production: int = 5
    four_player_conversion_late_source_margin: float = 1.6
    four_player_conversion_late_ship_ratio: float = 0.45
    four_player_conversion_late_pressure_cap: float = 10.0

    @classmethod
    def from_mapping(cls, values: dict[str, float | int | bool]) -> "HeuristicParams":
        params = cls()
        for key, value in values.items():
            if hasattr(params, key):
                setattr(params, key, value)
        return params


def default_v0_params() -> HeuristicParams:
    return HeuristicParams(
        aggression_2p=1.05,
        aggression_4p=0.65,
        reserve_base=8,
        neutral_priority=1.4,
        enemy_denial_bonus=0.2,
        travel_penalty=0.9,
        third_party_risk=1.4,
        max_actions_per_turn=3,
    )


def default_v1_params() -> HeuristicParams:
    return HeuristicParams(
        aggression_2p=1.35,
        aggression_4p=0.7,
        reserve_base=8,
        reserve_pressure_factor=1.2,
        neutral_priority=1.35,
        enemy_denial_bonus=0.35,
        travel_penalty=0.85,
        third_party_risk=1.35,
        min_send_margin=3,
        max_actions_per_turn=4,
        post_capture_buffer=1.35,
        home_guard_bias=1.6,
        early_max_eta=18,
        mid_max_eta=24,
        recovery_4p_expand_steps=110,
        recovery_4p_planet_cap=3,
        recovery_4p_neutral_max_eta=16,
        recovery_4p_min_home_ships_left=11,
        four_player_regroup_steps=120,
        four_player_safe_planet_cap=4,
        four_player_enemy_attack_margin=1.4,
        four_player_caution_steps=150,
        four_player_caution_enemy_count=3,
        four_player_caution_enemy_risk=0.55,
        four_player_midgame_reserve_start=50,
        four_player_midgame_reserve_end=110,
        four_player_midgame_reserve_bonus=6,
        four_player_conversion_start=50,
        four_player_conversion_end=110,
        four_player_conversion_planet_floor=3,
        four_player_conversion_neutral_bonus=0.9,
        four_player_conversion_enemy_bonus=0.75,
        four_player_conversion_enemy_ship_ratio=0.6,
        four_player_conversion_far_enemy_penalty=0.7,
        four_player_conversion_lead_ship_margin=0.98,
        four_player_conversion_lead_neutral_bonus=1.45,
        four_player_conversion_lead_enemy_bonus=1.1,
        four_player_conversion_target_max_eta=14,
        four_player_conversion_send_buffer=1.15,
        four_player_conversion_target_pressure_penalty=2.4,
        four_player_conversion_safe_pressure_cap=2.2,
        four_player_conversion_safe_target_bonus=1.2,
        four_player_conversion_enemy_closer_penalty=1.4,
        four_player_conversion_me_closer_bonus=0.9,
        four_player_conversion_break_even_end=75,
        four_player_conversion_break_even_score_floor=-55.0,
        four_player_conversion_break_even_min_production=4,
        four_player_conversion_break_even_source_margin=1.2,
        four_player_conversion_deny_score_floor=-115.0,
        four_player_conversion_deny_min_production=4,
        four_player_conversion_deny_source_margin=1.8,
        four_player_conversion_deny_ship_ratio=0.45,
        four_player_conversion_deny_pressure_cap=8.0,
        four_player_conversion_late_end=100,
        four_player_conversion_late_score_floor=-110.0,
        four_player_conversion_late_min_production=5,
        four_player_conversion_late_source_margin=1.6,
        four_player_conversion_late_ship_ratio=0.45,
        four_player_conversion_late_pressure_cap=10.0,
    )


def load_params(path: str | Path | None) -> HeuristicParams:
    if path is None:
        return default_v1_params()
    candidate = Path(path)
    if not candidate.exists():
        return default_v1_params()
    return HeuristicParams.from_mapping(json.loads(candidate.read_text(encoding="utf-8")))


def nearby_enemy_pressure(state: GameState, source: PlanetState) -> float:
    pressure = 0.0
    for planet in state.enemy_planets:
        gap = distance(source.x, source.y, planet.x, planet.y)
        if gap <= 0:
            continue
        if gap <= 24:
            pressure += max(0.0, planet.ships / gap)
    for fleet in state.fleets:
        if fleet.owner != state.my_id:
            gap = distance(source.x, source.y, fleet.x, fleet.y)
            if gap <= 18:
                pressure += fleet.ships / max(gap, 1.0)
    return pressure


def reserve_for_planet(state: GameState, source: PlanetState, params: HeuristicParams) -> int:
    value_term = source.production * params.reserve_value_factor
    pressure_term = nearby_enemy_pressure(state, source) * params.reserve_pressure_factor
    home_bias = params.home_guard_bias if _is_home_planet(state, source) else 1.0
    reserve = params.reserve_base + value_term + pressure_term
    if (
        state.num_players >= 4
        and params.four_player_midgame_reserve_start <= state.step <= params.four_player_midgame_reserve_end
        and len(state.my_planets) >= 3
        and len(_alive_enemy_players(state)) >= 2
    ):
        reserve += params.four_player_midgame_reserve_bonus
    return int(math.ceil(reserve * home_bias))


def required_ships(target: PlanetState, params: HeuristicParams) -> int:
    weight = params.neutral_ship_weight if target.owner == -1 else params.enemy_ship_weight
    return int(math.ceil(target.ships * weight + params.min_send_margin))


def _neutral_expand_action(
    state: GameState,
    params: HeuristicParams,
    *,
    expand_window: int,
    max_eta: int,
    min_home_left: int,
    score_prod_weight: float,
    score_ship_weight: float,
    pressure_penalty: float,
    max_planets: int | None = None,
) -> list[list[float | int]]:
    if state.step > expand_window:
        return []
    if not state.neutral_planets or not state.my_planets:
        return []
    if max_planets is not None and len(state.my_planets) > max_planets:
        return []
    my_planets = sorted(state.my_planets, key=lambda p: (p.production, p.ships), reverse=True)
    source = my_planets[0]
    pressure = nearby_enemy_pressure(state, source)
    if state.num_players >= 4 and pressure > params.opening_4p_enemy_pressure_cap:
        return []
    reserve = reserve_for_planet(state, source, params)
    safe_floor = max(reserve, min_home_left)
    available = source.ships - safe_floor
    if available <= params.opening_neutral_buffer:
        return []

    candidates: list[tuple[float, PlanetState, int]] = []
    for target in state.neutral_planets:
        gap = distance(source.x, source.y, target.x, target.y)
        eta = estimate_eta(gap, max(available, 1), 6.0)
        if eta > max_eta:
            continue
        launch_angle = angle_between(source.x, source.y, target.x, target.y)
        projected_x = source.x + math.cos(launch_angle) * gap
        projected_y = source.y + math.sin(launch_angle) * gap
        if crosses_sun(source.x, source.y, projected_x, projected_y):
            continue
        need = target.ships + params.opening_neutral_buffer
        if available < need:
            continue
        score = target.production * score_prod_weight - gap - target.ships * score_ship_weight
        score -= pressure * pressure_penalty
        candidates.append((score, target, need))

    if not candidates:
        return []
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, target, need = candidates[0]
    theta = angle_between(source.x, source.y, target.x, target.y)
    send = min(available, need)
    if send <= params.min_send_margin:
        return []
    return [[source.id, float(theta), int(send)]]


def _opening_expand_action(state: GameState, params: HeuristicParams) -> list[list[float | int]]:
    is_four_player = state.num_players >= 4
    return _neutral_expand_action(
        state,
        params,
        expand_window=params.opening_4p_expand_steps if is_four_player else params.opening_expand_steps,
        max_eta=params.opening_4p_neutral_max_eta if is_four_player else params.opening_neutral_max_eta,
        min_home_left=params.opening_4p_min_home_ships_left if is_four_player else params.opening_min_home_ships_left,
        score_prod_weight=6.5 if is_four_player else 8.0,
        score_ship_weight=1.9 if is_four_player else 1.5,
        pressure_penalty=2.0 if is_four_player else 0.0,
    )


def _recovery_expand_action(state: GameState, params: HeuristicParams) -> list[list[float | int]]:
    if state.num_players < 4:
        return []
    return _neutral_expand_action(
        state,
        params,
        expand_window=params.recovery_4p_expand_steps,
        max_eta=params.recovery_4p_neutral_max_eta,
        min_home_left=params.recovery_4p_min_home_ships_left,
        score_prod_weight=7.0,
        score_ship_weight=1.7,
        pressure_penalty=1.2,
        max_planets=params.recovery_4p_planet_cap,
    )


def _is_home_planet(state: GameState, planet: PlanetState) -> bool:
    for initial in state.raw_observation.get("initial_planets", []):
        if int(initial[0]) == planet.id and int(initial[1]) == state.my_id:
            return True
    return False


def _planet_is_threatened(state: GameState, target: PlanetState, params: HeuristicParams) -> bool:
    return nearby_enemy_pressure(state, target) >= max(2.5, target.ships * 0.08)


def _max_eta_for_phase(state: GameState, params: HeuristicParams) -> int:
    remaining = state.episode_steps - state.step
    if state.step <= params.early_game_steps:
        return params.early_max_eta
    if remaining <= params.final_step_horizon:
        return max(6, remaining - 1)
    return params.mid_max_eta


def _should_regroup_four_player(state: GameState, params: HeuristicParams) -> bool:
    if state.num_players < 4:
        return False
    if state.step > params.four_player_regroup_steps:
        return False
    return len(state.my_planets) <= params.four_player_safe_planet_cap


def _alive_enemy_players(state: GameState) -> set[int]:
    alive: set[int] = set()
    for planet in state.enemy_planets:
        alive.add(planet.owner)
    for fleet in state.fleets:
        if fleet.owner != state.my_id:
            alive.add(fleet.owner)
    return alive


def _territory_conversion_mode(state: GameState, params: HeuristicParams) -> bool:
    return (
        state.num_players >= 4
        and params.four_player_conversion_start <= state.step <= params.four_player_conversion_end
        and len(state.my_planets) >= params.four_player_conversion_planet_floor
        and len(_alive_enemy_players(state)) >= 2
    )


def _player_totals(state: GameState) -> dict[int, dict[str, float]]:
    totals: dict[int, dict[str, float]] = {}
    for player_id in range(state.num_players):
        totals[player_id] = {"planets": 0.0, "ships": 0.0}
    for planet in state.planets:
        if planet.owner >= 0:
            totals.setdefault(planet.owner, {"planets": 0.0, "ships": 0.0})
            totals[planet.owner]["planets"] += 1.0
            totals[planet.owner]["ships"] += float(planet.ships)
    for fleet in state.fleets:
        if fleet.owner >= 0:
            totals.setdefault(fleet.owner, {"planets": 0.0, "ships": 0.0})
            totals[fleet.owner]["ships"] += float(fleet.ships)
    return totals


def _is_midgame_leader(state: GameState, params: HeuristicParams) -> bool:
    if not _territory_conversion_mode(state, params):
        return False
    totals = _player_totals(state)
    mine = totals.get(state.my_id, {"planets": 0.0, "ships": 0.0})
    other_totals = [values for player_id, values in totals.items() if player_id != state.my_id]
    if not other_totals:
        return True
    best_other = max(other_totals, key=lambda values: (values["ships"], values["planets"]))
    if mine["ships"] < best_other["ships"] * params.four_player_conversion_lead_ship_margin:
        return False
    return (mine["ships"], mine["planets"]) >= (best_other["ships"], best_other["planets"])


def _best_other_player_id(state: GameState) -> int | None:
    totals = _player_totals(state)
    other_totals = [
        (player_id, values)
        for player_id, values in totals.items()
        if player_id != state.my_id
    ]
    if not other_totals:
        return None
    return max(other_totals, key=lambda item: (item[1]["ships"], item[1]["planets"], -item[0]))[0]


def _target_enemy_pressure(state: GameState, target: PlanetState) -> float:
    return nearby_enemy_pressure(state, target)


def _nearest_enemy_distance_to_target(state: GameState, target: PlanetState) -> float | None:
    enemy_gaps = [
        distance(target.x, target.y, enemy.x, enemy.y)
        for enemy in state.enemy_planets
        if enemy.owner != state.my_id
    ]
    if not enemy_gaps:
        return None
    return min(enemy_gaps)


def _nearest_enemy_owner_to_target(state: GameState, target: PlanetState) -> int | None:
    enemy_candidates = [
        (distance(target.x, target.y, enemy.x, enemy.y), enemy.owner)
        for enemy in state.enemy_planets
        if enemy.owner != state.my_id
    ]
    if not enemy_candidates:
        return None
    enemy_candidates.sort(key=lambda item: (item[0], item[1]))
    return enemy_candidates[0][1]


def _target_score(state: GameState, source: PlanetState, target: PlanetState, params: HeuristicParams) -> float:
    gap = distance(source.x, source.y, target.x, target.y)
    ships_needed = required_ships(target, params)
    eta = estimate_eta(gap, max(ships_needed, 1), 6.0)
    if eta > _max_eta_for_phase(state, params):
        return -1e9
    production_value = target.production * params.planet_value_factor
    neutral_bonus = params.neutral_priority if target.owner == -1 else 0.0
    enemy_bonus = params.enemy_denial_bonus * target.production if target.owner not in (-1, state.my_id) else 0.0
    reinforce_bonus = params.reinforcement_bonus * target.production if target.owner == state.my_id and _planet_is_threatened(state, target, params) else 0.0
    risk = 0.0
    alive_enemy_count = len(_alive_enemy_players(state))
    conversion_mode = _territory_conversion_mode(state, params)
    midgame_leader = _is_midgame_leader(state, params)
    if state.num_players >= 4 and target.owner not in (-1, state.my_id):
        risk += params.third_party_risk * 0.5
        if state.step <= params.four_player_caution_steps and alive_enemy_count >= params.four_player_caution_enemy_count:
            risk += target.production * params.four_player_caution_enemy_risk
    if target.is_comet and params.ignore_comets:
        return -1e9
    if state.episode_steps - state.step <= params.final_step_horizon:
        if eta >= state.episode_steps - state.step:
            return -1e9
    launch_angle = angle_between(source.x, source.y, target.x, target.y)
    projected_x = source.x + math.cos(launch_angle) * gap
    projected_y = source.y + math.sin(launch_angle) * gap
    if crosses_sun(source.x, source.y, projected_x, projected_y):
        risk += 100.0
    if target.owner == state.my_id and not _planet_is_threatened(state, target, params):
        return -1e9
    if _should_regroup_four_player(state, params) and target.owner not in (-1, state.my_id):
        ships_needed = required_ships(target, params)
        if source.ships < target.ships * params.four_player_enemy_attack_margin + ships_needed:
            return -1e9
        risk += params.third_party_risk * 1.5
    if conversion_mode:
        target_pressure = _target_enemy_pressure(state, target)
        if midgame_leader and target.owner != state.my_id:
            risk += target_pressure * params.four_player_conversion_target_pressure_penalty
            if target_pressure <= params.four_player_conversion_safe_pressure_cap:
                if target.owner == -1:
                    neutral_bonus += params.four_player_conversion_safe_target_bonus * max(1, target.production)
                else:
                    enemy_bonus += params.four_player_conversion_safe_target_bonus * max(1, target.production)
            nearest_enemy_gap = _nearest_enemy_distance_to_target(state, target)
            if nearest_enemy_gap is not None:
                if nearest_enemy_gap + 2.0 < gap:
                    risk += (gap - nearest_enemy_gap) * params.four_player_conversion_enemy_closer_penalty
                elif gap + 2.0 < nearest_enemy_gap:
                    if target.owner == -1:
                        neutral_bonus += (nearest_enemy_gap - gap) * params.four_player_conversion_me_closer_bonus * 0.2
                    else:
                        enemy_bonus += (nearest_enemy_gap - gap) * params.four_player_conversion_me_closer_bonus * 0.2
        if target.owner == -1:
            neutral_bonus += params.four_player_conversion_neutral_bonus * target.production
            if midgame_leader and eta <= params.four_player_conversion_target_max_eta:
                neutral_bonus += params.four_player_conversion_lead_neutral_bonus * max(1, target.production)
                neutral_bonus += max(0.0, 16.0 - target.ships) * 0.12
                risk -= min(target.ships * 0.25, 4.0)
        elif target.owner != state.my_id:
            if target.ships <= source.ships * params.four_player_conversion_enemy_ship_ratio:
                enemy_bonus += params.four_player_conversion_enemy_bonus * target.production
                if midgame_leader and eta <= params.four_player_conversion_target_max_eta:
                    enemy_bonus += params.four_player_conversion_lead_enemy_bonus * max(1, target.production)
                    enemy_bonus += max(0.0, 18.0 - target.ships) * 0.08
            else:
                risk += target.ships * params.four_player_conversion_far_enemy_penalty
            if midgame_leader and eta > params.four_player_conversion_target_max_eta:
                risk += gap * 0.5
    if target.owner != -1 and target.ships > source.ships * 0.9:
        risk += target.ships * 0.35
    return production_value + neutral_bonus + enemy_bonus + reinforce_bonus - gap * params.travel_penalty - ships_needed - risk


def _scored_targets_for_source(
    state: GameState,
    source: PlanetState,
    targets: list[PlanetState],
    committed_target_ids: set[int],
    params: HeuristicParams,
) -> list[tuple[float, PlanetState]]:
    return sorted(
        (
            (_target_score(state, source, target, params), target)
            for target in targets
            if target.id != source.id
            and (target.owner == state.my_id or target.id not in committed_target_ids)
        ),
        key=lambda item: item[0],
        reverse=True,
    )[: params.max_target_candidates]


def _allow_break_even_conversion_target(
    state: GameState,
    source: PlanetState,
    target: PlanetState,
    score: float,
    available: int,
    send_floor: int,
    params: HeuristicParams,
) -> bool:
    if state.num_players < 4:
        return False
    if not _territory_conversion_mode(state, params):
        return False
    if available < send_floor:
        return False
    gap = distance(source.x, source.y, target.x, target.y)
    eta = estimate_eta(gap, max(required_ships(target, params), 1), 6.0)
    if eta > params.four_player_conversion_target_max_eta:
        return False
    target_pressure = _target_enemy_pressure(state, target)
    is_midgame_leader = _is_midgame_leader(state, params)
    in_break_even_window = params.four_player_conversion_start <= state.step <= params.four_player_conversion_break_even_end
    in_late_window = params.four_player_conversion_break_even_end < state.step <= params.four_player_conversion_late_end
    if target.owner == -1:
        if not (is_midgame_leader and in_break_even_window):
            return False
        nearest_enemy_gap = _nearest_enemy_distance_to_target(state, target)
        if nearest_enemy_gap is not None and nearest_enemy_gap + 2.0 < gap:
            return False
        if target_pressure > params.four_player_conversion_safe_pressure_cap:
            return False
        if target.production < params.four_player_conversion_break_even_min_production:
            return False
        if score < params.four_player_conversion_break_even_score_floor:
            return False
        if available < int(math.ceil(send_floor * params.four_player_conversion_break_even_source_margin)):
            return False
        return True
    if target.owner == state.my_id:
        return False
    if is_midgame_leader and in_break_even_window:
        if target.owner != _best_other_player_id(state):
            return False
        if target_pressure > params.four_player_conversion_deny_pressure_cap:
            return False
        if target.production < params.four_player_conversion_deny_min_production:
            return False
        if score < params.four_player_conversion_deny_score_floor:
            return False
        if target.ships > source.ships * params.four_player_conversion_deny_ship_ratio:
            return False
        if available < int(math.ceil(send_floor * params.four_player_conversion_deny_source_margin)):
            return False
        return True
    if in_late_window:
        if target_pressure > params.four_player_conversion_late_pressure_cap:
            return False
        if target.production < params.four_player_conversion_late_min_production:
            return False
        if score < params.four_player_conversion_late_score_floor:
            return False
        if target.ships > source.ships * params.four_player_conversion_late_ship_ratio:
            return False
        if available < int(math.ceil(send_floor * params.four_player_conversion_late_source_margin)):
            return False
        return True
    return False


def choose_actions_with_trace(
    state: GameState,
    params: HeuristicParams,
    *,
    trace_top_n: int = 5,
) -> tuple[list[list[float | int]], dict[str, object]]:
    opening_actions = _opening_expand_action(state, params)
    if opening_actions:
        return opening_actions[: params.opening_expand_max_actions], {
            "step": state.step,
            "mode": "opening",
            "actions": opening_actions[: params.opening_expand_max_actions],
            "sources": [],
        }
    recovery_actions = _recovery_expand_action(state, params)
    if recovery_actions:
        return recovery_actions[: params.opening_expand_max_actions], {
            "step": state.step,
            "mode": "recovery",
            "actions": recovery_actions[: params.opening_expand_max_actions],
            "sources": [],
        }
    actions: list[list[float | int]] = []
    aggression = params.aggression_2p if state.num_players <= 2 else params.aggression_4p
    threatened_own = [planet for planet in state.my_planets if _planet_is_threatened(state, planet, params)]
    regrouping = _should_regroup_four_player(state, params)
    conversion_mode = _territory_conversion_mode(state, params)
    midgame_leader = _is_midgame_leader(state, params)
    neutral_targets = list(state.neutral_planets)
    enemy_targets = list(state.enemy_planets)
    if regrouping or conversion_mode:
        targets = threatened_own + neutral_targets + enemy_targets
    else:
        targets = threatened_own + [planet for planet in state.planets if planet.owner != state.my_id]
    committed_target_ids: set[int] = set()
    trace_sources: list[dict[str, object]] = []
    for source in sorted(state.my_planets, key=lambda planet: (planet.production, planet.ships), reverse=True):
        available = source.ships - reserve_for_planet(state, source, params)
        source_trace: dict[str, object] = {
            "source_id": source.id,
            "source_ships": source.ships,
            "available_start": available,
            "iterations": [],
        }
        if available <= params.min_send_margin:
            source_trace["skipped"] = "insufficient_available"
            trace_sources.append(source_trace)
            continue
        actions_from_source = 0
        while available > params.min_send_margin:
            scored_targets = _scored_targets_for_source(state, source, targets, committed_target_ids, params)
            iteration_trace: dict[str, object] = {
                "available_before": available,
                "top_candidates": [
                    {
                        "target_id": target.id,
                        "owner": target.owner,
                        "score": round(score, 3),
                        "ships": target.ships,
                        "production": target.production,
                    }
                    for score, target in scored_targets[:trace_top_n]
                ],
            }
            picked_target = False
            for score, target in scored_targets:
                send_floor = int(math.ceil(required_ships(target, params) * params.post_capture_buffer))
                if target.owner == state.my_id:
                    send_floor = max(send_floor, int(math.ceil(target.ships * 0.6)))
                if score <= 0 and not _allow_break_even_conversion_target(
                    state,
                    source,
                    target,
                    score,
                    available,
                    send_floor,
                    params,
                ):
                    continue
                if available < send_floor:
                    continue
                send = min(available, max(send_floor, int(math.ceil(available * aggression * 0.45))))
                if conversion_mode and midgame_leader and target.owner != state.my_id:
                    send = min(send, int(math.ceil(send_floor * params.four_player_conversion_send_buffer)))
                if send <= params.min_send_margin:
                    continue
                theta = angle_between(source.x, source.y, target.x, target.y)
                actions.append([source.id, float(theta), int(send)])
                iteration_trace["picked"] = {
                    "target_id": target.id,
                    "owner": target.owner,
                    "score": round(score, 3),
                    "send": int(send),
                }
                if target.owner != state.my_id:
                    committed_target_ids.add(target.id)
                available -= send
                actions_from_source += 1
                picked_target = True
                break
            if not picked_target:
                iteration_trace["picked"] = None
            source_trace["iterations"].append(iteration_trace)
            if not picked_target:
                break
            if len(actions) >= params.max_actions_per_turn:
                break
            if regrouping:
                break
            break
        trace_sources.append(source_trace)
        if len(actions) >= params.max_actions_per_turn:
            break
    return actions, {
        "step": state.step,
        "mode": "main",
        "conversion_mode": conversion_mode,
        "midgame_leader": midgame_leader,
        "regrouping": regrouping,
        "actions": actions,
        "sources": trace_sources,
    }


def choose_actions(state: GameState, params: HeuristicParams) -> list[list[float | int]]:
    actions, _ = choose_actions_with_trace(state, params)
    return actions


def make_agent(params: HeuristicParams):
    def agent(observation: dict, configuration: dict) -> list[list[float | int]]:
        state = parse_observation(observation, configuration)
        return choose_actions(state, params)

    return agent


def params_to_dict(params: HeuristicParams) -> dict[str, float | int | bool]:
    return asdict(params)
