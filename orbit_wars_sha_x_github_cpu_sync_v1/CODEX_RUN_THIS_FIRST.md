# SHA-X GitHub CPU Sync v1

This pack is CPU-only. It must not submit Kaggle packages, use NTU credentials,
launch SLURM jobs, start SHA-X canary, start standard/full/v4 training, or upload
large labels/model weights.

Run from the repository root:

```bash
python orbit_wars_sha_x_github_cpu_sync_v1/scripts/ci_sha_x_static_guard.py --repo-root . --output-dir experiments/sha_x_github_cpu_sync_v1
python orbit_wars_sha_x_github_cpu_sync_v1/scripts/generate_canary_retry_configs.py --repo-root . --output-dir experiments/sha_x_github_cpu_sync_v1
python orbit_wars_sha_x_github_cpu_sync_v1/scripts/build_github_artifact.py --repo-root . --output-dir experiments/sha_x_github_cpu_sync_v1 --artifact sha_x_cpu_sync_artifacts_20260611.zip
```

Expected artifact:

`experiments/sha_x_github_cpu_sync_v1/sha_x_cpu_sync_artifacts_20260611.zip`
