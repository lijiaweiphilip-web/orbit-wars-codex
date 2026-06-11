# SHA-X No-GPU-Today Report

Date: `2026-06-11`

Orbit Wars / SHA-X is in CPU-only sidecar mode today because NTU GPU capacity is reserved for other projects.

## Allowed Today

- GitHub Actions CPU checks.
- Static package structure checks.
- `py_compile` for SHA-X scripts.
- Config/document generation.
- Dry-run dependency graph generation.
- Small artifact zip generation.

## Forbidden Today

- no new NTU GPU job
- no SHA-X canary launch
- no Standard-RealLabel launch
- no full standard/full/v4/new rollout
- no Kaggle submission
- no project Python on NTU head node
- no TC2N01/TC2N02 use
- no Kaggle token or NTU credential use
- no large labels/model weights uploaded to GitHub

## Resume Point

When L40S is available and the user confirms, retry canary only using either retry option A or B.
