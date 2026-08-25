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
#   ./run_validation.sh image_build_manager <command> [options]
#   ./run_validation.sh image_build_manager <tag> <command> [options]
#   ./run_validation.sh image_build_manager list
#   ./run_validation.sh --completion
#
# Commands:
#   exec      Run the Ansible playbook only (no verification)
#   verify    Run verification tests only (no playbook execution)
#   test      exec + verify (full flow)
#
# When a <tag> is provided (validate, prepare, build, cleanup, cleanup_images):
#   - exec    runs the playbook with --tags <tag>
#   - verify  runs only tests in fvt/<tag>/
#   - test    exec + verify for that tag
#
# When NO tag is provided:
#   - exec    runs the playbook without tags (full stack)
#   - verify  runs ALL tests except cleanup/cleanup_images
#   - test    exec (full stack) + verify ALL
#
# Options:
#   --suite <name>    Filter by subfolder (container, s3, registry, naming)
#   --marker <expr>   Filter by pytest marker expression
#                       Single: --marker sanity
#                       AND:    --marker x86_64+sanity   (BOTH markers)
#                       OR:     --marker x86_64,aarch64  (EITHER marker)
#   -v, --verbose     Increase verbosity
#   --debug           Full debug output
#
# FVT Tags (match ansible playbook tags):
#   validate       Validate inputs + config
#   prepare        Build infrastructure setup
#   build          Build OS images
#   cleanup        Cleanup build artifacts
#   cleanup_images Delete S3 + registry images
#
# Tab Completion:
#   eval "$(./run_validation.sh --completion)"
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FVT_DIR="${SCRIPT_DIR}/fvt"
NFT_DIR="${SCRIPT_DIR}/nft"
CONFIG_FILE="${SCRIPT_DIR}/test_run_config.yml"
DOMAIN_NAME="image_build_manager"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SUPPORTED_COMMANDS="exec verify test"
SUPPORTED_TAGS="precheck validate prepare build cleanup cleanup_images"
# Destructive tags excluded from 'verify all' — must be run explicitly
EXCLUDE_FROM_ALL="cleanup cleanup_images"

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
if [[ $# -lt 1 ]]; then
    set -- "help"
fi

ARG1="${1:-help}"
shift || true

# Handle special cases first
case "$ARG1" in
    help|--help|-h)
        TAG=""
        COMMAND="help"
        ;;
    --completion)
        TAG=""
        COMMAND="completion"
        ;;
    --config)
        TAG=""
        COMMAND="config"
        ;;
    nft)
        TAG=""
        COMMAND="nft"
        ;;
    *)
        # First arg should be domain name
        if [[ "$ARG1" != "$DOMAIN_NAME" ]]; then
            echo -e "${RED}Error: Expected '${DOMAIN_NAME}' as first argument, got '${ARG1}'${NC}"
            echo -e "${YELLOW}Usage: $0 ${DOMAIN_NAME} [tag] <command> [options]${NC}"
            exit 1
        fi

        # Next arg is either a tag or a command
        ARG2="${1:-help}"
        shift || true

        if echo " ${SUPPORTED_TAGS} " | grep -q " ${ARG2} "; then
            # It's a tag — next arg is the command
            TAG="$ARG2"
            COMMAND="${1:-verify}"
            shift || true
        elif echo " ${SUPPORTED_COMMANDS} list help " | grep -q " ${ARG2} "; then
            # It's a command — no tag
            TAG=""
            COMMAND="$ARG2"
        else
            echo -e "${RED}Error: Unknown argument '${ARG2}'${NC}"
            echo -e "${YELLOW}Expected a tag (${SUPPORTED_TAGS}) or command (${SUPPORTED_COMMANDS})${NC}"
            exit 1
        fi
        ;;
esac

# Parse remaining options
SUITE=""
MARKER=""
VERBOSE=""
DEBUG=""

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

