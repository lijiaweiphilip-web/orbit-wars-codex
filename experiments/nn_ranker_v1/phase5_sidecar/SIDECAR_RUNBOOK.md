# Phase 5 Sidecar Runbook

## Scope

This sidecar exists to prepare Phase 5 validation, ablation, failure analysis,
and packaging gates while the NTU rollout job is still running.

## What Runs Where

### NTU

- rollout label generation on SLURM compute nodes
- later rollout aggregation on a compute node
- no Python on the head node

### GitHub Actions

- CPU-only validation
- pytest and package/runtime gate
- artifact aggregation
- failure-case report generation from public-safe repo artifacts

### Local

- lightweight report generation
- packaging smoke
- runbook maintenance
- sidecar script development

## What Must Never Run On GitHub Actions

- Kaggle token upload
- Kaggle submission
- private secret material
- NTU-only data paths
- GPU training

## Triggering The Validation Workflow

Use `.github/workflows/orbit_sidecar_validation.yml` via `workflow_dispatch`.

Inputs:

- `games`
- `episode_steps`
- `seed_start`
- `seed_count`
- `mode`
- `variant`

Current note:

- the sidecar workflow uses `seed_count` as the authoritative shardable game
  count and treats `games` as a compatibility input that should normally match
  `seed_count`

## Collecting Artifacts

GitHub Actions shards upload:

- `shard_*.csv`
- `shard_*.json`
- shard `failure_cases.jsonl`

Aggregate job writes:

- `experiments/nn_ranker_v1/phase5_sidecar/github_actions_validation/aggregate_report.md`
- `experiments/nn_ranker_v1/phase5_sidecar/github_actions_validation/failure_cases.jsonl`

## Interpreting Reports

- `package_runtime_gate_report.md`
  checks pytest, runtime p95, max runtime, import smoke, fallback, and reset.
- `failure_case_taxonomy.md`
  identifies the recurring 4p failure patterns we should suppress in v4.
- `hard_seed_bank_report.md`
  defines the extra difficult seeds to keep in future validation.
- `ablation_harness_report.md`
  keeps the scorer-versus-candidate and safety-layer comparisons reusable.
- `rollout_label_quality_template.md`
  is the dashboard shell that will be filled once the NTU 20k rollout labels
  are aggregated.

## Merge Path After NTU Job 25490

1. Keep monitoring NTU job `25490` only.
2. Wait until rollout shards complete.
3. Aggregate rollout labels on a compute node or other safe Python environment.
4. If rollout rows are still below `20000`, resume without restarting from zero.
5. Only after `rollout_rows >= 20000` may Phase 5D model selection begin.

## Non-Negotiable Rules

- No Kaggle token in GitHub Actions.
- No Kaggle submission from CI.
- No NTU head-node Python.
- No full training before rollout labels `>= 20000`.
- Current competition gate remains `DO NOT SUBMIT`.
