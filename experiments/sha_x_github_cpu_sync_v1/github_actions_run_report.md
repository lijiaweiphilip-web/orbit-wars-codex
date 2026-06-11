# SHA-X CPU Sync GitHub Actions Run Report

Date: `2026-06-11`

## Git State

- branch: `phase6-shax-cpu-sync`
- sync pack commit: `fb47006`
- branch head after N3 result update: `9030230`
- commit message: `sha-x github cpu sync pack and one-submission handoff`
- pushed: yes, to `origin/phase6-shax-cpu-sync`

## Workflow Dispatch

- workflow: `.github/workflows/sha_x_cpu_sync.yml`
- workflow run URL: `NOT_AVAILABLE`
- trigger status: `PENDING_DEFAULT_BRANCH`
- trigger command attempted: `gh workflow run sha_x_cpu_sync.yml --ref phase6-shax-cpu-sync`
- GitHub response: `HTTP 404: workflow sha_x_cpu_sync.yml not found on the default branch`
- interpretation: remote workflow did not run because the new workflow file is not on the default branch; this is not a SHA-X CPU sync failure.

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
- remote artifact: `PENDING_DEFAULT_BRANCH`

## Guardrails

- no second Kaggle submission
- no N7 submission
- no SHA-X scorer submission
- no NTU GPU job
- no SHA-X canary / standard / full / v4 / rollout
- no NTU head-node project Python
