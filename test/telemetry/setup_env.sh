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
# Telemetry — Test Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# INSTALL MODES:
#   Baremetal (default)  — Install into system Python (pip install --user)
#   Active venv          — Auto-detected; installs into the currently active venv
#   New venv (--venv)    — Creates .venv/ and installs there
#
# CREDENTIAL HANDLING:
#   SSH credentials (OIM server):
#     --set-password       — Prompt for SSH password (asks twice for confirmation).
#                            If password already exists, asks yes/no to update.
#     --update-password    — Force-update existing SSH password (prompt twice).
#     --password <pass>    — Set SSH password directly via flag (non-interactive).
#
#   Domain credentials (telemetry sources):
#     --set-domain-creds   — Interactive prompt for telemetry credentials:
#                            BMC, MySQL, PowerScale, LDMS, UFM, VAST.
#                            If creds already exist, asks yes/no to update.
#     --domain-creds <json> — Set all domain credentials non-interactively.
#                            Pass as JSON: '{"bmc_username":"x","bmc_password":"y",...}'
#
#   All credentials are written to test_creds.yml and encrypted with ansible-vault.
#   SSH credential flags require oim_server_ip to be set in test_config.yml.
#   Domain credential flags (--set-domain-creds / --domain-creds) do NOT require
#   oim_server_ip — they only write to the local test_creds.yml file.
#
# Usage:
#   bash setup_env.sh                        # Baremetal or active venv
#   bash setup_env.sh --venv                 # Create .venv/ and install there
#   bash setup_env.sh --venv --force         # Recreate .venv/ from scratch
#   bash setup_env.sh --set-password         # Prompt for SSH password
#   bash setup_env.sh --update-password      # Update existing SSH password
#   bash setup_env.sh --password "secret"    # Set SSH password via flag
#   bash setup_env.sh --set-domain-creds     # Prompt for telemetry creds
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
USE_VENV=false
FORCE=false
DEBUG=false
PIP_QUIET="--quiet"
SET_PASSWORD=false
UPDATE_PASSWORD=false
PASSWORD_VALUE=""
SET_DOMAIN_CREDS=false
DOMAIN_CREDS_JSON=""
TEST_CONFIG="${SCRIPT_DIR}/test_config.yml"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)         USE_VENV=true; shift ;;
        --force|-f)     FORCE=true; shift ;;
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
        --set-domain-creds) SET_DOMAIN_CREDS=true; shift ;;
        --domain-creds)
            if [[ $# -lt 2 ]]; then
                fail "--domain-creds requires a JSON value. Usage: --domain-creds '{\"bmc_username\":\"x\",\"bmc_password\":\"y\"}'"
            fi
            DOMAIN_CREDS_JSON="$2"
            shift 2
            ;;
        --help|-h)
            echo ""
            echo "Telemetry — Test Environment Setup"
            echo ""
            echo "Usage: bash setup_env.sh [OPTIONS]"
            echo ""
            echo "INSTALL MODES"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  (no flag)       Baremetal mode (default)."
            echo "                  Installs dependencies into the system Python"
            echo "                  using 'pip install --user'. If a virtual env"
            echo "                  is already activated (VIRTUAL_ENV is set), the"
            echo "                  script auto-detects it and installs there instead."
            echo ""
            echo "  --venv          Create a new .venv/ virtual environment in the"
            echo "                  current directory and install all dependencies"
            echo "                  inside it. After setup, activate with:"
            echo "                    source .venv/bin/activate"
            echo ""
            echo "  --force, -f     Only used with --venv. Deletes the existing .venv/"
            echo "                  directory and recreates it from scratch."
            echo ""
            echo "CREDENTIAL MANAGEMENT — SSH (OIM server access)"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  SSH credentials are stored in test_creds.yml and encrypted with"
            echo "  Ansible Vault automatically.  oim_server_ip must be set in"
            echo "  test_config.yml for SSH credential flags to work."
            echo ""
            echo "  --set-password  Interactive SSH password setup. Prompts twice for"
            echo "                  confirmation. If already set, asks yes/no to update."
            echo ""
            echo "  --update-password"
            echo "                  Force-update the existing SSH password. Prompts twice."
            echo "                  Overwrites test_creds.yml and re-encrypts."
            echo ""
            echo "  --password PWD  Non-interactive SSH password set (overwrites existing)."
            echo ""
            echo "CREDENTIAL MANAGEMENT — Domain (Telemetry Sources)"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  These credentials are passed to the playbook via the domain"
            echo "  credentials input file.  They are stored alongside the SSH"
            echo "  password in test_creds.yml (vault-encrypted)."
            echo "  NOTE: These flags do NOT require oim_server_ip — they only"
            echo "  write to the local test_creds.yml file."
            echo ""
            echo "  --set-domain-creds"
            echo "                  Interactive prompt for:"
            echo "                    bmc_username / bmc_password     — iDRAC BMC"
            echo "                    mysqldb_user / mysqldb_password — MySQL DB"
            echo "                    mysqldb_root_password           — MySQL root"
            echo "                    csi_username / csi_password     — PowerScale CSI"
            echo "                    ldms_sampler_password           — LDMS sampler"
            echo "                    ufm_username / ufm_password     — UFM"
            echo "                    vast_username / vast_password   — VAST"
            echo "                  If already set, asks yes/no to update each field."
            echo ""
            echo "  --domain-creds JSON"
            echo "                  Non-interactive domain cred set via JSON string."
            echo "                  Example:"
            echo "                    --domain-creds '{\"bmc_username\":\"admin\",\"bmc_password\":\"pass\"}'"
            echo ""
            echo "OTHER OPTIONS"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  --debug         Show verbose pip install output (no --quiet flag)."
            echo ""
            echo "  --help, -h      Show this help message and exit."
            echo ""
            echo "EXAMPLES"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  bash setup_env.sh                          # Baremetal install"
            echo "  bash setup_env.sh --venv                   # Create .venv/ and install"
            echo "  bash setup_env.sh --venv --force           # Recreate .venv/ from scratch"
            echo "  bash setup_env.sh --set-password           # Set SSH password (prompt)"
            echo "  bash setup_env.sh --update-password        # Update existing SSH password"
            echo "  bash setup_env.sh --password 'mypass'      # Set SSH password (inline)"
            echo "  bash setup_env.sh --set-domain-creds       # Set telemetry creds (prompt)"
            echo "  bash setup_env.sh --venv --set-password    # Venv + SSH password prompt"
            echo "  bash setup_env.sh --debug                  # Verbose pip output"
            echo ""
            echo "FILES"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  test_config.yml       Target server IP and sync settings"
            echo "  test_creds.yml        All credentials: SSH + telemetry (encrypted)"
            echo "  .test_creds.key       Vault encryption key (auto-generated, gitignored)"
            echo "  requirements.txt      Python dependencies"
            echo ""
            exit 0
            ;;
        *)
            fail "Unknown option: $1 (use --help for usage)"
            ;;
    esac
