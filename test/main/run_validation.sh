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
# Omnia Automation Framework — Validation Runner
# =============================================================================
#
# Usage:
#   run_validation <scenario> <command> [--suite <suite>] [--marker <marker>]
#   run_validation --config [--continue-on-failure] [--restart]
#   run_validation list
#
# Scenarios (subdirs of fvt/):
#   omnia_sh_install      Build + install + verification
#   omnia_sh_reinstall    Reinstall (overwrite) + verification
#   omnia_sh_uninstall    Uninstall + cleanup verification
#
# Commands (MANDATORY):
#   deploy   Run execution tests only  (test_deploy.py)
#   verify   Run verification tests    (all except test_deploy.py)
#   test     Run deploy THEN verify    (full lifecycle)
#
# Options:
#   --suite <suite>    Filter by functional area directory
#                      e.g. container, security, cleanup
#   --marker <marker>  Validation quality marker filter
#                      e.g. sanity, smoke, regression, functional, negative
#
# Config mode:
#   --config                 Run scenarios from test_run_config.yml
#   --continue-on-failure    Continue batch even if a scenario fails
#   --restart                Discard resume progress and start fresh
#
# Examples:
#   run_validation omnia_sh_install deploy
#   run_validation omnia_sh_install verify
#   run_validation omnia_sh_install test
#   run_validation omnia_sh_install verify --suite container --marker smoke
#   run_validation omnia_sh_reinstall test
#   run_validation omnia_sh_uninstall test
#   run_validation --config
#   run_validation --config --continue-on-failure
#   run_validation list
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$SCRIPT_DIR"
FVT_DIR="$MODULE_DIR/fvt"
CONFIG_FILE="$MODULE_DIR/test_run_config.yml"

SUPPORTED_COMMANDS=("deploy" "verify" "test")

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# =============================================================================
# ACTIVATE VIRTUAL ENVIRONMENT
# =============================================================================

