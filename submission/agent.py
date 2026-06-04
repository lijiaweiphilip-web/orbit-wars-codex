import math

PARAMS = {'aggression_2p': 1.3,
 'aggression_4p': 0.8,
 'enemy_denial_bonus': 0.2,
 'enemy_pressure_radius': 24.0,
 'final_step_horizon': 30,
 'ignore_comets': True,
 'max_actions_per_turn': 7,
 'max_target_candidates': 8,
 'min_send_margin': 3,
 'neutral_priority': 1.2,
 'planet_value_factor': 1.8,
 'reserve_base': 6,
 'reserve_pressure_factor': 1.0,
 'reserve_value_factor': 0.7,
 'third_party_risk': 1.1,
 'travel_penalty': 0.5}

def distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def angle_between(ax, ay, bx, by):
    return math.atan2(by - ay, bx - ax)

def reserve_for_planet(source, planets, fleets, my_id):
    pressure = 0.0
    for planet in planets:
        if planet[1] == my_id or planet[1] == -1:
            continue
        gap = distance(source[2], source[3], planet[2], planet[3])
        if 0 < gap <= 24:
            pressure += planet[5] / gap
    for fleet in fleets:
        if fleet[1] != my_id:
            gap = distance(source[2], source[3], fleet[2], fleet[3])
            if gap <= 18:
                pressure += fleet[6] / max(gap, 1.0)
    return int(math.ceil(PARAMS["reserve_base"] + source[6] * PARAMS["reserve_value_factor"] + pressure * PARAMS["reserve_pressure_factor"]))

def score_target(source, target, observation):
    if target[0] in set(observation.get("comet_planet_ids", [])) and PARAMS.get("ignore_comets", True):
        return -1e9
    gap = distance(source[2], source[3], target[2], target[3])
    ships_needed = target[5] + PARAMS["min_send_margin"]
    score = target[6] * PARAMS["planet_value_factor"] - gap * PARAMS["travel_penalty"] - ships_needed
    if target[1] == -1:
        score += PARAMS["neutral_priority"]
    elif target[1] != observation.get("player", 0):
        score += PARAMS["enemy_denial_bonus"] * target[6]
        if len({p[1] for p in observation.get("planets", []) if p[1] >= 0}) >= 4:
            score -= PARAMS["third_party_risk"] * 0.5
    return score

def agent(observation, configuration):
    my_id = observation.get("player", 0)
    planets = observation.get("planets", [])
    fleets = observation.get("fleets", [])
    my_planets = [planet for planet in planets if planet[1] == my_id]
    targets = [planet for planet in planets if planet[1] != my_id]
    actions = []
    num_players = max(2, len({planet[1] for planet in planets if planet[1] >= 0}))
    aggression = PARAMS["aggression_2p"] if num_players <= 2 else PARAMS["aggression_4p"]
    for source in sorted(my_planets, key=lambda p: (p[6], p[5]), reverse=True):
        available = source[5] - reserve_for_planet(source, planets, fleets, my_id)
        if available <= PARAMS["min_send_margin"]:
            continue
        best = max((score_target(source, target, observation), target) for target in targets if target[0] != source[0])
        if best[0] <= 0:
            continue
        target = best[1]
        send = min(available, max(target[5] + PARAMS["min_send_margin"], int(math.ceil(available * aggression * 0.5))))
        if send <= PARAMS["min_send_margin"]:
            continue
        theta = angle_between(source[2], source[3], target[2], target[3])
        actions.append([source[0], float(theta), int(send)])
        if len(actions) >= PARAMS["max_actions_per_turn"]:
            break
    return actions
