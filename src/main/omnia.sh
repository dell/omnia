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
#   1. Edit src/main/omnia.env with your environment settings
#   2. Run: ./omnia.sh --setup-venv   (one-time Python + Ansible setup)
#
# All configuration is via environment variables in omnia.env.
# No interactive prompts — fill omnia.env before running.
# =============================================================================

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SRC_DIR="$(dirname "$SCRIPT_DIR")"
readonly REPO_ROOT="$(dirname "$SRC_DIR")"
readonly ENV_FILE="$SCRIPT_DIR/omnia.env"

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
# Environment Loading
# ─────────────────────────────────────────────────────────────────────────────
load_env() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}ERROR: omnia.env not found at $ENV_FILE${NC}"
        echo -e "${YELLOW}Configure it before running:${NC}"
        echo -e "  vi $ENV_FILE"
        exit 1
    fi

    # Source env file (set -a exports all vars)
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a

    # Apply defaults for optional variables
    OMNIA_DATA_PATH="${OMNIA_DATA_PATH:-/opt/omnia}"
    OMNIA_PROJECT_NAME="${OMNIA_PROJECT_NAME:-project_default}"
    OMNIA_VENV_PATH="${OMNIA_VENV_PATH:-$OMNIA_DATA_PATH/venv}"
    OMNIA_HOSTNAME="${OMNIA_HOSTNAME:-oim}"
    OMNIA_DOMAIN_NAME="${OMNIA_DOMAIN_NAME:-omnia.cluster}"
    OMNIA_ADMIN_NIC_IP="${OMNIA_ADMIN_NIC_IP:-172.16.107.254}"

    export OMNIA_DATA_PATH OMNIA_PROJECT_NAME OMNIA_VENV_PATH
    export OMNIA_HOSTNAME OMNIA_DOMAIN_NAME OMNIA_ADMIN_NIC_IP
}

validate_env() {
    local errors=0

    if [ -z "${OMNIA_ADMIN_NIC_IP:-}" ]; then
        echo -e "${RED}ERROR: OMNIA_ADMIN_NIC_IP is not set in $ENV_FILE${NC}"
        errors=$((errors + 1))
    fi

    if [ -z "${OMNIA_HOSTNAME:-}" ]; then
        echo -e "${RED}ERROR: OMNIA_HOSTNAME is not set in $ENV_FILE${NC}"
        errors=$((errors + 1))
    fi

    if [ -z "${OMNIA_DOMAIN_NAME:-}" ]; then
        echo -e "${RED}ERROR: OMNIA_DOMAIN_NAME is not set in $ENV_FILE${NC}"
        errors=$((errors + 1))
    fi

    if [ "$errors" -gt 0 ]; then
        echo -e "${YELLOW}Edit $ENV_FILE and set all required variables before running omnia.sh${NC}"
        exit 1
    fi

    echo -e "${GREEN}Environment validated:${NC}"
    echo -e "  Hostname:    ${OMNIA_HOSTNAME}"
    echo -e "  Domain:      ${OMNIA_DOMAIN_NAME}"
    echo -e "  Admin IP:    ${OMNIA_ADMIN_NIC_IP}"
    echo -e "  Data path:   ${OMNIA_DATA_PATH}"
    echo -e "  Project:     ${OMNIA_PROJECT_NAME}"
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
    if ! command -v ansible >/dev/null 2>&1; then
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

    # ── Summary ──
    echo ""
    echo -e "${GREEN}================================================================================${NC}"
    echo -e "${GREEN}                Omnia Venv Setup Complete${NC}"
    echo -e "${GREEN}================================================================================${NC}"
    echo ""
    echo -e "  Venv:    ${GREEN}$OMNIA_VENV_PATH${NC}"
    echo -e "  Python:  ${GREEN}$(python3 --version)${NC}"
    echo -e "  Ansible: ${GREEN}$(ansible --version | head -1)${NC}"
    echo ""
    echo -e "${BLUE}Installed collections:${NC}"
    ansible-galaxy collection list 2>/dev/null | grep -E "^(ansible\.|containers\.|community\.|kubernetes\.|omnia\.)" || true
    echo ""
    echo -e "${YELLOW}Activate in your shell:${NC}"
    echo -e "  ${GREEN}source $OMNIA_VENV_PATH/bin/activate${NC}"
    echo ""

    deactivate 2>/dev/null || true
}

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
    cat <<EOF
Omnia Infrastructure Manager (OIM) — v${OMNIA_RELEASE}

PREREQUISITE:
  Edit src/main/omnia.env with your environment settings before running any command.

USAGE:
  $0 <command>

SETUP COMMANDS:
  --setup-venv, -s      Create/update the shared Python venv (pip + Galaxy collections)
                        Discovers and installs requirements from all domains automatically.
  --help, -h            Show this help message

DIAGNOSTICS (see omnia-cli):
  ./omnia-cli status [--project <name>]         All domain statuses
  ./omnia-cli repo-manager [--project <name>]   Repo manager details
  ./omnia-cli image-build [--project <name>]    Image build details
  ./omnia-cli <domain> [--project <name>]       Any domain status
  ./omnia-cli version                           Version info
  ./omnia-cli help [<domain>]                   CLI help

ENVIRONMENT:
  All configuration is via src/main/omnia.env:
    OMNIA_ADMIN_NIC_IP    Admin NIC IP (default: 172.16.107.254)
    OMNIA_DATA_PATH       Root data directory (default: /opt/omnia)
    OMNIA_PROJECT_NAME    Project name (default: project_default)
    OMNIA_HOSTNAME        OIM hostname (default: oim)
    OMNIA_DOMAIN_NAME     Domain name (default: omnia.cluster)
    OMNIA_VENV_PATH       Python venv path (default: /opt/omnia/venv)

EXAMPLES:
  # First-time setup:
  vi src/main/omnia.env          # Set OMNIA_ADMIN_NIC_IP and other vars
  ./omnia.sh --setup-venv        # Install Python + Ansible into venv

  # Check domain status:
  ./omnia-cli status             # All domains
  ./omnia-cli repo-manager       # Repo manager details

  # Run component playbooks (after venv setup):
  source /opt/omnia/venv/bin/activate
  cd src/image_build_manager/playbooks
  ansible-playbook image_build_manager.yml --tags validate
EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Dispatch
# ─────────────────────────────────────────────────────────────────────────────
main() {
    case "${1:-}" in
        --setup-venv|-s)
            setup_venv
            ;;
        --help|-h|"")
            show_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo -e "${YELLOW}For status & diagnostics, use: ./omnia-cli${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
