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
  bash setup_env.sh [--venv] [--force] [--set-password] [--password-env NAME] [--password-stdin]

Options:
  --venv              Create and install into .venv/
  --force             Recreate .venv/ from scratch
  --set-password      Prompt interactively for OIM SSH password (remote mode)
  --password-env NAME Read the OIM SSH password from the environment variable NAME (remote mode)
  --password-stdin    Read the OIM SSH password from the first line of standard input (remote mode)
  -h, --help          Show this help

Examples:
  bash setup_env.sh --venv
  OIM_PASSWORD='changeme' bash setup_env.sh --venv --force --password-env OIM_PASSWORD
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
        --password-env)
            [[ $# -ge 2 && "$2" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "--password-env needs the name of an environment variable"; exit 1; }
            PASSWORD="${!2:-}"; SET_PASSWORD=true; shift ;;
        --password-stdin) IFS= read -r PASSWORD || true; SET_PASSWORD=true ;;
        --password) echo "--password was removed: a password in the arguments is visible to other users (ps). Use --set-password, --password-env NAME or --password-stdin."; exit 1 ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown option: $1"; show_help; exit 1 ;;
    esac
    shift
done

if [[ -z "${OMNIA_PROJECT_NAME:-}" ]]; then
    echo "[FAIL] OMNIA_PROJECT_NAME is required. Source /etc/omnia/omnia.env (set -a; source /etc/omnia/omnia.env; set +a)."
    exit 1
fi

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
    MODULE_DIR="${SCRIPT_DIR}" OIM_SSH_PASSWORD="${PASSWORD}" python3 - <<'PY'
import os
import sys
module_dir = os.environ["MODULE_DIR"]
sys.path.insert(0, module_dir)
import omnia_auto
omnia_auto.configure(
    module_root=module_dir,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)
import yaml
from omnia_auto import encrypt_test_credentials
pwd = os.environ.get("OIM_SSH_PASSWORD", "")
if not pwd:
    import getpass
    pwd = getpass.getpass("OIM SSH password: ")
creds_file = os.path.join(module_dir, "test_creds.yml")
descriptor = os.open(creds_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
    yaml.safe_dump({"oim_password": pwd}, handle)
encrypt_test_credentials()
PY
fi

echo "Environment setup complete."
if "$USE_VENV"; then
    echo "Activate with: source ${SCRIPT_DIR}/.venv/bin/activate"
else
    echo "Run tests with: ${SCRIPT_DIR}/run_validation.sh <scenario> <command> [--marker <expr>]"
fi
