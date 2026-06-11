# SHA-X Pause And Resume Plan

Archived update: `2026-06-11`

## Current SHA-X State

- Dense mini: complete.
- RealLabel smoke v2: pass.
- Key RealLabel signal: `forced_trace_rate=1.0`, `nonzero_delta_rate=0.8646`, `pairwise_rows=1295`, `label_std=76.79`.
- Standard-RealLabel canary package: ready for retry.
- Latest canary job: `25789`, state `TIMEOUT`, elapsed `02:00:27`, node `TC2N03`.
- Current queue status from prior check: `squeue -u $USER` had no active job.

## Interpretation

The `25789` result is a canary walltime/workload issue, not a theoretical failure of SHA-X RealLabel. Dense mini and RealLabel v2 remain valid. The next SHA-X action is retrying the canary only.

## Pause Decision

Orbit Wars SHA-X GPU work stays paused while NTU GPU capacity is needed by other projects. Do not submit any new NTU GPU job for Orbit Wars during the pause. SHA-X now moves to GitHub Actions CPU-only sidecar mode for static checks, py_compile, retry config generation, dry-run planning, and artifact packaging only.

No pending SHA-X canary is currently recorded, so no cancellation is needed. If a future pending Orbit Wars/SHA-X job appears while the pause is active, cancel only that pending canary and document it.

## Resume Plan

Resume only when L40S capacity is available and the user confirms.

1. Retry Standard-RealLabel canary only.
2. Do not start standard/full standard/full/v4/new rollout.
3. Use `--nodes=1`, `--nodelist=TC2N[03-08]`, and avoid TC2N01/TC2N02.
4. Do not run project Python on the NTU head node.
5. Choose one canary retry option:
   - Option A: raise walltime to 5h30m-6h and keep the current canary workload.
   - Option B: keep walltime at 2h, halve states/missions/horizon, and add checkpoint plus partial report output.
6. After canary finishes, collect reports and write GO/NO_GO.
7. Start Standard-RealLabel only after explicit user confirmation.

## CPU Sidecar Artifacts

- workflow: `.github/workflows/sha_x_cpu_sidecar.yml`
- retry A config: `orbit_wars_sha_x1_real_label_v1/configs/canary_retry_A_walltime_config.json`
- retry B config: `orbit_wars_sha_x1_real_label_v1/configs/canary_retry_B_halfworkload_config.json`
- timeout diagnosis: `experiments/submission_day_plan_20260610/sha_x_canary_timeout_diagnosis.md`
- no-GPU report: `experiments/sha_x_no_gpu_today_report.md`
