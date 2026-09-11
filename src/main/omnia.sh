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
#   1. For a first-time install, edit src/main/omnia.env with your settings
#   2. Run: ./omnia.sh --setup-venv   (one-time Python + Ansible setup)
#
# During setup, this script:
#   - Installs omnia.env to /etc/omnia/omnia.env on the first run
#   - Preserves /etc/omnia/omnia.env on subsequent runs
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
SRC_DIR="$(dirname "$SCRIPT_DIR")"
readonly SRC_DIR
REPO_ROOT="$(dirname "$SRC_DIR")"
readonly REPO_ROOT

# Color definitions
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly YELLOW='\033[0;33m'
readonly DIM='\033[2m'
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

# Core infrastructure domain prepare order for --prepare-base
# Only these three domains are prepared by --prepare-base
readonly PREPARE_ORDER=(
    "repo_manager"          # First: Pulp server for package repos
    "image_build_manager"   # Second: MinIO + Registry for image building
    "orchestrator"          # Third: OpenLDAP, functional groups, credential management
)

# Lifecycle phases to run for each base domain (in order). Repo Manager uses
# precheck for its validation phase; the other base domains use validate.
readonly LIFECYCLE_PHASES=(
    "validate"      # Validate input configuration
    "credentials"   # Collect and encrypt credentials
    "prepare"       # Deploy infrastructure
)

# Variables owned by omnia.env. Clear these before loading the selected file so
# values removed from a config cannot leak in from a previously sourced shell.
readonly OMNIA_ENV_VARIABLES=(
    SYSTEM_ADMIN_NIC_IPV4
    OMNIA_DATA_PATH
    OMNIA_PROJECT_NAME
    SYSTEM_HOSTNAME
    SYSTEM_DOMAIN_NAME
    OMNIA_VENV_PATH
    OMNIA_VERSION
    CATALOG_FILE_PATH
    IMAGE_BUILD_MANAGER_DATA_PATH
    REPO_MANAGER_DATA_PATH
    DISCOVERY_DATA_PATH
    ORCHESTRATOR_DATA_PATH
    TELEMETRY_DATA_PATH
    BUILD_STREAM_DATA_PATH
)

# ─────────────────────────────────────────────────────────────────────────────
# Environment Loading
# ─────────────────────────────────────────────────────────────────────────────
source_omnia_env() {
    local env_file="$1"
    local variable
    local allexport_was_set=false

    if [[ "$-" == *a* ]]; then
        allexport_was_set=true
    fi

    for variable in "${OMNIA_ENV_VARIABLES[@]}"; do
        unset -v "$variable"
    done

    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    if [ "$allexport_was_set" = false ]; then
        set +a
    fi

    ACTIVE_ENV_FILE="$env_file"
}

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
    local env_file="${ACTIVE_ENV_FILE:-/etc/omnia/omnia.env}"

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
        echo -e "${YELLOW}Set the required variables in ${env_file} and re-run ./omnia.sh --setup-venv${NC}"
        echo -e "${YELLOW}Or export them manually:  export SYSTEM_ADMIN_NIC_IPV4=<ip>${NC}"
        exit 1
    fi

    export SYSTEM_ADMIN_NIC_IPV4

    # --- Validate hostname matches system (hostname -s) ---
    local actual_hostname
    actual_hostname="$(hostname -s 2>/dev/null || hostname 2>/dev/null)"
    if [ -n "$actual_hostname" ] && [ "$actual_hostname" != "$SYSTEM_HOSTNAME" ]; then
        echo -e "${RED}ERROR: SYSTEM_HOSTNAME (${SYSTEM_HOSTNAME}) does not match actual hostname (${actual_hostname})${NC}"
        echo -e "${YELLOW}  Fix the installed configuration: update SYSTEM_HOSTNAME in ${env_file}, then re-run ./omnia.sh -s${NC}"
        if [ "$env_file" = "$SYSTEM_ENV_FILE" ]; then
            echo -e "${YELLOW}  If you corrected ${SCRIPT_DIR}/omnia.env instead, apply it with:${NC}"
            echo -e "${YELLOW}    ./omnia.sh -s --force-env${NC}"
            echo -e "${YELLOW}  Note: --force-env replaces all values in ${SYSTEM_ENV_FILE} with the repository file.${NC}"
        fi
        echo -e "${YELLOW}  Or:  hostnamectl set-hostname ${SYSTEM_HOSTNAME}${NC}"
        errors=$((errors + 1))
    fi

    # --- Validate domain matches system (hostname -d) ---
    local actual_domain
    actual_domain="$(hostname -d 2>/dev/null || true)"
    if [ -n "$actual_domain" ] && [ "$actual_domain" != "$SYSTEM_DOMAIN_NAME" ]; then
        echo -e "${YELLOW}WARNING: SYSTEM_DOMAIN_NAME (${SYSTEM_DOMAIN_NAME}) does not match system domain (${actual_domain})${NC}"
        echo -e "${YELLOW}  Fix: update SYSTEM_DOMAIN_NAME in ${env_file}${NC}"
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
            echo -e "${YELLOW}  Fix: update SYSTEM_ADMIN_NIC_IPV4 in ${env_file}${NC}"
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

validate_env_source() {
    local env_file="$1"
    local errors=0

    if [ ! -r "$env_file" ]; then
        echo -e "${RED}ERROR: Environment file is not readable: ${env_file}${NC}"
        return 1
    fi

    if ! bash -n "$env_file"; then
        echo -e "${RED}ERROR: Environment file has invalid Bash syntax: ${env_file}${NC}"
        return 1
    fi

    # Read from a clean environment so inherited variables cannot hide a
    # missing value in the file being validated.
    local ip_value
    ip_value="$(env -i PATH="$PATH" bash --noprofile --norc -c \
        '. "$1"; printf "%s" "${SYSTEM_ADMIN_NIC_IPV4:-}"' bash "$env_file")"

    if [ -z "$ip_value" ]; then
        echo -e "${RED}ERROR: SYSTEM_ADMIN_NIC_IPV4 is not set in ${env_file}${NC}"
        echo -e "${YELLOW}  Edit ${env_file} and set SYSTEM_ADMIN_NIC_IPV4=<your_admin_nic_ip>${NC}"
        errors=$((errors + 1))
    fi

    # Validate all four IPv4 octets, including their numeric range.
    if [ -n "$ip_value" ]; then
        local octets
        local octet
        IFS='.' read -ra octets <<< "$ip_value"
        if [ "${#octets[@]}" -ne 4 ]; then
            echo -e "${RED}ERROR: SYSTEM_ADMIN_NIC_IPV4 ('${ip_value}') is not a valid IPv4 address in ${env_file}${NC}"
            echo -e "${YELLOW}  Edit ${env_file} and fix SYSTEM_ADMIN_NIC_IPV4${NC}"
            errors=$((errors + 1))
        else
            for octet in "${octets[@]}"; do
                if [[ ! "$octet" =~ ^[0-9]{1,3}$ ]] || [ "$((10#$octet))" -gt 255 ]; then
                    echo -e "${RED}ERROR: SYSTEM_ADMIN_NIC_IPV4 ('${ip_value}') is not a valid IPv4 address in ${env_file}${NC}"
                    echo -e "${YELLOW}  Edit ${env_file} and fix SYSTEM_ADMIN_NIC_IPV4${NC}"
                    errors=$((errors + 1))
                    break
                fi
            done
        fi
    fi

    if [ "$errors" -gt 0 ]; then
        echo -e "${RED}Environment file validation failed. Fix ${env_file} before running setup.${NC}"
        return 1
    fi
}

