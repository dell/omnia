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
# Repo Manager — Test Environment Setup
# =============================================================================
# One-time setup script. Creates a Python virtual environment and installs
# all dependencies from requirements.txt.
#
# Usage:
#   bash setup_env.sh            # Normal setup
#   bash setup_env.sh --force    # Delete .venv and recreate from scratch
#   bash setup_env.sh --debug    # Verbose pip output (show install details)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"

FORCE=false
DEBUG=false
PIP_QUIET="--quiet"

for arg in "$@"; do
    case "$arg" in
        --force) FORCE=true ;;
        --debug) DEBUG=true; PIP_QUIET="" ;;
        *)
            echo "Usage: bash setup_env.sh [--force] [--debug]"
            echo "  --force   Delete existing .venv and recreate"
            echo "  --debug   Show verbose pip install output"
            exit 1
            ;;
    esac
done

echo ""
echo "================================================================="
echo "  Repo Manager — Test Environment Setup"
echo "================================================================="
echo ""

# -----------------------------------------------
# Step 1: Check Python 3.12+
# -----------------------------------------------
PYTHON_CMD=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 12 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "  [ERROR] Python 3.12+ is required but not found."
    echo "          Install: dnf install python3.12 python3.12-pip"
    exit 1
fi

echo "  [OK] Python: $($PYTHON_CMD --version)"

# -----------------------------------------------
# Step 2: Create virtual environment
# -----------------------------------------------
if [ "$FORCE" = true ] && [ -d "$VENV_DIR" ]; then
    echo "  [...] Removing existing virtual environment (--force)"
    rm -rf "$VENV_DIR"
fi

if [ -d "$VENV_DIR" ]; then
    echo "  [OK] Virtual environment already exists: .venv/"
else
    echo "  [...] Creating virtual environment: .venv/"
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo "  [OK] Virtual environment created"
fi

# -----------------------------------------------
# Step 3: Activate and install dependencies
# -----------------------------------------------
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "  [...] Upgrading pip"
pip install --upgrade pip $PIP_QUIET

echo "  [...] Installing dependencies from requirements.txt"
pip install -r "$REQUIREMENTS" $PIP_QUIET

# pytest-order for test ordering
if ! pip show pytest-order &>/dev/null; then
    echo "  [...] Installing pytest-order"
    pip install pytest-order $PIP_QUIET
fi

echo "  [OK] All dependencies installed"

# =============================================================================
# REGISTER run_validation FUNCTION AND TAB COMPLETION IN .venv/bin/activate
# =============================================================================
# Inject into .venv/bin/activate so that `source .venv/bin/activate` gives:
#   - run_validation command (no ./ needed)
#   - Tab completion for run_validation (scenarios + commands + options)

ACTIVATE_SCRIPT="${VENV_DIR}/bin/activate"
MARKER="# >>> repo-manager-test >>>"
MARKER_END="# <<< repo-manager-test <<<"

# Remove any previous block (idempotent)
if grep -q "${MARKER}" "${ACTIVATE_SCRIPT}" 2>/dev/null; then
    sed -i "/${MARKER}/,/${MARKER_END}/d" "${ACTIVATE_SCRIPT}"
fi

cat >> "${ACTIVATE_SCRIPT}" << 'RM_ACTIVATE_EOF'

# >>> repo-manager-test >>>
# Added by setup_env.sh — shell function and tab-completion

# Shell function so run_validation works without ./
run_validation() {
    "${VIRTUAL_ENV%/.venv}/run_validation.sh" "$@"
}

# Tab-completion for run_validation
_run_validation_completions() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    local fvt_dir="${VIRTUAL_ENV%/.venv}/fvt"
    local scenarios=""
    if [ -d "${fvt_dir}" ]; then
        for d in "${fvt_dir}"/*/; do
            [ -d "$d" ] || continue
            local name
            name="$(basename "$d")"
            [ "$name" = "__pycache__" ] && continue
            scenarios="${scenarios} ${name}"
        done
    fi
    local commands="deploy verify test"
    local special="all list help --config --help"
    local options="--suite --marker -v --verbose --debug"
    local markers="sanity x86_64 aarch64 functional regression deploy"
    case "$COMP_CWORD" in
        1) COMPREPLY=( $(compgen -W "${scenarios} ${special}" -- "$cur") ) ;;
        2)
            case "$prev" in
                list|help|--help|-h|--config) COMPREPLY=() ;;
                *) COMPREPLY=( $(compgen -W "${commands}" -- "$cur") ) ;;
            esac ;;
        *)
            case "$prev" in
                --suite)
                    local scenario="${COMP_WORDS[1]}"
                    local suites=""
                    if [ -d "${fvt_dir}/${scenario}" ]; then
                        for d in "${fvt_dir}/${scenario}"/*/; do
                            [ -d "$d" ] || continue
                            local name
                            name="$(basename "$d")"
                            [ "$name" = "__pycache__" ] && continue
                            suites="${suites} ${name}"
                        done
                    fi
                    COMPREPLY=( $(compgen -W "${suites}" -- "$cur") ) ;;
                --marker) COMPREPLY=( $(compgen -W "${markers}" -- "$cur") ) ;;
                *) COMPREPLY=( $(compgen -W "${options}" -- "$cur") ) ;;
            esac ;;
    esac
}
complete -F _run_validation_completions run_validation

# <<< repo-manager-test <<<
RM_ACTIVATE_EOF

echo "  [OK] Registered run_validation and tab-completion in venv activate"

echo ""
echo "================================================================="
echo "  Environment Ready"
echo "================================================================="
echo ""
echo "  Next steps:"
echo "    source .venv/bin/activate"
echo "    vi test_config.yml                  # See docs/test_config.md"
echo "    run_validation --help               # Full usage (no ./ needed)"
echo "    run_validation repo_manager verify --marker sanity"
echo ""
echo "  Documentation:"
echo "    docs/test_config.md                 # Configuration reference"
echo "    docs/test_creds.md                  # Credentials setup"
echo "    docs/test_run_config.md             # Batch execution config"
echo ""
echo "================================================================="
echo ""
