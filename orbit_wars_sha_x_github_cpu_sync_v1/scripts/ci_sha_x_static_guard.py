from __future__ import annotations

import argparse
import json
import py_compile
import re
from pathlib import Path
from typing import Any


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def text_files(paths: list[Path]) -> list[Path]:
    rows: list[Path] = []
    for path in paths:
        if path.is_file():
            rows.append(path)
        elif path.is_dir():
            rows.extend(p for p in path.rglob("*") if p.is_file())
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="CPU-only SHA-X static guard.")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    out = repo / args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    required = [
        "orbit_wars_sha_x1_real_label_v1/CODEX_RUN_THIS_FIRST.md",
        "orbit_wars_sha_x1_real_label_v1/configs/smoke_v2_canary_config.json",
        "orbit_wars_sha_x1_real_label_v1/scripts/real_label_smoke.py",
        "orbit_wars_sha_x1_real_label_v1/slurm/01_real_label_smoke_v2_canary.sbatch",
        "orbit_wars_sha_x_github_cpu_sync_v1/CODEX_RUN_THIS_FIRST.md",
        "orbit_wars_sha_x_github_cpu_sync_v1/scripts/generate_canary_retry_configs.py",
        "orbit_wars_sha_x_github_cpu_sync_v1/scripts/build_github_artifact.py",
    ]
    missing = [p for p in required if not (repo / p).exists()]

    py_compile_errors: list[str] = []
    for script in sorted((repo / "orbit_wars_sha_x1_real_label_v1/scripts").glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as exc:
            py_compile_errors.append(f"{script}: {exc.msg}")
    for script in sorted((repo / "orbit_wars_sha_x_github_cpu_sync_v1/scripts").glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as exc:
            py_compile_errors.append(f"{script}: {exc.msg}")

    sbatch = repo / "orbit_wars_sha_x1_real_label_v1/slurm/01_real_label_smoke_v2_canary.sbatch"
    sbatch_text = sbatch.read_text(encoding="utf-8") if sbatch.exists() else ""
    sbatch_checks = {
        "nodes_1": "#SBATCH --nodes=1" in sbatch_text,
        "nodelist_l40s": "#SBATCH --nodelist=TC2N[03-08]" in sbatch_text,
        "gpu_1": "#SBATCH --gres=gpu:1" in sbatch_text,
        "no_tc2n01_02_request": re.search(r"(?m)^#SBATCH --nodelist=.*TC2N0[12]", sbatch_text) is None,
    }

    forbidden_submit = "kaggle competitions " + "submit"
    secret_patterns = [
        re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"gho_[A-Za-z0-9_]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile("-----BEGIN " + r"(RSA |OPENSSH |EC )?PRIVATE " + "KEY-----"),
        re.compile(r"(?i)(kaggle_key|kaggle_username)\s*[:=]\s*['\"][^'\"]+['\"]"),
        re.compile(r"(?i)ntu.*password\s*[:=]"),
    ]
    scan_roots = [
        repo / ".github/workflows/sha_x_cpu_sync.yml",
        repo / ".github/workflows/sha_x_cpu_sidecar.yml",
        repo / "orbit_wars_sha_x1_real_label_v1",
        repo / "orbit_wars_sha_x_github_cpu_sync_v1",
        repo / "experiments/github_actions_cpu_sidecar_plan.md",
        repo / "experiments/sha_x_canary_retry_A_B_plan.md",
        repo / "experiments/sha_x_standard_4shard_dry_run_plan.md",
        repo / "experiments/sha_x_no_gpu_today_report.md",
    ]
    forbidden_hits: list[str] = []
    secret_hits: list[str] = []
    large_artifact_hits: list[str] = []
    for path in text_files(scan_roots):
        if path.suffix.lower() in {".zip", ".pt", ".pth", ".ckpt", ".safetensors", ".parquet"}:
            if path.stat().st_size > 5_000_000:
                large_artifact_hits.append(str(path.relative_to(repo)))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if forbidden_submit in text:
            forbidden_hits.append(str(path.relative_to(repo)))
        if any(pattern.search(text) for pattern in secret_patterns):
            secret_hits.append(str(path.relative_to(repo)))

    ok = (
        not missing
        and not py_compile_errors
        and all(sbatch_checks.values())
        and not forbidden_hits
        and not secret_hits
        and not large_artifact_hits
    )
    report = {
        "status": "PASS" if ok else "FAIL",
        "missing": missing,
        "py_compile_errors": py_compile_errors,
        "sbatch_checks": sbatch_checks,
        "forbidden_kaggle_submit_hits": forbidden_hits,
        "secret_or_credential_hits": secret_hits,
        "large_label_or_weight_hits": large_artifact_hits,
        "no_ntu_gpu_job": True,
        "no_head_node_python": True,
        "no_kaggle_submission_from_guard": True,
    }
    save_json(out / "ci_sha_x_static_guard_report.json", report)
    lines = ["# SHA-X CPU Static Guard Report", ""]
    for key, value in report.items():
        lines.append(f"- {key}: `{value}`")
    write(out / "ci_sha_x_static_guard_report.md", "\n".join(lines) + "\n")
    print(json.dumps(report, sort_keys=True))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
