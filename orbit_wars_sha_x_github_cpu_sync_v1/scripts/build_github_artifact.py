from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def add_path(zf: zipfile.ZipFile, repo: Path, path: Path, added: list[str]) -> None:
    if not path.exists():
        return
    if path.is_file():
        rel = path.relative_to(repo).as_posix()
        zf.write(path, rel)
        added.append(rel)
        return
    for child in sorted(path.rglob("*")):
        if not child.is_file():
            continue
        if "__pycache__" in child.parts or child.suffix.lower() == ".pyc":
            continue
        if child.suffix.lower() in {".pt", ".pth", ".ckpt", ".safetensors", ".parquet"}:
            continue
        if child.stat().st_size > 5_000_000:
            continue
        rel = child.relative_to(repo).as_posix()
        zf.write(child, rel)
        added.append(rel)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build SHA-X GitHub CPU sync artifact.")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--artifact", required=True)
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    out = repo / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    artifact = Path(args.artifact)
    artifact_path = artifact if artifact.is_absolute() else out / artifact

    include = [
        repo / ".github/workflows/sha_x_cpu_sync.yml",
        repo / ".github/workflows/sha_x_cpu_sidecar.yml",
        repo / "orbit_wars_sha_x_github_cpu_sync_v1",
        repo / "orbit_wars_sha_x1_real_label_v1/CODEX_RUN_THIS_FIRST.md",
        repo / "orbit_wars_sha_x1_real_label_v1/scripts/real_label_smoke.py",
        repo / "orbit_wars_sha_x1_real_label_v1/configs/smoke_v2_canary_config.json",
        repo / "orbit_wars_sha_x1_real_label_v1/configs/canary_retry_A_walltime_config.json",
        repo / "orbit_wars_sha_x1_real_label_v1/configs/canary_retry_B_halfworkload_config.json",
        repo / "orbit_wars_sha_x1_real_label_v1/slurm/01_real_label_smoke_v2_canary.sbatch",
        repo / "experiments/github_actions_cpu_sidecar_plan.md",
        repo / "experiments/sha_x_canary_retry_A_B_plan.md",
        repo / "experiments/sha_x_standard_4shard_dry_run_plan.md",
        repo / "experiments/sha_x_no_gpu_today_report.md",
        repo / "experiments/submission_day_plan_20260610/sha_x_pause_and_resume_plan.md",
        repo / "experiments/submission_day_plan_20260610/sha_x_canary_timeout_diagnosis.md",
        out / "ci_sha_x_static_guard_report.md",
        out / "ci_sha_x_static_guard_report.json",
        out / "canary_retry_config_generation_report.md",
        out / "canary_retry_config_generation_report.json",
    ]

    added: list[str] = []
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(artifact_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in include:
            add_path(zf, repo, path, added)

    report = {
        "status": "PASS",
        "artifact": str(artifact_path.relative_to(repo)),
        "artifact_bytes": artifact_path.stat().st_size,
        "file_count": len(added),
        "files": added,
        "large_labels_or_weights_included": False,
        "kaggle_submission": "not_started",
        "ntu_gpu_job": "not_started",
    }
    save_json(out / "github_artifact_report.json", report)
    write(
        out / "github_artifact_report.md",
        "# GitHub CPU Sync Artifact Report\n\n"
        + "\n".join(f"- {k}: `{v}`" for k, v in report.items() if k != "files")
        + "\n\n## Files\n\n"
        + "\n".join(f"- `{f}`" for f in added)
        + "\n",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
