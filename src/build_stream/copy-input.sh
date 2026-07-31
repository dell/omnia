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
# copy-input.sh — Copy build_stream source and input files to runtime data path
# =============================================================================
#
# Copies:
#   1. app/ source code  → <OMNIA_DATA_PATH>/build_stream/
#   2. input/ config     → <OMNIA_DATA_PATH>/build_stream/input/<project>/
#
# This eliminates the need to bake app code into the container image.
# The container mounts <OMNIA_DATA_PATH> at /opt/omnia and reads code from NFS.
#
# Usage:
#   ./copy-input.sh                        # Uses env vars (must be exported)
#   ./copy-input.sh --force                # Overwrite without prompting
#   OMNIA_DATA_PATH=/opt/omnia OMNIA_PROJECT_NAME=prod ./copy-input.sh
#
# Called automatically by: omnia.sh --setup-venv
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

# ─────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# Read env vars (must be exported before running)
# ─────────────────────────────────────────────────────────────────────────────
_load_env() {
    OMNIA_DATA_PATH="${OMNIA_DATA_PATH:-/opt/omnia}"
    OMNIA_PROJECT_NAME="${OMNIA_PROJECT_NAME:-project_default}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Check if destination has existing files and prompt user
# Returns 0 if safe to proceed, 1 if user declined
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# Copy app source code to NFS runtime path
# ─────────────────────────────────────────────────────────────────────────────
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
    echo -e "  ${GREEN}[${DOMAIN_NAME}] Copied app source (${count} files) → ${dest_dir}${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Copy input files for a single project
# ─────────────────────────────────────────────────────────────────────────────
copy_project_input() {
    local project="$1"
    local src_dir="$SCRIPT_DIR/input"
    local dest_dir="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/input/${project}"

    if [ ! -d "$src_dir" ]; then
        echo -e "  ${YELLOW}[${DOMAIN_NAME}] No input directory at ${src_dir} — skipping${NC}"
        return 0
    fi

    if ! _check_existing_files "$dest_dir" "input/${project}"; then
        return 0
    fi

    mkdir -p "$dest_dir"

    # Copy top-level input files (e.g., build_stream_config.yml)
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --update "$src_dir/" "$dest_dir/" --exclude='*/'
    else
        find "$src_dir" -maxdepth 1 -type f -exec cp -a {} "$dest_dir/" \;
    fi

    local count
    count=$(find "$dest_dir" -type f | wc -l)
    echo -e "  ${GREEN}[${DOMAIN_NAME}] Copied ${count} input file(s) for project '${project}' → ${dest_dir}${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Copy top-level input config (default.yml)
# ─────────────────────────────────────────────────────────────────────────────
copy_top_level_config() {
    local src_file="$SCRIPT_DIR/input/default.yml"
    local dest_dir="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/input"
    local dest_file="$dest_dir/default.yml"

    if [ ! -f "$src_file" ]; then
        echo -e "  ${YELLOW}[${DOMAIN_NAME}] No default.yml found — skipping${NC}"
        return 0
    fi

    mkdir -p "$dest_dir"
    cp -a "$src_file" "$dest_file"
    echo -e "  ${GREEN}[${DOMAIN_NAME}] Copied default.yml → ${dest_file}${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
main() {
    _parse_args "$@"
    _load_env

    echo -e "  ${GREEN}[${DOMAIN_NAME}] Deploying to ${OMNIA_DATA_PATH}/${DOMAIN_NAME}${NC}"

    # 1. Copy app source code to NFS
    copy_app_source

    # 2. Copy top-level input config (default.yml)
    copy_top_level_config

    # 3. Copy input files for the configured project
    copy_project_input "$OMNIA_PROJECT_NAME"
}

main "$@"
