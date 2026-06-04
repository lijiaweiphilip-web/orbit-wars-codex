Title: Improve Orbit Wars sparring tooling for repeatable mixed-pool evaluation

The repo already has a sparring entry point and pool config. We want better tooling so mixed-pool evaluation is easier to rerun and compare without using local memory on ad hoc manual commands.

Scope:
- Improve `orbitwars/sparring.py` and related config support.
- Favor small CLI features over large architecture changes.

Allowed files:
- `orbitwars/sparring.py`
- `configs/sparring_pool.json`
- `tests/`
- `docs/FINAL_REPORT.md` only if command examples need refresh

Blocked files:
- `submission/`
- `agents/`
- `orbitwars/heuristics.py`

Acceptance criteria:
- Support at least one of these improvements:
  - run a selected subset of matchups by name
  - rerun only 2p or only 4p pools
  - print a concise combined summary without manual filtering
- Existing default pool behavior remains usable.
- Existing tests pass, and new CLI logic has minimal coverage where practical.

Checks:
- `python -m pytest -q`
- one example sparring invocation using the new feature

Notes:
- Keep output compact and reviewable.
- Do not add heavy dependencies.
