from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


SUBMISSION_AGENT_SOURCE = """from orbitwars.heuristics import default_v1_params, make_agent


agent = make_agent(default_v1_params())
"""


SUBMISSION_MAIN_SOURCE = """from agent import agent
"""

SUBMISSION_INIT_SOURCE = """\"\"\"Minimal runtime package for the Kaggle submission.\"\"\"
"""


def _copy_runtime_files(submission_dir: Path) -> None:
    package_dir = submission_dir / "orbitwars"
    package_dir.mkdir(parents=True, exist_ok=True)
    source_root = Path(__file__).resolve().parent
    runtime_files = [
        "geometry.py",
        "heuristics.py",
        "obs_parser.py",
    ]
    (package_dir / "__init__.py").write_text(SUBMISSION_INIT_SOURCE, encoding="utf-8")
    for name in runtime_files:
        shutil.copy2(source_root / name, package_dir / name)


def package_submission(best_params_path: str = "experiments/best_params.json") -> Path:
    submission_dir = Path("submission")
    submission_dir.mkdir(parents=True, exist_ok=True)
    (submission_dir / "agent.py").write_text(SUBMISSION_AGENT_SOURCE, encoding="utf-8")
    (submission_dir / "main.py").write_text(SUBMISSION_MAIN_SOURCE, encoding="utf-8")
    (submission_dir / "README_SUBMISSION.md").write_text(
        "# Submission\n\nStable Orbit Wars heuristic package with minimal runtime modules and import-safe package init.\n",
        encoding="utf-8",
    )
    _copy_runtime_files(submission_dir)
    zip_path = Path("submission.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(submission_dir / "agent.py", arcname="agent.py")
        archive.write(submission_dir / "main.py", arcname="main.py")
        archive.write(submission_dir / "README_SUBMISSION.md", arcname="README_SUBMISSION.md")
        for runtime_path in sorted((submission_dir / "orbitwars").glob("*.py")):
            archive.write(runtime_path, arcname=f"orbitwars/{runtime_path.name}")
    return zip_path


def main() -> None:
    package_submission()
    print("submission.zip")


if __name__ == "__main__":
    main()
