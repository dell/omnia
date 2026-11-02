#!/bin/bash
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
# SVT stage driver: run the integration stages on this OIM (local or from CI).
# =============================================================================
# Usage: ./run_svt.sh <stage|all> [options]   (./run_svt.sh --help for options)
#
#   stages: initialization cleanup environment_setup system_verification summary
#
# Creates or reuses .venv/ (./setup_env.sh --venv) and delegates to _svt.py.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c 'import pytest, yaml, ruamel.yaml, omnia_auto' 2>/dev/null; then
    "${SCRIPT_DIR}/setup_env.sh" --venv
fi

exec "$VENV_PYTHON" "${SCRIPT_DIR}/_svt.py" "$@"
