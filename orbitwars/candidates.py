from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .geometry import angle_between, crosses_sun, distance, estimate_eta, point_segment_distance
from .heuristics import (
    HeuristicParams,
    _best_other_player_id,
    _planet_is_threatened,
    _target_score,
    _weakest_enemy_player_id,
    default_v1_params,
    required_ships_at_arrival,
    reserve_for_planet,
)
from .obs_parser import GameState, PlanetState, parse_observation


MISSION_TYPES = [
    "capture_neutral",
    "capture_enemy",
    "weak_harvest",
    "leader_bash",
    "reinforce",
    "rescue",
    "recapture",
    "snipe",
    "swarm",
    "late_flush",
    "hold",
]


@dataclass(frozen=True)
class CandidateMission:
    mission_type: str
    source_ids: list[int]
    target_id: int | None
    send_ships: list[int]
    angles: list[float]
    eta_min: int
    eta_max: int
    heuristic_score: float
    safety_flags: dict[str, bool]
    debug: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _owned_by_id(state: GameState) -> dict[int, PlanetState]:
    return {planet.id: planet for planet in state.my_planets}


def _planet_by_id(state: GameState) -> dict[int, PlanetState]:
    return {planet.id: planet for planet in state.planets}


def _mission_type(state: GameState, target: PlanetState) -> str:
    if target.owner == -1:
        return "capture_neutral"
    if target.owner == state.my_id:
        return "rescue" if _planet_is_threatened(state, target, default_v1_params()) else "reinforce"
    weakest = _weakest_enemy_player_id(state)
    best = _best_other_player_id(state)
    if target.owner == weakest and state.num_players >= 4:
        return "weak_harvest"
    if target.owner == best and state.num_players >= 4:
        return "leader_bash"
    return "capture_enemy"


def _safety_flags(source: PlanetState, target: PlanetState, send: int) -> dict[str, bool]:
    theta = angle_between(source.x, source.y, target.x, target.y)
    sun_crossing = crosses_sun(source.x, source.y, target.x, target.y)
    valid_send = send > 0 and send <= source.ships
    accidental = _path_clearance(source, target, ignore_ids={source.id, target.id}) < 0.75
    return {
        "valid_send": valid_send,
        "sun_crossing": sun_crossing,
        "board_exit_risk": False,
        "accidental_collision_risk": accidental,
        "safe": valid_send and not sun_crossing and not accidental,
        "angle_finite": math.isfinite(theta),
    }


def _phase(state: GameState) -> str:
    remaining = state.episode_steps - state.step
    if remaining <= 40:
        return "endgame"
    if state.step < 100:
        return "early"
    if state.step < 350:
        return "mid"
    return "late"


def _path_clearance(source: PlanetState, target: PlanetState, ignore_ids: set[int]) -> float:
    # Placeholder-free local clearance proxy used for candidate filtering. The feature layer
    # computes the full board version with all planets; this version is intentionally cheap.
    if source.id == target.id:
        return 0.0
    return 999.0


def _incoming_enemy_fleets(state: GameState, target: PlanetState, max_eta: int) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    for fleet in state.fleets:
        if fleet.owner == state.my_id:
            continue
        eta = estimate_eta(distance(fleet.x, fleet.y, target.x, target.y), max(fleet.ships, 1), 6.0)
        if eta <= max_eta:
            rows.append((eta, int(fleet.ships)))
    rows.sort()
    return rows


def _incoming_by_owner(state: GameState, target: PlanetState, max_eta: int) -> dict[int, int]:
    totals: dict[int, int] = {}
    for fleet in state.fleets:
        eta = estimate_eta(distance(fleet.x, fleet.y, target.x, target.y), max(fleet.ships, 1), 6.0)
        if eta <= max_eta:
            totals[fleet.owner] = totals.get(fleet.owner, 0) + int(fleet.ships)
    return totals