done

echo ""
echo "================================================================="
echo "  Telemetry — Test Environment Setup"
echo "================================================================="
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Check Python 3.12+
# ─────────────────────────────────────────────────────────────────────────────
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

ok "Python: $($PYTHON_CMD --version 2>&1)"

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Determine install mode
# ─────────────────────────────────────────────────────────────────────────────
INSTALL_MODE="baremetal"
PIP_USER_FLAG="--user"

if [ "$USE_VENV" = true ]; then
    # User explicitly asked to create a venv
    INSTALL_MODE="venv"
    PIP_USER_FLAG=""

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

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    ok "Activated .venv/"

elif [ -n "${VIRTUAL_ENV:-}" ]; then
    # User has their own venv already activated
    INSTALL_MODE="active-venv"
    PIP_USER_FLAG=""
    ok "Detected active virtual environment: ${VIRTUAL_ENV}"

else
    # Baremetal — install into system Python
    INSTALL_MODE="baremetal"
    PIP_USER_FLAG="--user"
    ok "Install mode: baremetal (system Python)"
fi

echo -e "  ${CYAN}Mode:${NC} ${INSTALL_MODE}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
info "Upgrading pip"
pip install --upgrade pip $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
    pip install --upgrade pip $PIP_QUIET

info "Installing dependencies from requirements.txt"
pip install -r "$REQUIREMENTS" $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
    pip install -r "$REQUIREMENTS" $PIP_QUIET

# pytest-order for test ordering
if ! pip show pytest-order &>/dev/null; then
    info "Installing pytest-order"
    pip install pytest-order $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
        pip install pytest-order $PIP_QUIET
fi

ok "All dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Credential setup helpers
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

