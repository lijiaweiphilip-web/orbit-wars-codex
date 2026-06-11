from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def half_int(value: Any, minimum: int = 1) -> int:
    return max(minimum, int(value) // 2)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate SHA-X canary retry A/B configs.")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    out = repo / args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    base_path = repo / "orbit_wars_sha_x1_real_label_v1/configs/smoke_v2_canary_config.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))

    config_dir = repo / "orbit_wars_sha_x1_real_label_v1/configs"
    a = deepcopy(base)
    a["retry_plan"] = "A_walltime_5h30m_to_6h_keep_current_canary_workload"
    a["retry_notes"] = "Use next L40S window only. Raise SLURM walltime to 05:30:00-06:00:00 and keep current canary workload. Do not start Standard-RealLabel automatically."
    a["output_dir"] = "experiments/sha_x1_real_label_v1_smoke_v2_canary_retry_A_walltime"
    a["partial_checkpoint_every_states"] = int(a.get("partial_checkpoint_every_states", 2))

    b = deepcopy(base)
    b["retry_plan"] = "B_2h_half_states_missions_horizon_with_partial_reports"
    b["retry_notes"] = "Use next L40S window only if GPU time is tight. Keep 2h walltime, halve states/missions/horizon, and rely on partial checkpoints. Do not start Standard-RealLabel automatically."
    b["output_dir"] = "experiments/sha_x1_real_label_v1_smoke_v2_canary_retry_B_halfworkload"
    horizon = b.get("horizon_steps", 360)
    b["horizon_steps"] = [half_int(x) for x in horizon] if isinstance(horizon, list) else half_int(horizon)
    b["max_states"] = half_int(b.get("max_states", 16))
    b["missions_per_state"] = half_int(b.get("missions_per_state", 20))
    b["state_min_missions"] = half_int(b.get("state_min_missions", 16))
    b["state_max_missions"] = half_int(b.get("state_max_missions", 32))
    b["max_forced_labels"] = max(1, b["max_states"] * b["missions_per_state"])
    b["partial_checkpoint_every_states"] = 1
    b["progress_every_labels"] = half_int(b.get("progress_every_labels", 24))
    b["min_pairwise_rows"] = max(32, half_int(b.get("min_pairwise_rows", 128)))

    a_path = config_dir / "canary_retry_A_walltime_config.json"
    b_path = config_dir / "canary_retry_B_halfworkload_config.json"
    save_json(a_path, a)
    save_json(b_path, b)
    report = {
        "status": "PASS",
        "base_config": str(base_path.relative_to(repo)),
        "retry_A": str(a_path.relative_to(repo)),
        "retry_B": str(b_path.relative_to(repo)),
        "retry_A_max_states": a.get("max_states"),
        "retry_A_missions_per_state": a.get("missions_per_state"),
        "retry_A_horizon_steps": a.get("horizon_steps"),
        "retry_B_max_states": b.get("max_states"),
        "retry_B_missions_per_state": b.get("missions_per_state"),
        "retry_B_horizon_steps": b.get("horizon_steps"),
        "standard_started": False,
        "ntu_gpu_job_started": False,
    }
    save_json(out / "canary_retry_config_generation_report.json", report)
    write(
        out / "canary_retry_config_generation_report.md",
        "# Canary Retry Config Generation Report\n\n"
        + "\n".join(f"- {k}: `{v}`" for k, v in report.items())
        + "\n",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