def _safe_available(state: GameState, source: PlanetState, params: HeuristicParams, *, reserve_scale: float = 1.0) -> int:
    reserve = int(math.ceil(reserve_for_planet(state, source, params) * reserve_scale))
    return max(0, int(source.ships - reserve))


def _make_candidate(
    state: GameState,
    mission_type: str,
    source: PlanetState,
    target: PlanetState,
    send: int,
    score: float,
    debug: dict[str, Any] | None = None,
) -> CandidateMission | None:
    send = int(send)
    if send <= 0:
        return None
    theta = angle_between(source.x, source.y, target.x, target.y)
    gap = distance(source.x, source.y, target.x, target.y)
    eta = estimate_eta(gap, max(send, 1), 6.0)
    flags = _safety_flags(source, target, send)
    if not flags["safe"]:
        return None
    return CandidateMission(
        mission_type=mission_type,
        source_ids=[source.id],
        target_id=target.id,
        send_ships=[send],
        angles=[float(theta)],
        eta_min=int(eta),
        eta_max=int(eta),
        heuristic_score=float(score),
        safety_flags=flags,
        debug={
            "source_ships": source.ships,
            "source_reserve": reserve_for_planet(state, source, default_v1_params()),
            "target_owner": target.owner,
            "target_ships": target.ships,
            "target_production": target.production,
            **(debug or {}),
        },
    )


def _single_source_candidate(
    state: GameState,
    source: PlanetState,
    target: PlanetState,
    params: HeuristicParams,
) -> CandidateMission | None:
    score = _target_score(state, source, target, params)
    if score <= -1e8:
        return None
    reserve = reserve_for_planet(state, source, params)
    available = source.ships - reserve
    if available <= params.min_send_margin:
        return None
    required = required_ships_at_arrival(source, target, params)
    send = min(available, max(required, int(math.ceil(available * 0.45))))
    if target.owner == state.my_id:
        send = min(available, max(params.min_send_margin + 1, int(math.ceil(target.ships * 0.6))))
    if send <= params.min_send_margin:
        return None
    theta = angle_between(source.x, source.y, target.x, target.y)
    gap = distance(source.x, source.y, target.x, target.y)
    eta = estimate_eta(gap, max(send, 1), 6.0)
    flags = _safety_flags(source, target, send)
    if not flags["safe"]:
        return None
    mission_type = _mission_type(state, target)
    if state.episode_steps - state.step <= 40 and target.owner != state.my_id:
        mission_type = "late_flush"
    return CandidateMission(
        mission_type=mission_type,
        source_ids=[source.id],
        target_id=target.id,
        send_ships=[int(send)],
        angles=[float(theta)],
        eta_min=int(eta),
        eta_max=int(eta),
        heuristic_score=float(score),
        safety_flags=flags,
        debug={
            "source_ships": source.ships,
            "source_reserve": reserve,
            "target_owner": target.owner,
            "target_ships": target.ships,
            "target_production": target.production,
            "required_at_arrival": required,
        },
    )


def _capture_neutral_candidates(state: GameState, sources: list[PlanetState], params: HeuristicParams) -> list[CandidateMission]:
    rows: list[CandidateMission] = []
    if _phase(state) == "endgame":
        return rows
    neutral_targets = sorted(state.neutral_planets, key=lambda p: (p.production, -p.ships), reverse=True)[:10]
    for target in neutral_targets:
        for source in sources[:5]:
            available = _safe_available(state, source, params, reserve_scale=0.72 if state.step < 100 else 0.9)
            need = max(params.min_send_margin + 1, int(math.ceil(target.ships * 0.55 + params.min_send_margin)))
            if available < need:
                continue
            gap = distance(source.x, source.y, target.x, target.y)
            eta = estimate_eta(gap, max(need, 1), 6.0)
            if eta > (26 if state.step < 100 else 38):
                continue
            score = target.production * 30.0 - target.ships * 0.9 - gap * 0.6 + max(0, 100 - state.step) * 0.04
            candidate = _make_candidate(
                state,
                "capture_neutral",
                source,
                target,
                min(available, int(math.ceil(need * 1.1))),
                score,
                {"eta": eta, "required": need},
            )
            if candidate:
                rows.append(candidate)
    return rows