install_system_env() {
    local source_env_file="${1:-$SCRIPT_DIR/omnia.env}"
    local system_env_file="${2:-$SYSTEM_ENV_FILE}"
    local profile_drop_in="${3:-$PROFILE_DROP_IN}"
    local system_env_dir
    system_env_dir="$(dirname "$system_env_file")"
    local env_file

    echo -e "${BLUE}Configuring system environment...${NC}"

    if [ -f "$system_env_file" ] && [ "${FORCE_ENV:-false}" != true ]; then
        env_file="$system_env_file"
        echo -e "  ${GREEN}Using existing: ${system_env_file}${NC}"
        if [ -f "$source_env_file" ] && ! diff -q "$source_env_file" "$system_env_file" >/dev/null 2>&1; then
            echo -e "  ${YELLOW}Repository omnia.env differs; preserving the system configuration.${NC}"
            echo -e "  ${YELLOW}To apply changes made in ${source_env_file}, run:${NC}"
            echo -e "    ${YELLOW}./omnia.sh -s --force-env${NC}"
            echo -e "  ${DIM}This replaces all values in ${system_env_file} with the repository file.${NC}"
        fi
    else
        if [ ! -f "$source_env_file" ]; then
            echo -e "${RED}ERROR: Bootstrap environment file not found: ${source_env_file}${NC}"
            return 1
        fi

        validate_env_source "$source_env_file"
        mkdir -p "$system_env_dir"
        install -m 0644 "$source_env_file" "$system_env_file"
        env_file="$system_env_file"
        if [ "${FORCE_ENV:-false}" = true ]; then
            echo -e "  ${GREEN}Replaced: ${system_env_file} (--force-env)${NC}"
        else
            echo -e "  ${GREEN}Installed: ${system_env_file}${NC}"
        fi
    fi

    # Validate the file that setup will actually use before loading it.
    validate_env_source "$env_file"

    local quoted_system_env_file
    printf -v quoted_system_env_file '%q' "$system_env_file"
    mkdir -p "$(dirname "$profile_drop_in")"
    cat > "$profile_drop_in" <<PROFILE_EOF
#!/bin/bash
#
# Omnia environment variables
#

if [ -f ${quoted_system_env_file} ]; then
    unset SYSTEM_ADMIN_NIC_IPV4 OMNIA_DATA_PATH OMNIA_PROJECT_NAME \
        SYSTEM_HOSTNAME SYSTEM_DOMAIN_NAME OMNIA_VENV_PATH OMNIA_VERSION \
        CATALOG_FILE_PATH IMAGE_BUILD_MANAGER_DATA_PATH REPO_MANAGER_DATA_PATH \
        DISCOVERY_DATA_PATH ORCHESTRATOR_DATA_PATH TELEMETRY_DATA_PATH \
        BUILD_STREAM_DATA_PATH
    _omnia_allexport_was_set=false
    if [[ "\$-" == *a* ]]; then
        _omnia_allexport_was_set=true
    fi
    set -a
    . ${quoted_system_env_file}
    if [ "\$_omnia_allexport_was_set" = false ]; then
        set +a
    fi
    unset _omnia_allexport_was_set
fi
PROFILE_EOF

    chmod 0644 "$profile_drop_in"

    echo -e "  ${GREEN}Installed: ${profile_drop_in}${NC}"

    #
    # Load into current script execution
    #
    source_omnia_env "$env_file"

    echo -e "${GREEN}System environment ready.${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Base Directory Creation
# ─────────────────────────────────────────────────────────────────────────────
create_base_dirs() {
    echo -e "${BLUE}Creating base directory structure at ${OMNIA_DATA_PATH}...${NC}"
    mkdir -p "${OMNIA_DATA_PATH}"
    mkdir -p "${OMNIA_DATA_PATH}/.data"
    echo -e "${GREEN}Base directories created. Domain directories will be created by respective playbooks.${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Venv Setup
# ─────────────────────────────────────────────────────────────────────────────
setup_venv() {
    local start_time=$SECONDS
    local setup_complete=false

    cleanup_on_failure() {
        if [ "$setup_complete" = false ]; then
            echo -e "\n${RED}Setup interrupted. Venv may be incomplete.${NC}"
            echo -e "${YELLOW}Re-run: ./omnia.sh -s${NC}"
            deactivate 2>/dev/null || true
        fi
    }
    trap cleanup_on_failure EXIT INT TERM

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
    unset SYSTEM_ADMIN_NIC_IPV4 OMNIA_DATA_PATH OMNIA_PROJECT_NAME \
        SYSTEM_HOSTNAME SYSTEM_DOMAIN_NAME OMNIA_VENV_PATH OMNIA_VERSION \
        CATALOG_FILE_PATH IMAGE_BUILD_MANAGER_DATA_PATH REPO_MANAGER_DATA_PATH \
        DISCOVERY_DATA_PATH ORCHESTRATOR_DATA_PATH TELEMETRY_DATA_PATH \
        BUILD_STREAM_DATA_PATH
    _omnia_allexport_was_set=false
    if [[ "$-" == *a* ]]; then
        _omnia_allexport_was_set=true
    fi
    set -a
    . /etc/omnia/omnia.env
    if [ "$_omnia_allexport_was_set" = false ]; then
        set +a
    fi
    unset _omnia_allexport_was_set
fi

if [ -f "${OMNIA_VENV_PATH}/bin/activate" ]; then
    source "${OMNIA_VENV_PATH}/bin/activate"
else
    echo "ERROR: Virtual environment not found at ${OMNIA_VENV_PATH}"
    return 1 2>/dev/null || exit 1
fi

# Load the shared omnia-cli and omnia.sh Bash completion
if [ -f /etc/bash_completion.d/omnia-bash-completion ]; then
    source /etc/bash_completion.d/omnia-bash-completion
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

    local elapsed=$(( SECONDS - start_time ))
    local mins=$(( elapsed / 60 ))
    local secs=$(( elapsed % 60 ))
    echo -e "  ${GREEN}Setup completed in ${mins}m ${secs}s${NC}"
    echo ""

    setup_complete=true
    trap - EXIT INT TERM

    deactivate 2>/dev/null || true
}

# ─────────────────────────────────────────────────────────────────────────────
# Initialize Domain Input Files
# Accepts an optional comma-separated domain filter (e.g. "repo_manager,telemetry").
# If empty or "all", initializes every domain.
# ─────────────────────────────────────────────────────────────────────────────
init_domains() {
    local domain_filter="${1:-}"
    local start_time=$SECONDS
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

    # ── Build skip set ──
    declare -A skip_set
    if [ -n "$SKIP_DOMAINS" ]; then
        IFS=',' read -ra skip_list <<< "$SKIP_DOMAINS"
        for skip in "${skip_list[@]}"; do
            skip="$(echo "$skip" | xargs)"  # trim whitespace
            # Validate that the skipped domain actually exists
            local valid=false
            for d in "${DOMAINS[@]}"; do
                if [ "$d" = "$skip" ]; then
                    valid=true
                    break
                fi
            done
            if [ "$valid" = false ]; then
                echo -e "${RED}ERROR: Unknown domain in --skip: '$skip'${NC}"
                echo -e "${YELLOW}Available domains: ${DOMAINS[*]}${NC}"
                exit 1
            fi
            skip_set["$skip"]=1
        done
    fi

    # ── Build the list of domains to initialize ──
    local target_domains=()

    if [ -z "$domain_filter" ] || [ "$domain_filter" = "all" ]; then
        # Start with all domains, then apply skip filter
        for d in "${DOMAINS[@]}"; do
            if [ -z "${skip_set[$d]+_}" ]; then
                target_domains+=("$d")
            else
                echo -e "${YELLOW}Skipping domain: $d (--skip)${NC}"
            fi
        done
    else
        # Explicit include list — skip filter not allowed (validated earlier)
        IFS=',' read -ra requested <<< "$domain_filter"
        for req in "${requested[@]}"; do
            req="$(echo "$req" | xargs)"
            local found=false
            for d in "${DOMAINS[@]}"; do
                if [ "$d" = "$req" ]; then
                    found=true
                    break
                fi
            done
            if [ "$found" = true ]; then
                target_domains+=("$req")
            else
                echo -e "${RED}ERROR: Unknown domain '$req'${NC}"
                echo -e "${YELLOW}Available domains: ${DOMAINS[*]}${NC}"
                exit 1
            fi
        done
    fi

    # ── Bail if nothing to init ──
    if [ ${#target_domains[@]} -eq 0 ]; then
        echo -e "${YELLOW}No domains to initialize (all were skipped).${NC}"
        deactivate 2>/dev/null || true
        return 0
    fi

    local domain_init_args=()
    if [ "$DEPS_ONLY" = true ]; then
        domain_init_args+=(--deps-only)
        echo -e "${BLUE}Initializing domains (deps only, skipping input staging) ...${NC}"
    else
        echo -e "${BLUE}Initializing domains (deps + log dirs + input files) ...${NC}"
    fi
    if [ "$FORCE_DEPS" = true ]; then
        domain_init_args+=(--force-deps)
    fi

    # Show target list (always useful when skipping)
    echo -e "${BLUE}  Targets: ${target_domains[*]}${NC}"
    if [ -n "$SKIP_DOMAINS" ]; then
        echo -e "${YELLOW}  Skipped: ${SKIP_DOMAINS}${NC}"
    fi

    # ── Dry-run mode ──
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}DRY RUN — would initialize these domains:${NC}"
        for domain in "${target_domains[@]}"; do
            local init_script="$SRC_DIR/$domain/domain-init.sh"
            local has_script=" (no domain-init.sh)"
            [ -f "$init_script" ] && has_script=""
            echo -e "  ${GREEN}${domain}${has_script}${NC}"
        done
        if [ -n "$SKIP_DOMAINS" ]; then
            echo -e "${YELLOW}  Skipped: ${SKIP_DOMAINS}${NC}"
        fi
        deactivate 2>/dev/null || true
        return 0
    fi

    local initialized=0
    for domain in "${target_domains[@]}"; do
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

    local elapsed=$(( SECONDS - start_time ))
    local mins=$(( elapsed / 60 ))
    local secs=$(( elapsed % 60 ))
    echo -e "  ${GREEN}Domain init completed in ${mins}m ${secs}s${NC}"

    deactivate 2>/dev/null || true
}

# ─────────────────────────────────────────────────────────────────────────────
# Stage-Order Warning (non-blocking)
# ─────────────────────────────────────────────────────────────────────────────
warn_stage_order() {
    local domain="$1"
    local project="${OMNIA_PROJECT_NAME:-project_default}"
    local data_path="${OMNIA_DATA_PATH:-/opt/omnia}"

    case "$domain" in
        image_build_manager)
            # image_build_manager reads repo_status.yml from repo_manager
            local repo_status="$data_path/repo_manager/output/$project/repo_status.yml"
            if [ ! -f "$repo_status" ]; then
                echo -e "${YELLOW}WARNING: repo_manager has not been run yet (no repo_status.yml found).${NC}"
                echo -e "${YELLOW}  Recommended order: repo_manager -> image_build_manager -> orchestrator${NC}"
                echo -e "${YELLOW}  Run: ./omnia.sh --run repo_manager${NC}"
                echo ""
            fi
            ;;
        orchestrator)
            # orchestrator reads build_status.yml from image_build_manager
            local build_status="$data_path/image_build_manager/output/$project/build_status.yml"
            if [ ! -f "$build_status" ]; then
                echo -e "${YELLOW}WARNING: image_build_manager has not been run yet (no build_status.yml found).${NC}"
                echo -e "${YELLOW}  Recommended order: repo_manager -> image_build_manager -> orchestrator${NC}"
                echo -e "${YELLOW}  Run: ./omnia.sh --run image_build_manager${NC}"
                echo ""
            fi
            ;;
    esac
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

    # --- Stage-order warnings (non-blocking) ---
    warn_stage_order "$domain"

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
# Prepare Base Domains
# Orchestrates prepare steps of core infrastructure domains in dependency order
# ─────────────────────────────────────────────────────────────────────────────
prepare_tag_for_phase() {
    local domain="$1"
    local phase="$2"

    if [ "$domain" = "repo_manager" ] && [ "$phase" = "validate" ]; then
        printf '%s' "precheck"
    else
        printf '%s' "$phase"
    fi
}

prepare_base_domains() {
    local skip_filter="${SKIP_DOMAINS:-}"
    local dry_run="${DRY_RUN:-false}"
    local start_time=$SECONDS

    load_env

    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}               Prepare Base Infrastructure Domains${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""

    # Activate venv
    if [ ! -f "$OMNIA_VENV_PATH/bin/activate" ]; then
        echo -e "${RED}ERROR: Venv not found at $OMNIA_VENV_PATH${NC}"
        echo -e "${YELLOW}Run './omnia.sh -s' first to create the venv${NC}"
        exit 1
    fi

    # shellcheck disable=SC1091
    source "$OMNIA_VENV_PATH/bin/activate"

    # ── Build target domain list from PREPARE_ORDER ──
    local target_domains=()
    for domain in "${PREPARE_ORDER[@]}"; do
        target_domains+=("$domain")
    done

    # ── Apply skip filter ──
    if [ -n "$skip_filter" ]; then
        IFS=',' read -ra skip_list <<< "$skip_filter"
        local filtered_domains=()

        # Validate skip domains
        for skip_domain in "${skip_list[@]}"; do
            skip_domain="$(echo "$skip_domain" | xargs)"
            local valid=false
            for domain in "${PREPARE_ORDER[@]}"; do
                if [ "$domain" = "$skip_domain" ]; then
                    valid=true
                    break
                fi
            done
            if [ "$valid" = false ]; then
                echo -e "${RED}ERROR: Unknown domain in --skip: '$skip_domain'${NC}"
                echo -e "${YELLOW}Valid domains for --prepare-base: ${PREPARE_ORDER[*]}${NC}"
                exit 1
            fi
        done

        for domain in "${target_domains[@]}"; do
            local skip=false
            for skip_domain in "${skip_list[@]}"; do
                skip_domain="$(echo "$skip_domain" | xargs)"
                if [ "$domain" = "$skip_domain" ]; then
                    skip=true
                    break
                fi
            done
            if [ "$skip" = false ]; then
                filtered_domains+=("$domain")
            else
                echo -e "${YELLOW}Skipping domain: $domain${NC}"
            fi
        done
        target_domains=("${filtered_domains[@]}")
    fi

    # ── Bail if nothing to prepare ──
    if [ ${#target_domains[@]} -eq 0 ]; then
        echo -e "${YELLOW}No domains to prepare (all were skipped).${NC}"
        deactivate 2>/dev/null || true
        return 0
    fi

    # ── Show prepare order ──
    echo -e "${BLUE}Preparing domains in order:${NC}"
    for domain in "${target_domains[@]}"; do
        echo -e "  ${GREEN}${domain}${NC}"
    done
    echo ""

    # ── Dry-run mode ──
    if [ "$dry_run" = true ]; then
        echo -e "${BLUE}DRY RUN — would prepare these domains (phase-by-phase, fail-fast):${NC}"
        echo ""
        for phase in "${LIFECYCLE_PHASES[@]}"; do
            echo -e "  ${BLUE}Phase: $phase${NC}"
            for domain in "${target_domains[@]}"; do
                local domain_tag
                domain_tag="$(prepare_tag_for_phase "$domain" "$phase")"
                echo -e "    ${GREEN}${domain}${NC} ${DIM}(--tags ${domain_tag})${NC}"
            done
            echo ""
        done
        echo -e "${YELLOW}Note: Execution stops immediately if any domain fails in any phase.${NC}"
        deactivate 2>/dev/null || true
        return 0
    fi

    # ── Run phases across all domains (phase-by-phase, not domain-by-domain) ──
    for phase in "${LIFECYCLE_PHASES[@]}"; do
        echo -e "${BLUE}================================================================================${NC}"
        echo -e "${BLUE}Phase: $phase (all domains)${NC}"
        echo -e "${BLUE}================================================================================${NC}"
        echo ""

        for domain in "${target_domains[@]}"; do
            local playbook="$SRC_DIR/$domain/playbooks/${domain}.yml"
            local domain_tag
            domain_tag="$(prepare_tag_for_phase "$domain" "$phase")"

            if [ ! -f "$playbook" ]; then
                echo -e "${RED}  ERROR: No playbook found for $domain at $playbook${NC}"
                echo -e "${YELLOW}  Fix the issue above and re-run: ./omnia.sh --prepare-base${NC}"
                deactivate 2>/dev/null || true
                return 1
            fi

            echo -e "${BLUE}  Running: $domain --tags $domain_tag${NC}"

            # Build ansible-playbook command
            local cmd=("ansible-playbook" "$playbook" "--tags" "$domain_tag")

            echo -e "${DIM}    ${cmd[*]}${NC}"

            cd "$SRC_DIR/$domain"
            if "${cmd[@]}"; then
                echo -e "${GREEN}    ✓ $domain $domain_tag completed${NC}"
            else
                local rc=$?
                echo -e "${RED}    ✗ $domain $domain_tag failed (exit code: $rc)${NC}"
                echo ""
                echo -e "${RED}================================================================================${NC}"
                echo -e "${RED}  FAILED: $domain failed in $phase phase. Stopping --prepare-base.${NC}"
                echo -e "${RED}================================================================================${NC}"
                echo -e "${YELLOW}  Fix the issue above and re-run: ./omnia.sh --prepare-base${NC}"
                deactivate 2>/dev/null || true
                return 1
            fi
            echo ""
        done

        echo -e "${GREEN}Phase $phase completed${NC}"
        echo ""
    done

    # ── Summary (only reached on full success due to fail-fast) ──
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}               Prepare Summary${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""
    echo -e "  Prepared: ${GREEN}${#target_domains[@]}${NC}"
    echo -e "  Failed:   ${RED}0${NC}"
    echo ""
    echo -e "${GREEN}Prepared domains: ${target_domains[*]}${NC}"

    deactivate 2>/dev/null || true
}

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────
validate_full_cleanup_state() {
    local data_root
    local logical_data_root
    local configured_data_path="${OMNIA_DATA_PATH%/}"
    local domain domain_dir entry entry_name
    local blockers=()

    if ! data_root="$(realpath -m -- "$OMNIA_DATA_PATH")"; then
        echo -e "${RED}ERROR: Cannot resolve OMNIA_DATA_PATH: ${OMNIA_DATA_PATH}${NC}" >&2
        return 1
    fi
    logical_data_root="$(realpath -ms -- "$OMNIA_DATA_PATH")"
    if [[ "$data_root" != /* ]] || [[ "$data_root" =~ ^(/|/boot|/dev|/etc|/home|/media|/mnt|/opt|/proc|/root|/run|/srv|/sys|/tmp|/usr|/var)$ ]]; then
        echo -e "${RED}ERROR: Refusing full cleanup for unsafe OMNIA_DATA_PATH: ${OMNIA_DATA_PATH}${NC}" >&2
        return 1
    fi
    if [ -L "$configured_data_path" ] || [ "$data_root" != "$logical_data_root" ]; then
        echo -e "${RED}ERROR: Refusing full cleanup because OMNIA_DATA_PATH contains a symbolic link: ${OMNIA_DATA_PATH}${NC}" >&2
        return 1
    fi

    for domain in "${DOMAINS[@]}"; do
        domain_dir="${data_root}/${domain}"
        [ -e "$domain_dir" ] || [ -L "$domain_dir" ] || continue

        if [ -L "$domain_dir" ] || [ ! -d "$domain_dir" ]; then
            blockers+=("${domain_dir} (not a regular directory)")
            continue
        fi
        if [ ! -r "$domain_dir" ] || [ ! -x "$domain_dir" ]; then
            blockers+=("${domain_dir} (cannot be fully inspected)")
            continue
        fi

        while IFS= read -r -d '' entry; do
            entry_name="$(basename "$entry")"
            case "$entry_name" in
                input) ;;
                *) blockers+=("$entry") ;;
            esac
        done < <(find -P "$domain_dir" -mindepth 1 -maxdepth 1 -print0)
    done

    if [ "${#blockers[@]}" -gt 0 ]; then
        echo -e "${RED}ERROR: --cleanup --all cannot continue because domain cleanup is incomplete.${NC}"
        echo -e "${RED}The following paths contain deployed, generated, or unrecognized state:${NC}"
        printf '  - %s\n' "${blockers[@]}"
        echo ""
        echo -e "${YELLOW}No files were removed. Run the matching domain cleanup first, for example:${NC}"
        echo "  ./omnia.sh --run <domain> --tags cleanup"
        echo -e "${YELLOW}Then remove any intentionally retained paths reported above and retry.${NC}"
        return 1
    fi
}

cleanup_domain_initializer_artifacts() {
    local domain init_script

    for domain in "${DOMAINS[@]}"; do
        init_script="${SRC_DIR}/${domain}/domain-init.sh"
        if [ ! -x "$init_script" ]; then
            echo -e "${RED}ERROR: Domain cleanup helper is missing or not executable: ${init_script}${NC}" >&2
            return 1
        fi
        DOMAIN_INIT_LOG_ROOT="/var/log/omnia" "$init_script" --cleanup
    done
}

cleanup_omnia() {
    local cleanup_all="${1:-false}"
    local skip_approval="${2:-false}"
    local confirm=""
    load_env

    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}               Omnia Cleanup${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""

    if [ "$cleanup_all" = true ]; then
        # Refuse before prompting or deleting if lifecycle cleanup is pending.
        validate_full_cleanup_state || return 1

        echo -e "${RED}WARNING: This will remove ALL Omnia data including:${NC}"
        echo -e "  - Python venv:          ${OMNIA_VENV_PATH}"
        echo -e "  - System env:           ${SYSTEM_ENV_FILE}"
        echo -e "  - Profile drop-in:      ${PROFILE_DROP_IN}"
        echo -e "  - omnia-cli:            /usr/local/bin/omnia-cli"
        echo -e "  - Bash completion:      /etc/bash_completion.d/omnia-bash-completion"
        echo -e "  - Activation script:    ${OMNIA_DATA_PATH}/activate-omnia.sh"
        echo -e "  - Initializer input data: ${OMNIA_DATA_PATH}/<domain>/input"
        echo -e "  - Remaining Omnia data:      ${OMNIA_DATA_PATH}/"
    else
        echo -e "${YELLOW}This will remove the Omnia venv, system environment files, omnia-cli, and dependency cache:${NC}"
        echo -e "  - Python venv:          ${OMNIA_VENV_PATH}"
        echo -e "  - System env:           ${SYSTEM_ENV_FILE}"
        echo -e "  - Profile drop-in:      ${PROFILE_DROP_IN}"
        echo -e "  - omnia-cli:            /usr/local/bin/omnia-cli"
        echo -e "  - Bash completion:      /etc/bash_completion.d/omnia-bash-completion"
        echo -e "  - Activation script:    ${OMNIA_DATA_PATH}/activate-omnia.sh"
        echo -e "  - Dependency cache:     ${OMNIA_DATA_PATH}/.data/deps-cache/"
        echo ""
        echo -e "${GREEN}Runtime data at ${OMNIA_DATA_PATH}/ (input, output, logs) will be preserved.${NC}"
        echo -e "${YELLOW}Use --cleanup --all for a guarded full reset.${NC}"
    fi

    echo ""
    if [ "$skip_approval" = true ]; then
        echo -e "${YELLOW}Confirmation skipped by --skip-approval. Cleanup will start immediately.${NC}"
    else
        if [ "$cleanup_all" = true ]; then
            if ! read -r -p "Type 'yes' to permanently remove the Omnia environment and all remaining data: " confirm; then
                echo -e "${RED}ERROR: Confirmation input was not available. No files were removed.${NC}" >&2
                echo -e "${YELLOW}Run interactively, or use --skip-approval only in trusted automation.${NC}" >&2
                return 1
            fi
        elif ! read -r -p "Type 'yes' to remove the Omnia environment while preserving runtime data: " confirm; then
            echo -e "${RED}ERROR: Confirmation input was not available. No files were removed.${NC}" >&2
            echo -e "${YELLOW}Run interactively, or use --skip-approval only in trusted automation.${NC}" >&2
            return 1
        fi
        if [ "$confirm" != "yes" ]; then
            echo -e "${YELLOW}Cleanup cancelled. No files were removed.${NC}"
            return 0
        fi
    fi

    echo ""

    if [ "$cleanup_all" = true ]; then
        echo -e "${BLUE}Removing domain initializer input and log artifacts${NC}"
        cleanup_domain_initializer_artifacts
        # Close the preflight-to-delete race before global cleanup starts.
        validate_full_cleanup_state || return 1
    fi

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

    # Remove omnia-cli from /usr/local/bin
    if [ -f "/usr/local/bin/omnia-cli" ]; then
        echo -e "${BLUE}Removing omnia-cli from /usr/local/bin/omnia-cli${NC}"
        rm -f /usr/local/bin/omnia-cli
        echo -e "  ${GREEN}Removed.${NC}"
    fi

    # Remove Bash completion
    if [ -f "/etc/bash_completion.d/omnia-bash-completion" ]; then
        echo -e "${BLUE}Removing Bash completion from /etc/bash_completion.d/omnia-bash-completion${NC}"
        rm -f /etc/bash_completion.d/omnia-bash-completion
        echo -e "  ${GREEN}Removed.${NC}"
    fi

    # Remove dependency cache (tied to venv, not user data)
    local deps_cache_dir="${OMNIA_DATA_PATH}/.data/deps-cache"
    if [ -d "$deps_cache_dir" ]; then
        echo -e "${BLUE}Removing dependency cache: ${deps_cache_dir}${NC}"
        rm -rf "$deps_cache_dir"
        echo -e "  ${GREEN}Removed.${NC}"
    fi

    # The full-cleanup preflight proved that no deployed domain state existed
    # before deletion began.
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
        echo -e "  ${GREEN}Venv, system env files, and dependency cache removed. Runtime data at ${OMNIA_DATA_PATH}/ preserved.${NC}"
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
    local configured_catalog_file="${CATALOG_FILE_PATH:-$catalog_target_file}"
    local configured_catalog_dir
    configured_catalog_dir="$(dirname "$configured_catalog_file")"

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
    echo -e "${GREEN}Configured catalog file:${NC}"
    echo -e "  ${GREEN}CATALOG_FILE_PATH=${configured_catalog_file}${NC}"
    echo -e "  ${DIM}The default catalog contains packages for both Slurm and service_k8s deployments.${NC}"
    if [ "$configured_catalog_file" != "$catalog_target_file" ]; then
        echo -e "  ${YELLOW}The configured path differs from the copied default (${catalog_target_file}).${NC}"
        echo -e "  ${YELLOW}Copy the catalog you want to ${configured_catalog_file} before running catalog-based workflows.${NC}"
    fi
    echo ""
    echo -e "${YELLOW}To use a different catalog:${NC}"
    echo -e "  ${YELLOW}1. Keep the current path and replace its contents:${NC}"
    echo -e "     mkdir -p \"${configured_catalog_dir}\""
    echo -e "     cp /path/to/catalog.json \"${configured_catalog_file}\""
    echo ""
    echo -e "  ${YELLOW}2. Or keep a separate filename and update the catalog path:${NC}"
    echo -e "     cp /path/to/catalog.json \"${configured_catalog_dir}/custom_catalog.json\""
    echo -e "     vi ${ACTIVE_ENV_FILE:-$SYSTEM_ENV_FILE}"
    echo -e "     Set: CATALOG_FILE_PATH=${configured_catalog_dir}/custom_catalog.json"
    echo -e "     source ${PROFILE_DROP_IN}"
    echo ""
    echo -e "  ${YELLOW}Example (RHEL 10.0, service_k8s only):${NC}"
    printf '     cp "%s" \\\n' "${SCRIPT_DIR}/samples/catalogs/10.0/service_k8s_x86_64.json"
    echo -e "       \"${configured_catalog_dir}/service_k8s_x86_64.json\""
    echo -e "     Set CATALOG_FILE_PATH=${configured_catalog_dir}/service_k8s_x86_64.json in ${ACTIVE_ENV_FILE:-$SYSTEM_ENV_FILE}"
    echo ""
    echo -e "  ${DIM}If you edit ${SCRIPT_DIR}/omnia.env instead of ${ACTIVE_ENV_FILE:-$SYSTEM_ENV_FILE},${NC}"
    echo -e "  ${DIM}apply it with ./omnia.sh -s --force-env (this replaces the installed env file).${NC}"
    echo ""
}


# ─────────────────────────────────────────────────────────────────────────────
# Check Dependency Version Mismatches Across Domains
# Scans all domain requirements.txt and requirements.yml for the same
# package/collection pinned at different versions.  Exits non-zero if
# mismatches are found.
# ─────────────────────────────────────────────────────────────────────────────
check_deps() {
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}               Dependency Version Audit${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""

    local has_mismatch=false

    # ── pip requirements.txt ──
    echo -e "${BLUE}Scanning pip requirements.txt across domains...${NC}"
    declare -A pip_versions  # key = normalized_pkg, value = "domain:spec domain:spec ..."
    for domain in "${DOMAINS[@]}"; do
        local req_txt="$SRC_DIR/$domain/requirements.txt"
        [ -f "$req_txt" ] || continue
        while IFS= read -r line; do
            # Skip comments and blanks
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ "$line" =~ ^[[:space:]]*$ ]] && continue
            # Extract package name and version spec
            local pkg spec
            pkg="$(echo "$line" | sed -E 's/([a-zA-Z0-9_-]+).*/\1/' | tr '[:upper:]' '[:lower:]' | tr '_' '-')"
            spec="$(echo "$line" | sed -E 's/[a-zA-Z0-9_-]+//')"
            pip_versions["$pkg"]+="${domain}:${spec} "
        done < "$req_txt"
    done

    local pip_mismatches=0
    if [ ${#pip_versions[@]} -gt 0 ]; then
        for pkg in $(echo "${!pip_versions[@]}" | tr ' ' '\n' | sort); do
            local entries="${pip_versions[$pkg]}"
            # Extract unique version specs
            local unique_specs
            unique_specs=$(echo "$entries" | tr ' ' '\n' | grep -v '^$' | sed 's/^[^:]*://' | sort -u | wc -l)
            if [ "$unique_specs" -gt 1 ]; then
                echo -e "  ${RED}MISMATCH: ${pkg}${NC}"
                for entry in $entries; do
                    local d="${entry%%:*}"
                    local v="${entry#*:}"
                    echo -e "    ${YELLOW}${d}: ${v}${NC}"
                done
                pip_mismatches=$((pip_mismatches + 1))
                has_mismatch=true
            fi
        done
    fi

    if [ "$pip_mismatches" -eq 0 ]; then
        echo -e "  ${GREEN}No pip version mismatches found.${NC}"
    else
        echo -e "  ${RED}${pip_mismatches} pip package(s) have version mismatches.${NC}"
    fi
    echo ""

    # ── Galaxy requirements.yml ──
    echo -e "${BLUE}Scanning Galaxy requirements.yml across domains...${NC}"
    declare -A galaxy_versions  # key = collection_name, value = "domain:version ..."
    for domain in "${DOMAINS[@]}"; do
        local req_yml="$SRC_DIR/$domain/requirements.yml"
        [ -f "$req_yml" ] || continue
        # Parse YAML manually (name/version pairs)
        local current_name=""
        while IFS= read -r line; do
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            if [[ "$line" =~ name:[[:space:]]*(.+) ]]; then
                current_name="${BASH_REMATCH[1]}"
                current_name="$(echo "$current_name" | tr -d '"' | tr -d "'" | xargs)"
            elif [[ "$line" =~ version:[[:space:]]*(.+) ]] && [ -n "$current_name" ]; then
                local ver="${BASH_REMATCH[1]}"
                ver="$(echo "$ver" | tr -d '"' | tr -d "'" | xargs)"
                galaxy_versions["$current_name"]+="${domain}:${ver} "
                current_name=""
            fi
        done < "$req_yml"
    done

    local galaxy_mismatches=0
    if [ ${#galaxy_versions[@]} -gt 0 ]; then
        for col in $(echo "${!galaxy_versions[@]}" | tr ' ' '\n' | sort); do
            local entries="${galaxy_versions[$col]}"
            local unique_specs
            unique_specs=$(echo "$entries" | tr ' ' '\n' | grep -v '^$' | sed 's/^[^:]*://' | sort -u | wc -l)
            if [ "$unique_specs" -gt 1 ]; then
                echo -e "  ${RED}MISMATCH: ${col}${NC}"
                for entry in $entries; do
                    local d="${entry%%:*}"
                    local v="${entry#*:}"
                    echo -e "    ${YELLOW}${d}: ${v}${NC}"
                done
                galaxy_mismatches=$((galaxy_mismatches + 1))
                has_mismatch=true
            fi
        done
    fi

    if [ "$galaxy_mismatches" -eq 0 ]; then
        echo -e "  ${GREEN}No Galaxy version mismatches found.${NC}"
    else
        echo -e "  ${RED}${galaxy_mismatches} Galaxy collection(s) have version mismatches.${NC}"
    fi
    echo ""

    # ── Summary ──
    local total=$((pip_mismatches + galaxy_mismatches))
    if [ "$has_mismatch" = true ]; then
        echo -e "${RED}================================================================================${NC}"
        echo -e "${RED}  ${total} mismatch(es) found — align versions across domains to avoid conflicts.${NC}"
        echo -e "${RED}================================================================================${NC}"
        return 1
    else
        echo -e "${GREEN}================================================================================${NC}"
        echo -e "${GREEN}  All dependency versions are consistent across domains.${NC}"
        echo -e "${GREEN}================================================================================${NC}"
        return 0
    fi
}


# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
    cat <<EOF
Omnia Infrastructure Manager (OIM) — v${OMNIA_RELEASE}

PREREQUISITE:
  Before the first --setup-venv, edit src/main/omnia.env.
  After the first setup, edit /etc/omnia/omnia.env; setup preserves it.

USAGE:
  $0 <command> [options]

SETUP COMMANDS (run once, in order):
  --setup-venv, -s      Create/update the shared Python venv, then run all
                        domain-init.sh scripts (pip deps, Galaxy collections,
                        log dirs, input file staging) and copy catalog files.
  --init, -i [domain,...]
                        Re-run domain-init.sh scripts only (no venv rebuild).
                        Optionally specify comma-separated domains to init.
                        Default: all domains.  Runs automatically with -s.
                        Examples:
                          ./omnia.sh -i                  # all domains
                          ./omnia.sh -i telemetry        # single domain
                          ./omnia.sh -i repo_manager,telemetry  # specific set

EXECUTION COMMANDS:
  --prepare-base [options]
                        Prepare three base infrastructure domains in dependency order.
                        Runs validation → credentials → prepare. Validation uses
                        precheck for repo_manager and validate for the other domains.
                        Domains: repo_manager, image_build_manager, orchestrator
                        Options:
                          --skip <list>       Comma-separated domains to skip
                          --dry-run           Show what would be prepared
                        Example:
                          ./omnia.sh --prepare-base
                          ./omnia.sh --prepare-base --skip orchestrator
                          ./omnia.sh --prepare-base --dry-run

  --run, -r <domain> [--tags <tags>] [extra ansible args]
                        Activate venv and run the specified domain's playbook.
                        Passes --tags and any extra args to ansible-playbook.

RECOMMENDED EXECUTION ORDER:
  Domains should be run in this order (each reads the previous domain's output):

    Step 1. repo_manager          Mirror packages, images, pip (writes repo_status.yml)
    Step 2. image_build_manager   Build OS images              (reads repo_status.yml, writes build_status.yml)
    Step 3. discovery [optional]  Discover servers             (writes bmc_pxe_mapping_file.csv)
    Step 4. orchestrator          Deploy cluster + K8s/Slurm   (reads build_status.yml + discovery output)
    Step 5. telemetry             Deploy telemetry on K8s      (requires K8s from step 4)
    Step 6. utils     [optional]  Utility playbooks            (run anytime)

  WARNING: Running a later step without completing earlier steps may fail.
           The CLI will warn you if prerequisite outputs are missing.

  Public tags by domain (use --tags <tag> to select a stage):
    build_stream:        precheck validate credentials prepare execute build cleanup upgrade rollback
    discovery:           precheck validate credentials prepare execute discovery cleanup cleanup_credentials upgrade rollback
    image_build_manager: precheck validate credentials prepare execute build cleanup cleanup_images upgrade rollback
    orchestrator:        precheck validate credentials prepare deploy provision execute validate-deployment pxeboot cleanup cleanup_credentials upgrade rollback
    repo_manager:        precheck credentials prepare deploy execute download status cleanup cleanup_pulp cleanup_repos upgrade rollback catalog_generate catalog_add catalog_delete catalog_validate
    telemetry:           precheck validate validation prepare credentials execute deploy cleanup cleanup_kafka cleanup_victoria_metrics cleanup_victoria_logs cleanup_idrac cleanup_ldms cleanup_ome cleanup_powerscale cleanup_ufm cleanup_vast upgrade rollback external_kafka external_victoria
    utils:               precheck setup collect install_os backup_oim_logs cleanup cleanup_logs cleanup_install_os cleanup_backup_oim_logs upgrade rollback

  Without --tags, each playbook runs its full default flow. Tags marked with
  Ansible's "never" tag run only when explicitly selected. Domain playbooks
  validate supported tags and combinations.

DIAGNOSTIC COMMANDS:
  --check-deps          Audit all domain requirements.txt and requirements.yml
                        for version mismatches (e.g. pyyaml>=5.4 vs >=6.0.3).
                        Exits non-zero if any mismatch is found.

CLEANUP COMMANDS:
  --cleanup             Remove venv, system env files (/etc/omnia/omnia.env,
                        /etc/profile.d/omnia-env.sh), omnia-cli, shared Bash
                        completion, activation script, and dependency cache.
                        Runtime data at \$OMNIA_DATA_PATH/ (input, output, logs)
                        is preserved.
  --cleanup --all       Guarded full reset. Refuses to start when a domain has
                        anything except its initializer-owned input directory;
                        run that domain's cleanup (or remove the path manually)
                        first. Then removes domain input/log paths, the venv,
                        system env, cache, and remaining \$OMNIA_DATA_PATH data.

OPTIONS:
  --deps-only           With -s or -i: install pip/Galaxy deps but skip input file staging.
                        Cannot be used standalone; requires -s or -i.
  --force-deps          With -s or -i: bypass the dependency cache and force a
                        fresh pip install + Galaxy collection install.
  --force-env           With -s: replace /etc/omnia/omnia.env with the repository
                        omnia.env. Existing system configuration is preserved by default.
  --skip <domain,...>   With -s or -i: skip specific domains during init.
                        With --prepare-base: skip only repo_manager,
                        image_build_manager, or orchestrator.
                        Cannot be combined with an explicit -i domain list.
                        Examples:
                          ./omnia.sh -i --skip telemetry
                          ./omnia.sh -s --skip telemetry,utils
                          ./omnia.sh -i --skip build_stream --deps-only
  --dry-run             With -s or -i: show which domains would be initialized.
                        With --prepare-base: show which base domains and phases
                        would run. Does not initialize or prepare domains; other
                        setup steps still run when used with -s.
  --skip-catalog        With -s: skip the automatic catalog copy.
  --skip-omnia-cli      With -s: skip installing omnia-cli and shared bash completion
                        to /usr/local/bin/ and /etc/bash_completion.d/.
  --skip-approval       With --cleanup: skip the confirmation prompt. Intended
                        only for trusted, unattended automation.
  --help, -h            Show this help message.

DOMAINS:
  ${DOMAINS[*]}

DEPENDENCY CACHING:
  On first run, each domain's requirements.txt and requirements.yml are hashed
  (MD5).  On subsequent runs, if the file hasn't changed the install step is
  skipped entirely — saving 10-30 seconds per domain.  Use --force-deps to
  bypass the cache.  Cache files are stored at \$OMNIA_DATA_PATH/.data/deps-cache/.

DIAGNOSTICS (see omnia-cli):
  omnia-cli status [--project <name>]         All domain statuses
  omnia-cli repo-manager [--project <name>]   Repo manager details
  omnia-cli image-build [--project <name>]    Image build details
  omnia-cli <domain> [--project <name>]       Any domain status
  omnia-cli version                           Version info
  omnia-cli help [<domain>]                   CLI help

INSTALL omnia-cli TO PATH (automatic during --setup-venv):
  omnia-cli and shared completion for omnia-cli and omnia.sh are installed automatically.
  To skip: omnia.sh -s --skip-omnia-cli
  Manual: sudo cp omnia-cli /usr/local/bin/ && sudo chmod +x /usr/local/bin/omnia-cli

SYSTEM ENVIRONMENT:
  On the first --setup-venv, the repository omnia.env is installed to:
    /etc/omnia/omnia.env           — system-wide env file
    /etc/profile.d/omnia-env.sh    — auto-sourced on login

  On later runs, /etc/omnia/omnia.env is authoritative and is not overwritten.
  Edit that file for normal changes. Use -s --force-env only to replace it
  intentionally from the repository copy.

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
  ./omnia.sh -s                                # Installs env + venv + deps + input files + catalog
  vi /etc/omnia/omnia.env                      # Make environment changes after first setup
  ./omnia.sh -s --force-env                    # Explicitly replace system env from repository
  ./omnia.sh -s --deps-only                    # Installs env + venv + deps (skips input staging)
  ./omnia.sh -s --skip-catalog                 # Setup without catalog copy

  # Init specific domains (re-stage input files or reinstall deps):
  ./omnia.sh -i                                # All domains
  ./omnia.sh -i telemetry                      # Single domain
  ./omnia.sh -i repo_manager,telemetry         # Comma-separated
  ./omnia.sh -i --force-deps                   # Force reinstall even if cached
  ./omnia.sh -i telemetry --deps-only          # Only deps for telemetry

  # Skip specific domains during init:
  ./omnia.sh -i --skip telemetry               # All except telemetry
  ./omnia.sh -i --skip telemetry,utils         # All except telemetry and utils
  ./omnia.sh -s --skip build_stream            # Full setup, skip build_stream init
  ./omnia.sh -i --skip telemetry --deps-only   # Deps only, skip telemetry

  # Dry-run to preview init:
  ./omnia.sh -i --dry-run                      # Preview which domains would be initialized
  ./omnia.sh -i --dry-run --skip telemetry     # Preview with skip filter

  # Check dependency versions across all domains:
  ./omnia.sh --check-deps                      # Lists any pip/Galaxy version mismatches

  # Prepare base infrastructure domains:
  ./omnia.sh --prepare-base                     # Prepare repo_manager, image_build_manager, orchestrator
  ./omnia.sh --prepare-base --skip orchestrator # Skip orchestrator if not needed
  ./omnia.sh --prepare-base --dry-run           # Preview what would be prepared

  # Run a domain playbook:
  ./omnia.sh --run image_build_manager --tags prepare
  ./omnia.sh -r repo_manager                   # Run the default Repo Manager flow
  ./omnia.sh -r telemetry                      # Run the default Telemetry flow

  # Validate domain input:
  ./omnia.sh --run image_build_manager --tags validate
  ./omnia.sh -r repo_manager --tags precheck

  # Cleanup (remove environment + CLI integration, preserve runtime data):
  ./omnia.sh --cleanup

  # Guarded full cleanup (requires domain lifecycle state to be cleaned first):
  ./omnia.sh --cleanup --all

  # Unattended cleanup (no confirmation prompt):
  ./omnia.sh --cleanup --skip-approval
  ./omnia.sh --cleanup --all --skip-approval

  # Diagnostics:
  omnia-cli status               # All domains
  omnia-cli repo-manager         # Repo manager details
EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Dispatch
# ─────────────────────────────────────────────────────────────────────────────
main() {
    DEPS_ONLY=false    # Global — used by init_domains()
    FORCE_DEPS=false   # Global — passed to domain-init.sh
    FORCE_ENV=false    # Global — explicitly replace the installed environment
    SKIP_DOMAINS=""    # Global — comma-separated domains to skip during init
    DRY_RUN=false      # Global — preview mode for init
    local CLEANUP_ALL=false
    local CLEANUP_SKIP_APPROVAL=false
    local SKIP_CATALOG=false
    local SKIP_OMNIA_CLI=false
    local command=""
    local init_domain_filter=""
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
            --prepare-base)
                command="prepare-base"
                shift
                ;;
            --deps-only)
                DEPS_ONLY=true
                shift
                ;;
            --force-deps)
                FORCE_DEPS=true
                shift
                ;;
            --force-env)
                FORCE_ENV=true
                shift
                ;;
            --skip-catalog)
                SKIP_CATALOG=true
                shift
                ;;
            --skip-omnia-cli)
                SKIP_OMNIA_CLI=true
                shift
                ;;
            --skip)
                if [ $# -lt 2 ] || [[ "$2" == --* ]]; then
                    echo -e "${RED}ERROR: --skip requires a comma-separated list of domains${NC}"
                    echo -e "${YELLOW}Usage: $0 -i --skip telemetry,utils${NC}"
                    echo -e "${YELLOW}Domains: ${DOMAINS[*]}${NC}"
                    exit 1
                fi
                SKIP_DOMAINS="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --init|-i)
                command="init"
                shift
                # Next arg may be a domain filter (not starting with --)
                if [ $# -gt 0 ] && [[ "$1" != --* ]]; then
                    init_domain_filter="$1"
                    shift
                fi
                ;;
            --check-deps)
                command="check-deps"
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
            --skip-approval)
                CLEANUP_SKIP_APPROVAL=true
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

    # Setup selects and validates its environment in install_system_env(). Other
    # commands load the already-installed configuration before using defaults.
    if [ "$command" != "setup-venv" ] && [ -f "$SYSTEM_ENV_FILE" ]; then
        source_omnia_env "$SYSTEM_ENV_FILE"
    fi

    # Validate flag combinations
    if [ "$DEPS_ONLY" = true ] && [ "$command" != "setup-venv" ] && [ "$command" != "init" ]; then
        echo -e "${RED}ERROR: --deps-only requires --setup-venv (-s) or --init (-i)${NC}"
        echo -e "${YELLOW}Usage: $0 -s --deps-only or $0 -i --deps-only${NC}"
        exit 1
    fi
    if [ "$FORCE_DEPS" = true ] && [ "$command" != "setup-venv" ] && [ "$command" != "init" ]; then
        echo -e "${RED}ERROR: --force-deps requires --setup-venv (-s) or --init (-i)${NC}"
        echo -e "${YELLOW}Usage: $0 -s --force-deps or $0 -i --force-deps${NC}"
        exit 1
    fi
    if [ "$FORCE_ENV" = true ] && [ "$command" != "setup-venv" ]; then
        echo -e "${RED}ERROR: --force-env requires --setup-venv (-s)${NC}"
        echo -e "${YELLOW}Usage: $0 -s --force-env${NC}"
        exit 1
    fi
    if [ -n "$SKIP_DOMAINS" ] && [ "$command" != "setup-venv" ] && [ "$command" != "init" ] && [ "$command" != "prepare-base" ]; then
        echo -e "${RED}ERROR: --skip requires --setup-venv (-s), --init (-i), or --prepare-base${NC}"
        echo -e "${YELLOW}Usage: $0 -s --skip telemetry or $0 -i --skip telemetry or $0 --prepare-base --skip orchestrator${NC}"
        exit 1
    fi
    if [ -n "$SKIP_DOMAINS" ] && [ -n "$init_domain_filter" ]; then
        echo -e "${RED}ERROR: Cannot use --skip with an explicit domain list${NC}"
        echo -e "${YELLOW}Use either: $0 -i telemetry  OR  $0 -i --skip telemetry${NC}"
        echo -e "${YELLOW}Not both.${NC}"
        exit 1
    fi
    if [ "$DRY_RUN" = true ] && [ "$command" != "init" ] && [ "$command" != "setup-venv" ] && [ "$command" != "prepare-base" ]; then
        echo -e "${RED}ERROR: --dry-run requires --init (-i), --setup-venv (-s), or --prepare-base${NC}"
        echo -e "${YELLOW}Usage: $0 -i --dry-run or $0 --prepare-base --dry-run${NC}"
        exit 1
    fi
    if [ "$CLEANUP_ALL" = true ] && [ "$command" != "cleanup" ]; then
        echo -e "${RED}ERROR: --all is only valid with --cleanup${NC}"
        echo -e "${YELLOW}Usage: $0 --cleanup --all${NC}"
        exit 1
    fi
    if [ "$CLEANUP_SKIP_APPROVAL" = true ] && [ "$command" != "cleanup" ]; then
        echo -e "${RED}ERROR: --skip-approval is only valid with --cleanup${NC}"
        echo -e "${YELLOW}Usage: $0 --cleanup [--all] --skip-approval${NC}"
        exit 1
    fi

    case "$command" in
        setup-venv)
            setup_venv
            init_domains ""

            # Auto-copy catalog unless --skip-catalog
            if [ "$SKIP_CATALOG" = false ]; then
                copy_catalog
            fi

            # Install omnia-cli and shared completion unless --skip-omnia-cli
            if [ "$SKIP_OMNIA_CLI" = false ]; then
                local cli_src="${SCRIPT_DIR}/omnia-cli"
                local completion_src="${SCRIPT_DIR}/omnia-bash-completion"
                local completion_dest="/etc/bash_completion.d/omnia-bash-completion"
                if [ -f "$cli_src" ]; then
                    cp "$cli_src" /usr/local/bin/omnia-cli
                    chmod +x /usr/local/bin/omnia-cli
                    echo -e "${GREEN}Installed omnia-cli to /usr/local/bin/omnia-cli${NC}"
                fi
                if [ -f "$completion_src" ]; then
                    mkdir -p /etc/bash_completion.d
                    cp "$completion_src" "$completion_dest"
                    echo -e "${GREEN}Installed Bash completion for omnia-cli and omnia.sh to ${completion_dest}${NC}"
                fi
            else
                echo -e "${DIM}Skipping omnia-cli install (--skip-omnia-cli)${NC}"
            fi

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
        prepare-base)
            prepare_base_domains
            ;;
        init)
            init_domains "$init_domain_filter"
            ;;
        check-deps)
            check_deps
            ;;
        cleanup)
            cleanup_omnia "$CLEANUP_ALL" "$CLEANUP_SKIP_APPROVAL"
            ;;
        run)
            run_domain "$run_domain_name" "${run_extra_args[@]}"
            ;;
        help)
            show_help
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
