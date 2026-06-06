from orbitwars.candidates import generate_candidate_missions
from orbitwars.heuristics import default_v1_params


def test_late_flush_does_not_dominate_early_game():
    obs = {
        "step": 20,
        "player": 0,
        "planets": [
            [0, 0, 12, 12, 2, 80, 4],
            [1, -1, 22, 12, 2, 8, 5],
            [2, -1, 24, 16, 2, 6, 4],
            [3, 1, 35, 12, 2, 20, 4],
            [4, 1, 40, 18, 2, 12, 3],
        ],
        "fleets": [],
        "angular_velocity": 0.03,
        "initial_planets": [],
        "comets": [],
        "comet_planet_ids": [],
    }
    candidates = generate_candidate_missions(obs, {"episodeSteps": 500}, max_candidates=16, params=default_v1_params())
    missions = [candidate.mission_type for candidate in candidates]

    assert "capture_neutral" in missions
    assert missions.count("late_flush") == 0


def test_rescue_appears_when_own_planet_has_enemy_incoming():
    obs = {
        "step": 110,
        "player": 0,
        "planets": [
            [0, 0, 20, 20, 2, 14, 4],
            [1, 0, 14, 18, 2, 70, 4],
            [2, 1, 42, 20, 2, 55, 4],
        ],
        "fleets": [[0, 1, 25, 20, 3.14, 2, 35]],
        "angular_velocity": 0.03,
        "initial_planets": [],
        "comets": [],
        "comet_planet_ids": [],
    }
    candidates = generate_candidate_missions(obs, {"episodeSteps": 500}, max_candidates=16, params=default_v1_params())

    assert any(candidate.mission_type == "rescue" for candidate in candidates)


def test_four_player_enemy_missions_are_diverse():
    obs = {
        "step": 180,
        "player": 0,
        "planets": [
            [0, 0, 15, 15, 2, 120, 5],
            [1, 0, 18, 22, 2, 70, 3],
            [2, 1, 30, 15, 2, 18, 5],
            [3, 1, 35, 22, 2, 26, 4],
            [4, 2, 75, 20, 2, 120, 5],
            [5, 2, 80, 25, 2, 95, 4],
            [6, 3, 82, 80, 2, 35, 4],
            [7, -1, 28, 28, 2, 10, 5],
        ],
        "fleets": [[9, 2, 70, 20, 3.14, 4, 20], [10, 3, 78, 75, -2.2, 6, 12]],
        "angular_velocity": 0.03,
        "initial_planets": [],
        "comets": [],
        "comet_planet_ids": [],
    }
    candidates = generate_candidate_missions(obs, {"episodeSteps": 500}, max_candidates=24, params=default_v1_params())
    missions = {candidate.mission_type for candidate in candidates}

    assert {"weak_harvest", "leader_bash", "capture_neutral"} & missions
    assert {"capture_enemy", "recapture", "snipe", "swarm"} & missions