# =============================================================================
# Helper functions
# =============================================================================
get_tags() {
    for dir in "$FVT_DIR"/*/; do
        name=$(basename "$dir")
        [[ "$name" == __pycache__ ]] && continue
        echo "$name"
    done
}

build_verify_dirs() {
    # Build the list of test directories to run
    # If TAG is set, use only that tag's directory
    # If TAG is empty, use ALL directories except excluded ones
    if [[ -n "$TAG" ]]; then
        echo "${FVT_DIR}/${TAG}"
    else
        local dirs=""
        for dir in "$FVT_DIR"/*/; do
            name=$(basename "$dir")
            [[ "$name" == __pycache__ ]] && continue
            if echo " ${EXCLUDE_FROM_ALL} " | grep -q " ${name} "; then
                continue
            fi
            dirs="${dirs} ${dir}"
        done
        echo "$dirs"
    fi
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
# Handle special commands
# =============================================================================
case "$COMMAND" in

    # -------------------------------------------------------------------------
    # LIST: Show available tags and test counts
    # -------------------------------------------------------------------------
    list|help)
        echo -e "${BLUE}=================================================================${NC}"
        echo -e "${BLUE}  Image Build Manager — Validation Runner${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""

        if [[ "$COMMAND" == "list" ]]; then
            echo -e "${YELLOW}Available tags:${NC}"
            for name in $(get_tags); do
                tag_dir="${FVT_DIR}/${name}"
                test_count=$(find "$tag_dir" -name 'test_*.py' 2>/dev/null | wc -l)
                suites=$(find "$tag_dir" -mindepth 1 -maxdepth 1 -type d -not -name '__pycache__' -printf '%f ' 2>/dev/null)
                echo -e "  ${GREEN}${name}${NC}  (${test_count} test files)"
                if [ -n "$suites" ]; then
                    echo -e "    suites: ${YELLOW}${suites}${NC}"
                fi
            done
            echo ""
            if [ -d "$NFT_DIR" ]; then
                nft_count=$(find "$NFT_DIR" -name 'test_*.py' 2>/dev/null | wc -l)
                echo -e "${YELLOW}NFT:${NC}"
                echo -e "  ${GREEN}nft${NC}  (${nft_count} test files — performance, idempotency)"
            fi
            echo ""
            exit 0
        fi

        echo -e "  End-to-end tests for the ${GREEN}${DOMAIN_NAME}${NC} domain."
        echo ""
        echo -e "${YELLOW}USAGE${NC}"
        echo "  $0 ${DOMAIN_NAME} <command> [options]"
        echo "  $0 ${DOMAIN_NAME} <tag> <command> [options]"
        echo "  $0 ${DOMAIN_NAME} list"
        echo "  $0 --config"
        echo "  $0 --completion"
        echo ""
        echo -e "${YELLOW}COMMANDS${NC}"
        echo "  exec       Run the Ansible playbook only (no verification tests)"
        echo "  verify     Run pytest verification tests only (no playbook execution)"
        echo "  test       exec + verify (full flow: deploy then verify)"
        echo ""
        echo "  When a <tag> is provided:"
        echo "    exec     runs:  ansible-playbook image_build_manager.yml --tags <tag>"
        echo "    verify   runs:  pytest tests under fvt/<tag>/"
        echo "    test     runs:  exec + verify for that tag"
        echo ""
        echo "  When NO tag is provided:"
        echo "    exec     runs:  ansible-playbook image_build_manager.yml (no tags, full stack)"
        echo "    verify   runs:  ALL tests except cleanup/cleanup_images"
        echo "    test     runs:  exec (full stack) + verify ALL"
        echo ""
        echo -e "${YELLOW}TAGS${NC} (match Ansible --tags values)"
        echo "  precheck       Environment prechecks (connectivity, env vars)"
        echo "  validate       Validate inputs + config files"
        echo "  prepare        Build infrastructure setup (MinIO, registry)"
        echo "  build          Build OS images (S3, registry, packages)"
        echo "  cleanup        Cleanup build artifacts (containers, services)"
        echo "  cleanup_images Delete S3 + registry images only"
        echo ""
        echo -e "${YELLOW}OPTIONS${NC}"
        echo "  --suite <name>    Run only tests in a subfolder (container, s3, registry, naming)"
        echo "  --marker <expr>   Filter by pytest marker expression"
        echo "  -v, --verbose     Increase pytest verbosity"
        echo "  --debug           Full debug output (-vvs)"
        echo ""
        echo -e "${YELLOW}MARKERS${NC}"
        echo "  sanity       Baseline must-pass tests"
        echo "  x86_64       x86_64 architecture tests"
        echo "  aarch64      aarch64 architecture tests"
        echo "  functional   Functional verification tests"
        echo "  deploy       Playbook execution tests"
        echo ""
        echo -e "${YELLOW}MARKER EXPRESSIONS${NC}"
        echo "  Single:   --marker sanity                  Tests with @pytest.mark.sanity"
        echo "  AND:      --marker x86_64+sanity           Tests with BOTH markers"
        echo "  OR:       --marker x86_64,aarch64          Tests with EITHER marker"
        echo ""
        echo -e "${YELLOW}EXAMPLES${NC}"
        echo "  $0 ${DOMAIN_NAME} verify                              # All tests except cleanup"
        echo "  $0 ${DOMAIN_NAME} verify --marker sanity               # All sanity tests"
        echo "  $0 ${DOMAIN_NAME} exec                                 # Run playbook (full stack)"
        echo "  $0 ${DOMAIN_NAME} build exec                           # Run playbook --tags build"
        echo "  $0 ${DOMAIN_NAME} build verify                         # Verify build only"
        echo "  $0 ${DOMAIN_NAME} build verify --suite registry        # Build registry tests only"
        echo "  $0 ${DOMAIN_NAME} build verify --suite naming          # Build naming tests only"
        echo "  $0 ${DOMAIN_NAME} build test --marker x86_64           # Exec + verify x86_64"
        echo "  $0 ${DOMAIN_NAME} build test --marker x86_64+sanity    # Exec + verify x86_64 AND sanity"
        echo "  $0 ${DOMAIN_NAME} build test --marker x86_64,aarch64   # Exec + verify x86_64 OR aarch64"
        echo "  $0 ${DOMAIN_NAME} prepare test                         # Exec prepare + verify"
        echo "  $0 ${DOMAIN_NAME} cleanup test                         # Run cleanup + verify"
        echo "  $0 ${DOMAIN_NAME} list                                 # Show tags + test counts"
        echo ""
        echo -e "${YELLOW}TYPICAL WORKFLOW${NC}"
        echo "  $0 ${DOMAIN_NAME} cleanup test                      # 1. Clean previous state"
        echo "  $0 ${DOMAIN_NAME} validate test                     # 2. Validate inputs"
        echo "  $0 ${DOMAIN_NAME} prepare test                      # 3. Prepare infrastructure"
        echo "  $0 ${DOMAIN_NAME} build test --marker x86_64        # 4. Build + verify x86_64"
        echo "  $0 ${DOMAIN_NAME} verify --marker sanity             # 5. Full sanity verification"
        echo ""
        echo -e "${YELLOW}NFT (NON-FUNCTIONAL TESTS)${NC}"
        echo "  $0 nft test                        Run all NFT tests"
        echo ""
        echo -e "${YELLOW}CONFIG-DRIVEN EXECUTION${NC}"
        echo "  $0 --config                        Run scenarios from test_run_config.yml"
        echo ""
        echo -e "${YELLOW}TAB COMPLETION${NC}"
        echo "  eval \"\$($0 --completion)\""
        echo ""
        exit 0
        ;;

    # -------------------------------------------------------------------------
    # COMPLETION: Output bash completion function
    # -------------------------------------------------------------------------
    completion)
        cat << COMPLETION_EOF
