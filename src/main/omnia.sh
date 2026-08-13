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

# Known domain directories (each must provide domain-init.sh)
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
    local warnings=0

    # --- Required env vars ---
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
        echo -e "${YELLOW}Set the required variables in src/main/omnia.env and re-run ./omnia.sh --setup-venv${NC}"
        echo -e "${YELLOW}Or export them manually:  export SYSTEM_ADMIN_NIC_IPV4=<ip>${NC}"
        exit 1
    fi

    export SYSTEM_ADMIN_NIC_IPV4

    # --- Validate hostname matches system (hostname -s) ---
    local actual_hostname
    actual_hostname="$(hostname -s 2>/dev/null || hostname 2>/dev/null)"
    if [ -n "$actual_hostname" ] && [ "$actual_hostname" != "$SYSTEM_HOSTNAME" ]; then
        echo -e "${RED}ERROR: SYSTEM_HOSTNAME (${SYSTEM_HOSTNAME}) does not match actual hostname (${actual_hostname})${NC}"
        echo -e "${YELLOW}  Fix: update SYSTEM_HOSTNAME in omnia.env${NC}"
        echo -e "${YELLOW}  Or:  hostnamectl set-hostname ${SYSTEM_HOSTNAME}${NC}"
        errors=$((errors + 1))
    fi

    # --- Validate domain matches system (hostname -d) ---
    local actual_domain
    actual_domain="$(hostname -d 2>/dev/null || true)"
    if [ -n "$actual_domain" ] && [ "$actual_domain" != "$SYSTEM_DOMAIN_NAME" ]; then
        echo -e "${YELLOW}WARNING: SYSTEM_DOMAIN_NAME (${SYSTEM_DOMAIN_NAME}) does not match system domain (${actual_domain})${NC}"
        echo -e "${YELLOW}  Fix: update SYSTEM_DOMAIN_NAME in omnia.env${NC}"
        echo -e "${YELLOW}  Or:  hostnamectl set-hostname ${SYSTEM_HOSTNAME}.${SYSTEM_DOMAIN_NAME}${NC}"
        warnings=$((warnings + 1))
    fi

    # --- Validate admin IP is assigned to a local interface ---
    local all_ips
    all_ips="$(hostname -I 2>/dev/null || ip -4 addr show | grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+' 2>/dev/null || true)"
    if [ -n "$all_ips" ]; then
        local ip_found=false
        for ip in $all_ips; do
            if [ "$ip" = "$SYSTEM_ADMIN_NIC_IPV4" ]; then
                ip_found=true
                break
            fi
        done
        if [ "$ip_found" = false ]; then
            echo -e "${RED}ERROR: SYSTEM_ADMIN_NIC_IPV4 (${SYSTEM_ADMIN_NIC_IPV4}) is not assigned to any local interface${NC}"
            echo -e "${YELLOW}  Available IPs: ${all_ips}${NC}"
            echo -e "${YELLOW}  Fix: update SYSTEM_ADMIN_NIC_IPV4 in omnia.env${NC}"
            errors=$((errors + 1))
        fi
    fi

    if [ "$errors" -gt 0 ]; then
        echo -e "${RED}Environment validation failed with ${errors} error(s)${NC}"
        exit 1
    fi

    echo -e "${GREEN}Environment validated:${NC}"
    echo -e "  Hostname:    ${SYSTEM_HOSTNAME} (actual: ${actual_hostname})"
    echo -e "  Domain:      ${SYSTEM_DOMAIN_NAME}${actual_domain:+ (actual: ${actual_domain})}"
    echo -e "  FQDN:        ${SYSTEM_HOSTNAME}.${SYSTEM_DOMAIN_NAME}"
    echo -e "  Admin IP:    ${SYSTEM_ADMIN_NIC_IPV4} (verified on interface)"
    echo -e "  Data path:   ${OMNIA_DATA_PATH}"
    echo -e "  Project:     ${OMNIA_PROJECT_NAME}"
    if [ "$warnings" -gt 0 ]; then
        echo -e "  ${YELLOW}Warnings: ${warnings}${NC}"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Install Environment to System
# ─────────────────────────────────────────────────────────────────────────────
readonly SYSTEM_ENV_DIR="/etc/omnia"
readonly SYSTEM_ENV_FILE="${SYSTEM_ENV_DIR}/omnia.env"
readonly PROFILE_DROP_IN="/etc/profile.d/omnia-env.sh"