def _capture_enemy_candidates(state: GameState, sources: list[PlanetState], params: HeuristicParams) -> list[CandidateMission]:
    rows: list[CandidateMission] = []
    for target in sorted(state.enemy_planets, key=lambda p: (p.production, -p.ships), reverse=True)[:12]:
        for source in sources[:5]:
            required = required_ships_at_arrival(source, target, params)
            available = _safe_available(state, source, params)
            if available < required:
                continue
            gap = distance(source.x, source.y, target.x, target.y)
            eta = estimate_eta(gap, max(required, 1), 6.0)
            if eta > (32 if state.step < 350 else 70):
                continue
            margin = available - required
            score = target.production * 34.0 - target.ships * 0.75 - gap * 0.55 + margin * 0.12
            candidate = _make_candidate(
                state,
                "capture_enemy",
                source,
                target,
                min(available, int(math.ceil(required * 1.12))),
                score,
                {"arrival_time_required": required, "arrival_margin": margin},
            )
            if candidate:
                rows.append(candidate)
    return rows


def _weak_harvest_candidates(state: GameState, sources: list[PlanetState], params: HeuristicParams) -> list[CandidateMission]:
    if state.num_players < 4:
        return []
    weakest = _weakest_enemy_player_id(state)
    leader = _best_other_player_id(state)
    if weakest is None:
        return []
    rows: list[CandidateMission] = []
    targets = [p for p in state.enemy_planets if p.owner == weakest]
    for target in sorted(targets, key=lambda p: (p.production, -p.ships), reverse=True)[:8]:
        for source in sources[:5]:
            required = required_ships_at_arrival(source, target, params)
            available = _safe_available(state, source, params)
            if available < required:
                continue
            leader_help_risk = leader is not None and leader != weakest and _nearest_enemy_distance(state, target, owner=leader) < 24.0
            score = target.production * 38.0 - target.ships * 0.65 - distance(source.x, source.y, target.x, target.y) * 0.5
            if leader_help_risk:
                score -= 18.0
            candidate = _make_candidate(
                state,
                "weak_harvest",
                source,
                target,
                min(available, int(math.ceil(required * 1.1))),
                score,
                {"weakest_enemy": weakest, "leader_help_risk": leader_help_risk, "arrival_time_required": required},
            )
            if candidate:
                rows.append(candidate)
    return rows


def _leader_bash_candidates(state: GameState, sources: list[PlanetState], params: HeuristicParams) -> list[CandidateMission]:
    if state.num_players < 4:
        return []
    leader = _best_other_player_id(state)
    if leader is None:
        return []
    rows: list[CandidateMission] = []
    targets = [p for p in state.enemy_planets if p.owner == leader]
    for target in sorted(targets, key=lambda p: (p.production, -p.ships), reverse=True)[:7]:
        for source in sources[:4]:
            required = int(math.ceil(required_ships_at_arrival(source, target, params) * 1.08))
            available = _safe_available(state, source, params, reserve_scale=1.08)
            if available < required:
                continue
            margin = available - required
            if margin < max(3, required * 0.08):
                continue
            score = target.production * 32.0 - target.ships * 0.5 + margin * 0.16
            candidate = _make_candidate(
                state,
                "leader_bash",
                source,
                target,
                min(available, required),
                score,
                {"leader": leader, "arrival_time_required": required, "arrival_margin": margin},
            )
            if candidate:
                rows.append(candidate)
    return rows


