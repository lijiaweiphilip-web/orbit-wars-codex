#!/bin/bash
#SBATCH --job-name=shax1_real_smoke_v2_canary
#SBATCH --nodes=1
#SBATCH --nodelist=TC2N[03-08]
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=logs/slurm/shax1_real_smoke_v2_canary_%j.out
#SBATCH --error=logs/slurm/shax1_real_smoke_v2_canary_%j.err

set -euo pipefail
mkdir -p logs/slurm
cd /home/mcaai/w250001/orbit-wars-codex
VENV_BIN="/home/mcaai/w250001/.conda/envs/t2v/bin"
if [ -f "${VENV_BIN}/activate" ]; then
  source "${VENV_BIN}/activate"
fi
PYTHON="${VENV_BIN}/python"
if [ ! -x "${PYTHON}" ]; then
  echo "BLOCKED: missing executable ${PYTHON}" >&2
  exit 3
fi
export PYTHONPATH="/home/mcaai/w250001/orbit-wars-codex/third_party/kaggle_env_t2v_linux:/home/mcaai/w250001/orbit-wars-codex/third_party/kaggle_environments_vendor:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
OUT="${SHA_X1_REAL_LABEL_OUT:-experiments/sha_x1_real_label_v1_smoke_v2_canary}"
CONFIG="${SHA_X1_REAL_LABEL_CONFIG:-orbit_wars_sha_x1_real_label_v1/configs/smoke_v2_canary_config.json}"
"${PYTHON}" orbit_wars_sha_x1_real_label_v1/scripts/real_label_smoke.py \
  --repo-root . \
  --config "$CONFIG" \
  --output-dir "$OUT"
