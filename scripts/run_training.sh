#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: $0 DATASET_ROOT OUTPUT_ROOT [SEEDS_CONFIG]" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
aether-p3-nowcast check --dataset-root "$1"
aether-p3-nowcast train-runs \
  --dataset-root "$1" \
  --output-root "$2" \
  --seeds-config "${3:-config/seeds.json}"
