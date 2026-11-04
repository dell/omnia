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
# Build Stream — Test Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# INSTALL MODES:
#   Baremetal (default)  — Install into system Python (pip install --user)
#   Active venv          — Auto-detected; installs into the currently active venv
#   New venv (--venv)    — Creates .venv/ and installs there
#
# Credential stores (all Ansible Vault encrypted, 0600):
#   1. test_creds.yml (this directory) — OIM SSH password for remote mode.
#   2. Domain credential stores, at <DOMAIN>_DATA_PATH (or
#      OMNIA_DATA_PATH/<domain>)/input/<OMNIA_PROJECT_NAME>/ from omnia.env,
#      in the order the playbooks need them:
#        repo_manager         repo_manager_config_credentials.yml
#        image_build_manager  image_build_credentials.yml
#        orchestrator         orchestrator_credentials.yml
#        build_stream         build_stream_credentials.yml
#      The playbooks prompt when a store is missing; setting them here
#      lets the suite run unattended.
#
# Usage:
#   ./setup_env.sh                         Baremetal or active venv
#   ./setup_env.sh --venv                  Create .venv/ and install there
#   ./setup_env.sh --force                 Force-reinstall all requirements
#                                          (with --venv, also recreate .venv/)
#   ./setup_env.sh --set-creds             Prompt for the OIM SSH password
#   ./setup_env.sh --update-creds          Update the existing SSH password
#   approved-secret-provider | ./setup_env.sh --creds-stdin
#   ./setup_env.sh --set-domain-creds      Prompt every domain store in order
#   ./setup_env.sh --set-domain-creds --domain build_stream
#   ./setup_env.sh --update-domain-creds [--domain <name>]
#   credential-json-provider | ./setup_env.sh --domain-creds-stdin
#       JSON keyed by domain, e.g. {"repo_manager": {"pulp_password": "..."},
#       "build_stream": {...}}; only the listed domains are written.
#   ./setup_env.sh --debug                 Verbose pip output
#   ./setup_env.sh --help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
WHEEL_PATH="${SCRIPT_DIR}/../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl"
TEST_CONFIG="${SCRIPT_DIR}/test_config.yml"
OMNIA_ENV_FILE="/etc/omnia/omnia.env"
DOMAIN_CREDS_HELPER="${SCRIPT_DIR}/library/domain_credentials.py"
cd "$SCRIPT_DIR"

# ── SSH credentials (local) ──
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"

# ── Domain credentials (at env-var path), in playbook order ──
DOMAINS=(repo_manager image_build_manager orchestrator build_stream)

