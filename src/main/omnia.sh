#!/bin/bash

# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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
# omnia.sh — Omnia Infrastructure Manager (OIM) CLI
# =============================================================================
#
# Prerequisites:
#   1. Edit src/main/omnia.env with your settings
#   2. Run: ./omnia.sh --setup-venv   (one-time Python + Ansible setup)
#
# During setup, this script:
#   - Installs omnia.env to /etc/omnia/omnia.env (system-wide)
#   - Creates /etc/profile.d/omnia-env.sh so all new shells auto-load vars
#   - Creates venv, installs deps, copies domain input files
#
# After setup, environment variables are available system-wide.
# New login shells load them automatically.

# For immediate use in the current shell:
#   source /opt/omnia/activate-omnia.sh
# =============================================================================

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SRC_DIR="$(dirname "$SCRIPT_DIR")"
readonly REPO_ROOT="$(dirname "$SRC_DIR")"

# Color definitions
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly YELLOW='\033[0;33m'
readonly NC='\033[0m'

# Omnia release metadata
readonly OMNIA_RELEASE="2.3.0.0"

# Known domain directories (each may contain requirements.txt / requirements.yml)
readonly DOMAINS=(
    "build_stream"
    "discovery"
    "image_build_manager"
    "orchestrator"
    "repo_manager"
    "telemetry"
    "utils"
)

# ─────────────────────────────────────────────────────────────────────────────
# Auto-load installed environment
# ─────────────────────────────────────────────────────────────────────────────
if [ -f /etc/profile.d/omnia-env.sh ]; then
    # shellcheck disable=SC1091
    . /etc/profile.d/omnia-env.sh
fi

# ─────────────────────────────────────────────────────────────────────────────
# Environment Loading
# ─────────────────────────────────────────────────────────────────────────────
load_env() {
    # Apply defaults for optional variables
    OMNIA_DATA_PATH="${OMNIA_DATA_PATH:-/opt/omnia}"
    OMNIA_PROJECT_NAME="${OMNIA_PROJECT_NAME:-project_default}"
    OMNIA_VENV_PATH="${OMNIA_VENV_PATH:-$OMNIA_DATA_PATH/venv}"
    SYSTEM_HOSTNAME="${SYSTEM_HOSTNAME:-oim}"
    SYSTEM_DOMAIN_NAME="${SYSTEM_DOMAIN_NAME:-omnia.cluster}"

    export OMNIA_DATA_PATH OMNIA_PROJECT_NAME OMNIA_VENV_PATH
    export SYSTEM_HOSTNAME SYSTEM_DOMAIN_NAME
}