if [ -f "$MODULE_DIR/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$MODULE_DIR/.venv/bin/activate"
fi

# =============================================================================
# LIST SCENARIOS
# =============================================================================

list_scenarios() {
    echo ""
    echo -e "${BLUE}Available scenarios:${NC}"
    echo ""
    for s in "$FVT_DIR"/*/; do
        [ -d "$s" ] || continue
        local sname
        sname=$(basename "$s")
        [[ "$sname" == "__pycache__" ]] && continue

        local suites=""
        for suite_dir in "$s"/*/; do
            [ -d "$suite_dir" ] || continue
            local suite_name
            suite_name=$(basename "$suite_dir")
            [[ "$suite_name" == "__pycache__" ]] && continue
            local test_count
            test_count=$(find "$suite_dir" -maxdepth 1 -name 'test_*.py' | wc -l)
            suites="$suites $suite_name($test_count)"
        done
        echo -e "  ${GREEN}$sname${NC}  suites:${suites:-" none"}"
    done
    echo ""
    echo -e "${BLUE}Usage:${NC}  run_validation <scenario> <command> [--suite <suite>] [--marker <marker>]"
    echo ""
}

# =============================================================================
# VALIDATE COMMAND
# =============================================================================

validate_command() {
    local cmd="$1"
    for c in "${SUPPORTED_COMMANDS[@]}"; do
        [ "$c" = "$cmd" ] && return 0
    done
    echo -e "${RED}ERROR: Invalid command '$cmd'${NC}"
    echo -e "Supported: ${SUPPORTED_COMMANDS[*]}"
    exit 1
}

# =============================================================================
# FIND test_deploy.py RECURSIVELY IN A PATH
# =============================================================================

find_deploy_files() {
    find "$1" -name 'test_deploy.py' -type f 2>/dev/null
}

# =============================================================================
# RUN PYTEST FOR A GIVEN PATH + OPTIONS
# =============================================================================

run_pytest() {
    local test_path="$1"
    local label="$2"
    shift 2
    local extra_args=("$@")

    echo -e "${YELLOW}-> ${label}...${NC}"
    echo ""

    local pytest_cmd=("pytest" "-v" "-s" "--tb=short" "$test_path" "${extra_args[@]}")
    echo -e "  ${CYAN}Command: ${pytest_cmd[*]}${NC}"
    echo ""

    export OMNIA_MODULE_DIR="$MODULE_DIR"
    "${pytest_cmd[@]}"
    local rc=$?
    return $rc
}

# =============================================================================
# RUN SINGLE SCENARIO
# =============================================================================

run_single() {
    local scenario="$1"
    local command="$2"
    local suite="${3:-}"
    local marker="${4:-}"

    local scenario_dir="$FVT_DIR/$scenario"
    if [ ! -d "$scenario_dir" ]; then
        echo -e "${RED}ERROR: Scenario '$scenario' not found${NC}"
        list_scenarios
        exit 1
    fi

    # Resolve test path
    local test_path="$scenario_dir"
    if [ -n "$suite" ]; then
        test_path="$scenario_dir/$suite"
        if [ ! -d "$test_path" ]; then
            echo -e "${RED}ERROR: Suite '$suite' not found in $scenario_dir${NC}"
            echo -e "Available suites:"
            for d in "$scenario_dir"/*/; do
                [ -d "$d" ] || continue
                local dname
                dname=$(basename "$d")
                [[ "$dname" == "__pycache__" ]] && continue
                echo -e "  - $dname"
            done
            exit 1
        fi
    fi

    # Banner
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "  Scenario : ${GREEN}${scenario}${NC}"
    echo -e "  Command  : ${GREEN}${command}${NC}"
    [ -n "$suite" ]  && echo -e "  Suite    : ${GREEN}${suite}${NC}"
    [ -n "$marker" ] && echo -e "  Marker   : ${GREEN}${marker}${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

    local deploy_files
    deploy_files=$(find_deploy_files "$test_path")
    local marker_args=()
    [ -n "$marker" ] && marker_args+=("-m" "$marker")

    case "$command" in
        deploy)
            if [ -z "$deploy_files" ]; then
                echo -e "${RED}ERROR: No test_deploy.py found in $test_path${NC}"
                exit 1
            fi
            # shellcheck disable=SC2086
            run_pytest "$deploy_files" "Deploy: ${scenario}" "${marker_args[@]+"${marker_args[@]}"}"
            ;;
        verify)
            local ignore_args=()
            for f in $deploy_files; do
                ignore_args+=("--ignore=$f")
            done
            run_pytest "$test_path" "Verify: ${scenario}" "${ignore_args[@]+"${ignore_args[@]}"}" "${marker_args[@]+"${marker_args[@]}"}"
            ;;
        test)
            local FAILED=0

            echo ""
            echo -e "${YELLOW}══════════════════════════════════════════════════${NC}"
            echo -e "${YELLOW}  Step 1/2: Deploy${NC}"
            echo -e "${YELLOW}══════════════════════════════════════════════════${NC}"
            echo ""

            if [ -z "$deploy_files" ]; then
                echo -e "${YELLOW}WARN: No test_deploy.py found — skipping deploy phase${NC}"
            else
                if run_pytest "$deploy_files" "Deploy: ${scenario}" "${marker_args[@]+"${marker_args[@]}"}"; then
                    echo -e "${GREEN}Deploy succeeded${NC}"
                else
                    echo -e "${RED}Deploy failed${NC}"
                    FAILED=1
                fi
            fi

            if [ $FAILED -eq 0 ]; then
                echo ""
                echo -e "${YELLOW}══════════════════════════════════════════════════${NC}"
                echo -e "${YELLOW}  Step 2/2: Verify${NC}"
                echo -e "${YELLOW}══════════════════════════════════════════════════${NC}"
                echo ""

                local ignore_args=()
                for f in $deploy_files; do
                    ignore_args+=("--ignore=$f")
                done
                if run_pytest "$test_path" "Verify: ${scenario}" "${ignore_args[@]+"${ignore_args[@]}"}" "${marker_args[@]+"${marker_args[@]}"}"; then
                    echo -e "${GREEN}Verify succeeded${NC}"
                else
                    echo -e "${RED}Verify failed${NC}"
                    FAILED=1
                fi
            else
                echo -e "${YELLOW}Skipping verify — deploy failed${NC}"
            fi

            echo ""
            echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
            if [ $FAILED -eq 0 ]; then
                echo -e "${GREEN}  ${scenario}: DEPLOY + VERIFY PASSED${NC}"
            else
                echo -e "${RED}  ${scenario}: FAILED${NC}"
            fi
            echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
            [ $FAILED -eq 0 ] || return 1
            ;;
    esac
}

# =============================================================================
# BATCH TRACK FILE HELPERS
# =============================================================================

track_update() {
    local track_file="$1" key="$2" status="$3"
    if grep -q "^${key}:" "$track_file" 2>/dev/null; then
        sed -i "s|^${key}:.*|${key}:${status}|" "$track_file"
    else
        echo "${key}:${status}" >> "$track_file"
    fi
}

track_has() {
    local track_file="$1" key="$2" status="$3"
    grep -q "^${key}:${status}$" "$track_file" 2>/dev/null
}

# =============================================================================
# RUN BATCH CONFIG MODE
# =============================================================================

run_config_mode() {
    local continue_on_failure="$1"
    local restart="$2"

    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}ERROR: Config file not found: ${CONFIG_FILE}${NC}"
        echo -e "Create test_run_config.yml in test/main/ with scenario definitions."
        exit 1
    fi

    export CONFIG_FILE
    local TRACK_FILE="$MODULE_DIR/.batch_track"

    # Handle --restart
    if [ "$restart" = "true" ]; then
        rm -f "$TRACK_FILE"
        echo -e "  ${YELLOW}RESTART${NC} Cleared batch progress — starting fresh"
        echo ""
    fi

    # Resume mode
    local resume_mode=false
    if [ -f "$TRACK_FILE" ]; then
        resume_mode=true
        echo -e "  ${CYAN}RESUME${NC} Found previous batch progress (.batch_track)"
        echo -e "  ${CYAN}RESUME${NC} Completed steps will be skipped (use --restart to start fresh)"
        echo ""
    fi

    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Batch Execution from test_run_config.yml${NC}"
    if [ "$continue_on_failure" = "true" ]; then
        echo -e "${BLUE}  Mode: continue-on-failure${NC}"
    fi
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    # -------------------------------------------------------------------------
    # Validate config and get ordered scenario names
    # -------------------------------------------------------------------------
    local scenario_names
    if ! scenario_names=$(python3 - <<'PY'
import os, sys, yaml

VALID_COMMANDS = {"deploy", "verify", "test"}

with open(os.environ["CONFIG_FILE"]) as fh:
    cfg = yaml.safe_load(fh) or {}

scenarios = cfg.get("scenarios", {}) or {}
errors = []
seen = {}
dups = {}

for name, sc in scenarios.items():
    sc = sc or {}
    order = sc.get("order")
    if order is None:
        errors.append("Scenario '%s' is missing the required 'order' field" % name)
    else:
        try:
            order = int(order)
        except (ValueError, TypeError):
            errors.append("Scenario '%s' has non-integer order '%s'" % (name, order))
            continue
        if order in seen:
            dups.setdefault(order, [seen[order]]).append(name)
        else:
            seen[order] = name

    cmd = str(sc.get("command", "test")).strip()
    if cmd not in VALID_COMMANDS:
        errors.append(
            "Scenario '%s' has invalid command '%s' (must be: %s)"
            % (name, cmd, ", ".join(sorted(VALID_COMMANDS)))
        )

if dups:
    for order in sorted(dups):
        errors.append(
            "Duplicate order %s shared by: %s" % (order, ", ".join(dups[order]))
        )

if errors:
    for e in errors:
        sys.stderr.write("ERROR: " + e + "\n")
    sys.exit(1)

for name, sc in sorted(
    scenarios.items(), key=lambda kv: int((kv[1] or {}).get("order", 0))
):
    print(name)
PY
    ); then
        echo -e "${RED}ERROR: Invalid configuration in ${CONFIG_FILE}${NC}"
        echo -e "${YELLOW}Fix the errors above and re-run.${NC}"
        exit 1
    fi

    # Initialize track file
    if [ ! -f "$TRACK_FILE" ]; then
        echo "BATCH_START=$(date '+%Y%m%d%H%M%S')" > "$TRACK_FILE"
    fi

    # -------------------------------------------------------------------------
    # Scenario loop
    # -------------------------------------------------------------------------
    declare -a _r_name=() _r_cmd=() _r_suite=() _r_deploy=() _r_verify=() _r_overall=()
    local total=0 passed=0 failed=0 skipped=0
    local batch_stopped=false batch_stopped_at=""

    for name in $scenario_names; do
        local run_flag command suite marker_cfg
        eval "$(python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
sc = cfg.get('scenarios', {}).get('${name}', {}) or {}
print(f'run_flag={str(sc.get(\"run\", False)).lower()}')
print(f'command={sc.get(\"command\", \"test\")}')
print(f'suite={sc.get(\"suite\", \"\")}')
print(f'marker_cfg={sc.get(\"marker\", \"\")}')
")"
        total=$((total + 1))

        # If batch was stopped, mark remaining as STOP
        if [ "$batch_stopped" = "true" ]; then
            _r_name+=("$name"); _r_cmd+=("$command")
            _r_suite+=("${suite:--}"); _r_deploy+=("--"); _r_verify+=("--"); _r_overall+=("STOP")
            skipped=$((skipped + 1))
            continue
        fi

        if [ "$run_flag" != "true" ]; then
            echo -e "  ${YELLOW}SKIP${NC}  ${name}"
            _r_name+=("$name"); _r_cmd+=("$command")
            _r_suite+=("${suite:--}"); _r_deploy+=("--"); _r_verify+=("--"); _r_overall+=("SKIP")
            skipped=$((skipped + 1))
            continue
        fi

        local extra_args=""
        [ -n "$suite" ] && extra_args="$extra_args --suite $suite"
        [ -n "$marker_cfg" ] && extra_args="$extra_args --marker $marker_cfg"

        local scenario_failed=false
        local deploy_st="N/A" verify_st="N/A"

        if [ "$command" = "test" ]; then
            # DEPLOY PHASE
            if [ "$resume_mode" = "true" ] && track_has "$TRACK_FILE" "${name}:deploy" "PASS"; then
                echo -e "  ${GREEN}DONE${NC}  ${name}:deploy (previous run)"
                deploy_st="DONE"
            else
                echo -e "  ${CYAN}RUN${NC}   ${name}:deploy"
                if "$0" "$name" "deploy" $extra_args; then
                    echo -e "  ${GREEN}PASS${NC}  ${name}:deploy"
                    track_update "$TRACK_FILE" "${name}:deploy" "PASS"
                    deploy_st="PASS"
                else
                    echo -e "  ${RED}FAIL${NC}  ${name}:deploy"
                    track_update "$TRACK_FILE" "${name}:deploy" "FAIL"
                    deploy_st="FAIL"
                    scenario_failed=true
                fi
            fi

            # VERIFY PHASE (only if deploy succeeded)
            if [ "$scenario_failed" = "false" ]; then
                if [ "$resume_mode" = "true" ] && track_has "$TRACK_FILE" "${name}:verify" "PASS"; then
                    echo -e "  ${GREEN}DONE${NC}  ${name}:verify (previous run)"
                    verify_st="DONE"
                else
                    echo -e "  ${CYAN}RUN${NC}   ${name}:verify (suite=${suite:-all}, marker=${marker_cfg:-none})"
                    if "$0" "$name" "verify" $extra_args; then
                        echo -e "  ${GREEN}PASS${NC}  ${name}:verify"
                        track_update "$TRACK_FILE" "${name}:verify" "PASS"
                        verify_st="PASS"
                    else
                        echo -e "  ${RED}FAIL${NC}  ${name}:verify"
                        track_update "$TRACK_FILE" "${name}:verify" "FAIL"
                        verify_st="FAIL"
                        scenario_failed=true
                    fi
                fi
            else
                verify_st="SKIP"
            fi
        else
            # SINGLE PHASE (deploy-only or verify-only)
            if [ "$resume_mode" = "true" ] && track_has "$TRACK_FILE" "${name}" "PASS"; then
                echo -e "  ${GREEN}DONE${NC}  ${name} (previous run)"
                if [ "$command" = "deploy" ]; then deploy_st="DONE"; else verify_st="DONE"; fi
                passed=$((passed + 1))
                _r_name+=("$name"); _r_cmd+=("$command")
                _r_suite+=("${suite:--}"); _r_deploy+=("$deploy_st"); _r_verify+=("$verify_st")
                _r_overall+=("PASS")
                continue
            fi

            echo -e "  ${CYAN}RUN${NC}   ${name} (${command}, suite=${suite:-all}, marker=${marker_cfg:-none})"
            if "$0" "$name" "$command" $extra_args; then
                echo -e "  ${GREEN}PASS${NC}  ${name}"
                track_update "$TRACK_FILE" "${name}" "PASS"
                if [ "$command" = "deploy" ]; then deploy_st="PASS"; else verify_st="PASS"; fi
            else
                echo -e "  ${RED}FAIL${NC}  ${name}"
                track_update "$TRACK_FILE" "${name}" "FAIL"
                if [ "$command" = "deploy" ]; then deploy_st="FAIL"; else verify_st="FAIL"; fi
                scenario_failed=true
            fi
        fi

        # Record result
        local overall_st="PASS"
        if [ "$scenario_failed" = "true" ]; then
            overall_st="FAIL"
            failed=$((failed + 1))
        else
            passed=$((passed + 1))
        fi
        _r_name+=("$name"); _r_cmd+=("$command")
        _r_suite+=("${suite:--}"); _r_deploy+=("$deploy_st"); _r_verify+=("$verify_st")
        _r_overall+=("$overall_st")

        # Stop on failure unless --continue-on-failure
        if [ "$scenario_failed" = "true" ] && [ "$continue_on_failure" != "true" ]; then
            echo ""
            echo -e "  ${RED}Batch stopped due to failure in '${name}'.${NC}"
            echo -e "  ${YELLOW}Fix the issue and re-run 'run_validation --config' to resume.${NC}"
            echo -e "  ${YELLOW}Use --restart to start from the beginning.${NC}"
            batch_stopped=true
            batch_stopped_at="$name"
        fi
    done

    # Clean track file if all passed
    if [ $failed -eq 0 ]; then
        rm -f "$TRACK_FILE"
    fi

    # -------------------------------------------------------------------------
    # Summary table
    # -------------------------------------------------------------------------
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Batch Execution Summary${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    printf "  %-25s %-8s %-10s %-8s %-8s %-8s\n" "SCENARIO" "CMD" "SUITE" "DEPLOY" "VERIFY" "STATUS"
    printf "  %-25s %-8s %-10s %-8s %-8s %-8s\n" "-------------------------" "--------" "----------" "--------" "--------" "--------"

    local i
    for ((i=0; i<${#_r_name[@]}; i++)); do
        local st_color="$NC"
        case "${_r_overall[$i]}" in
            PASS) st_color="$GREEN" ;;
            FAIL) st_color="$RED" ;;
            SKIP|STOP) st_color="$YELLOW" ;;
        esac

        local dep_color="$NC" ver_color="$NC"
        case "${_r_deploy[$i]}" in
            PASS|DONE) dep_color="$GREEN" ;;
            FAIL) dep_color="$RED" ;;
            *) dep_color="$YELLOW" ;;
        esac
        case "${_r_verify[$i]}" in
            PASS|DONE) ver_color="$GREEN" ;;
            FAIL) ver_color="$RED" ;;
            *) ver_color="$YELLOW" ;;
        esac

        printf "  %-25s %-8s %-10s ${dep_color}%-8s${NC} ${ver_color}%-8s${NC} ${st_color}%-8s${NC}\n" \
            "${_r_name[$i]}" "${_r_cmd[$i]}" "${_r_suite[$i]}" \
            "${_r_deploy[$i]}" "${_r_verify[$i]}" "${_r_overall[$i]}"
    done

    echo ""
    echo -e "  Total: ${total}  ${GREEN}Passed: ${passed}${NC}  ${RED}Failed: ${failed}${NC}  ${YELLOW}Skipped: ${skipped}${NC}"

    if [ "$batch_stopped" = "true" ]; then
        echo -e "  ${RED}Stopped at: ${batch_stopped_at}${NC}"
    fi

    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    [ $failed -eq 0 ] || exit 1
}

# =============================================================================
# HELP
# =============================================================================

show_help() {
    echo -e "${BOLD}Omnia Validation Runner${NC}"
    echo ""
    echo "Usage: run_validation <scenario> <command> [options]"
    echo "       run_validation --config [--continue-on-failure] [--restart]"
    echo "       run_validation list"
    echo ""
    echo "Commands (MANDATORY):"
    echo "  deploy    Run execution tests only (test_deploy.py)"
    echo "  verify    Run verification tests (all except test_deploy.py)"
    echo "  test      Run deploy + verify (full lifecycle)"
    echo ""
    echo "Options:"
    echo "  --suite <name>    Filter by functional area directory (container, security, cleanup)"
    echo "  --marker <expr>   Filter by pytest marker (sanity, smoke, regression, functional)"
    echo ""
    echo "Config mode:"
    echo "  --config                  Run scenarios from test_run_config.yml"
    echo "  --continue-on-failure     Continue batch even if a scenario fails"
    echo "  --restart                 Discard resume progress, start fresh"
    echo ""
    echo "Suite + Marker Combinations:"
    echo "  run_validation omnia_sh_install verify --suite container               # all container tests"
    echo "  run_validation omnia_sh_install verify --marker smoke                  # smoke tests only"
    echo "  run_validation omnia_sh_install verify --suite security --marker sanity # combined"
    echo "  run_validation omnia_sh_reinstall test                                 # deploy + verify"
    echo "  run_validation omnia_sh_uninstall verify --suite cleanup               # cleanup tests"
    echo "  run_validation --config                                                # batch from config"
    echo "  run_validation list                                                    # show scenarios"
    echo ""
}

# =============================================================================
# MAIN — ARGUMENT PARSING
# =============================================================================

if [ $# -eq 0 ]; then
    echo -e "${RED}ERROR: Missing required arguments.${NC}"
    echo ""
    echo "Usage: run_validation <scenario> <command> [--suite <suite>] [--marker <marker>]"
    echo "       run_validation --config [--continue-on-failure] [--restart]"
    echo "       run_validation list"
    echo ""
    echo "Both <scenario> and <command> are mandatory."
    echo "Run 'run_validation help' for full usage."
    exit 1
fi

ACTION="$1"
shift

case "$ACTION" in
    list|--list)
        list_scenarios
        exit 0
        ;;
    help|--help|-h)
        show_help
        exit 0
        ;;
    --config)
        # Parse config mode options
        COF=false
        RST=false
        while [ $# -gt 0 ]; do
            case "$1" in
                --continue-on-failure) COF=true; shift ;;
                --restart)            RST=true; shift ;;
                *)
                    echo -e "${RED}Unknown option for --config: $1${NC}"
                    echo "Usage: run_validation --config [--continue-on-failure] [--restart]"
                    exit 1 ;;
            esac
        done
        run_config_mode "$COF" "$RST"
        exit 0
        ;;
    *)
        SCENARIO="$ACTION"

        # Command is MANDATORY — check if provided
        if [ $# -eq 0 ]; then
            echo -e "${RED}ERROR: Missing required argument: <command>${NC}"
            echo ""
            echo "Usage: run_validation <scenario> <command> [--suite <suite>] [--marker <marker>]"
            echo "Commands: deploy, verify, test"
            echo ""
            echo "Examples:"
            echo "  run_validation $SCENARIO deploy"
            echo "  run_validation $SCENARIO verify"
            echo "  run_validation $SCENARIO test"
            exit 1
        fi

        COMMAND="$1"
        shift

        # Validate command is one of deploy/verify/test
        validate_command "$COMMAND"

        # Parse optional --suite / --marker
        SUITE=""
        MARKER=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --suite)
                    [ $# -lt 2 ] && { echo -e "${RED}ERROR: --suite requires a value${NC}"; exit 1; }
                    SUITE="$2"; shift 2 ;;
                --marker)
                    [ $# -lt 2 ] && { echo -e "${RED}ERROR: --marker requires a value${NC}"; exit 1; }
                    MARKER="$2"; shift 2 ;;
                *)
                    echo -e "${RED}Unknown option: $1${NC}"
                    echo "Usage: run_validation <scenario> <command> [--suite <suite>] [--marker <marker>]"
                    exit 1 ;;
            esac
        done

        run_single "$SCENARIO" "$COMMAND" "$SUITE" "$MARKER"
        ;;
esac