declare -A DOMAIN_CREDS_FILE=(
    [repo_manager]="repo_manager_config_credentials.yml"
    [image_build_manager]="image_build_credentials.yml"
    [orchestrator]="orchestrator_credentials.yml"
    [build_stream]="build_stream_credentials.yml"
)
declare -A DOMAIN_CREDS_KEY=(
    [repo_manager]=".repo_manager_config_credentials_key"
    [image_build_manager]=".image_build_credentials_key"
    [orchestrator]=".orchestrator_credentials_key"
    [build_stream]=".build_stream_credentials_key"
)
declare -A DOMAIN_TITLE=(
    [repo_manager]="Repo Manager Credentials — Pulp, Docker Hub"
    [image_build_manager]="Image Build Manager Credentials — S3/MinIO, aarch64 build host"
    [orchestrator]="Orchestrator Credentials — Provision, Slurm, OpenLDAP, CSI"
    [build_stream]="BuildStream Credentials — GitLab, BuildStream Manager, Postgres"
)
# Field specs match each domain's playbook and its domain test suite.
# An entry with "value" is fixed: written without a prompt when the file does not
# hold it yet (pulp_username is hard-coded to admin by repo_manager, and its
# credential schema requires it).
declare -A DOMAIN_CRED_SPEC=(
    [repo_manager]='[
  {"field":"pulp_username","label":"Pulp Username","value":"admin"},
  {"field":"pulp_password","label":"Pulp Password","group":"Pulp Credentials","secret":true,"confirm":true,"min_length":1},
  {"field":"docker_username","label":"Docker Hub Username","group":"Docker Hub (optional; set both or neither)","secret":false,"optional":true},
  {"field":"docker_password","label":"Docker Hub Password","secret":true,"confirm":true,"optional":true}
]'
    [image_build_manager]='[
  {"field":"s3_access_id","label":"S3 Access ID","group":"S3/MinIO Credentials","secret":false,"optional":true},
  {"field":"s3_secret_key","label":"S3 Secret Key","secret":true,"confirm":true,"min_length":8},
  {"field":"aarch64_ssh_password","label":"aarch64 SSH Password","group":"aarch64 Build Host","secret":true,"confirm":true,"optional":true}
]'
    [orchestrator]='[
  {"field":"provision_password","label":"Provision Password","group":"Provision Credentials","secret":true,"confirm":true,"min_length":8},
  {"field":"bmc_username","label":"BMC Username","group":"Provision Credentials","secret":false},
  {"field":"bmc_password","label":"BMC Password","group":"Provision Credentials","secret":true,"confirm":true,"min_length":3},
  {"field":"slurm_db_password","label":"Slurm Database Password","group":"Slurm Credentials (optional unless Slurm is enabled)","secret":true,"confirm":true,"min_length":8,"optional":true},
  {"field":"openldap_db_username","label":"OpenLDAP Database Username","group":"OpenLDAP Credentials (optional unless OpenLDAP is enabled)","secret":false,"min_length":4,"optional":true},
  {"field":"openldap_db_password","label":"OpenLDAP Database Password","group":"OpenLDAP Credentials (optional unless OpenLDAP is enabled)","secret":true,"confirm":true,"min_length":8,"optional":true},
  {"field":"csi_username","label":"CSI Driver Username","group":"CSI Driver (optional unless PowerScale CSI is enabled)","secret":false,"min_length":4,"optional":true},
  {"field":"csi_password","label":"CSI Driver Password","group":"CSI Driver (optional unless PowerScale CSI is enabled)","secret":true,"confirm":true,"min_length":5,"optional":true}
]'
    [build_stream]='[
  {"field":"gitlab_root_password","label":"GitLab Root Password","group":"GitLab Credentials","secret":true,"confirm":true},
  {"field":"gitlab_ssh_password","label":"GitLab SSH Password","secret":true,"confirm":true},
  {"field":"build_stream_auth_username","label":"BuildStream Auth Username","group":"BuildStream Manager Credentials","secret":false},
  {"field":"build_stream_auth_password","label":"BuildStream Auth Password","secret":true,"confirm":true,"min_length":8},
  {"field":"postgres_user","label":"Postgres Username","group":"Postgres Credentials","secret":false},
  {"field":"postgres_password","label":"Postgres Password","secret":true,"confirm":true}
]'
)

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

usage() {
    sed -n '/^# Usage:/,/^# ====/p' "${BASH_SOURCE[0]}" | sed '$d; s/^# \{0,1\}//'
}

# ─────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
USE_VENV=false
FORCE=false
PIP_QUIET="--quiet"
SET_CREDS=false
UPDATE_CREDS=false
CREDS_FROM_STDIN=false
SET_DOMAIN_CREDS=false
UPDATE_DOMAIN_CREDS=false
DOMAIN_CREDS_FROM_STDIN=false
SELECTED_DOMAIN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)                USE_VENV=true; shift ;;
        --force|-f)            FORCE=true; shift ;;
        --debug)               PIP_QUIET=""; shift ;;
        --set-creds)           SET_CREDS=true; shift ;;
        --update-creds)        UPDATE_CREDS=true; shift ;;
        --creds-stdin)         CREDS_FROM_STDIN=true; shift ;;
        --set-domain-creds)    SET_DOMAIN_CREDS=true; shift ;;
        --update-domain-creds) UPDATE_DOMAIN_CREDS=true; shift ;;
        --domain-creds-stdin)  DOMAIN_CREDS_FROM_STDIN=true; shift ;;
        --domain)
            [ $# -ge 2 ] || fail "--domain requires one of: ${DOMAINS[*]}"
            SELECTED_DOMAIN="$2"; shift 2 ;;
        --domain=*)            SELECTED_DOMAIN="${1#--domain=}"; shift ;;
        --creds|--creds=*|--password|--password=*|--set-password|\
        --update-password|--password-stdin)
            fail "Secret-valued command-line flags are no longer supported. Pipe the password to --creds-stdin."
            ;;
        --domain-creds|--domain-creds=*)
            fail "Secret-valued command-line flags are no longer supported. Pipe JSON to --domain-creds-stdin."
            ;;
        --help|-h)             usage; exit 0 ;;
        *)                     usage; fail "Unknown option: $1" ;;
    esac
