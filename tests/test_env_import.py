from kaggle_environments import make


def test_orbit_wars_env_imports():
    env = make("orbit_wars", configuration={"episodeSteps": 20}, debug=True)
    assert env.name == "orbit_wars"
