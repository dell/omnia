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
# Repo Manager — Test Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# INSTALL MODES:
#   Baremetal (default)  — Install into system Python (pip install --user)
#   Active venv          — Auto-detected; installs into the currently active venv
#   New venv (--venv)    — Creates .venv/ and installs there
#
# CREDENTIAL HANDLING:
#   --set-password       — Prompt for SSH password (asks twice for confirmation).
#                          If password already exists, asks yes/no to update.
#   --update-password    — Force-update existing password (prompt twice).
#   --password <pass>    — Set password directly via flag (non-interactive).
#   Credentials are written to test_creds.yml and encrypted with ansible-vault.
#   All credential flags require oim_server_ip to be set in test_config.yml.
#
# Usage:
#   bash setup_env.sh                        # Baremetal or active venv
#   bash setup_env.sh --venv                 # Create .venv/ and install there
#   bash setup_env.sh --venv --force         # Recreate .venv/ from scratch
#   bash setup_env.sh --set-password         # Prompt for SSH password
#   bash setup_env.sh --update-password      # Update existing password
#   bash setup_env.sh --password "secret"    # Set password via flag
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
        --help|-h)
            echo ""
            echo "Repo Manager — Test Environment Setup"
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
            echo "CREDENTIAL MANAGEMENT"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  Credentials are required for remote mode (when oim_server_ip is"
            echo "  configured in test_config.yml). The SSH password is saved to"
            echo "  test_creds.yml and encrypted with Ansible Vault automatically."
            echo ""
            echo "  --set-password  Interactive password setup. Prompts for the SSH"
            echo "                  password twice (for confirmation). If a password"
            echo "                  is already set, asks whether to update it."
            echo "                  Requires oim_server_ip to be set in test_config.yml."
            echo ""
            echo "  --update-password"
            echo "                  Force-update an existing password. Prompts for a"
            echo "                  new password twice (for confirmation). Overwrites"
            echo "                  the existing test_creds.yml and re-encrypts it."
            echo "                  Requires oim_server_ip to be set in test_config.yml."
            echo ""
            echo "  --password PWD  Non-interactive password setup. Creates test_creds.yml"
            echo "                  with the given password and encrypts it immediately."
            echo "                  Overwrites any existing credentials without prompting."
            echo "                  Requires oim_server_ip to be set in test_config.yml."
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
            echo "  bash setup_env.sh --venv --force            # Recreate .venv/ from scratch"
            echo "  bash setup_env.sh --set-password           # Set SSH password (prompt)"
            echo "  bash setup_env.sh --update-password        # Update existing password"
            echo "  bash setup_env.sh --password 'mypass'      # Set password (non-interactive)"
            echo "  bash setup_env.sh --venv --set-password    # Venv + password prompt"
            echo "  bash setup_env.sh --debug                  # Verbose pip output"
            echo ""
            echo "FILES"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  test_config.yml       Target server IP and sync settings"
            echo "  test_creds.yml        SSH credentials (auto-encrypted, gitignored)"
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
echo "  Repo Manager — Test Environment Setup"
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

_create_and_encrypt_creds() {
    local _secret="$1"

    # Write plain-text creds file
    cat > "$CREDS_FILE" << CREDS_EOF
---
# SSH credentials for remote OIM server.
# This file is auto-encrypted with Ansible Vault.
oim_password: "${_secret}"
CREDS_EOF
    chmod 600 "$CREDS_FILE"

    # Create vault key if not exists
    if [ ! -f "$CREDS_KEY" ]; then
        info "Generating vault key: .test_creds.key"
        python3 -c "import secrets; print(secrets.token_urlsafe(32)[:32])" > "$CREDS_KEY"
        chmod 600 "$CREDS_KEY"
    fi

    # Encrypt with ansible-vault
    if command -v ansible-vault &>/dev/null; then
        ansible-vault encrypt "$CREDS_FILE" --vault-password-file "$CREDS_KEY" 2>/dev/null
        ok "Credentials encrypted: test_creds.yml"
    else
        warn "ansible-vault not found — credentials saved as plain text"
        warn "Install ansible-core and re-run to encrypt"
    fi
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

if [ -n "$PASSWORD_VALUE" ]; then
    # Password passed via --password flag (non-interactive)
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
    echo -e "  ${CYAN}This will overwrite test_creds.yml and re-encrypt it.${NC}"
    echo ""
    _cred_input=$(_prompt_credential)
    _create_and_encrypt_creds "$_cred_input"
    ok "Password updated successfully"

elif [ "$SET_PASSWORD" = true ]; then
    # --set-password: check if already set, ask to update
    _check_oim_server_ip

    if [ -f "$CREDS_FILE" ]; then
        warn "Password is already set (test_creds.yml exists)."
        if _ask_yes_no "  Do you want to update the password?"; then
            echo ""
            echo -e "  ${CYAN}Enter new SSH password for the target OIM server.${NC}"
            echo ""
            _cred_input=$(_prompt_credential)
            _create_and_encrypt_creds "$_cred_input"
            ok "Password updated successfully"
        else
            ok "Password update skipped. Existing credentials kept."
        fi
    else
        echo ""
        echo -e "  ${CYAN}Enter SSH password for the target OIM server.${NC}"
        echo -e "  ${CYAN}This will be saved to test_creds.yml (encrypted).${NC}"
        echo ""
        _cred_input=$(_prompt_credential)
        _create_and_encrypt_creds "$_cred_input"
    fi

else
    # No password flags — check if creds file exists
    if [ -f "$CREDS_FILE" ]; then
        ok "Credentials file exists: test_creds.yml"
        ok "To update, re-run with: --set-password or --update-password"
    else
        warn "No credentials file found (test_creds.yml)"
        warn "For remote mode, run: bash setup_env.sh --set-password"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Register run_validation + tab completion (venv modes only)
# ─────────────────────────────────────────────────────────────────────────────
_inject_tab_completion() {
    local activate_script="$1"
    local marker="# >>> repo-manager-test >>>"
    local marker_end="# <<< repo-manager-test <<<"
    local module_dir="$SCRIPT_DIR"

    # Remove any previous block (idempotent)
    if grep -q "${marker}" "${activate_script}" 2>/dev/null; then
        sed -i "/${marker}/,/${marker_end}/d" "${activate_script}"
    fi

    cat >> "${activate_script}" << RM_ACTIVATE_EOF

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
    local markers="sanity x86_64 aarch64 functional regression deploy"
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
RM_ACTIVATE_EOF
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
    local markers="sanity x86_64 aarch64 functional regression deploy"
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
        echo "    run_validation repo_manager verify --marker sanity"
        ;;
    active-venv)
        echo "  Next steps (venv already active):"
        echo "    run_validation --help"
        echo "    run_validation repo_manager verify --marker sanity"
        ;;
    baremetal)
        echo "  Next steps:"
        echo "    source .run_validation_rc              # Load run_validation + tab-completion"
        echo "    run_validation --help"
        echo "    run_validation repo_manager verify --marker sanity"
        ;;
esac

echo ""
echo "  Credentials:"
if [ -f "$CREDS_FILE" ]; then
    echo "    test_creds.yml exists (encrypted)"
    echo "    To update:  bash setup_env.sh --set-password"
    echo "    Force update: bash setup_env.sh --update-password"
else
    echo "    No credentials set."
    echo "    For remote mode: bash setup_env.sh --set-password"
fi

echo ""
echo "  Documentation:"
echo "    docs/test_config.md                 # Configuration reference"
echo "    docs/test_creds.md                  # Credentials setup"
echo "    docs/test_run_config.md             # Batch execution config"
echo ""
echo "================================================================="
echo ""