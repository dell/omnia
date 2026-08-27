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
# Build Stream — Test Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# INSTALL MODES:
#   Baremetal (default)  — Install into system Python (pip install --user)
#   Active venv          — Auto-detected; installs into the currently active venv
#   New venv (--venv)    — Creates .venv/ and installs there
#
# CREDENTIAL HANDLING:
#   SSH credentials (OIM server — only needed for remote execution):
#     --set-password       — Prompt for SSH password (asks twice for confirmation).
#                            If password already exists, asks yes/no to update.
#     --update-password    — Force-update existing SSH password (prompt twice).
#     --password <pass>    — Set SSH password directly via flag (non-interactive).
#
#   Domain credentials (BuildStream — GitLab, BSM, Postgres):
#     --set-domain-creds   — Interactive prompt for GitLab root password,
#                            GitLab SSH password, BSM auth username/password,
#                            and Postgres username/password.
#                            If creds already exist, asks yes/no to update.
#     --domain-creds <json> — Set all domain credentials non-interactively.
#                            Pass as JSON: '{"gitlab_root_password":"x","gitlab_ssh_password":"y",...}'
#
#   All credentials are written to test_creds.yml and encrypted with ansible-vault.
#   SSH credential flags (--set-password / --password) require oim_server_ip to be
#   set in test_config.yml — they are only needed for remote test execution.
#   Domain credential flags (--set-domain-creds / --domain-creds) do NOT require
#   oim_server_ip — they only write to the local test_creds.yml file.
#
# Usage:
#   bash setup_env.sh                        # Baremetal or active venv
#   bash setup_env.sh --venv                 # Create .venv/ and install there
#   bash setup_env.sh --venv --force         # Recreate .venv/ from scratch
#   bash setup_env.sh --set-password         # Prompt for SSH password (remote mode)
#   bash setup_env.sh --update-password      # Update existing SSH password
#   bash setup_env.sh --password "secret"    # Set SSH password via flag
#   bash setup_env.sh --set-domain-creds     # Prompt for GitLab + BSM + Postgres creds
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
        --set-domain-creds) SET_DOMAIN_CREDS=true; shift ;;
        --domain-creds)
            if [[ $# -lt 2 ]]; then
                fail "--domain-creds requires a JSON value. Usage: --domain-creds '{\"gitlab_root_password\":\"x\",...}'"
            fi
            DOMAIN_CREDS_JSON="$2"
            shift 2
            ;;
        --help|-h)
            echo ""
            echo "Build Stream — Test Environment Setup"
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
            echo "  --force         Only used with --venv. Deletes the existing .venv/"
            echo "                  directory and recreates it from scratch."
            echo ""
            echo "CREDENTIAL MANAGEMENT — SSH (OIM server access)"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  SSH credentials are stored in test_creds.yml and encrypted with"
            echo "  Ansible Vault automatically.  oim_server_ip must be set in"
            echo "  test_config.yml for SSH credential flags to work."
            echo "  NOTE: Only needed for REMOTE test execution. Skip for local mode."
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
            echo "CREDENTIAL MANAGEMENT — Domain (GitLab / BSM / Postgres)"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  These credentials are used by the build_stream playbook during"
            echo "  prepare/deploy phases.  They are stored alongside the SSH"
            echo "  password in test_creds.yml (vault-encrypted)."
            echo "  NOTE: These flags do NOT require oim_server_ip — they only"
            echo "  write to the local test_creds.yml file."
            echo ""
            echo "  --set-domain-creds"
            echo "                  Interactive prompt for:"
            echo "                    gitlab_root_password       — GitLab root user password"
            echo "                    gitlab_ssh_password        — SSH password for GitLab host"
            echo "                    build_stream_auth_username — BSM API auth username"
            echo "                    build_stream_auth_password — BSM API auth password"
            echo "                    postgres_user              — Postgres DB username"
            echo "                    postgres_password          — Postgres DB password"
            echo "                  If already set, asks yes/no to update each field."
            echo ""
            echo "  --domain-creds JSON"
            echo "                  Non-interactive domain cred set via JSON string."
            echo "                  Example:"
            echo "                    --domain-creds '{\"gitlab_root_password\":\"pass\",\"gitlab_ssh_password\":\"pass\"}'"
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
            echo "  bash setup_env.sh --set-password           # Set SSH password (remote mode)"
            echo "  bash setup_env.sh --update-password        # Update existing SSH password"
            echo "  bash setup_env.sh --password 'mypass'      # Set SSH password (inline)"
            echo "  bash setup_env.sh --set-domain-creds       # Set GitLab/BSM/Postgres creds"
            echo "  bash setup_env.sh --venv --set-domain-creds  # Venv + domain creds prompt"
            echo "  bash setup_env.sh --debug                  # Verbose pip output"
            echo ""
            echo "FILES"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  test_config.yml       Target server IP and sync settings"
            echo "  test_creds.yml        All credentials: SSH + domain (encrypted)"
            echo "  .test_creds.key       Vault encryption key (auto-generated, gitignored)"
            echo "  .run_validation_rc    Sourceable shell snippet (baremetal mode)"
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
echo "  Build Stream — Test Environment Setup"
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
# Step 4: Credential helpers
# ─────────────────────────────────────────────────────────────────────────────

# Check that oim_server_ip is configured in test_config.yml (SSH only)
_check_oim_server_ip() {
    if [ ! -f "$TEST_CONFIG" ]; then
        fail "test_config.yml not found at ${TEST_CONFIG}. Create it first."
    fi
    local oim_ip
    oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -z "$oim_ip" ]; then
        fail "oim_server_ip is blank in test_config.yml. Set the target server IP first:\n         vi ${TEST_CONFIG}\n         SSH password is only needed for remote test execution."
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

# _read_field_from_tmp <field> — read a plain-text field value from DECRYPTED_CREDS_TMP.
_read_field_from_tmp() {
    local _field="$1"
    grep -E "^${_field}:" "$DECRYPTED_CREDS_TMP" 2>/dev/null \
        | sed "s/^${_field}:[[:space:]]*//; s/[\"']//g" || true
}

_create_and_encrypt_creds() {
    # Args:  $1 = oim_password   (optional; keep existing if empty)
    #        $2 = gitlab_root_password (optional)
    #        $3 = gitlab_ssh_password  (optional)
    #        $4 = build_stream_auth_username (optional)
    #        $5 = build_stream_auth_password (optional)
    #        $6 = postgres_user        (optional)
    #        $7 = postgres_password    (optional)
    local _oim_pass="${1:-}"
    local _gl_root="${2:-}"
    local _gl_ssh="${3:-}"
    local _bs_user="${4:-}"
    local _bs_pass="${5:-}"
    local _pg_user="${6:-}"
    local _pg_pass="${7:-}"

    # If file already exists, preserve existing values for fields not being updated
    if [ -f "$CREDS_FILE" ]; then
        _decrypt_creds_temp
        [ -z "$_oim_pass" ] && _oim_pass=$(_read_field_from_tmp "oim_password")
        [ -z "$_gl_root" ]  && _gl_root=$(_read_field_from_tmp "gitlab_root_password")
        [ -z "$_gl_ssh" ]   && _gl_ssh=$(_read_field_from_tmp "gitlab_ssh_password")
        [ -z "$_bs_user" ]  && _bs_user=$(_read_field_from_tmp "build_stream_auth_username")
        [ -z "$_bs_pass" ]  && _bs_pass=$(_read_field_from_tmp "build_stream_auth_password")
        [ -z "$_pg_user" ]  && _pg_user=$(_read_field_from_tmp "postgres_user")
        [ -z "$_pg_pass" ]  && _pg_pass=$(_read_field_from_tmp "postgres_password")
        rm -f "$DECRYPTED_CREDS_TMP"
    fi

    # Write plain-text creds file (all fields)
    cat > "$CREDS_FILE" << CREDS_EOF
---
# Build Stream — test credentials
# Auto-encrypted with Ansible Vault.  Do NOT commit this file.

# SSH password for the remote OIM server (oim_server_ip in test_config.yml).
# Leave empty for key-based authentication or local execution.
oim_password: "${_oim_pass}"

# GitLab root user password (set during GitLab installation).
# Required for API operations and runner registration.
gitlab_root_password: "${_gl_root}"

# SSH password for the GitLab server host.
# Required for passwordless SSH setup between OIM and GitLab host.
gitlab_ssh_password: "${_gl_ssh}"

# BuildStream Manager (BSM) API authentication credentials.
# Used by BSM registrar for API access.
build_stream_auth_username: "${_bs_user}"
build_stream_auth_password: "${_bs_pass}"

# Postgres database credentials for BSM.
# Used by the build_stream_db container.
postgres_user: "${_pg_user}"
postgres_password: "${_pg_pass}"
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

# _prompt_domain_creds — interactive prompt for BuildStream domain credentials.
# Reads existing values from a decrypted copy; shows current value as default.
_prompt_domain_creds() {
    local _existing_gl_root="" _existing_gl_ssh=""
    local _existing_bs_user="" _existing_bs_pass=""
    local _existing_pg_user="" _existing_pg_pass=""

    if [ -f "$CREDS_FILE" ]; then
        _decrypt_creds_temp
        _existing_gl_root=$(_read_field_from_tmp "gitlab_root_password")
        _existing_gl_ssh=$(_read_field_from_tmp "gitlab_ssh_password")
        _existing_bs_user=$(_read_field_from_tmp "build_stream_auth_username")
        _existing_bs_pass=$(_read_field_from_tmp "build_stream_auth_password")
        _existing_pg_user=$(_read_field_from_tmp "postgres_user")
        _existing_pg_pass=$(_read_field_from_tmp "postgres_password")
        rm -f "$DECRYPTED_CREDS_TMP"
    fi

    echo ""
    echo -e "  ${CYAN}BuildStream Domain Credentials${NC}"
    echo -e "  ${CYAN}──────────────────────────────────────────────────────────${NC}"
    echo ""

    # --- GitLab Root Password (mandatory) ---
    echo -e "  ${YELLOW}1/6${NC} GitLab Root Password ${CYAN}[MANDATORY]${NC}"
    if [ -n "$_existing_gl_root" ]; then
        echo -e "       Current: ${CYAN}(set)${NC}"
    fi
    echo -e "       ${CYAN}(hidden input)${NC}"
    read -s -r -p "  GitLab Root Password: " _new_gl_root1; echo ""
    if [ -n "$_new_gl_root1" ]; then
        read -s -r -p "  Confirm:              " _new_gl_root2; echo ""
        if [ "$_new_gl_root1" != "$_new_gl_root2" ]; then
            fail "GitLab root passwords do not match. Re-run --set-domain-creds."
        fi
        _existing_gl_root="$_new_gl_root1"
    else
        [ -n "$_existing_gl_root" ] && warn "GitLab root password unchanged (kept existing)." || \
            fail "GitLab root password is mandatory. Cannot be empty."
    fi
    echo ""

    # --- GitLab SSH Password (mandatory) ---
    echo -e "  ${YELLOW}2/6${NC} GitLab SSH Password ${CYAN}[MANDATORY]${NC}"
    if [ -n "$_existing_gl_ssh" ]; then
        echo -e "       Current: ${CYAN}(set)${NC}"
    fi
    echo -e "       ${CYAN}(hidden input)${NC}"
    read -s -r -p "  GitLab SSH Password: " _new_gl_ssh1; echo ""
    if [ -n "$_new_gl_ssh1" ]; then
        read -s -r -p "  Confirm:             " _new_gl_ssh2; echo ""
        if [ "$_new_gl_ssh1" != "$_new_gl_ssh2" ]; then
            fail "GitLab SSH passwords do not match. Re-run --set-domain-creds."
        fi
        _existing_gl_ssh="$_new_gl_ssh1"
    else
        [ -n "$_existing_gl_ssh" ] && warn "GitLab SSH password unchanged (kept existing)." || \
            fail "GitLab SSH password is mandatory. Cannot be empty."
    fi
    echo ""

    # --- BSM Auth Username ---
    echo -e "  ${YELLOW}3/6${NC} BuildStream Auth Username ${CYAN}[CONDITIONAL]${NC}"
    local _prompt_bs_user="  BSM Auth Username"
    [ -n "$_existing_bs_user" ] && _prompt_bs_user="${_prompt_bs_user} [current: ${_existing_bs_user}]"
    read -r -p "${_prompt_bs_user}: " _new_bs_user
    _existing_bs_user="${_new_bs_user:-$_existing_bs_user}"
    echo ""

    # --- BSM Auth Password ---
    echo -e "  ${YELLOW}4/6${NC} BuildStream Auth Password ${CYAN}[CONDITIONAL]${NC}"
    if [ -n "$_existing_bs_pass" ]; then
        echo -e "       Current: ${CYAN}(set)${NC}"
    fi
    echo -e "       ${CYAN}(hidden input)${NC}"
    read -s -r -p "  BSM Auth Password: " _new_bs_pass1; echo ""
    if [ -n "$_new_bs_pass1" ]; then
        read -s -r -p "  Confirm:           " _new_bs_pass2; echo ""
        if [ "$_new_bs_pass1" != "$_new_bs_pass2" ]; then
            fail "BSM auth passwords do not match. Re-run --set-domain-creds."
        fi
        _existing_bs_pass="$_new_bs_pass1"
    else
        [ -n "$_existing_bs_pass" ] && warn "BSM auth password unchanged (kept existing)."
    fi
    echo ""

    # --- Postgres Username ---
    echo -e "  ${YELLOW}5/6${NC} Postgres Username ${CYAN}[CONDITIONAL]${NC}"
    local _prompt_pg_user="  Postgres Username"
    [ -n "$_existing_pg_user" ] && _prompt_pg_user="${_prompt_pg_user} [current: ${_existing_pg_user}]"
    read -r -p "${_prompt_pg_user}: " _new_pg_user
    _existing_pg_user="${_new_pg_user:-$_existing_pg_user}"
    echo ""

    # --- Postgres Password ---
    echo -e "  ${YELLOW}6/6${NC} Postgres Password ${CYAN}[CONDITIONAL]${NC}"
    if [ -n "$_existing_pg_pass" ]; then
        echo -e "       Current: ${CYAN}(set)${NC}"
    fi
    echo -e "       ${CYAN}(hidden input)${NC}"
    read -s -r -p "  Postgres Password: " _new_pg_pass1; echo ""
    if [ -n "$_new_pg_pass1" ]; then
        read -s -r -p "  Confirm:           " _new_pg_pass2; echo ""
        if [ "$_new_pg_pass1" != "$_new_pg_pass2" ]; then
            fail "Postgres passwords do not match. Re-run --set-domain-creds."
        fi
        _existing_pg_pass="$_new_pg_pass1"
    else
        [ -n "$_existing_pg_pass" ] && warn "Postgres password unchanged (kept existing)."
    fi
    echo ""

    # Write back preserving oim_password
    _create_and_encrypt_creds "" \
        "$_existing_gl_root" "$_existing_gl_ssh" \
        "$_existing_bs_user" "$_existing_bs_pass" \
        "$_existing_pg_user" "$_existing_pg_pass"
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
    echo -e "  ${CYAN}Existing domain credentials are preserved.${NC}"
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
            echo -e "  ${CYAN}Existing domain credentials are preserved.${NC}"
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
#
# Domain credentials are primarily stored on the target server at:
#   /opt/omnia/build_stream/input/<project>/build_stream_credentials.yml
#
# The build_stream.yml playbook creates this file during deployment.
# --set-domain-creds checks the server first; if creds already exist
# there, prompting is skipped.
# ─────────────────────────────────────────────────────────────────────────────

# Check if domain credentials already exist on the target server
_check_server_creds_exist() {
    local oim_ip
    oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -z "$oim_ip" ]; then
        return 1  # can't check server, proceed with prompts
    fi

    local server_creds_path="/opt/omnia/build_stream/input/project_default/build_stream_credentials.yml"

    # Try SSH to check if the file exists and has content
    local ssh_result
    ssh_result=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
        "$oim_ip" "test -s ${server_creds_path} && echo 'exists'" 2>/dev/null || true)

    if [ "$ssh_result" = "exists" ]; then
        return 0  # creds exist on server
    fi
    return 1  # creds don't exist or SSH failed
}

if [ -n "$DOMAIN_CREDS_JSON" ]; then
    # --domain-creds JSON: non-interactive
    info "Setting domain credentials from --domain-creds flag"
    _gl_root=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('gitlab_root_password',''))" 2>/dev/null || true)
    _gl_ssh=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('gitlab_ssh_password',''))" 2>/dev/null || true)
    _bs_user=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('build_stream_auth_username',''))" 2>/dev/null || true)
    _bs_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('build_stream_auth_password',''))" 2>/dev/null || true)
    _pg_user=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('postgres_user',''))" 2>/dev/null || true)
    _pg_pass=$(echo "$DOMAIN_CREDS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('postgres_password',''))" 2>/dev/null || true)
    _create_and_encrypt_creds "" "$_gl_root" "$_gl_ssh" "$_bs_user" "$_bs_pass" "$_pg_user" "$_pg_pass"
    ok "Domain credentials set"

