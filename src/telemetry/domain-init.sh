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
# domain-init.sh — Initialize telemetry domain runtime environment
# =============================================================================
#
# Performs first-time domain setup:
#   1. Installs Python pip packages from requirements.txt
#   2. Installs Ansible Galaxy collections from requirements.yml
#   3. Creates Ansible log directory:  /var/log/omnia/telemetry/
#   4. Copies input files from source tree to runtime data path:
#      - <OMNIA_DATA_PATH>/telemetry/input/<project>/
#   5. Creates output directories:
#      - <OMNIA_DATA_PATH>/telemetry/output/<project>/
#
# Source (flat):   src/telemetry/input/
# Destination:     <OMNIA_DATA_PATH>/telemetry/input/<project>/
#
# The source input/ directory contains template config files without any
# project subdirectory.  The project directory (e.g. project_default) is
# created ONLY at the runtime destination on the NFS share.
#
# Usage:
#   ./domain-init.sh                        # Uses env vars (must be exported)
#   ./domain-init.sh --force                # Overwrite without prompting
#   OMNIA_DATA_PATH=/opt/omnia OMNIA_PROJECT_NAME=prod ./domain-init.sh
#
# Called automatically by: omnia.sh --setup-venv
#
# Manual alternative (if not using this script):
#   sudo mkdir -p /var/log/omnia/telemetry
#   chmod 755 /var/log/omnia/telemetry
#   mkdir -p /opt/omnia/telemetry/input/project_default
#   cp -a input/*.yml /opt/omnia/telemetry/input/project_default/
# =============================================================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DOMAIN_NAME="telemetry"

# Color definitions
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

FORCE_OVERWRITE=false
DEPS_ONLY=false
FORCE_DEPS=false

# -----------------------------------------------------------------------------
# Parse arguments
# -----------------------------------------------------------------------------
_parse_args() {
    for arg in "$@"; do
        case "$arg" in
            --force|-f) FORCE_OVERWRITE=true ;;
            --deps-only) DEPS_ONLY=true ;;
            --force-deps) FORCE_DEPS=true ;;
            --help|-h)
                echo "Usage: $0 [--force|-f] [--deps-only] [--force-deps]"
                echo "  --force, -f     Overwrite existing files without prompting"
                echo "  --deps-only     Skip input file staging (only install deps)"
                echo "  --force-deps    Bypass dep cache and force reinstall of pip/Galaxy deps"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown argument: $arg${NC}" >&2
                echo "Usage: $0 [--force|-f] [--deps-only] [--force-deps]" >&2
                exit 1
                ;;
        esac
    done
}

# -----------------------------------------------------------------------------
# Read env vars (must be exported before running)
# -----------------------------------------------------------------------------
_load_env() {
    OMNIA_DATA_PATH="${OMNIA_DATA_PATH:-/opt/omnia}"
    OMNIA_PROJECT_NAME="${OMNIA_PROJECT_NAME:-project_default}"
}

