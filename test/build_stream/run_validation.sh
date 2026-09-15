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
# build_stream -- Validation Runner
# =============================================================================
# Delegates to the Python validation runner. Environment setup (venv,
# baremetal, dependencies) is handled by setup_env.sh. Prefer the domain
# virtual environment so invocation does not depend on whether the caller
# remembered to activate it.
#
# Usage:
#   ./run_validation.sh fvt_build_stream <tag> <command> [options]
#   ./run_validation.sh fvt_build_stream list
#   ./run_validation.sh --config
#   ./run_validation.sh --help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"

if [[ -x "${VENV_PYTHON}" ]]; then
    PYTHON_BIN="${VENV_PYTHON}"
else
    # setup_env.sh also supports baremetal installation. In that mode there
    # is intentionally no domain .venv, so use the caller's Python.
    PYTHON_BIN="$(command -v python3)"
fi

exec "${PYTHON_BIN}" "${SCRIPT_DIR}/_run.py" "$@"
