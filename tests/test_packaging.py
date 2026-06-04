from pathlib import Path

from orbitwars.packaging import package_submission


def test_package_submission_creates_agent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "experiments").mkdir()
    package_submission()
    assert (tmp_path / "submission" / "agent.py").exists()
    assert (tmp_path / "submission.zip").exists()
