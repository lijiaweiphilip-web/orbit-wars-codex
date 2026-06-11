# Orbit Wars SHA-X1 RealLabel v1

Executor package for a controlled Standard-RealLabel smoke.

## Scope

This package turns the SHA-X1 Dense Standard-RealLabel plan into executable scripts.

Run flow is staged:

1. run **v2 canary** (small scale, fixed repair path),
2. review canary quality gates,
3. run standard RealLabel smoke only when canary is approved.

The smoke job verifies:

- real Orbit Wars state extraction from actual games
- candidate mission generation
- forced-mission rollout labeling by deterministic replay with one forced mission
- real label and pairwise sample generation
- tiny mission-value ranker training
- numpy inference export
- full standard dry-run graph generation

## Hard Locks

- Do not submit Kaggle.
- Do not start full standard directly.
- Do not start full/v4 training.
- Do not start a new rollout job outside this explicitly approved smoke.
- Do not run Python on the NTU head node.
- Do not use TC2N01/TC2N02.
- Keep smoke output below 3GB.

## Smoke Commands

### Canary (required first)

```bash
cd /home/mcaai/w250001/orbit-wars-codex
sbatch --export=ALL,SHA_X1_REAL_LABEL_OUT=experiments/sha_x1_real_label_v1_smoke_v2_canary,SHA_X1_REAL_LABEL_CONFIG=orbit_wars_sha_x1_real_label_v1/configs/smoke_v2_canary_config.json \
  orbit_wars_sha_x1_real_label_v1/slurm/01_real_label_smoke_v2_canary.sbatch
```

### Standard smoke (after canary pass)

```bash
cd /home/mcaai/w250001/orbit-wars-codex
sbatch --export=ALL,SHA_X1_REAL_LABEL_OUT=experiments/sha_x1_real_label_v1_smoke_v2 \
  orbit_wars_sha_x1_real_label_v1/slurm/01_real_label_smoke.sbatch
```

Both jobs must run on TC2N03-08 and use:

```bash
source /home/mcaai/w250001/.conda/envs/t2v/bin/activate
```

## Outputs

```text
experiments/sha_x1_real_label_v1_smoke_v2_canary/
experiments/sha_x1_real_label_v1_smoke_v2/
  real_label_smoke_report.md
  label_quality_report.md
  pairwise_quality_report.md
  tiny_train_report.md
  export_report.md
  standard_dry_run_plan.md
  storage_check_report.md
  real_label_sample.csv
  pairwise_sample.csv
  go_no_go_for_standard.md
```