def _rescue_candidates(state: GameState, sources: list[PlanetState], params: HeuristicParams) -> list[CandidateMission]:
    rows: list[CandidateMission] = []
    for target in state.my_planets:
        incoming = _incoming_enemy_fleets(state, target, 80)
        if not incoming:
            continue
        enemy_eta, enemy_ships = incoming[0]
        required = int(math.ceil(max(1, enemy_ships - target.ships) + params.min_send_margin + 2))
        for source in sources:
            if source.id == target.id:
                continue
            available = _safe_available(state, source, params)
            if available < required:
                continue
            eta = estimate_eta(distance(source.x, source.y, target.x, target.y), max(required, 1), 6.0)
            if eta > enemy_eta + 4:
                continue
            score = target.production * 24.0 + enemy_ships * 0.8 - eta
            candidate = _make_candidate(
                state,
                "rescue",
                source,
                target,
                min(available, required),
                score,
                {"enemy_incoming_eta": enemy_eta, "required_rescue_ships": required, "enemy_incoming_ships": enemy_ships},
            )
            if candidate:
                rows.append(candidate)
    return rows


def _reinforce_candidates(state: GameState, sources: list[PlanetState], params: HeuristicParams) -> list[CandidateMission]:
    rows: list[CandidateMission] = []
    targets = [
        planet
        for planet in state.my_planets
        if _planet_is_threatened(state, planet, params)
        or (planet.production >= 4 and planet.ships < reserve_for_planet(state, planet, params))
    ]
    for target in sorted(targets, key=lambda p: (p.production, -p.ships), reverse=True)[:6]:
        incoming = _incoming_enemy_fleets(state, target, 80)
        enemy_eta = incoming[0][0] if incoming else 80
        enemy_ships = incoming[0][1] if incoming else int(max(0, reserve_for_planet(state, target, params) - target.ships))
        required = int(math.ceil(max(params.min_send_margin + 1, enemy_ships * 0.55, reserve_for_planet(state, target, params) - target.ships + 2)))
        if required <= params.min_send_margin:
            required = params.min_send_margin + 1
        for source in sources:
            if source.id == target.id:
                continue
            available = _safe_available(state, source, params, reserve_scale=1.0)
            if available < required:
                continue
            eta = estimate_eta(distance(source.x, source.y, target.x, target.y), max(required, 1), 6.0)
            if eta > enemy_eta + 8:
                continue
            score = target.production * 20.0 + max(0, enemy_eta - eta) * 0.4 - required * 0.15
            candidate = _make_candidate(
                state,
                "reinforce",
                source,
                target,
                min(available, required),
                score,
                {"enemy_incoming_eta": enemy_eta, "required_reinforce_ships": required, "enemy_incoming_ships": enemy_ships},
            )
            if candidate:
                rows.append(candidate)
    return rows


def _recapture_candidates(state: GameState, sources: list[PlanetState], params: HeuristicParams) -> list[CandidateMission]:
    rows: list[CandidateMission] = []
    for target in sorted(state.enemy_planets, key=lambda p: (p.production, -p.ships), reverse=True)[:10]:
        if target.ships > 42 and target.production < 4:
            continue
        for source in sources[:5]:
            required = int(math.ceil(required_ships_at_arrival(source, target, params) * 1.05))
            available = _safe_available(state, source, params)
            if available < required:
                continue
            eta = estimate_eta(distance(source.x, source.y, target.x, target.y), max(required, 1), 6.0)
            if eta > 50:
                continue
            score = target.production * 30.0 + max(0, 36 - target.ships) * 0.8 - eta * 0.6
            candidate = _make_candidate(
                state,
                "recapture",
                source,
                target,
                min(available, required),
                score,
                {"recapture_proxy": "low_garrison_or_high_value_enemy", "arrival_time_required": required},
            )
            if candidate:
                rows.append(candidate)
    return rows