validate_env() {
    local errors=0

    if [ -z "${SYSTEM_ADMIN_NIC_IPV4:-}" ]; then
        echo -e "${RED}ERROR: SYSTEM_ADMIN_NIC_IPV4 is not set${NC}"
        echo -e "${YELLOW}  export SYSTEM_ADMIN_NIC_IPV4=<your_admin_nic_ip>${NC}"
        errors=$((errors + 1))
    fi

    if [ -z "${SYSTEM_HOSTNAME:-}" ]; then
        echo -e "${RED}ERROR: SYSTEM_HOSTNAME is not set${NC}"
        echo -e "${YELLOW}  export SYSTEM_HOSTNAME=oim${NC}"
        errors=$((errors + 1))
    fi

    if [ -z "${SYSTEM_DOMAIN_NAME:-}" ]; then
        echo -e "${RED}ERROR: SYSTEM_DOMAIN_NAME is not set${NC}"
        echo -e "${YELLOW}  export SYSTEM_DOMAIN_NAME=omnia.cluster${NC}"
        errors=$((errors + 1))
    fi

    if [ "$errors" -gt 0 ]; then
        echo -e "${YELLOW}Set the required variables in src/main/omnia.env and re-run ./omnia.sh -s${NC}"
        echo -e "${YELLOW}Or export them manually:  export SYSTEM_ADMIN_NIC_IPV4=<ip>${NC}"
        exit 1
    fi

    export SYSTEM_ADMIN_NIC_IPV4

    echo -e "${GREEN}Environment validated:${NC}"
    echo -e "  Hostname:    ${SYSTEM_HOSTNAME}"
    echo -e "  Domain:      ${SYSTEM_DOMAIN_NAME}"
    echo -e "  Admin IP:    ${SYSTEM_ADMIN_NIC_IPV4}"
    echo -e "  Data path:   ${OMNIA_DATA_PATH}"
    echo -e "  Project:     ${OMNIA_PROJECT_NAME}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Install Environment to System
# ─────────────────────────────────────────────────────────────────────────────
readonly SYSTEM_ENV_DIR="/etc/omnia"
readonly SYSTEM_ENV_FILE="${SYSTEM_ENV_DIR}/omnia.env"
readonly PROFILE_DROP_IN="/etc/profile.d/omnia-env.sh"

install_system_env() {
    local env_file="$SCRIPT_DIR/omnia.env"

    if [ ! -f "$env_file" ]; then
        echo -e "${YELLOW}WARNING: src/main/omnia.env not found — skipping system env install${NC}"
        return 0
    fi

    echo -e "${BLUE}Installing environment to system...${NC}"

    mkdir -p "$SYSTEM_ENV_DIR"
    cp -f "$env_file" "$SYSTEM_ENV_FILE"
    chmod 0644 "$SYSTEM_ENV_FILE"

    echo -e "  ${GREEN}Installed: ${SYSTEM_ENV_FILE}${NC}"

    cat > "$PROFILE_DROP_IN" <<'PROFILE_EOF'
#!/bin/bash
#
# Omnia environment variables
#

if [ -f /etc/omnia/omnia.env ]; then
    set -a
    . /etc/omnia/omnia.env
    set +a
fi
PROFILE_EOF

    chmod 0644 "$PROFILE_DROP_IN"

    echo -e "  ${GREEN}Installed: ${PROFILE_DROP_IN}${NC}"

    #
    # Load into current script execution
    #
    set -a
    # shellcheck disable=SC1090
    . "$SYSTEM_ENV_FILE"
    set +a

    echo -e "${GREEN}Environment installed system-wide.${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Base Directory Creation
# ─────────────────────────────────────────────────────────────────────────────
create_base_dirs() {
    echo -e "${BLUE}Creating base directory structure at ${OMNIA_DATA_PATH}...${NC}"
    mkdir -p "${OMNIA_DATA_PATH}"
    mkdir -p "${OMNIA_DATA_PATH}/log"
    mkdir -p "${OMNIA_DATA_PATH}/input"
    mkdir -p "${OMNIA_DATA_PATH}/.data"
    echo -e "${GREEN}Base directories created. Domain directories will be created by respective playbooks.${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Venv Setup
# ─────────────────────────────────────────────────────────────────────────────
setup_venv() {
    install_system_env
    load_env
    validate_env
    create_base_dirs

    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}               Omnia Virtual Environment Setup${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""
    echo -e "  Venv path:   ${GREEN}$OMNIA_VENV_PATH${NC}"
    echo -e "  Source dir:  ${GREEN}$SRC_DIR${NC}"
    echo ""

    # ── Find Python 3.11+ ──
    local python_cmd=""
    for candidate in python3.12 python3.11 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            python_cmd="$candidate"
            break
        fi
    done

    if [ -z "$python_cmd" ]; then
        echo -e "${RED}ERROR: Python 3.11+ is required but not found.${NC}"
        echo -e "${YELLOW}Install: dnf install -y python3.12${NC}"
        exit 1
    fi

    local py_ver
    py_ver=$($python_cmd --version 2>&1 | awk '{print $2}')
    local py_major py_minor
    py_major=$(echo "$py_ver" | cut -d. -f1)
    py_minor=$(echo "$py_ver" | cut -d. -f2)

    if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 11 ]; }; then
        echo -e "${RED}ERROR: Python >= 3.11 required. Found: $py_ver${NC}"
        exit 1
    fi
    echo -e "${GREEN}Using Python: $python_cmd ($py_ver)${NC}"

    # ── Create or update venv ──
    if [ -d "$OMNIA_VENV_PATH" ]; then
        echo -e "${YELLOW}Venv exists at $OMNIA_VENV_PATH — updating...${NC}"
    else
        echo -e "${GREEN}Creating venv at $OMNIA_VENV_PATH ...${NC}"
        mkdir -p "$(dirname "$OMNIA_VENV_PATH")"
        $python_cmd -m venv "$OMNIA_VENV_PATH"
    fi

    # shellcheck disable=SC1091
    source "$OMNIA_VENV_PATH/bin/activate"

    echo -e "${BLUE}Upgrading pip...${NC}"
    pip install --upgrade pip setuptools wheel --quiet

    # ── Discover and install per-domain pip requirements ──
    local pip_installed=0
    for domain in "${DOMAINS[@]}"; do
        local domain_pip="$SRC_DIR/$domain/requirements.txt"
        if [ -f "$domain_pip" ]; then
            echo -e "${BLUE}Installing pip packages for ${domain} ...${NC}"
            if ! pip install -r "$domain_pip"; then
                echo -e "${YELLOW}WARNING: pip install failed for $domain_pip — continuing${NC}"
            else
                pip_installed=$((pip_installed + 1))
            fi
        fi
    done

    if [ "$pip_installed" -eq 0 ]; then
        echo -e "${YELLOW}WARNING: No requirements.txt found in any domain${NC}"
    fi

    # ── Verify ansible is available ──
    if ! "$OMNIA_VENV_PATH/bin/ansible" --version >/dev/null 2>&1; then
        echo -e "${RED}ERROR: ansible not found after pip install${NC}"
        deactivate 2>/dev/null || true
        exit 1
    fi

    # ── Discover and install per-domain Galaxy collections ──
    for domain in "${DOMAINS[@]}"; do
        local domain_galaxy="$SRC_DIR/$domain/requirements.yml"
        if [ -f "$domain_galaxy" ]; then
            echo -e "${BLUE}Installing Galaxy collections for ${domain} ...${NC}"
            if ! ansible-galaxy collection install -r "$domain_galaxy" --force; then
                echo -e "${YELLOW}WARNING: Galaxy install failed for $domain_galaxy — continuing${NC}"
            fi
        fi
    done

    #
    # Reload latest environment
    #
    if [ -f "$SYSTEM_ENV_FILE" ]; then
        set -a
        # shellcheck disable=SC1090
        . "$SYSTEM_ENV_FILE"
        set +a
    fi

    #
    # Create convenience activation script
    #
    cat > "${OMNIA_DATA_PATH}/activate-omnia.sh" <<'ACTIVATE_EOF'
#!/bin/bash
#
# Convenience script to load Omnia environment and activate venv
# Usage: source /opt/omnia/activate-omnia.sh
#

if [ -f /etc/omnia/omnia.env ]; then
    set -a
    . /etc/omnia/omnia.env
    set +a
fi

if [ -f "${OMNIA_VENV_PATH}/bin/activate" ]; then
    source "${OMNIA_VENV_PATH}/bin/activate"
else
    echo "ERROR: Virtual environment not found at ${OMNIA_VENV_PATH}"
    return 1 2>/dev/null || exit 1
fi
ACTIVATE_EOF
    chmod +x "${OMNIA_DATA_PATH}/activate-omnia.sh"

    # ── Summary ──
    echo ""
    echo -e "${GREEN}================================================================================${NC}"
    echo -e "${GREEN}                Omnia Venv Setup Complete${NC}"
    echo -e "${GREEN}================================================================================${NC}"
    echo ""
    echo -e "  Venv:    ${GREEN}$OMNIA_VENV_PATH${NC}"
    echo -e "  Python:  ${GREEN}$(python --version)${NC}"
    echo -e "  Ansible: ${GREEN}$(ansible --version | head -1)${NC}"
    echo ""
    echo -e "${BLUE}Installed collections:${NC}"
    ansible-galaxy collection list 2>/dev/null | grep -E "^(ansible\.|containers\.|community\.|kubernetes\.|omnia\.)" || true
    echo ""
    echo -e "${GREEN}Environment helper created:${NC}"
    echo -e "  ${GREEN}${OMNIA_DATA_PATH}/activate-omnia.sh${NC}"
    echo ""
    echo -e "${YELLOW}Activate in your shell:${NC}"
    echo -e "  ${GREEN}source ${OMNIA_DATA_PATH}/activate-omnia.sh${NC}"
    echo ""

    deactivate 2>/dev/null || true
}

# ─────────────────────────────────────────────────────────────────────────────
# Copy Domain Input Files
# ─────────────────────────────────────────────────────────────────────────────
copy_domain_inputs() {
    echo -e "${BLUE}Initializing domains (log dirs + input files) to ${OMNIA_DATA_PATH}/ ...${NC}"
    local copied=0
    for domain in "${DOMAINS[@]}"; do
        local init_script="$SRC_DIR/$domain/domain-init.sh"
        if [ -f "$init_script" ]; then
            chmod +x "$init_script"
            if bash "$init_script"; then
                copied=$((copied + 1))
            else
                echo -e "${YELLOW}WARNING: domain-init.sh failed for $domain — continuing${NC}"
            fi
        fi
    done
    if [ "$copied" -eq 0 ]; then
        echo -e "${YELLOW}No domain-init.sh scripts found in any domain${NC}"
    else
        echo -e "${GREEN}Domain init scripts completed for ${copied} domain(s)${NC}"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
    cat <<EOF
Omnia Infrastructure Manager (OIM) — v${OMNIA_RELEASE}

PREREQUISITE:
  Edit src/main/omnia.env before running --setup-venv.
  After setup, vars are installed system-wide at /etc/omnia/omnia.env.

USAGE:
  $0 <command> [options]

SETUP COMMANDS:
  --setup-venv, -s      Create/update the shared Python venv (pip + Galaxy collections)
                        Also copies domain input files to the runtime data path.
  --help, -h            Show this help message

OPTIONS:
  --skip-input-copy     Skip copying domain input files during --setup-venv.
                        Useful in CI or when input files are managed externally.

DIAGNOSTICS (see omnia-cli):
  omnia-cli status [--project <name>]         All domain statuses
  omnia-cli repo-manager [--project <name>]   Repo manager details
  omnia-cli image-build [--project <name>]    Image build details
  omnia-cli <domain> [--project <name>]       Any domain status
  omnia-cli version                           Version info
  omnia-cli help [<domain>]                   CLI help

INSTALL omnia-cli TO PATH:
  sudo cp omnia-cli /usr/local/bin/
  sudo chmod +x /usr/local/bin/omnia-cli

SYSTEM ENVIRONMENT:
  After --setup-venv, omnia.env is installed to:
    /etc/omnia/omnia.env           — system-wide env file
    /etc/profile.d/omnia-env.sh    — auto-sourced on login

  Variables:
    SYSTEM_ADMIN_NIC_IPV4  Admin NIC IPv4 (REQUIRED)
    OMNIA_DATA_PATH        Root data directory (default: /opt/omnia)
    OMNIA_PROJECT_NAME     Project name (default: project_default)
    SYSTEM_HOSTNAME        OIM hostname (default: oim)
    SYSTEM_DOMAIN_NAME     Domain name (default: omnia.cluster)
    OMNIA_VENV_PATH        Python venv path (default: /opt/omnia/venv)

EXAMPLES:
  # First-time setup:
  vi src/main/omnia.env                        # Set SYSTEM_ADMIN_NIC_IPV4 and other vars
  ./omnia.sh -s                                # Installs env + venv + input files
  ./omnia.sh -s --skip-input-copy              # Installs env + venv only

  # After setup:
  #   New login shells automatically load environment variables.
  #
  #   For immediate use in current shell:
  #   source /opt/omnia/activate-omnia.sh

  # Install CLI:
  sudo cp omnia-cli /usr/local/bin/
  sudo chmod +x /usr/local/bin/omnia-cli

  # Check domain status:
  omnia-cli status               # All domains
  omnia-cli repo-manager         # Repo manager details

  # Run component playbooks (after venv setup):
  source /opt/omnia/activate-omnia.sh
  cd src/image_build_manager/playbooks
  ansible-playbook image_build_manager.yml --tags validate
EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Dispatch
# ─────────────────────────────────────────────────────────────────────────────
main() {
    local skip_input_copy=false
    local command=""

    # Parse all arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            --setup-venv|-s)
                command="setup-venv"
                shift
                ;;
            --skip-input-copy)
                skip_input_copy=true
                shift
                ;;
            --help|-h)
                command="help"
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                echo -e "${YELLOW}For status & diagnostics, use: omnia-cli${NC}"
                echo ""
                show_help
                exit 1
                ;;
        esac
    done

    case "${command:-help}" in
        setup-venv)
            setup_venv
            if [ "$skip_input_copy" = false ]; then
                copy_domain_inputs
            else
                echo -e "${YELLOW}Skipping input file copy (--skip-input-copy)${NC}"
            fi
            ;;
        help)
            show_help
            ;;
    esac
}

main "$@"
