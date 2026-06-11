# SHA-X Canary Timeout Diagnosis

Archived update: `2026-06-11`

## Observed Result

- job: `25789`
- stage: SHA-X Standard-RealLabel canary
- node: `TC2N03`
- state: `TIMEOUT`
- elapsed: `02:00:27`
- current queue status from prior check: `squeue -u $USER` had no active job

## Diagnosis

This is a walltime/workload timeout, not a RealLabel theory failure.

Evidence:

- Dense mini is complete.
- RealLabel smoke v2 passed.
- RealLabel signal was repaired: `forced_trace_rate=1.0`, `nonzero_delta_rate=0.8646`, `pairwise_rows=1295`, `label_std=76.79`.
- The canary reached the 2-hour limit rather than producing a label-quality rejection.

## Next Action When L40S Is Available

Retry canary only. Do not start Standard-RealLabel, full standard, full/v4 training, or any new rollout.

Choose one retry shape:

| option | change | use when | tradeoff |
|---|---|---|---|
| A | walltime `5h30m-6h`, keep current canary workload | we want the cleanest continuation of the current canary definition | uses more GPU walltime but preserves workload fidelity |
| B | keep `2h`, halve states/missions/horizon, add checkpoint and partial report | GPU window is tight or queue pressure is high | faster answer, but lower canary coverage |

Required safety constraints for either option:

- one L40S job only
- `--nodes=1`
- `--nodelist=TC2N[03-08]`
- no TC2N01/TC2N02
- no project Python on NTU head node
- no Kaggle submission from SHA-X learned scorer
- no automatic promotion to standard/full standard after canary
