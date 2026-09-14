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
# Telemetry — Test Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# INSTALL MODES:
#   Baremetal (default)  — Install into system Python (pip install --user)
#   Active venv          — Auto-detected; installs into the currently active venv
#   New venv (--venv)    — Creates .venv/ and installs there
#
# TWO CREDENTIAL FILES:
#   1. test_creds.yml       — OIM SSH and enabled external appliance credentials
#                              (OME and SFM), stored locally.
#   2. telemetry_credentials.yml — Domain credentials (BMC, MySQL, CSI, LDMS, UFM, VAST).
#      Created at $TELEMETRY_DATA_PATH/input/$OMNIA_PROJECT_NAME/ when set,
#      otherwise $OMNIA_DATA_PATH/telemetry/input/$OMNIA_PROJECT_NAME/,
#      and encrypted with ansible-vault.
#
# TEST CREDENTIALS:
#   --set-creds          Prompt for OIM SSH and enabled OME/SFM credentials.
#   --update-creds       Force-update OIM SSH and enabled OME/SFM credentials.
#   --creds-stdin        Read a non-interactive OIM SSH password from stdin.
#
# DOMAIN CREDENTIALS:
#   --set-domain-creds   Interactive prompt for telemetry domain credentials.
#   --update-domain-creds  Force-update domain credentials (no "already set" check).
#   --domain-creds-stdin Read a non-interactive JSON object from stdin.
#
# Usage:
#   bash setup_env.sh                        # Baremetal or active venv
#   bash setup_env.sh --venv                 # Create .venv/ and install there
#   bash setup_env.sh --force                 # Force-reinstall dependencies
#   bash setup_env.sh --venv --force         # Recreate .venv/ from scratch
#   bash setup_env.sh --set-creds            # Prompt for test credentials
#   bash setup_env.sh --update-creds         # Update test credentials
#   approved-secret-provider | bash setup_env.sh --creds-stdin
#   bash setup_env.sh --set-domain-creds     # Prompt for telemetry creds
#   credential-json-provider | bash setup_env.sh --domain-creds-stdin
#   bash setup_env.sh --debug                # Verbose pip output
#   bash setup_env.sh --help                 # Show this help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
WHEEL_PATH="${SCRIPT_DIR}/../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl"
cd "$SCRIPT_DIR"

# ── Test credentials (local) ──
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"

# ── Domain credentials (at env-var path) ──
DOMAIN_CREDS_FILENAME="telemetry_credentials.yml"
DOMAIN_CREDS_KEY_FILENAME=".telemetry_credentials_key"
DOMAIN_NAME="telemetry"
DOMAIN_DATA_PATH_ENV="TELEMETRY_DATA_PATH"

