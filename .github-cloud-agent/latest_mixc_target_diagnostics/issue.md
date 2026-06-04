# Analyze mix_c target selection failures, identify safe planets our agent should have taken but did not, extend replay diagnostics to surface missed-safe-target candidates, and optionally implement one bounded heuristic branch if diagnostics justify it.

## Scope
Analyze mix_c target selection failures, identify safe planets our agent should have taken but did not, extend replay diagnostics to surface missed-safe-target candidates, and optionally implement one bounded heuristic branch if diagnostics justify it.

## Repo
unknown

## Privacy
normal

## Allowed Files
- `orbitwars/replay_tools.py`
- `orbitwars/heuristics.py`
- `tests/test_replay_tools.py`
- `tests/test_heuristics.py`
- `docs/FINAL_REPORT.md`
- `TEAM_STATUS.md`

## Blocked Files
- `experiments/results.csv`
- `submission/agent.py`
- `submission.zip`

## Acceptance Criteria
- Add a reproducible diagnostic path for mix_c-style losses that highlights likely missed safe targets or target-ordering mistakes.
- Keep edits inside the allowed files only.
- Preserve current passing tests and add or update tests for any new diagnostics or heuristic helpers.
- If a heuristic change is included, keep it narrow, data-driven, and documented in FINAL_REPORT/TEAM_STATUS.

## Checks
- `python -m pytest -q`
- `python -m orbitwars.replay_tools --compare-tags sparring_v2_recover_4p_mix_c,mixc_proximity_v1`
- `python -m orbitwars.replay_tools --loss-report sparring_v2_recover_4p_mix_c`