run_validation() { "${SCRIPT_DIR}/run_validation.sh" "\$@"; }
_run_validation_completions() {
    local cur prev pprev
    cur="\${COMP_WORDS[\$COMP_CWORD]}"
    prev="\${COMP_WORDS[\$COMP_CWORD-1]}"
    pprev="\${COMP_WORDS[\$COMP_CWORD-2]:-}"
    local domain="${DOMAIN_NAME}"
    local tags="${SUPPORTED_TAGS}"
    local commands="exec verify test list help"
    local options="--suite --marker -v --verbose --debug"
    local markers="sanity x86_64 aarch64 functional deploy"
    local fvt_dir="${FVT_DIR}"
    case "\$COMP_CWORD" in
        1) COMPREPLY=( \$(compgen -W "\${domain} nft" -- "\$cur") ) ;;
        2) COMPREPLY=( \$(compgen -W "\${tags} \${commands}" -- "\$cur") ) ;;
        3)
            if echo " \${tags} " | grep -q " \${prev} "; then
                COMPREPLY=( \$(compgen -W "\${commands}" -- "\$cur") )
            else
                COMPREPLY=( \$(compgen -W "\${options}" -- "\$cur") )
            fi
            ;;
        *)
            case "\$prev" in
                --suite)
                    local tag_dir=""
                    for w in "\${COMP_WORDS[@]}"; do
                        if echo " \${tags} " | grep -q " \${w} "; then
                            tag_dir="\${fvt_dir}/\${w}"
                            break
                        fi
                    done
                    if [ -n "\${tag_dir}" ] && [ -d "\${tag_dir}" ]; then
                        local suites=""
                        for d in "\${tag_dir}"/*/; do
                            [ -d "\$d" ] || continue
                            local n; n="\$(basename "\$d")"
                            [ "\$n" = "__pycache__" ] && continue
                            suites="\${suites} \${n}"
                        done
                        COMPREPLY=( \$(compgen -W "\${suites}" -- "\$cur") )
                    fi
                    ;;
                --marker) COMPREPLY=( \$(compgen -W "\${markers}" -- "\$cur") ) ;;
                *) COMPREPLY=( \$(compgen -W "\${options}" -- "\$cur") ) ;;
            esac
            ;;
    esac
}
complete -F _run_validation_completions run_validation
COMPLETION_EOF
        exit 0
        ;;

    # -------------------------------------------------------------------------
    # CONFIG: Batch run from test_run_config.yml
    # -------------------------------------------------------------------------
    config)
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

        # Read global overrides
        local_total=0; local_passed=0; local_failed=0; local_skipped=0
        # shellcheck disable=SC2034
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

        scenario_names=$(python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
for name in cfg.get('scenarios', {}):
    print(name)
")

        for name in $scenario_names; do
            eval "$(python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
sc = cfg.get('scenarios', {}).get('${name}', {})
print(f'run_flag={str(sc.get(\"run\", False)).lower()}')
print(f'marker_cfg={sc.get(\"marker\", \"\")}')
print(f'suite_cfg={sc.get(\"suite\", \"\")}')
print(f'command_cfg={sc.get(\"command\", \"test\")}')
print(f'tag_cfg={sc.get(\"tag\", \"${name}\")}')
print(f'dataset_cfg={sc.get(\"dataset\", \"\")}')
print(f'sync_input_cfg={str(sc.get(\"sync_input\", \"\")).lower()}')
print(f'sync_output_cfg={str(sc.get(\"sync_output\", \"\")).lower()}')
")"
            local_total=$((local_total + 1))
            if [[ "$run_flag" != "true" ]]; then
                echo -e "  ${YELLOW}SKIP${NC}  ${name}"
                local_skipped=$((local_skipped + 1))
                continue
            fi

            # shellcheck disable=SC2154
            effective_dataset="${global_dataset:-${dataset_cfg}}"
            # shellcheck disable=SC2154
            effective_sync_input="${global_sync_input:-${sync_input_cfg}}"
            # shellcheck disable=SC2154
            effective_sync_output="${global_sync_output:-${sync_output_cfg}}"

            extra_args=""
            [[ -n "$marker_cfg" ]] && extra_args="$extra_args --marker $marker_cfg"
            [[ -n "$suite_cfg" ]] && extra_args="$extra_args --suite $suite_cfg"

            run_args="${DOMAIN_NAME}"
            [[ -n "$tag_cfg" ]] && run_args="${run_args} ${tag_cfg}"
            run_args="${run_args} ${command_cfg:-test}"

            env_vars=()
            [[ -n "$effective_dataset" ]] && env_vars+=("OMNIA_DATASET_OVERRIDE=${effective_dataset}")
            [[ -n "$effective_sync_input" ]] && env_vars+=("OMNIA_SYNC_INPUT_OVERRIDE=${effective_sync_input}")
            [[ -n "$effective_sync_output" ]] && env_vars+=("OMNIA_SYNC_OUTPUT_OVERRIDE=${effective_sync_output}")

            if env "${env_vars[@]}" "$0" $run_args $extra_args; then
                echo -e "  ${GREEN}PASS${NC}  ${name}"
                local_passed=$((local_passed + 1))
            else
                echo -e "  ${RED}FAIL${NC}  ${name}"
                local_failed=$((local_failed + 1))
            fi
        done

        print_combined_summary

        echo ""
        echo -e "${BLUE}=================================================================${NC}"
        echo -e "  Total: ${local_total}  ${GREEN}Passed: ${local_passed}${NC}  ${RED}Failed: ${local_failed}${NC}  ${YELLOW}Skipped: ${local_skipped}${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        [[ $local_failed -eq 0 ]] || exit 1
        exit 0
        ;;

    # -------------------------------------------------------------------------
    # NFT: Non-functional tests
    # -------------------------------------------------------------------------
    nft)
        if [[ ! -d "$NFT_DIR" ]]; then
            echo -e "${RED}Error: NFT directory not found at ${NFT_DIR}${NC}"
            exit 1
        fi
        export OMNIA_COMMAND_TYPE="nft"
        nft_args="-m nft"
        [[ -n "$MARKER" ]] && nft_args="${nft_args} --marker ${MARKER}"

        echo -e "${BLUE}=================================================================${NC}"
        echo -e "${BLUE}  Image Build Manager — NFT Runner${NC}"
        echo -e "${BLUE}=================================================================${NC}"
        echo ""

        run_pytest \
            "${NFT_DIR}" \
            "${nft_args}" \
            "Running NFT (performance + idempotency)"

        echo ""
        echo -e "${GREEN}NFT execution completed.${NC}"
        exit $?
        ;;
esac

# =============================================================================
# Validate inputs
# =============================================================================
if [[ -n "$TAG" ]]; then
    TAG_DIR="${FVT_DIR}/${TAG}"
    if [[ ! -d "$TAG_DIR" ]]; then
        echo -e "${RED}Error: Tag '${TAG}' not found in fvt/${NC}"
        echo -e "${YELLOW}Available:${NC}"
        get_tags | while read -r s; do echo "  $s"; done
        exit 1
    fi
fi

if ! echo " ${SUPPORTED_COMMANDS} " | grep -q " ${COMMAND} "; then
    echo -e "${RED}Error: Invalid command '${COMMAND}'${NC}"
    echo -e "${YELLOW}Supported: ${SUPPORTED_COMMANDS}${NC}"
    exit 1
fi

# Validate suite folder
if [[ -n "$SUITE" && -n "$TAG" && ! -d "${FVT_DIR}/${TAG}/${SUITE}" ]]; then
    echo -e "${YELLOW}Warning: Suite '${SUITE}' not found in fvt/${TAG}/${NC}"
    echo -e "${YELLOW}Available:${NC}"
    ls -d "${FVT_DIR}/${TAG}"/*/ 2>/dev/null | xargs -I{} basename {} | while read -r d; do echo "  $d"; done
    exit 1
