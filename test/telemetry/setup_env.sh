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
# TWO CREDENTIAL FILES:
#   1. test_creds.yml       — OIM SSH and enabled external appliance credentials
#                              (OME and SFM), stored locally.
#   2. telemetry_credentials.yml — Domain credentials (BMC, MySQL, CSI, LDMS, UFM, VAST).
#      Created at $OMNIA_DATA_PATH/telemetry/input/$OMNIA_PROJECT_NAME/
#      and encrypted with ansible-vault.
#
# TEST CREDENTIALS:
#   --set-creds          Prompt for OIM SSH and enabled OME/SFM credentials.
#   --update-creds       Force-update OIM SSH and enabled OME/SFM credentials.
#   --creds <pass>       Non-interactive OIM SSH password set only.
#
# DOMAIN CREDENTIALS:
#   --set-domain-creds   Interactive prompt for telemetry domain credentials.
#   --update-domain-creds  Force-update domain credentials (no "already set" check).
#   --domain-creds <json>  Non-interactive. JSON: '{"bmc_username":"x",...}'
#
# Usage:
#   bash setup_env.sh                        # Baremetal or active venv
#   bash setup_env.sh --venv                 # Create .venv/ and install there
#   bash setup_env.sh --venv --force         # Recreate .venv/ from scratch
#   bash setup_env.sh --set-creds            # Prompt for test credentials
#   bash setup_env.sh --update-creds         # Update test credentials
#   bash setup_env.sh --creds "secret"       # Set OIM SSH password via flag
#   bash setup_env.sh --set-domain-creds     # Prompt for telemetry creds
#   bash setup_env.sh --domain-creds '{...}' # Non-interactive domain creds
#   bash setup_env.sh --debug                # Verbose pip output
#   bash setup_env.sh --help                 # Show this help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"

# ── Test credentials (local) ──
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"

# ── Domain credentials (at env-var path) ──
DOMAIN_CREDS_FILENAME="telemetry_credentials.yml"
DOMAIN_CREDS_KEY_FILENAME=".telemetry_credentials_key"
DOMAIN_NAME="telemetry"

# ── omnia_auto credential CLI ──
CRED_CLI="python3 -m omnia_auto"

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
# Resolve domain creds path from env vars
# ─────────────────────────────────────────────────────────────────────────────
_resolve_domain_creds_dir() {
    local _data_path="${OMNIA_DATA_PATH:-/opt/omnia}"
    local _project="${OMNIA_PROJECT_NAME:-project_default}"
    echo "${_data_path}/${DOMAIN_NAME}/input/${_project}"
}

_domain_creds_path() {
    echo "$(_resolve_domain_creds_dir)/${DOMAIN_CREDS_FILENAME}"
}

