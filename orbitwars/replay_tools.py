from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        extras = row.get(None)
        if extras and "snapshots" not in row:
            row["snapshots"] = extras[0]
    return rows


def _filter_rows(rows: list[dict[str, str]], tag_filter: str = "") -> list[dict[str, str]]:
    return [row for row in rows if not tag_filter or row["tag"] == tag_filter]


def summarize(rows: list[dict[str, str]], tag_filter: str = "") -> dict[str, object]:
    filtered = _filter_rows(rows, tag_filter=tag_filter)
    if not filtered:
        return {"games": 0, "message": "no matching rows"}

    wins = 0
    rank_counter: Counter[int] = Counter()
    mode_counter: Counter[str] = Counter()
    winner_counter: Counter[str] = Counter()
    score_deltas: list[int] = []
    snapshot_rollups: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    by_tag: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in filtered:
        ranks = {int(k): int(v) for k, v in json.loads(row["ranks"]).items()}
        scores = {int(k): int(v) for k, v in json.loads(row["scores"]).items()}
        my_rank = ranks.get(0, 99)
        wins += 1 if my_rank == 1 else 0
        rank_counter[my_rank] += 1
        mode_counter[row["mode"]] += 1
        winner_counter[row["winner"]] += 1
        best_other = max((score for player, score in scores.items() if player != 0), default=0)
        score_deltas.append(scores.get(0, 0) - best_other)
        snapshots = json.loads(row.get("snapshots", "{}") or "{}")
        for step_name, players in snapshots.items():
            player0 = players.get("0") or players.get(0)
            if not player0:
                continue
            snapshot_rollups[step_name]["planets"].append(float(player0["planets"]))
            snapshot_rollups[step_name]["ships"].append(float(player0["ships"]))
            snapshot_rollups[step_name]["home_alive"].append(1.0 if player0["home_alive"] else 0.0)
        by_tag[row["tag"]].append(row)

    avg_rank = sum(rank * count for rank, count in rank_counter.items()) / len(filtered)
    avg_delta = sum(score_deltas) / len(score_deltas)
    worst = min(score_deltas) if score_deltas else 0
    best = max(score_deltas) if score_deltas else 0
    return {
        "games": len(filtered),
        "win_rate_agent0": round(wins / len(filtered), 4),
        "avg_rank_agent0": round(avg_rank, 4),
        "rank_histogram": dict(sorted(rank_counter.items())),
        "mode_histogram": dict(mode_counter),
        "winner_histogram": dict(winner_counter),
        "avg_score_delta_vs_best_other": round(avg_delta, 2),
        "best_score_delta": best,
        "worst_score_delta": worst,
        "snapshot_summary": {
            step_name: {
                metric: round(sum(values) / len(values), 3)
                for metric, values in metrics.items()
                if values
            }
            for step_name, metrics in snapshot_rollups.items()
        },
        "tags_seen": sorted(by_tag.keys()),
    }


def compare_tags(rows: list[dict[str, str]], tags: list[str]) -> dict[str, object]:
    cleaned_tags = [tag for tag in tags if tag]
    if not cleaned_tags:
        return {"message": "no tags requested", "comparisons": {}}
    per_tag = {tag: summarize(rows, tag_filter=tag) for tag in cleaned_tags}
    valid_tags = [tag for tag in cleaned_tags if per_tag[tag].get("games", 0)]
    if not valid_tags:
        return {"message": "no matching rows", "comparisons": per_tag}

    baseline = valid_tags[0]
    baseline_summary = per_tag[baseline]
    comparisons: dict[str, object] = {}
    for tag in valid_tags:
        summary = per_tag[tag]
        delta: dict[str, object] = {}
        if tag != baseline:
            delta["avg_rank_delta_vs_baseline"] = round(
                float(summary.get("avg_rank_agent0", 0.0)) - float(baseline_summary.get("avg_rank_agent0", 0.0)),
                4,
            )
            delta["score_delta_vs_baseline"] = round(
                float(summary.get("avg_score_delta_vs_best_other", 0.0))
                - float(baseline_summary.get("avg_score_delta_vs_best_other", 0.0)),
                2,
            )
            baseline_steps = baseline_summary.get("snapshot_summary", {})
            current_steps = summary.get("snapshot_summary", {})
            snapshot_delta: dict[str, dict[str, float]] = {}
            for step_name in sorted(set(baseline_steps) | set(current_steps)):
                current_metrics = current_steps.get(step_name, {})
                baseline_metrics = baseline_steps.get(step_name, {})
                step_delta = {}
                for metric in sorted(set(baseline_metrics) | set(current_metrics)):
                    if metric in baseline_metrics and metric in current_metrics:
                        step_delta[metric] = round(float(current_metrics[metric]) - float(baseline_metrics[metric]), 3)
                if step_delta:
                    snapshot_delta[step_name] = step_delta
            if snapshot_delta:
                delta["snapshot_delta_vs_baseline"] = snapshot_delta
        comparisons[tag] = {
            "summary": summary,
            "delta_vs_baseline": delta,
        }
    return {
        "baseline_tag": baseline,
        "comparisons": comparisons,
    }


def classify_loss_pattern(snapshot_gaps: dict[str, dict[str, float]]) -> str:
    step_50 = snapshot_gaps.get("step_50", {})
    step_100 = snapshot_gaps.get("step_100", {})
    gap50_planets = float(step_50.get("planet_gap_vs_winner", 0.0))
    gap50_ships = float(step_50.get("ship_gap_vs_winner", 0.0))
    gap100_planets = float(step_100.get("planet_gap_vs_winner", 0.0))
    gap100_ships = float(step_100.get("ship_gap_vs_winner", 0.0))

    if gap50_planets <= -2 or gap50_ships <= -80:
        return "early_deficit"
    if gap50_planets >= 0 and gap50_ships >= -40 and (gap100_planets <= -1 or gap100_ships <= -120):
        return "midgame_falloff"
    if abs(gap100_planets) <= 1 and abs(gap100_ships) <= 120:
        return "close_finish"
    return "steady_outscaled"


