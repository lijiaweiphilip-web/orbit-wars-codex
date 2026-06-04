import json
from pathlib import Path

from orbitwars import sparring


def test_run_pool_builds_expected_summary_rows(tmp_path, monkeypatch):
    results_path = tmp_path / "results.csv"

    def fake_run_match(agents, seed, episode_steps):
        rank0 = 1 if seed % 2 else 2
        return {
            "ranks": {0: rank0, 1: 2 if rank0 == 1 else 1},
            "scores": {0: 500 - seed, 1: 400 + seed},
            "statuses": ["DONE", "DONE"],
            "snapshots": {
                "step_50": {"0": {"planets": 3, "ships": 200, "home_alive": True}},
                "step_100": {"0": {"planets": 4, "ships": 350, "home_alive": True}},
            },
        }

    monkeypatch.setattr(sparring, "run_match", fake_run_match)

    pool = [
        {
            "name": "smoke",
            "mode": "2p",
            "games": 2,
            "episode_steps": 100,
            "agents": ["agents/heuristic_v1.py", "random"],
        }
    ]
    summaries = sparring.run_pool(pool, "testtag", results_path)
    assert summaries[0]["tag"] == "testtag_smoke"
    assert summaries[0]["games"] == 2
    assert summaries[0]["win_rate_agent0"] == 0.5


def test_sparring_main_writes_summary_file(tmp_path, monkeypatch):
    results_path = tmp_path / "results.csv"
    summary_path = tmp_path / "summary.json"
    config_path = tmp_path / "pool.json"
    config_path.write_text(
        json.dumps(
            {
                "tiny": [
                    {
                        "name": "tiny_match",
                        "mode": "2p",
                        "games": 1,
                        "episode_steps": 100,
                        "agents": ["agents/heuristic_v1.py", "random"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_run_match(agents, seed, episode_steps):
        return {
            "ranks": {0: 1, 1: 2},
            "scores": {0: 600, 1: 200},
            "statuses": ["DONE", "DONE"],
            "snapshots": {
                "step_50": {"0": {"planets": 3, "ships": 180, "home_alive": True}},
                "step_100": {"0": {"planets": 5, "ships": 400, "home_alive": True}},
            },
        }

    monkeypatch.setattr(sparring, "run_match", fake_run_match)
    monkeypatch.setattr(
        "sys.argv",
        [
            "sparring",
            "--pool",
            "tiny",
            "--config",
            str(config_path),
            "--tag-prefix",
            "ci",
            "--results-path",
            str(results_path),
            "--summary-path",
            str(summary_path),
        ],
    )

    sparring.main()

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["pool"] == "tiny"
    assert payload["combined"]["games"] == 1
    assert payload["matchups"][0]["tag"] == "ci_tiny_match"