_domain_creds_key_path() {
    echo "$(_resolve_domain_creds_dir)/${DOMAIN_CREDS_KEY_FILENAME}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
USE_VENV=false
FORCE=false
DEBUG=false
PIP_QUIET="--quiet"
SET_CREDS=false
UPDATE_CREDS=false
CREDS_VALUE=""
SET_DOMAIN_CREDS=false
UPDATE_DOMAIN_CREDS=false
DOMAIN_CREDS_JSON=""
TEST_CONFIG="${SCRIPT_DIR}/test_config.yml"

# shellcheck disable=SC2034
while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)              USE_VENV=true; shift ;;
        --force|-f)          FORCE=true; shift ;;
        --debug)             DEBUG=true; PIP_QUIET=""; shift ;;
        --set-creds)         SET_CREDS=true; shift ;;
        --update-creds)      UPDATE_CREDS=true; shift ;;
        --creds)
            if [[ $# -lt 2 ]]; then
                fail "--creds requires a value. Usage: --creds <PASSWORD>"
            fi
            CREDS_VALUE="$2"; shift 2 ;;
        --set-domain-creds)    SET_DOMAIN_CREDS=true; shift ;;
        --update-domain-creds) UPDATE_DOMAIN_CREDS=true; shift ;;
        --domain-creds)
            if [[ $# -lt 2 ]]; then
                fail "--domain-creds requires JSON. Usage: --domain-creds '{\"bmc_username\":\"x\"}'"
            fi
            DOMAIN_CREDS_JSON="$2"; shift 2 ;;
        --help|-h)
            cat <<'HELPEOF'

Telemetry — Test Environment Setup

Usage: bash setup_env.sh [OPTIONS]

INSTALL MODES
─────────────────────────────────────────────────────────────────
  (no flag)       Baremetal mode (pip install --user).
  --venv          Create .venv/ and install there.
  --force, -f     With --venv: recreate .venv/ from scratch.

TEST CREDENTIALS (test_creds.yml)
─────────────────────────────────────────────────────────────────
  --set-creds     Prompt for OIM SSH and enabled OME/SFM credentials.
  --update-creds  Force-update OIM SSH and enabled OME/SFM credentials.
  --creds PWD     Non-interactive OIM SSH password set only.

DOMAIN CREDENTIALS (telemetry_credentials.yml)
─────────────────────────────────────────────────────────────────
  Created at: $OMNIA_DATA_PATH/telemetry/input/$OMNIA_PROJECT_NAME/
  Fields: bmc, mysql, csi, ldms, ufm, vast credentials.

  --set-domain-creds     Interactive prompt for all domain fields.
  --update-domain-creds  Force-update domain creds (no "exists" check).
  --domain-creds JSON    Non-interactive. Example:
    --domain-creds '{"bmc_username":"admin","bmc_password":"pass"}'

OTHER OPTIONS
─────────────────────────────────────────────────────────────────
  --debug         Verbose pip output.
  --help, -h      Show this help.

HELPEOF
            exit 0 ;;
        *)
            fail "Unknown option: $1 (use --help for usage)" ;;
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
# Step 2: Install system dependencies (sshpass for PowerScale syslog config)
# ─────────────────────────────────────────────────────────────────────────────
if command -v dnf &>/dev/null; then
    info "Checking for sshpass (required for PowerScale syslog configuration)"
    if ! command -v sshpass &>/dev/null; then
        info "Installing sshpass via dnf"
        dnf install -y sshpass
        ok "sshpass installed"
    else
        ok "sshpass already installed"
    fi
elif command -v apt-get &>/dev/null; then
    info "Checking for sshpass (required for PowerScale syslog configuration)"
    if ! command -v sshpass &>/dev/null; then
        info "Installing sshpass via apt-get"
        apt-get update -qq && apt-get install -y sshpass
        ok "sshpass installed"
    else
        ok "sshpass already installed"
    fi
else
    warn "Could not install sshpass (dnf/apt-get not found)"
    warn "PowerScale syslog configuration tests may fail"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Determine install mode
# ─────────────────────────────────────────────────────────────────────────────
INSTALL_MODE="baremetal"
PIP_USER_FLAG="--user"

if [ "$USE_VENV" = true ]; then
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
    INSTALL_MODE="active-venv"
    PIP_USER_FLAG=""
    ok "Detected active virtual environment: ${VIRTUAL_ENV}"

else
    INSTALL_MODE="baremetal"
    PIP_USER_FLAG="--user"
    ok "Install mode: baremetal (system Python)"
fi

echo -e "  ${CYAN}Mode:${NC} ${INSTALL_MODE}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
info "Upgrading pip"
pip install --upgrade pip $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
    pip install --upgrade pip $PIP_QUIET

info "Installing dependencies from requirements.txt"
pip install -r "$REQUIREMENTS" $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
    pip install -r "$REQUIREMENTS" $PIP_QUIET

if ! pip show pytest-order &>/dev/null; then
    info "Installing pytest-order"
    pip install pytest-order $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
        pip install pytest-order $PIP_QUIET
fi

ok "All dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Credential helpers (delegate to omnia_auto credential CLI)
# ─────────────────────────────────────────────────────────────────────────────