# -----------------------------------------------------------------------------
# Check if destination has existing files and prompt user
# Returns 0 if safe to proceed, 1 if user declined
# -----------------------------------------------------------------------------
_check_existing_files() {
    local dest_dir="$1"

    # No destination — safe to proceed
    [ -d "$dest_dir" ] || return 0

    local existing_count
    existing_count=$(find "$dest_dir" -type f 2>/dev/null | wc -l)
    [ "$existing_count" -gt 0 ] || return 0

    # Files exist — check if force mode
    if [ "$FORCE_OVERWRITE" = true ]; then
        echo -e "  ${YELLOW}[${DOMAIN_NAME}] Overwriting ${existing_count} existing file(s) in ${dest_dir} (--force)${NC}"
        return 0
    fi

    # Interactive prompt
    echo -e "  ${YELLOW}[${DOMAIN_NAME}] WARNING: ${existing_count} file(s) already exist in ${dest_dir}${NC}"
    echo -e "  ${YELLOW}Existing files may contain user customizations that will be overwritten.${NC}"

    # List files that would be overwritten
    local src_dir="$SCRIPT_DIR/input"
    local overwrite_list
    overwrite_list=$(cd "$src_dir" && find . -type f | sed 's|^\./||' | sort)
    for f in $overwrite_list; do
        if [ -f "$dest_dir/$f" ]; then
            echo -e "    ${YELLOW}-> $f (exists — will be overwritten)${NC}"
        fi
    done

    # Non-interactive check (piped input, cron, etc.)
    if [ ! -t 0 ]; then
        echo -e "  ${RED}[${DOMAIN_NAME}] Non-interactive mode — skipping overwrite. Use --force to override.${NC}"
        return 1
    fi

    echo -en "  ${YELLOW}Overwrite existing files for project '${OMNIA_PROJECT_NAME}'? [y/N]: ${NC}"
    read -r response
    case "$response" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *)
            echo -e "  ${YELLOW}[${DOMAIN_NAME}] Skipped project '${OMNIA_PROJECT_NAME}' — no files overwritten${NC}"
            return 1
            ;;
    esac
}

# -----------------------------------------------------------------------------
# Copy flat input/ files to the runtime project directory
# Source:  src/<domain>/input/            (flat — no project subdirectory)
# Dest:   <OMNIA_DATA_PATH>/<domain>/input/<project>/
# -----------------------------------------------------------------------------
copy_input_files() {
    local src_dir="$SCRIPT_DIR/input"
    local dest_dir="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/input/${OMNIA_PROJECT_NAME}"

    if [ ! -d "$src_dir" ]; then
        echo -e "  ${YELLOW}[${DOMAIN_NAME}] No input directory at ${src_dir} — skipping${NC}"
        return 0
    fi

    # Check that source has files (ignore subdirectories)
    local src_count
    src_count=$(find "$src_dir" -maxdepth 1 -type f 2>/dev/null | wc -l)
    if [ "$src_count" -eq 0 ]; then
        echo -e "  ${YELLOW}[${DOMAIN_NAME}] No input files in ${src_dir} — skipping${NC}"
        return 0
    fi

    # Check for existing files and prompt if needed
    if ! _check_existing_files "$dest_dir"; then
        return 0
    fi

    mkdir -p "$dest_dir"

    # Use rsync if available (preserves permissions, only copies changed files)
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --update "$src_dir/" "$dest_dir/" --exclude='.*'
    else
        cp -a "$src_dir"/. "$dest_dir/"
    fi

    local count
    count=$(find "$dest_dir" -type f | wc -l)
    echo -e "  ${GREEN}[${DOMAIN_NAME}] Copied ${count} file(s) → ${dest_dir}${NC}"
}

# -----------------------------------------------------------------------------
# Create Ansible log directory under /var/log/omnia/
# ansible.cfg log_path points here — Ansible cannot create parent dirs.
# All ansible.cfg log files are flat (no subfolders).
# -----------------------------------------------------------------------------
create_log_directory() {
    local log_dir="/var/log/omnia/${DOMAIN_NAME}"
    if [ ! -d "$log_dir" ]; then
        mkdir -p "$log_dir"
        chmod 755 "$log_dir"
        echo -e "  ${GREEN}[${DOMAIN_NAME}] Created Ansible log directory: ${log_dir}${NC}"
    else
        echo -e "  ${GREEN}[${DOMAIN_NAME}] Ansible log directory exists: ${log_dir}${NC}"
    fi
}

# -----------------------------------------------------------------------------
# Install domain-specific pip + Galaxy dependencies
# Expects the shared Omnia venv to be activated before calling this script.
# -----------------------------------------------------------------------------
_checksum_file() {
    if command -v md5sum >/dev/null 2>&1; then
        md5sum "$1" | awk '{print $1}'
    elif command -v md5 >/dev/null 2>&1; then
        md5 -q "$1"
    else
        echo "no-md5"
    fi
}