# ─────────────────────────────────────────────────────────────────────────────
# Colors & helpers
# ─────────────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "  ${BLUE}[...]${NC} $1"; }
ok()    { echo -e "  ${GREEN}[OK]${NC}  $1"; }
warn()  { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "  ${RED}[FAIL]${NC} $1"; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
# Resolve domain creds path from env vars
# ─────────────────────────────────────────────────────────────────────────────
_resolve_domain_creds_dir() {
    local _domain_root=""
    if [[ -v "$DOMAIN_DATA_PATH_ENV" ]]; then
        _domain_root="${!DOMAIN_DATA_PATH_ENV}"
    fi
    if [ -z "$_domain_root" ]; then
        _domain_root="${OMNIA_DATA_PATH%/}/${DOMAIN_NAME}"
    fi
    echo "${_domain_root%/}/input/${OMNIA_PROJECT_NAME}"
}

_domain_creds_path() {
    echo "$(_resolve_domain_creds_dir)/${DOMAIN_CREDS_FILENAME}"
}

_domain_creds_key_path() {
    echo "$(_resolve_domain_creds_dir)/${DOMAIN_CREDS_KEY_FILENAME}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
USE_VENV=false
FORCE=false
DEBUG=false
PIP_QUIET="--quiet"
SET_CREDS=false
UPDATE_CREDS=false
CREDS_FROM_STDIN=false
SET_DOMAIN_CREDS=false
UPDATE_DOMAIN_CREDS=false
DOMAIN_CREDS_FROM_STDIN=false
TEST_CONFIG="${SCRIPT_DIR}/test_config.yml"

# shellcheck disable=SC2034
while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)              USE_VENV=true; shift ;;
        --force|-f)          FORCE=true; shift ;;
        --debug)             DEBUG=true; PIP_QUIET=""; shift ;;
        --set-creds)         SET_CREDS=true; shift ;;
        --update-creds)      UPDATE_CREDS=true; shift ;;
        --creds-stdin)       CREDS_FROM_STDIN=true; shift ;;
        --set-domain-creds)    SET_DOMAIN_CREDS=true; shift ;;
        --update-domain-creds) UPDATE_DOMAIN_CREDS=true; shift ;;
        --domain-creds-stdin) DOMAIN_CREDS_FROM_STDIN=true; shift ;;
        --creds|--creds=*|--password|--password=*|--set-password|\
        --update-password|--password-stdin)
            fail "Secret-valued command-line flags are no longer supported. Pipe the password to --creds-stdin."
            ;;
        --domain-creds|--domain-creds=*)
            fail "Secret-valued command-line flags are no longer supported. Pipe JSON to --domain-creds-stdin."
            ;;
        --help|-h)
            cat <<'HELPEOF'

Telemetry — Test Environment Setup

Usage: bash setup_env.sh [OPTIONS]

INSTALL MODES
─────────────────────────────────────────────────────────────────
  (no flag)       Baremetal mode (pip install --user).
  --venv          Create .venv/ and install there.
  --force, -f     Force-reinstall all packages from requirements.txt.
                  With --venv, also recreate .venv/ from scratch.

TEST CREDENTIALS (test_creds.yml)
─────────────────────────────────────────────────────────────────
  --set-creds     Prompt for OIM SSH and enabled OME/SFM credentials.
  --update-creds  Force-update OIM SSH and enabled OME/SFM credentials.
  --creds-stdin   Read an OIM SSH password from standard input.
DOMAIN CREDENTIALS (telemetry_credentials.yml)
─────────────────────────────────────────────────────────────────
  Created at $TELEMETRY_DATA_PATH/input/$OMNIA_PROJECT_NAME/ when set;
  otherwise $OMNIA_DATA_PATH/telemetry/input/$OMNIA_PROJECT_NAME/.
  Fields: bmc, mysql, csi, ldms, ufm, vast credentials.

  --set-domain-creds     Interactive prompt for all domain fields.
  --update-domain-creds  Update an existing valid domain credential store.
  --domain-creds-stdin   Read a JSON object from standard input. Example:
    credential-json-provider | bash setup_env.sh --domain-creds-stdin

OTHER OPTIONS
─────────────────────────────────────────────────────────────────
  --debug         Verbose pip output.
  --help, -h      Show this help.

HELPEOF
            exit 0 ;;
        *)
            fail "Unknown option. Use --help for supported arguments." ;;
    esac
done

