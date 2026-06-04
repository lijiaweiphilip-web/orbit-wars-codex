import json
import subprocess
import sys
from pathlib import Path


def test_prepare_github_cloud_agent_issue_generates_files(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "prepare_github_cloud_agent_issue.py"
    output_dir = tmp_path / "packet"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "prepare",
            "--task-text",
            "Add summary artifact support to lightweight sparring",
            "--repo",
            "example/orbit-wars-codex",
            "--allowed",
            "orbitwars/sparring.py",
            "--blocked",
            "submission",
            "--acceptance",
            "Summary JSON is produced.",
            "--tests",
            "python -m pytest -q",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    packet = json.loads((output_dir / "packet.json").read_text(encoding="utf-8"))
    issue_md = (output_dir / "issue.md").read_text(encoding="utf-8")
    decision_md = (output_dir / "decision.md").read_text(encoding="utf-8")

    assert packet["objective"] == "Add summary artifact support to lightweight sparring"
    assert "orbitwars/sparring.py" in packet["allowed_files"]
    assert "Add summary artifact support to lightweight sparring" in issue_md
    assert "Decision: Hybrid" in decision_md
