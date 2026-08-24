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
# Build Stream — Validation Runner
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FVT_DIR="${SCRIPT_DIR}/fvt"
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

# Activate venv if exists, otherwise use system python
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# =============================================================================
SCENARIO="${1:-help}"
COMMAND="${2:-test}"
SUITE=""
MARKER=""
VERBOSE=""
DEBUG=""

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
            --debug)
                DEBUG="true"
                VERBOSE="-vvs"
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
        esac
    done
fi

# =============================================================================
get_scenarios() {
    for dir in "$FVT_DIR"/*/; do
        name=$(basename "$dir")
        [[ "$name" == __pycache__ ]] && continue
        echo "$name"
    done
}

build_test_path() {
    local tests_dir="$1"
    if [[ -n "$SUITE" && -d "${tests_dir}/${SUITE}" ]]; then
        echo "${tests_dir}/${SUITE}"
    else
        echo "${tests_dir}"
    fi
}

build_pytest_args() {
    local exclude_deploy="$1"
    local args=""

    if [[ -n "$MARKER" ]]; then
        args="${args} --marker ${MARKER}"
    fi

    if [[ "$exclude_deploy" == "yes" ]]; then
        args="${args} -m 'not deploy'"
    fi

    echo "$args"
}

print_combined_summary() {
    local results_file="${1:-${OMNIA_RESULTS_FILE:-}}"
    if [[ -z "$results_file" || ! -f "$results_file" ]]; then
        return
    fi
    python3 - "$results_file" <<'PYEOF'
import json, sys
results_file = sys.argv[1]
try:
    with open(results_file) as f:
        results = json.load(f)
except (json.JSONDecodeError, OSError):
    sys.exit(0)
if not results:
    sys.exit(0)

passed = [r for r in results if r["status"] == "PASSED"]
failed = [r for r in results if r["status"] == "FAILED"]
skipped = [r for r in results if r["status"] == "SKIPPED"]
total = len(results)
sep = "=" * 85
print(f"\n{sep}")
print("  TEST EXECUTION SUMMARY")
print(sep)
hdr = f"  {'TC ID':<12} {'Test Name':<40} {'Status':<10} {'Duration':>8}"
div = f"  {'-' * 12} {'-' * 40} {'-' * 10} {'-' * 8}"
print(hdr)
print(div)
cyan = "\033[36m"
rst = "\033[0m"
for r in results:
    tc = r.get("tc_id", "")
    name = r["test_name"]
    if len(name) > 39:
        name = name[:36] + "..."
    st = r["status"]
    dur = f"{r['duration']:.2f}s"
    if st == "PASSED":
        tag = f"\033[32m{st}\033[0m"
    elif st == "FAILED":
        tag = f"\033[31m{st}\033[0m"
    else:
        tag = f"\033[33m{st}\033[0m"
    pad = " " * max(1, 40 - len(name))
    print(f"  {cyan}{tc:<12}{rst} {cyan}{name}{rst}{pad} {tag:<19} {dur:>8}")
print(div)
total_dur = sum(r["duration"] for r in results)
print(
    f"  \033[32m{len(passed)} passed\033[0m, "
    f"\033[31m{len(failed)} failed\033[0m, "
    f"\033[33m{len(skipped)} skipped\033[0m "
    f"/ {total} total "
    f"({total_dur:.2f}s)"
)
print(sep)
print()
PYEOF
    rm -f "$results_file"
}

run_pytest() {
    local test_path="$1"
    local marker_args="$2"
    local label="$3"

    echo -e "${YELLOW}-> ${label}...${NC}"
    echo ""

    local pytest_cmd="python3 -m pytest ${test_path} -s --tb=short --no-header -q ${marker_args} ${VERBOSE}"
    echo -e "  ${CYAN}Command: ${pytest_cmd}${NC}"
    echo ""

    local rc=0
    if [[ -n "${OMNIA_LOG_FILE:-}" ]]; then
        set +e
        eval "$pytest_cmd" 2>&1 | tee -a "${OMNIA_LOG_FILE}"
        rc="${PIPESTATUS[0]}"
        set -e
    else
        set +e
        eval "$pytest_cmd"
        rc=$?
        set -e
    fi
    return $rc
}

# =============================================================================
case "$SCENARIO" in
    list|--list)
        echo -e "${BLUE}=================================================================${NC}"
        echo -e "${BLUE}  Available Scenarios${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""
        for name in $(get_scenarios); do
            scenario_dir="${FVT_DIR}/${name}"
            if [ -d "$scenario_dir" ]; then
                test_count=$(find "$scenario_dir" -name 'test_*.py' 2>/dev/null | wc -l)
                suites=$(find "$scenario_dir" -mindepth 1 -maxdepth 1 -type d -not -name '__pycache__' -printf '%f ' 2>/dev/null)
                echo -e "  ${GREEN}${name}${NC}  (${test_count} test files)"
                if [ -n "$suites" ]; then
                    echo -e "    suites: ${YELLOW}${suites}${NC}"
                fi
            else
                echo -e "  ${RED}${name}${NC}  (not found)"
            fi
        done
        echo ""
        exit 0
        ;;
    --config)
        echo -e "${RED}Batch config mode not yet implemented for build_stream.${NC}"
        exit 1
        ;;
    all)
        export REPORT_ID=$(date '+%Y%m%d%H%M%S')
        echo -e "${BLUE}=================================================================${NC}"
        echo -e "${BLUE}  Running ALL Scenarios: ${COMMAND}${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""
        total=0; pass_count=0; fail_count=0
        for name in $(get_scenarios); do
            total=$((total + 1))
            echo -e "${YELLOW}[${total}] ${name}${NC}"
            extra=""
            [[ -n "$SUITE" ]] && extra="$extra --suite $SUITE"
            [[ -n "$MARKER" ]] && extra="$extra --marker $MARKER"
            if "$0" "$name" "$COMMAND" $extra; then
                pass_count=$((pass_count + 1))
            else
                fail_count=$((fail_count + 1))
            fi
            echo ""
        done
        echo -e "${BLUE}=================================================================${NC}"
        echo -e "  Total: ${total}  ${GREEN}Passed: ${pass_count}${NC}  ${RED}Failed: ${fail_count}${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        [[ $fail_count -eq 0 ]] || exit 1
        exit 0
        ;;
    help|--help|-h|"")
        echo -e "${BLUE}=================================================================${NC}"
        echo -e "${BLUE}  Build Stream — Validation Runner${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""
        echo "Usage:"
        echo "  $0 <scenario> <command> [options]"
        echo "  $0 all <command> [options]"
        echo "  $0 list"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo "  deploy    Run the Ansible playbook only (live streaming output)"
        echo "  verify    Run verification tests only (no playbook execution)"
        echo "  test      Full flow: deploy playbook, then run verification"
        echo ""
        echo -e "${YELLOW}Options:${NC}"
        echo "  --suite <name>    Filter by subfolder (gitlab_install, health, etc.)"
        echo "  --marker <expr>   Filter by pytest marker expression"
        echo "  -v, --verbose     Increase pytest verbosity"
        echo "  --debug           Enable full debug output (pytest -vvs + debug env)"
        echo ""
        echo -e "${YELLOW}Scenarios:${NC}"
        echo "  gitlab_install       GitLab installation and infrastructure verification"
        echo "  gitlab_cleanup       GitLab cleanup verification"
        echo "  buildstream_cleanup  BuildStream domain cleanup verification"
        echo ""
        echo -e "${YELLOW}Markers:${NC}"
        echo "  sanity               Baseline must-pass tests (verify only)"
        echo "  regression           Regression tests (deploy + verify)"
        echo "  functional           Functional verification tests"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo ""
        echo "  # Verify GitLab installation"
        echo "  $0 gitlab_install verify --marker sanity"
        echo ""
        echo "  # Full GitLab install + verify"
        echo "  $0 gitlab_install test"
        echo ""
        echo "  # Verify only health checks"
        echo "  $0 gitlab_install verify --suite health"
        echo ""
        echo "  # Verify GitLab cleanup (after cleanup already ran)"
        echo "  $0 gitlab_cleanup verify --marker sanity"
        echo ""
        echo "  # Full regression: run cleanup playbook + verify"
        echo "  $0 gitlab_cleanup test --marker regression"
        echo ""
        echo "  # Verify BuildStream domain cleanup"
        echo "  $0 buildstream_cleanup verify --marker sanity"
        echo ""
        echo "  # Run all scenarios"
        echo "  $0 all test"
        echo ""
        exit 0
        ;;
esac

# =============================================================================
SCENARIO_DIR="${FVT_DIR}/${SCENARIO}"

if [[ ! -d "$SCENARIO_DIR" ]]; then
    echo -e "${RED}Error: Scenario '${SCENARIO}' not found in fvt/${NC}"
    echo ""
    echo -e "${YELLOW}Available scenarios:${NC}"
    get_scenarios | while read -r s; do echo "  $s"; done
    exit 1
fi

# Validate command
if ! echo " ${SUPPORTED_COMMANDS} " | grep -q " ${COMMAND} "; then
    echo -e "${RED}Error: Invalid command '${COMMAND}'${NC}"
    echo -e "${YELLOW}Supported: ${SUPPORTED_COMMANDS}${NC}"
    exit 1
fi

# Validate suite folder
if [[ -n "$SUITE" && ! -d "${SCENARIO_DIR}/${SUITE}" ]]; then
    echo -e "${YELLOW}Warning: Suite folder '${SUITE}' not found in ${SCENARIO_DIR}/${NC}"
    echo -e "${YELLOW}Available:${NC}"
    ls -d "${SCENARIO_DIR}"/*/ 2>/dev/null | xargs -I{} basename {} | while read -r d; do echo "  $d"; done
    exit 1
fi

# =============================================================================
if [[ -z "${REPORT_ID:-}" ]]; then
    export REPORT_ID=$(date '+%Y%m%d%H%M%S')
fi

export OMNIA_SUITE="${SUITE:-all}"
export OMNIA_MARKER="${MARKER:-}"
[[ -n "$DEBUG" ]] && export OMNIA_DEBUG="true"
LOG_DIR="${SCRIPT_DIR}/reports/logs"
mkdir -p "${LOG_DIR}"
export OMNIA_LOG_FILE="${LOG_DIR}/${SCENARIO}_${COMMAND}_${REPORT_ID}.log"

# =============================================================================
echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}  Build Stream — Validation Runner${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo -e "  Scenario  : ${GREEN}${SCENARIO}${NC}"
echo -e "  Command   : ${GREEN}${COMMAND}${NC}"
[[ -n "$SUITE" ]]       && echo -e "  Suite     : ${GREEN}${SUITE}${NC}"
[[ -n "$MARKER" ]]      && echo -e "  Marker    : ${GREEN}${MARKER}${NC}"
[[ -n "$DEBUG" ]] && echo -e "  Debug     : ${YELLOW}yes${NC}"
echo -e "  Report ID : ${GREEN}${REPORT_ID}${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo ""

# =============================================================================
case "$COMMAND" in

    deploy)
        export OMNIA_COMMAND_TYPE="deploy"
        marker_cmd="-m deploy"
        [[ -n "$MARKER" ]] && marker_cmd="${marker_cmd} --marker ${MARKER}"
        run_pytest \
            "${SCENARIO_DIR}" \
            "${marker_cmd}" \
            "Running playbook deployment for ${SCENARIO}"

        echo ""
        echo -e "${GREEN}Deployment completed.${NC}"
        ;;

    verify)
        export OMNIA_COMMAND_TYPE="verify"
        test_path=$(build_test_path "${SCENARIO_DIR}")
        extra_args=$(build_pytest_args "yes")

        run_pytest \
            "${test_path}" \
            "${extra_args}" \
            "Running verification tests for ${SCENARIO}"

        echo ""
        echo -e "${GREEN}Verification completed.${NC}"
        ;;

    test)
        FAILED=0

        export OMNIA_SUPPRESS_SUMMARY="true"
        export OMNIA_RESULTS_FILE=$(mktemp /tmp/omnia_results_XXXXXX.json)

        # Step 1: Deploy
        export OMNIA_COMMAND_TYPE="deploy"
        echo -e "${YELLOW}=================================================================${NC}"
        echo -e "${YELLOW}  Step 1/2: Deploy${NC}"
        echo -e "${YELLOW}=================================================================${NC}"
        echo ""

        deploy_args="-m deploy"
        [[ -n "$MARKER" ]] && deploy_args="${deploy_args} --marker ${MARKER}"
        if run_pytest "${SCENARIO_DIR}" "${deploy_args}" "Running playbook deployment"; then
            echo -e "${GREEN}Deployment succeeded${NC}"
        else
            echo -e "${RED}Deployment failed${NC}"
            FAILED=1
        fi
        echo ""

        # Step 2: Verify (only if deploy succeeded)
        if [[ $FAILED -eq 0 ]]; then
            export OMNIA_COMMAND_TYPE="verify"
            echo -e "${YELLOW}=================================================================${NC}"
            echo -e "${YELLOW}  Step 2/2: Verify${NC}"
            echo -e "${YELLOW}=================================================================${NC}"
            echo ""

            test_path=$(build_test_path "${SCENARIO_DIR}")
            verify_args=$(build_pytest_args "yes")

            if run_pytest "${test_path}" "${verify_args}" "Running verification tests"; then
                echo -e "${GREEN}Verification succeeded${NC}"
            else
                echo -e "${RED}Verification failed${NC}"
                FAILED=1
            fi
        else
            echo -e "${YELLOW}Skipping verification — deployment failed${NC}"
        fi

        print_combined_summary

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
