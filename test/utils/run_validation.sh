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
# Utils Domain — Test Runner Script
# =============================================================================
# Runs FVT tests for the utils domain.
#
# Usage:
#   ./run_validation.sh <scenario> <command> [options]
#
# Scenarios:
#   precheck      - Environment and connectivity checks
#   collect       - Log collector tests
#   install_os    - OS installation tests
#
# Commands:
#   deploy        - Run playbook deployment tests only
#   verify        - Run verification tests only
#   test          - Run all tests (deploy + verify)
#
# Options:
#   --marker <expr>   - Filter by marker (sanity, functional, deploy)
#   --suite <name>    - Run specific test suite
#   --config          - Run all scenarios from test_run_config.yml
#
# Examples:
#   ./run_validation.sh collect test
#   ./run_validation.sh collect test --marker sanity
#   ./run_validation.sh precheck verify
#   ./run_validation.sh --config
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"; }

usage() {
    echo "Usage: $0 <scenario> <command> [options]"
    echo ""
    echo "Scenarios:"
    echo "  precheck      Environment and connectivity checks"
    echo "  collect       Log collector tests"
    echo "  install_os    OS installation tests"
    echo ""
    echo "Commands:"
    echo "  deploy        Run playbook deployment tests only"
    echo "  verify        Run verification tests only"
    echo "  test          Run all tests (deploy + verify)"
    echo ""
    echo "Options:"
    echo "  --marker <expr>   Filter by marker expression"
    echo "  --suite <name>    Run specific test suite"
    echo "  --config          Run all scenarios from test_run_config.yml"
    echo ""
    echo "Examples:"
    echo "  $0 collect test"
    echo "  $0 collect test --marker sanity"
    echo "  $0 precheck verify"
    echo "  $0 --config"
    exit 1
}

# Check virtual environment
if [[ ! -d "${VENV_DIR}" ]]; then
    log_error "Virtual environment not found. Run ./setup_env.sh first."
    exit 1
fi

# Activate virtual environment
source "${VENV_DIR}/bin/activate"

# Parse arguments
SCENARIO=""
COMMAND=""
MARKER=""
SUITE=""
CONFIG_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_MODE=true
            shift
            ;;
        --marker)
            MARKER="$2"
            shift 2
            ;;
        --suite)
            SUITE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [[ -z "${SCENARIO}" ]]; then
                SCENARIO="$1"
            elif [[ -z "${COMMAND}" ]]; then
                COMMAND="$1"
            else
                log_error "Unknown argument: $1"
                usage
            fi
            shift
            ;;
    esac
done

# Config mode: run all scenarios from test_run_config.yml
if [[ "${CONFIG_MODE}" == "true" ]]; then
    log_header
    log_info "Running all scenarios from test_run_config.yml"
    log_header

    # Parse test_run_config.yml and run each enabled scenario
    python3 << 'EOF'
import yaml
import subprocess
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
config_file = os.path.join(script_dir, 'test_run_config.yml')

with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

skip_on_failure = config.get('skip_on_failure', False)
scenarios = config.get('scenarios', {})

# Sort by order
sorted_scenarios = sorted(scenarios.items(), key=lambda x: x[1].get('order', 999))

failed = False
for name, settings in sorted_scenarios:
    if not settings.get('run', True):
        print(f"[SKIP] Scenario '{name}' is disabled")
        continue

    if failed and skip_on_failure:
        print(f"[SKIP] Scenario '{name}' skipped due to previous failure")
        continue

    command = settings.get('command', 'test')
    marker = settings.get('marker', '')
    suite = settings.get('suite', '')

    print(f"\n{'='*60}")
    print(f"Running scenario: {name} ({command})")
    print(f"{'='*60}\n")

    cmd = [sys.executable, '-m', 'pytest', f'fvt/{name}/', '-v']
    if marker:
        cmd.extend(['--marker', marker])

    result = subprocess.run(cmd, cwd=script_dir)
    if result.returncode != 0:
        failed = True
        print(f"[FAIL] Scenario '{name}' failed")
    else:
        print(f"[PASS] Scenario '{name}' passed")

sys.exit(1 if failed else 0)
EOF
    exit $?
fi

# Validate arguments
if [[ -z "${SCENARIO}" ]] || [[ -z "${COMMAND}" ]]; then
    usage
fi

# Validate scenario
VALID_SCENARIOS=("precheck" "collect" "install_os")
if [[ ! " ${VALID_SCENARIOS[*]} " =~ " ${SCENARIO} " ]]; then
    log_error "Invalid scenario: ${SCENARIO}"
    log_error "Valid scenarios: ${VALID_SCENARIOS[*]}"
    exit 1
fi

# Validate command
VALID_COMMANDS=("deploy" "verify" "test")
if [[ ! " ${VALID_COMMANDS[*]} " =~ " ${COMMAND} " ]]; then
    log_error "Invalid command: ${COMMAND}"
    log_error "Valid commands: ${VALID_COMMANDS[*]}"
    exit 1
fi

# Build pytest command
PYTEST_ARGS=("-v")

# Add test path
if [[ -n "${SUITE}" ]]; then
    TEST_PATH="fvt/${SCENARIO}/${SUITE}/"
else
    TEST_PATH="fvt/${SCENARIO}/"
fi

# Add marker filter based on command
if [[ "${COMMAND}" == "deploy" ]]; then
    PYTEST_ARGS+=("--marker" "deploy")
elif [[ "${COMMAND}" == "verify" ]]; then
    # Verify = all non-deploy tests
    if [[ -n "${MARKER}" ]]; then
        PYTEST_ARGS+=("--marker" "${MARKER}")
    fi
fi

# Add custom marker if specified
if [[ -n "${MARKER}" ]] && [[ "${COMMAND}" != "deploy" ]]; then
    PYTEST_ARGS+=("--marker" "${MARKER}")
fi

log_header
log_info "Utils Domain FVT"
log_info "Scenario: ${SCENARIO}"
log_info "Command: ${COMMAND}"
log_info "Test path: ${TEST_PATH}"
[[ -n "${MARKER}" ]] && log_info "Marker: ${MARKER}"
[[ -n "${SUITE}" ]] && log_info "Suite: ${SUITE}"
log_header

# Run pytest
cd "${SCRIPT_DIR}"
python -m pytest "${TEST_PATH}" "${PYTEST_ARGS[@]}"
