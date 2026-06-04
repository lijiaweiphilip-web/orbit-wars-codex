from pathlib import Path
import importlib
import sys
import zipfile

from orbitwars.packaging import package_submission


def test_package_submission_creates_agent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "experiments").mkdir()
    package_submission()
    assert (tmp_path / "submission" / "agent.py").exists()
    assert (tmp_path / "submission.zip").exists()


def test_package_submission_zip_imports_agent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "experiments").mkdir()
    package_submission()
    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(tmp_path / "submission.zip") as archive:
        archive.extractall(extract_dir)

    monkeypatch.syspath_prepend(str(extract_dir))
    sys.modules.pop("agent", None)
    sys.modules.pop("main", None)
    sys.modules.pop("orbitwars", None)
    agent_module = importlib.import_module("agent")
    main_module = importlib.import_module("main")

    assert callable(agent_module.agent)
    assert callable(main_module.agent)
