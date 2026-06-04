from __future__ import annotations

import math


BOARD_CENTER = (50.0, 50.0)
SUN_RADIUS = 10.0


def distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def angle_between(ax: float, ay: float, bx: float, by: float) -> float:
    return math.atan2(by - ay, bx - ax)


def estimate_fleet_speed(ships: int, max_speed: float) -> float:
    ships = max(int(ships), 1)
    if ships == 1:
        return 1.0
    return 1.0 + (max_speed - 1.0) * (math.log(ships) / math.log(1000)) ** 1.5


def estimate_eta(distance_units: float, ships: int, max_speed: float) -> int:
    speed = max(estimate_fleet_speed(ships, max_speed), 1e-6)
    return int(math.ceil(distance_units / speed))


def point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    denom = abx * abx + aby * aby
    if denom == 0:
        return distance(px, py, ax, ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
    cx = ax + t * abx
    cy = ay + t * aby
    return distance(px, py, cx, cy)


def crosses_sun(ax: float, ay: float, bx: float, by: float) -> bool:
    return point_segment_distance(BOARD_CENTER[0], BOARD_CENTER[1], ax, ay, bx, by) <= SUN_RADIUS
