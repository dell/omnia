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
# TWO CREDENTIAL FILES:
#   1. test_creds.yml                — SSH password for OIM server access (local).
#   2. build_stream_credentials.yml   — GitLab, BSM, and Postgres credentials.
#      Created below $OMNIA_DATA_PATH/build_stream/input/$OMNIA_PROJECT_NAME/, and
#      encrypted with ansible-vault.
#
# SSH CREDENTIALS:
#   --set-creds          Interactive prompt (2x confirmation). Asks to update if exists.
#   --update-creds       Force-update existing SSH password (2x prompt).
#   --creds-stdin        Read a non-interactive SSH password from stdin.
#
# DOMAIN CREDENTIALS:
#   --set-domain-creds     Create credentials or fill only missing fields.
#   --update-domain-creds  Rejected; populated fields cannot be changed here.
#   --domain-creds-stdin   Create/fill missing fields from JSON on stdin.
#
# Usage:
#   ./setup_env.sh                        # Baremetal or active venv
#   ./setup_env.sh --force                # Force-reinstall all requirements
#   ./setup_env.sh --venv                 # Create .venv/ and install there
#   ./setup_env.sh --venv --force         # Recreate .venv/ and reinstall requirements
#   ./setup_env.sh --set-creds            # Prompt for SSH password
#   ./setup_env.sh --update-creds         # Update existing SSH password
#   approved-secret-provider | ./setup_env.sh --creds-stdin
#   ./setup_env.sh --set-domain-creds     # Prompt for GitLab/BSM/Postgres creds
#   credential-json-provider | ./setup_env.sh --domain-creds-stdin
#   ./setup_env.sh --debug                # Verbose pip output
#   ./setup_env.sh --help                 # Show this help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
WHEEL_PATH="${SCRIPT_DIR}/../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl"
cd "$SCRIPT_DIR"

# ── SSH credentials (local) ──
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"

# ── Domain credentials (at env-var path) ──
DOMAIN_CREDS_FILENAME="build_stream_credentials.yml"
DOMAIN_CREDS_KEY_FILENAME=".build_stream_credentials_key"
DOMAIN_NAME="build_stream"

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
    local _domain_root="${OMNIA_DATA_PATH%/}/${DOMAIN_NAME}"
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

Build Stream — Test Environment Setup

Usage: ./setup_env.sh [OPTIONS]

INSTALL MODES
─────────────────────────────────────────────────────────────────
  (no flag)       Baremetal mode (pip install --user).
  --venv          Create .venv/ and install there.
  --force, -f     Force-reinstall all packages from requirements.txt.
                  With --venv, also recreate .venv/ from scratch.

SSH CREDENTIALS (test_creds.yml)
─────────────────────────────────────────────────────────────────
  --set-creds     Interactive SSH password setup (2x confirmation).
  --update-creds  Force-update existing SSH password (2x prompt).
  --creds-stdin   Read an SSH password from standard input.