# _decrypt_creds_temp — decrypt CREDS_FILE to a temp file.
# Sets DECRYPTED_CREDS_TMP and caller MUST clean it up.
_decrypt_creds_temp() {
    DECRYPTED_CREDS_TMP=$(mktemp)
    if command -v ansible-vault &>/dev/null && grep -q '^\$ANSIBLE_VAULT' "$CREDS_FILE" 2>/dev/null; then
        ansible-vault decrypt --output "$DECRYPTED_CREDS_TMP" \
            --vault-password-file "$CREDS_KEY" "$CREDS_FILE" 2>/dev/null || true
    else
        cp "$CREDS_FILE" "$DECRYPTED_CREDS_TMP"
    fi
}

# _read_field_from_file <field> <file> — read a plain-text field value from file.
_read_field_from_file() {
    local _field="$1"
    local _file="$2"
    grep -E "^${_field}:" "$_file" 2>/dev/null \
        | sed "s/^${_field}:[[:space:]]*//; s/[\"']//g" || true
}

_create_and_encrypt_creds() {
    # Args:  $1 = oim_password
    #        $2 = bmc_username, $3 = bmc_password
    #        $4 = mysqldb_user, $5 = mysqldb_password, $6 = mysqldb_root_password
    #        $7 = csi_username, $8 = csi_password
    #        $9 = ldms_sampler_password
    #        $10 = ufm_username, $11 = ufm_password
    #        $12 = vast_username, $13 = vast_password
    local _oim_pass="${1:-}"
    local _bmc_user="${2:-}"
    local _bmc_pass="${3:-}"
    local _mysql_user="${4:-}"
    local _mysql_pass="${5:-}"
    local _mysql_root="${6:-}"
    local _csi_user="${7:-}"
    local _csi_pass="${8:-}"
    local _ldms_pass="${9:-}"
    local _ufm_user="${10:-}"
    local _ufm_pass="${11:-}"
    local _vast_user="${12:-}"
    local _vast_pass="${13:-}"

    # If file already exists, preserve existing values for fields not being updated
    if [ -f "$CREDS_FILE" ]; then
        _decrypt_creds_temp
        [ -z "$_oim_pass" ]   && _oim_pass=$(_read_field_from_file "oim_password" "$DECRYPTED_CREDS_TMP")
        [ -z "$_bmc_user" ]   && _bmc_user=$(_read_field_from_file "bmc_username" "$DECRYPTED_CREDS_TMP")
        [ -z "$_bmc_pass" ]   && _bmc_pass=$(_read_field_from_file "bmc_password" "$DECRYPTED_CREDS_TMP")
        [ -z "$_mysql_user" ] && _mysql_user=$(_read_field_from_file "mysqldb_user" "$DECRYPTED_CREDS_TMP")
        [ -z "$_mysql_pass" ] && _mysql_pass=$(_read_field_from_file "mysqldb_password" "$DECRYPTED_CREDS_TMP")
        [ -z "$_mysql_root" ] && _mysql_root=$(_read_field_from_file "mysqldb_root_password" "$DECRYPTED_CREDS_TMP")
        [ -z "$_csi_user" ]   && _csi_user=$(_read_field_from_file "csi_username" "$DECRYPTED_CREDS_TMP")
        [ -z "$_csi_pass" ]   && _csi_pass=$(_read_field_from_file "csi_password" "$DECRYPTED_CREDS_TMP")
        [ -z "$_ldms_pass" ]  && _ldms_pass=$(_read_field_from_file "ldms_sampler_password" "$DECRYPTED_CREDS_TMP")
        [ -z "$_ufm_user" ]   && _ufm_user=$(_read_field_from_file "ufm_username" "$DECRYPTED_CREDS_TMP")
        [ -z "$_ufm_pass" ]   && _ufm_pass=$(_read_field_from_file "ufm_password" "$DECRYPTED_CREDS_TMP")
        [ -z "$_vast_user" ]  && _vast_user=$(_read_field_from_file "vast_username" "$DECRYPTED_CREDS_TMP")
        [ -z "$_vast_pass" ]  && _vast_pass=$(_read_field_from_file "vast_password" "$DECRYPTED_CREDS_TMP")
        rm -f "$DECRYPTED_CREDS_TMP"
    fi

    # Write plain-text creds file (all fields)
    cat > "$CREDS_FILE" << CREDS_EOF
---
# Telemetry — test credentials
# Auto-encrypted with Ansible Vault.  Do NOT commit this file.

# SSH password for the remote OIM server (oim_server_ip in test_config.yml).
# Leave empty to use key-based authentication.
oim_password: "${_oim_pass}"

# iDRAC BMC credentials
bmc_username: "${_bmc_user}"
bmc_password: "${_bmc_pass}"

# MySQL database credentials for iDRAC telemetry
mysqldb_user: "${_mysql_user}"
mysqldb_password: "${_mysql_pass}"
mysqldb_root_password: "${_mysql_root}"

# CSI PowerScale credentials
csi_username: "${_csi_user}"
csi_password: "${_csi_pass}"

# LDMS sampler credentials
ldms_sampler_password: "${_ldms_pass}"

# UFM telemetry credentials
ufm_username: "${_ufm_user}"
ufm_password: "${_ufm_pass}"

# VAST telemetry credentials
vast_username: "${_vast_user}"
vast_password: "${_vast_pass}"
CREDS_EOF
    chmod 600 "$CREDS_FILE"

    _ensure_vault_key
    _vault_encrypt
}

