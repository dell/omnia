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
#   Default              — Installs dependencies with pip --user
#   Active venv          — Installs into the currently active venv
#   --venv               — Creates test/main/.venv and installs there
#
# CREDENTIAL HANDLING:
#   SSH credentials (OIM server):
#     --set-creds          — Prompt for SSH password (asks twice for confirmation).
#                            If credentials exist, asks whether to update them.
#     --update-creds       — Force-update existing SSH password (prompt twice).
#     --creds <pass>       — Set SSH password directly (non-interactive).
#
#   Credentials are written atomically by omnia_auto to test_creds.yml and
#   encrypted with Ansible Vault. They may be prepared before selecting a
#   remote target; oim_server_ip is informational for credential setup.
#
# Usage:
#   ./setup_env.sh                         # Install with pip --user
#   ./setup_env.sh --venv                  # Create .venv/ and install
#   ./setup_env.sh --force                 # Force-reinstall dependencies
#   ./setup_env.sh --venv --force          # Recreate .venv/ and install
#   ./setup_env.sh --set-creds             # Prompt for SSH password
#   ./setup_env.sh --update-creds          # Update existing SSH password
#   ./setup_env.sh --creds "placeholder"   # Non-interactive setup
#   ./setup_env.sh --debug                 # Verbose pip output
#   ./setup_env.sh --help                  # Show this help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"
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
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
USE_VENV=false
FORCE=false
DEBUG=false
PIP_QUIET="--quiet"
SET_CREDS=false
UPDATE_CREDS=false
CREDS_VALUE=""
TEST_CONFIG="${SCRIPT_DIR}/test_config.yml"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)        USE_VENV=true; shift ;;
        --force)        FORCE=true; shift ;;
        --debug)        DEBUG=true; PIP_QUIET=""; shift ;;
        --set-creds|--set-password)       SET_CREDS=true; shift ;;
        --update-creds|--update-password) UPDATE_CREDS=true; shift ;;
        --creds|--password)
            if [[ $# -lt 2 ]]; then
                fail "--creds requires a value. Usage: --creds <PASSWORD>"
            fi
            CREDS_VALUE="$2"
            shift 2
            ;;
        --help|-h)
            echo ""
            echo "Omnia Main — Test Environment Setup"
            echo ""
            echo "Usage: ./setup_env.sh [OPTIONS]"
            echo ""
            echo "INSTALL"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  (no flag)       Baremetal mode (pip install --user)."
            echo "  --venv          Create .venv/ and install there."
            echo "  --force         Force-reinstall all requirements."
            echo "                  With --venv, recreate .venv/ first."
            echo ""
            echo "CREDENTIAL MANAGEMENT"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  SSH credentials are stored in test_creds.yml and encrypted with"
            echo "  Ansible Vault automatically. They are gitignored and may be"
            echo "  created before oim_server_ip is configured."
            echo ""
            echo "  --set-creds     Interactive SSH password setup. Prompts twice for"
            echo "                  confirmation. If already set, asks yes/no to update."
            echo ""
            echo "  --update-creds"
            echo "                  Force-update the existing SSH password."
            echo ""
            echo "  --creds PWD     Non-interactive SSH password set."
            echo ""
            echo "  Legacy aliases: --set-password, --update-password, --password"
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
            echo "Usage: ./setup_env.sh [--venv] [--force] [--debug] [--set-creds] [--help]"
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
# Step 2: Determine install mode
# -----------------------------------------------
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
    ok "Install mode: baremetal (system Python)"
fi

echo -e "  ${CYAN}Mode:${NC} ${INSTALL_MODE}"

# -----------------------------------------------
# Step 3: Install dependencies
# -----------------------------------------------
info "Upgrading pip"
pip install --upgrade pip $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
    pip install --upgrade pip $PIP_QUIET

info "Installing dependencies from requirements.txt"
PIP_FORCE_ARGS=()
if [ "$FORCE" = true ]; then
    PIP_FORCE_ARGS=(--force-reinstall)
    info "Force-reinstalling all requirements (--force)"
fi

pip install "${PIP_FORCE_ARGS[@]}" -r "$REQUIREMENTS" \
    $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
    pip install "${PIP_FORCE_ARGS[@]}" -r "$REQUIREMENTS" $PIP_QUIET

# pytest-order for test ordering
if ! pip show pytest-order &>/dev/null; then
    info "Installing pytest-order"
    pip install pytest-order $PIP_QUIET $PIP_USER_FLAG 2>/dev/null || \
        pip install pytest-order $PIP_QUIET
fi

ok "All dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Credential setup (delegated to omnia_auto)
# ─────────────────────────────────────────────────────────────────────────────

# Display the configured target without requiring one during credential setup.
_show_oim_server_ip() {
    if [ ! -f "$TEST_CONFIG" ]; then
        warn "test_config.yml not found — set oim_server_ip for remote mode."
        return
    fi
    local oim_ip
    oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -n "$oim_ip" ]; then
        ok "Target server: ${oim_ip}"
    else
        warn "oim_server_ip not set — credentials saved locally for later use."
    fi
}

