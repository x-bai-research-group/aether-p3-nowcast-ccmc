#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

environment_name="${AETHER_P3_ENV_NAME:-aether-p3-nowcast}"
example_utc="2024-05-28T12:00:00Z"
example_filename="aether_p3_nowcast_20240528T120000Z.nc"
reference_file="examples/output/${example_filename}"

if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda is required. Install Miniconda or Anaconda first." >&2
  exit 2
fi

if ! conda run -n "${environment_name}" python --version >/dev/null 2>&1; then
  echo "[setup] creating conda environment: ${environment_name}"
  conda env create --name "${environment_name}" -f environment.yml
fi

echo "[setup] installing AETHER-P3 Nowcast"
conda run --no-capture-output -n "${environment_name}" \
  python -m pip install .

mkdir -p output
output_directory="$(mktemp -d output/example.XXXXXX)"

echo "[example] generating the frozen-model NetCDF"
conda run --no-capture-output -n "${environment_name}" \
  python scripts/run_preprocessed_example.py \
  --input examples/input/preprocessed_example.npz \
  --model-root model \
  --output-dir "${output_directory}"

echo "[example] verifying output against the committed reference"
conda run --no-capture-output -n "${environment_name}" \
  python scripts/verify_example.py \
  --actual "${output_directory}/${example_filename}" \
  --reference "${reference_file}"
