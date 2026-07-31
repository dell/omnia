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
# copy-input.sh — Copy orchestrator input files to runtime data path
# =============================================================================
#
# Copies:
#   1. input/ config templates → <OMNIA_DATA_PATH>/orchestrator/input/<project>/
#
# Usage:
#   ./copy-input.sh
#   ./copy-input.sh --force
#   OMNIA_DATA_PATH=/opt/omnia OMNIA_PROJECT_NAME=prod ./copy-input.sh
#
# Called automatically by: omnia.sh --setup-venv
# =============================================================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DOMAIN_NAME="orchestrator"

# --- Resolve environment variables ---
OMNIA_DATA_PATH="${OMNIA_DATA_PATH:-/opt/omnia}"
OMNIA_PROJECT_NAME="${OMNIA_PROJECT_NAME:-project_default}"
FORCE="${1:-}"

readonly INPUT_SRC="${SCRIPT_DIR}/input"
readonly INPUT_DST="${OMNIA_DATA_PATH}/input/${OMNIA_PROJECT_NAME}"
readonly LOG_DIR="/var/log/omnia/${DOMAIN_NAME}"

# --- Functions ---
log() { echo "[${DOMAIN_NAME}] $*"; }

ensure_dir() {
    if [[ ! -d "$1" ]]; then
        mkdir -p "$1"
        log "Created directory: $1"
    fi
}

copy_if_missing() {
    local src="$1" dst="$2"
    if [[ ! -f "$dst" ]] || [[ "$FORCE" == "--force" ]]; then
        cp "$src" "$dst"
        log "Copied: $(basename "$src") → $dst"
    else
        log "Skipped (exists): $(basename "$dst")"
    fi
}

# --- Main ---
log "Setting up ${DOMAIN_NAME} domain..."

# Create required directories
ensure_dir "$INPUT_DST"
ensure_dir "$LOG_DIR"
ensure_dir "${OMNIA_DATA_PATH}/.data"

# Copy input templates (only if not already present)
if [[ -d "$INPUT_SRC" ]]; then
    for f in "$INPUT_SRC"/*; do
        [[ -f "$f" ]] && copy_if_missing "$f" "${INPUT_DST}/$(basename "$f")"
    done
else
    log "No input/ directory found — skipping input copy"
fi

log "Domain setup complete."
