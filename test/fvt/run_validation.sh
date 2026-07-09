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
# Omnia Validation Runner
# =============================================================================
#
# Runs Ansible playbooks and verification tests via pytest.
#
# Usage:
#   run_validation <scenario> <command> [options]
#   run_validation all <command> [options]
#   run_validation list
#   run_validation --config
#
# Commands:
#   deploy    - Run the playbook only (live streaming output)
#   verify    - Run verification tests only (no playbook execution)
#   test      - Run playbook + verification tests (full flow)
#   list      - List available scenarios
#   --config  - Run scenarios from test_run_config.yml
#
# Options:
#   --suite <name>    Filter by test folder (sanity, negative, regression, smoke, stress)
#   --marker <expr>   Filter by pytest marker expression (e.g., deploy, build_stream)
#   -v, --verbose     Increase pytest verbosity
#
# Filtering:
#   --suite selects tests from the matching folder (e.g., tests/sanity/)
#   --marker selects tests with the matching @pytest.mark decorator
#   Combined: --suite sanity --marker build_stream  runs sanity/ tests WITH marker build_stream
#   Neither: runs ALL tests across all suite folders
#
# Examples:
#   run_validation prepare_oim deploy                     # Run playbook
#   run_validation prepare_oim verify                     # Run all verification tests
#   run_validation prepare_oim verify --suite sanity       # Sanity folder only
#   run_validation prepare_oim verify --marker build_stream   # Tests with marker only
#   run_validation prepare_oim verify --suite sanity --marker build_stream  # Combined
#   run_validation prepare_oim test                       # Deploy + verify
#   run_validation all test                               # All scenarios
#   run_validation list                                   # List scenarios
#   run_validation --config                               # Batch from config
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATIONS_DIR="${SCRIPT_DIR}/validations"
CONFIG_FILE="${SCRIPT_DIR}/test_run_config.yml"

SUPPORTED_COMMANDS="deploy verify test"
SUPPORTED_SUITES="sanity negative regression smoke stress performance"

# Change to script directory
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# =============================================================================
# Parse arguments
# =============================================================================
SCENARIO="$1"
COMMAND="$2"
SUITE=""
MARKER=""
VERBOSE=""

