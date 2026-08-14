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
# Omnia Main — Test Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# INSTALL MODES:
#   Default              — Creates .venv/ virtual environment and installs deps
#   Active venv          — Auto-detected; installs into the currently active venv
#
# CREDENTIAL HANDLING:
#   SSH credentials (OIM server):
#     --set-password       — Prompt for SSH password (asks twice for confirmation).
#                            If password already exists, asks yes/no to update.
#     --update-password    — Force-update existing SSH password (prompt twice).
#     --password <pass>    — Set SSH password directly via flag (non-interactive).
#
#   All credentials are written to test_creds.yml and encrypted with ansible-vault.
#   SSH credential flags require oim_server_ip to be set in test_config.yml.
#
# Usage:
#   bash setup_env.sh                        # Create .venv/ and install
#   bash setup_env.sh --force                # Recreate .venv/ from scratch
#   bash setup_env.sh --set-password         # Prompt for SSH password
#   bash setup_env.sh --update-password      # Update existing SSH password
#   bash setup_env.sh --password "secret"    # Set SSH password via flag
#   bash setup_env.sh --debug                # Verbose pip output
#   bash setup_env.sh --help                 # Show this help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"

# ─────────────────────────────────────────────────────────────────────────────
# Colors & helpers
# ─────────────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "  ${BLUE}[...]${NC} $1"; }
ok()    { echo -e "  ${GREEN}[OK]${NC}  $1"; }
warn()  { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "  ${RED}[FAIL]${NC} $1"; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
FORCE=false
DEBUG=false
PIP_QUIET="--quiet"
SET_PASSWORD=false
UPDATE_PASSWORD=false
PASSWORD_VALUE=""
TEST_CONFIG="${SCRIPT_DIR}/test_config.yml"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)        FORCE=true; shift ;;
        --debug)        DEBUG=true; PIP_QUIET=""; shift ;;
        --set-password)    SET_PASSWORD=true; shift ;;
        --update-password) UPDATE_PASSWORD=true; shift ;;
        --password)
            if [[ $# -lt 2 ]]; then
                fail "--password requires a value. Usage: --password <PASSWORD>"
            fi
            PASSWORD_VALUE="$2"
            shift 2
            ;;
        --help|-h)
            echo ""
            echo "Omnia Main — Test Environment Setup"
            echo ""
            echo "Usage: bash setup_env.sh [OPTIONS]"
            echo ""
            echo "INSTALL"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  (no flag)       Create .venv/ and install all dependencies."
            echo "  --force         Delete existing .venv/ and recreate from scratch."
            echo ""
            echo "CREDENTIAL MANAGEMENT"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  SSH credentials are stored in test_creds.yml and encrypted with"
            echo "  Ansible Vault automatically.  oim_server_ip must be set in"
            echo "  test_config.yml for SSH credential flags to work."
            echo ""
            echo "  --set-password  Interactive SSH password setup. Prompts twice for"
            echo "                  confirmation. If already set, asks yes/no to update."
            echo ""
            echo "  --update-password"
            echo "                  Force-update the existing SSH password."
            echo ""
            echo "  --password PWD  Non-interactive SSH password set."
            echo ""
            echo "OTHER"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  --debug         Show verbose pip install output."
            echo "  --help, -h      Show this help message and exit."
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash setup_env.sh [--force] [--debug] [--set-password] [--help]"
            exit 1
            ;;
    esac
done

echo ""
echo "================================================================="
echo "  Omnia Main — Test Environment Setup"
echo "================================================================="
echo ""

# -----------------------------------------------
# Step 1: Check Python 3.12+
# -----------------------------------------------
PYTHON_CMD=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 12 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fail "Python 3.12+ is required but not found. Install: dnf install python3.12 python3.12-pip"
fi

ok "Python: $($PYTHON_CMD --version)"

# -----------------------------------------------
# Step 2: Create virtual environment
# -----------------------------------------------
if [ "$FORCE" = true ] && [ -d "$VENV_DIR" ]; then
    info "Removing existing virtual environment (--force)"
    rm -rf "$VENV_DIR"
fi

if [ -d "$VENV_DIR" ]; then
    ok "Virtual environment already exists: .venv/"
else
    info "Creating virtual environment: .venv/"
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    ok "Virtual environment created"
fi

# -----------------------------------------------
# Step 3: Activate and install dependencies
# -----------------------------------------------
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

info "Upgrading pip"
pip install --upgrade pip $PIP_QUIET

info "Installing dependencies from requirements.txt"
pip install -r "$REQUIREMENTS" $PIP_QUIET

# pytest-order for test ordering
if ! pip show pytest-order &>/dev/null; then
    info "Installing pytest-order"
    pip install pytest-order $PIP_QUIET
fi

ok "All dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Credential setup (--set-password / --update-password / --password)
# ─────────────────────────────────────────────────────────────────────────────

# Check that oim_server_ip is configured in test_config.yml
_check_oim_server_ip() {
    if [ ! -f "$TEST_CONFIG" ]; then
        fail "test_config.yml not found at ${TEST_CONFIG}. Create it first."
    fi
    local oim_ip
    oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -z "$oim_ip" ]; then
        fail "oim_server_ip is blank in test_config.yml. Set the target server IP first:\n         vi ${TEST_CONFIG}"
    fi
    ok "Target server: ${oim_ip}"
}