_show_oim_server_ip() {
    if [ ! -f "$TEST_CONFIG" ]; then
        warn "test_config.yml not found — set oim_server_ip for remote mode."
        return
    fi
    local oim_ip
    oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -n "$oim_ip" ]; then
        ok "Target server: ${oim_ip}"
    else
        warn "oim_server_ip not set — credentials saved locally for later use."
    fi
}

# Write SSH creds to test_creds.yml (local)
_write_ssh_creds() {
    local _pass="$1"
    $CRED_CLI write-fields \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --fields "{\"oim_password\":\"${_pass}\"}" >/dev/null 2>&1
    ok "SSH credentials saved: test_creds.yml (encrypted)"
}

# OME credential field spec (JSON for prompt-fields CLI)
OME_CRED_SPEC='[
  {"field":"ome_username","label":"OME Username","group":"OME Credentials","secret":false},
  {"field":"ome_password","label":"OME Password","secret":true,"confirm":true},
  {"field":"pfx_secret","label":"PFX Secret","secret":true,"optional":true}
]'

# Prompt for OME credentials interactively using Python CLI
_prompt_ome_creds() {
    echo ""
    $CRED_CLI prompt-fields \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --spec "$OME_CRED_SPEC"
    ok "OME credentials saved: test_creds.yml (encrypted)"
}

# SFM credential field spec (JSON for prompt-fields CLI)
SFM_CRED_SPEC='[
  {"field":"sfm_api_username","label":"SFM API Username","group":"SFM API Credentials","secret":false},
  {"field":"sfm_api_password","label":"SFM API Password","secret":true,"confirm":true},
  {"field":"sfm_ssh_username","label":"SFM SSH Username","group":"SFM SSH Credentials","secret":false},
  {"field":"sfm_ssh_password","label":"SFM SSH Password","secret":true,"confirm":true}
]'

# Prompt for SFM credentials interactively using Python CLI
_prompt_sfm_creds() {
    echo ""
    $CRED_CLI prompt-fields \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --spec "$SFM_CRED_SPEC"
    ok "SFM credentials saved: test_creds.yml (encrypted)"
}

# Read a field from test_creds.yml
_read_test_creds_field() {
    local _field="$1"
    $CRED_CLI read-field --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --field "$_field" 2>/dev/null || true
}

# Check if ome_ip is configured in test_config.yml
_get_ome_ip() {
    grep -E '^ome_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^ome_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true
}

# Check if configure_ome is true in test_config.yml
_is_ome_enabled() {
    local _val
    _val=$(grep -E '^configure_ome:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^configure_ome:[[:space:]]*//; s/["'\''[:space:]]//g' || echo "false")
    [ "$_val" = "true" ]
}

# Read SFM endpoints from test_config.yml for prompt context
_get_sfm_api_ip() {
    grep -E '^sfm_api_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^sfm_api_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true
}

_get_sfm_ssh_ip() {
    grep -E '^sfm_ssh_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^sfm_ssh_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true
}

# Check if configure_sfm is true in test_config.yml
_is_sfm_enabled() {
    local _val
    _val=$(grep -E '^configure_sfm:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^configure_sfm:[[:space:]]*//; s/[[:space:]]#.*$//; s/["'\'']//g' \
        | tr '[:upper:]' '[:lower:]' || echo "false")
    [ "$_val" = "true" ]
}

# Write domain creds to telemetry_credentials.yml (at env-var path)
_write_domain_creds() {
    local _json="$1"
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)
    local _dir;  _dir=$(_resolve_domain_creds_dir)

    mkdir -p "$_dir"
    $CRED_CLI write-fields \
        --creds-path "$_path" --key-path "$_key" \
        --fields "$_json" >/dev/null 2>&1
    ok "Domain credentials saved: $_path (encrypted)"
}

# Read a field from the domain creds file
_read_domain_field() {
    local _field="$1"
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)
    $CRED_CLI read-field --creds-path "$_path" --key-path "$_key" \
        --field "$_field" 2>/dev/null || true
}

