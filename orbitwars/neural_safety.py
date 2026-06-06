from __future__ import annotations

from typing import Any


DEFAULT_SAFETY_CFG = {
    "leader_help_risk": 0.8,
    "third_party_steal_risk": 1.2,
    "accidental_collision_risk": 1.5,
    "overdrain": 0.8,
    "arrives_before_end_zero": 1.2,
    "home_threatened_over_send": 1.4,
    "home_threatened_fraction_threshold": 0.55,
    "home_threat_margin_threshold": 0.0,
    "top2_snipe_spam": 1.0,
    "top2_snipe_risk_threshold": 0.35,
    "weak_harvest_leader_help": 0.9,
}


def safety_penalty(features: dict[str, float], cfg: dict[str, float] | None = None) -> tuple[float, dict[str, float]]:
    cfg = {**DEFAULT_SAFETY_CFG, **(cfg or {})}
    penalties: dict[str, float] = {}

    leader_help_risk = float(features.get("leader_help_risk", 0.0))
    third_party_steal_risk = float(features.get("third_party_steal_risk", 0.0))
    accidental_collision_risk = float(features.get("accidental_collision_risk", 0.0))
    max_source_fraction_sent = float(features.get("max_source_fraction_sent", 0.0))
    arrives_before_end = float(features.get("arrives_before_end", 1.0))
    src_is_home = float(features.get("src_is_home", 0.0))
    src_threat_margin = float(features.get("src_threat_margin", 0.0))
    src_incoming_enemy_before_30 = float(features.get("src_incoming_enemy_before_30", 0.0))
    my_rank_by_strength = float(features.get("my_rank_by_strength", 9.0))
    is_4p = float(features.get("is_4p", 0.0))
    mt_snipe = float(features.get("mt_snipe", 0.0))
    mt_weak_harvest = float(features.get("mt_weak_harvest", 0.0))

    penalties["leader_help_risk"] = cfg["leader_help_risk"] * leader_help_risk
    penalties["third_party_steal_risk"] = cfg["third_party_steal_risk"] * third_party_steal_risk
    penalties["accidental_collision_risk"] = cfg["accidental_collision_risk"] * accidental_collision_risk
    penalties["overdrain"] = cfg["overdrain"] * max(0.0, max_source_fraction_sent - 0.68)

    if arrives_before_end <= 0.0:
        penalties["arrives_before_end_zero"] = cfg["arrives_before_end_zero"]

    home_threatened = (
        src_is_home > 0.5
        and src_incoming_enemy_before_30 > 0.0
        and src_threat_margin <= cfg["home_threat_margin_threshold"]
        and max_source_fraction_sent >= cfg["home_threatened_fraction_threshold"]
    )
    if home_threatened:
        penalties["home_threatened_over_send"] = cfg["home_threatened_over_send"] * (1.0 + max_source_fraction_sent)

    top2_and_risky_snipe = (
        is_4p > 0.5
        and my_rank_by_strength <= 2.0
        and mt_snipe > 0.5
        and (leader_help_risk > 0.0 or third_party_steal_risk >= cfg["top2_snipe_risk_threshold"])
    )
    if top2_and_risky_snipe:
        penalties["top2_snipe_spam"] = cfg["top2_snipe_spam"]

    if is_4p > 0.5 and mt_weak_harvest > 0.5 and leader_help_risk > 0.0:
        penalties["weak_harvest_leader_help"] = cfg["weak_harvest_leader_help"] * max(leader_help_risk, third_party_steal_risk)

    return sum(penalties.values()), penalties


def apply_safety_penalties(score: float, features: dict[str, float], cfg: dict[str, float] | None = None) -> tuple[float, dict[str, float]]:
    penalty, details = safety_penalty(features, cfg)
    return score - penalty, details
