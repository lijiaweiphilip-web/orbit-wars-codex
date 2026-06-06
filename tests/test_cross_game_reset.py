from orbitwars.env_loader import make_env
from orbitwars.eval_runner import _random_agent
from orbitwars.heuristics import default_v1_params, make_agent


def test_same_agent_process_repeated_games_does_not_error_or_cache_leak():
    agent = make_agent(default_v1_params())
    statuses = []
    for seed in (20260605, 20260606, 20260607):
        env = make_env(num_agents=2, seed=seed, episode_steps=80)
        env.run([agent, _random_agent])
        statuses.append(tuple(entry.status for entry in env.state))

    assert all(status[0] in ("DONE", "ACTIVE", "INACTIVE") for status in statuses)
