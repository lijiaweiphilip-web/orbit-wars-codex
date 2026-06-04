from orbitwars.heuristics import choose_actions_with_trace, default_v1_params, make_agent
from orbitwars.obs_parser import parse_observation


agent = make_agent(default_v1_params())


def trace_observation(observation: dict, configuration: dict) -> dict[str, object]:
    params = default_v1_params()
    state = parse_observation(observation, configuration)
    actions, trace = choose_actions_with_trace(state, params)
    return {"actions": actions, "trace": trace}
