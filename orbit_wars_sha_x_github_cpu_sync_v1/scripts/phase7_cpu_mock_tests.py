from __future__ import annotations

import argparse
import importlib.util
import json
import re
import zipfile
from pathlib import Path
from typing import Any


REWARD_COMPONENTS = [
    "planet_count_delta",
    "production_delta",
    "ship_delta",
    "target_capture",
    "source_overdrain_penalty",
    "rank_delta",
    "top2_delta",
    "win_proxy",
    "leader_help_penalty",
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def load_real_label_module(repo: Path) -> Any:
    script = repo / "orbit_wars_sha_x1_real_label_v1/scripts/real_label_smoke.py"
    spec = importlib.util.spec_from_file_location("real_label_smoke_phase7", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def planet(pid: int, owner: int, ships: float, production: float) -> list[Any]:
    return [pid, owner, 0.0, 0.0, 0.0, ships, production]


def mock_reward_obs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    before = {
        "step": 100,
        "state_id": "mock_reward",
        "planets": [
            planet(1, 0, 100, 5),
            planet(2, 1, 30, 4),
            planet(3, 1, 100, 8),
            planet(4, 2, 120, 5),
            planet(5, 3, 95, 5),
        ],
        "fleets": [],
    }
    control = {
        "step": 140,
        "state_id": "mock_reward",
        "planets": [
            planet(1, 0, 50, 5),
            planet(2, 1, 28, 4),
            planet(3, 1, 100, 8),
            planet(4, 2, 120, 5),
            planet(5, 3, 95, 5),
        ],
        "fleets": [],
    }
    forced = {
        "step": 140,
        "state_id": "mock_reward",
        "planets": [
            planet(1, 0, 220, 5),
            planet(2, 0, 160, 4),
            planet(3, 1, 80, 8),
            planet(4, 2, 260, 9),
            planet(5, 3, 95, 5),
        ],
        "fleets": [[9, 2, 10, 10, 60]],
    }
    candidate = {
        "label_id": "mock_reward_candidate",
        "state_id": "mock_reward",
        "source_ids": [1],
        "target_id": 2,
        "send_ships": [90],
        "eta_min": 1.0,
        "mission_profile": "high_production_capture",
    }
    return before, control, forced, candidate


def run_reward_component_test(module: Any) -> dict[str, Any]:
    before, control, forced, candidate = mock_reward_obs()
    components = module.shaped_reward(before, control, forced, candidate, nplayers=4)
    missing = [name for name in REWARD_COMPONENTS if name not in components]
    non_numeric = [name for name in REWARD_COMPONENTS if name in components and not isinstance(components[name], (int, float))]
    nonempty = {
        name: (name in components and isinstance(components[name], (int, float)))
        for name in REWARD_COMPONENTS
    }
    return {
        "status": "PASS" if not missing and not non_numeric else "FAIL",
        "components": {name: components.get(name) for name in REWARD_COMPONENTS},
        "delta_reward": components.get("delta_reward"),
        "missing": missing,
        "non_numeric": non_numeric,
        "all_components_nonempty_numeric": all(nonempty.values()),
    }


def run_trace_diff_test(module: Any) -> dict[str, Any]:
    candidate = {
        "source_ids": [1],
        "target_id": 2,
        "send_ships": [42],
        "eta_min": 1.0,
    }
    control = {
        "step": 101,
        "state_id": "mock_trace",
        "planets": [
            planet(1, 0, 80, 5),
            planet(2, 1, 45, 6),
            planet(3, 2, 70, 4),
        ],
        "fleets": [],
    }
    forced = {
        "step": 101,
        "state_id": "mock_trace",
        "planets": [
            planet(1, 0, 38, 5),
            planet(2, 0, 18, 6),
            planet(3, 2, 70, 4),
        ],
        "fleets": [[1, 0, 0.0, 0.0, 42]],
    }
    control_snapshot = module.trace_snapshot(control, candidate, nplayers=3)
    forced_snapshot = module.trace_snapshot(forced, candidate, nplayers=3)
    diff = module.snapshot_diff(control_snapshot, forced_snapshot, candidate)
    required = ["source_ships", "target_ships", "fleet_count", "arrival_event", "owner_change"]
    checks = {
        "source_ships": bool(diff.get("source_ships")) and abs(float(diff["source_ships"].get("1", 0.0))) > 0.0,
        "target_ships": isinstance(diff.get("target_ships"), (int, float)) and abs(float(diff["target_ships"])) > 0.0,
        "fleet_count": isinstance(diff.get("fleet_count"), (int, float)) and int(diff["fleet_count"]) == 1,
        "arrival_event": diff.get("arrival_event") is True,
        "owner_change": diff.get("owner_change") is True,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "required_fields": required,
        "checks": checks,
        "diff": diff,
    }


def label_row(state_id: str, idx: int, reward: float) -> dict[str, Any]:
    return {
        "state_id": state_id,
        "label_id": f"{state_id}_{idx}",
        "delta_reward": reward,
        "top2_delta": 1.0 if reward > 0 else 0.0,
    }


def run_pairwise_test(module: Any) -> dict[str, Any]:
    signal_rows = [label_row("signal_state", idx, float(idx)) for idx in range(10)]
    pairs, low_signal = module.build_pairwise(signal_rows, top_quantile=0.20, bottom_quantile=0.20)
    tie_rows = [label_row("tie_state", idx, 5.0) for idx in range(5)]
    tie_pairs, tie_low_signal = module.build_pairwise(tie_rows, top_quantile=0.20, bottom_quantile=0.20)
    status = "PASS" if len(pairs) > 0 and not low_signal and not tie_pairs and "tie_state" in tie_low_signal else "FAIL"
    return {
        "status": status,
        "pairwise_rows": len(pairs),
        "low_signal_states": low_signal,
        "tie_pairwise_rows": len(tie_pairs),
        "tie_status": "LOW_SIGNAL_STATE" if "tie_state" in tie_low_signal else "NOT_MARKED",
        "tie_low_signal_states": tie_low_signal,
    }


def run_sbatch_safety_lint(repo: Path) -> dict[str, Any]:
    slurm_dir = repo / "orbit_wars_sha_x1_real_label_v1/slurm"
    files = sorted(slurm_dir.glob("*.sbatch"))
    rows: list[dict[str, Any]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        checks = {
            "nodes_1": "#SBATCH --nodes=1" in text,
            "nodelist_l40s": "#SBATCH --nodelist=TC2N[03-08]" in text,
            "gpu_1": "#SBATCH --gres=gpu:1" in text,
            "no_tc2n01_tc2n02": "TC2N01" not in text and "TC2N02" not in text,
        }
        rows.append({"file": str(path.relative_to(repo)), "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks})
    return {
        "status": "PASS" if files and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "checked_files": len(files),
        "files": rows,
    }


def run_no_secret_no_submit_scan(repo: Path) -> dict[str, Any]:
    roots = [
        repo / ".github/workflows/sha_x_cpu_sync.yml",
        repo / ".github/workflows/sha_x_phase7_ci_hardening.yml",
        repo / "orbit_wars_sha_x_github_cpu_sync_v1",
        repo / "orbit_wars_sha_x1_real_label_v1/scripts",
    ]
    secret_patterns = [
        re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile("-----BEGIN " + r"(RSA |OPENSSH |EC )?PRIVATE " + "KEY-----"),
        re.compile(r"(?i)(kaggle_key|kaggle_username)\s*[:=]\s*['\"][^'\"]+['\"]"),
        re.compile(r"(?i)ntu.*password\s*[:=]\s*['\"][^'\"]+['\"]"),
    ]
    submit_hits: list[str] = []
    secret_hits: list[str] = []
    files_scanned = 0
    for root in roots:
        paths = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in paths:
            if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".zip"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            files_scanned += 1
            for line_no, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if re.search(r"(^|[;&|]\s*)kaggle\s+competitions\s+submit\b", stripped):
                    submit_hits.append(f"{path.relative_to(repo)}:{line_no}")
                if any(pattern.search(line) for pattern in secret_patterns):
                    secret_hits.append(f"{path.relative_to(repo)}:{line_no}")
    return {
        "status": "PASS" if not submit_hits and not secret_hits else "FAIL",
        "files_scanned": files_scanned,
        "kaggle_submit_execution_hits": submit_hits,
        "secret_or_credential_hits": secret_hits,
    }


def write_markdown_reports(out: Path, reports: dict[str, Any]) -> None:
    summary_lines = [
        "# SHA-X Phase7 CI Hardening Report",
        "",
        f"- status: `{reports['status']}`",
        f"- reward_components_all_covered: `{reports['reward_component_test']['all_components_nonempty_numeric']}`",
        f"- pairwise_rows: `{reports['pairwise_builder_test']['pairwise_rows']}`",
        f"- tie_case_status: `{reports['pairwise_builder_test']['tie_status']}`",
        f"- sbatch_safety: `{reports['sbatch_safety_lint']['status']}`",
        f"- no_secret_no_submit_scan: `{reports['no_secret_no_submit_scan']['status']}`",
        f"- ntu_gpu_job_started: `False`",
        f"- kaggle_submission_started: `False`",
        f"- head_node_python_used: `False`",
        "",
    ]
    write(out / "phase7_ci_hardening_report.md", "\n".join(summary_lines))
    write(out / "reward_component_unit_test_report.md", "# Reward Component Unit Test\n\n" + json.dumps(reports["reward_component_test"], indent=2, sort_keys=True) + "\n")
    write(out / "trace_diff_parser_test_report.md", "# Forced-Mission Trace Diff Parser Test\n\n" + json.dumps(reports["trace_diff_parser_test"], indent=2, sort_keys=True) + "\n")
    write(out / "pairwise_builder_test_report.md", "# Pairwise Builder Test\n\n" + json.dumps(reports["pairwise_builder_test"], indent=2, sort_keys=True) + "\n")
    write(out / "sbatch_safety_lint_report.md", "# SBatch Safety Lint\n\n" + json.dumps(reports["sbatch_safety_lint"], indent=2, sort_keys=True) + "\n")
    write(out / "no_secret_no_kaggle_submit_scan_report.md", "# No Secret / No Kaggle Submit Scan\n\n" + json.dumps(reports["no_secret_no_submit_scan"], indent=2, sort_keys=True) + "\n")
    write(
        out / "partial_checkpoint_patch_report.md",
        "# Partial Checkpoint Patch Report\n\n"
        "- status: `PRESENT_FROM_PHASE6`\n"
        "- partial outputs: `trace_diff_audit_partial.md`, `label_quality_partial.md`, `pairwise_quality_partial.md`\n"
        "- timeout behavior: `PARTIAL reports are written during canary progress checkpoints`\n"
        "- core reward logic changed in phase7: `False`\n",
    )
    write(
        out / "next_l40s_canary_retry_instructions.md",
        "# Next L40S Canary Retry Instructions\n\n"
        "Status: `PLAN_ONLY`\n\n"
        "Use the next available L40S window to retry canary only. Do not start Standard-RealLabel automatically.\n\n"
        "## Option A\n\n"
        "- config: `orbit_wars_sha_x1_real_label_v1/configs/canary_retry_A_walltime_config.json`\n"
        "- walltime: `05:30:00` to `06:00:00`\n"
        "- workload: keep current canary workload\n\n"
        "## Option B\n\n"
        "- config: `orbit_wars_sha_x1_real_label_v1/configs/canary_retry_B_halfworkload_config.json`\n"
        "- walltime: `02:00:00`\n"
        "- workload: half states / missions / horizon with partial reports\n",
    )


def build_artifact(repo: Path, out: Path, artifact_name: str) -> dict[str, Any]:
    artifact = out / artifact_name
    include = [
        out / "phase7_ci_hardening_report.md",
        out / "phase7_ci_hardening_report.json",
        out / "reward_component_unit_test_report.md",
        out / "trace_diff_parser_test_report.md",
        out / "pairwise_builder_test_report.md",
        out / "sbatch_safety_lint_report.md",
        out / "no_secret_no_kaggle_submit_scan_report.md",
        out / "partial_checkpoint_patch_report.md",
        out / "next_l40s_canary_retry_instructions.md",
        repo / "orbit_wars_sha_x1_real_label_v1/configs/canary_retry_A_walltime_config.json",
        repo / "orbit_wars_sha_x1_real_label_v1/configs/canary_retry_B_halfworkload_config.json",
        repo / ".github/workflows/sha_x_phase7_ci_hardening.yml",
        repo / "orbit_wars_sha_x_github_cpu_sync_v1/scripts/phase7_cpu_mock_tests.py",
    ]
    added: list[str] = []
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in include:
            if not path.exists() or not path.is_file():
                continue
            rel = path.relative_to(repo).as_posix()
            zf.write(path, rel)
            added.append(rel)
    return {
        "status": "PASS",
        "artifact": str(artifact.relative_to(repo)),
        "artifact_bytes": artifact.stat().st_size,
        "files": added,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="SHA-X phase7 CPU-only CI hardening mock tests.")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--artifact", default="sha_x_phase7_ci_hardening_artifacts_20260611.zip")
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    out = repo / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    module = load_real_label_module(repo)

    reports: dict[str, Any] = {
        "reward_component_test": run_reward_component_test(module),
        "trace_diff_parser_test": run_trace_diff_test(module),
        "pairwise_builder_test": run_pairwise_test(module),
        "sbatch_safety_lint": run_sbatch_safety_lint(repo),
        "no_secret_no_submit_scan": run_no_secret_no_submit_scan(repo),
        "kaggle_submission_started": False,
        "ntu_gpu_job_started": False,
        "head_node_python_used": False,
        "github_actions_secrets_used": False,
    }
    reports["status"] = "PASS" if all(
        reports[key]["status"] == "PASS"
        for key in [
            "reward_component_test",
            "trace_diff_parser_test",
            "pairwise_builder_test",
            "sbatch_safety_lint",
            "no_secret_no_submit_scan",
        ]
    ) else "FAIL"
    write_markdown_reports(out, reports)
    save_json(out / "phase7_ci_hardening_report.json", reports)
    artifact = build_artifact(repo, out, args.artifact)
    reports["artifact"] = artifact
    save_json(out / "phase7_ci_hardening_report.json", reports)
    print(json.dumps(reports, sort_keys=True))
    if reports["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
