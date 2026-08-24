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
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Vault key management
_ensure_vault_key() {
    if [ ! -f "$CREDS_KEY" ]; then
        log_info "Generating vault key: .test_creds.key"
        python3 -c "import secrets; print(secrets.token_urlsafe(32)[:32])" > "$CREDS_KEY"
        chmod 600 "$CREDS_KEY"
    fi
}

_vault_encrypt() {
    if command -v ansible-vault &>/dev/null; then
        ansible-vault encrypt "$CREDS_FILE" --vault-password-file "$CREDS_KEY" 2>/dev/null
        log_info "Credentials encrypted: test_creds.yml"
    else
        log_warn "ansible-vault not found — credentials saved as plain text"
        log_warn "Install ansible-core and re-run to encrypt"
    fi
}

_decrypt_creds_temp() {
    DECRYPTED_CREDS_TMP=$(mktemp)
    if command -v ansible-vault &>/dev/null && grep -q '^\$ANSIBLE_VAULT' "$CREDS_FILE" 2>/dev/null; then
        ansible-vault decrypt --output "$DECRYPTED_CREDS_TMP" \
            --vault-password-file "$CREDS_KEY" "$CREDS_FILE" 2>/dev/null || true
    else
        cp "$CREDS_FILE" "$DECRYPTED_CREDS_TMP"
    fi
}

_read_existing_field() {
    local _field="$1"
    grep -E "^${_field}:" "$CREDS_FILE" 2>/dev/null \
        | sed "s/^${_field}:[[:space:]]*//; s/[\"']//g" || true
}

_create_and_encrypt_creds() {
    # Args:  $1 = oim_password
    #        $2 = bmc_username   (optional; keep existing if not provided)
    #        $3 = bmc_password  (optional; keep existing if not provided)
    local _oim_pass="${1:-}"
    local _bmc_user="${2:-}"
    local _bmc_pass="${3:-}"

    # If file already exists, preserve existing values for fields not being updated
    if [ -f "$CREDS_FILE" ]; then
        _decrypt_creds_temp
        [ -z "$_oim_pass" ]  && _oim_pass=$(grep -E '^oim_password:' "$DECRYPTED_CREDS_TMP" | sed 's/^oim_password:[[:space:]]*//; s/[\"'\'']//g' || true)
        [ -z "$_bmc_user" ]  && _bmc_user=$(grep -E '^bmc_username:' "$DECRYPTED_CREDS_TMP" | sed 's/^bmc_username:[[:space:]]*//; s/[\"'\'']//g' || true)
        [ -z "$_bmc_pass" ]  && _bmc_pass=$(grep -E '^bmc_password:' "$DECRYPTED_CREDS_TMP" | sed 's/^bmc_password:[[:space:]]*//; s/[\"'\'']//g' || true)
        rm -f "$DECRYPTED_CREDS_TMP"
    fi

    # Write plain-text creds file (all fields)
    cat > "$CREDS_FILE" << CREDS_EOF
---
# Utils Domain — test credentials
# Auto-encrypted with Ansible Vault.  Do NOT commit this file.

# SSH password for the remote OIM server (oim_server_ip in test_config.yml).
# Leave empty to use key-based authentication.
oim_password: "${_oim_pass}"

# BMC credentials for PXE boot tests — synced to set_pxe_boot_credentials.yml on the target.
# Required by the set_pxe_boot playbook for iDRAC/BMC access.
bmc_username: "${_bmc_user}"
bmc_password: "${_bmc_pass}"
CREDS_EOF
    chmod 600 "$CREDS_FILE"

    _ensure_vault_key
    _vault_encrypt
}

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
        _create_and_encrypt_creds "${PASSWORD_VALUE}"
        log_info "SSH password updated in test_creds.yml"
    else
        # Interactive mode
        read -sp "Enter SSH password for oim_server_ip: " password
        echo
        _create_and_encrypt_creds "${password}"
        log_info "SSH password saved to test_creds.yml"
    fi
fi

# Handle domain credentials
if [[ "${SET_DOMAIN_CREDS}" == "true" ]]; then
    if [[ -n "${DOMAIN_CREDS_JSON}" ]]; then
        # Non-interactive mode (JSON input)
        _bmc_user=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('bmc_username',''))" 2>/dev/null || true)
        _bmc_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('bmc_password',''))" 2>/dev/null || true)
        _create_and_encrypt_creds "" "$_bmc_user" "$_bmc_pass"
        log_info "BMC credentials updated in test_creds.yml"
    else
        # Interactive mode
        read -p "Enter BMC username: " bmc_user
        read -sp "Enter BMC password: " bmc_pass
        echo
        _create_and_encrypt_creds "" "$bmc_user" "$bmc_pass"
        log_info "BMC credentials saved to test_creds.yml"
    fi
fi

log_info "Setup complete!"
