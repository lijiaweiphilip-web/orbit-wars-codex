# SHA-X CPU Sidecar GitHub Actions Run Report

Date: `2026-06-11`

## Git State

- branch: `phase5-sidecar-ci`
- final pushed commit: `dca9f5942a7c44a0ef1c902b56cd11d0e303fe8d`
- commit message: `sha-x cpu sidecar and canary retry configs`
- pushed: yes, to `origin/phase5-sidecar-ci`

## Workflow Dispatch

- workflow: `.github/workflows/sha_x_cpu_sidecar.yml`
- workflow run URL: `NOT_AVAILABLE`
- trigger status: `REMOTE_WORKFLOW_NOT_RUN_BECAUSE_WORKFLOW_NOT_ON_DEFAULT_BRANCH`
- trigger command attempted: `gh workflow run sha_x_cpu_sidecar.yml --ref phase5-sidecar-ci`
- GitHub response: `HTTP 404: workflow sha_x_cpu_sidecar.yml not found on the default branch`
- interpretation: this is not a SHA-X failure and not a CPU sidecar failure; GitHub did not create a run because the new workflow is not yet visible from the default branch

## Validation Status

| check | status | evidence |
|---|---|---|
| local py_compile | PASS | `python -m py_compile` passed for SHA-X scripts |
| directory structure | PASS | required canary files exist locally and are committed |
| sbatch TC2N03-08 | PASS | canary sbatch contains `--nodes=1`, `--nodelist=TC2N[03-08]`, `--gres=gpu:1` |
| no TC2N01/TC2N02 request | PASS | canary sbatch does not request TC2N01/TC2N02 |
| no Kaggle CLI submit | PASS | sidecar scope has no forbidden Kaggle CLI submission command |
| no token/credential pattern | PASS | sidecar scope passed local forbidden-pattern check |
| artifact upload | PENDING_DEFAULT_BRANCH | remote workflow could not be dispatched before default-branch visibility |

## Artifact

- expected artifact name: `sha_x_cpu_sidecar_artifacts_20260610.zip`
- local artifact generated: yes
- remote artifact generated: no, workflow dispatch blocked before run creation

## Final Status

- CPU sidecar local validation: `PASS`
- remote GitHub Actions: `PENDING_DEFAULT_BRANCH`
- Kaggle submission: `NO`
- NTU GPU job: `NO`
- secrets used: `NO`
- NTU head-node project Python: `NO`

## Safety Guardrails

- no Kaggle submission performed
- no NTU GPU job submitted
- no SHA-X canary started
- no standard/full standard/full/v4/new rollout started
- no project Python run on NTU head node
- no Kaggle token, NTU credential, or repository secret used by this run

## Next Step

No more action today. If remote validation is needed tomorrow, use one of the safe paths in `experiments/github_actions_manual_run_instructions.md`. The next GPU action, when L40S is available, remains canary retry A/B only, not full standard.
