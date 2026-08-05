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
# image_build_manager — Validation Runner
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
#   --suite <name>    Filter by subfolder (container, s3, registry, etc.)
#   --marker <expr>   Filter by pytest marker (x86_64, sanity, etc.)
#   -v, --verbose     Increase verbosity
#
# Scenarios:
#   image_build_manager     Full end-to-end (deploy without tags + verify)
#   validate                Validate tag tests
#   prepare                 Prepare tag tests
#   build                   Build tag tests
#   cleanup                 Cleanup tag tests
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

    # Custom --marker option for arch/quality filtering
    if [[ -n "$MARKER" ]]; then
        args="${args} --marker ${MARKER}"
    fi

    # Native -m for deploy exclusion
    if [[ "$exclude_deploy" == "yes" ]]; then
        args="${args} -m 'not deploy'"
    fi

    echo "$args"
}

print_combined_summary() {
    # Print a combined summary table from the OMNIA_RESULTS_FILE JSON
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

    # Tee output to log file for report if OMNIA_LOG_FILE is set
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

    # Read global overrides (dataset, sync_input, sync_output)
    local global_dataset global_sync_input global_sync_output
    eval "$(python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
ds = cfg.get('dataset_override', '')
si = cfg.get('sync_input_override', '')
so = cfg.get('sync_output_override', '')
print(f'global_dataset={ds}')
print(f'global_sync_input={str(si).lower() if si != \"\" else \"\"}')
print(f'global_sync_output={str(so).lower() if so != \"\" else \"\"}')
")"

    for name in $scenario_names; do
        local run_flag marker_cfg suite_cfg dataset_cfg sync_input_cfg sync_output_cfg
        eval "$(python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
sc = cfg.get('scenarios', {}).get('${name}', {})
print(f'run_flag={str(sc.get(\"run\", False)).lower()}')
print(f'marker_cfg={sc.get(\"marker\", \"\")}')
print(f'suite_cfg={sc.get(\"suite\", \"\")}')
print(f'command_cfg={sc.get(\"command\", \"test\")}')
print(f'dataset_cfg={sc.get(\"dataset\", \"\")}')
print(f'sync_input_cfg={str(sc.get(\"sync_input\", \"\")).lower()}')
print(f'sync_output_cfg={str(sc.get(\"sync_output\", \"\")).lower()}')
")"
        total=$((total + 1))
        if [[ "$run_flag" != "true" ]]; then
            echo -e "  ${YELLOW}SKIP${NC}  ${name}"
            skipped=$((skipped + 1))
            continue
        fi

        # Resolve dataset: global override > per-scenario > test_config.yml default
        local effective_dataset="${global_dataset:-${dataset_cfg}}"
        local effective_sync_input="${global_sync_input:-${sync_input_cfg}}"
        local effective_sync_output="${global_sync_output:-${sync_output_cfg}}"

        local dataset_info=""
        [[ -n "$effective_dataset" ]] && dataset_info=", dataset=${effective_dataset}"
        echo -e "  ${CYAN}RUN${NC}   ${name} (command=${command_cfg:-test}, marker=${marker_cfg:-none}, suite=${suite_cfg:-all}${dataset_info})"

        local extra_args=""
        [[ -n "$marker_cfg" ]] && extra_args="$extra_args --marker $marker_cfg"
        [[ -n "$suite_cfg" ]] && extra_args="$extra_args --suite $suite_cfg"

        # Pass dataset/sync overrides as environment variables
        local -a env_vars=()
        [[ -n "$effective_dataset" ]] && env_vars+=("OMNIA_DATASET_OVERRIDE=${effective_dataset}")
        [[ -n "$effective_sync_input" ]] && env_vars+=("OMNIA_SYNC_INPUT_OVERRIDE=${effective_sync_input}")
        [[ -n "$effective_sync_output" ]] && env_vars+=("OMNIA_SYNC_OUTPUT_OVERRIDE=${effective_sync_output}")

        if env "${env_vars[@]}" "$0" "$name" "${command_cfg:-test}" $extra_args; then
            echo -e "  ${GREEN}PASS${NC}  ${name}"
            passed=$((passed + 1))
        else
            echo -e "  ${RED}FAIL${NC}  ${name}"
            failed=$((failed + 1))
        fi
    done

    # Combined test-level summary across all scenarios
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
        run_config_mode
        exit 0
        ;;
    --completion)
        # Output a shell snippet users can eval to get tab completion
        # without running setup_env.sh. Usage: eval "$(./run_validation.sh --completion)"
        cat << COMPLETION_EOF
