from orbitwars.heuristics import (
    _allow_break_even_conversion_target,
    _is_midgame_leader,
    _nearest_enemy_distance_to_target,
    _target_score,
    choose_actions_with_trace,
    default_v1_params,
)
from orbitwars.obs_parser import parse_observation


def test_is_midgame_leader_true_when_ship_and_planet_totals_lead():
    observation = {
        "step": 70,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 60, 3],
            [1, 0, 20, 10, 2, 30, 2],
            [6, 0, 15, 25, 2, 10, 1],
            [2, 1, 40, 10, 2, 55, 3],
            [3, 2, 60, 10, 2, 25, 2],
            [4, 3, 80, 10, 2, 20, 2],
            [5, -1, 30, 30, 2, 8, 2],
        ],
        "fleets": [[0, 0, 25, 12, 0.1, 0, 20], [1, 1, 42, 12, 0.1, 2, 5]],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})

    assert _is_midgame_leader(state, default_v1_params()) is True


def test_is_midgame_leader_false_when_best_other_has_more_ships():
    observation = {
        "step": 70,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 45, 3],
            [1, 0, 20, 10, 2, 18, 2],
            [6, 0, 15, 25, 2, 10, 1],
            [2, 1, 40, 10, 2, 60, 3],
            [3, 1, 50, 10, 2, 20, 2],
            [4, 2, 70, 10, 2, 20, 2],
            [5, 3, 90, 10, 2, 20, 2],
        ],
        "fleets": [[0, 1, 45, 12, 0.1, 2, 15]],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})

    assert _is_midgame_leader(state, default_v1_params()) is False


def test_target_score_prefers_safer_neutral_in_midgame_conversion():
    observation = {
        "step": 70,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 70, 3],
            [1, 0, 16, 12, 2, 22, 2],
            [2, 0, 14, 22, 2, 12, 1],
            [3, -1, 28, 10, 2, 8, 2],
            [4, -1, 28, 22, 2, 8, 2],
            [5, 1, 30, 10, 2, 40, 3],
            [6, 2, 70, 10, 2, 24, 2],
            [7, 3, 90, 10, 2, 20, 2],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})
    params = default_v1_params()
    source = state.my_planets[0]
    contested_target = next(planet for planet in state.neutral_planets if planet.id == 3)
    safer_target = next(planet for planet in state.neutral_planets if planet.id == 4)

    assert _target_score(state, source, safer_target, params) > _target_score(state, source, contested_target, params)


def test_nearest_enemy_distance_to_target_uses_closest_enemy_planet():
    observation = {
        "step": 70,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 70, 3],
            [1, 0, 16, 12, 2, 22, 2],
            [2, -1, 28, 10, 2, 8, 2],
            [3, 1, 30, 10, 2, 40, 3],
            [4, 2, 80, 10, 2, 24, 2],
            [5, 3, 90, 10, 2, 20, 2],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})
    target = next(planet for planet in state.neutral_planets if planet.id == 2)

    assert _nearest_enemy_distance_to_target(state, target) == 2.0


def test_choose_actions_with_trace_records_candidates_for_main_phase():
    observation = {
        "step": 70,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 70, 3],
            [1, 0, 16, 12, 2, 22, 2],
            [2, 0, 14, 22, 2, 12, 1],
            [3, -1, 28, 10, 2, 8, 2],
            [4, -1, 28, 22, 2, 8, 2],
            [5, 1, 30, 10, 2, 40, 3],
            [6, 2, 70, 10, 2, 24, 2],
            [7, 3, 90, 10, 2, 20, 2],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})
    actions, trace = choose_actions_with_trace(state, default_v1_params())

    assert trace["step"] == 70
    assert trace["mode"] == "main"
    assert trace["sources"]
    assert "top_candidates" in trace["sources"][0]["iterations"][0]
    assert trace["actions"] == actions


