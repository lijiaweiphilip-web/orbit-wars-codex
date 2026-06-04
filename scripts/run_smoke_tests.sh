#!/usr/bin/env bash
set -euo pipefail
AGENT_PATH="${1:-agents/heuristic_v0.py}"
python -m pytest tests/test_env_import.py tests/test_agent_action_schema.py tests/test_no_timeout.py tests/test_packaging.py -q
python -m orbitwars.tournament --agents "${AGENT_PATH},random" --mode 2p --games 4 --episode-steps 80 --tag smoke
