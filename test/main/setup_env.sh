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
# Main Module — Environment Setup
# =============================================================================
# Creates a Python virtual environment, installs dependencies, and configures
# the test environment for omnia.sh validation tests.
#
# Usage:
#   ./setup_env.sh           # Standard setup
#   ./setup_env.sh --force   # Remove existing .venv and recreate
#   ./setup_env.sh --debug   # Verbose output
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$SCRIPT_DIR/.venv"
FORCE=false
DEBUG=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --force)  FORCE=true ;;
        --debug)  DEBUG=true ;;
        --help|-h)
            echo "Usage: $0 [--force] [--debug]"
            echo "  --force   Remove existing .venv and recreate"
            echo "  --debug   Verbose output"
            exit 0
            ;;
    esac
done

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================

info "Checking prerequisites..."

# Python 3.9+
if ! command -v python3 &>/dev/null; then
    fail "python3 not found. Install Python 3.9+ first."
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]; }; then
    fail "Python 3.9+ required. Found: $PYTHON_VERSION"
fi
ok "Python $PYTHON_VERSION"

# sshpass (needed for remote mode)
if command -v sshpass &>/dev/null; then
    ok "sshpass found"
else
    warn "sshpass not found — remote mode will not work. Install: dnf install -y sshpass"
fi

# =============================================================================
# VIRTUAL ENVIRONMENT
# =============================================================================

if [ "$FORCE" = true ] && [ -d "$VENV_DIR" ]; then
    info "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created"
else
    ok "Virtual environment already exists"
fi

# Activate
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# =============================================================================
# INSTALL DEPENDENCIES
# =============================================================================

info "Installing Python dependencies..."

# Use top-level requirements.txt if present, else module-level
REQ_FILE="$TEST_ROOT/requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
    REQ_FILE="$SCRIPT_DIR/requirements.txt"
fi

if [ ! -f "$REQ_FILE" ]; then
    fail "requirements.txt not found at $TEST_ROOT or $SCRIPT_DIR"
fi

if [ "$DEBUG" = true ]; then
    pip install --upgrade pip setuptools wheel
    # Run from TEST_ROOT so '-e .' in requirements.txt resolves to test/setup.py
    (cd "$TEST_ROOT" && pip install -r "$REQ_FILE")
else
    pip install --upgrade pip setuptools wheel -q
    (cd "$TEST_ROOT" && pip install -r "$REQ_FILE" -q)
fi

ok "Dependencies installed"

# =============================================================================
# MAKE SCRIPTS EXECUTABLE
# =============================================================================

chmod +x "$SCRIPT_DIR/run_validation.sh" 2>/dev/null || true
chmod +x "$TEST_ROOT/run_validation.sh" 2>/dev/null || true

ok "Scripts made executable"

# =============================================================================
# INJECT run_validation FUNCTION INTO .venv/bin/activate
# =============================================================================

ACTIVATE_FILE="$VENV_DIR/bin/activate"
MARKER="# >>> omnia-automation >>>"

if ! grep -q "$MARKER" "$ACTIVATE_FILE" 2>/dev/null; then
    info "Adding run_validation shell function and tab-completion..."
    cat >> "$ACTIVATE_FILE" << 'OMNIA_ACTIVATE_EOF'

# >>> omnia-automation >>>
# Added by setup_env.sh — shell functions and tab-completion for Omnia Automation

# Shell function so run_validation works without ./
run_validation() {
    "$(dirname "${VIRTUAL_ENV%/.venv}")/run_validation.sh" "$@"
}

# Tab-completion for run_validation
_run_validation_completions() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    local fvt_dir="${VIRTUAL_ENV%/.venv}/fvt"
    local scenarios=""
    for d in "$fvt_dir"/*/; do
        [ -d "$d" ] || continue
        local sname=$(basename "$d")
        [[ "$sname" == "__pycache__" ]] && continue
        scenarios="${scenarios} $sname"
    done
    local commands="deploy verify test"
    local special="list help --config"
    local config_opts="--continue-on-failure --restart"
    local options="--suite --marker"
    local suites="container security cleanup"
    local markers="sanity smoke regression functional negative security performance"
    case "$COMP_CWORD" in
        1) COMPREPLY=( $(compgen -W "${scenarios} ${special}" -- "$cur") ) ;;
        2)
            case "$prev" in
                list|help|--help|-h) COMPREPLY=() ;;
                --config) COMPREPLY=( $(compgen -W "${config_opts}" -- "$cur") ) ;;
                *) COMPREPLY=( $(compgen -W "${commands} ${options}" -- "$cur") ) ;;
            esac ;;
        *)
            case "$prev" in
                --suite)  COMPREPLY=( $(compgen -W "${suites}" -- "$cur") ) ;;
                --marker) COMPREPLY=( $(compgen -W "${markers}" -- "$cur") ) ;;
                --config) COMPREPLY=( $(compgen -W "${config_opts}" -- "$cur") ) ;;
                *) COMPREPLY=( $(compgen -W "${options}" -- "$cur") ) ;;
            esac ;;
    esac
}
complete -F _run_validation_completions run_validation

# <<< omnia-automation <<<
OMNIA_ACTIVATE_EOF
    ok "Shell function and tab-completion added to activate script"
else
    ok "Shell function already present in activate script"
fi

# =============================================================================
# VERIFY CONFIGURATION FILES
# =============================================================================

info "Checking configuration files..."

if [ -f "$SCRIPT_DIR/test_config.yml" ]; then
    ok "test_config.yml found"
else
    warn "test_config.yml not found — create it before running tests"
fi

if [ -f "$SCRIPT_DIR/test_creds.yml" ]; then
    ok "test_creds.yml found"
else
    warn "test_creds.yml not found — create it before running tests"
fi

# =============================================================================
# DONE
# =============================================================================

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Main Module Environment — Ready${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Activate:${NC}     source $VENV_DIR/bin/activate"
echo -e "  ${BLUE}Run tests:${NC}    run_validation omnia_sh_install deploy"
echo -e "  ${BLUE}List:${NC}         run_validation help"
echo ""