elif [ "$SET_DOMAIN_CREDS" = true ]; then
    # --set-domain-creds: check server first before prompting
    if _check_server_creds_exist; then
        ok "Domain credentials already configured on the target server."
        ok "Source: /opt/omnia/build_stream/input/project_default/build_stream_credentials.yml"
        ok "Test cases will read credentials directly from the server."
        ok "To force update, use: --domain-creds '{...}'"
    else
        info "Server credentials not found — prompting for domain credentials"
        _prompt_domain_creds
        ok "Domain credentials saved to test_creds.yml"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ -z "$PASSWORD_VALUE" ] && [ "$UPDATE_PASSWORD" = false ] && [ "$SET_PASSWORD" = false ] \
   && [ -z "$DOMAIN_CREDS_JSON" ] && [ "$SET_DOMAIN_CREDS" = false ]; then
    if [ -f "$CREDS_FILE" ]; then
        ok "Credentials file exists: test_creds.yml"
        ok "SSH:    re-run with --set-password or --update-password to change"
        ok "Domain: re-run with --set-domain-creds to update GitLab/BSM/Postgres creds"
    else
        warn "No credentials file found (test_creds.yml)"
        warn "SSH creds:    bash setup_env.sh --set-password       (remote mode only)"
        warn "Domain creds: bash setup_env.sh --set-domain-creds   (GitLab/BSM/Postgres)"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Register run_validation + tab completion (venv modes only)