# Ask yes/no
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
# Step 6: Test credential dispatch  (--set-creds / --update-creds / --creds)
# ─────────────────────────────────────────────────────────────────────────────
if [ -n "$CREDS_VALUE" ]; then
    _show_oim_server_ip
    info "Setting SSH password from --creds flag"
    _write_ssh_creds "$CREDS_VALUE"

elif [ "$UPDATE_CREDS" = true ]; then
    _show_oim_server_ip
    if [ ! -f "$CREDS_FILE" ]; then
        fail "No credentials file found. Use --set-creds to create one first."
    fi
    echo -e "\n  ${CYAN}Update SSH password for the target OIM server.${NC}\n"
    _cred_input=$($CRED_CLI prompt-and-confirm --message "SSH Password")
    _write_ssh_creds "$_cred_input"

    # Also prompt for OME credentials if configure_ome=true
    if _is_ome_enabled; then
        _ome_ip=$(_get_ome_ip)
        echo ""
        if [ -n "$_ome_ip" ]; then
            echo -e "  ${CYAN}OME (OpenManage Enterprise) detected: ${_ome_ip}${NC}"
        else
            echo -e "  ${CYAN}OME telemetry enabled (configure_ome=true)${NC}"
        fi
        echo -e "  ${CYAN}OME credentials required for Kafka forwarder.${NC}"
        _prompt_ome_creds
    fi

    # Also prompt for SFM credentials if configure_sfm=true
    if _is_sfm_enabled; then
        _sfm_api_ip=$(_get_sfm_api_ip)
        _sfm_ssh_ip=$(_get_sfm_ssh_ip)
        echo ""
        if [ -n "$_sfm_api_ip" ] || [ -n "$_sfm_ssh_ip" ]; then
            echo -e "  ${CYAN}SFM detected: API=${_sfm_api_ip:-not set}, SSH=${_sfm_ssh_ip:-not set}${NC}"
        else
            echo -e "  ${CYAN}SFM integration enabled (configure_sfm=true)${NC}"
        fi
        echo -e "  ${CYAN}SFM API and SSH credentials are required.${NC}"
        _prompt_sfm_creds
    fi