fi

# =============================================================================
# Setup environment
# =============================================================================
if [[ -z "${REPORT_ID:-}" ]]; then
    export REPORT_ID=$(date '+%Y%m%d%H%M%S')
fi

export OMNIA_SUITE="${SUITE:-all}"
export OMNIA_MARKER="${MARKER:-}"
[[ -n "$DEBUG" ]] && export OMNIA_DEBUG="true"
LOG_DIR="${SCRIPT_DIR}/reports/logs"
mkdir -p "${LOG_DIR}"
LABEL="${TAG:-all}"
export OMNIA_LOG_FILE="${LOG_DIR}/${LABEL}_${COMMAND}_${REPORT_ID}.log"

# Set the deploy tag so test_playbook.py knows which ansible tag to use
export OMNIA_DEPLOY_TAG="${TAG}"

# =============================================================================
# Display banner
# =============================================================================
echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}  Image Build Manager — Validation Runner${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo -e "  Domain    : ${GREEN}${DOMAIN_NAME}${NC}"
[[ -n "$TAG" ]]        && echo -e "  Tag       : ${GREEN}${TAG}${NC}" \
                        || echo -e "  Tag       : ${GREEN}(all except cleanup)${NC}"
echo -e "  Command   : ${GREEN}${COMMAND}${NC}"
[[ -n "$SUITE" ]]      && echo -e "  Suite     : ${GREEN}${SUITE}${NC}"
[[ -n "$MARKER" ]]     && echo -e "  Marker    : ${GREEN}${MARKER}${NC}"
[[ -n "$DEBUG" ]]      && echo -e "  Debug     : ${YELLOW}yes${NC}"
echo -e "  Report ID : ${GREEN}${REPORT_ID}${NC}"
echo -e "${BLUE}=================================================================${NC}"
echo ""

# =============================================================================
# Build marker args for pytest
# =============================================================================
build_marker_args() {
    local args=""
    if [[ -n "$MARKER" ]]; then
        args="${args} --marker ${MARKER}"
    fi
    echo "$args"
}

# =============================================================================
# Execute based on command
# =============================================================================
case "$COMMAND" in

    # -------------------------------------------------------------------------
    # EXEC: Run the Ansible playbook only (no verification)
    # -------------------------------------------------------------------------
    exec)
        export OMNIA_COMMAND_TYPE="exec"

        # Find the test_playbook.py in the appropriate tag dir
        if [[ -n "$TAG" ]]; then
            exec_dir="${FVT_DIR}/${TAG}"
        else
            exec_dir="${FVT_DIR}/build"
        fi

        exec_args="-m deploy"
        [[ -n "$MARKER" ]] && exec_args="${exec_args} --marker ${MARKER}"
        run_pytest "${exec_dir}" "${exec_args}" "Executing playbook (tag=${TAG:-none})"

        echo ""
        echo -e "${GREEN}Playbook execution completed.${NC}"
        ;;

    # -------------------------------------------------------------------------
    # VERIFY: Run verification tests only (no playbook)
    # -------------------------------------------------------------------------
    verify)
        export OMNIA_COMMAND_TYPE="verify"
        verify_dirs=$(build_verify_dirs)
        marker_args=$(build_marker_args)
        extra_args="${marker_args} -m 'not deploy'"

        # Build test path with suite filter
        test_paths=""
        for dir in $verify_dirs; do
            if [[ -n "$SUITE" && -d "${dir}/${SUITE}" ]]; then
                test_paths="${test_paths} ${dir}/${SUITE}"
            else
                test_paths="${test_paths} ${dir}"
            fi
        done

        run_pytest \
            "${test_paths}" \
            "${extra_args}" \
            "Running verification tests (${TAG:-all except cleanup})"

        echo ""
        echo -e "${GREEN}Verification completed.${NC}"
        ;;

    # -------------------------------------------------------------------------
    # TEST: Exec playbook + Verify (full flow)
    # -------------------------------------------------------------------------
    test)
        FAILED=0

        export OMNIA_SUPPRESS_SUMMARY="true"
        export OMNIA_RESULTS_FILE=$(mktemp /tmp/omnia_results_XXXXXX.json)

        # Step 1: Execute playbook
        export OMNIA_COMMAND_TYPE="exec"
        echo -e "${YELLOW}=================================================================${NC}"
        echo -e "${YELLOW}  Step 1/2: Execute Playbook${NC}"
        echo -e "${YELLOW}=================================================================${NC}"
        echo ""

        # Find the test_playbook.py in the appropriate tag dir
        if [[ -n "$TAG" ]]; then
            exec_dir="${FVT_DIR}/${TAG}"
        else
            exec_dir="${FVT_DIR}/build"
        fi

        exec_args="-m deploy"
        [[ -n "$MARKER" ]] && exec_args="${exec_args} --marker ${MARKER}"
        if run_pytest "${exec_dir}" "${exec_args}" "Executing playbook (tag=${TAG:-none})"; then
            echo -e "${GREEN}Playbook execution succeeded${NC}"
        else
            echo -e "${RED}Playbook execution failed${NC}"
            FAILED=1
        fi
        echo ""

        # Step 2: Verify (only if exec succeeded)
        if [[ $FAILED -eq 0 ]]; then
            export OMNIA_COMMAND_TYPE="verify"
            echo -e "${YELLOW}=================================================================${NC}"
            echo -e "${YELLOW}  Step 2/2: Verify${NC}"
            echo -e "${YELLOW}=================================================================${NC}"
            echo ""

            verify_dirs=$(build_verify_dirs)
            marker_args=$(build_marker_args)
            extra_args="${marker_args} -m 'not deploy'"

            test_paths=""
            for dir in $verify_dirs; do
                if [[ -n "$SUITE" && -d "${dir}/${SUITE}" ]]; then
                    test_paths="${test_paths} ${dir}/${SUITE}"
                else
                    test_paths="${test_paths} ${dir}"
                fi
            done

            if run_pytest "${test_paths}" "${extra_args}" "Running verification tests"; then
                echo -e "${GREEN}Verification succeeded${NC}"
            else
                echo -e "${RED}Verification failed${NC}"
                FAILED=1
            fi
        else
            echo -e "${YELLOW}Skipping verification — playbook execution failed${NC}"
        fi

        print_combined_summary

        echo ""
        echo -e "${BLUE}=================================================================${NC}"
        if [[ $FAILED -eq 0 ]]; then
            echo -e "${GREEN}  ${DOMAIN_NAME} ${TAG:-full}: EXEC + VERIFY PASSED${NC}"
        else
            echo -e "${RED}  ${DOMAIN_NAME} ${TAG:-full}: FAILED${NC}"
        fi
        echo -e "${BLUE}=================================================================${NC}"

        [[ $FAILED -eq 0 ]] || exit 1
        ;;
esac
