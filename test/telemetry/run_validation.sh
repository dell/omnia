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
# telemetry — Validation Runner
# =============================================================================
# Usage:
#   ./run_validation.sh <scenario> <command> [options]
#   ./run_validation.sh all <command> [options]
#   ./run_validation.sh --config
#   ./run_validation.sh list
#
# Commands:
#   deploy    Run the playbook only (tests marked @deploy)
#   verify    Run verification tests only (exclude @deploy)
#   test      Deploy + Verify (full flow)
#
# Options:
#   --suite <name>    Filter by subfolder (sinks, sources, cluster, etc.)
#   --marker <expr>   Filter by pytest marker (sanity, sink, source, etc.)
#   -v, --verbose     Increase verbosity
#
# FVT Scenarios:
#   precheck            Precheck environment tests
#   validate            Input validation tests
#   deploy              Deploy telemetry tests (sinks + sources)
#   cleanup             Cleanup tests
#   telemetry           Full end-to-end (deploy without tags + verify)
#
# NFT Scenarios:
#   nft                 Non-functional tests (performance + idempotency)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FVT_DIR="${SCRIPT_DIR}/fvt"
NFT_DIR="${SCRIPT_DIR}/nft"
CONFIG_FILE="${SCRIPT_DIR}/test_run_config.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SUPPORTED_COMMANDS="deploy verify test"

# Change to script dir
cd "$SCRIPT_DIR"

# Activate venv if exists
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# =============================================================================
# Parse arguments
# =============================================================================
SCENARIO="${1:-help}"
COMMAND="${2:-test}"
SUITE=""
MARKER=""
VERBOSE=""
DEBUG=""

shift 2 2>/dev/null || true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --suite)
            SUITE="$2"
            shift 2
            ;;
        --marker)
            MARKER="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# =============================================================================
# Functions
# =============================================================================
list_scenarios() {
    echo -e "${CYAN}Available FVT scenarios:${NC}"
    for dir in "$FVT_DIR"/*/; do
        [ -d "$dir" ] || continue
        name=$(basename "$dir")
        echo -e "  ${GREEN}${name}${NC}"
    done
    if [ -d "$NFT_DIR" ]; then
        echo -e "\n${CYAN}Available NFT scenarios:${NC}"
        echo -e "  ${GREEN}nft${NC}"
    fi
}

show_help() {
    echo -e "${CYAN}Telemetry Validation Runner${NC}"
    echo ""
    echo "Usage: ./run_validation.sh <scenario> <command> [options]"
    echo ""
    echo "Scenarios:"
    echo "  precheck       Precheck environment"
    echo "  validate       Input validation"
    echo "  deploy         Deploy telemetry"
    echo "  cleanup        Cleanup telemetry"
    echo "  telemetry      Full E2E"
    echo "  nft            Non-functional tests"
    echo "  all            Run all FVT scenarios"
    echo "  list           List available scenarios"
    echo ""
    echo "Commands:"
    echo "  deploy         Run playbook only (@deploy marker)"
    echo "  verify         Run verification only (exclude @deploy)"
    echo "  test           Deploy + Verify (default)"
    echo ""
    echo "Options:"
    echo "  --suite <name>   Filter by subfolder"
    echo "  --marker <expr>  Filter by marker (sanity, sink, source)"
    echo "  -v, --verbose    Increase verbosity"
    echo "  --config         Run batch from test_run_config.yml"
}

run_scenario() {
    local scenario="$1"
    local command="$2"

    # Determine test directory
    local test_dir
    if [ "$scenario" = "nft" ]; then
        test_dir="$NFT_DIR"
    else
        test_dir="$FVT_DIR/$scenario"
    fi

    if [ ! -d "$test_dir" ]; then
        echo -e "${RED}Scenario directory not found: ${test_dir}${NC}"
        return 1
    fi

    # Build pytest command
    local pytest_args=()
    pytest_args+=("$test_dir")

    # Suite filter
    if [ -n "$SUITE" ]; then
        pytest_args=("$test_dir/$SUITE/")
    fi

    # Command filter (marker-based)
    case "$command" in
        deploy)
            pytest_args+=("-m" "deploy")
            ;;
        verify)
            pytest_args+=("-m" "not deploy")
            ;;
        test)
            # No marker filter — run all
            ;;
        *)
            echo -e "${RED}Invalid command: $command${NC}"
            echo "Valid commands: $SUPPORTED_COMMANDS"
            return 1
            ;;
    esac

    # Additional marker filter
    if [ -n "$MARKER" ]; then
        pytest_args+=("--marker" "$MARKER")
    fi

    # Verbose
    if [ -n "$VERBOSE" ]; then
        pytest_args+=("-v")
    fi

    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Scenario: ${GREEN}${scenario}${BLUE}  Command: ${GREEN}${command}${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    pytest "${pytest_args[@]}"
}

run_config() {
    echo -e "${CYAN}Running batch configuration from ${CONFIG_FILE}${NC}"

    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}Config file not found: ${CONFIG_FILE}${NC}"
        exit 1
    fi

    # Parse YAML using python
    python3 -c "
import yaml, sys
with open('$CONFIG_FILE') as f:
    cfg = yaml.safe_load(f)
for s in cfg.get('scenarios', []):
    if s.get('enabled', False):
        print(f\"{s['scenario']}|{s.get('command', 'test')}|{s.get('dataset', '')}|{s.get('sync_input', '')}|{s.get('marker', '')}\")
" | while IFS='|' read -r scenario command dataset sync_input marker; do
        # Set overrides
        [ -n "$dataset" ] && export OMNIA_DATASET_OVERRIDE="$dataset"
        [ -n "$sync_input" ] && export OMNIA_SYNC_INPUT_OVERRIDE="$sync_input"

        # Override marker if set
        if [ -n "$marker" ]; then
            MARKER="$marker"
        fi

        run_scenario "$scenario" "$command"

        # Clear overrides
        unset OMNIA_DATASET_OVERRIDE 2>/dev/null || true
        unset OMNIA_SYNC_INPUT_OVERRIDE 2>/dev/null || true
    done
}

# =============================================================================
# Main
# =============================================================================
case "$SCENARIO" in
    help|-h|--help)
        show_help
        ;;
    list)
        list_scenarios
        ;;
    --config)
        run_config
        ;;
    all)
        for dir in "$FVT_DIR"/*/; do
            [ -d "$dir" ] || continue
            name=$(basename "$dir")
            run_scenario "$name" "$COMMAND" || true
        done
        ;;
    *)
        run_scenario "$SCENARIO" "$COMMAND"
        ;;
esac