elif [ "$SET_CREDS" = true ]; then
    _show_oim_server_ip
    if [ -f "$CREDS_FILE" ]; then
        warn "SSH password is already set (test_creds.yml exists)."
        if _ask_yes_no "  Do you want to update the SSH password?"; then
            echo -e "\n  ${CYAN}Enter new SSH password for the target OIM server.${NC}\n"
            _cred_input=$($CRED_CLI prompt-and-confirm --message "SSH Password")
            _write_ssh_creds "$_cred_input"
        else
            ok "SSH password update skipped."
        fi
    else
        echo -e "\n  ${CYAN}Enter SSH password for the target OIM server.${NC}\n"
        _cred_input=$($CRED_CLI prompt-and-confirm --message "SSH Password")
        _write_ssh_creds "$_cred_input"
    fi

    # Also prompt for OME credentials if configure_ome=true
    if _is_ome_enabled; then
        _ome_ip=$(_get_ome_ip)
        echo ""
        if [ -n "$_ome_ip" ]; then
            echo -e "  ${CYAN}OME (OpenManage Enterprise) detected: ${_ome_ip}${NC}"
        else
            echo -e "  ${CYAN}OME telemetry enabled (configure_ome=true)${NC}"
        fi
        _e_ome_user=$(_read_test_creds_field "ome_username")

        if [ -n "$_e_ome_user" ]; then
            warn "OME credentials already set."
            if _ask_yes_no "  Do you want to update OME credentials?"; then
                _prompt_ome_creds
            else
                ok "OME credentials update skipped."
            fi
        else
            echo -e "  ${CYAN}Enter OME credentials for Kafka forwarder configuration.${NC}"
            _prompt_ome_creds
        fi
    fi

    # Also prompt for SFM credentials if configure_sfm=true
    if _is_sfm_enabled; then
        _sfm_api_ip=$(_get_sfm_api_ip)
        _sfm_ssh_ip=$(_get_sfm_ssh_ip)
        echo ""
        if [ -n "$_sfm_api_ip" ] || [ -n "$_sfm_ssh_ip" ]; then
            echo -e "  ${CYAN}SFM detected: API=${_sfm_api_ip:-not set}, SSH=${_sfm_ssh_ip:-not set}${NC}"
        else
            echo -e "  ${CYAN}SFM integration enabled (configure_sfm=true)${NC}"
        fi
        _e_sfm_api_user=$(_read_test_creds_field "sfm_api_username")
        _e_sfm_api_password=$(_read_test_creds_field "sfm_api_password")
        _e_sfm_ssh_user=$(_read_test_creds_field "sfm_ssh_username")
        _e_sfm_ssh_password=$(_read_test_creds_field "sfm_ssh_password")

        if [ -n "$_e_sfm_api_user" ] \
            && [ -n "$_e_sfm_api_password" ] \
            && [ -n "$_e_sfm_ssh_user" ] \
            && [ -n "$_e_sfm_ssh_password" ]; then
            warn "SFM credentials already set."
            if _ask_yes_no "  Do you want to update SFM credentials?"; then
                _prompt_sfm_creds
            else
                ok "SFM credentials update skipped."
            fi
        else
            echo -e "  ${CYAN}Enter SFM API and SSH credentials.${NC}"
            _prompt_sfm_creds
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Domain credential dispatch  (--set-domain-creds / --update-domain-creds / --domain-creds)
# ─────────────────────────────────────────────────────────────────────────────

# Domain credential field spec (JSON for prompt-fields CLI)
DOMAIN_CRED_SPEC='[
  {"field":"bmc_username","label":"BMC Username","group":"iDRAC BMC Credentials","secret":false},
  {"field":"bmc_password","label":"BMC Password","secret":true},
  {"field":"mysqldb_user","label":"MySQL User","group":"MySQL Database Credentials","secret":false},
  {"field":"mysqldb_password","label":"MySQL Password","secret":true},
  {"field":"mysqldb_root_password","label":"MySQL Root Password","secret":true},
  {"field":"csi_username","label":"CSI Username","group":"PowerScale CSI Credentials","secret":false},
  {"field":"csi_password","label":"CSI Password","secret":true},
  {"field":"ldms_sampler_password","label":"LDMS Sampler Password","group":"LDMS Sampler Credentials","secret":true},
  {"field":"ufm_username","label":"UFM Username","group":"UFM Telemetry Credentials","secret":false},
  {"field":"ufm_password","label":"UFM Password","secret":true},
  {"field":"vast_username","label":"VAST Username","group":"VAST Telemetry Credentials","secret":false},
  {"field":"vast_password","label":"VAST Password","secret":true}
]'

if [ -n "$DOMAIN_CREDS_JSON" ]; then
    info "Setting domain credentials from --domain-creds flag"
    _write_domain_creds "$DOMAIN_CREDS_JSON"

