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
# domain-init.sh — Copy repo_manager input files to runtime data path
# =============================================================================
#
# Copies input files from the source tree to the Omnia data directory so that
# Ansible playbooks read from a stable runtime location.
#
# Source:      src/repo_manager/input/<project>/
# Destination: <OMNIA_DATA_PATH>/repo_manager/input/<project>/
#
# Usage:
#   ./domain-init.sh                        # Uses env vars (must be exported)
#   ./domain-init.sh --force                # Overwrite without prompting
#   OMNIA_DATA_PATH=/opt/omnia OMNIA_PROJECT_NAME=prod ./domain-init.sh
#
# Called automatically by: omnia.sh --setup-venv
# =============================================================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DOMAIN_NAME="repo_manager"

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
    local project="$2"

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
    local src_dir="$SCRIPT_DIR/input/${project}"
    local overwrite_list
    overwrite_list=$(cd "$src_dir" && find . -type f | sed 's|^\./||' | sort)
    for f in $overwrite_list; do
        if [ -f "$dest_dir/$f" ]; then
            echo -e "    ${YELLOW}→ $f (exists — will be overwritten)${NC}"
        fi
    done

    # Non-interactive check (piped input, cron, etc.)
    if [ ! -t 0 ]; then
        echo -e "  ${RED}[${DOMAIN_NAME}] Non-interactive mode — skipping overwrite. Use --force to override.${NC}"
        return 1
    fi

    echo -en "  ${YELLOW}Overwrite existing files for project '${project}'? [y/N]: ${NC}"
    read -r response
    case "$response" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *)
            echo -e "  ${YELLOW}[${DOMAIN_NAME}] Skipped project '${project}' — no files overwritten${NC}"
            return 1
            ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Copy input files for a single project
# ─────────────────────────────────────────────────────────────────────────────
copy_project_input() {
    local project="$1"
    local src_dir="$SCRIPT_DIR/input/${project}"
    local dest_dir="${OMNIA_DATA_PATH}/${DOMAIN_NAME}/input/${project}"

    if [ ! -d "$src_dir" ]; then
        echo -e "  ${YELLOW}[${DOMAIN_NAME}] No input directory for project '${project}' at ${src_dir} — skipping${NC}"
        return 0
    fi

    # Check for existing files and prompt if needed
    if ! _check_existing_files "$dest_dir" "$project"; then
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
    echo -e "  ${GREEN}[${DOMAIN_NAME}] Copied ${count} file(s) for project '${project}' → ${dest_dir}${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
main() {
    _parse_args "$@"
    _load_env

    # Copy the configured project
    copy_project_input "$OMNIA_PROJECT_NAME"

    # Also copy any other project directories that exist in input/
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