_validate_domain_environment() {
    if [ -z "${OMNIA_PROJECT_NAME:-}" ]; then
        fail "OMNIA_PROJECT_NAME is required. Source /etc/omnia/omnia.env."
    fi
    if [[ ! "$OMNIA_PROJECT_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
        fail "OMNIA_PROJECT_NAME contains unsupported characters."
    fi
    if [ "$OMNIA_PROJECT_NAME" = "." ] \
        || [ "$OMNIA_PROJECT_NAME" = ".." ]; then
        fail "OMNIA_PROJECT_NAME must name a project directory."
    fi

    local _domain_root=""
    if [[ -v "$DOMAIN_DATA_PATH_ENV" ]]; then
        _domain_root="${!DOMAIN_DATA_PATH_ENV}"
    fi
    if [ -z "$_domain_root" ]; then
        if [ -z "${OMNIA_DATA_PATH:-}" ]; then
            fail "$DOMAIN_DATA_PATH_ENV or OMNIA_DATA_PATH is required."
        fi
        _domain_root="${OMNIA_DATA_PATH%/}/${DOMAIN_NAME}"
    fi
    case "$_domain_root" in
        /*) ;;
        *) fail "Resolved domain data path must be absolute." ;;
    esac
    if [ "${_domain_root%/}" = "" ]; then
        fail "Resolved domain data path must not be the filesystem root."
    fi
}

_validate_domain_environment

ssh_action_count=0
for selected in "$CREDS_FROM_STDIN" "$SET_CREDS" "$UPDATE_CREDS"; do
    if [ "$selected" = true ]; then
        ssh_action_count=$((ssh_action_count + 1))
    fi
done
if [ "$ssh_action_count" -gt 1 ]; then
    fail "Use only one OIM SSH credential action per invocation."
fi

domain_action_count=0
for selected in \
    "$DOMAIN_CREDS_FROM_STDIN" "$SET_DOMAIN_CREDS" "$UPDATE_DOMAIN_CREDS"; do
    if [ "$selected" = true ]; then
        domain_action_count=$((domain_action_count + 1))
    fi
done
if [ "$domain_action_count" -gt 1 ]; then
    fail "Use only one domain credential action per invocation."
fi
if [ "$CREDS_FROM_STDIN" = true ] \
    && [ "$DOMAIN_CREDS_FROM_STDIN" = true ]; then
    fail "Only one credential payload can be read from stdin per invocation."
fi

echo ""
echo "================================================================="
echo "  Telemetry — Test Environment Setup"
echo "================================================================="
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Check Python 3.12+
# ─────────────────────────────────────────────────────────────────────────────
_python_is_supported() {
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' \
        </dev/null 2>/dev/null
}

PYTHON_CMD=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1 && _python_is_supported "$cmd"; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fail "Python 3.12+ is required but not found. Install: dnf install python3.12 python3.12-pip"
fi

ok "Python: $($PYTHON_CMD --version </dev/null 2>&1)"

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Install system dependencies (sshpass for PowerScale syslog config)
# ─────────────────────────────────────────────────────────────────────────────
if command -v dnf &>/dev/null; then
    info "Checking for sshpass (required for PowerScale syslog configuration)"
    if ! command -v sshpass &>/dev/null; then
        info "Installing sshpass via dnf"
        dnf install -y sshpass </dev/null
        ok "sshpass installed"
    else
        ok "sshpass already installed"
    fi
elif command -v apt-get &>/dev/null; then
    info "Checking for sshpass (required for PowerScale syslog configuration)"
    if ! command -v sshpass &>/dev/null; then
        info "Installing sshpass via apt-get"
        apt-get update -qq </dev/null
        apt-get install -y sshpass </dev/null
        ok "sshpass installed"
    else
        ok "sshpass already installed"
    fi
else
    warn "Could not install sshpass (dnf/apt-get not found)"
    warn "PowerScale syslog configuration tests may fail"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Determine install mode
# ─────────────────────────────────────────────────────────────────────────────
INSTALL_MODE="baremetal"
PIP_USER_FLAG="--user"

if [ "$USE_VENV" = true ]; then
    INSTALL_MODE="venv"
    PIP_USER_FLAG=""

    if [ "$FORCE" = true ] && [ -d "$VENV_DIR" ]; then
        info "Removing existing virtual environment (--force)"
        rm -rf "$VENV_DIR"
    fi

    if [ -d "$VENV_DIR" ]; then
        ok "Virtual environment already exists: .venv/"
    else
        info "Creating virtual environment: .venv/"
        "$PYTHON_CMD" -m venv "$VENV_DIR" </dev/null
        ok "Virtual environment created"
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate" </dev/null
    PYTHON_CMD="${VENV_DIR}/bin/python"
    ok "Activated .venv/"

elif [ -n "${VIRTUAL_ENV:-}" ]; then
    INSTALL_MODE="active-venv"
    PIP_USER_FLAG=""
    PYTHON_CMD="${VIRTUAL_ENV}/bin/python"
    ok "Detected active virtual environment: ${VIRTUAL_ENV}"

else
    INSTALL_MODE="baremetal"
    PIP_USER_FLAG="--user"
    ok "Install mode: baremetal (system Python)"
fi

if ! _python_is_supported "$PYTHON_CMD"; then
    fail "The selected Python interpreter must be version 3.12 or newer: ${PYTHON_CMD}"
fi

echo -e "  ${CYAN}Mode:${NC} ${INSTALL_MODE}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
_pip_install() {
    PIP_NO_INPUT=1 "$PYTHON_CMD" -m pip install --no-input "$@" </dev/null
}

info "Upgrading pip"
_pip_install --upgrade pip $PIP_QUIET $PIP_USER_FLAG

if [ ! -f "$WHEEL_PATH" ]; then
    fail "omnia-auto wheel not found: ${WHEEL_PATH}"
fi

info "Installing dependencies from requirements.txt"
PIP_FORCE_ARGS=()
if [ "$FORCE" = true ]; then
    PIP_FORCE_ARGS=(--force-reinstall)
    info "Force-reinstalling all requirements (--force)"
fi

_pip_install "${PIP_FORCE_ARGS[@]}" -r "$REQUIREMENTS" \
    $PIP_QUIET $PIP_USER_FLAG

_omnia_auto_has_required_features() {
    "$PYTHON_CMD" -c '
import inspect
import omnia_auto
params = inspect.signature(omnia_auto.sync_files).parameters
if not {"auth_secret", "port"}.issubset(params) or not callable(omnia_auto.connection_params):
    raise SystemExit(1)
' </dev/null 2>/dev/null \
        && "$PYTHON_CMD" -m omnia_auto write-field --help \
            </dev/null 2>/dev/null \
            | grep -q -- "--value-stdin" \
        && "$PYTHON_CMD" -m omnia_auto write-fields --help \
            </dev/null 2>/dev/null \
            | grep -q -- "--fields-stdin"
}

_omnia_auto_matches_local_wheel() {
    "$PYTHON_CMD" - "$WHEEL_PATH" 2>/dev/null <<'PY'
import importlib.util
from pathlib import Path, PurePosixPath
import sys
import zipfile

wheel_path = Path(sys.argv[1])
spec = importlib.util.find_spec("omnia_auto")
if spec is None or not spec.submodule_search_locations:
    raise SystemExit(1)
package_root = Path(next(iter(spec.submodule_search_locations))).resolve()
with zipfile.ZipFile(wheel_path) as archive:
    members = [
        name for name in archive.namelist()
        if name.startswith("omnia_auto/") and not name.endswith("/")
    ]
    if not members:
        raise SystemExit(1)
    for name in members:
        relative_path = PurePosixPath(name).relative_to("omnia_auto")
        if ".." in relative_path.parts:
            raise SystemExit(1)
        installed_path = package_root.joinpath(*relative_path.parts)
        if (
            not installed_path.is_file()
            or installed_path.read_bytes() != archive.read(name)
        ):
            raise SystemExit(1)
PY
}


if ! _omnia_auto_has_required_features \
    || ! _omnia_auto_matches_local_wheel; then
    info "Refreshing the same-version local omnia-auto wheel"
    _pip_install --force-reinstall --no-deps \
        "$WHEEL_PATH" $PIP_QUIET $PIP_USER_FLAG
fi

if ! _omnia_auto_has_required_features \
    || ! _omnia_auto_matches_local_wheel; then
    fail "Installed omnia-auto does not match the required local wheel API"
fi

ok "All dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Credential helpers (delegate to omnia_auto credential CLI)
# ─────────────────────────────────────────────────────────────────────────────

_credential_cli() {
    "$PYTHON_CMD" -m omnia_auto "$@"
}

_show_oim_server_ip() {
    if [ ! -f "$TEST_CONFIG" ]; then
        warn "test_config.yml not found — set oim_server_ip for remote mode."
        return
    fi
    local oim_ip
    oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -n "$oim_ip" ]; then
        ok "Target server: ${oim_ip}"
    else
        warn "oim_server_ip not set — credentials saved locally for later use."
    fi
}

# Prompt for and write SSH creds without retaining the secret in the shell.
_prompt_and_write_ssh_creds() {
    _credential_cli prompt-and-confirm --message "SSH Password" </dev/tty \
        | _credential_cli write-field \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --field oim_password --value-stdin >/dev/null
    ok "SSH credentials saved: test_creds.yml (encrypted)"
}

_write_ssh_creds_stdin() {
    _credential_cli write-field \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --field oim_password --value-stdin >/dev/null
    ok "SSH credentials saved: test_creds.yml (encrypted)"
}

# OME credential field spec (JSON for prompt-fields CLI)
OME_CRED_SPEC='[
  {"field":"ome_username","label":"OME Username","group":"OME Credentials","secret":false},
  {"field":"ome_password","label":"OME Password","secret":true,"confirm":true},
  {"field":"pfx_secret","label":"PFX Secret","secret":true,"confirm":true,"optional":true}
]'

# Prompt for OME credentials interactively using Python CLI
_prompt_ome_creds() {
    echo ""
    _credential_cli prompt-fields \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --spec "$OME_CRED_SPEC" --require-complete </dev/tty
    ok "OME credentials saved: test_creds.yml (encrypted)"
}

# SFM credential field spec (JSON for prompt-fields CLI)
SFM_CRED_SPEC='[
  {"field":"sfm_api_username","label":"SFM API Username","group":"SFM API Credentials","secret":false},
  {"field":"sfm_api_password","label":"SFM API Password","secret":true,"confirm":true},
  {"field":"sfm_ssh_username","label":"SFM SSH Username","group":"SFM SSH Credentials","secret":false},
  {"field":"sfm_ssh_password","label":"SFM SSH Password","secret":true,"confirm":true}
]'

# Prompt for SFM credentials interactively using Python CLI
_prompt_sfm_creds() {
    echo ""
    _credential_cli prompt-fields \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --spec "$SFM_CRED_SPEC" --require-complete </dev/tty
    ok "SFM credentials saved: test_creds.yml (encrypted)"
}

# Return success only when every named test credential is present and non-empty.
# Values stay inside the pipeline and are not retained by this script.
_test_credential_fields_are_set() {
    if ! _credential_cli is-encrypted \
        --creds-path "$CREDS_FILE" </dev/null >/dev/null 2>&1; then
        return 1
    fi
    local _field
    for _field in "$@"; do
        if ! _credential_cli read-field \
            --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
            --field "$_field" 2>/dev/null \
            | grep -q '[^[:space:]]'; then
            return 1
        fi
    done
    return 0
}

# Check if ome_ip is configured in test_config.yml
_get_ome_ip() {
    grep -E '^ome_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^ome_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true
}

# Check if configure_ome is true in test_config.yml
_is_ome_enabled() {
    local _val
    _val=$(grep -E '^configure_ome:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^configure_ome:[[:space:]]*//; s/[[:space:]]#.*$//; s/["'\''[:space:]]//g' \
        | tr '[:upper:]' '[:lower:]' || echo "false")
    [ "$_val" = "true" ]
}

# Read SFM endpoints from test_config.yml for prompt context
_get_sfm_api_ip() {
    grep -E '^sfm_api_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^sfm_api_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true
}

_get_sfm_ssh_ip() {
    grep -E '^sfm_ssh_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^sfm_ssh_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true
}

# Check if configure_sfm is true in test_config.yml
_is_sfm_enabled() {
    local _val
    _val=$(grep -E '^configure_sfm:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^configure_sfm:[[:space:]]*//; s/[[:space:]]#.*$//; s/["'\'']//g' \
        | tr '[:upper:]' '[:lower:]' || echo "false")
    [ "$_val" = "true" ]
}

