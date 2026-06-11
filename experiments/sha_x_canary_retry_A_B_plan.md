# SHA-X Canary Retry A/B Plan

Date: `2026-06-11`

The canary timeout is treated as a walltime/workload issue, not a RealLabel theory failure.

## Current Evidence

- Dense mini: complete.
- RealLabel smoke v2: pass.
- Key signal: `forced_trace_rate=1.0`, `nonzero_delta_rate=0.8646`, `pairwise_rows=1295`, `label_std=76.79`.
- Canary job `25789`: `TIMEOUT` on `TC2N03` after `02:00:27`.

## Retry Options

| option | config | walltime | workload | when to use |
|---|---|---|---|---|
| A | `orbit_wars_sha_x1_real_label_v1/configs/canary_retry_A_walltime_config.json` | 5h30m-6h | keep current canary workload | best fidelity to current canary |
| B | `orbit_wars_sha_x1_real_label_v1/configs/canary_retry_B_halfworkload_config.json` | 2h | halve states, missions, and horizon | tight GPU window or queue pressure |

Both options include partial checkpoint/report output from the patched `real_label_smoke.py`.

## Guardrails

- retry canary only
- no Standard-RealLabel/full standard/full/v4/new rollout
- one L40S job only when the user confirms
- no TC2N01/TC2N02
- no project Python on NTU head node
- no Kaggle submission
