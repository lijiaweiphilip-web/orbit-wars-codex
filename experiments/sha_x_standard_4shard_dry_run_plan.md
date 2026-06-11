# SHA-X Standard-RealLabel 4-Shard Dry-Run Dependency Graph

Date: `2026-06-11`

Status: dry-run plan only. No `sbatch` command should be run from this document or from GitHub Actions.

## Dependency Graph

```mermaid
flowchart TD
  A["canary retry PASS and GO/NO_GO report"] --> B["standard shard 0 dry-run config"]
  A --> C["standard shard 1 dry-run config"]
  A --> D["standard shard 2 dry-run config"]
  A --> E["standard shard 3 dry-run config"]
  B --> F["merge manifest dry-run"]
  C --> F
  D --> F
  E --> F
  F --> G["standard-real-label GO/NO_GO decision"]
```

## Shard Contract

| shard | dependency | dry-run output | execution status |
|---:|---|---|---|
| 0 | canary retry pass | shard 0 config/manifest only | NOT_SUBMITTED |
| 1 | canary retry pass | shard 1 config/manifest only | NOT_SUBMITTED |
| 2 | canary retry pass | shard 2 config/manifest only | NOT_SUBMITTED |
| 3 | canary retry pass | shard 3 config/manifest only | NOT_SUBMITTED |

## Locks

- Do not run standard until canary retry completes and user confirms.
- Do not submit any 4-shard job from GitHub Actions.
- Do not upload labels or model weights to GitHub.
- Do not use NTU or Kaggle credentials.
