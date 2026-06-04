from orbitwars.obs_parser import parse_observation


def test_parse_observation_basic():
    observation = {
        "step": 0,
        "player": 0,
        "planets": [[0, 0, 10, 20, 2, 10, 3], [1, -1, 20, 30, 2, 5, 2]],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    state = parse_observation(observation, {"episodeSteps": 50})
    assert state.my_id == 0
    assert len(state.my_planets) == 1
    assert len(state.neutral_planets) == 1