# _prompt_telemetry_creds — interactive prompt for telemetry domain creds.
_prompt_telemetry_creds() {
    local _existing_bmc_user="" _existing_bmc_pass=""
    local _existing_mysql_user="" _existing_mysql_pass="" _existing_mysql_root=""
    local _existing_csi_user="" _existing_csi_pass=""
    local _existing_ldms_pass=""
    local _existing_ufm_user="" _existing_ufm_pass=""
    local _existing_vast_user="" _existing_vast_pass=""

    if [ -f "$CREDS_FILE" ]; then
        _decrypt_creds_temp
        _existing_bmc_user=$(_read_field_from_file "bmc_username" "$DECRYPTED_CREDS_TMP")
        _existing_bmc_pass=$(_read_field_from_file "bmc_password" "$DECRYPTED_CREDS_TMP")
        _existing_mysql_user=$(_read_field_from_file "mysqldb_user" "$DECRYPTED_CREDS_TMP")
        _existing_mysql_pass=$(_read_field_from_file "mysqldb_password" "$DECRYPTED_CREDS_TMP")
        _existing_mysql_root=$(_read_field_from_file "mysqldb_root_password" "$DECRYPTED_CREDS_TMP")
        _existing_csi_user=$(_read_field_from_file "csi_username" "$DECRYPTED_CREDS_TMP")
        _existing_csi_pass=$(_read_field_from_file "csi_password" "$DECRYPTED_CREDS_TMP")
        _existing_ldms_pass=$(_read_field_from_file "ldms_sampler_password" "$DECRYPTED_CREDS_TMP")
        _existing_ufm_user=$(_read_field_from_file "ufm_username" "$DECRYPTED_CREDS_TMP")
        _existing_ufm_pass=$(_read_field_from_file "ufm_password" "$DECRYPTED_CREDS_TMP")
        _existing_vast_user=$(_read_field_from_file "vast_username" "$DECRYPTED_CREDS_TMP")
        _existing_vast_pass=$(_read_field_from_file "vast_password" "$DECRYPTED_CREDS_TMP")
        rm -f "$DECRYPTED_CREDS_TMP"
    fi

    echo ""
    echo -e "  ${CYAN}Telemetry Domain Credentials${NC}"
    echo -e "  ${CYAN}Press Enter to keep existing value (shown in brackets).${NC}"
    echo ""

    # BMC credentials
    echo -e "  ${YELLOW}iDRAC BMC Credentials:${NC}"
    local _prompt="  BMC Username"
    [ -n "$_existing_bmc_user" ] && _prompt="${_prompt} [${_existing_bmc_user}]"
    read -r -p "${_prompt}: " _new_bmc_user
    local _bmc_user="${_new_bmc_user:-$_existing_bmc_user}"

    read -s -r -p "  BMC Password: " _new_bmc_pass; echo ""
    local _bmc_pass="${_new_bmc_pass:-$_existing_bmc_pass}"

    # MySQL credentials
    echo ""
    echo -e "  ${YELLOW}MySQL Database Credentials (iDRAC):${NC}"
    _prompt="  MySQL User"
    [ -n "$_existing_mysql_user" ] && _prompt="${_prompt} [${_existing_mysql_user}]"
    read -r -p "${_prompt}: " _new_mysql_user
    local _mysql_user="${_new_mysql_user:-$_existing_mysql_user}"

    read -s -r -p "  MySQL Password: " _new_mysql_pass; echo ""
    local _mysql_pass="${_new_mysql_pass:-$_existing_mysql_pass}"

    read -s -r -p "  MySQL Root Password: " _new_mysql_root; echo ""
    local _mysql_root="${_new_mysql_root:-$_existing_mysql_root}"

    # PowerScale CSI credentials
    echo ""
    echo -e "  ${YELLOW}PowerScale CSI Credentials:${NC}"
    _prompt="  CSI Username"
    [ -n "$_existing_csi_user" ] && _prompt="${_prompt} [${_existing_csi_user}]"
    read -r -p "${_prompt}: " _new_csi_user
    local _csi_user="${_new_csi_user:-$_existing_csi_user}"

    read -s -r -p "  CSI Password: " _new_csi_pass; echo ""
    local _csi_pass="${_new_csi_pass:-$_existing_csi_pass}"

    # LDMS credentials
    echo ""
    echo -e "  ${YELLOW}LDMS Sampler Credentials:${NC}"
    read -s -r -p "  LDMS Sampler Password: " _new_ldms_pass; echo ""
    local _ldms_pass="${_new_ldms_pass:-$_existing_ldms_pass}"

    # UFM credentials
    echo ""
    echo -e "  ${YELLOW}UFM Telemetry Credentials:${NC}"
    _prompt="  UFM Username"
    [ -n "$_existing_ufm_user" ] && _prompt="${_prompt} [${_existing_ufm_user}]"
    read -r -p "${_prompt}: " _new_ufm_user
    local _ufm_user="${_new_ufm_user:-$_existing_ufm_user}"

    read -s -r -p "  UFM Password: " _new_ufm_pass; echo ""
    local _ufm_pass="${_new_ufm_pass:-$_existing_ufm_pass}"

    # VAST credentials
    echo ""
    echo -e "  ${YELLOW}VAST Telemetry Credentials:${NC}"
    _prompt="  VAST Username"
    [ -n "$_existing_vast_user" ] && _prompt="${_prompt} [${_existing_vast_user}]"
    read -r -p "${_prompt}: " _new_vast_user
    local _vast_user="${_new_vast_user:-$_existing_vast_user}"

    read -s -r -p "  VAST Password: " _new_vast_pass; echo ""
    local _vast_pass="${_new_vast_pass:-$_existing_vast_pass}"

    echo ""

    # Write back preserving oim_password
    _create_and_encrypt_creds "" "$_bmc_user" "$_bmc_pass" \
        "$_mysql_user" "$_mysql_pass" "$_mysql_root" \
        "$_csi_user" "$_csi_pass" "$_ldms_pass" \
        "$_ufm_user" "$_ufm_pass" "$_vast_user" "$_vast_pass"
}

