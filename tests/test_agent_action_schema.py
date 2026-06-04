from agents.heuristic_v0 import agent


def test_agent_returns_valid_schema():
    observation = {
        "step": 0,
        "player": 0,
        "planets": [[0, 0, 10, 10, 2, 30, 3], [1, -1, 30, 10, 2, 6, 2]],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    actions = agent(observation, {"episodeSteps": 100})
    assert isinstance(actions, list)
    for action in actions:
        assert len(action) == 3