# Write domain creds to telemetry_credentials.yml (at env-var path)
_write_domain_creds_stdin() {
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)
    local _dir;  _dir=$(_resolve_domain_creds_dir)

    mkdir -p "$_dir"
    _credential_cli write-fields \
        --creds-path "$_path" --key-path "$_key" \
        --fields-stdin --spec "$DOMAIN_CRED_SPEC" >/dev/null
    ok "Domain credentials saved: $_path (encrypted)"
}

# Return success for an encrypted store with at least one non-empty credential.
# Telemetry fields are component-dependent, so no single field is universally
# mandatory here; the playbook validates fields for the enabled components.
_domain_credential_store_is_readable() {
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)
    if ! _credential_cli is-encrypted --creds-path "$_path" \
        </dev/null >/dev/null 2>&1; then
        return 1
    fi
    _credential_cli read-all \
        --creds-path "$_path" --key-path "$_key" \
        </dev/null 2>/dev/null \
        | "$PYTHON_CMD" -c '
import json
import sys
fields = json.load(sys.stdin)
raise SystemExit(0 if any(isinstance(value, str) and value for value in fields.values()) else 1)
' >/dev/null 2>&1
}

# Ask yes/no
_ask_yes_no() {
    local prompt="$1"
    while true; do
        read -r -p "$prompt (yes/no): " answer </dev/tty
        case "$answer" in
            yes|YES|Yes|y|Y) return 0 ;;
            no|NO|No|n|N)   return 1 ;;
            *) echo -e "  ${RED}Please enter 'yes' or 'no'.${NC}" ;;
        esac
    done
}