_deps_cache_dir() {
    local cache_dir="${OMNIA_DATA_PATH}/.data/deps-cache"
    mkdir -p "$cache_dir"
    echo "$cache_dir"
}

install_dependencies() {
    local req_txt="$SCRIPT_DIR/requirements.txt"
    local req_yml="$SCRIPT_DIR/requirements.yml"
    local cache_dir
    cache_dir="$(_deps_cache_dir)"

    if [ -f "$req_txt" ]; then
        if command -v pip >/dev/null 2>&1; then
            local pip_hash pip_cache_file
            pip_hash="$(_checksum_file "$req_txt")"
            pip_cache_file="${cache_dir}/${DOMAIN_NAME}.pip.md5"

            if [ "$FORCE_DEPS" = false ] && [ -f "$pip_cache_file" ] && [ "$(cat "$pip_cache_file")" = "$pip_hash" ]; then
                echo -e "  ${GREEN}[${DOMAIN_NAME}] pip deps unchanged (cached) — skipped${NC}"
            else
                echo -e "  ${GREEN}[${DOMAIN_NAME}] Installing pip packages ...${NC}"
                if pip install -r "$req_txt" --quiet; then
                    echo "$pip_hash" > "$pip_cache_file"
                else
                    echo -e "  ${YELLOW}[${DOMAIN_NAME}] WARNING: pip install failed — continuing${NC}"
                fi
            fi
        else
            echo -e "  ${YELLOW}[${DOMAIN_NAME}] pip not found (venv not activated?) — skipping pip install${NC}"
        fi
    fi

    if [ -f "$req_yml" ]; then
        if command -v ansible-galaxy >/dev/null 2>&1; then
            local galaxy_hash galaxy_cache_file
            galaxy_hash="$(_checksum_file "$req_yml")"
            galaxy_cache_file="${cache_dir}/${DOMAIN_NAME}.galaxy.md5"

            if [ "$FORCE_DEPS" = false ] && [ -f "$galaxy_cache_file" ] && [ "$(cat "$galaxy_cache_file")" = "$galaxy_hash" ]; then
                echo -e "  ${GREEN}[${DOMAIN_NAME}] Galaxy deps unchanged (cached) — skipped${NC}"
            else
                echo -e "  ${GREEN}[${DOMAIN_NAME}] Installing Galaxy collections ...${NC}"
                if ansible-galaxy collection install -r "$req_yml" --force 2>&1 | tail -1; then
                    echo "$galaxy_hash" > "$galaxy_cache_file"
                else
                    echo -e "  ${YELLOW}[${DOMAIN_NAME}] WARNING: Galaxy install failed — continuing${NC}"
                fi
            fi
        else
            echo -e "  ${YELLOW}[${DOMAIN_NAME}] ansible-galaxy not found — skipping Galaxy install${NC}"
        fi
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    _parse_args "$@"
    _load_env

    echo -e "${GREEN}[${DOMAIN_NAME}] Initializing domain...${NC}"

    # 1. Install domain-specific dependencies
    install_dependencies

    # 2. Create log directory
    create_log_directory

    # 3. Copy flat input files to the runtime project directory (skip if --deps-only)
    if [ "$DEPS_ONLY" = false ]; then
        copy_input_files
    else
        echo -e "  ${YELLOW}[${DOMAIN_NAME}] Skipping input file staging (--deps-only)${NC}"
    fi

    # 4. Create output directory
    local output_dir="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/output/${OMNIA_PROJECT_NAME}"
    mkdir -p "$output_dir"
    echo -e "  ${GREEN}[${DOMAIN_NAME}] Output directory ready: ${output_dir}${NC}"

    echo -e "${GREEN}[${DOMAIN_NAME}] Domain initialization complete.${NC}"
}

main "$@"
