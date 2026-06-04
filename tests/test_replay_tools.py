from orbitwars.replay_tools import classify_loss_pattern, compare_tags, loss_report, summarize


def _row(tag: str, rank0: int, score0: int, best_other: int, planets50: int, planets100: int) -> dict[str, str]:
    winner = 0 if rank0 == 1 else 1
    return {
        "tag": tag,
        "mode": "4p",
        "winner": str(winner),
        "ranks": f'{{"0": {rank0}, "1": 1, "2": 3, "3": 4}}' if rank0 != 1 else '{"0": 1, "1": 2, "2": 3, "3": 4}',
        "scores": f'{{"0": {score0}, "1": {best_other}, "2": 100, "3": 50}}',
        "statuses": '["DONE", "DONE", "DONE", "DONE"]',
        "snapshots": (
            '{"step_50": {"0": {"planets": '
            f"{planets50}"
            ', "ships": 200, "home_alive": true}, "'
            f"{winner}"
            '": {"planets": 3, "ships": 240, "home_alive": true}}, "step_100": {"0": {"planets": '
            f"{planets100}"
            ', "ships": 400, "home_alive": true}, "'
            f"{winner}"
            '": {"planets": 5, "ships": 480, "home_alive": true}}}'
        ),
    }


def test_summarize_single_tag():
    rows = [_row("a", 1, 500, 300, 3, 4), _row("a", 2, 400, 450, 2, 3)]
    summary = summarize(rows, tag_filter="a")
    assert summary["games"] == 2
    assert summary["avg_rank_agent0"] == 1.5
    assert summary["snapshot_summary"]["step_50"]["planets"] == 2.5


def test_compare_tags_reports_deltas():
    rows = [
        _row("baseline", 2, 400, 500, 2, 3),
        _row("candidate", 1, 650, 450, 3, 5),
    ]
    payload = compare_tags(rows, ["baseline", "candidate"])
    assert payload["baseline_tag"] == "baseline"
    candidate = payload["comparisons"]["candidate"]
    assert candidate["summary"]["avg_rank_agent0"] == 1.0
    assert candidate["delta_vs_baseline"]["avg_rank_delta_vs_baseline"] == -1.0
    assert candidate["delta_vs_baseline"]["snapshot_delta_vs_baseline"]["step_100"]["planets"] == 2.0


def test_loss_report_lists_non_wins():
    rows = [
        _row("mix", 2, 400, 500, 2, 3),
        _row("mix", 1, 650, 450, 3, 5),
    ]
    rows[0]["seed"] = "7"
    rows[1]["seed"] = "8"
    report = loss_report(rows, "mix")
    assert report["loss_count"] == 1
    assert report["losses"][0]["seed"] == 7
    assert report["losses"][0]["snapshot_gaps"]["step_50"]["planet_gap_vs_winner"] <= 0
    assert report["winner_histogram"] == {1: 1}
    assert report["losses"][0]["leader_transition"] == "1->1"
    assert report["losses"][0]["growth_step_50_to_100"]["agent0"]["planet_growth"] == 1.0


def test_classify_loss_pattern_midgame_falloff():
    pattern = classify_loss_pattern(
        {
            "step_50": {"planet_gap_vs_winner": 0.0, "ship_gap_vs_winner": 20.0},
            "step_100": {"planet_gap_vs_winner": -2.0, "ship_gap_vs_winner": -180.0},
        }
    )
    assert pattern == "midgame_falloff"
