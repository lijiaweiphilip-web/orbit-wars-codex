from pathlib import Path

from orbitwars.heuristics import load_params, make_agent


agent = make_agent(load_params(Path("experiments") / "best_params.json"))
