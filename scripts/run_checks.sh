#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
# AETHER-P3 tests do not depend on third-party pytest plugins.
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest
(
  cd feature_generator
  mvn -q test package
)
