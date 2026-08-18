#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 UTC OUTPUT_DIR" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
aether-p3-nowcast grid \
  --config config/production.json \
  --utc "$1" \
  --output-dir "$2"
