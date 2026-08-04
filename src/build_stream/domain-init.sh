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
# domain-init.sh — Initialize build_stream domain runtime environment
# =============================================================================
#
# Performs first-time domain setup:
#   1. Creates Ansible log directory:  /var/log/omnia/build_stream/
#   2. Copies app/ source code to NFS runtime data path
#   3. Copies input files from source tree to runtime data path
#
# Source:      src/build_stream/app/   -> <OMNIA_DATA_PATH>/build_stream/
#              src/build_stream/input/ -> <OMNIA_DATA_PATH>/build_stream/input/<project>/
#
# The container mounts <OMNIA_DATA_PATH> at /opt/omnia and reads code from NFS.
# This eliminates the need to bake app code into the container image.
#
# Usage:
#   ./domain-init.sh                        # Uses env vars (must be exported)
#   ./domain-init.sh --force                # Overwrite without prompting
#   OMNIA_DATA_PATH=/opt/omnia OMNIA_PROJECT_NAME=build_stream ./domain-init.sh
#
# Called automatically by: omnia.sh --setup-venv
#
# Manual alternative (if not using this script):
#   sudo mkdir -p /var/log/omnia/build_stream
#   chmod 755 /var/log/omnia/build_stream
#   cp -a app/ <OMNIA_DATA_PATH>/build_stream/
#   cp -a input/build_stream/ <OMNIA_DATA_PATH>/build_stream/input/build_stream/
# =============================================================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DOMAIN_NAME="build_stream"

# Color definitions
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

FORCE_OVERWRITE=false

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
_parse_args() {
    for arg in "$@"; do
        case "$arg" in
            --force|-f) FORCE_OVERWRITE=true ;;
            --help|-h)
                echo "Usage: $0 [--force|-f]"
                echo "  --force, -f   Overwrite existing files without prompting"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown argument: $arg${NC}" >&2
                echo "Usage: $0 [--force|-f]" >&2
                exit 1
                ;;
        esac
    done
}

# ---------------------------------------------------------------------------
# Read env vars (must be exported before running)
# ---------------------------------------------------------------------------
_load_env() {
    OMNIA_DATA_PATH="${OMNIA_DATA_PATH:-/opt/omnia}"
    OMNIA_PROJECT_NAME="${OMNIA_PROJECT_NAME:-build_stream}"
}

# ---------------------------------------------------------------------------
# Check if destination has existing files and prompt user
# Returns 0 if safe to proceed, 1 if user declined
# ---------------------------------------------------------------------------
_check_existing_files() {
    local dest_dir="$1"
    local label="$2"

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

    # Non-interactive check (piped input, cron, etc.)
    if [ ! -t 0 ]; then
        echo -e "  ${RED}[${DOMAIN_NAME}] Non-interactive mode — skipping overwrite. Use --force to override.${NC}"
        return 1
    fi

    echo -en "  ${YELLOW}Overwrite existing ${label} files? [y/N]: ${NC}"
    read -r response
    case "$response" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *)
            echo -e "  ${YELLOW}[${DOMAIN_NAME}] Skipped ${label} — no files overwritten${NC}"
            return 1
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Create Ansible log directory under /var/log/omnia/
# ansible.cfg log_path points here — Ansible cannot create parent dirs.
# All ansible.cfg log files are flat (no subfolders).
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Copy app source code to NFS runtime path
# ---------------------------------------------------------------------------
copy_app_source() {
    local src_dir="$SCRIPT_DIR/app"
    local dest_dir="${OMNIA_DATA_PATH}/${DOMAIN_NAME}"

    if [ ! -d "$src_dir" ]; then
        echo -e "  ${RED}[${DOMAIN_NAME}] App source directory not found at ${src_dir}${NC}" >&2
        return 1
    fi

    if ! _check_existing_files "$dest_dir" "app source"; then
        return 0
    fi

    mkdir -p "$dest_dir"

    # Use rsync if available (preserves permissions, only copies changed files)
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --update "$src_dir/" "$dest_dir/"
    else
        cp -a "$src_dir/." "$dest_dir/"
    fi

    local count
    count=$(find "$dest_dir" -type f | wc -l)
    echo -e "  ${GREEN}[${DOMAIN_NAME}] Copied app source (${count} files) -> ${dest_dir}${NC}"
}

# ---------------------------------------------------------------------------
# Copy input files for a single project
# ---------------------------------------------------------------------------
copy_project_input() {
    local project="$1"
    local src_dir="$SCRIPT_DIR/input/${project}"
    local dest_dir="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/input/${project}"

    if [ ! -d "$src_dir" ]; then
        echo -e "  ${YELLOW}[${DOMAIN_NAME}] No input directory for project '${project}' at ${src_dir} — skipping${NC}"
        return 0
    fi

    if ! _check_existing_files "$dest_dir" "input/${project}"; then
        return 0
    fi

    mkdir -p "$dest_dir"

    if command -v rsync >/dev/null 2>&1; then
        rsync -a --update "$src_dir/" "$dest_dir/"
    else
        cp -a "$src_dir/." "$dest_dir/"
    fi

    local count
    count=$(find "$dest_dir" -type f | wc -l)
    echo -e "  ${GREEN}[${DOMAIN_NAME}] Copied ${count} input file(s) for project '${project}' -> ${dest_dir}${NC}"
}

# ---------------------------------------------------------------------------
# Copy top-level input config files (not in a project subdirectory)
# ---------------------------------------------------------------------------
copy_top_level_config() {
    local src_dir="$SCRIPT_DIR/input"
    local dest_dir="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/input"

    mkdir -p "$dest_dir"

    # Copy top-level .yml files from input/ (not subdirectories)
    local copied=0
    for src_file in "$src_dir"/*.yml; do
        [ -f "$src_file" ] || continue
        local basename
        basename=$(basename "$src_file")
        cp -a "$src_file" "$dest_dir/$basename"
        copied=$((copied + 1))
    done

    if [ "$copied" -gt 0 ]; then
        echo -e "  ${GREEN}[${DOMAIN_NAME}] Copied ${copied} top-level config file(s) -> ${dest_dir}${NC}"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    _parse_args "$@"
    _load_env

    echo -e "${GREEN}[${DOMAIN_NAME}] Initializing domain...${NC}"

    # 1. Create Ansible log directory (ansible.cfg log_path)
    create_log_directory

    # 2. Copy app source code to NFS
    copy_app_source

    # 3. Copy top-level input config files
    copy_top_level_config

    # 4. Copy input files for the configured project
    copy_project_input "$OMNIA_PROJECT_NAME"

    # 5. Copy any other project directories that exist in input/
    for project_dir in "$SCRIPT_DIR/input"/*/; do
        [ -d "$project_dir" ] || continue
        local project
        project=$(basename "$project_dir")
        if [ "$project" != "$OMNIA_PROJECT_NAME" ]; then
            copy_project_input "$project"
        fi
    done
}

main "$@"