# Parse optional arguments
if [[ $# -gt 2 ]]; then
    shift 2
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
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                echo "Run '$0 help' for usage."
                exit 1
                ;;
        esac
    done
fi

# =============================================================================
# Build test path and marker arguments
# =============================================================================
# --suite  => filters by folder  (tests/<suite>/)
# --marker => filters by pytest marker (-m <marker>)
# Combined => folder + marker
# Neither  => all tests in tests/
build_test_path() {
    local tests_dir="$1"
    if [[ -n "$SUITE" && -d "${tests_dir}/${SUITE}" ]]; then
        echo "${tests_dir}/${SUITE}"
    else
        echo "${tests_dir}"
    fi
}

build_marker_args() {
    local exclude_deploy="$1"  # "yes" or ""
    local marker_expr=""

    if [[ -n "$MARKER" ]]; then
        marker_expr="$MARKER"
    fi

    if [[ "$exclude_deploy" == "yes" ]]; then
        if [[ -n "$marker_expr" ]]; then
            marker_expr="${marker_expr} and not deploy"
        else
            marker_expr="not deploy"
        fi
    fi

    if [[ -n "$marker_expr" ]]; then
        echo "-m \"${marker_expr}\""
    fi
}

# =============================================================================
# Get available scenarios
# =============================================================================
get_scenarios() {
    if [[ -d "$VALIDATIONS_DIR" ]]; then
        for dir in "$VALIDATIONS_DIR"/*/; do
            local name
            name=$(basename "$dir")
            if [[ -d "${dir}tests" ]]; then
                echo "$name"
            fi
        done
    fi
}

# =============================================================================
# Run pytest
# =============================================================================
run_pytest() {
    local test_path="$1"
    local marker_args="$2"
    local label="$3"

    echo -e "${YELLOW}-> ${label}...${NC}"
    echo ""

    local pytest_cmd="python -m pytest ${test_path} -s --tb=short ${marker_args}"

    echo -e "  ${CYAN}Command: ${pytest_cmd}${NC}"
    echo ""

    eval "$pytest_cmd"
}

# =============================================================================
# Run batch config mode
# =============================================================================
run_config_mode() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo -e "${RED}Error: Config file not found: ${CONFIG_FILE}${NC}"
        exit 1
    fi

    # Share ONE report ID across all scenarios in this batch
    export OMNIA_REPORT_ID=$(date '+%Y%m%d%H%M%S')

    echo -e "${BLUE}=================================================================${NC}"
    echo -e "${BLUE}  Batch Execution from test_run_config.yml${NC}"
    echo -e "${BLUE}  Report ID : ${OMNIA_REPORT_ID}${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    echo ""

    local total=0 passed=0 failed=0 skipped=0
    local scenario_names
    scenario_names=$(python3 -c "
import yaml, sys
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
for name in cfg.get('scenarios', {}):
    print(name)
")

    for name in $scenario_names; do
        local run_flag command suite marker_cfg
        eval "$(python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
sc = cfg.get('scenarios', {}).get('${name}', {})
print(f'run_flag={str(sc.get(\"run\", False)).lower()}')
print(f'command={sc.get(\"command\", \"test\")}')
print(f'suite={sc.get(\"suite\", \"\")}')
print(f'marker_cfg={sc.get(\"marker\", \"\")}')
")"
        total=$((total + 1))
        if [[ "$run_flag" != "true" ]]; then
            echo -e "  ${YELLOW}SKIP${NC}  ${name}"
            skipped=$((skipped + 1))
            continue
        fi

        echo -e "  ${CYAN}RUN${NC}   ${name} (${command}, suite=${suite:-all}, marker=${marker_cfg:-none})"

        local extra_args=""
        [[ -n "$suite" ]] && extra_args="$extra_args --suite $suite"
        [[ -n "$marker_cfg" ]] && extra_args="$extra_args --marker $marker_cfg"

        if "$0" "$name" "$command" $extra_args; then
            echo -e "  ${GREEN}PASS${NC}  ${name}"
            passed=$((passed + 1))
        else
            echo -e "  ${RED}FAIL${NC}  ${name}"
            failed=$((failed + 1))
        fi
    done

    echo ""
    echo -e "${BLUE}=================================================================${NC}"
    echo -e "  Total: ${total}  ${GREEN}Passed: ${passed}${NC}  ${RED}Failed: ${failed}${NC}  ${YELLOW}Skipped: ${skipped}${NC}"
    echo -e "  ${CYAN}Report: reports/test_report.json${NC}"
    echo -e "  ${CYAN}Report: reports/test_report.html${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    [[ $failed -eq 0 ]] || exit 1
}

# =============================================================================
# Run all scenarios
# =============================================================================
run_all_scenarios() {
    local cmd="$1"

    # Share ONE report ID across all scenarios
    export OMNIA_REPORT_ID=$(date '+%Y%m%d%H%M%S')

    echo -e "${BLUE}=================================================================${NC}"
    echo -e "${BLUE}  Running ALL Scenarios: ${cmd}${NC}"
    echo -e "${BLUE}  Report ID : ${OMNIA_REPORT_ID}${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    echo ""

    local total=0 passed=0 failed=0
    for name in $(get_scenarios); do
        total=$((total + 1))
        echo -e "${YELLOW}[${total}] ${name}${NC}"
        local extra_args=""
        [[ -n "$SUITE" ]] && extra_args="$extra_args --suite $SUITE"
        [[ -n "$MARKER" ]] && extra_args="$extra_args --marker $MARKER"
        [[ -n "$VERBOSE" ]] && extra_args="$extra_args $VERBOSE"

        if "$0" "$name" "$cmd" $extra_args; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
        fi
        echo ""
    done

    echo -e "${BLUE}=================================================================${NC}"
    echo -e "  Total: ${total}  ${GREEN}Passed: ${passed}${NC}  ${RED}Failed: ${failed}${NC}"
    echo -e "  ${CYAN}Report: reports/test_report.json${NC}"
    echo -e "  ${CYAN}Report: reports/test_report.html${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    [[ $failed -eq 0 ]] || exit 1
}

# =============================================================================
# Handle special commands
# =============================================================================
case "$SCENARIO" in
    list|--list)
        echo -e "${BLUE}=================================================================${NC}"
        echo -e "${BLUE}  Available Validation Scenarios${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""
        SCENARIOS=$(get_scenarios)
        if [[ -z "$SCENARIOS" ]]; then
            echo -e "  ${YELLOW}No scenarios found in validations/${NC}"
        else
            for name in $SCENARIOS; do
                echo -e "  ${GREEN}${name}${NC}"
            done
        fi
        echo ""
        exit 0
        ;;

    --config)
        run_config_mode
        exit 0
        ;;

    all)
        COMMAND="${COMMAND:-test}"
        if ! echo " ${SUPPORTED_COMMANDS} " | grep -q " ${COMMAND} "; then
            echo -e "${RED}Error: Invalid command '${COMMAND}'${NC}"
            exit 1
        fi
        run_all_scenarios "$COMMAND"
        exit 0
        ;;

    help|--help|-h|"")
        echo -e "${BOLD}Omnia Validation Runner${NC}"
        echo ""
        echo "Usage: $0 <scenario> <command> [options]"
        echo "       $0 all <command> [options]"
        echo "       $0 --config"
        echo ""
        echo "Commands:"
        echo "  deploy    - Run the Ansible playbook only (live streaming output)"
        echo "  verify    - Run verification tests only (no playbook)"
        echo "  test      - Run playbook + verification tests (full flow)"
        echo ""
        echo "Options:"
        echo "  --suite <name>    Filter by test folder (sanity, negative, regression, smoke, stress)"
        echo "  --marker <expr>   Filter by pytest marker decorator"
        echo "  -v, --verbose     Increase pytest verbosity"
        echo ""
        echo "Filtering:"
        echo "  --suite sanity                     -> tests in tests/sanity/ folder"
        echo "  --marker build_stream              -> tests with @pytest.mark.build_stream"
        echo "  --suite sanity --marker build_stream -> sanity/ tests WITH marker build_stream"
        echo "  (no flags)                         -> ALL tests across all folders"
        echo ""
        echo "Examples:"
        echo "  $0 prepare_oim deploy                     # Run playbook"
        echo "  $0 prepare_oim verify --suite sanity       # Sanity tests only"
        echo "  $0 prepare_oim test                       # Deploy + verify"
        echo "  $0 all test                               # All scenarios"
        echo "  $0 --config                               # Batch from config"
        echo "  $0 list                                   # List scenarios"
        echo ""
        exit 0
        ;;
esac

# =============================================================================
# Validate scenario
# =============================================================================
SCENARIO_DIR="${VALIDATIONS_DIR}/${SCENARIO}"
TESTS_DIR="${SCENARIO_DIR}/tests"

if [[ ! -d "$SCENARIO_DIR" ]]; then
    echo -e "${RED}Error: Scenario '${SCENARIO}' not found in validations/${NC}"
    echo ""
    echo -e "${YELLOW}Available scenarios:${NC}"
    get_scenarios | while read -r s; do echo "  $s"; done
    echo ""
    echo "Run '$0 list' to see all scenarios."
    exit 1
fi

if [[ ! -d "$TESTS_DIR" ]]; then
    echo -e "${RED}Error: No tests/ directory found in validations/${SCENARIO}/${NC}"
    exit 1
fi

# Default command
COMMAND="${COMMAND:-test}"

# Validate command
if ! echo " ${SUPPORTED_COMMANDS} " | grep -q " ${COMMAND} "; then
    echo -e "${RED}Error: Invalid command '${COMMAND}'${NC}"
    echo -e "${YELLOW}Supported commands:${NC} ${SUPPORTED_COMMANDS}"
    exit 1
fi

# Validate suite — check folder exists
if [[ -n "$SUITE" ]]; then
    if ! echo " ${SUPPORTED_SUITES} " | grep -q " ${SUITE} "; then
        echo -e "${RED}Error: Invalid suite '${SUITE}'${NC}"
        echo -e "${YELLOW}Supported suites:${NC} ${SUPPORTED_SUITES}"
        exit 1
    fi
    if [[ ! -d "${TESTS_DIR}/${SUITE}" ]]; then
        echo -e "${YELLOW}Warning: Suite folder '${SUITE}' not found in ${TESTS_DIR}/${NC}"
        echo -e "${YELLOW}Available suite folders:${NC}"
        ls -d "${TESTS_DIR}"/*/ 2>/dev/null | xargs -I{} basename {} | while read -r d; do echo "  $d"; done
        exit 1
    fi
fi

# =============================================================================
# Generate report ID (reuse if already set by batch/all mode)
# =============================================================================
if [[ -z "${OMNIA_REPORT_ID:-}" ]]; then
    export OMNIA_REPORT_ID=$(date '+%Y%m%d%H%M%S')
fi

# =============================================================================
# Display banner
# =============================================================================
echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}  Omnia Validation Runner${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo -e "  Scenario  : ${GREEN}${SCENARIO}${NC}"
echo -e "  Command   : ${GREEN}${COMMAND}${NC}"
if [[ -n "$SUITE" ]]; then
    echo -e "  Suite     : ${GREEN}${SUITE}${NC}"
fi
if [[ -n "$MARKER" ]]; then
    echo -e "  Marker    : ${GREEN}${MARKER}${NC}"
fi
echo -e "  Report ID : ${GREEN}${OMNIA_REPORT_ID}${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo ""

# =============================================================================
# Export execution context for report capture
# =============================================================================
export OMNIA_SUITE="${SUITE:-all}"
export OMNIA_MARKER="${MARKER:-}"
export OMNIA_COMMAND_TYPE="${COMMAND}"

# =============================================================================
# Execute based on command
# =============================================================================
case "$COMMAND" in

    # -------------------------------------------------------------------------
    # DEPLOY: Run playbook only (always from tests/ root with -m deploy)
    # -------------------------------------------------------------------------
    deploy)
        run_pytest \
            "${TESTS_DIR}" \
            "-m deploy" \
            "Running playbook deployment for ${SCENARIO}"

        echo ""
        echo -e "${GREEN}Deployment completed.${NC}"
        ;;

    # -------------------------------------------------------------------------
    # VERIFY: Run verification tests only (folder + marker filtering)
    # -------------------------------------------------------------------------
    verify)
        test_path=$(build_test_path "${TESTS_DIR}")
        marker_args=$(build_marker_args "yes")   # exclude deploy

        run_pytest \
            "${test_path}" \
            "${marker_args} ${VERBOSE}" \
            "Running verification tests for ${SCENARIO}"

        echo ""
        echo -e "${GREEN}Verification completed.${NC}"
        ;;

    # -------------------------------------------------------------------------
    # TEST: Deploy + Verify (full flow)
    # -------------------------------------------------------------------------
    test)
        FAILED=0

        # Step 1: Deploy
        echo -e "${YELLOW}=================================================================${NC}"
        echo -e "${YELLOW}  Step 1/2: Deploy${NC}"
        echo -e "${YELLOW}=================================================================${NC}"
        echo ""

        if run_pytest "${TESTS_DIR}" "-m deploy" "Running playbook deployment"; then
            echo -e "${GREEN}Deployment succeeded${NC}"
        else
            echo -e "${RED}Deployment failed${NC}"
            FAILED=1
        fi
        echo ""

        # Step 2: Verify (only if deploy succeeded)
        if [[ $FAILED -eq 0 ]]; then
            echo -e "${YELLOW}=================================================================${NC}"
            echo -e "${YELLOW}  Step 2/2: Verify${NC}"
            echo -e "${YELLOW}=================================================================${NC}"
            echo ""

            test_path=$(build_test_path "${TESTS_DIR}")
            marker_args=$(build_marker_args "yes")  # exclude deploy

            if run_pytest "${test_path}" "${marker_args} ${VERBOSE}" "Running verification tests"; then
                echo -e "${GREEN}Verification succeeded${NC}"
            else
                echo -e "${RED}Verification failed${NC}"
                FAILED=1
            fi
        else
            echo -e "${YELLOW}Skipping verification -- deployment failed${NC}"
        fi

        # Summary
        echo ""
        echo -e "${BLUE}=================================================================${NC}"
        if [[ $FAILED -eq 0 ]]; then
            echo -e "${GREEN}  ${SCENARIO}: DEPLOY + VERIFY PASSED${NC}"
        else
            echo -e "${RED}  ${SCENARIO}: FAILED${NC}"
        fi
        echo -e "${BLUE}=================================================================${NC}"

        [[ $FAILED -eq 0 ]] || exit 1
        ;;
esac

echo ""
echo -e "  ${CYAN}Report: reports/test_report.json${NC}"
echo ""

# =============================================================================
# Bash Tab Completion (sourced by setup_env.sh)
# =============================================================================
if [[ "$1" == "--completion" ]]; then
    cat <<'COMPLETION_SCRIPT'
_run_validation_completions() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local scenarios commands suites
    scenarios=$(ls -d validations/*/tests 2>/dev/null | cut -d/ -f2)
    commands="deploy verify test"
    suites="sanity negative regression smoke stress performance"

    case "${COMP_CWORD}" in
        1) COMPREPLY=($(compgen -W "$scenarios all list help --config" -- "$cur")) ;;
        2) COMPREPLY=($(compgen -W "$commands" -- "$cur")) ;;
        *)
            case "$prev" in
                --suite) COMPREPLY=($(compgen -W "$suites" -- "$cur")) ;;
                *) COMPREPLY=($(compgen -W "--suite --marker -v --verbose" -- "$cur")) ;;
            esac
            ;;
    esac
}
complete -F _run_validation_completions run_validation
complete -F _run_validation_completions ./run_validation.sh
COMPLETION_SCRIPT
    exit 0
fi
