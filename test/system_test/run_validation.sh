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
# =============================================================================
# SVT runner entry point: bootstrap .venv when needed, delegate to _run.py.
#   ./run_validation.sh --help
#   ./run_validation.sh svt_<theme> list
#   ./run_validation.sh svt_<theme> <stage>|all [options]
#     stages: initialization cleanup environment_setup system_verification summary
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c 'import pytest, yaml, ruamel.yaml, omnia_auto' 2>/dev/null; then
    "${SCRIPT_DIR}/setup_env.sh" --venv
fi

exec "$VENV_PYTHON" "${SCRIPT_DIR}/_run.py" "$@"