DOMAIN CREDENTIALS (build_stream_credentials.yml)
─────────────────────────────────────────────────────────────────
  Created on this machine at:
    $OMNIA_DATA_PATH/build_stream/input/$OMNIA_PROJECT_NAME/.
  Fields: gitlab_root_password, gitlab_ssh_password,
          build_stream_auth_username, build_stream_auth_password,
          postgres_user, postgres_password.
  For remote execution, run this command on the target OIM server.

  --set-domain-creds     Create a credential store, or prompt only for fields
                         that are missing or empty. Existing values are kept.
  --update-domain-creds  Populated credentials cannot be changed in place.
                         Perform a full Build Stream cleanup first.
  --domain-creds-stdin   Create a store or fill only missing fields from JSON.
                         A partial-store payload must contain only its missing
                         fields. Example:
    credential-json-provider | ./setup_env.sh --domain-creds-stdin

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

    if [ -z "${OMNIA_DATA_PATH:-}" ]; then
        fail "OMNIA_DATA_PATH is required. Source /etc/omnia/omnia.env."
    fi
    local _domain_root="${OMNIA_DATA_PATH%/}/${DOMAIN_NAME}"
    case "$_domain_root" in
        /*) ;;
        *) fail "Resolved domain data path must be absolute." ;;
    esac
    if [ "${_domain_root%/}" = "" ]; then
        fail "Resolved domain data path must not be the filesystem root."
    fi
}

_domain_environment_is_set() {
    [ -n "${OMNIA_PROJECT_NAME:-}" ] \
        && [ -n "${OMNIA_DATA_PATH:-}" ] \
        && [[ "$OMNIA_PROJECT_NAME" =~ ^[A-Za-z0-9._-]+$ ]] \
        && [ "$OMNIA_PROJECT_NAME" != "." ] \
        && [ "$OMNIA_PROJECT_NAME" != ".." ] \
        && [[ "$OMNIA_DATA_PATH" = /* ]]
}

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
if [ "$domain_action_count" -gt 0 ]; then
    _validate_domain_environment
fi
if [ "$CREDS_FROM_STDIN" = true ] \
    && [ "$DOMAIN_CREDS_FROM_STDIN" = true ]; then
    fail "Only one credential payload can be read from stdin per invocation."
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

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Credential helpers (delegate to omnia_auto credential CLI)
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

# Write domain creds to build_stream_credentials.yml (at env-var path)
_write_domain_creds_stdin() {
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)
    local _dir;  _dir=$(_resolve_domain_creds_dir)

    mkdir -p "$_dir"
    _credential_cli write-fields \
        --creds-path "$_path" --key-path "$_key" \
        --fields-stdin --spec "$DOMAIN_CRED_SPEC" \
        --require-complete >/dev/null
    ok "Domain credentials saved: $_path (encrypted)"
}

# Read a field from the domain creds file
_read_domain_field() {
    local _field="$1"
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)
    _credential_cli read-field --creds-path "$_path" --key-path "$_key" \
        --field "$_field" 2>/dev/null || true
}

# Generate the registrar hash without storing the plaintext password in a
# shell variable or exposing it in process arguments/output.
_write_domain_auth_password_hash() {
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)

    _read_domain_field build_stream_auth_password \
        | "$PYTHON_CMD" -c '
import sys
from argon2 import PasswordHasher, Type

password = sys.stdin.read().rstrip("\n")
if not password:
    raise SystemExit("BuildStream Auth Password is required")
hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
print(hasher.hash(password))
' \
        | _credential_cli write-field \
            --creds-path "$_path" --key-path "$_key" \
            --field build_stream_auth_password_hash \
            --value-stdin >/dev/null
    ok "BuildStream authentication password hash generated"
}

_credential_fields_are_set() {
    local _path="$1"
    local _key="$2"
    shift 2
    if ! _credential_cli is-encrypted \
        --creds-path "$_path" </dev/null >/dev/null 2>&1; then
        return 1
    fi
    local _field
    for _field in "$@"; do
        if ! _credential_cli read-field \
            --creds-path "$_path" --key-path "$_key" \
            --field "$_field" 2>/dev/null \
            | grep -q '[^[:space:]]'; then
            return 1
        fi
    done
}

_ssh_credentials_are_set() {
    _credential_fields_are_set \
        "$CREDS_FILE" "$CREDS_KEY" oim_password
}

DOMAIN_CREDENTIAL_FIELDS=(
    gitlab_root_password
    gitlab_ssh_password
    build_stream_auth_username
    build_stream_auth_password
    postgres_user
    postgres_password
)
DOMAIN_STORED_FIELDS=(
    "${DOMAIN_CREDENTIAL_FIELDS[@]}"
    build_stream_auth_password_hash
)

_domain_credential_file_is_encrypted() {
    local _path; _path=$(_domain_creds_path)
    [ -f "$_path" ] \
        && IFS= read -r _header < "$_path" \
        && [[ "$_header" == \$ANSIBLE_VAULT\;* ]]
}

_domain_vault() (
    umask 077
    local _ansible_tmp
    _ansible_tmp=$(mktemp -d "${TMPDIR:-/tmp}/bsm-ansible.XXXXXX")
    trap 'rm -rf -- "$_ansible_tmp"' EXIT
    ANSIBLE_LOCAL_TEMP="$_ansible_tmp" ansible-vault "$@"
)

_domain_credentials_plaintext() {
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)

    [ -f "$_path" ] || return 1
    if _domain_credential_file_is_encrypted; then
        [ -f "$_key" ] || return 1
        _domain_vault view "$_path" --vault-password-file "$_key"
    else
        cat -- "$_path"
    fi
}

# Print only field names that are absent, empty, or not scalar strings. Secret
# values never leave the pipe and nested runtime data such as oauth_clients is
# deliberately ignored.
_domain_missing_fields() {
    _domain_credentials_plaintext | "$PYTHON_CMD" -c '
import sys
import yaml

loaded = yaml.safe_load(sys.stdin.read()) or {}
if not isinstance(loaded, dict):
    raise SystemExit("Build Stream credential content must be a YAML mapping")
for field in sys.argv[1:]:
    value = loaded.get(field)
    if not isinstance(value, str) or not value.strip():
        print(field)
' "$@"
}

_domain_credentials_are_set() {
    local _missing
    [ -f "$(_domain_creds_path)" ] \
        && [ -f "$(_domain_creds_key_path)" ] \
        && _domain_credential_file_is_encrypted \
        && _missing=$(_domain_missing_fields "${DOMAIN_STORED_FIELDS[@]}" 2>/dev/null) \
        && [ -z "$_missing" ]
}

_domain_credential_store_exists() {
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)
    [ -e "$_path" ] || [ -L "$_path" ] \
        || [ -e "$_key" ] || [ -L "$_key" ]
}

_print_domain_credentials_immutable() {
    local _path; _path=$(_domain_creds_path)
    ok "Build Stream domain credentials are already configured: $_path"
    warn "Populated Build Stream domain credentials cannot be changed in place."
    warn "To use different credentials, first run a full Build Stream cleanup:"
    warn "  ./omnia.sh -r build_stream --tags cleanup"
    warn "Then create fresh credentials and redeploy Build Stream."
}

_print_build_stream_redeploy_required() {
    warn "Running the following command is mandatory after credential setup:"
    warn "  ./omnia.sh -r build_stream"
}

_write_plaintext_domain_field() {
    local _path="$1"
    local _field="$2"
    "$PYTHON_CMD" -c '
import os
import sys
import yaml

path, field = sys.argv[1:]
value = sys.stdin.read()
if value.endswith("\n"):
    value = value[:-1]
    if value.endswith("\r"):
        value = value[:-1]
if not value.strip():
    raise SystemExit(f"{field} cannot be empty")
if field == "build_stream_auth_password" and len(value) < 8:
    raise SystemExit("build_stream_auth_password must contain at least 8 characters")
with open(path, encoding="utf-8") as stream:
    data = yaml.safe_load(stream) or {}
if not isinstance(data, dict):
    raise SystemExit("Build Stream credential content must be a YAML mapping")
data[field] = value
with open(path, "w", encoding="utf-8") as stream:
    yaml.safe_dump(data, stream, default_flow_style=False, sort_keys=False)
os.chmod(path, 0o600)
' "$_path" "$_field"
}

_write_plaintext_domain_auth_hash() {
    local _path="$1"
    "$PYTHON_CMD" -c '
import os
import sys
import yaml
from argon2 import PasswordHasher, Type

path = sys.argv[1]
with open(path, encoding="utf-8") as stream:
    data = yaml.safe_load(stream) or {}
password = data.get("build_stream_auth_password", "")
if not isinstance(password, str) or not password:
    raise SystemExit("build_stream_auth_password is required to generate its hash")
hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
data["build_stream_auth_password_hash"] = hasher.hash(password)
with open(path, "w", encoding="utf-8") as stream:
    yaml.safe_dump(data, stream, default_flow_style=False, sort_keys=False)
os.chmod(path, 0o600)
' "$_path"
}

_domain_field_label() {
    case "$1" in
        gitlab_root_password) echo "GitLab Root Password" ;;
        gitlab_ssh_password) echo "GitLab SSH Password" ;;
        build_stream_auth_username) echo "BuildStream Auth Username" ;;
        build_stream_auth_password) echo "BuildStream Auth Password" ;;
        postgres_user) echo "Postgres Username" ;;
        postgres_password) echo "Postgres Password" ;;
        *) return 1 ;;
    esac
}

_prepare_domain_work_file() {
    local _work_path="$1"
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)

    if [ ! -e "$_path" ]; then
        : > "$_work_path"
    elif _domain_credential_file_is_encrypted; then
        [ -f "$_key" ] || fail "Vault key is missing for encrypted credentials: $_key"
        _domain_vault view "$_path" --vault-password-file "$_key" > "$_work_path"
    else
        cp -- "$_path" "$_work_path"
    fi
    chmod 0600 "$_work_path"
}

_install_domain_work_file() {
    local _work_path="$1"
    local _path; _path=$(_domain_creds_path)
    local _key;  _key=$(_domain_creds_key_path)

    _credential_cli ensure-key --key-path "$_key" >/dev/null
    _domain_vault encrypt "$_work_path" --vault-password-file "$_key" >/dev/null
    chmod 0600 "$_work_path" "$_key"
    mv -f -- "$_work_path" "$_path"
}

_fill_missing_domain_credentials_interactive() (
    set -euo pipefail
    local _missing="$1"
    local _path; _path=$(_domain_creds_path)
    local _dir;  _dir=$(_resolve_domain_creds_dir)
    local _work=""
    local _field _label _value

    mkdir -p "$_dir"
    _work=$(mktemp "${_dir}/.build_stream_credentials.setup.XXXXXX")
    trap '[ -z "$_work" ] || rm -f -- "$_work"' EXIT
    _prepare_domain_work_file "$_work"

    while IFS= read -r _field; do
        [ -n "$_field" ] || continue
        [ "$_field" != "build_stream_auth_password_hash" ] || continue
        _label=$(_domain_field_label "$_field")
        case "$_field" in
            build_stream_auth_username|postgres_user)
                while true; do
                    IFS= read -r -p "  ${_label}: " _value </dev/tty
                    if [ -n "${_value//[[:space:]]/}" ]; then
                        printf '%s' "$_value" \
                            | _write_plaintext_domain_field "$_work" "$_field"
                        unset _value
                        break
                    fi
                    warn "${_label} cannot be empty."
                done
                ;;
            *)
                _credential_cli prompt-and-confirm --message "$_label" </dev/tty \
                    | _write_plaintext_domain_field "$_work" "$_field"
                ;;
        esac
    done <<< "$_missing"

    if printf '%s\n' "$_missing" \
        | grep -Eq '^(build_stream_auth_password|build_stream_auth_password_hash)$'; then
        _write_plaintext_domain_auth_hash "$_work"
        ok "BuildStream authentication password hash generated"
    fi

    _install_domain_work_file "$_work"
    _work=""
    ok "Missing domain credentials were added; existing values were preserved: $_path"
)

_fill_missing_domain_credentials_stdin() (
    set -euo pipefail
    local _dir; _dir=$(_resolve_domain_creds_dir)
    local _path; _path=$(_domain_creds_path)
    local _work=""

    mkdir -p "$_dir"
    _work=$(mktemp "${_dir}/.build_stream_credentials.setup.XXXXXX")
    trap '[ -z "$_work" ] || rm -f -- "$_work"' EXIT
    _prepare_domain_work_file "$_work"

    "$PYTHON_CMD" -c '
import json
import os
import sys
import yaml
from argon2 import PasswordHasher, Type

path = sys.argv[1]
allowed = set(sys.argv[2:])
payload_bytes = sys.stdin.buffer.read(65537)
if len(payload_bytes) > 65536:
    raise SystemExit("Credential input exceeds 65536 bytes")
try:
    payload = json.loads(payload_bytes.decode("utf-8"))
except (UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SystemExit("Credential input must be valid UTF-8 JSON") from exc
if not isinstance(payload, dict):
    raise SystemExit("Credential input must be a JSON object")
with open(path, encoding="utf-8") as stream:
    data = yaml.safe_load(stream) or {}
if not isinstance(data, dict):
    raise SystemExit("Build Stream credential content must be a YAML mapping")
missing = {
    field for field in allowed
    if not isinstance(data.get(field), str) or not data[field].strip()
}
unknown = set(payload) - allowed
if unknown:
    raise SystemExit("Unknown credential fields: " + ", ".join(sorted(unknown)))
protected = set(payload) - missing
if protected:
    raise SystemExit(
        "Populated credential fields cannot be changed: "
        + ", ".join(sorted(protected))
    )
omitted = missing - set(payload)
if omitted:
    raise SystemExit("Missing required credential fields: " + ", ".join(sorted(omitted)))
for field, value in payload.items():
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{field} must contain a non-empty string")
    if field == "build_stream_auth_password" and len(value) < 8:
        raise SystemExit("build_stream_auth_password must contain at least 8 characters")
    data[field] = value
if "build_stream_auth_password" in missing or not data.get("build_stream_auth_password_hash"):
    hasher = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )
    data["build_stream_auth_password_hash"] = hasher.hash(
        data["build_stream_auth_password"]
    )
with open(path, "w", encoding="utf-8") as stream:
    yaml.safe_dump(data, stream, default_flow_style=False, sort_keys=False)
os.chmod(path, 0o600)
' "$_work" "${DOMAIN_CREDENTIAL_FIELDS[@]}"

    _install_domain_work_file "$_work"
    _work=""
    ok "Missing domain credentials were added; existing values were preserved: $_path"
)

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

# ─────────────────────────────────────────────────────────────────────────────
# SSH credential dispatch
# ─────────────────────────────────────────────────────────────────────────────
if [ "$CREDS_FROM_STDIN" = true ]; then
    _show_oim_server_ip
    info "Reading SSH password from standard input"
    _write_ssh_creds_stdin

elif [ "$UPDATE_CREDS" = true ]; then
    _show_oim_server_ip
    if ! _ssh_credentials_are_set; then
        fail "No valid SSH credentials found. Use --set-creds first."
    fi
    echo -e "\n  ${CYAN}Update SSH password for the target OIM server.${NC}\n"
    _prompt_and_write_ssh_creds

elif [ "$SET_CREDS" = true ]; then
    _show_oim_server_ip
    if _ssh_credentials_are_set; then
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

# ─────────────────────────────────────────────────────────────────────────────
# Domain credential dispatch
# ─────────────────────────────────────────────────────────────────────────────

# Domain credentials are shared with the deployed BuildStream service. The
# service adds runtime-owned OAuth clients to this store, while PostgreSQL uses
# its initial password for the persistent data volume. Updating only the file
# would create inconsistent service, database, and GitLab credentials.
if [ "$UPDATE_DOMAIN_CREDS" = true ]; then
    if _domain_credential_store_exists; then
        _print_domain_credentials_immutable
        fail "In-place Build Stream domain credential updates are not supported."
    fi
    fail "No domain credential store exists. Use --set-domain-creds."
fi

if [ "$SET_DOMAIN_CREDS" = true ] \
    || [ "$DOMAIN_CREDS_FROM_STDIN" = true ]; then
    _domain_path=$(_domain_creds_path)
    _domain_key=$(_domain_creds_key_path)

    if [ -L "$_domain_path" ] || [ -L "$_domain_key" ]; then
        fail "Credential files must not be symbolic links."
    fi
    if [ -e "$_domain_path" ] && [ ! -f "$_domain_path" ]; then
        fail "Credential path is not a regular file: $_domain_path"
    fi
    if [ -e "$_domain_key" ] && [ ! -f "$_domain_key" ]; then
        fail "Vault key path is not a regular file: $_domain_key"
    fi

    if [ -f "$_domain_path" ]; then
        if _domain_credential_file_is_encrypted && [ ! -f "$_domain_key" ]; then
            fail "Vault key is missing for encrypted credentials: $_domain_key"
        fi
        if ! _missing_domain_fields=$( \
            _domain_missing_fields "${DOMAIN_STORED_FIELDS[@]}"
        ); then
            fail "Unable to inspect the existing credential store. Check its Vault key."
        fi

        if [ -z "$_missing_domain_fields" ] \
            && _domain_credential_file_is_encrypted; then
            _print_domain_credentials_immutable
        else
            if [ -n "$_missing_domain_fields" ]; then
                warn "Only the following missing credential fields will be added:"
                while IFS= read -r _missing_field; do
                    [ -z "$_missing_field" ] || warn "  $_missing_field"
                done <<< "$_missing_domain_fields"
            else
                warn "Credential values are complete, but the file must be Vault-encrypted."
            fi

            _missing_user_fields=$(printf '%s\n' "$_missing_domain_fields" \
                | grep -Fvx 'build_stream_auth_password_hash' || true)
            if [ -z "$_missing_user_fields" ]; then
                # A plaintext-but-complete store only needs encryption, while
                # a missing derived hash can be regenerated from the existing
                # password. Neither case requires new credential input.
                _fill_missing_domain_credentials_interactive \
                    "$_missing_domain_fields"
            elif [ "$SET_DOMAIN_CREDS" = true ]; then
                _fill_missing_domain_credentials_interactive \
                    "$_missing_domain_fields"
            else
                info "Reading only missing domain credentials from standard input"
                _fill_missing_domain_credentials_stdin
            fi
            _print_build_stream_redeploy_required
        fi
        SET_DOMAIN_CREDS=false
        DOMAIN_CREDS_FROM_STDIN=false
    fi
fi

# Domain credential field spec (JSON for prompt-fields CLI)
DOMAIN_CRED_SPEC='[
  {"field":"gitlab_root_password","label":"GitLab Root Password","group":"GitLab Credentials","secret":true,"confirm":true},
  {"field":"gitlab_ssh_password","label":"GitLab SSH Password","secret":true,"confirm":true},
  {"field":"build_stream_auth_username","label":"BuildStream Auth Username","group":"BuildStream Manager Credentials","secret":false},
  {"field":"build_stream_auth_password","label":"BuildStream Auth Password","secret":true,"confirm":true},
  {"field":"postgres_user","label":"Postgres Username","group":"Postgres Credentials","secret":false},
  {"field":"postgres_password","label":"Postgres Password","secret":true,"confirm":true}
]'

if [ "$DOMAIN_CREDS_FROM_STDIN" = true ]; then
    info "Reading domain credentials from standard input"
    _write_domain_creds_stdin
    _write_domain_auth_password_hash
    _print_build_stream_redeploy_required

elif [ "$SET_DOMAIN_CREDS" = true ]; then
    _domain_path=$(_domain_creds_path)
    _domain_key=$(_domain_creds_key_path)

    echo ""
    echo -e "  ${CYAN}Build Stream credentials — GitLab, BSM, and Postgres${NC}"

    # Use the prompt-fields CLI to handle the one-time credential setup.
    mkdir -p "$(_resolve_domain_creds_dir)"
    _credential_cli prompt-fields \
        --creds-path "$_domain_path" \
        --key-path "$_domain_key" \
        --spec "$DOMAIN_CRED_SPEC" --require-complete </dev/tty

    _write_domain_auth_password_hash

    echo ""
    ok "Domain credentials saved: $_domain_path (encrypted)"
    _print_build_stream_redeploy_required
fi

# ─────────────────────────────────────────────────────────────────────────────
# No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ "$CREDS_FROM_STDIN" = false ] && [ "$UPDATE_CREDS" = false ] && [ "$SET_CREDS" = false ] \
   && [ "$DOMAIN_CREDS_FROM_STDIN" = false ] && [ "$SET_DOMAIN_CREDS" = false ] \
   && [ "$UPDATE_DOMAIN_CREDS" = false ]; then
    if _ssh_credentials_are_set; then
        ok "SSH credentials: test_creds.yml (encrypted)"
    else
        warn "No SSH credentials (test_creds.yml)"
        warn "  Set with: ./setup_env.sh --set-creds"
    fi
    if ! _domain_environment_is_set; then
        warn "Domain credential status unavailable"
        warn "  Source /etc/omnia/omnia.env on the execution OIM to inspect it."
    elif _domain_credentials_are_set; then
        ok "Domain credentials: $(_domain_creds_path) (encrypted)"
    else
        warn "No domain credentials: $(_domain_creds_path)"
        warn "  Set with: ./setup_env.sh --set-domain-creds"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Make scripts executable
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
        echo "    ./run_validation.sh fvt_build_stream list"
        ;;
    active-venv)
        echo "  Next steps (venv already active):"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh fvt_build_stream list"
        ;;
    baremetal)
        echo "  Next steps:"
        echo "    ./run_validation.sh --help"
        echo "    ./run_validation.sh fvt_build_stream list"
        ;;
esac

echo ""
echo "  Credentials (two separate files):"
echo ""
echo "    1. SSH credentials (test_creds.yml) — for remote test execution:"
if _ssh_credentials_are_set; then
    echo "       test_creds.yml is readable and contains the SSH password"
    echo "       To update:  ./setup_env.sh --update-creds"
else
    echo "       Not set. Create with: ./setup_env.sh --set-creds"
fi
echo ""
echo "    2. Build Stream domain credentials (current machine):"
if ! _domain_environment_is_set; then
    echo "       Status unavailable: source /etc/omnia/omnia.env on the execution OIM"
elif _domain_credentials_are_set; then
    echo "       $(_domain_creds_path) contains every required credential"
    echo "       Populated values cannot be changed in place"
    echo "       To replace them: run full Build Stream cleanup, configure fresh"
    echo "       credentials, then run ./omnia.sh -r build_stream"
else
    echo "       Missing or incomplete. Run: ./setup_env.sh --set-domain-creds"
fi
echo ""
echo "================================================================="
echo ""
