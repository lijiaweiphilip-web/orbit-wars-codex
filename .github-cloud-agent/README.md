# Cloud Agent Packets

This folder stores ready-to-use issue packets for GitHub cloud agent work.

## How To Use

1. Pick a packet under `packets/`.
2. Copy the matching `issue.md` content into a GitHub issue.
3. Keep the task scoped to the listed files.
4. Review the resulting PR locally before merge.

You can also generate a new packet with:

`python scripts/prepare_github_cloud_agent_issue.py prepare --task-text "..." --repo "owner/repo" --allowed orbitwars/replay_tools.py --tests "python -m pytest -q" --output-dir .github-cloud-agent/latest`

If you prefer opening a GitHub issue directly, start from:

` .github/ISSUE_TEMPLATE/cloud-agent-task.md `

## Current Packets

- `packets/weak-table-diagnostics`
- `packets/sparring-tooling`