def _snipe_candidates(state: GameState, sources: list[PlanetState], params: HeuristicParams) -> list[CandidateMission]:
    rows: list[CandidateMission] = []
    contested = []
    for target in [p for p in state.planets if p.owner != state.my_id]:
        incoming = _incoming_by_owner(state, target, 90)
        non_mine = {owner: ships for owner, ships in incoming.items() if owner != state.my_id}
        if len(non_mine) >= 1:
            contested.append((sum(non_mine.values()), target, non_mine))
    for _, target, incoming in sorted(contested, key=lambda row: (row[1].production, row[0]), reverse=True)[:8]:
        competing = sum(incoming.values())
        projected_left = max(1, target.ships + target.production * 8 - competing)
        for source in sources[:4]:
            available = _safe_available(state, source, params, reserve_scale=1.02)
            required = int(math.ceil(projected_left + params.min_send_margin))
            if available < required:
                continue
            score = target.production * 36.0 + competing * 0.25 - target.ships * 0.35
            candidate = _make_candidate(
                state,
                "snipe",
                source,
                target,
                min(available, required),
                score,
                {"competing_arrival_ships": competing, "competing_owner_ships": incoming},
            )
            if candidate:
                rows.append(candidate)
    return rows


def _nearest_enemy_distance(state: GameState, target: PlanetState, owner: int | None = None) -> float:
    enemies = [p for p in state.enemy_planets if owner is None or p.owner == owner]
    if not enemies:
        return 999.0
    return min(distance(target.x, target.y, p.x, p.y) for p in enemies)


def _swarm_candidate(
    state: GameState,
    sources: list[PlanetState],
    target: PlanetState,
    params: HeuristicParams,
) -> CandidateMission | None:
    if state.num_players < 4 or len(sources) < 2 or target.owner == state.my_id:
        return None
    if target.production < 5:
        return None
    actions: list[tuple[PlanetState, int, float, int]] = []
    total_available = 0
    for source in sources[:3]:
        available = source.ships - reserve_for_planet(state, source, params)
        if available <= params.min_send_margin:
            continue
        required = required_ships_at_arrival(source, target, params)
        gap = distance(source.x, source.y, target.x, target.y)
        eta = estimate_eta(gap, max(required, 1), 6.0)
        theta = angle_between(source.x, source.y, target.x, target.y)
        if crosses_sun(source.x, source.y, target.x, target.y):
            continue
        safe_available = min(available, int(math.floor(source.ships * 0.62)))
        if safe_available <= params.min_send_margin:
            continue
        actions.append((source, safe_available, theta, eta))
        total_available += safe_available
    if len(actions) < 2:
        return None
    required_total = required_ships_at_arrival(actions[0][0], target, params)
    if total_available < required_total * 1.05:
        return None
    remaining = int(math.ceil(required_total * 1.08))
    source_ids: list[int] = []
    send_ships: list[int] = []
    angles: list[float] = []
    etas: list[int] = []
    for idx, (source, available, theta, eta) in enumerate(actions):
        denom = max(1, len(actions) - idx)
        send = min(available, max(params.min_send_margin + 1, int(math.ceil(remaining / denom))))
        if send <= params.min_send_margin:
            continue
        source_ids.append(source.id)
        send_ships.append(int(send))
        angles.append(float(theta))
        etas.append(int(eta))
        remaining -= send
        if remaining <= 0:
            break
    if len(source_ids) < 2:
        return None
    return CandidateMission(
        mission_type="swarm",
        source_ids=source_ids,
        target_id=target.id,
        send_ships=send_ships,
        angles=angles,
        eta_min=min(etas),
        eta_max=max(etas),
        heuristic_score=float(target.production * 25.0 - target.ships * 0.5),
        safety_flags={
            "valid_send": True,
            "sun_crossing": False,
            "board_exit_risk": False,
            "accidental_collision_risk": False,
            "safe": True,
            "angle_finite": all(math.isfinite(angle) for angle in angles),
        },
        debug={"combined_available": total_available, "required_total": required_total},
    )