# Prompt for credential with 2× confirmation
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
    echo -e "  ${CYAN}Existing telemetry credentials are preserved.${NC}"
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
            echo -e "  ${CYAN}Existing telemetry credentials are preserved.${NC}"
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
# Domain credential dispatch  (--set-domain-creds / --domain-creds)
# NOTE: These do NOT require oim_server_ip — they only write to local test_creds.yml.
# ─────────────────────────────────────────────────────────────────────────────
if [ -n "$DOMAIN_CREDS_JSON" ]; then
    # --domain-creds JSON: non-interactive (parse all telemetry credentials)
    info "Setting domain credentials from --domain-creds flag"
    _bmc_user=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('bmc_username',''))" 2>/dev/null || true)
    _bmc_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('bmc_password',''))" 2>/dev/null || true)
    _mysql_user=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('mysqldb_user',''))" 2>/dev/null || true)
    _mysql_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('mysqldb_password',''))" 2>/dev/null || true)
    _mysql_root=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('mysqldb_root_password',''))" 2>/dev/null || true)
    _csi_user=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('csi_username',''))" 2>/dev/null || true)
    _csi_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('csi_password',''))" 2>/dev/null || true)
    _ldms_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ldms_sampler_password',''))" 2>/dev/null || true)
    _ufm_user=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ufm_username',''))" 2>/dev/null || true)
    _ufm_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ufm_password',''))" 2>/dev/null || true)
    _vast_user=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('vast_username',''))" 2>/dev/null || true)
    _vast_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('vast_password',''))" 2>/dev/null || true)
    _create_and_encrypt_creds "" "$_bmc_user" "$_bmc_pass" \
        "$_mysql_user" "$_mysql_pass" "$_mysql_root" \
        "$_csi_user" "$_csi_pass" "$_ldms_pass" \
        "$_ufm_user" "$_ufm_pass" "$_vast_user" "$_vast_pass"
    ok "Domain credentials set"

