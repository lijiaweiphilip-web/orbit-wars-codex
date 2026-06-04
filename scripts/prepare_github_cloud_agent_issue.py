from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_issue_markdown(payload: dict[str, object]) -> str:
    allowed_files = payload.get("allowed_files", [])
    blocked_files = payload.get("blocked_files", [])
    acceptance_criteria = payload.get("acceptance_criteria", [])
    tests = payload.get("tests", [])

    lines = [
        f"# {payload['objective']}",
        "",
        "## Scope",
        str(payload["objective"]),
        "",
        "## Repo",
        str(payload.get("repo", "unknown")),
        "",
        "## Privacy",
        str(payload["privacy"]),
        "",
        "## Allowed Files",
    ]
    lines.extend(f"- `{item}`" for item in allowed_files)
    lines.extend(
        [
            "",
            "## Blocked Files",
        ]
    )
    lines.extend(f"- `{item}`" for item in blocked_files)
    lines.extend(
        [
            "",
            "## Acceptance Criteria",
        ]
    )
    lines.extend(f"- {item}" for item in acceptance_criteria)
    lines.extend(
        [
            "",
            "## Checks",
        ]
    )
    lines.extend(f"- `{item}`" for item in tests)
    return "\n".join(lines) + "\n"


def build_decision_markdown(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            f"Decision: {payload['decision']}",
            "",
            f"Objective: {payload['objective']}",
            f"Repo: {payload.get('repo', 'unknown')}",
            f"Privacy: {payload['privacy']}",
            "",
            "Why this is GitHub-cloud-agent friendly:",
            "- Bounded repository task",
            "- Allowed files are explicit",
            "- Acceptance criteria and checks are explicit",
            "- No NTU-only or local-secret state is required",
            "",
            "Next step:",
            "Copy `issue.md` into a GitHub issue and assign it to GitHub cloud agent or Copilot coding agent.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--task-text", required=True)
    prepare.add_argument("--repo", default="unknown")
    prepare.add_argument("--privacy", default="normal")
    prepare.add_argument("--decision", default="Hybrid")
    prepare.add_argument("--task-type", default="tooling")
    prepare.add_argument("--allowed", action="append", default=[])
    prepare.add_argument("--blocked", action="append", default=[])
    prepare.add_argument("--acceptance", action="append", default=[])
    prepare.add_argument("--tests", action="append", default=[])
    prepare.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "decision": args.decision,
        "repo_task_type": args.task_type,
        "objective": args.task_text,
        "repo": args.repo,
        "privacy": args.privacy,
        "allowed_files": args.allowed,
        "blocked_files": args.blocked,
        "acceptance_criteria": args.acceptance,
        "tests": args.tests,
    }

    (output_dir / "packet.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "issue.md").write_text(build_issue_markdown(payload), encoding="utf-8")
    (output_dir / "decision.md").write_text(build_decision_markdown(payload), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "files": ["packet.json", "issue.md", "decision.md"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
