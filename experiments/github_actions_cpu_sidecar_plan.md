# SHA-X GitHub Actions CPU Sidecar Plan

Date: `2026-06-11`

## Purpose

Run only CPU-safe SHA-X maintenance in GitHub Actions while NTU GPU capacity is reserved for other projects. This workflow must not submit Kaggle packages, use Kaggle secrets, use NTU credentials, launch SLURM, or upload large labels/model weights.

## Workflow

File: `.github/workflows/sha_x_cpu_sidecar.yml`

Manual trigger only: `workflow_dispatch`

Runner: `ubuntu-latest`

Steps:

1. Checkout repository.
2. Setup Python `3.11`.
3. Check required SHA-X canary files exist.
4. Run `python -m py_compile orbit_wars_sha_x1_real_label_v1/scripts/*.py`.
5. Check canary sbatch keeps `--nodes=1`, `--nodelist=TC2N[03-08]`, and `--gres=gpu:1`.
6. Check canary sbatch does not request TC2N01/TC2N02.
7. Check no Kaggle submit command and no credential-like hardcoded tokens in SHA-X sidecar files.
8. Build and upload `sha_x_cpu_sidecar_artifacts_20260610.zip`.

## Non-Goals

- no NTU GPU job
- no SHA-X canary launch
- no Standard-RealLabel launch
- no full standard/full/v4/new rollout
- no Kaggle submission
- no large label/model-weight upload
