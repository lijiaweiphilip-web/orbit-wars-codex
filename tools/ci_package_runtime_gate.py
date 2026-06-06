from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SIDECAR_ROOT = REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase5_sidecar"


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


def _profile_package(name: str, package_path: Path, output_dir: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "name": name,
        "path": str(package_path),
        "exists": package_path.exists(),
        "pass": False,
    }
    if not package_path.exists():
        result["missing_reason"] = "artifact_not_present"
        return result
    profile_path = output_dir / f"{name}_runtime_profile.json"
    proc = _run(
        [
            sys.executable,
            "tools/profile_agent_runtime.py",
            "--agent",
            str(package_path),
            "--games",
            "4",
            "--episode-steps",
            "120",
            "--output",
            str(profile_path),
        ]
    )
    result["returncode"] = proc.returncode
    result["stdout"] = proc.stdout.strip()
    result["stderr"] = proc.stderr.strip()
    if proc.returncode != 0 or not profile_path.exists():
        result["missing_reason"] = "runtime_profile_failed"
        return result
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    result["profile"] = profile
    result["pass"] = all(
        [
            profile.get("local_import_smoke_pass", False),
            profile.get("smoke_2p_pass", False),
            profile.get("smoke_4p_pass", False),
            float(profile.get("p95_act_time_sec", 999.0)) < 0.2,
            float(profile.get("max_act_time_sec", 999.0)) < 0.8,
            profile.get("no_torch_sklearn_dependency", False),
            profile.get("fallback_heuristic_pass", False),
            profile.get("cross_game_reset_pass", False),
        ]
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5 sidecar package/runtime gate.")
    parser.add_argument("--output", default="experiments/nn_ranker_v1/phase5_sidecar/package_runtime_gate_report.md")
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    SIDECAR_ROOT.mkdir(parents=True, exist_ok=True)
    output_path = REPO_ROOT / args.output

    pytest_result = {"run": not args.skip_pytest, "pass": None, "returncode": None, "stdout": "", "stderr": ""}
    if not args.skip_pytest:
        proc = _run([sys.executable, "-m", "pytest", "-q"])
        pytest_result.update(
            {
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "pass": proc.returncode == 0,
            }
        )
    else:
        pytest_result["pass"] = True

    packages = {
        "baseline": REPO_ROOT / "experiments" / "nn_ranker_v1" / "frozen_baseline" / "submission_10_swarm_surplus_arrival_v1.zip",
        "neural_v2": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_neural_branch" / "submission_neural_ranker_v2.zip",
        "neural_v3": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase4_rollout_repair" / "submission_neural_ranker_v3.zip",
        "neural_v4": REPO_ROOT / "experiments" / "nn_ranker_v1" / "phase5_ntu_rollout" / "submission_neural_ranker_v4.zip",
    }
    profiles = [_profile_package(name, path, SIDECAR_ROOT) for name, path in packages.items()]
    overall_pass = bool(pytest_result["pass"]) and all(
        row["pass"] for row in profiles if row.get("exists")
    )

    lines = [
        "# Phase 5 Sidecar Package Runtime Gate Report",
        "",
        f"- overall_pass: `{overall_pass}`",
        f"- pytest_pass: `{pytest_result['pass']}`",
        f"- runtime_gate_policy: `p95 < 0.2s, max < 0.8s, no torch/sklearn, fallback pass, cross-game reset pass`",
        "",
        "## Pytest",
        "",
        f"- run: `{pytest_result['run']}`",
        f"- pass: `{pytest_result['pass']}`",
    ]
    if pytest_result["stdout"]:
        lines.append(f"- summary: `{pytest_result['stdout'].splitlines()[-1]}`")
    if pytest_result["stderr"]:
        lines.append(f"- stderr_tail: `{pytest_result['stderr'].splitlines()[-1]}`")
    lines.extend(
        [
            "",
            "## Package Matrix",
            "",
            "| package | exists | import | 2p | 4p | p95 | max | no_torch_sklearn | fallback | reset | pass |",
            "|---|---|---|---|---|---:|---:|---|---|---|---|",
        ]
    )
    for row in profiles:
        profile = row.get("profile", {})
        if not row.get("exists"):
            lines.append(f"| {row['name']} | no | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | skipped |")
            continue
        lines.append(
            "| {name} | yes | {imp} | {smoke2} | {smoke4} | {p95:.4f} | {mx:.4f} | {deps} | {fb} | {reset} | {passed} |".format(
                name=row["name"],
                imp=profile.get("local_import_smoke_pass"),
                smoke2=profile.get("smoke_2p_pass"),
                smoke4=profile.get("smoke_4p_pass"),
                p95=float(profile.get("p95_act_time_sec", 999.0)),
                mx=float(profile.get("max_act_time_sec", 999.0)),
                deps=profile.get("no_torch_sklearn_dependency"),
                fb=profile.get("fallback_heuristic_pass"),
                reset=profile.get("cross_game_reset_pass"),
                passed=row.get("pass"),
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `neural_v4` is optional at this stage and will remain skipped until Phase 5 rollout labels and model selection are complete.",
            "- This gate is CPU-safe and does not require Kaggle tokens.",
            "- This report does not trigger Kaggle submission.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "overall_pass": overall_pass}, sort_keys=True))


if __name__ == "__main__":
    main()