# _ensure_vault_key — creates .test_creds.key if it does not yet exist.
_ensure_vault_key() {
    if [ ! -f "$CREDS_KEY" ]; then
        info "Generating vault key: .test_creds.key"
        python3 -c "import secrets; print(secrets.token_urlsafe(32)[:32])" > "$CREDS_KEY"
        chmod 600 "$CREDS_KEY"
    fi
}

# _vault_encrypt — encrypt (or re-encrypt) CREDS_FILE.
_vault_encrypt() {
    if command -v ansible-vault &>/dev/null; then
        ansible-vault encrypt "$CREDS_FILE" --vault-password-file "$CREDS_KEY" 2>/dev/null
        ok "Credentials encrypted: test_creds.yml"
    else
        warn "ansible-vault not found — credentials saved as plain text"
        warn "Install ansible-core and re-run to encrypt"
    fi
}

_create_and_encrypt_creds() {
    # Args:  $1 = oim_password
    local _oim_pass="${1:-}"

    # If file already exists and encrypted, preserve existing values
    if [ -f "$CREDS_FILE" ]; then
        local _tmp
        _tmp=$(mktemp)
        if command -v ansible-vault &>/dev/null && grep -q '^\$ANSIBLE_VAULT' "$CREDS_FILE" 2>/dev/null; then
            ansible-vault decrypt --output "$_tmp" \
                --vault-password-file "$CREDS_KEY" "$CREDS_FILE" 2>/dev/null || true
        else
            cp "$CREDS_FILE" "$_tmp"
        fi
        [ -z "$_oim_pass" ] && _oim_pass=$(grep -E '^oim_password:' "$_tmp" | sed 's/^oim_password:[[:space:]]*//; s/[\"'\'']//g' || true)
        rm -f "$_tmp"
    fi

    # Write plain-text creds file
    cat > "$CREDS_FILE" << CREDS_EOF
---
# Omnia Main — test credentials
# Auto-encrypted with Ansible Vault.  Do NOT commit this file.

# SSH password for the remote OIM server (oim_server_ip in test_config.yml).
# Leave empty to use key-based authentication.
oim_password: "${_oim_pass}"
CREDS_EOF
    chmod 600 "$CREDS_FILE"

    _ensure_vault_key
    _vault_encrypt
}

# Prompt for credential with 2x confirmation
# Returns credential via stdout; all prompts/errors go to stderr
_prompt_credential() {
    while true; do
        read -s -r -p "  Password: " _input1
        echo "" >&2
        read -s -r -p "  Confirm:  " _input2
        echo "" >&2

        if [ -z "$_input1" ]; then
            echo -e "  ${RED}Password cannot be empty. Try again.${NC}" >&2
            echo "" >&2
            continue
        fi

        if [ "$_input1" = "$_input2" ]; then
            echo "$_input1"
            return 0
        else
            echo -e "  ${RED}Passwords do not match. Try again.${NC}" >&2
            echo "" >&2
        fi
    done
}

# Ask yes/no with strict validation (loops until valid answer)
_ask_yes_no() {
    local prompt="$1"
    while true; do
        read -r -p "$prompt (yes/no): " answer
        case "$answer" in
            yes|YES|Yes|y|Y) return 0 ;;
            no|NO|No|n|N)   return 1 ;;
            *) echo -e "  ${RED}Please enter 'yes' or 'no'.${NC}" ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# SSH credential dispatch
# ─────────────────────────────────────────────────────────────────────────────
if [ -n "$PASSWORD_VALUE" ]; then
    # --password: non-interactive SSH password set
    _check_oim_server_ip
    info "Setting SSH password from --password flag"
    _create_and_encrypt_creds "$PASSWORD_VALUE"

elif [ "$UPDATE_PASSWORD" = true ]; then
    # --update-password: force update, no "already set" check
    _check_oim_server_ip
    if [ ! -f "$CREDS_FILE" ]; then
        fail "No credentials file found. Use --set-password to create one first."
    fi
    echo ""
    echo -e "  ${CYAN}Update SSH password for the target OIM server.${NC}"
    echo ""
    _cred_input=$(_prompt_credential)
    _create_and_encrypt_creds "$_cred_input"
    ok "SSH password updated successfully"