done

ssh_action_count=0
for selected in "$CREDS_FROM_STDIN" "$SET_CREDS" "$UPDATE_CREDS"; do
    [ "$selected" = true ] && ssh_action_count=$((ssh_action_count + 1))
done
domain_action_count=0
for selected in \
    "$DOMAIN_CREDS_FROM_STDIN" "$SET_DOMAIN_CREDS" "$UPDATE_DOMAIN_CREDS"; do
    [ "$selected" = true ] && domain_action_count=$((domain_action_count + 1))
done
[ "$ssh_action_count" -le 1 ] || fail "Use only one OIM SSH credential action per invocation."
[ "$domain_action_count" -le 1 ] || fail "Use only one domain credential action per invocation."
if [ "$CREDS_FROM_STDIN" = true ] && [ "$DOMAIN_CREDS_FROM_STDIN" = true ]; then
    fail "Only one credential payload can be read from stdin per invocation."
fi

SELECTED_DOMAINS=("${DOMAINS[@]}")
if [ -n "$SELECTED_DOMAIN" ]; then
    [ -n "${DOMAIN_CREDS_FILE[$SELECTED_DOMAIN]+set}" ] \
        || fail "Unknown domain '$SELECTED_DOMAIN'. Use one of: ${DOMAINS[*]}"
    SELECTED_DOMAINS=("$SELECTED_DOMAIN")
fi

echo ""
echo "================================================================="
echo "  Build Stream — Test Environment Setup"
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

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Determine install mode
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

ok "Python: $($PYTHON_CMD --version </dev/null 2>&1)"
echo -e "  ${CYAN}Mode:${NC} ${INSTALL_MODE}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Install dependencies
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

# The credential CLIs call ansible-vault from the same environment.
PYTHON_BIN_DIR="$(dirname "$PYTHON_CMD")"
export PATH="${PYTHON_BIN_DIR}:${HOME}/.local/bin:${PATH}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Credential helpers
# ─────────────────────────────────────────────────────────────────────────────
_credential_cli() {
    "$PYTHON_CMD" -m omnia_auto "$@"
}

# omnia.env values, without overriding variables already exported.
_omnia_env() {
    local _name="$1" _default="$2"
    if [ -n "${!_name:-}" ]; then
        echo "${!_name}"
        return
    fi
    if [ -f "$OMNIA_ENV_FILE" ]; then
        local _value
        # shellcheck source=/dev/null  # omnia.env is installed by omnia.sh --setup-venv
        _value=$(set +u; set -a; . "$OMNIA_ENV_FILE" >/dev/null 2>&1; echo "${!_name:-}")
        if [ -n "$_value" ]; then
            echo "$_value"
            return
        fi
    fi
    echo "$_default"
}

# No fallback values: credential stores are only written where omnia.env says.
OMNIA_DATA_PATH_VALUE=$(_omnia_env OMNIA_DATA_PATH "")
OMNIA_PROJECT_NAME_VALUE=$(_omnia_env OMNIA_PROJECT_NAME "")

_domain_paths_known() {
    [ -n "$OMNIA_DATA_PATH_VALUE" ] && [ -n "$OMNIA_PROJECT_NAME_VALUE" ] \
        && [[ "$OMNIA_PROJECT_NAME_VALUE" =~ ^[A-Za-z0-9._-]+$ ]] \
        && [ "$OMNIA_PROJECT_NAME_VALUE" != "." ] \
        && [ "$OMNIA_PROJECT_NAME_VALUE" != ".." ]
}
_require_domain_paths() {
    _domain_paths_known || fail "OMNIA_DATA_PATH and a valid OMNIA_PROJECT_NAME must be set in ${OMNIA_ENV_FILE} (run ./omnia.sh --setup-venv)"
}

_domain_creds_dir() {
    local _domain="$1" _env_name _root
    _env_name="$(echo "$_domain" | tr '[:lower:]' '[:upper:]')_DATA_PATH"
    _root=$(_omnia_env "$_env_name" "${OMNIA_DATA_PATH_VALUE%/}/${_domain}")
    case "$_root" in
        /?*) ;;
        *) fail "Resolved ${_domain} data path must be absolute: '${_root}'" ;;
    esac
    echo "${_root%/}/input/${OMNIA_PROJECT_NAME_VALUE}"
}
_domain_creds_path() { echo "$(_domain_creds_dir "$1")/${DOMAIN_CREDS_FILE[$1]}"; }
_domain_creds_key_path() { echo "$(_domain_creds_dir "$1")/${DOMAIN_CREDS_KEY[$1]}"; }

