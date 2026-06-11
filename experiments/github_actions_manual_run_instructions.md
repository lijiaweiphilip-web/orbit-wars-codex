# SHA-X CPU Sidecar Manual Run Instructions

Date: `2026-06-11`

## Why Manual Steps Are Needed

The branch `phase5-sidecar-ci` was pushed with `.github/workflows/sha_x_cpu_sidecar.yml`, but GitHub returned:

`HTTP 404: workflow sha_x_cpu_sidecar.yml not found on the default branch`

GitHub only exposes new `workflow_dispatch` workflows after the workflow file is present on the default branch, or after the repository UI indexes it through the normal PR/default-branch path.

## Current Commit

- branch: `phase5-sidecar-ci`
- final pushed commit: `dca9f5942a7c44a0ef1c902b56cd11d0e303fe8d`
- commit message: `sha-x cpu sidecar and canary retry configs`

## Safe Paths For Tomorrow

### Path A: Remote GitHub Actions Validation

1. Open a PR from `phase5-sidecar-ci` to the repository default branch.
2. Review that the PR contains only SHA-X CPU sidecar workflow/config/docs/safe partial-checkpoint patch changes.
3. Merge only that safe workflow/config/docs/script patch to the default branch.
4. In GitHub Actions, select `SHA-X CPU Sidecar`.
5. Use `Run workflow`.
6. Select ref `phase5-sidecar-ci` if GitHub offers a ref selector; otherwise run on the default branch after the workflow lands.
7. Confirm these checks pass:
   - checkout
   - setup-python 3.11
   - py_compile
   - directory structure check
   - sbatch TC2N03-08 check
   - no TC2N01/TC2N02 request
   - no Kaggle submit command
   - no token/credential pattern
   - artifact upload

### Path B: No Remote Validation

Do not merge the workflow yet. Keep the local artifact and current pushed branch as the CPU sidecar record. When L40S is available, resume from canary retry A/B only; do not jump to standard/full standard.

## Final Status

- CPU sidecar local validation: `PASS`
- remote GitHub Actions: `PENDING_DEFAULT_BRANCH`
- Kaggle submission: `NO`
- NTU GPU job: `NO`
- secrets used: `NO`
- NTU head-node project Python: `NO`

## Artifact

Expected uploaded artifact name:

`sha_x_cpu_sidecar_artifacts_20260610.zip`

The artifact should contain only workflow yaml, SHA-X scripts/configs/slurm file, and markdown plans/reports. It should not contain large labels or model weights.
