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

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    cat <<EOF
Repo Manager FVT environment setup.

Usage:
  bash setup_env.sh [--venv] [--force] [--set-password] [--password PWD]

Options:
  --venv              Create and install into .venv/
  --force             Recreate .venv/ from scratch
  --set-password      Prompt interactively for OIM SSH password (remote mode)
  --password PWD      Set OIM SSH password non-interactively (remote mode)
  -h, --help          Show this help

Examples:
  bash setup_env.sh --venv
  bash setup_env.sh --venv --force --password 'changeme'
EOF
}

USE_VENV=false
FORCE=false
SET_PASSWORD=false
PASSWORD=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv) USE_VENV=true ;;
        --force) FORCE=true ;;
        --set-password) SET_PASSWORD=true ;;
        --password) PASSWORD="$2"; SET_PASSWORD=true; shift ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown option: $1"; show_help; exit 1 ;;
    esac
    shift
done

if "$FORCE" && "$USE_VENV"; then
    rm -rf "${SCRIPT_DIR}/.venv"
fi

if "$USE_VENV"; then
    if [[ ! -d "${SCRIPT_DIR}/.venv" ]]; then
        python3 -m venv "${SCRIPT_DIR}/.venv"
    fi
    source "${SCRIPT_DIR}/.venv/bin/activate"
fi

pip install --upgrade pip
pip install -r "${SCRIPT_DIR}/requirements.txt"

# Install omnia-auto wheel if not already available
if ! python3 -c "import omnia_auto" 2>/dev/null; then
    pip install "${SCRIPT_DIR}/../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl"
fi

# Set SSH password for remote mode if requested
if "$SET_PASSWORD"; then
    python3 - <<PY
import sys, os
sys.path.insert(0, "${SCRIPT_DIR}")
import omnia_auto
omnia_auto.configure(
    module_root="${SCRIPT_DIR}",
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)
from omnia_auto import encrypt_test_credentials
pwd = """${PASSWORD}"""
if not pwd:
    import getpass
    pwd = getpass.getpass("OIM SSH password: ")
encrypt_test_credentials({"oim_password": pwd})
PY
fi

echo "Environment setup complete."
if "$USE_VENV"; then
    echo "Activate with: source ${SCRIPT_DIR}/.venv/bin/activate"
else
    echo "Run tests with: ${SCRIPT_DIR}/run_validation.sh <scenario> <command> [--marker <expr>]"
fi
