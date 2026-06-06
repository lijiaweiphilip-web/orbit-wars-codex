# Phase 5 Sidecar Hard Seed Bank Report

- source_rows: `400`
- generated_categories: `8`

| category | count | note |
|---|---:|---|
| 4p_catastrophic_loss_seeds | 8 | Worst 4p deltas from existing v2/v3 validation. |
| 2p_reversal_seeds | 8 | 2p seeds where challenger lost despite being the candidate branch. |
| leader_snowball_seeds | 8 | Step-100 leader margin already large. |
| symmetric_deadlock_seeds | 8 | Step-100 score band stayed unusually tight. |
| high_comet_interference_seeds | 0 | Not inferable from current artifacts; placeholder category kept empty. |
| sun_geometry_dangerous_seeds | 0 | Not inferable from current CSV-only artifacts; placeholder category kept empty. |
| weak_harvest_backfire_seeds | 8 | Negative delta with high weak_harvest usage. |
| snipe_overfit_seeds | 8 | Negative delta with high snipe usage. |

## Validation Use

- Future v4 validation should always include these seeds in addition to the broad 200-game and 100-game banks.
- Empty categories are preserved intentionally so later telemetry can fill them without changing downstream tooling.
