# GitHub Daily Checklist

Use this when you want to save local RAM on a 16 GB laptop.

If the repo is not set up on GitHub yet, start with `docs/GITHUB_SETUP.md`.

## Fast Choice

- Need code checked remotely:
  - push branch or open PR
  - let `Python CI` run
- Need a small strategy smoke run:
  - trigger `Lightweight Sparring`
  - read the Actions job summary first
- Need repo work done asynchronously:
  - generate a packet with `scripts/prepare_github_cloud_agent_issue.py`
  - open a GitHub issue
  - assign it to GitHub cloud agent or Copilot coding agent
- Need heavy compute:
  - do not use the laptop
  - do not use GitHub Actions
  - send it to NTU compute nodes

## Daily Flow

1. Decide whether the task is `remote check`, `remote coding`, or `heavy compute`.
2. For `remote check`, use GitHub Actions.
3. For `remote coding`, generate a cloud-agent packet and open the issue.
4. For `heavy compute`, keep it off GitHub and off the laptop.
5. Review PRs locally only after remote checks finish.
6. Rebuild `submission.zip` only after the final local smoke test.

## Remote Check

### Python CI

- Best for:
  - test suite validation
  - PR safety checks
  - small repo changes

### Lightweight Sparring

- Best for:
  - quick heuristic smoke checks
  - verifying a PR did not obviously weaken the agent
- What to read:
  - first: GitHub Actions job summary
  - second: uploaded Markdown or JSON summary
  - third: CSV artifact only if you need raw rows

## Remote Coding

### Good Cloud-Agent Tasks

- `orbitwars/replay_tools.py` reporting work
- `orbitwars/sparring.py` tooling work
- tests under `tests/`
- docs updates
- bounded changes in `orbitwars/heuristics.py` with explicit acceptance criteria

### Avoid Sending

- secrets
- local-only notes
- NTU-specific state
- anything needing GPU or long tournament runs

## Simple Routine

1. Start local only long enough to scope the task.
2. Push the branch.
3. Let GitHub handle the first validation pass.
4. Look at the job summary, not the raw artifact, unless something looks off.
5. Pull results back local only for final review or deeper debugging.
