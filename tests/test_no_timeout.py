from agents.heuristic_v1 import agent


def test_agent_runs_quickly():
    observation = {
        "step": 5,
        "player": 0,
        "planets": [[0, 0, 10, 10, 2, 30, 3], [1, -1, 30, 10, 2, 6, 2], [2, 1, 50, 50, 2, 12, 3]],
        "fleets": [],
        "angular_velocity": 0.03,
        "comet_planet_ids": [],
    }
    for _ in range(50):
        agent(observation, {"episodeSteps": 100})