def _checkpoint_leader(players: dict[str | int, dict[str, float | int | bool]]) -> dict[str, float | int] | None:
    if not players:
        return None
    normalized: list[tuple[int, dict[str, float | int | bool]]] = []
    for raw_player, metrics in players.items():
        normalized.append((int(raw_player), metrics))
    player_id, metrics = max(
        normalized,
        key=lambda item: (
            float(item[1]["ships"]),
            float(item[1]["planets"]),
            -item[0],
        ),
    )
    return {
        "player": player_id,
        "ships": float(metrics["ships"]),
        "planets": float(metrics["planets"]),
        "home_alive": 1.0 if metrics["home_alive"] else 0.0,
    }


def _growth_between_checkpoints(
    snapshots: dict[str, dict[str | int, dict[str, float | int | bool]]],
    player: int,
    start_step: str = "step_50",
    end_step: str = "step_100",
) -> dict[str, float] | None:
    start_players = snapshots.get(start_step, {})
    end_players = snapshots.get(end_step, {})
    start_metrics = start_players.get(str(player)) or start_players.get(player)
    end_metrics = end_players.get(str(player)) or end_players.get(player)
    if not start_metrics or not end_metrics:
        return None
    return {
        "planet_growth": float(end_metrics["planets"]) - float(start_metrics["planets"]),
        "ship_growth": float(end_metrics["ships"]) - float(start_metrics["ships"]),
    }


def loss_report(rows: list[dict[str, str]], tag_filter: str) -> dict[str, object]:
    filtered = _filter_rows(rows, tag_filter=tag_filter)
    if not filtered:
        return {"games": 0, "message": "no matching rows"}

    losses: list[dict[str, object]] = []
    pattern_counter: Counter[str] = Counter()
    winner_counter: Counter[int] = Counter()
    leader_transition_counter: Counter[str] = Counter()
    for row in filtered:
        ranks = {int(k): int(v) for k, v in json.loads(row["ranks"]).items()}
        scores = {int(k): int(v) for k, v in json.loads(row["scores"]).items()}
        snapshots = json.loads(row.get("snapshots", "{}") or "{}")
        my_rank = ranks.get(0, 99)
        if my_rank == 1:
            continue
        best_other_score = max((score for player, score in scores.items() if player != 0), default=0)
        winner = int(row["winner"])
        winner_counter[winner] += 1
        snapshot_gaps: dict[str, dict[str, float]] = {}
        checkpoint_leaders: dict[str, dict[str, float | int] | None] = {}
        for step_name, players in snapshots.items():
            me = players.get("0") or players.get(0)
            leader = players.get(str(winner)) or players.get(winner)
            checkpoint_leaders[step_name] = _checkpoint_leader(players)
            if not me or not leader:
                continue
            snapshot_gaps[step_name] = {
                "planet_gap_vs_winner": float(me["planets"]) - float(leader["planets"]),
                "ship_gap_vs_winner": float(me["ships"]) - float(leader["ships"]),
                "home_alive_gap_vs_winner": (1.0 if me["home_alive"] else 0.0) - (1.0 if leader["home_alive"] else 0.0),
            }
        step_50_leader = checkpoint_leaders.get("step_50")
        step_100_leader = checkpoint_leaders.get("step_100")
        my_growth = _growth_between_checkpoints(snapshots, 0)
        winner_growth = _growth_between_checkpoints(snapshots, winner)
        if step_50_leader or step_100_leader:
            transition = f"{int(step_50_leader['player']) if step_50_leader else 'na'}->{int(step_100_leader['player']) if step_100_leader else 'na'}"
            leader_transition_counter[transition] += 1
        else:
            transition = "na->na"
        losses.append(
            {
                "seed": int(row["seed"]),
                "rank": my_rank,
                "winner": winner,
                "score_delta_vs_best_other": scores.get(0, 0) - best_other_score,
                "pattern": classify_loss_pattern(snapshot_gaps),
                "snapshot_gaps": snapshot_gaps,
                "checkpoint_leaders": checkpoint_leaders,
                "growth_step_50_to_100": {
                    "agent0": my_growth,
                    "winner": winner_growth,
                },
                "leader_transition": transition,
            }
        )
        pattern_counter[losses[-1]["pattern"]] += 1

    losses.sort(key=lambda item: (int(item["rank"]), float(item["score_delta_vs_best_other"])))
    return {
        "tag": tag_filter,
        "games": len(filtered),
        "loss_count": len(losses),
        "pattern_histogram": dict(sorted(pattern_counter.items())),
        "winner_histogram": dict(sorted(winner_counter.items())),
        "leader_transition_histogram": dict(sorted(leader_transition_counter.items())),
        "losses": losses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="experiments/results.csv")
    parser.add_argument("--tag", default="")
    parser.add_argument("--compare-tags", default="")
    parser.add_argument("--loss-report", default="")
    args = parser.parse_args()
    rows = load_rows(Path(args.results))
    if args.loss_report:
        payload = loss_report(rows, args.loss_report)
    elif args.compare_tags:
        compare_list = [item.strip() for item in args.compare_tags.split(",") if item.strip()]
        payload = compare_tags(rows, compare_list)
    else:
        payload = summarize(rows, tag_filter=args.tag)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
