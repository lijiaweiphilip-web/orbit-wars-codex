import math

from orbitwars.candidates import CandidateMission
from orbitwars.nn_features import featurize_candidate


def _candidate(source_id=0, target_id=1, send=20, eta=10):
    return CandidateMission(
        mission_type="capture_neutral",
        source_ids=[source_id],
        target_id=target_id,
        send_ships=[send],
        angles=[0.0],
        eta_min=eta,
        eta_max=eta,
        heuristic_score=1.0,
        safety_flags={"valid_send": True, "sun_crossing": False, "board_exit_risk": False, "accidental_collision_risk": False, "safe": True},
        debug={},
    )


def test_orbiting_target_future_position_changes_projected_distance():
    obs = {
        "step": 10,
        "player": 0,
        "planets": [
            [0, 0, 20, 20, 2, 80, 4],
            [1, -1, 60, 50, 2, 8, 4],
        ],
        "fleets": [],
        "angular_velocity": 0.05,
        "initial_planets": [
            [0, 0, 20, 20, 2, 80, 4],
            [1, -1, 60, 50, 2, 8, 4],
        ],
        "comets": [],
        "comet_planet_ids": [],
    }
    features = featurize_candidate(obs, {"episodeSteps": 500}, _candidate())

    assert features["distance_eta_projected"] != features["distance_current"]
    assert math.isfinite(features["distance_eta_projected"])


def test_static_target_future_position_equals_current_distance():
    obs = {
        "step": 10,
        "player": 0,
        "planets": [
            [0, 0, 20, 20, 2, 80, 4],
            [1, -1, 95, 95, 2, 8, 4],
        ],
        "fleets": [],
        "angular_velocity": 0.05,
        "initial_planets": [
            [0, 0, 20, 20, 2, 80, 4],
            [1, -1, 95, 95, 2, 8, 4],
        ],
        "comets": [],
        "comet_planet_ids": [],
    }
    features = featurize_candidate(obs, {"episodeSteps": 500}, _candidate())

    assert features["distance_eta_projected"] == features["distance_current"]


def test_sun_crossing_flag_works():
    obs = {
        "step": 10,
        "player": 0,
        "planets": [
            [0, 0, 20, 50, 2, 80, 4],
            [1, -1, 80, 50, 2, 8, 4],
        ],
        "fleets": [],
        "angular_velocity": 0.0,
        "initial_planets": [],
        "comets": [],
        "comet_planet_ids": [],
    }
    features = featurize_candidate(obs, {"episodeSteps": 500}, _candidate())

    assert features["sun_crossing_flag"] == 1.0
    assert features["sun_path_margin"] <= 0.0


def test_accidental_collision_risk_not_always_zero():
    obs = {
        "step": 10,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 80, 4],
            [1, -1, 40, 10, 2, 8, 4],
            [2, -1, 25, 10, 3, 8, 1],
        ],
        "fleets": [],
        "angular_velocity": 0.0,
        "initial_planets": [],
        "comets": [],
        "comet_planet_ids": [],
    }
    features = featurize_candidate(obs, {"episodeSteps": 500}, _candidate())

    assert features["path_clearance_min"] < 1.0
    assert features["accidental_collision_risk"] == 1.0


def test_feature_vector_is_finite():
    obs = {
        "step": 120,
        "player": 0,
        "planets": [
            [0, 0, 10, 10, 2, 80, 4],
            [1, 1, 40, 10, 2, 8, 4],
        ],
        "fleets": [[0, 1, 35, 10, 3.14, 1, 5]],
        "angular_velocity": 0.02,
        "initial_planets": [],
        "comets": [],
        "comet_planet_ids": [],
    }
    features = featurize_candidate(obs, {"episodeSteps": 500}, _candidate())

    assert all(math.isfinite(float(value)) for value in features.values())