# Handle telemetry-specific external appliance credentials after the common
# OIM SSH flow. Mode is either "set" (confirm before replacing) or "update".
_handle_external_credentials() {
    local _mode="$1"
    local _ome_ip _sfm_api_ip _sfm_ssh_ip

    if _is_ome_enabled; then
        _ome_ip=$(_get_ome_ip)
        echo ""
        if [ -n "$_ome_ip" ]; then
            echo -e "  ${CYAN}OME (OpenManage Enterprise) detected: ${_ome_ip}${NC}"
        else
            echo -e "  ${CYAN}OME telemetry enabled (configure_ome=true)${NC}"
        fi

        if [ "$_mode" = "update" ]; then
            echo -e "  ${CYAN}OME credentials required for Kafka forwarder.${NC}"
            _prompt_ome_creds
        elif _test_credential_fields_are_set ome_username ome_password; then
            warn "OME credentials already set."
            if _ask_yes_no "  Do you want to update OME credentials?"; then
                _prompt_ome_creds
            else
                ok "OME credentials update skipped."
            fi
        else
            echo -e "  ${CYAN}Enter OME credentials for Kafka forwarder configuration.${NC}"
            _prompt_ome_creds
        fi
    fi

    if _is_sfm_enabled; then
        _sfm_api_ip=$(_get_sfm_api_ip)
        _sfm_ssh_ip=$(_get_sfm_ssh_ip)
        echo ""
        if [ -n "$_sfm_api_ip" ] || [ -n "$_sfm_ssh_ip" ]; then
            echo -e "  ${CYAN}SFM detected: API=${_sfm_api_ip:-not set}, SSH=${_sfm_ssh_ip:-not set}${NC}"
        else
            echo -e "  ${CYAN}SFM integration enabled (configure_sfm=true)${NC}"
        fi

        if [ "$_mode" = "update" ]; then
            echo -e "  ${CYAN}SFM API and SSH credentials are required.${NC}"
            _prompt_sfm_creds
        elif _test_credential_fields_are_set \
            sfm_api_username sfm_api_password \
            sfm_ssh_username sfm_ssh_password; then
            warn "SFM credentials already set."
            if _ask_yes_no "  Do you want to update SFM credentials?"; then
                _prompt_sfm_creds
            else
                ok "SFM credentials update skipped."
            fi
        else
            echo -e "  ${CYAN}Enter SFM API and SSH credentials.${NC}"
            _prompt_sfm_creds
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Test credential dispatch
# ─────────────────────────────────────────────────────────────────────────────
if [ "$CREDS_FROM_STDIN" = true ]; then
    _show_oim_server_ip
    info "Reading SSH password from standard input"
    _write_ssh_creds_stdin

elif [ "$UPDATE_CREDS" = true ]; then
    _show_oim_server_ip
    if ! _test_credential_fields_are_set oim_password; then
        fail "No SSH password found. Use --set-creds to create one first."
    fi
    echo -e "\n  ${CYAN}Update SSH password for the target OIM server.${NC}\n"
    _prompt_and_write_ssh_creds

elif [ "$SET_CREDS" = true ]; then
    _show_oim_server_ip
    if _test_credential_fields_are_set oim_password; then
        warn "SSH password is already set."
        if _ask_yes_no "  Do you want to update the SSH password?"; then
            echo -e "\n  ${CYAN}Enter new SSH password for the target OIM server.${NC}\n"
            _prompt_and_write_ssh_creds
        else
            ok "SSH password update skipped."
        fi
    else
        echo -e "\n  ${CYAN}Enter SSH password for the target OIM server.${NC}\n"
        _prompt_and_write_ssh_creds
    fi
fi

if [ "$UPDATE_CREDS" = true ]; then
    _handle_external_credentials update
elif [ "$SET_CREDS" = true ]; then
    _handle_external_credentials set
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Domain credential dispatch
# ─────────────────────────────────────────────────────────────────────────────

# Domain credential field spec (JSON for prompt-fields CLI)
DOMAIN_CRED_SPEC='[
  {"field":"bmc_username","label":"BMC Username","group":"iDRAC BMC Credentials","secret":false},
  {"field":"bmc_password","label":"BMC Password","secret":true,"confirm":true},
  {"field":"mysqldb_user","label":"MySQL User","group":"MySQL Database Credentials","secret":false},
  {"field":"mysqldb_password","label":"MySQL Password","secret":true,"confirm":true},
  {"field":"mysqldb_root_password","label":"MySQL Root Password","secret":true,"confirm":true},
  {"field":"csi_username","label":"CSI Username","group":"PowerScale CSI Credentials","secret":false},
  {"field":"csi_password","label":"CSI Password","secret":true,"confirm":true},
  {"field":"ldms_sampler_password","label":"LDMS Sampler Password","group":"LDMS Sampler Credentials","secret":true,"confirm":true},
  {"field":"ufm_username","label":"UFM Username","group":"UFM Telemetry Credentials","secret":false},
  {"field":"ufm_password","label":"UFM Password","secret":true,"confirm":true},
  {"field":"vast_username","label":"VAST Username","group":"VAST Telemetry Credentials","secret":false},
  {"field":"vast_password","label":"VAST Password","secret":true,"confirm":true}
]'