elif [ "$SET_PASSWORD" = true ]; then
    # --set-password: check if already set, ask to update
    _check_oim_server_ip

    if [ -f "$CREDS_FILE" ]; then
        warn "SSH password is already set (test_creds.yml exists)."
        if _ask_yes_no "  Do you want to update the SSH password?"; then
            echo ""
            echo -e "  ${CYAN}Enter new SSH password for the target OIM server.${NC}"
            echo ""
            _cred_input=$(_prompt_credential)
            _create_and_encrypt_creds "$_cred_input"
            ok "SSH password updated successfully"
        else
            ok "SSH password update skipped. Existing credentials kept."
        fi
    else
        echo ""
        echo -e "  ${CYAN}Enter SSH password for the target OIM server.${NC}"
        echo -e "  ${CYAN}This will be saved to test_creds.yml (encrypted).${NC}"
        echo ""
        _cred_input=$(_prompt_credential)
        _create_and_encrypt_creds "$_cred_input"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ -z "$PASSWORD_VALUE" ] && [ "$UPDATE_PASSWORD" = false ] && [ "$SET_PASSWORD" = false ]; then
    if [ -f "$CREDS_FILE" ]; then
        ok "Credentials file exists: test_creds.yml"
        ok "SSH: re-run with --set-password or --update-password to change"
    else
        warn "No credentials file found (test_creds.yml)"
        warn "SSH creds: bash setup_env.sh --set-password"
    fi
fi

# =============================================================================
# REGISTER run_validation FUNCTION AND TAB COMPLETION IN .venv/bin/activate
# =============================================================================

ACTIVATE_SCRIPT="${VENV_DIR}/bin/activate"
MARKER="# >>> omnia-main-test >>>"
MARKER_END="# <<< omnia-main-test <<<"

# Remove any previous block (idempotent)
if grep -q "${MARKER}" "${ACTIVATE_SCRIPT}" 2>/dev/null; then
    sed -i "/${MARKER}/,/${MARKER_END}/d" "${ACTIVATE_SCRIPT}"
fi

cat >> "${ACTIVATE_SCRIPT}" << 'MAIN_ACTIVATE_EOF'

# >>> omnia-main-test >>>
# Added by setup_env.sh — shell function and tab-completion

# Shell function so run_validation works without ./
run_validation() {
    "${VIRTUAL_ENV%/.venv}/run_validation.sh" "$@"
}

# Tab-completion for run_validation
_run_validation_completions() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    local fvt_dir="${VIRTUAL_ENV%/.venv}/fvt"
    local scenarios=""
    if [ -d "${fvt_dir}" ]; then
        for d in "${fvt_dir}"/*/; do
            [ -d "$d" ] || continue
            local name
            name="$(basename "$d")"
            [ "$name" = "__pycache__" ] && continue
            scenarios="${scenarios} ${name}"
        done
    fi
    local commands="deploy verify test"
    local special="all list help --config --help"
    local options="--suite --marker -v --verbose --debug"
    local markers="sanity functional regression deploy"
    case "$COMP_CWORD" in
        1) COMPREPLY=( $(compgen -W "${scenarios} ${special}" -- "$cur") ) ;;
        2)
            case "$prev" in
                list|help|--help|-h|--config) COMPREPLY=() ;;
                *) COMPREPLY=( $(compgen -W "${commands}" -- "$cur") ) ;;
            esac ;;
        *)
            case "$prev" in
                --suite)
                    local scenario="${COMP_WORDS[1]}"
                    local suites=""
                    if [ -d "${fvt_dir}/${scenario}" ]; then
                        for d in "${fvt_dir}/${scenario}"/*/; do
                            [ -d "$d" ] || continue
                            local name
                            name="$(basename "$d")"
                            [ "$name" = "__pycache__" ] && continue
                            suites="${suites} ${name}"
                        done
                    fi
                    COMPREPLY=( $(compgen -W "${suites}" -- "$cur") ) ;;
                --marker) COMPREPLY=( $(compgen -W "${markers}" -- "$cur") ) ;;
                *) COMPREPLY=( $(compgen -W "${options}" -- "$cur") ) ;;
            esac ;;
    esac
}
complete -F _run_validation_completions run_validation

# <<< omnia-main-test <<<
MAIN_ACTIVATE_EOF

ok "Registered run_validation and tab-completion in venv activate"

echo ""
echo "================================================================="
echo "  Environment Ready"
echo "================================================================="
echo ""
echo "  Next steps:"
echo "    source .venv/bin/activate"
echo "    vi test_config.yml                  # Set oim_server_ip"
echo "    bash setup_env.sh --set-password    # Set SSH password"
echo "    run_validation --help               # Full usage (no ./ needed)"
echo "    run_validation setup verify --marker sanity"
echo ""
echo "================================================================="
echo ""