install_system_env() {
    local env_file="$SCRIPT_DIR/omnia.env"

    echo -e "${BLUE}Installing environment to system...${NC}"

    mkdir -p "$SYSTEM_ENV_DIR"

    if [ -f "$SYSTEM_ENV_FILE" ]; then
        echo -e "  ${YELLOW}Existing: ${SYSTEM_ENV_FILE} (not overwritten)${NC}"
        echo -e "  ${YELLOW}  Edit ${SYSTEM_ENV_FILE} to change settings.${NC}"
    else
        if [ ! -f "$env_file" ]; then
            echo -e "${YELLOW}WARNING: src/main/omnia.env not found — skipping env file install${NC}"
            return 0
        fi
        cp -f "$env_file" "$SYSTEM_ENV_FILE"
        chmod 0644 "$SYSTEM_ENV_FILE"
        echo -e "  ${GREEN}Installed: ${SYSTEM_ENV_FILE}${NC}"
    fi

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
    echo -e "${GREEN}                Omnia Venv Created${NC}"
    echo -e "${GREEN}================================================================================${NC}"
    echo ""
    echo -e "  Venv:    ${GREEN}$OMNIA_VENV_PATH${NC}"
    echo -e "  Python:  ${GREEN}$(python --version)${NC}"
    echo ""
    echo -e "${BLUE}Dependencies will be installed by each domain's domain-init.sh.${NC}"
    echo ""

    deactivate 2>/dev/null || true
}

# ─────────────────────────────────────────────────────────────────────────────
# Initialize Domain Input Files
# ─────────────────────────────────────────────────────────────────────────────
init_domains() {
    load_env

    # Activate venv so domain-init.sh can install pip/galaxy deps
    if [ -f "$OMNIA_VENV_PATH/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "$OMNIA_VENV_PATH/bin/activate"
    else
        echo -e "${RED}ERROR: Venv not found at ${OMNIA_VENV_PATH}${NC}"
        echo -e "${YELLOW}Run './omnia.sh -s' first to create the venv${NC}"
        exit 1
    fi

    local domain_init_args=()
    if [ "$DEPS_ONLY" = true ]; then
        domain_init_args+=(--deps-only)
        echo -e "${BLUE}Initializing domains (deps only, skipping input staging) ...${NC}"
    else
        echo -e "${BLUE}Initializing domains (deps + log dirs + input files) ...${NC}"
    fi

    local initialized=0
    for domain in "${DOMAINS[@]}"; do
        local init_script="$SRC_DIR/$domain/domain-init.sh"
        if [ -f "$init_script" ]; then
            chmod +x "$init_script"
            if bash "$init_script" "${domain_init_args[@]}"; then
                initialized=$((initialized + 1))
            else
                echo -e "${YELLOW}WARNING: domain-init.sh failed for $domain — continuing${NC}"
            fi
        fi
    done
    if [ "$initialized" -eq 0 ]; then
        echo -e "${YELLOW}No domain-init.sh scripts found in any domain${NC}"
    else
        echo -e "${GREEN}Domain init completed for ${initialized} domain(s)${NC}"
    fi

    # Show installed summary
    if command -v ansible >/dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}Ansible: $(ansible --version | head -1)${NC}"
        echo -e "${BLUE}Installed collections:${NC}"
        ansible-galaxy collection list 2>/dev/null | grep -E "^(ansible\.|containers\.|community\.|kubernetes\.|omnia\.)" || true
    fi

    deactivate 2>/dev/null || true
}

