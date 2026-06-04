from orbitwars.heuristics import (
    _is_midgame_leader,
    _nearest_enemy_distance_to_target,
    _target_score,
    choose_actions,
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
