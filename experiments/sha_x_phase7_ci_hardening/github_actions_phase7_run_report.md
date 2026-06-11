# SHA-X Phase7 GitHub Actions Run Report

Date: `2026-06-11`

## Run

- branch: `phase7-shax-ci-hardening`
- commit: `69b87372bfdd822e086ead1f373232c338cb3934`
- workflow: `SHA-X Phase7 CI Hardening`
- event: `push`
- run id: `27342826592`
- run URL: `https://github.com/lijiaweiphilip-web/orbit-wars-codex/actions/runs/27342826592`
- status: `completed`
- conclusion: `success`

## Remote Step Results

| step | status |
|---|---|
| Checkout | PASS |
| Setup Python | PASS |
| Compile SHA-X scripts | PASS |
| Run phase7 CPU mock tests | PASS |
| Upload artifact | PASS |

## Artifact

- artifact: `sha_x_phase7_ci_hardening_artifacts_20260611.zip`
- artifact id: `7562504496`
- artifact size: `9476` bytes
- artifact digest: `sha256:29532e3342756865ef6f945872cee2c2f8ab9f71ef9132a7c7f165757863c731`

## Test Conclusions

- reward component unit test: `PASS`
- reward components covered: `planet_count_delta`, `production_delta`, `ship_delta`, `target_capture`, `source_overdrain_penalty`, `rank_delta`, `top2_delta`, `win_proxy`, `leader_help_penalty`
- forced-mission trace diff parser test: `PASS`
- compared fields: `source_ships`, `target_ships`, `fleet_count`, `arrival_event`, `owner_change`
- pairwise builder test: `PASS`
- pairwise_rows: `4`
- all-tie case: `LOW_SIGNAL_STATE`
- sbatch safety lint: `PASS`
- no-secret/no-kaggle-submit scan: `PASS`

## Guardrails

- Kaggle submission: `not_started`
- NTU GPU job: `not_started`
- SHA-X canary / standard / full / v4 / rollout: `not_started`
- NTU head-node project Python: `not_used`
- Kaggle token / NTU credential / GitHub Actions secret: `not_used`
- push main / merge main: `not_done`