if [ "$DOMAIN_CREDS_FROM_STDIN" = true ]; then
    info "Reading domain credentials from standard input"
    _write_domain_creds_stdin

elif [ "$UPDATE_DOMAIN_CREDS" = true ] || [ "$SET_DOMAIN_CREDS" = true ]; then
    _domain_path=$(_domain_creds_path)
    _domain_key=$(_domain_creds_key_path)

    if [ "$UPDATE_DOMAIN_CREDS" = true ] \
        && ! _domain_credential_store_is_readable; then
        fail "No readable, non-empty encrypted domain credential store found. Use --set-domain-creds first."
    fi

    if [ "$SET_DOMAIN_CREDS" = true ] \
        && _domain_credential_store_is_readable; then
        warn "Domain credentials already exist: $_domain_path"
        if ! _ask_yes_no "  Do you want to update domain credentials?"; then
            ok "Domain credential update skipped."
            SET_DOMAIN_CREDS=false
        fi
    fi

    if [ "$UPDATE_DOMAIN_CREDS" = true ] || [ "$SET_DOMAIN_CREDS" = true ]; then
        echo ""
        echo -e "  ${CYAN}Telemetry Domain Credentials${NC}"
        echo -e "  ${CYAN}Press Enter to keep existing value.${NC}"

        # Use the prompt-fields CLI to handle all prompting
        mkdir -p "$(_resolve_domain_creds_dir)"
        _domain_prompt_result=$(_credential_cli prompt-fields \
            --creds-path "$_domain_path" \
            --key-path "$_domain_key" \
            --spec "$DOMAIN_CRED_SPEC" </dev/tty)

        echo ""
        if [ "$_domain_prompt_result" = "SKIPPED" ]; then
            warn "No domain credential values were entered; nothing was changed."
        else
            ok "Domain credentials saved: $_domain_path (encrypted)"
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 8: No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ "$CREDS_FROM_STDIN" = false ] && [ "$UPDATE_CREDS" = false ] && [ "$SET_CREDS" = false ] \
   && [ "$DOMAIN_CREDS_FROM_STDIN" = false ] && [ "$SET_DOMAIN_CREDS" = false ] \
   && [ "$UPDATE_DOMAIN_CREDS" = false ]; then
    if _test_credential_fields_are_set oim_password; then
        ok "OIM SSH credentials: test_creds.yml (encrypted)"
    else
        warn "No OIM SSH credentials (test_creds.yml)"
        warn "  Set with: bash setup_env.sh --set-creds"
    fi
    if _is_ome_enabled; then
        if _test_credential_fields_are_set ome_username ome_password; then
            ok "OME credentials: test_creds.yml (encrypted)"
        else
            warn "OME is enabled but required credentials are incomplete"
        fi
    fi
    if _is_sfm_enabled; then
        if _test_credential_fields_are_set \
            sfm_api_username sfm_api_password \
            sfm_ssh_username sfm_ssh_password; then
            ok "SFM credentials: test_creds.yml (encrypted)"
        else
            warn "SFM is enabled but required credentials are incomplete"
        fi
    fi
    _dc=$(_domain_creds_path)
    if _domain_credential_store_is_readable; then
        ok "Domain credential store: $_dc (readable and encrypted)"
    else
        warn "No readable, non-empty domain credential store: $_dc"
        warn "  Set with: bash setup_env.sh --set-domain-creds"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 9: Make scripts executable
