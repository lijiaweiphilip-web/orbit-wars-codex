from __future__ import annotations

import argparse
import json
from pathlib import Path

from .eval_runner import run_match


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--episode-steps", type=int, default=120)
    parser.add_argument("--checkpoints", default="25,50,75,100")
    parser.add_argument("--trace-player", type=int, default=0)
    parser.add_argument("--trace-step-start", type=int, default=50)
    parser.add_argument("--trace-step-end", type=int, default=75)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    checkpoints = tuple(int(item) for item in args.checkpoints.split(",") if item.strip())
    agent_specs = [item.strip() for item in args.agents.split(",") if item.strip()]
    result = run_match(
        agent_specs,
        seed=args.seed,
        episode_steps=args.episode_steps,
        checkpoints=checkpoints,
        trace_player=args.trace_player,
        trace_step_start=args.trace_step_start,
        trace_step_end=args.trace_step_end,
    )
    payload = {
        "seed": args.seed,
        "agents": agent_specs,
        "ranks": result["ranks"],
        "scores": result["scores"],
        "snapshots": result["snapshots"],
        "decision_traces": result.get("decision_traces", []),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
