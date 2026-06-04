from __future__ import annotations

from collections import defaultdict


def player_scores(final_obs: dict, num_players: int) -> dict[int, int]:
    scores = defaultdict(int)
    for planet in final_obs.get("planets", []):
        owner = int(planet[1])
        if owner >= 0:
            scores[owner] += int(planet[5])
    for fleet in final_obs.get("fleets", []):
        owner = int(fleet[1])
        if owner >= 0:
            scores[owner] += int(fleet[6])
    for player in range(num_players):
        scores[player] += 0
    return dict(scores)


def player_ranks(scores: dict[int, int]) -> dict[int, int]:
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    ranks: dict[int, int] = {}
    current_rank = 1
    previous_score = None
    for index, (player_id, score) in enumerate(ordered, start=1):
        if previous_score is not None and score < previous_score:
            current_rank = index
        ranks[player_id] = current_rank
        previous_score = score
    return ranks


def summarize_match(statuses: list[str], final_obs: dict, num_players: int) -> dict[str, object]:
    scores = player_scores(final_obs, num_players)
    ranks = player_ranks(scores)
    return {
        "statuses": statuses,
        "scores": scores,
        "ranks": ranks,
    }
