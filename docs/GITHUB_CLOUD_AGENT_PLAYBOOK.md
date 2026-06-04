# GitHub Cloud Agent Playbook

## Goal

Use GitHub cloud agent to offload repository work that would otherwise consume local RAM and attention, while keeping heavy compute and private/local-only work off the cloud path.

## What Is Now Wired Up

- GitHub Actions CI:
  - `.github/workflows/python-ci.yml`
  - runs `pytest` remotely on push, pull request, or manual trigger
- GitHub Actions lightweight sparring:
  - `.github/workflows/lightweight-sparring.yml`
  - manual trigger for a bounded sparring pool
  - defaults to `github_light`, a small remote-safe pool in `configs/sparring_pool.json`
  - writes a runner-local CSV, summary JSON, and summary Markdown
  - publishes the Markdown into the GitHub Actions job summary
  - uploads the CSV plus both summaries as artifacts

This gives the project a practical GitHub lane for code validation and small evaluation runs without spending your local RAM.

For the shortest day-to-day version, use `docs/GITHUB_DAILY_CHECKLIST.md`.
For the first-time repo hookup, use `docs/GITHUB_SETUP.md`.

## Best Split For This Project

- Local Windows machine:
  - quick debugging
  - single-match inspection
  - final PR review
  - final smoke tests before submission packaging
- GitHub cloud agent:
  - code cleanup
  - script improvements
  - test additions
  - docs updates
  - bounded heuristic experiments that can be reviewed as a PR
  - GitHub Actions test runs
  - manual lightweight sparring runs with artifact download
- NTU GPU / SLURM:
  - long tournaments
  - large sweeps
  - self-play or training workloads
  - anything compute-heavy or queue-based

## Delegate To Cloud Agent

- `orbitwars/sparring.py` improvements
- `orbitwars/replay_tools.py` reporting and diagnostics
- new result summarizers or CSV tooling
- test coverage under `tests/`
- doc cleanup in `docs/`
- packaging checks that stay inside the repo
- bounded heuristic branches in `orbitwars/heuristics.py` with clear acceptance criteria

## Keep Local Or On NTU

- unpublished notes outside the repo
- secrets, tokens, cookies, private account state
- local-only files not pushed to GitHub
- NTU paths, queue state, or SLURM operations
- heavy tournament batches
- GPU training or large sweeps

## Recommended Workflow

1. Scope the task locally.
2. Limit editable files.
3. Write acceptance criteria and exact checks.
4. If it is code work, hand the task to GitHub cloud agent as an issue.
5. Let GitHub Actions run tests remotely.
6. For small evaluation jobs, trigger `Lightweight Sparring` from GitHub Actions and download the artifact CSV.
7. Review the PR locally.
8. Run final local smoke tests.

## Good Remote Candidates For A 16 GB Laptop

- PR validation through `Python CI`
- remote replay-tooling work through GitHub cloud agent
- bounded sparring pools through `Lightweight Sparring`
- docs and test maintenance
- issue-packet generation through `scripts/prepare_github_cloud_agent_issue.py`

## Do Not Push Into GitHub Actions

- long 4p tournament batches
- heavy sweeps
- anything GPU-like
- NTU queue or SLURM operations

Those belong on NTU compute nodes, not on your laptop and not on GitHub runners.

## Practical Pattern

1. Use `scripts/prepare_github_cloud_agent_issue.py` to generate a fresh packet for bounded repo work.
2. Open the issue on GitHub and let cloud agent produce the PR.
3. Let `Python CI` validate the PR remotely.
4. If you want a small strategy smoke run, trigger `Lightweight Sparring` and read the job summary first.
5. Keep big runs on NTU compute nodes.

## Ready-Made GitHub Entry Points

- Daily operating checklist:
  - `docs/GITHUB_DAILY_CHECKLIST.md`
- First-time setup guide:
  - `docs/GITHUB_SETUP.md`
- GitHub issue template for cloud-agent work:
  - `.github/ISSUE_TEMPLATE/cloud-agent-task.md`
- Packet generator:
  - `scripts/prepare_github_cloud_agent_issue.py`

## Good Acceptance Criteria

- No edits outside the allowed file list.
- Existing tests stay green.
- Any new script has CLI help or obvious entry args.
- New result summaries write to existing artifact paths unless explicitly changed.
- Docs reflect current commands and tags.

## Ready Checks Before Delegating

- Repo is pushed to GitHub.
- Cloud agent is enabled for the repo/account.
- The task does not require unpublished local context.
- The task can be reviewed as one PR.

## Suggested Cloud-Agent Task Queue

1. Strengthen `orbitwars/replay_tools.py` with weak-table diagnostics.
2. Extend `orbitwars/sparring.py` with named pools and filtered reruns.
3. Add regression tests for opening and recovery expansion behavior.
4. Add a small script that compares tags side by side from `experiments/results.csv`.

## Suggested Local Queue

1. Inspect the PR diff for strategy regressions.
2. Run a short targeted tournament after merging.
3. Rebuild `submission.zip` only after local verification.