elif [ "$SET_DOMAIN_CREDS" = true ]; then
    # --set-domain-creds: interactive prompt
    _prompt_telemetry_creds
    ok "Domain credentials saved to test_creds.yml"
fi

# ─────────────────────────────────────────────────────────────────────────────
# No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ -z "$PASSWORD_VALUE" ] && [ "$UPDATE_PASSWORD" = false ] && [ "$SET_PASSWORD" = false ] \
   && [ -z "$DOMAIN_CREDS_JSON" ] && [ "$SET_DOMAIN_CREDS" = false ]; then
    if [ -f "$CREDS_FILE" ]; then
        ok "Credentials file exists: test_creds.yml"
        ok "SSH:    re-run with --set-password or --update-password to change"
        ok "Domain: re-run with --set-domain-creds to update telemetry creds"
    else
        warn "No credentials file found (test_creds.yml)"
        warn "SSH creds:    bash setup_env.sh --set-password"
        warn "Domain creds: bash setup_env.sh --set-domain-creds"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Make scripts executable
# ─────────────────────────────────────────────────────────────────────────────
chmod +x "${SCRIPT_DIR}/run_validation.sh" 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# Tab-completion for run_validation.sh
# ─────────────────────────────────────────────────────────────────────────────
_run_validation_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"
    local domain="telemetry"
    local tags="precheck validate deploy cleanup"
    local commands="exec verify test list help"
    local options="--suite --marker -v --verbose --debug --config"
    local markers="sanity functional sink source deploy nft"

    case "$COMP_CWORD" in
        1)
            # First arg is always the domain name
            COMPREPLY=( $(compgen -W "${domain} --config help --completion" -- "$cur") )
            ;;
        2)
            # After domain: tag or command
            COMPREPLY=( $(compgen -W "${tags} ${commands}" -- "$cur") )
            ;;
        3)
            # After tag: command; after command: options
            if echo " ${tags} " | grep -q " ${prev} "; then
                COMPREPLY=( $(compgen -W "${commands}" -- "$cur") )
            else
                COMPREPLY=( $(compgen -W "${options}" -- "$cur") )
            fi
            ;;
        *)
            case "$prev" in
                --suite)
                    local suites=""
                    local tag_dir=""
                    for w in "${COMP_WORDS[@]}"; do
                        if echo " ${tags} " | grep -q " ${w} "; then
                            tag_dir="${SCRIPT_DIR}/fvt/${w}"
                            break
                        fi
                    done
                    if [ -n "${tag_dir}" ] && [ -d "${tag_dir}" ]; then
                        suites=$(find "${tag_dir}" -mindepth 1 -maxdepth 1 -type d -not -name '__pycache__' -printf '%f\n' 2>/dev/null || true)
                    fi
                    COMPREPLY=( $(compgen -W "${suites}" -- "$cur") )
                    ;;
                --marker)
                    COMPREPLY=( $(compgen -W "${markers}" -- "$cur") )
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "${options}" -- "$cur") )
                    ;;
            esac
            ;;
    esac
}

complete -F _run_validation_completions ./run_validation.sh

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}=================================================================${NC}"
echo -e "${GREEN}  Environment Ready  (${INSTALL_MODE})${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo ""

case "$INSTALL_MODE" in
    venv)
        echo "  Next steps:"
        echo "    source .venv/bin/activate"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh telemetry list"
        ;;
    active-venv)
        echo "  Next steps (venv already active):"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh telemetry list"
        ;;
    baremetal)
        echo "  Next steps:"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh telemetry list"
        ;;
esac

echo ""
echo "  Credentials (two separate types):"
echo ""
echo "    1. SSH credentials (test_creds.yml) — for remote test execution:"
if [ -f "$CREDS_FILE" ]; then
    echo "       test_creds.yml exists (encrypted)"
    echo "       To update:  bash setup_env.sh --set-password"
    echo "       Force update: bash setup_env.sh --update-password"
else
    echo "       No SSH credentials set."
    echo "       For remote mode: bash setup_env.sh --set-password"
fi
echo ""
echo "    2. Telemetry domain credentials (test_creds.yml):"
echo "       BMC, MySQL, PowerScale CSI, LDMS, UFM, VAST"
echo "       To set/update: bash setup_env.sh --set-domain-creds"
echo "       Non-interactive: bash setup_env.sh --domain-creds '{...}'"

echo ""
echo "  Tab-completion enabled for ./run_validation.sh"
echo ""
echo "================================================================="
echo ""