# ─────────────────────────────────────────────────────────────────────────────
_inject_tab_completion() {
    local activate_script="$1"
    local marker="# >>> build-stream-test >>>"
    local marker_end="# <<< build-stream-test <<<"
    local module_dir="$SCRIPT_DIR"

    # Remove any previous block (idempotent)
    if grep -q "${marker}" "${activate_script}" 2>/dev/null; then
        sed -i "/${marker}/,/${marker_end}/d" "${activate_script}"
    fi

    cat >> "${activate_script}" << BSM_ACTIVATE_EOF

${marker}
# Added by setup_env.sh — shell function and tab-completion

# Shell function so run_validation works without ./
run_validation() {
    "${module_dir}/run_validation.sh" "\$@"
}

# Tab-completion for run_validation
_run_validation_completions() {
    local cur prev
    cur="\${COMP_WORDS[COMP_CWORD]}"
    prev="\${COMP_WORDS[COMP_CWORD-1]}"
    local fvt_dir="${module_dir}/fvt"
    local scenarios=""
    if [ -d "\${fvt_dir}" ]; then
        for d in "\${fvt_dir}"/*/; do
            [ -d "\$d" ] || continue
            local name
            name="\$(basename "\$d")"
            [ "\$name" = "__pycache__" ] && continue
            scenarios="\${scenarios} \${name}"
        done
    fi
    local commands="deploy verify test"
    local special="all list help --config --help"
    local options="--suite --marker -v --verbose --debug"
    local markers="sanity functional regression deploy"
    case "\$COMP_CWORD" in
        1) COMPREPLY=( \$(compgen -W "\${scenarios} \${special}" -- "\$cur") ) ;;
        2)
            case "\$prev" in
                list|help|--help|-h|--config) COMPREPLY=() ;;
                *) COMPREPLY=( \$(compgen -W "\${commands}" -- "\$cur") ) ;;
            esac ;;
        *)
            case "\$prev" in
                --suite)
                    local scenario="\${COMP_WORDS[1]}"
                    local suites=""
                    if [ -d "\${fvt_dir}/\${scenario}" ]; then
                        for d in "\${fvt_dir}/\${scenario}"/*/; do
                            [ -d "\$d" ] || continue
                            local name
                            name="\$(basename "\$d")"
                            [ "\$name" = "__pycache__" ] && continue
                            suites="\${suites} \${name}"
                        done
                    fi
                    COMPREPLY=( \$(compgen -W "\${suites}" -- "\$cur") ) ;;
                --marker) COMPREPLY=( \$(compgen -W "\${markers}" -- "\$cur") ) ;;
                *) COMPREPLY=( \$(compgen -W "\${options}" -- "\$cur") ) ;;
            esac ;;
    esac
}
complete -F _run_validation_completions run_validation

