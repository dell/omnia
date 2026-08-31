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
# Image Build Manager — Test Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# INSTALL MODES:
#   Baremetal (default)  — Install into system Python (pip install --user)
#   Active venv          — Auto-detected; installs into the currently active venv
#   New venv (--venv)    — Creates .venv/ and installs there
#
# TWO CREDENTIAL FILES:
#   1. test_creds.yml                — SSH password for OIM server access (local).
#   2. image_build_credentials.yml   — Domain credentials (S3, aarch64).
#      Created at $OMNIA_DATA_PATH/image_build_manager/input/$OMNIA_PROJECT_NAME/
#      and encrypted with ansible-vault.
#
# SSH CREDENTIALS:
#   --set-creds          Interactive prompt (2x confirmation). Asks to update if exists.
#   --update-creds       Force-update existing SSH password (2x prompt).
#   --creds <pass>       Non-interactive SSH password set.
#
# DOMAIN CREDENTIALS:
#   --set-domain-creds     Interactive prompt for S3 + aarch64 creds.
#   --update-domain-creds  Force-update domain credentials.
#   --domain-creds <json>  Non-interactive. JSON: '{"s3_access_id":"x",...}'
#
# Usage:
#   bash setup_env.sh                        # Baremetal or active venv
#   bash setup_env.sh --venv                 # Create .venv/ and install there
#   bash setup_env.sh --venv --force         # Recreate .venv/ from scratch
#   bash setup_env.sh --set-creds            # Prompt for SSH password
#   bash setup_env.sh --update-creds         # Update existing SSH password
#   bash setup_env.sh --creds "secret"       # Set SSH password via flag
#   bash setup_env.sh --set-domain-creds     # Prompt for S3 + aarch64 creds
#   bash setup_env.sh --domain-creds '{...}' # Non-interactive domain creds
#   bash setup_env.sh --debug                # Verbose pip output
#   bash setup_env.sh --help                 # Show this help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"

# ── SSH credentials (local) ──
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"

# ── Domain credentials (at env-var path) ──
DOMAIN_CREDS_FILENAME="image_build_credentials.yml"
DOMAIN_CREDS_KEY_FILENAME=".image_build_credentials_key"
DOMAIN_NAME="image_build_manager"

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
        --force)             FORCE=true; shift ;;
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
                fail "--domain-creds requires JSON. Usage: --domain-creds '{\"s3_access_id\":\"x\"}'"
            fi
            DOMAIN_CREDS_JSON="$2"; shift 2 ;;
        --help|-h)
            cat <<'HELPEOF'

Image Build Manager — Test Environment Setup

Usage: bash setup_env.sh [OPTIONS]

INSTALL MODES
─────────────────────────────────────────────────────────────────
  (no flag)       Baremetal mode (pip install --user).
  --venv          Create .venv/ and install there.
  --force         With --venv: recreate .venv/ from scratch.

SSH CREDENTIALS (test_creds.yml)
─────────────────────────────────────────────────────────────────
  --set-creds     Interactive SSH password setup (2x confirmation).
  --update-creds  Force-update existing SSH password (2x prompt).
  --creds PWD     Non-interactive SSH password set.

DOMAIN CREDENTIALS (image_build_credentials.yml)
─────────────────────────────────────────────────────────────────
  Created at: $OMNIA_DATA_PATH/image_build_manager/input/$OMNIA_PROJECT_NAME/
  Fields: s3_access_id, s3_secret_key, aarch64_ssh_password.

  --set-domain-creds     Interactive prompt for all domain fields.
  --update-domain-creds  Force-update domain creds (no "exists" check).
  --domain-creds JSON    Non-interactive. Example:
    --domain-creds '{"s3_access_id":"key","s3_secret_key":"sec"}'

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
echo "  Image Build Manager — Test Environment Setup"
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
# Step 3: Install dependencies
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
# Step 4: Credential helpers (delegate to omnia_auto credential CLI)
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

# Write domain creds to image_build_credentials.yml (at env-var path)
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
# SSH credential dispatch  (--set-creds / --update-creds / --creds)
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
fi

# ─────────────────────────────────────────────────────────────────────────────
# Domain credential dispatch  (--set-domain-creds / --update-domain-creds / --domain-creds)
# ─────────────────────────────────────────────────────────────────────────────

# Domain credential field spec (JSON for prompt-fields CLI)
DOMAIN_CRED_SPEC='[
  {"field":"s3_access_id","label":"S3 Access ID","group":"S3/MinIO Credentials","secret":false},
  {"field":"s3_secret_key","label":"S3 Secret Key","secret":true},
  {"field":"aarch64_ssh_password","label":"aarch64 SSH Password","group":"aarch64 Build Host","secret":true,"optional":true}
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
        echo -e "  ${CYAN}Image Build Credentials — S3/MinIO + aarch64 build host${NC}"
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
# No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ -z "$CREDS_VALUE" ] && [ "$UPDATE_CREDS" = false ] && [ "$SET_CREDS" = false ] \
   && [ -z "$DOMAIN_CREDS_JSON" ] && [ "$SET_DOMAIN_CREDS" = false ] \
   && [ "$UPDATE_DOMAIN_CREDS" = false ]; then
    if [ -f "$CREDS_FILE" ]; then
        ok "SSH credentials: test_creds.yml (encrypted)"
    else
        warn "No SSH credentials (test_creds.yml)"
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
# Step 5: Make scripts executable
# ─────────────────────────────────────────────────────────────────────────────
chmod +x "${SCRIPT_DIR}/run_validation.sh" 2>/dev/null || true

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
        echo "    ./run_validation.sh fvt_image_build_manager list"
        ;;
    active-venv)
        echo "  Next steps (venv already active):"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh fvt_image_build_manager list"
        ;;
    baremetal)
        echo "  Next steps:"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh fvt_image_build_manager list"
        ;;
esac

echo ""
echo "  Credentials (two separate files):"
echo ""
echo "    1. SSH credentials (test_creds.yml) — for remote test execution:"
if [ -f "$CREDS_FILE" ]; then
    echo "       test_creds.yml exists (encrypted)"
    echo "       To update:  bash setup_env.sh --update-creds"
else
    echo "       Not set. Create with: bash setup_env.sh --set-creds"
fi
echo ""
echo "    2. Image build domain credentials:"
_dc_summary=$(_domain_creds_path)
if [ -f "$_dc_summary" ]; then
    echo "       ${_dc_summary} (encrypted)"
    echo "       To update:  bash setup_env.sh --update-domain-creds"
else
    echo "       Not set. Create with: bash setup_env.sh --set-domain-creds"
fi
echo ""
echo "================================================================="
echo ""