elif [ "$UPDATE_DOMAIN_CREDS" = true ] || [ "$SET_DOMAIN_CREDS" = true ]; then
    _domain_path=$(_domain_creds_path)
    _domain_key=$(_domain_creds_key_path)

    if [ "$SET_DOMAIN_CREDS" = true ] && [ -f "$_domain_path" ]; then
        warn "Domain credentials already exist: $_domain_path"
        if ! _ask_yes_no "  Do you want to update domain credentials?"; then
            ok "Domain credential update skipped."
            SET_DOMAIN_CREDS=false
        fi
    fi

    if [ "$UPDATE_DOMAIN_CREDS" = true ] || [ "$SET_DOMAIN_CREDS" = true ]; then
        echo ""
        echo -e "  ${CYAN}Telemetry Domain Credentials${NC}"
        echo -e "  ${CYAN}Press Enter to keep existing value.${NC}"

        # Use the prompt-fields CLI to handle all prompting
        mkdir -p "$(_resolve_domain_creds_dir)"
        $CRED_CLI prompt-fields \
            --creds-path "$_domain_path" \
            --key-path "$_domain_key" \
            --spec "$DOMAIN_CRED_SPEC"

        echo ""
        ok "Domain credentials saved: $_domain_path (encrypted)"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 8: No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ -z "$CREDS_VALUE" ] && [ "$UPDATE_CREDS" = false ] && [ "$SET_CREDS" = false ] \
   && [ -z "$DOMAIN_CREDS_JSON" ] && [ "$SET_DOMAIN_CREDS" = false ] \
   && [ "$UPDATE_DOMAIN_CREDS" = false ]; then
    if [ -f "$CREDS_FILE" ]; then
        ok "Test credentials: test_creds.yml (encrypted)"
    else
        warn "No test credentials (test_creds.yml)"
        warn "  Set with: bash setup_env.sh --set-creds"
    fi
    _dc=$(_domain_creds_path)
    if [ -f "$_dc" ]; then
        ok "Domain credentials: $_dc (encrypted)"
    else
        warn "No domain credentials: $_dc"
        warn "  Set with: bash setup_env.sh --set-domain-creds"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 9: Make scripts executable
# ─────────────────────────────────────────────────────────────────────────────
chmod +x "${SCRIPT_DIR}/run_validation.sh" 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# Tab-completion for run_validation.sh
# ─────────────────────────────────────────────────────────────────────────────
# shellcheck disable=SC2207
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
            COMPREPLY=( $(compgen -W "${domain} --config help --completion" -- "$cur") )
            ;;
        2)
            COMPREPLY=( $(compgen -W "${tags} ${commands}" -- "$cur") )
            ;;
        3)
            if echo " ${tags} " | grep -q " ${prev} "; then
                COMPREPLY=( $(compgen -W "${commands}" -- "$cur") )
            else
                COMPREPLY=( $(compgen -W "${options}" -- "$cur") )
            fi
            ;;
        *)
            case "$prev" in
                --suite)
                    local suites="" tag_dir=""
                    for w in "${COMP_WORDS[@]}"; do
                        if echo " ${tags} " | grep -q " ${w} "; then
                            tag_dir="${SCRIPT_DIR}/fvt/${w}"; break
                        fi
                    done
                    if [ -n "${tag_dir}" ] && [ -d "${tag_dir}" ]; then
                        suites=$(find "${tag_dir}" -mindepth 1 -maxdepth 1 -type d \
                            -not -name '__pycache__' -printf '%f\n' 2>/dev/null || true)
                    fi
                    COMPREPLY=( $(compgen -W "${suites}" -- "$cur") )
                    ;;
                --marker) COMPREPLY=( $(compgen -W "${markers}" -- "$cur") ) ;;
                *)        COMPREPLY=( $(compgen -W "${options}" -- "$cur") ) ;;
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
echo "  Credentials (two separate files):"
echo ""
echo "    1. Test credentials (test_creds.yml) — OIM SSH and enabled OME/SFM access:"
if [ -f "$CREDS_FILE" ]; then
    echo "       test_creds.yml exists (encrypted)"
    echo "       To update:  bash setup_env.sh --update-creds"
else
    echo "       Not set. Create with: bash setup_env.sh --set-creds"
fi
echo ""
echo "    2. Telemetry domain credentials:"
_dc_summary=$(_domain_creds_path)
if [ -f "$_dc_summary" ]; then
    echo "       ${_dc_summary} (encrypted)"
    echo "       To update:  bash setup_env.sh --update-domain-creds"
else
    echo "       Not set. Create with: bash setup_env.sh --set-domain-creds"
fi
echo ""
echo "  Tab-completion enabled for ./run_validation.sh"
echo ""
echo "================================================================="
echo ""
