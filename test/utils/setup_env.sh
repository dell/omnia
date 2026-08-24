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
# Utils Domain — Environment Setup Script
# =============================================================================
# One-time setup for the test environment.
# Creates virtual environment, installs dependencies, and configures credentials.
#
# Usage:
#   ./setup_env.sh                    # Basic setup
#   ./setup_env.sh --set-password     # Setup + prompt for SSH password
#   ./setup_env.sh --set-domain-creds # Setup + prompt for BMC credentials
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
PLUGINS_DIR="${SCRIPT_DIR}/../plugins"
WHEEL_PATH="${PLUGINS_DIR}/dist/omnia_auto-1.0.0-py3-none-any.whl"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
SET_PASSWORD=false
SET_DOMAIN_CREDS=false
PASSWORD_VALUE=""
DOMAIN_CREDS_JSON=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --set-password)
            SET_PASSWORD=true
            shift
            ;;
        --update-password)
            SET_PASSWORD=true
            shift
            ;;
        --password)
            PASSWORD_VALUE="$2"
            shift 2
            ;;
        --set-domain-creds)
            SET_DOMAIN_CREDS=true
            shift
            ;;
        --domain-creds)
            DOMAIN_CREDS_JSON="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create virtual environment
if [[ ! -d "${VENV_DIR}" ]]; then
    log_info "Creating virtual environment..."
    python3 -m venv "${VENV_DIR}"
fi

# Activate virtual environment
source "${VENV_DIR}/bin/activate"

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip --quiet

# Install requirements
log_info "Installing requirements..."
pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet

# Install omnia-auto plugin
if [[ -f "${WHEEL_PATH}" ]]; then
    log_info "Installing omnia-auto plugin..."
    pip install "${WHEEL_PATH}" --force-reinstall --quiet
else
    log_warn "omnia-auto wheel not found at ${WHEEL_PATH}"
    log_warn "Build it with: cd ${PLUGINS_DIR} && pip wheel . -w dist/"
fi

log_info "Environment setup complete!"
log_info "Activate with: source ${VENV_DIR}/bin/activate"

# Handle password setting
if [[ "${SET_PASSWORD}" == "true" ]]; then
    if [[ -n "${PASSWORD_VALUE}" ]]; then
        # Non-interactive mode
        python3 -c "
import yaml
with open('${SCRIPT_DIR}/test_creds.yml', 'r') as f:
    creds = yaml.safe_load(f) or {}
creds['oim_password'] = '${PASSWORD_VALUE}'
with open('${SCRIPT_DIR}/test_creds.yml', 'w') as f:
    yaml.dump(creds, f, default_flow_style=False)
"
        log_info "SSH password updated in test_creds.yml"
    else
        # Interactive mode
        read -sp "Enter SSH password for oim_server_ip: " password
        echo
        python3 -c "
import yaml
with open('${SCRIPT_DIR}/test_creds.yml', 'r') as f:
    creds = yaml.safe_load(f) or {}
creds['oim_password'] = '${password}'
with open('${SCRIPT_DIR}/test_creds.yml', 'w') as f:
    yaml.dump(creds, f, default_flow_style=False)
"
        log_info "SSH password saved to test_creds.yml"
    fi
fi

# Handle domain credentials
if [[ "${SET_DOMAIN_CREDS}" == "true" ]]; then
    if [[ -n "${DOMAIN_CREDS_JSON}" ]]; then
        # Non-interactive mode (JSON input)
        python3 -c "
import yaml
import json
with open('${SCRIPT_DIR}/test_creds.yml', 'r') as f:
    creds = yaml.safe_load(f) or {}
domain_creds = json.loads('${DOMAIN_CREDS_JSON}')
creds.update(domain_creds)
with open('${SCRIPT_DIR}/test_creds.yml', 'w') as f:
    yaml.dump(creds, f, default_flow_style=False)
"
        log_info "Domain credentials updated in test_creds.yml"
    else
        # Interactive mode
        read -p "Enter BMC username: " bmc_user
        read -sp "Enter BMC password: " bmc_pass
        echo
        python3 -c "
import yaml
with open('${SCRIPT_DIR}/test_creds.yml', 'r') as f:
    creds = yaml.safe_load(f) or {}
creds['bmc_username'] = '${bmc_user}'
creds['bmc_password'] = '${bmc_pass}'
with open('${SCRIPT_DIR}/test_creds.yml', 'w') as f:
    yaml.dump(creds, f, default_flow_style=False)
"
        log_info "BMC credentials saved to test_creds.yml"
    fi
fi

log_info "Setup complete!"
