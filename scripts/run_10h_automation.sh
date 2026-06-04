#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs experiments docs submission
date > TEAM_STATUS.md
bash scripts/run_smoke_tests.sh agents/heuristic_v0.py | tee logs/smoke_v0.log
python -m orbitwars.tournament --agents agents/heuristic_v1.py,agents/heuristic_v0.py --mode 2p --games 10 --episode-steps 120 --tag auto | tee logs/tournament_2p.log
python -m orbitwars.tournament --agents agents/heuristic_v1.py,agents/heuristic_v0.py,random,random --mode 4p --games 10 --episode-steps 120 --tag auto | tee logs/tournament_4p.log
python -m orbitwars.bug_checks --quick | tee logs/bug_checks.log
python -m orbitwars.sweeper --samples 4 | tee logs/sweep.log
python -m orbitwars.packaging | tee logs/package.log