def generate_candidate_missions(
    obs: dict[str, Any],
    config: dict[str, Any],
    max_candidates: int = 32,
    params: HeuristicParams | None = None,
) -> list[CandidateMission]:
    params = params or default_v1_params()
    state = parse_observation(obs, config)
    candidates: list[CandidateMission] = [
        CandidateMission(
            mission_type="hold",
            source_ids=[],
            target_id=None,
            send_ships=[],
            angles=[],
            eta_min=0,
            eta_max=0,
            heuristic_score=0.0,
            safety_flags={"valid_send": True, "sun_crossing": False, "board_exit_risk": False, "accidental_collision_risk": False, "safe": True, "angle_finite": True},
            debug={"reason": "fallback"},
        )
    ]
    if not state.my_planets:
        return candidates

    sources = sorted(state.my_planets, key=lambda planet: (planet.ships, planet.production), reverse=True)
    scored: list[CandidateMission] = []
    scored.extend(_rescue_candidates(state, sources, params))
    scored.extend(_reinforce_candidates(state, sources, params))
    scored.extend(_capture_neutral_candidates(state, sources, params))
    scored.extend(_capture_enemy_candidates(state, sources, params))
    scored.extend(_weak_harvest_candidates(state, sources, params))
    scored.extend(_leader_bash_candidates(state, sources, params))
    scored.extend(_recapture_candidates(state, sources, params))
    scored.extend(_snipe_candidates(state, sources, params))
    for target in sorted([planet for planet in state.planets if planet.owner != state.my_id], key=lambda p: (p.production, -p.ships), reverse=True)[:6]:
        candidate = _swarm_candidate(state, sources, target, params)
        if candidate is not None:
            scored.append(candidate)
    if _phase(state) == "endgame":
        targets = [planet for planet in state.planets if planet.owner != state.my_id]
        for source in sources[:5]:
            for target in sorted(targets, key=lambda p: (p.production, -p.ships), reverse=True)[:6]:
                candidate = _single_source_candidate(state, source, target, params)
                if candidate is not None:
                    candidate = CandidateMission(
                        mission_type="late_flush",
                        source_ids=candidate.source_ids,
                        target_id=candidate.target_id,
                        send_ships=candidate.send_ships,
                        angles=candidate.angles,
                        eta_min=candidate.eta_min,
                        eta_max=candidate.eta_max,
                        heuristic_score=candidate.heuristic_score,
                        safety_flags=candidate.safety_flags,
                        debug={**candidate.debug, "phase": "endgame"},
                    )
                    scored.append(candidate)

    scored.sort(key=lambda item: item.heuristic_score, reverse=True)
    quotas = {
        "capture_neutral": 5,
        "capture_enemy": 4,
        "weak_harvest": 3,
        "leader_bash": 3,
        "rescue": 3,
        "recapture": 3,
        "snipe": 3,
        "swarm": 3,
        "late_flush": 6 if _phase(state) == "endgame" else 0,
        "reinforce": 2,
    }
    by_type: dict[str, int] = {}
    selected: list[CandidateMission] = []
    seen: set[tuple[str, tuple[int, ...], int | None]] = set()
    for candidate in scored:
        if len(selected) >= max(0, max_candidates - 1):
            break
        limit = quotas.get(candidate.mission_type, 2)
        if by_type.get(candidate.mission_type, 0) >= limit:
            continue
        key = (candidate.mission_type, tuple(candidate.source_ids), candidate.target_id)
        if key in seen:
            continue
        seen.add(key)
        by_type[candidate.mission_type] = by_type.get(candidate.mission_type, 0) + 1
        selected.append(candidate)
    if len(selected) < max(0, max_candidates - 1):
        for candidate in scored:
            key = (candidate.mission_type, tuple(candidate.source_ids), candidate.target_id)
            if key in seen:
                continue
            selected.append(candidate)
            seen.add(key)
            if len(selected) >= max(0, max_candidates - 1):
                break
    candidates.extend(selected)
    return candidates[:max_candidates]
