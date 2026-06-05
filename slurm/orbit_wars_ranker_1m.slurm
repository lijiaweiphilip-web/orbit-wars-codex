#!/bin/bash
#SBATCH --job-name=orbit-ranker1m
#SBATCH --partition=MGPU-TC2
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --nodelist=TC2N[03-08]
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=05:50:00
#SBATCH --output=logs/slurm/orbit_ranker1m_%j.out
#SBATCH --error=logs/slurm/orbit_ranker1m_%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs/slurm experiments/ranker_dataset experiments/ranker_model

module load python312

if [[ -n "${VENV_PATH:-}" ]]; then
  source "${VENV_PATH}/bin/activate"
fi

python - <<'PY'
import importlib.util
import subprocess
import sys

missing = [pkg for pkg in ("numpy", "torch") if importlib.util.find_spec(pkg) is None]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "torch", "--index-url", "https://download.pytorch.org/whl/cu121"])
PY

EXAMPLE_COUNT="${EXAMPLE_COUNT:-1000000}"
SEED_START="${SEED_START:-3001}"
EPOCHS="${EPOCHS:-8}"

python tools/generate_orbit_ranker_dataset.py \
  --parents configs/orbit_hard_parents_20260605.json \
  --output experiments/ranker_dataset/orbit_ranker_examples.npz \
  --count "${EXAMPLE_COUNT}" \
  --seed-start "${SEED_START}" \
  --sample-every 5 \
  --max-targets 8

python tools/train_orbit_ranker.py \
  --data experiments/ranker_dataset/orbit_ranker_examples.npz \
  --output-dir experiments/ranker_model \
  --epochs "${EPOCHS}" \
  --batch-size 4096 \
  --hidden 96
