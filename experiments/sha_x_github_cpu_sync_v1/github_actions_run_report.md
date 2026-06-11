# SHA-X CPU Sync GitHub Actions Run Report

Date: `2026-06-11`

## Git State

- branch: `phase6-shax-cpu-sync`
- sync pack commit: `fb47006`
- push trigger commit: `0d0619e`
- remote validation commit: `bcd4bfa35dec410c2dc9f5717a6bdfb40eac895c`
- remote validation commit message: `trigger sha-x cpu sync workflow on feature branch`
- pushed: yes, to `origin/phase6-shax-cpu-sync`

## Workflow Dispatch

- workflow: `.github/workflows/sha_x_cpu_sync.yml`
- workflow dispatch status: `PENDING_DEFAULT_BRANCH`
- trigger command attempted: `gh workflow run sha_x_cpu_sync.yml --ref phase6-shax-cpu-sync`
- GitHub response: `HTTP 404: workflow sha_x_cpu_sync.yml not found on the default branch`
- interpretation: remote workflow did not run because the new workflow file is not on the default branch; this is not a SHA-X CPU sync failure.

## Push Trigger Validation

- trigger status: `PASS`
- event: `push`
- run id: `27342076381`
- branch: `phase6-shax-cpu-sync`
- run URL: `https://github.com/lijiaweiphilip-web/orbit-wars-codex/actions/runs/27342076381`
- workflow name: `SHA-X CPU Sync`
- job: `sha-x-cpu-sync`
- run status: `completed`
- run conclusion: `success`
- artifact upload: `success`

## Local Validation

| check | status |
|---|---|
| static guard | PASS |
| py_compile | PASS |
| directory structure | PASS |
| sbatch TC2N03-08 | PASS |
| no TC2N01/TC2N02 request | PASS |
| no forbidden Kaggle submit command | PASS |
| no token/credential pattern | PASS |
| no large labels/model weights | PASS |
| artifact generated | PASS |

## Artifact

- local artifact: `experiments/sha_x_github_cpu_sync_v1/sha_x_cpu_sync_artifacts_20260611.zip`
- remote artifact: `sha_x_cpu_sync_artifacts_20260611.zip`
- artifact id: `7562197652`
- artifact size: `28276` bytes
- artifact digest: `sha256:d160d4572e097e05f0603db1039171be19a0eb4f34d9a9a5aee635e4821db8b6`

## Remote Step Results

| step | status |
|---|---|
| Checkout | PASS |
| Setup Python | PASS |
| Static guard | PASS |
| Generate canary retry configs | PASS |
| Build artifact | PASS |
| Upload artifact | PASS |

## Guardrails

- no second Kaggle submission
- no N7 submission
- no SHA-X scorer submission
- no NTU GPU job
- no SHA-X canary / standard / full / v4 / rollout
- no NTU head-node project Python
- no Kaggle token, NTU credential, or GitHub Actions secret used by the workflow
