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
# omnia main — Validation Runner
# =============================================================================
# Usage:
#   ./run_validation.sh <scenario> <command> [options]
#   ./run_validation.sh all <command> [options]
#   ./run_validation.sh --config
#   ./run_validation.sh list
#
# Commands:
#   deploy    Run the script/playbook only (tests marked @deploy)
#   verify    Run verification tests only (exclude @deploy)
#   test      Deploy + Verify (full flow)
#
# Options:
#   --suite <name>    Filter by subfolder (environment, venv, commands, etc.)
#   --marker <expr>   Filter by pytest marker (sanity, functional, etc.)
#   -v, --verbose     Increase verbosity
#
# Scenarios:
#   setup      omnia.sh --setup-venv tests
#   init       omnia.sh --init tests
#   cli        CLI argument parsing tests
#   execution  Actual omnia.sh operations (setup, init, run --tags, cleanup*)
#              * cleanup skipped if running from omnia production venv
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

# Activate venv if exists, otherwise use system python
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
# Helper functions
# =============================================================================
get_scenarios() {
    for dir in "$FVT_DIR"/*/; do
        name=$(basename "$dir")
        [[ "$name" == __pycache__ ]] && continue
        echo "$name"
    done
    # NFT lives in nft/ (sibling of fvt/)
    if [ -d "$NFT_DIR" ]; then
        echo "nft"
    fi
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

    # pytest exit code 5 = no tests collected (all skipped/deselected) — not a failure
    if [[ $rc -eq 5 ]]; then
        return 0
    fi
    return $rc
}

# =============================================================================
# Config mode — run from test_run_config.yml
# =============================================================================
run_config_mode() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo -e "${RED}Error: Config file not found: ${CONFIG_FILE}${NC}"
        exit 1
    fi

    export REPORT_ID=$(date '+%Y%m%d%H%M%S')
    export OMNIA_SUPPRESS_SUMMARY="true"
    export OMNIA_RESULTS_FILE=$(mktemp /tmp/omnia_results_XXXXXX.json)

    echo -e "${BLUE}=================================================================${NC}"
    echo -e "${BLUE}  Batch Execution from test_run_config.yml${NC}"
    echo -e "${BLUE}  Report ID : ${REPORT_ID}${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    echo ""

    local total=0 passed=0 failed=0 skipped=0
    local scenario_names
    scenario_names=$(python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
for name in cfg.get('scenarios', {}):
    print(name)
")

    for name in $scenario_names; do
        local run_flag marker_cfg suite_cfg
        eval "$(python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
sc = cfg.get('scenarios', {}).get('${name}', {})
print(f'run_flag={str(sc.get(\"run\", False)).lower()}')
print(f'marker_cfg={sc.get(\"marker\", \"\")}')
print(f'suite_cfg={sc.get(\"suite\", \"\")}')
")"
        total=$((total + 1))
        if [[ "$run_flag" != "true" ]]; then
            echo -e "  ${YELLOW}SKIP${NC}  ${name}"
            skipped=$((skipped + 1))
            continue
        fi

        echo -e "  ${CYAN}RUN${NC}   ${name} (marker=${marker_cfg:-none}, suite=${suite_cfg:-all})"

        local extra_args=""
        [[ -n "$marker_cfg" ]] && extra_args="$extra_args --marker $marker_cfg"
        [[ -n "$suite_cfg" ]] && extra_args="$extra_args --suite $suite_cfg"

        if "$0" "$name" test $extra_args; then
            echo -e "  ${GREEN}PASS${NC}  ${name}"
            passed=$((passed + 1))
        else
            echo -e "  ${RED}FAIL${NC}  ${name}"
            failed=$((failed + 1))
        fi
    done

    print_combined_summary

    echo ""
    echo -e "${BLUE}=================================================================${NC}"
    echo -e "  Scenarios: ${total}  ${GREEN}Passed: ${passed}${NC}  ${RED}Failed: ${failed}${NC}  ${YELLOW}Skipped: ${skipped}${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    [[ $failed -eq 0 ]] || exit 1
}

# =============================================================================
# Handle special commands
# =============================================================================
case "$SCENARIO" in
    list|--list)
        echo -e "${BLUE}=================================================================${NC}"
        echo -e "${BLUE}  Available Scenarios${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""
        for name in $(get_scenarios); do
            if [[ "$name" == "nft" ]]; then
                scenario_dir="${NFT_DIR}"
            else
                scenario_dir="${FVT_DIR}/${name}"
            fi
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
        run_config_mode
        exit 0
        ;;
    --completion)
        echo "Tab completion is automatically registered in .venv/bin/activate."
        echo "Run: source .venv/bin/activate"
        exit 0
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
        echo -e "${BLUE}  Omnia Main — Validation Runner${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""
        echo -e "  Tests for ${GREEN}omnia.sh${NC} (setup, init, CLI args) and ${GREEN}omnia-cli${NC} diagnostics."
        echo -e "  Module: ${CYAN}main${NC}   FVT: ${CYAN}test/main/fvt/${NC}   NFT: ${CYAN}test/main/nft/${NC}"
        echo ""
        echo -e "${YELLOW}USAGE${NC}"
        echo "  $0 <scenario> <command> [options]"
        echo "  $0 all <command>                  Run all scenarios"
        echo "  $0 list                           List available scenarios"
        echo "  $0 --config                       Batch run from test_run_config.yml"
        echo ""
        echo -e "${YELLOW}COMMANDS${NC}"
        echo "  deploy    Execute the omnia.sh command (tests marked @deploy)"
        echo "  verify    Run verification tests only (no script execution)"
        echo "  test      Deploy + verify (full flow)"
        echo ""
        echo -e "${YELLOW}OPTIONS${NC}"
        echo "  --suite <name>    Run only tests in a subfolder (environment, venv, etc.)"
        echo "  --marker <expr>   Filter by pytest marker (sanity, functional, deploy)"
        echo "  -v, --verbose     Increase pytest verbosity"
        echo "  --debug           Full debug output (pytest -vvs)"
        echo ""
        echo -e "${YELLOW}SCENARIOS (FVT)${NC}"
        echo "  setup      omnia.sh --setup-venv: env install, venv, dirs, env validation"
        echo "  init       omnia.sh --init: domain-init.sh scripts, input staging (7 domains)"
        echo "  cli        omnia.sh argument parsing: help flags, error handling, tags, --skip-catalog"
        echo "  omnia_cli  omnia-cli diagnostics: status, check, domain cmds, logs, help, errors"
        echo "  execution  Actual execution: setup, init, run --tags, cleanup (smart skip)"
        echo ""
        echo -e "${YELLOW}SCENARIOS (NFT)${NC}"
        echo "  nft        Performance, idempotency, file permissions, CLI performance"
        echo ""
        echo -e "${YELLOW}MARKERS${NC}"
        echo "  sanity       Baseline must-pass tests"
        echo "  functional   Functional verification tests"
        echo "  deploy       Script execution tests (omnia.sh actually runs)"
        echo ""
        echo -e "${YELLOW}QUICK START${NC}"
        echo ""
        echo "  # Verify everything on an existing installation (no deploy):"
        echo "  $0 all verify"
        echo ""
        echo "  # Full test: deploy setup + verify results:"
        echo "  $0 setup test"
        echo ""
        echo "  # Just check CLI help output:"
        echo "  $0 cli verify"
        echo ""
        echo -e "${YELLOW}TYPICAL WORKFLOW${NC}"
        echo "  $0 setup test                    # 1. Install env + venv + verify"
        echo "  $0 init test                     # 2. Stage domain input files + verify"
        echo "  $0 cli verify                    # 3. Verify CLI argument handling"
        echo "  $0 omnia_cli verify              # 4. Verify omnia-cli diagnostics"
        echo "  $0 execution test                # 5. Full lifecycle (setup/init/run/cleanup)"
        echo "  $0 nft test                      # 6. Performance + idempotency + permissions"
        echo "  $0 all verify                    # Or: verify everything at once"
        echo ""
        echo -e "${YELLOW}CONFIGURATION${NC}"
        echo "  test_config.yml      Target server settings (clone_path, oim_server_ip)"
        echo "  test_run_config.yml  Batch suite definitions for --config mode"
        echo ""
        exit 0
        ;;
esac

# =============================================================================
# Validate scenario
# =============================================================================
if [[ "$SCENARIO" == "nft" ]]; then
    SCENARIO_DIR="${NFT_DIR}"
else
    SCENARIO_DIR="${FVT_DIR}/${SCENARIO}"
fi

if [[ ! -d "$SCENARIO_DIR" ]]; then
    echo -e "${RED}Error: Scenario '${SCENARIO}' not found${NC}"
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
# Generate report ID
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
# Display banner
# =============================================================================
echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}  Omnia Main — Validation Runner${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo -e "  Scenario  : ${GREEN}${SCENARIO}${NC}"
echo -e "  Command   : ${GREEN}${COMMAND}${NC}"
[[ -n "$SUITE" ]]  && echo -e "  Suite     : ${GREEN}${SUITE}${NC}"
[[ -n "$MARKER" ]] && echo -e "  Marker    : ${GREEN}${MARKER}${NC}"
[[ -n "$DEBUG" ]]  && echo -e "  Debug     : ${YELLOW}yes${NC}"
echo -e "  Report ID : ${GREEN}${REPORT_ID}${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo ""

# =============================================================================
# Execute based on command
# =============================================================================
case "$COMMAND" in

    deploy)
        export OMNIA_COMMAND_TYPE="deploy"
        marker_cmd="-m deploy"
        [[ -n "$MARKER" ]] && marker_cmd="${marker_cmd} --marker ${MARKER}"
        run_pytest \
            "${SCENARIO_DIR}" \
            "${marker_cmd}" \
            "Running deployment for ${SCENARIO}"

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

        # Check if scenario has deploy tests (grep for @pytest.mark.deploy)
        has_deploy=$(grep -rl '@pytest\.mark\.deploy\|pytest\.mark\.deploy' "${SCENARIO_DIR}" --include='*.py' 2>/dev/null | head -1 || true)

        # Step 1: Deploy (skip if no deploy-marked tests in this scenario)
        if [[ -n "$has_deploy" ]]; then
            export OMNIA_COMMAND_TYPE="deploy"
            echo -e "${YELLOW}=================================================================${NC}"
            echo -e "${YELLOW}  Step 1/2: Deploy${NC}"
            echo -e "${YELLOW}=================================================================${NC}"
            echo ""

            deploy_args="-m deploy"
            [[ -n "$MARKER" ]] && deploy_args="${deploy_args} --marker ${MARKER}"
            if run_pytest "${SCENARIO_DIR}" "${deploy_args}" "Running deployment"; then
                echo -e "${GREEN}Deployment succeeded${NC}"
            else
                echo -e "${RED}Deployment failed${NC}"
                FAILED=1
            fi
            echo ""
        else
            echo -e "${YELLOW}No deploy tests in ${SCENARIO} — skipping deploy step${NC}"
            echo ""
        fi

        # Step 2: Verify (only if deploy succeeded or was skipped)
        if [[ $FAILED -eq 0 ]]; then
            export OMNIA_COMMAND_TYPE="verify"
            echo -e "${YELLOW}=================================================================${NC}"
            if [[ -n "$has_deploy" ]]; then
                echo -e "${YELLOW}  Step 2/2: Verify${NC}"
            else
                echo -e "${YELLOW}  Running: Verify${NC}"
            fi
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