run_validation() { "${SCRIPT_DIR}/run_validation.sh" "\$@"; }
_run_validation_completions() {
    local cur prev; cur="\${COMP_WORDS[\$COMP_CWORD]}"; prev="\${COMP_WORDS[\$COMP_CWORD-1]}"
    local fvt_dir="${SCRIPT_DIR}/fvt"
    local scenarios=""; if [ -d "\${fvt_dir}" ]; then for d in "\${fvt_dir}"/*/; do [ -d "\$d" ] || continue; local n; n="\$(basename "\$d")"; [ "\$n" = "__pycache__" ] && continue; scenarios="\${scenarios} \${n}"; done; fi
    local commands="deploy verify test"; local special="all list help --config --help"; local options="--suite --marker -v --verbose --debug"; local markers="sanity x86_64 aarch64 functional regression deploy"
    case "\$COMP_CWORD" in
        1) COMPREPLY=( \$(compgen -W "\${scenarios} \${special}" -- "\$cur") ) ;;
        2) case "\$prev" in list|help|--help|-h|--config) COMPREPLY=() ;; *) COMPREPLY=( \$(compgen -W "\${commands}" -- "\$cur") ) ;; esac ;;
        *) case "\$prev" in --suite) local sc="\${COMP_WORDS[1]}"; local suites=""; if [ -d "\${fvt_dir}/\${sc}" ]; then for d in "\${fvt_dir}/\${sc}"/*/; do [ -d "\$d" ] || continue; local n; n="\$(basename "\$d")"; [ "\$n" = "__pycache__" ] && continue; suites="\${suites} \${n}"; done; fi; COMPREPLY=( \$(compgen -W "\${suites}" -- "\$cur") ) ;; --marker) COMPREPLY=( \$(compgen -W "\${markers}" -- "\$cur") ) ;; *) COMPREPLY=( \$(compgen -W "\${options}" -- "\$cur") ) ;; esac ;; esac
}
complete -F _run_validation_completions run_validation
COMPLETION_EOF
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
        echo -e "${BLUE}  Image Build Manager — Validation Runner${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""
        echo "Usage:"
        echo "  $0 <scenario> <command> [options]"
        echo "  $0 all <command> [options]"
        echo "  $0 --config"
        echo "  $0 list"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo "  deploy    Run the Ansible playbook only (live streaming output)"
        echo "  verify    Run verification tests only (no playbook execution)"
        echo "  test      Full flow: deploy playbook, then run verification"
        echo ""
        echo -e "${YELLOW}Options:${NC}"
        echo "  --suite <name>    Filter by subfolder (container, s3, registry, etc.)"
        echo "  --marker <expr>   Filter by pytest marker expression"
        echo "  -v, --verbose     Increase pytest verbosity"
        echo "  --debug           Enable full debug output (pytest -vvs + debug env)"
        echo ""
        echo -e "${YELLOW}Scenarios:${NC}"
        echo "  image_build_manager    Full end-to-end (deploy without tags + verify)"
        echo "  validate               Deploy --tags validate + verify inputs"
        echo "  prepare                Deploy --tags prepare + verify infrastructure"
        echo "  build                  Deploy --tags build + verify images"
        echo "  cleanup                Deploy --tags cleanup + verify removal"
        echo ""
        echo -e "${YELLOW}Markers:${NC}"
        echo "  sanity               Baseline must-pass tests"
        echo "  x86_64               x86_64 architecture tests"
        echo "  aarch64              aarch64 architecture tests"
        echo "  functional           Functional verification tests"
        echo ""
        echo -e "${YELLOW}Marker Expressions:${NC}"
        echo "  sanity               Single marker"
        echo "  x86_64,aarch64       OR — tests with either marker"
        echo "  x86_64+sanity        AND — tests with both markers"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo ""
        echo "  # Verify all sanity tests on an existing deployment"
        echo "  $0 image_build_manager verify --marker sanity"
        echo ""
        echo "  # Verify only x86_64 tests"
        echo "  $0 image_build_manager verify --marker x86_64"
        echo ""
        echo "  # Verify both architectures (OR)"
        echo "  $0 image_build_manager verify --marker x86_64,aarch64"
        echo ""
        echo "  # Verify only x86_64 sanity tests (AND)"
        echo "  $0 image_build_manager verify --marker x86_64+sanity"
        echo ""
        echo "  # Verify only container tests"
        echo "  $0 image_build_manager verify --suite container"
        echo ""
        echo "  # Deploy prepare tag and verify"
        echo "  $0 prepare test"
        echo ""
        echo "  # Deploy build tag, verify x86_64 images only"
        echo "  $0 build test --marker x86_64"
        echo ""
        echo "  # Run cleanup (deploy + verify removal)"
        echo "  $0 cleanup test"
        echo ""
        echo "  # Deploy only (no verification)"
        echo "  $0 prepare deploy"
        echo ""
        echo "  # Run all scenarios with x86_64 marker"
        echo "  $0 all test --marker x86_64"
        echo ""
        echo "  # Batch run from test_run_config.yml"
        echo "  $0 --config"
        echo ""
        echo -e "${YELLOW}Typical Workflow:${NC}"
        echo "  $0 cleanup test                          # 1. Clean previous state"
        echo "  $0 validate test                          # 2. Validate inputs"
        echo "  $0 prepare test                          # 3. Prepare infrastructure"
        echo "  $0 build test --marker x86_64             # 4. Build images"
        echo "  $0 image_build_manager verify --marker sanity  # 5. Full verification"
        echo ""
        echo -e "${YELLOW}Configuration:${NC}"
        echo "  test_config.yml      Target server, sync, report settings"
        echo "  test_creds.yml       SSH credentials (Ansible Vault encrypted)"
        echo "  test_run_config.yml  Batch suite definitions for --config mode"
        echo ""
        echo -e "${YELLOW}Tab Completion:${NC}"
        echo "  eval \"\$($0 --completion)\""
        echo ""
        echo -e "${YELLOW}Reports:${NC}"
        echo "  Reports are generated in reports/ after each run."
        echo "  View: python3 -m http.server 8899 --directory reports/"
        echo ""
        exit 0
        ;;
esac

# =============================================================================
# Validate scenario
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
# Generate report ID
# =============================================================================
if [[ -z "${REPORT_ID:-}" ]]; then
    export REPORT_ID=$(date '+%Y%m%d%H%M%S')
fi

# Export vars for TestReport in conftest.py
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
echo -e "${BLUE}  Image Build Manager — Validation Runner${NC}"
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
# Execute based on command
# =============================================================================
case "$COMMAND" in

    # -------------------------------------------------------------------------
    # DEPLOY: Run playbook only (tests with @pytest.mark.deploy)
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # VERIFY: Run verification tests only (exclude @deploy, apply filters)
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # TEST: Deploy + Verify (full flow)
    # -------------------------------------------------------------------------
    test)
        FAILED=0

        # Suppress individual pytest summaries; print combined at end
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

        # Combined summary at the very end
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
