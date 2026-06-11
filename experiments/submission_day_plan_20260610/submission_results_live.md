# Submission Results Live - 2026-06-10

Latest refresh: `2026-06-11T16:51:20+08:00`

## 2026-06-11 Single Submission

| slot | package | Kaggle ref | message | status | latest public score |
|---:|---|---:|---|---|---|
| 1 | `N3_top8_home_guard_plus.zip` | `53563011` | `rerun_N3_top8_home_guard_plus_current_main_510_20260611_slot1` | `COMPLETE` | `462.2` |

Guardrail: one Kaggle submission only. No N7, no second submission, no SHA-X learned scorer.

## Slot Check

- observed same-day submissions before the stable batch: 2 (`53537306`, `53536388`)
- assumed daily quota: 5
- remaining submissions before the stable batch: 3
- selected pool: stable `N3/N2/N4`
- action now: all 3 stable-pool submissions are already submitted; no new package submitted on this refresh

## Runtime Gate Recheck

| package | gate source | errors | p95 | result |
|---|---|---:|---:|---|
| `N3_top8_home_guard_plus.zip` | `experiments/s1_top8_neighbor_engineering/runtime_gate_summary.md` | 0 | 0.015409522499976448 | PASS |
| `N2_top8_leader_penalty_plus.zip` | `experiments/s1_top8_neighbor_engineering/runtime_gate_summary.md` | 0 | 0.01561895000001338 | PASS |
| `N4_top8_third_party_steal_penalty_plus.zip` | `experiments/s1_top8_neighbor_engineering/runtime_gate_summary.md` | 0 | 0.01658906916685131 | PASS |

## Submitted Stable Batch

| slot | package | Kaggle ref | message | status | latest public score |
|---:|---|---:|---|---|---:|
| 1 | `N3_top8_home_guard_plus.zip` | `53542478` | `rerun_N3_top8_home_guard_plus_after_490_current_stable_slot1` | `COMPLETE` | 510.2 |
| 2 | `N2_top8_leader_penalty_plus.zip` | `53542496` | `rerun_N2_top8_leader_penalty_plus_after_436_current_stable_slot2` | `COMPLETE` | 415.4 |
| 3 | `N4_top8_third_party_steal_penalty_plus.zip` | `53542519` | `rerun_N4_top8_third_party_steal_penalty_plus_after_427_current_stable_slot3` | `COMPLETE` | 429.3 |

## Earlier Same-Day Context

| package | Kaggle ref | message | status | latest public score |
|---|---:|---|---|---:|
| `N7_top8_leader_thirdparty_snipe_guard.zip` | `53537306` | `N7_top8_leader_thirdparty_snipe_guard_after_N2_drift_426` | `COMPLETE` | 313.8 |
| `N2_top8_leader_penalty_plus.zip` | `53536388` | `rerun_current_best_N2_top8_leader_penalty_plus_after_582` | `COMPLETE` | 436.9 |

## SHA-X GPU Pause Snapshot

- current `squeue -u $USER`: no active jobs listed
- SHA-X canary `25789`: `TIMEOUT`, elapsed `02:00:27`, node `TC2N03`
- pending SHA-X canary found: no
- cancelled pending SHA-X canary: no cancellation needed
- canary left paused; no new NTU GPU job submitted

## Guardrails

- no additional `N7` submission on this refresh
- no SHA-X learned scorer submission
- no full standard started
- no full/v4 training started
- no new rollout started
- no project Python run on the NTU head node
- no TC2N01/TC2N02 used by this refresh
- no other project GPU job killed
