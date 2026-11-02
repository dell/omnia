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
# System verification test (SVT) - environment setup
# =============================================================================
# Usage: ./setup_env.sh [--venv] [--force] [--debug] [--help]
#
# Installs requirements.txt (pytest, pytest-order, PyYAML, ruamel.yaml and the
# omnia_auto wheel) for the SVT runner, the stage driver and the dataset
# generator. The SVT holds no credentials, so there are no credential options:
# domain credentials belong to each FVT suite (test/<domain>/setup_env.sh).
#
#   (default)        install into the active virtualenv, else for the user
#                    (pip --user)
#   --venv           create or reuse .venv/ and install into it
#   --force          reinstall every requirement (with --venv: recreate .venv/)
#   --debug          show pip output
#   --help           show this help
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
VENV_DIR="${SCRIPT_DIR}/.venv"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
info() { echo -e "  ${BLUE}[...]${NC} $1"; }
ok()   { echo -e "  ${GREEN}[OK]${NC}  $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1" >&2; exit 1; }
usage() { sed -n '/^# Usage:/,/^# ====/p' "${BASH_SOURCE[0]}" | sed '$d; s/^# \{0,1\}//'; }

USE_VENV=false
FORCE=false
PIP_QUIET="--quiet"
while [ $# -gt 0 ]; do
    case "$1" in
        --venv)    USE_VENV=true; shift ;;
        --force)   FORCE=true; shift ;;
        --debug)   PIP_QUIET=""; shift ;;
        --help|-h) usage; exit 0 ;;
        *)         usage; fail "Unknown option: $1" ;;
    esac
done

PYTHON_CMD=""
for candidate in python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
        PYTHON_CMD="$(command -v "$candidate")"
        break
    fi
done
[ -n "$PYTHON_CMD" ] || fail "Python 3.12+ is required (dnf install python3.12 python3.12-pip)"

PIP_USER_FLAG="--user"
if [ "$USE_VENV" = true ]; then
    if [ "$FORCE" = true ] && [ -d "$VENV_DIR" ]; then
        info "Removing .venv/ (--force)"
        rm -rf -- "$VENV_DIR"
    fi
    if [ ! -d "$VENV_DIR" ]; then
        info "Creating .venv/"
        "$PYTHON_CMD" -m venv "$VENV_DIR" </dev/null
    fi
    PYTHON_CMD="${VENV_DIR}/bin/python"
    PIP_USER_FLAG=""
    ok "Install mode: .venv/"
elif [ -n "${VIRTUAL_ENV:-}" ]; then
    PYTHON_CMD="${VIRTUAL_ENV}/bin/python"
    PIP_USER_FLAG=""
    ok "Install mode: active virtualenv ${VIRTUAL_ENV}"
else
    ok "Install mode: user (pip --user)"
fi

PIP_ARGS=(-m pip install --disable-pip-version-check)
[ -n "$PIP_QUIET" ] && PIP_ARGS+=("$PIP_QUIET")
[ -n "$PIP_USER_FLAG" ] && PIP_ARGS+=("$PIP_USER_FLAG")
[ "$FORCE" = true ] && PIP_ARGS+=(--force-reinstall)
info "Installing requirements.txt"
"$PYTHON_CMD" "${PIP_ARGS[@]}" -r "$REQUIREMENTS" </dev/null \
    || fail "pip install -r requirements.txt failed"
"$PYTHON_CMD" -c 'import pytest, pytest_order, yaml, ruamel.yaml, omnia_auto' \
    || fail "requirements are not importable after the installation"
ok "Requirements installed"

echo ""
echo "Next steps:"
[ "$USE_VENV" = true ] && echo "  source .venv/bin/activate"
echo "  ./run_validation.sh --help"
echo "  ./run_validation.sh svt_build_stream list"
