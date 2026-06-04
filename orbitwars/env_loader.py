from __future__ import annotations

from kaggle_environments import make


def make_env(num_agents: int, seed: int | None = None, episode_steps: int = 500):
    configuration = {"episodeSteps": episode_steps}
    if seed is not None:
        configuration["seed"] = seed
    env = make("orbit_wars", configuration=configuration, debug=True)
    env.num_agents = num_agents
    return env