def test_choose_actions_skips_target_when_available_below_send_floor():
    observation = {
        "step": 70,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 31, 5],
            [1, -1, 14, 10, 2, 30, 4],
            [2, 1, 60, 10, 2, 20, 2],
            [3, 2, 70, 20, 2, 20, 2],
            [4, 3, 80, 30, 2, 20, 2],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})
    actions, trace = choose_actions_with_trace(state, default_v1_params())

    assert actions == []
    assert trace["sources"][0]["iterations"][0]["picked"] is None


def test_allow_break_even_conversion_target_for_safe_high_production_neutral():
    observation = {
        "step": 60,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 120, 5],
            [1, 0, 20, 10, 2, 50, 3],
            [6, 0, 18, 22, 2, 18, 2],
            [2, -1, 26, 10, 2, 48, 5],
            [3, 1, 70, 10, 2, 28, 3],
            [4, 2, 85, 20, 2, 24, 2],
            [5, 3, 80, 40, 2, 22, 2],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})
    params = default_v1_params()
    source = next(planet for planet in state.my_planets if planet.id == 0)
    target = next(planet for planet in state.neutral_planets if planet.id == 2)
    score = _target_score(state, source, target, params)
    send_floor = 34

    assert -55.0 <= score < 0
    assert _allow_break_even_conversion_target(state, source, target, score, 96, send_floor, params) is True


def test_allow_break_even_conversion_target_for_best_enemy_high_production_planet():
    observation = {
        "step": 60,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 135, 5],
            [1, 0, 20, 10, 2, 65, 3],
            [6, 0, 18, 22, 2, 22, 2],
            [2, 1, 34, 10, 2, 34, 4],
            [7, 1, 44, 16, 2, 80, 3],
            [3, 2, 85, 20, 2, 30, 3],
            [4, 3, 80, 40, 2, 28, 2],
            [5, -1, 70, 80, 2, 24, 2],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})
    params = default_v1_params()
    source = next(planet for planet in state.my_planets if planet.id == 0)
    target = next(planet for planet in state.enemy_planets if planet.id == 2)
    score = _target_score(state, source, target, params)
    send_floor = 42

    assert -115.0 <= score < 0
    assert _allow_break_even_conversion_target(state, source, target, score, 110, send_floor, params) is True


def test_allow_late_conversion_target_for_high_production_enemy_when_regrouping():
    observation = {
        "step": 90,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 230, 5],
            [1, 0, 16, 12, 2, 55, 3],
            [6, 0, 18, 22, 2, 30, 2],
            [8, 0, 22, 22, 2, 20, 1],
            [2, 1, 34, 10, 2, 75, 5],
            [7, 1, 92, 88, 2, 310, 4],
            [3, 2, 85, 20, 2, 150, 4],
            [4, 3, 80, 40, 2, 145, 4],
            [5, -1, 28, 18, 2, 40, 1],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})
    params = default_v1_params()
    source = next(planet for planet in state.my_planets if planet.id == 0)
    target = next(planet for planet in state.enemy_planets if planet.id == 2)
    score = _target_score(state, source, target, params)
    send_floor = 86

    assert not _is_midgame_leader(state, params)
    assert -90.0 <= score < 0
    assert _allow_break_even_conversion_target(state, source, target, score, 175, send_floor, params) is True


def test_late_conversion_does_not_unlock_low_production_neutral():
    observation = {
        "step": 90,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 230, 5],
            [1, 0, 16, 12, 2, 55, 3],
            [6, 0, 18, 22, 2, 30, 2],
            [8, 0, 22, 22, 2, 20, 1],
            [2, 1, 34, 10, 2, 75, 5],
            [7, 1, 92, 88, 2, 310, 4],
            [3, 2, 85, 20, 2, 150, 4],
            [4, 3, 80, 40, 2, 145, 4],
            [5, -1, 28, 18, 2, 40, 1],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 120})
    params = default_v1_params()
    source = next(planet for planet in state.my_planets if planet.id == 0)
    target = next(planet for planet in state.neutral_planets if planet.id == 5)
    score = _target_score(state, source, target, params)
    send_floor = 31

    assert score < 0
    assert _allow_break_even_conversion_target(state, source, target, score, 175, send_floor, params) is False
