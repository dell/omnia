#!/usr/bin/env bash
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
# telemetry — One-Time Environment Setup
# =============================================================================
# Creates a Python venv, installs dependencies, and sets up tab-completion.
#
# Usage:
#   source setup_env.sh     # Create venv + install deps + activate
#   source setup_env.sh -f  # Force recreate venv
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
FORCE=false

for arg in "$@"; do
    case "$arg" in
        -f|--force) FORCE=true ;;
    esac
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Create venv
if [ "$FORCE" = true ] && [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Removing existing venv...${NC}"
    rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}Creating Python venv at ${VENV_DIR}...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Activate
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# Install deps
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -r "${SCRIPT_DIR}/requirements.txt" -q

# Tab-completion for run_validation.sh
_run_validation_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    case "$COMP_CWORD" in
        1)
            COMPREPLY=( $(compgen -W "precheck validate deploy cleanup telemetry nft all list --config help" -- "$cur") )
            ;;
        2)
            COMPREPLY=( $(compgen -W "deploy verify test" -- "$cur") )
            ;;
        *)
            case "$prev" in
                --suite)
                    local suites=""
                    local scenario="${COMP_WORDS[1]}"
                    local fvt_dir="${SCRIPT_DIR}/fvt/${scenario}"
                    if [ -d "$fvt_dir" ]; then
                        suites=$(find "$fvt_dir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null || true)
                    fi
                    COMPREPLY=( $(compgen -W "$suites" -- "$cur") )
                    ;;
                --marker)
                    COMPREPLY=( $(compgen -W "sanity functional deploy sink source nft" -- "$cur") )
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "--suite --marker -v --verbose" -- "$cur") )
                    ;;
            esac
            ;;
    esac
}

complete -F _run_validation_completions ./run_validation.sh

echo -e "${GREEN}Environment ready. Tab-completion enabled.${NC}"
echo -e "${GREEN}Run: ./run_validation.sh <scenario> <command>${NC}"
