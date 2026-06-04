# GitHub Setup

Use this once when turning this repo into a GitHub-first low-RAM workflow.

## Goal

After this setup:

- pushes and PRs can run `Python CI`
- you can manually trigger `Lightweight Sparring`
- you can open bounded cloud-agent issues with a ready template
- your laptop only keeps fast local debug and final review work

## Prerequisites

- the repo is committed locally
- you have a GitHub repo for this project
- GitHub Actions is allowed for the repo
- GitHub cloud agent or Copilot coding agent is available in your account or org if you want async repo work

## One-Time Setup

1. Push this repo to GitHub.
2. Open the repo on GitHub.
3. If you want to avoid local RAM pressure, open the repo in `Codespaces`.
4. Let the dev container finish `postCreateCommand` dependency install.
5. Go to `Actions`.
6. Enable workflows if GitHub asks.
7. Confirm these workflows are visible:
   - `Python CI`
   - `Lightweight Sparring`
8. Go to `Issues`.
9. Confirm the issue template `Cloud Agent Task` is available.
10. Open `Actions` again and manually run `Lightweight Sparring`.
11. Confirm the run shows:
   - a job summary with win rate and avg rank
   - uploaded artifacts for CSV, JSON, and Markdown summary

## Recommended Low-RAM Split

- Codespaces:
  - code edits
  - test runs
  - lightweight sparring
  - packet generation
- Local laptop:
  - quick inspection
  - final PR review
  - final smoke check before packaging
- NTU compute:
  - heavy tournament batches
  - sweeps
  - training or GPU-heavy work

## First Remote Coding Trial

1. Pick one bounded task, such as a docs or replay-tooling improvement.
2. Generate a packet:
   - `python scripts/prepare_github_cloud_agent_issue.py prepare ...`
3. Open a GitHub issue using the generated packet or the `Cloud Agent Task` template.
4. Assign it to GitHub cloud agent or Copilot coding agent if available.
5. Review the PR locally only after `Python CI` finishes.

## What To Keep Off GitHub

- secrets
- local-only files
- NTU queue or SLURM state
- heavy tournament batches
- long sweeps
- GPU workloads

## Quick Validation

If you want a minimal confidence check after setup:

1. Push a tiny doc change.
2. Confirm `Python CI` runs.
3. Trigger `Lightweight Sparring`.
4. Read the job summary.
5. Stop there unless the summary looks suspicious.

## If Something Is Missing

- Workflow not visible:
  - check that `.github/workflows/` was pushed
  - check that Actions is enabled for the repo
- No issue template:
  - check that `.github/ISSUE_TEMPLATE/cloud-agent-task.md` was pushed
- No job summary:
  - check that `Lightweight Sparring` finished the Markdown render step
- Cloud agent unavailable:
  - keep using GitHub Actions for remote checks
  - use packet generation as a manual issue-writing shortcut