# Domain stores keep nested data (build_stream oauth_clients, repo_manager
# registry_credentials) the flat credential CLI cannot load, so they go
# through library/domain_credentials.py, which merges top-level fields only.
_domain_cli() {
    local _command="$1" _domain="$2"
    local _path _key
    _path=$(_domain_creds_path "$_domain")
    _key=$(_domain_creds_key_path "$_domain")
    if [ -L "$_path" ] || [ -L "$_key" ]; then
        fail "Credential files must not be symbolic links: ${_path}"
    fi
    "$PYTHON_CMD" "$DOMAIN_CREDS_HELPER" "$_command" \
        --creds-path "$_path" --key-path "$_key" \
        --spec "${DOMAIN_CRED_SPEC[$_domain]}"
}

_credential_fields_are_set() {
    local _path="$1" _key="$2" _field
    shift 2
    _credential_cli is-encrypted --creds-path "$_path" </dev/null >/dev/null 2>&1 || return 1
    for _field in "$@"; do
        _credential_cli read-field --creds-path "$_path" --key-path "$_key" \
            --field "$_field" 2>/dev/null | grep -q '[^[:space:]]' || return 1
    done
}

_ssh_credentials_are_set() {
    _credential_fields_are_set "$CREDS_FILE" "$CREDS_KEY" oim_password
}

_domain_credentials_are_set() {
    _domain_cli status "$1" </dev/null >/dev/null 2>&1
}

_ask_yes_no() {
    local prompt="$1" answer
    while true; do
        read -r -p "$prompt (yes/no): " answer </dev/tty
        case "$answer" in
            yes|YES|Yes|y|Y) return 0 ;;
            no|NO|No|n|N)   return 1 ;;
            *) echo -e "  ${RED}Please enter 'yes' or 'no'.${NC}" ;;
        esac
    done
}

_show_oim_server_ip() {
    local oim_ip=""
    [ -f "$TEST_CONFIG" ] && oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null \
        | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -n "$oim_ip" ]; then
        ok "Target server: ${oim_ip}"
    else
        warn "oim_server_ip not set — local mode; the SSH password is only used remotely."
    fi
}

_prompt_and_write_ssh_creds() {
    _credential_cli prompt-and-confirm --message "SSH Password" </dev/tty \
        | _credential_cli write-field \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --field oim_password --value-stdin >/dev/null
    chmod 0600 "$CREDS_FILE" "$CREDS_KEY"
    ok "SSH credentials saved: test_creds.yml (encrypted)"
}

_write_ssh_creds_stdin() {
    _credential_cli write-field \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --field oim_password --value-stdin >/dev/null
    chmod 0600 "$CREDS_FILE" "$CREDS_KEY"
    ok "SSH credentials saved: test_creds.yml (encrypted)"
}

# BuildStream stores an Argon2id hash of the auth password next to it
# (same parameters as build_stream.yml and the registrar API).
_write_build_stream_auth_hash() {
    _domain_cli hash-auth build_stream </dev/null
    ok "BuildStream authentication password hash generated"
}

_after_domain_write() {
    local _domain="$1"
    chmod 0600 "$(_domain_creds_path "$_domain")" "$(_domain_creds_key_path "$_domain")"
    if [ "$_domain" = build_stream ]; then
        _write_build_stream_auth_hash
        warn "Running the following command is mandatory after BuildStream credential changes:"
        warn "  ./omnia.sh -r build_stream"
    fi
    ok "${_domain} credentials saved: $(_domain_creds_path "$_domain") (encrypted)"
}

_prompt_domain_credentials() {
    local _domain="$1"
    echo ""
    echo -e "  ${CYAN}${DOMAIN_TITLE[$_domain]}${NC}"
    echo -e "  ${CYAN}Press Enter to keep an existing value.${NC}"
    _domain_cli prompt "$_domain" </dev/tty
    _after_domain_write "$_domain"
}

