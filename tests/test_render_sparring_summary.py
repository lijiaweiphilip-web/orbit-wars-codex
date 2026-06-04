from scripts.render_sparring_summary import render_markdown


def test_render_markdown_includes_core_sections():
    payload = {
        "pool": "github_light",
        "tag_prefix": "gha_sparring_12",
        "matchups": [
            {
                "tag": "gha_sparring_12_2p_random_smoke",
                "mode": "2p",
                "games": 4,
                "win_rate_agent0": 0.75,
                "avg_rank_agent0": 1.25,
            }
        ],
        "combined": {
            "games": 4,
            "win_rate_agent0": 0.75,
            "avg_rank_agent0": 1.25,
            "avg_score_delta_vs_best_other": 120.5,
            "snapshot_summary": {
                "step_50": {"planets": 3.5, "ships": 220.0, "home_alive": 1.0},
            },
        },
    }

    markdown = render_markdown(payload)

    assert "# Lightweight Sparring Summary" in markdown
    assert "`gha_sparring_12_2p_random_smoke`" in markdown
    assert "## Snapshots" in markdown
    assert "`step_50`" in markdown