# ─────────────────────────────────────────────────────────────────────────────
# Run Domain Playbook
# ─────────────────────────────────────────────────────────────────────────────
run_domain() {
    local domain="$1"
    shift
    local tags=""
    local extra_args=()

    # Parse remaining args for --tags
    while [ $# -gt 0 ]; do
        case "$1" in
            --tags|-t)
                if [ $# -lt 2 ]; then
                    echo -e "${RED}ERROR: --tags requires a value${NC}"
                    exit 1
                fi
                tags="$2"
                shift 2
                ;;
            *)
                extra_args+=("$1")
                shift
                ;;
        esac
    done

    # Validate domain exists
    local domain_found=false
    for d in "${DOMAINS[@]}"; do
        if [ "$d" = "$domain" ]; then
            domain_found=true
            break
        fi
    done

    if [ "$domain_found" = false ]; then
        echo -e "${RED}ERROR: Unknown domain '$domain'${NC}"
        echo -e "${YELLOW}Available domains: ${DOMAINS[*]}${NC}"
        exit 1
    fi

    # Find the domain playbook
    local playbook="$SRC_DIR/$domain/playbooks/${domain}.yml"
    if [ ! -f "$playbook" ]; then
        echo -e "${RED}ERROR: No playbook found for domain '$domain'${NC}"
        echo -e "${YELLOW}Expected: src/$domain/playbooks/${domain}.yml${NC}"
        exit 1
    fi

    # Activate venv
    load_env
    if [ ! -f "$OMNIA_VENV_PATH/bin/activate" ]; then
        echo -e "${RED}ERROR: Venv not found at $OMNIA_VENV_PATH${NC}"
        echo -e "${YELLOW}Run './omnia.sh -s' first to create the venv${NC}"
        exit 1
    fi

    # shellcheck disable=SC1091
    source "$OMNIA_VENV_PATH/bin/activate"

    # Build ansible-playbook command
    local cmd=("ansible-playbook" "$playbook")
    if [ -n "$tags" ]; then
        cmd+=("--tags" "$tags")
    fi
    if [ ${#extra_args[@]} -gt 0 ]; then
        cmd+=("${extra_args[@]}")
    fi

    echo -e "${BLUE}Running: ${cmd[*]}${NC}"
    echo -e "${BLUE}Domain:  $domain${NC}"
    echo -e "${BLUE}Playbook: $playbook${NC}"
    [ -n "$tags" ] && echo -e "${BLUE}Tags:    $tags${NC}"
    echo ""

    cd "$SRC_DIR/$domain"
    "${cmd[@]}"
    local rc=$?

    deactivate 2>/dev/null || true
    return $rc
}

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────
cleanup_omnia() {
    local cleanup_all="${1:-false}"
    load_env

    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}               Omnia Cleanup${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""

    if [ "$cleanup_all" = true ]; then
        echo -e "${RED}WARNING: This will remove ALL Omnia data including:${NC}"
        echo -e "  - Python venv:          ${OMNIA_VENV_PATH}"
        echo -e "  - System env:           ${SYSTEM_ENV_FILE}"
        echo -e "  - Profile drop-in:      ${PROFILE_DROP_IN}"
        echo -e "  - Activation script:    ${OMNIA_DATA_PATH}/activate-omnia.sh"
        echo -e "  - ALL data:             ${OMNIA_DATA_PATH}/ (input, output, logs, everything)"
    else
        echo -e "${YELLOW}This will remove the Omnia venv and system environment files:${NC}"
        echo -e "  - Python venv:          ${OMNIA_VENV_PATH}"
        echo -e "  - System env:           ${SYSTEM_ENV_FILE}"
        echo -e "  - Profile drop-in:      ${PROFILE_DROP_IN}"
        echo -e "  - Activation script:    ${OMNIA_DATA_PATH}/activate-omnia.sh"
        echo ""
        echo -e "${GREEN}Data at ${OMNIA_DATA_PATH}/ will be preserved.${NC}"
        echo -e "${YELLOW}Use --cleanup --all to remove everything.${NC}"
    fi

    echo ""
    read -rp "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo -e "${YELLOW}Cleanup cancelled.${NC}"
        return 0
    fi

    echo ""

    # Remove venv
    if [ -d "$OMNIA_VENV_PATH" ]; then
        echo -e "${BLUE}Removing venv: ${OMNIA_VENV_PATH}${NC}"
        rm -rf "$OMNIA_VENV_PATH"
        echo -e "  ${GREEN}Removed.${NC}"
    else
        echo -e "  ${YELLOW}Venv not found at ${OMNIA_VENV_PATH} — skipping.${NC}"
    fi

    # Remove activation script
    if [ -f "${OMNIA_DATA_PATH}/activate-omnia.sh" ]; then
        echo -e "${BLUE}Removing activation script${NC}"
        rm -f "${OMNIA_DATA_PATH}/activate-omnia.sh"
        echo -e "  ${GREEN}Removed.${NC}"
    fi

    # Remove system env file
    if [ -f "$SYSTEM_ENV_FILE" ]; then
        echo -e "${BLUE}Removing system env: ${SYSTEM_ENV_FILE}${NC}"
        rm -f "$SYSTEM_ENV_FILE"
        echo -e "  ${GREEN}Removed.${NC}"
    fi
    # Remove empty /etc/omnia dir
    if [ -d "$SYSTEM_ENV_DIR" ]; then
        rmdir "$SYSTEM_ENV_DIR" 2>/dev/null || true
    fi

    # Remove profile drop-in
    if [ -f "$PROFILE_DROP_IN" ]; then
        echo -e "${BLUE}Removing profile drop-in: ${PROFILE_DROP_IN}${NC}"
        rm -f "$PROFILE_DROP_IN"
        echo -e "  ${GREEN}Removed.${NC}"
    fi

    # If --all, remove entire data path
    if [ "$cleanup_all" = true ]; then
        if [ -d "$OMNIA_DATA_PATH" ]; then
            echo -e "${BLUE}Removing all data: ${OMNIA_DATA_PATH}${NC}"
            rm -rf "$OMNIA_DATA_PATH"
            echo -e "  ${GREEN}Removed.${NC}"
        fi
    fi

    echo ""
    echo -e "${GREEN}================================================================================${NC}"
    echo -e "${GREEN}               Cleanup Complete${NC}"
    echo -e "${GREEN}================================================================================${NC}"
    if [ "$cleanup_all" = true ]; then
        echo -e "  ${GREEN}All Omnia data, venv, and system env files have been removed.${NC}"
    else
        echo -e "  ${GREEN}Venv and system env files removed. Data at ${OMNIA_DATA_PATH}/ preserved.${NC}"
    fi
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Catalog Copy
# ─────────────────────────────────────────────────────────────────────────────
copy_catalog() {
    load_env

    local catalog_source="${SCRIPT_DIR}/samples/catalog_rhel.json"
    local catalog_target_dir="${OMNIA_DATA_PATH}/catalog"
    local catalog_target_file="${catalog_target_dir}/catalog_rhel.json"

    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}               Catalog Copy${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""

    if [ ! -f "$catalog_source" ]; then
        echo -e "${RED}ERROR: Catalog source not found: ${catalog_source}${NC}"
        echo -e "${YELLOW}Expected at: src/main/samples/catalog_rhel.json${NC}"
        exit 1
    fi

    mkdir -p "$catalog_target_dir"

    # Copy all sample/catalog files from src/main/samples/
    local copied=0
    for sample_file in "$SCRIPT_DIR"/samples/*.json "$SCRIPT_DIR"/samples/*.yml "$SCRIPT_DIR"/samples/*.yaml; do
        if [ -f "$sample_file" ]; then
            local filename
            filename="$(basename "$sample_file")"
            cp -f "$sample_file" "${catalog_target_dir}/${filename}"
            echo -e "  ${GREEN}Copied: ${filename} -> ${catalog_target_dir}/${filename}${NC}"
            copied=$((copied + 1))
        fi
    done

    if [ "$copied" -eq 0 ]; then
        echo -e "${YELLOW}No catalog/sample files found in ${SCRIPT_DIR}/samples/${NC}"
        return 1
    fi

    echo ""
    echo -e "${GREEN}Catalog files copied to: ${catalog_target_dir}/${NC}"
    echo -e "${GREEN}  CATALOG_FILE_PATH=${catalog_target_file}${NC}"
    echo ""
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
  --setup-venv, -s      Create/update the shared Python venv, then run all
                        domain-init.sh scripts (pip deps, Galaxy collections,
                        log dirs, and input file staging).
  --init, -i            Re-run domain-init.sh scripts only (no venv rebuild).
                        Useful to re-stage input files or install deps after
                        editing domain configs. Runs automatically with -s.
  --catalog             Copy catalog/sample files from src/main/samples/ to
                        \$OMNIA_DATA_PATH/catalog/. Makes catalog_rhel.json available at runtime.

EXECUTION COMMANDS:
  --run, -r <domain> [--tags <tags>] [extra ansible args]
                        Activate venv and run the specified domain's playbook.
                        Passes --tags and any extra args to ansible-playbook.

CLEANUP COMMANDS:
  --cleanup             Remove venv, system env files (/etc/omnia/omnia.env,
                        /etc/profile.d/omnia-env.sh), and activation script.
                        Data at \$OMNIA_DATA_PATH/ is preserved.
  --cleanup --all       Remove EVERYTHING: venv, system env, AND all data at
                        \$OMNIA_DATA_PATH/ (full reset). Prompts for confirmation.

OPTIONS:
  --deps-only           With -s or -i: install pip/Galaxy deps but skip input file staging.
                        Cannot be used standalone; requires -s or -i.
  --help, -h            Show this help message.

DOMAINS:
  ${DOMAINS[*]}

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
  ./omnia.sh -s                                # Installs env + venv + deps + input files
  ./omnia.sh -s --deps-only                    # Installs env + venv + deps (skips input staging)

  # Stage domain input files (without full setup):
  ./omnia.sh --init                            # Run all domain-init.sh scripts

  # Copy catalog files to runtime path:
  ./omnia.sh --catalog                         # Copies catalog_rhel.json to \$OMNIA_DATA_PATH/catalog/

  # Run a domain playbook:
  ./omnia.sh --run image_build_manager --tags prepare
  ./omnia.sh -r repo_manager --tags build
  ./omnia.sh -r telemetry                      # Run all tags

  # Validate a domain (uses --tags validate):
  ./omnia.sh --run image_build_manager --tags validate
  ./omnia.sh -r repo_manager --tags validate

  # Cleanup (remove venv + system env, preserve data):
  ./omnia.sh --cleanup

  # Full cleanup (remove EVERYTHING including data):
  ./omnia.sh --cleanup --all

  # Diagnostics:
  omnia-cli status               # All domains
  omnia-cli repo-manager         # Repo manager details
EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Dispatch
# ─────────────────────────────────────────────────────────────────────────────
main() {
    DEPS_ONLY=false  # Global — used by init_domains()
    local CLEANUP_ALL=false
    local command=""
    local run_domain_name=""
    local run_extra_args=()

    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    # Parse arguments — first pass to identify the command
    while [ $# -gt 0 ]; do
        case "$1" in
            --setup-venv|-s)
                command="setup-venv"
                shift
                ;;
            --deps-only)
                DEPS_ONLY=true
                shift
                ;;
            --init|-i)
                command="init"
                shift
                ;;
            --catalog)
                command="catalog"
                shift
                ;;
            --cleanup)
                command="cleanup"
                shift
                ;;
            --all)
                CLEANUP_ALL=true
                shift
                ;;
            --run|-r)
                command="run"
                if [ $# -lt 2 ]; then
                    echo -e "${RED}ERROR: --run requires a domain name${NC}"
                    echo -e "${YELLOW}Usage: $0 --run <domain> [--tags <tags>]${NC}"
                    echo -e "${YELLOW}Domains: ${DOMAINS[*]}${NC}"
                    exit 1
                fi
                run_domain_name="$2"
                shift 2
                # Collect remaining args for ansible-playbook
                while [ $# -gt 0 ]; do
                    run_extra_args+=("$1")
                    shift
                done
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

    # Validate flag combinations
    if [ "$DEPS_ONLY" = true ] && [ "$command" != "setup-venv" ] && [ "$command" != "init" ]; then
        echo -e "${RED}ERROR: --deps-only requires --setup-venv (-s) or --init (-i)${NC}"
        echo -e "${YELLOW}Usage: $0 -s --deps-only or $0 -i --deps-only${NC}"
        exit 1
    fi

    case "$command" in
        setup-venv)
            setup_venv
            init_domains

            # ── Post-setup activation instructions (shown LAST) ──
            echo ""
            echo -e "${GREEN}================================================================================${NC}"
            echo -e "${GREEN}               Setup Complete${NC}"
            echo -e "${GREEN}================================================================================${NC}"
            echo ""
            echo -e "${GREEN}Environment helper created:${NC}"
            echo -e "  ${GREEN}${OMNIA_DATA_PATH}/activate-omnia.sh${NC}"
            echo ""
            echo -e "${YELLOW}Activate in your shell:${NC}"
            echo -e "  ${GREEN}source ${OMNIA_DATA_PATH}/activate-omnia.sh${NC}"
            echo ""
            ;;
        init)
            init_domains
            ;;
        catalog)
            copy_catalog
            ;;
        cleanup)
            cleanup_omnia "$CLEANUP_ALL"
            ;;
        run)
            run_domain "$run_domain_name" "${run_extra_args[@]}"
            ;;
        help)
            show_help
            ;;
    esac
}

main "$@"