_write_domain_credentials_stdin() {
    local _payload _domain _fields
    _payload=$(head -c 65537)
    [ "${#_payload}" -le 65536 ] || fail "Credential input exceeds 65536 bytes"
    for _domain in "${SELECTED_DOMAINS[@]}"; do
        _fields=$(printf '%s' "$_payload" | "$PYTHON_CMD" -c '
import json, sys
data = json.load(sys.stdin)
if not isinstance(data, dict):
    raise SystemExit("Domain credential JSON must be an object keyed by domain")
value = data.get(sys.argv[1])
if value is not None:
    if not isinstance(value, dict):
        raise SystemExit(f"{sys.argv[1]} credentials must be a JSON object")
    print(json.dumps(value))' "$_domain") || fail "Invalid domain credential JSON"
        [ -n "$_fields" ] || continue
        printf '%s' "$_fields" | _domain_cli write-stdin "$_domain"
        _after_domain_write "$_domain"
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: SSH credential dispatch (test_creds.yml)
# ─────────────────────────────────────────────────────────────────────────────
if [ "$CREDS_FROM_STDIN" = true ]; then
    _show_oim_server_ip
    info "Reading SSH password from standard input"
    _write_ssh_creds_stdin
elif [ "$UPDATE_CREDS" = true ]; then
    _show_oim_server_ip
    _ssh_credentials_are_set || fail "No valid SSH credentials found. Use --set-creds first."
    echo -e "\n  ${CYAN}Update SSH password for the target OIM server.${NC}\n"
    _prompt_and_write_ssh_creds
elif [ "$SET_CREDS" = true ]; then
    _show_oim_server_ip
    if _ssh_credentials_are_set && ! _ask_yes_no "  SSH password is already set. Update it?"; then
        ok "SSH password update skipped."
    else
        echo -e "\n  ${CYAN}Enter SSH password for the target OIM server.${NC}\n"
        _prompt_and_write_ssh_creds
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Domain credential dispatch (four domain stores)
# ─────────────────────────────────────────────────────────────────────────────
if [ "$domain_action_count" -gt 0 ]; then
    _require_domain_paths
fi
if [ "$DOMAIN_CREDS_FROM_STDIN" = true ]; then
    info "Reading domain credential JSON from standard input"
    _write_domain_credentials_stdin
elif [ "$UPDATE_DOMAIN_CREDS" = true ]; then
    for domain in "${SELECTED_DOMAINS[@]}"; do
        _domain_credentials_are_set "$domain" \
            || fail "No valid ${domain} credentials. Use --set-domain-creds --domain ${domain} first."
    done
    for domain in "${SELECTED_DOMAINS[@]}"; do
        _prompt_domain_credentials "$domain"
    done
elif [ "$SET_DOMAIN_CREDS" = true ]; then
    for domain in "${SELECTED_DOMAINS[@]}"; do
        if _domain_credentials_are_set "$domain"; then
            warn "${domain} credentials already exist: $(_domain_creds_path "$domain")"
            if ! _ask_yes_no "  Update ${domain} credentials?"; then
                ok "${domain} credential update skipped."
                continue
            fi
        fi
        _prompt_domain_credentials "$domain"
    done
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Credential status (always shown)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
info "Credential status (needed for unattended runs)"
if _ssh_credentials_are_set; then
    ok "SSH credentials: test_creds.yml (encrypted)"
else
    warn "No SSH credentials (test_creds.yml): only needed when oim_server_ip is set (remote mode)"
    warn "  Set with: ./setup_env.sh --set-creds"
fi
DOMAINS_TO_SHOW=()
if _domain_paths_known; then
    DOMAINS_TO_SHOW=("${DOMAINS[@]}")
else
    warn "Domain credential status unavailable: OMNIA_DATA_PATH/OMNIA_PROJECT_NAME not set in ${OMNIA_ENV_FILE}"
fi
for domain in "${DOMAINS_TO_SHOW[@]}"; do
    if _domain_credentials_are_set "$domain"; then
        ok "${domain}: $(_domain_creds_path "$domain") (encrypted)"
    else
        warn "No ${domain} credentials: $(_domain_creds_path "$domain")"
        warn "  Set with: ./setup_env.sh --set-domain-creds --domain ${domain}"
    fi
done

chmod +x "${SCRIPT_DIR}/run_validation.sh" 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}=================================================================${NC}"
echo -e "${GREEN}  Environment Ready  (${INSTALL_MODE})${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo ""
echo "  Next steps:"
[ "$INSTALL_MODE" = venv ] && echo "    source .venv/bin/activate"
echo "    ./run_validation.sh --help"
echo "    ./run_validation.sh fvt_build_stream list"
echo ""
