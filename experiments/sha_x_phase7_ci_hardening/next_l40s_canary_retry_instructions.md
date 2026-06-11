# Next L40S Canary Retry Instructions

Status: `PLAN_ONLY`

Use the next available L40S window to retry canary only. Do not start Standard-RealLabel automatically.

## Option A

- config: `orbit_wars_sha_x1_real_label_v1/configs/canary_retry_A_walltime_config.json`
- walltime: `05:30:00` to `06:00:00`
- workload: keep current canary workload

## Option B

- config: `orbit_wars_sha_x1_real_label_v1/configs/canary_retry_B_halfworkload_config.json`
- walltime: `02:00:00`
- workload: half states / missions / horizon with partial reports
