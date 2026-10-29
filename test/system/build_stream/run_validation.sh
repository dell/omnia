#!/usr/bin/env bash
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
# BuildStream System Verification Test (SVT) — Validation Runner
# =============================================================================
# Runs the SVT scenarios under svt/ (prepare_base -> installation ->
# auto_cleanup -> cleanup). Set up the environment first with ./setup_env.sh.
#
# Usage:
#   ./run_validation.sh svt_build_stream list
#   ./run_validation.sh svt_build_stream test                  full flow
#   ./run_validation.sh svt_build_stream <scenario> <exec|verify|test> [options]
#   ./run_validation.sh svt_build_stream installation verify --marker cadence
#   ./run_validation.sh --config                               test_run_config.yml
#   ./run_validation.sh --help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python3" ]; then
    PYTHON_BIN="${VIRTUAL_ENV}/bin/python3"
elif [ -x "${SCRIPT_DIR}/.venv/bin/python3" ]; then
    PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python3"
fi

if ! "${PYTHON_BIN}" -c "import pytest, yaml, omnia_auto" >/dev/null 2>&1; then
    echo "Error: the test dependencies are not installed for ${PYTHON_BIN}." >&2
    echo "  Run ./setup_env.sh --venv (then: source .venv/bin/activate), or" >&2
    echo "  ./setup_env.sh to install into the active Python environment." >&2
    exit 1
fi

exec "${PYTHON_BIN}" "${SCRIPT_DIR}/_run.py" "$@"