_write_ssh_creds() {
    local _pass="$1"
    $CRED_CLI write-fields \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --fields "{\"oim_password\":\"${_pass}\"}" >/dev/null 2>&1
    ok "SSH credentials saved: test_creds.yml (encrypted)"
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
# SSH credential dispatch (--set-creds / --update-creds / --creds)
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
# No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ -z "$CREDS_VALUE" ] && [ "$UPDATE_CREDS" = false ] && [ "$SET_CREDS" = false ]; then
    if [ -f "$CREDS_FILE" ]; then
        ok "Credentials file exists: test_creds.yml"
        ok "SSH: re-run with --set-creds or --update-creds to change"
    else
        warn "No credentials file found (test_creds.yml)"
        warn "SSH creds: ./setup_env.sh --set-creds"
    fi
fi

# =============================================================================
# REGISTER run_validation FUNCTION AND TAB COMPLETION IN .venv/bin/activate
# =============================================================================

if [ "$INSTALL_MODE" = "venv" ]; then
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
    local commands="exec verify test"
    local categories="fvt_main nft_main"
    local special="help --config --help"
    local options="--suite --marker -v --verbose --debug"
    local markers="sanity functional regression deploy"
    case "$COMP_CWORD" in
        1) COMPREPLY=( $(compgen -W "${categories} ${special}" -- "$cur") ) ;;
        2)
            case "$prev" in
                fvt_main) COMPREPLY=( $(compgen -W "${scenarios} ${commands} list" -- "$cur") ) ;;
                nft_main) COMPREPLY=( $(compgen -W "test verify list" -- "$cur") ) ;;
                *) COMPREPLY=() ;;
            esac ;;
        3)
            if [ "${COMP_WORDS[1]}" = "fvt_main" ] && \
               [[ " ${scenarios} " == *" ${COMP_WORDS[2]} "* ]]; then
                COMPREPLY=( $(compgen -W "${commands}" -- "$cur") )
            else
                COMPREPLY=( $(compgen -W "${options}" -- "$cur") )
            fi ;;
        *)
            case "$prev" in
                --suite)
                    local scenario="${COMP_WORDS[2]}"
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
fi

echo ""
echo "================================================================="
echo "  Environment Ready (${INSTALL_MODE})"
echo "================================================================="
echo ""
case "$INSTALL_MODE" in
    venv)
        echo "  Next steps:"
        echo "    source .venv/bin/activate"
        ;;
    active-venv)
        echo "  Next steps (venv already active):"
        ;;
    baremetal)
        echo "  Next steps:"
        ;;
esac
echo "    vi test_config.yml                 # Set oim_server_ip"
echo "    ./setup_env.sh --set-creds         # Optional SSH password"
echo "    ./run_validation.sh --help"
echo "    ./run_validation.sh fvt_main verify --marker sanity"
echo ""
echo "================================================================="
echo ""
