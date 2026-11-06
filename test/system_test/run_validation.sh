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
# SVT runner entry point (delegates to _run.py with the SVT .venv Python).
#   Prepare the OIM first: ./setup_env.sh (see ./setup_env.sh --help)
#   ./run_validation.sh --help
#   ./run_validation.sh svt_<theme> list
#   ./run_validation.sh svt_<theme> <stage>|all [options]
#     stages: initialization, the theme's stages (build_stream:
#     prepare_build_stream build_deploy cadence automatic_cleanup), summary
#   The Omnia venv is activated here when it is not active yet
#   (<OMNIA_DATA_PATH>/activate-omnia.sh, paths read from /etc/omnia/omnia.env).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"
OMNIA_ENV_FILE="/etc/omnia/omnia.env"
OMNIA_ACTIVATE_SCRIPT="activate-omnia.sh"

if [ ! -x "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c 'import pytest, yaml, ruamel.yaml, omnia_auto' </dev/null 2>/dev/null; then
    echo "ERROR: the SVT .venv is missing or incomplete. HOW TO FIX: run ./setup_env.sh first (see ./setup_env.sh --help)" >&2
    exit 2
fi

# A file sourced here must belong to root (or this user) and be writable by no one else.
_trusted() {
    local owner mode
    [ -f "$1" ] && [ ! -L "$1" ] || return 1
    owner=$(stat -c '%u' "$1") && mode=$(stat -c '%a' "$1") || return 1
    { [ "$owner" = 0 ] || [ "$owner" = "$(id -u)" ]; } && [ $(( 8#$mode & 8#022 )) -eq 0 ]
}

# Activate the Omnia venv (what "source <OMNIA_DATA_PATH>/activate-omnia.sh" does)
# when another or no virtualenv is active. Nothing happens before omnia.sh -s;
# _run.py then reports what is missing.
activate_omnia_venv() {
    local data venv activate
    _trusted "$OMNIA_ENV_FILE" || return 0
    data=$(set +u; set -a; . "$OMNIA_ENV_FILE" >/dev/null 2>&1; echo "${OMNIA_DATA_PATH:-}")
    venv=$(set +u; set -a; . "$OMNIA_ENV_FILE" >/dev/null 2>&1; echo "${OMNIA_VENV_PATH:-}")
    [ -n "$data" ] && [ -n "$venv" ] || return 0
    if [ -n "${VIRTUAL_ENV:-}" ] && [ "$(realpath -m "$VIRTUAL_ENV")" = "$(realpath -m "$venv")" ]; then
        return 0
    fi
    activate="${data%/}/${OMNIA_ACTIVATE_SCRIPT}"
    _trusted "$activate" && [ -f "${venv}/bin/activate" ] || return 0
    set +u
    # shellcheck source=/dev/null  # written by omnia.sh -s; trust checked above
    . "$activate" >/dev/null 2>&1 || true
    set -u
    [ "${VIRTUAL_ENV:-}" = "$venv" ] && echo "Omnia venv activated: ${venv} (${activate})" >&2
    return 0
}
activate_omnia_venv

exec "$VENV_PYTHON" "${SCRIPT_DIR}/_run.py" "$@"
