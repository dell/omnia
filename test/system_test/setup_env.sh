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
# System verification test (SVT) - prepare this OIM
# =============================================================================
# Usage: ./setup_env.sh [action] [options]
#
#   (no action)              every step, in order:
#                              configure -> install -> set the missing domain
#                              credentials; with --force: configure -> cleanup
#                              -> full install -> credentials
#   --configure              user_inputs.yml -> src/<domain>/input and
#                            src/main/omnia.env (dataset generator, theme of
#                            test_config.yml); the cleanup flags of
#                            test_config.yml -> each test/<suite>/test_config.yml
#   --install                omnia.sh -s (venv, every domain-init.sh, catalog,
#                            omnia-cli), then the test requirements of
#                            repo_manager, image_build_manager, orchestrator and
#                            build_stream in the Omnia venv (only the suites
#                            whose requirements changed). No venv activation
#                            needed
#   --install --force        cleanup first, then a full install (omnia.sh -s
#                            --force-deps, every test requirement again)
#   --cleanup                DESTRUCTIVE: each suite's cleanup FVT, then
#                            omnia.sh --cleanup; asks for 'yes' unless --yes
#   --set-domain-creds       prompt every domain credential store (repo_manager,
#                            image_build_manager, orchestrator, build_stream)
#   --update-domain-creds    update existing stores
#   credential-json-provider | ./setup_env.sh --domain-creds-stdin
#                            JSON keyed by domain, e.g. {"repo_manager": {...}}
#   --status                 the steps and the readiness checks, in a box
#   Then: ./run_validation.sh svt_<theme> all
#
# Options:
#   --yes                    answer every confirmation (cleanup, domain-init
#                            overwrite); for pipelines. Without a terminal the
#                            missing credentials are read as JSON from stdin
#   --force                  with no action or --install: cleanup + full install
#   --domain <name>          with a credential action: one domain store only
#   --recreate-venv          recreate the SVT .venv/
#   --debug                  show pip output
#   --help                   show this help
#
# The Omnia venv is activated for every step that needs it; you never have to
# source activate-omnia.sh. The SVT itself runs from its own .venv/ (created
# here, never activated). Every step's output is printed and appended to
# reports/setup/<step>.log; its outcome goes to reports/setup/setup.json
# (copied into each run report). Credential prompts are never logged.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="${SCRIPT_DIR}/$(basename "${BASH_SOURCE[0]}")"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
VENV_DIR="${SCRIPT_DIR}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
DRIVER="${SCRIPT_DIR}/_setup.py"
REQUIRED_IMPORTS='import pytest, pytest_order, yaml, ruamel.yaml, omnia_auto'
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
info() { echo -e "  ${BLUE}[...]${NC} $1"; }
ok()   { echo -e "  ${GREEN}[OK]${NC}  $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1" >&2; exit 1; }
usage() { sed -n '/^# Usage:/,/^# ====/p' "$SELF" | sed '$d; s/^# \{0,1\}//'; }

ACTION="all"
ACTION_COUNT=0
DRIVER_ARGS=()
DOMAIN=""
FORCE=false
YES=false
RECREATE_VENV=false
PIP_QUIET="--quiet"
set_action() {
    ACTION="$1"
    ACTION_COUNT=$((ACTION_COUNT + 1))
}
while [ $# -gt 0 ]; do
    case "$1" in
        --configure)           set_action configure; shift ;;
        --cleanup)             set_action cleanup; shift ;;
        --install)             set_action install; shift ;;
        --status)              set_action status; shift ;;
        --set-domain-creds|--update-domain-creds|--domain-creds-stdin)
            set_action creds; DRIVER_ARGS+=("--flag=$1"); shift ;;
        --domain)
            [ $# -ge 2 ] || fail "--domain needs a domain name"
            DOMAIN="$2"; shift 2 ;;
        --domain=*)            DOMAIN="${1#--domain=}"; shift ;;
        --yes|-y)              YES=true; shift ;;
        --force)               FORCE=true; shift ;;
        --recreate-venv)       RECREATE_VENV=true; shift ;;
        --debug)               PIP_QUIET=""; shift ;;
        --help|-h)             usage; exit 0 ;;
        --domain-creds|--domain-creds=*|--password|--password=*)
            fail "Secret-valued command-line flags are not supported. Pipe JSON to --domain-creds-stdin." ;;
        *)                     usage; fail "Unknown option: $1" ;;
    esac
done
[ "$ACTION_COUNT" -le 1 ] || fail "Use one action per run (see --help)"
if [ -n "$DOMAIN" ]; then
    [ "$ACTION" = creds ] || fail "--domain needs a credential action (--set-domain-creds ...)"
    [[ "$DOMAIN" =~ ^[a-z_]+$ ]] || fail "Invalid domain name: $DOMAIN"
    DRIVER_ARGS+=(--domain "$DOMAIN")
fi
if [ "$FORCE" = true ]; then
    case "$ACTION" in
        all|install) DRIVER_ARGS+=(--force) ;;
        *) fail "--force is only valid alone or with --install" ;;
    esac
fi
if [ "$YES" = true ]; then
    case "$ACTION" in
        all|install|cleanup) DRIVER_ARGS+=(--yes) ;;
        *) fail "--yes is only valid alone, with --install or with --cleanup" ;;
    esac
fi

# ----------------------------------------------------- SVT .venv (never activated)
PYTHON_CMD=""
for candidate in python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 12))' </dev/null; then
        PYTHON_CMD="$(command -v "$candidate")"
        break
    fi
done
[ -n "$PYTHON_CMD" ] || fail "Python 3.12+ is required (dnf install python3.12 python3.12-pip)"

if [ "$RECREATE_VENV" = true ] && [ -d "$VENV_DIR" ]; then
    info "Removing .venv/ (--recreate-venv)"
    rm -rf -- "$VENV_DIR"
fi
if [ ! -x "$VENV_PYTHON" ]; then
    info "Creating the SVT .venv/"
    # Outside any active virtualenv, so the SVT .venv is built from the system Python.
    env -u VIRTUAL_ENV "$PYTHON_CMD" -m venv "$VENV_DIR" </dev/null
fi
if [ "$RECREATE_VENV" = true ] || ! "$VENV_PYTHON" -c "$REQUIRED_IMPORTS" </dev/null 2>/dev/null; then
    info "Installing the SVT requirements into .venv/"
    PIP_ARGS=(-m pip install --disable-pip-version-check --no-input -r "$REQUIREMENTS")
    [ -n "$PIP_QUIET" ] && PIP_ARGS+=("$PIP_QUIET")
    [ "$RECREATE_VENV" = true ] && PIP_ARGS+=(--force-reinstall)
    PIP_NO_INPUT=1 "$VENV_PYTHON" "${PIP_ARGS[@]}" </dev/null \
        || fail "pip install -r requirements.txt failed"
    "$VENV_PYTHON" -c "$REQUIRED_IMPORTS" </dev/null \
        || fail "the SVT requirements are not importable after the installation"
    ok "SVT requirements installed (.venv/)"
fi
chmod +x "${SCRIPT_DIR}/run_validation.sh" 2>/dev/null || true

# ------------------------------------------------------------------- action
exec "$VENV_PYTHON" "$DRIVER" "$ACTION" "${DRIVER_ARGS[@]+"${DRIVER_ARGS[@]}"}"