# ─────────────────────────────────────────────────────────────────────────────
chmod +x "${SCRIPT_DIR}/run_validation.sh" 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}=================================================================${NC}"
echo -e "${GREEN}  Environment Ready  (${INSTALL_MODE})${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo ""

case "$INSTALL_MODE" in
    venv)
        echo "  Next steps:"
        echo "    source .venv/bin/activate"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh telemetry list"
        ;;
    active-venv)
        echo "  Next steps (venv already active):"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh telemetry list"
        ;;
    baremetal)
        echo "  Next steps:"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh telemetry list"
        ;;
esac

echo ""
echo "  Credentials (two separate files):"
echo ""
echo "    1. Test credentials (test_creds.yml) — OIM SSH and enabled OME/SFM access:"
if _test_credential_fields_are_set oim_password; then
    echo "       OIM SSH credentials are set (encrypted)"
    echo "       To update:  bash setup_env.sh --update-creds"
else
    echo "       OIM SSH credentials are not set. Create with: bash setup_env.sh --set-creds"
fi
echo ""
echo "    2. Telemetry domain credentials:"
_dc_summary=$(_domain_creds_path)
if _domain_credential_store_is_readable; then
    echo "       ${_dc_summary} (readable and encrypted)"
    echo "       To update:  bash setup_env.sh --update-domain-creds"
else
    echo "       Not set. Create with: bash setup_env.sh --set-domain-creds"
fi
echo ""
echo "================================================================="
echo ""
