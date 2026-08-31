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
# Orchestrator — One-Time Environment Setup
# =============================================================================
# Creates a Python venv, installs dependencies, and sets up tab-completion.
#
# Usage:
#   source setup_env.sh     # Create venv + install deps + activate
#   source setup_env.sh -f  # Force recreate venv
# =============================================================================

set -uo pipefail

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
# Usage: ./run_validation.sh orchestrator [tag] <command> [options]
_run_validation_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"
    local domain="orchestrator"
    local tags="validate prepare provision cleanup"
    local commands="exec verify test list help"
    local options="--suite --marker -v --verbose --debug --config"
    local markers="sanity functional regression deploy"

    case "$COMP_CWORD" in
        1)
            # First arg is always the domain name
            COMPREPLY=( $(compgen -W "${domain} --config help --completion" -- "$cur") )
            ;;
        2)
            # After domain: tag or command
            COMPREPLY=( $(compgen -W "${tags} ${commands}" -- "$cur") )
            ;;
        3)
            # After tag: command; after command: options
            if echo " ${tags} " | grep -q " ${prev} "; then
                COMPREPLY=( $(compgen -W "${commands}" -- "$cur") )
            else
                COMPREPLY=( $(compgen -W "${options}" -- "$cur") )
            fi
            ;;
        *)
            case "$prev" in
                --suite)
                    local suites=""
                    local tag_dir=""
                    for w in "${COMP_WORDS[@]}"; do
                        if echo " ${tags} " | grep -q " ${w} "; then
                            tag_dir="${SCRIPT_DIR}/fvt/${w}"
                            break
                        fi
                    done
                    if [ -n "${tag_dir}" ] && [ -d "${tag_dir}" ]; then
                        suites=$(find "${tag_dir}" -mindepth 1 -maxdepth 1 -type d -not -name '__pycache__' -printf '%f\n' 2>/dev/null || true)
                    fi
                    COMPREPLY=( $(compgen -W "${suites}" -- "$cur") )
                    ;;
                --marker)
                    COMPREPLY=( $(compgen -W "${markers}" -- "$cur") )
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "${options}" -- "$cur") )
                    ;;
            esac
            ;;
    esac
}

complete -F _run_validation_completions ./run_validation.sh

echo -e "${GREEN}Environment ready. Tab-completion enabled.${NC}"
echo -e "${GREEN}Run: ./run_validation.sh orchestrator [tag] <command>${NC}"
