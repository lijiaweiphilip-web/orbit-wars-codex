from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import yaml

from .eval_runner import run_match
from .heuristics import HeuristicParams, params_to_dict


def sample_params(space: dict[str, list[float | int]]) -> HeuristicParams:
    params = {key: random.choice(values) for key, values in space.items()}
    return HeuristicParams.from_mapping(params)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget-minutes", type=int, default=5)
    parser.add_argument("--samples", type=int, default=6)
    parser.add_argument("--space", default="configs/sweep_space.yaml")
    args = parser.parse_args()

    space = yaml.safe_load(Path(args.space).read_text(encoding="utf-8"))
    best = None
    best_score = float("-inf")
    results_path = Path("experiments/candidates.jsonl")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    for index in range(args.samples):
        params = sample_params(space)
        payload_path = Path("experiments") / f"candidate_params_{index}.json"
        serialized = json.dumps(params_to_dict(params), ensure_ascii=False, indent=2)
        payload_path.write_text(serialized, encoding="utf-8")
        Path("experiments/best_params.json").write_text(serialized, encoding="utf-8")
        result = run_match(
            [str(Path("agents") / "candidate.py"), str(Path("agents") / "heuristic_v1.py")],
            seed=index + 1,
            episode_steps=140,
        )
        score = -float(result["ranks"][0]) + float(result["scores"][0]) / 1000.0
        record = {
            "index": index,
            "score": score,
            "params": params_to_dict(params),
            "result": {
                "ranks": result["ranks"],
                "scores": result["scores"],
                "statuses": result["statuses"],
            },
        }
        with results_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        if score > best_score:
            best_score = score
            best = params_to_dict(params)
            Path("experiments/best_params.json").write_text(
                json.dumps(best, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    print(json.dumps({"best_score": best_score, "best_params": best}, ensure_ascii=False))


if __name__ == "__main__":
    main()
