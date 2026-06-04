Title: Add weak-table diagnostics for Orbit Wars 4p sparring

We have a local Orbit Wars repo with mixed 4-player sparring already wired up. The current weakness is table-shape sensitivity: some 4p mixes perform worse than others.

Scope:
- Add diagnostics that explain why a tag under `experiments/results.csv` is weak.
- Focus on differences in early expansion, midgame planet count, score delta, and rank distribution.

Allowed files:
- `orbitwars/replay_tools.py`
- `tests/`
- `docs/FINAL_REPORT.md` only if command examples must be updated

Blocked files:
- `submission/`
- `agents/`
- `orbitwars/heuristics.py`
- anything outside the repo

Acceptance criteria:
- There is a CLI path to inspect one or more tags and print comparative diagnostics.
- Output includes at least rank distribution, score delta summary, and snapshot comparison.
- Existing behavior of `python -m orbitwars.replay_tools --tag ...` remains intact.
- Existing tests pass, and any new parsing/reporting logic has coverage where reasonable.

Checks:
- `python -m pytest -q`
- one example invocation against `experiments/results.csv`

Notes:
- Do not invent external data.
- Keep the change reviewable as one PR.