${marker_end}
BSM_ACTIVATE_EOF
}

if [ "$INSTALL_MODE" = "venv" ]; then
    _inject_tab_completion "${VENV_DIR}/bin/activate"
    ok "Registered run_validation + tab-completion in .venv/bin/activate"
elif [ "$INSTALL_MODE" = "active-venv" ]; then
    _inject_tab_completion "${VIRTUAL_ENV}/bin/activate"
    ok "Registered run_validation + tab-completion in ${VIRTUAL_ENV}/bin/activate"
else
    # Baremetal — create a sourceable shell snippet
    SHELL_SNIPPET="${SCRIPT_DIR}/.run_validation_rc"
    _inject_tab_completion_baremetal() {
        cat > "$SHELL_SNIPPET" << BARE_EOF
# Source this file to get run_validation + tab-completion
# Usage: source ${SHELL_SNIPPET}

run_validation() {
    "${SCRIPT_DIR}/run_validation.sh" "\$@"
}

_run_validation_completions() {
    local cur prev
    cur="\${COMP_WORDS[COMP_CWORD]}"
    prev="\${COMP_WORDS[COMP_CWORD-1]}"
    local fvt_dir="${SCRIPT_DIR}/fvt"
    local scenarios=""
    if [ -d "\${fvt_dir}" ]; then
        for d in "\${fvt_dir}"/*/; do
            [ -d "\$d" ] || continue
            local name
            name="\$(basename "\$d")"
            [ "\$name" = "__pycache__" ] && continue
            scenarios="\${scenarios} \${name}"
        done
    fi
    local commands="deploy verify test"
    local special="all list help --config --help"
    local options="--suite --marker -v --verbose --debug"
    local markers="sanity functional regression deploy"
    case "\$COMP_CWORD" in
        1) COMPREPLY=( \$(compgen -W "\${scenarios} \${special}" -- "\$cur") ) ;;
        2)
            case "\$prev" in
                list|help|--help|-h|--config) COMPREPLY=() ;;
                *) COMPREPLY=( \$(compgen -W "\${commands}" -- "\$cur") ) ;;
            esac ;;
        *)
            case "\$prev" in
                --suite)
                    local scenario="\${COMP_WORDS[1]}"
                    local suites=""
                    if [ -d "\${fvt_dir}/\${scenario}" ]; then
                        for d in "\${fvt_dir}/\${scenario}"/*/; do
                            [ -d "\$d" ] || continue
                            local name
                            name="\$(basename "\$d")"
                            [ "\$name" = "__pycache__" ] && continue
                            suites="\${suites} \${name}"
                        done
                    fi
                    COMPREPLY=( \$(compgen -W "\${suites}" -- "\$cur") ) ;;
                --marker) COMPREPLY=( \$(compgen -W "\${markers}" -- "\$cur") ) ;;
                *) COMPREPLY=( \$(compgen -W "\${options}" -- "\$cur") ) ;;
            esac ;;
    esac
}
complete -F _run_validation_completions run_validation
BARE_EOF
    }
    _inject_tab_completion_baremetal
    ok "Created shell snippet: .run_validation_rc"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Make scripts executable
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
        echo "    run_validation --help"
        echo "    run_validation gitlab_install verify --marker sanity"
        ;;
    active-venv)
        echo "  Next steps (venv already active):"
        echo "    run_validation --help"
        echo "    run_validation gitlab_install verify --marker sanity"
        ;;
    baremetal)
        echo "  Next steps:"
        echo "    source .run_validation_rc              # Load run_validation + tab-completion"
        echo "    run_validation --help"
        echo "    run_validation gitlab_install verify --marker sanity"
        ;;
esac

echo ""
echo "  Credentials (two separate types):"
echo ""
echo "    1. SSH credentials (test_creds.yml) — for REMOTE test execution only:"
if [ -f "$CREDS_FILE" ]; then
    echo "       test_creds.yml exists (encrypted)"
    echo "       To update:  bash setup_env.sh --set-password"
    echo "       Force update: bash setup_env.sh --update-password"
else
    echo "       No SSH credentials set."
    echo "       For remote mode: bash setup_env.sh --set-password"
fi
echo ""
echo "    2. Domain credentials (GitLab / BSM / Postgres):"
echo "       Used by the build_stream playbook for deployment."
echo "       To set/update: bash setup_env.sh --set-domain-creds"

echo ""
echo "================================================================="
echo ""
