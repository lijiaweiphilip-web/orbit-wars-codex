---
name: Cloud Agent Task
about: Scoped repository work for GitHub cloud agent or Copilot coding agent
title: "[Cloud Agent] "
labels: ["cloud-agent"]
assignees: []
---

## Objective

Describe the exact bounded task.

## Allowed Files

- `orbitwars/...`

## Blocked Files

- `submission/`

## Acceptance Criteria

- Existing tests stay green.
- Changes stay inside the allowed file list.
- New commands or outputs are documented if needed.

## Checks

- `python -m pytest -q`

## Notes

- Use small, reviewable changes.
- Do not include secrets, NTU-only state, or local-only files.
