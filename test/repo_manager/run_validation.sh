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

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    cat <<EOF
Repo Manager FVT runner.

Usage:
  run_validation.sh <scenario> <command> [options]
  run_validation.sh --config
  run_validation.sh --help

Commands:
  deploy          Run the Ansible playbook only
  verify          Run verification tests only (no playbook)
  test            Full flow: deploy + verify

Scenarios:
  validate        Validate repo_manager input files
  deploy          Deploy Pulp server
  download        Download and sync repositories
  status          Generate repo_status.yml
  cleanup         Cleanup Pulp server and data
  repo_manager    Full end-to-end run (validate + deploy + download + status)
  all             Run all scenarios

Options:
  --marker <expr>     Filter by marker: sanity, functional, positive, negative, x86_64, aarch64
                      Use '+' for AND, ',' for OR
  --suite <name>      Filter by test suite (subfolder)
  -v, --verbose       Verbose pytest output
  --debug             Debug output (pytest -vvs)
  --config            Run batch scenarios from test_run_config.yml

Examples:
  run_validation.sh validate verify --marker sanity
  run_validation.sh deploy test --marker sanity
  run_validation.sh download verify --marker "sanity+positive"
  run_validation.sh cleanup test --marker "sanity+negative"
  run_validation.sh repo_manager test --marker "sanity"
EOF
}

SCENARIO=""
COMMAND=""
MARKER=""
SUITE=""
VERBOSE=""
DEBUG=""
USE_CONFIG=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) show_help; exit 0 ;;
        --config) USE_CONFIG=true ;;
        --marker) MARKER="$2"; shift ;;
        --suite) SUITE="$2"; shift ;;
        -v|--verbose) VERBOSE="-v" ;;
        --debug) DEBUG="-vvs" ;;
        *)
            if [[ -z "$SCENARIO" ]]; then
                SCENARIO="$1"
            elif [[ -z "$COMMAND" ]]; then
                COMMAND="$1"
            else
                echo "Unknown argument: $1"; show_help; exit 1
            fi
            ;;
    esac
    shift
done

PYTEST_ARGS=()
[[ -n "$MARKER" ]] && PYTEST_ARGS+=("--marker" "$MARKER")
[[ -n "$SUITE" ]] && PYTEST_ARGS+=("--suite" "$SUITE")
[[ -n "$VERBOSE" ]] && PYTEST_ARGS+=("$VERBOSE")
[[ -n "$DEBUG" ]] && PYTEST_ARGS+=("$DEBUG")

if "$USE_CONFIG"; then
    # Run all scenarios from test_run_config.yml
    SCENARIOS=$(python3 - <<PY
import yaml
with open("${SCRIPT_DIR}/test_run_config.yml") as f:
    cfg = yaml.safe_load(f)
for s in cfg.get("scenarios", []):
    print(s)
PY
)
    for s in $SCENARIOS; do
        echo "===== Running scenario: $s ====="
        pytest "${SCRIPT_DIR}/fvt/${s}" "${PYTEST_ARGS[@]}" --tb=short
    done
    exit 0
fi

if [[ -z "$SCENARIO" || -z "$COMMAND" ]]; then
    echo "Missing scenario or command."
    show_help
    exit 1
fi

if [[ "$SCENARIO" == "repo_manager" ]]; then
    # Full end-to-end: run validate, deploy, download, status in order
    for s in validate deploy download status; do
        echo "===== Running scenario: $s ====="
        pytest "${SCRIPT_DIR}/fvt/${s}" "${PYTEST_ARGS[@]}" --tb=short
    done
    exit 0
fi

if [[ "$SCENARIO" == "all" ]]; then
    for s in validate deploy download status cleanup; do
        echo "===== Running scenario: $s ====="
        pytest "${SCRIPT_DIR}/fvt/${s}" "${PYTEST_ARGS[@]}" --tb=short
    done
    exit 0
fi

pytest "${SCRIPT_DIR}/fvt/${SCENARIO}" "${PYTEST_ARGS[@]}" --tb=short
