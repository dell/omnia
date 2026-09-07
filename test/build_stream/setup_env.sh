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
# Build Stream — Test Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# INSTALL MODES:
#   Baremetal (default)  — Install into system Python (pip install --user)
#   Active venv          — Auto-detected; installs into the currently active venv
#   New venv (--venv)    — Creates .venv/ and installs there
#
# CREDENTIAL HANDLING:
#   SSH credentials (OIM server — only needed for remote execution):
#     --set-creds          — Prompt for SSH password (asks twice for confirmation).
#                            If password already exists, asks yes/no to update.
#     --update-creds       — Force-update existing SSH password (prompt twice).
#     --creds-stdin        — Read SSH password from standard input.
#
#   Domain credentials (BuildStream — GitLab, BSM, Postgres):
#     --set-domain-creds   — Interactive prompt for GitLab root password,
#                            GitLab SSH password, BSM auth username/password,
#                            and Postgres username/password.
#                            If creds already exist, asks yes/no to update.
#     --update-domain-creds — Force-update domain credentials interactively.
#     --domain-creds-stdin — Read domain credential JSON from standard input.
#
#   All credentials are written to test_creds.yml and encrypted with ansible-vault.
#   SSH credential flags (--set-creds / --creds-stdin) require oim_server_ip to be
#   set in test_config.yml — they are only needed for remote test execution.
#   Domain credential flags (--set-domain-creds / --domain-creds-stdin) do NOT require
#   oim_server_ip — they only write to the local test_creds.yml file.
#
# Usage:
#   bash setup_env.sh                        # Baremetal or active venv
#   bash setup_env.sh --venv                 # Create .venv/ and install there
#   bash setup_env.sh --force                 # Force-reinstall dependencies
#   bash setup_env.sh --venv --force         # Recreate .venv/ from scratch
#   bash setup_env.sh --set-creds            # Prompt for SSH password (remote mode)
#   bash setup_env.sh --update-creds         # Update existing SSH password
#   printf '%s' "$OIM_PASSWORD" | bash setup_env.sh --creds-stdin
#   bash setup_env.sh --set-domain-creds     # Prompt for GitLab + BSM + Postgres creds
#   bash setup_env.sh --debug                # Verbose pip output
#   bash setup_env.sh --help                 # Show this help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
WHEEL_PATH="${SCRIPT_DIR}/../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl"
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"

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
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
USE_VENV=false
FORCE=false
PIP_QUIET="--quiet"
SET_PASSWORD=false
UPDATE_PASSWORD=false
PASSWORD_STDIN=false
SET_DOMAIN_CREDS=false
UPDATE_DOMAIN_CREDS=false
DOMAIN_CREDS_STDIN=false
TEST_CONFIG="${SCRIPT_DIR}/test_config.yml"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)         USE_VENV=true; shift ;;
        --force)        FORCE=true; shift ;;
        --debug)        PIP_QUIET=""; shift ;;
        --set-creds|--set-password)       SET_PASSWORD=true; shift ;;
        --update-creds|--update-password) UPDATE_PASSWORD=true; shift ;;
        --creds-stdin|--password-stdin)   PASSWORD_STDIN=true; shift ;;
        --set-domain-creds) SET_DOMAIN_CREDS=true; shift ;;
        --update-domain-creds) UPDATE_DOMAIN_CREDS=true; shift ;;
        --domain-creds-stdin) DOMAIN_CREDS_STDIN=true; shift ;;
        --password|--password=*|--creds|--creds=*)
            fail "Secret-valued command-line flags are no longer supported. Pipe the password to --creds-stdin."
            ;;
        --domain-creds|--domain-creds=*)
            fail "Secret-valued command-line flags are no longer supported. Pipe JSON to --domain-creds-stdin."
            ;;
        --help|-h)
            echo ""
            echo "Build Stream — Test Environment Setup"
            echo ""
            echo "Usage: bash setup_env.sh [OPTIONS]"
            echo ""
            echo "INSTALL MODES"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  (no flag)       Baremetal mode (default)."
            echo "                  Installs dependencies into the system Python"
            echo "                  using 'pip install --user'. If a virtual env"
            echo "                  is already activated (VIRTUAL_ENV is set), the"
            echo "                  script auto-detects it and installs there instead."
            echo ""
            echo "  --venv          Create a new .venv/ virtual environment in the"
            echo "                  current directory and install all dependencies"
            echo "                  inside it. After setup, activate with:"
            echo "                    source .venv/bin/activate"
            echo ""
            echo "  --force         Force-reinstall all packages from requirements.txt."
            echo "                  With --venv, also recreates .venv/ from scratch."
            echo ""
            echo "CREDENTIAL MANAGEMENT — SSH (OIM server access)"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  SSH credentials are stored in test_creds.yml and encrypted with"
            echo "  Ansible Vault automatically.  oim_server_ip must be set in"
            echo "  test_config.yml for SSH credential flags to work."
            echo "  NOTE: Only needed for REMOTE test execution. Skip for local mode."
            echo ""
            echo "  --set-creds     Interactive SSH password setup. Prompts twice for"
            echo "                  confirmation. If already set, asks yes/no to update."
            echo ""
            echo "  --update-creds"
            echo "                  Force-update the existing SSH password. Prompts twice."
            echo "                  Overwrites test_creds.yml and re-encrypts."
            echo ""
            echo "  --creds-stdin"
            echo "                  Read the SSH password from standard input."
            echo "                  Aliases: --set-password, --update-password,"
            echo "                           --password-stdin"
            echo ""
            echo "CREDENTIAL MANAGEMENT — Domain (GitLab / BSM / Postgres)"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  These credentials are used by the build_stream playbook during"
            echo "  prepare/deploy phases.  They are stored alongside the SSH"
            echo "  password in test_creds.yml (vault-encrypted)."
            echo "  NOTE: These flags do NOT require oim_server_ip — they only"
            echo "  write to the local test_creds.yml file."
            echo ""
            echo "  --set-domain-creds"
            echo "                  Interactive prompt for:"
            echo "                    gitlab_root_password       — GitLab root user password"
            echo "                    gitlab_ssh_password        — SSH password for GitLab host"
            echo "                    build_stream_auth_username — BSM API auth username"
            echo "                    build_stream_auth_password — BSM API auth password"
            echo "                    postgres_user              — Postgres DB username"
            echo "                    postgres_password          — Postgres DB password"
            echo "                  If already set, asks yes/no to update each field."
            echo ""
            echo "  --update-domain-creds"
            echo "                  Force-update domain credentials interactively."
            echo ""
            echo "  --domain-creds-stdin"
            echo "                  Read non-interactive domain credential JSON from stdin."
            echo "                  Example:"
            echo "                    printf '%s' '{...}' | bash setup_env.sh --domain-creds-stdin"
            echo ""
            echo "OTHER OPTIONS"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  --debug         Show verbose pip install output (no --quiet flag)."
            echo ""
            echo "  --help, -h      Show this help message and exit."
            echo ""
            echo "EXAMPLES"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  bash setup_env.sh                          # Baremetal install"
            echo "  bash setup_env.sh --venv                   # Create .venv/ and install"
            echo "  bash setup_env.sh --force                  # Force-reinstall dependencies"
            echo "  bash setup_env.sh --venv --force           # Recreate .venv/ from scratch"
            echo "  bash setup_env.sh --set-creds              # Set SSH password (remote mode)"
            echo "  bash setup_env.sh --update-creds           # Update existing SSH password"
            echo "  printf '%s' \"\$OIM_PASSWORD\" | bash setup_env.sh --creds-stdin"
            echo "  bash setup_env.sh --set-domain-creds       # Set GitLab/BSM/Postgres creds"
            echo "  bash setup_env.sh --venv --set-domain-creds  # Venv + domain creds prompt"
            echo "  bash setup_env.sh --debug                  # Verbose pip output"
            echo ""
            echo "FILES"
            echo "─────────────────────────────────────────────────────────────────"
            echo "  test_config.yml       Target server IP and sync settings"
            echo "  test_creds.yml        All credentials: SSH + domain (encrypted)"
            echo "  .test_creds.key       Vault encryption key (auto-generated, gitignored)"
            echo "  .run_validation_rc    Sourceable shell snippet (baremetal mode)"
            echo "  requirements.txt      Python dependencies"
            echo ""
            exit 0
            ;;
        *)
            fail "Unknown option. Use --help for supported arguments."
            ;;
    esac
done

ssh_action_count=0
for selected in "$SET_PASSWORD" "$UPDATE_PASSWORD" "$PASSWORD_STDIN"; do
    if [ "$selected" = true ]; then
        ssh_action_count=$((ssh_action_count + 1))
    fi
done
if [ "$ssh_action_count" -gt 1 ]; then
    fail "Use only one OIM SSH credential action per invocation."
fi

domain_action_count=0
for selected in \
    "$SET_DOMAIN_CREDS" "$UPDATE_DOMAIN_CREDS" "$DOMAIN_CREDS_STDIN"; do
    if [ "$selected" = true ]; then
        domain_action_count=$((domain_action_count + 1))
    fi
done
if [ "$domain_action_count" -gt 1 ]; then
    fail "Use only one domain credential action per invocation."
fi
if [ "$PASSWORD_STDIN" = true ] && [ "$DOMAIN_CREDS_STDIN" = true ]; then
    fail "Only one credential payload can be read from stdin per invocation."
fi

CREDENTIAL_STDIN_FILE=""
_cleanup_credential_stdin() {
    if [ -n "${CREDENTIAL_STDIN_FILE:-}" ]; then
        rm -f -- "$CREDENTIAL_STDIN_FILE"
        CREDENTIAL_STDIN_FILE=""
    fi
}
trap _cleanup_credential_stdin EXIT
trap '_cleanup_credential_stdin; exit 129' HUP
trap '_cleanup_credential_stdin; exit 130' INT
trap '_cleanup_credential_stdin; exit 143' TERM

if [ "$PASSWORD_STDIN" = true ] || [ "$DOMAIN_CREDS_STDIN" = true ]; then
    old_umask=$(umask)
    umask 077
    if ! CREDENTIAL_STDIN_FILE=$(mktemp \
        "${TMPDIR:-/tmp}/omnia_build_stream_creds.XXXXXX"); then
        umask "$old_umask"
        fail "Unable to create a private credential input file."
    fi
    umask "$old_umask"
    if ! head -c 65537 > "$CREDENTIAL_STDIN_FILE"; then
        fail "Unable to read the credential payload from standard input."
    fi
    credential_stdin_size=$(wc -c < "$CREDENTIAL_STDIN_FILE")
    if [ "$credential_stdin_size" -gt 65536 ]; then
        fail "Credential input exceeds the 64 KiB limit."
    fi
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
    # User explicitly asked to create a venv
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
        "$PYTHON_CMD" -m venv "$VENV_DIR"
        ok "Virtual environment created"
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    PYTHON_CMD="${VENV_DIR}/bin/python"
    ok "Activated .venv/"

elif [ -n "${VIRTUAL_ENV:-}" ]; then
    # User has their own venv already activated
    INSTALL_MODE="active-venv"
    PIP_USER_FLAG=""
    PYTHON_CMD="${VIRTUAL_ENV}/bin/python"
    ok "Detected active virtual environment: ${VIRTUAL_ENV}"

else
    # Baremetal — install into system Python
    INSTALL_MODE="baremetal"
    PIP_USER_FLAG="--user"
    ok "Install mode: baremetal (system Python)"
fi

if ! _python_is_supported "$PYTHON_CMD"; then
    fail "The selected Python interpreter must be version 3.12 or newer: ${PYTHON_CMD}"
fi

ok "Python: $($PYTHON_CMD --version 2>&1)"
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

# pytest-order for test ordering
if ! PIP_NO_INPUT=1 "$PYTHON_CMD" -m pip show pytest-order \
    </dev/null >/dev/null 2>&1; then
    info "Installing pytest-order"
    _pip_install pytest-order $PIP_QUIET $PIP_USER_FLAG
fi

_omnia_auto_has_required_features() {
    "$PYTHON_CMD" -c '
import inspect
import omnia_auto
params = inspect.signature(omnia_auto.sync_files).parameters
if not {"auth_secret", "port"}.issubset(params) or not callable(omnia_auto.connection_params):
    raise SystemExit(1)
' 2>/dev/null \
        && "$PYTHON_CMD" -m omnia_auto write-field --help 2>/dev/null \
            | grep -q -- "--value-stdin" \
        && "$PYTHON_CMD" -m omnia_auto write-fields --help 2>/dev/null \
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
# Step 4: Credential helpers
# ─────────────────────────────────────────────────────────────────────────────

# Check that oim_server_ip is configured in test_config.yml (SSH only)
_check_oim_server_ip() {
    if [ ! -f "$TEST_CONFIG" ]; then
        fail "test_config.yml not found at ${TEST_CONFIG}. Create it first."
    fi
    local oim_ip
    oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -z "$oim_ip" ]; then
        fail "oim_server_ip is blank in test_config.yml. Set the target server IP first:\n         vi ${TEST_CONFIG}\n         SSH password is only needed for remote test execution."
    fi
    ok "Target server: ${oim_ip}"
}

_credential_cli() {
    "$PYTHON_CMD" -m omnia_auto "$@"
}

# Write SSH credentials to the shared test_creds.yml file.
_write_ssh_creds() {
    local _pass="$1"
    printf '%s' "$_pass" | _credential_cli write-field \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --field oim_password --value-stdin >/dev/null
    ok "SSH credentials saved: test_creds.yml (encrypted)"
}

_write_ssh_creds_stdin() {
    _credential_cli write-field \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --field oim_password --value-stdin \
        < "$CREDENTIAL_STDIN_FILE" >/dev/null
    ok "SSH credentials saved: test_creds.yml (encrypted)"
}

# Return success only when every named field exists and is non-empty. Values
# remain inside the pipeline and are never printed or stored by this script.
_credential_fields_are_set() {
    local _field
    for _field in "$@"; do
        if ! _credential_cli read-field \
            --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
            --field "$_field" 2>/dev/null \
            | grep -z '[^[:space:]]' >/dev/null; then
            return 1
        fi
    done
    return 0
}

# Ask yes/no with strict validation (loops until valid answer)
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

# Build Stream domain credential fields. GitLab credentials are mandatory;
# BSM and Postgres fields are conditional and may remain empty.
DOMAIN_CRED_SPEC='[
  {"field":"gitlab_root_password","label":"GitLab Root Password","group":"GitLab Credentials","secret":true,"confirm":true},
  {"field":"gitlab_ssh_password","label":"GitLab SSH Password","secret":true,"confirm":true},
  {"field":"build_stream_auth_username","label":"BuildStream Auth Username","group":"BuildStream Manager Credentials","secret":false,"optional":true},
  {"field":"build_stream_auth_password","label":"BuildStream Auth Password","secret":true,"confirm":true,"optional":true},
  {"field":"postgres_user","label":"Postgres Username","group":"Postgres Credentials","secret":false,"optional":true},
  {"field":"postgres_password","label":"Postgres Password","secret":true,"confirm":true,"optional":true}
]'

# Prompt for Build Stream domain credentials through omnia_auto.
_prompt_domain_creds() {
    echo ""
    echo -e "  ${CYAN}BuildStream Domain Credentials${NC}"
    echo -e "  ${CYAN}Press Enter to keep an existing value.${NC}"

    _credential_cli prompt-fields \
        --creds-path "$CREDS_FILE" \
        --key-path "$CREDS_KEY" \
        --spec "$DOMAIN_CRED_SPEC" </dev/tty

    if ! _credential_fields_are_set \
        gitlab_root_password gitlab_ssh_password; then
        fail "GitLab root and SSH passwords are mandatory. Re-run credential setup."
    fi

    echo ""
    ok "Domain credentials saved: test_creds.yml (encrypted)"
}

# ─────────────────────────────────────────────────────────────────────────────
# SSH credential dispatch
# ─────────────────────────────────────────────────────────────────────────────
if [ "$PASSWORD_STDIN" = true ]; then
    _check_oim_server_ip
    info "Reading SSH password from standard input"
    _write_ssh_creds_stdin

elif [ "$UPDATE_PASSWORD" = true ]; then
    _check_oim_server_ip
    if ! _credential_fields_are_set oim_password; then
        fail "No SSH password found. Use --set-password to create one first."
    fi
    echo -e "\n  ${CYAN}Update SSH password for the target OIM server.${NC}\n"
    _cred_input=$(
        _credential_cli prompt-and-confirm --message "SSH Password" </dev/tty
    )
    _write_ssh_creds "$_cred_input"
    unset _cred_input

elif [ "$SET_PASSWORD" = true ]; then
    _check_oim_server_ip

    if _credential_fields_are_set oim_password; then
        warn "SSH password is already set."
        if _ask_yes_no "  Do you want to update the SSH password?"; then
            echo -e "\n  ${CYAN}Enter new SSH password for the target OIM server.${NC}\n"
            _cred_input=$(
                _credential_cli prompt-and-confirm --message "SSH Password" </dev/tty
            )
            _write_ssh_creds "$_cred_input"
            unset _cred_input
        else
            ok "SSH password update skipped."
        fi
    else
        echo -e "\n  ${CYAN}Enter SSH password for the target OIM server.${NC}\n"
        _cred_input=$(
            _credential_cli prompt-and-confirm --message "SSH Password" </dev/tty
        )
        _write_ssh_creds "$_cred_input"
        unset _cred_input
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Domain credential dispatch
#
# Domain credentials are primarily stored on the target server at:
#   /opt/omnia/build_stream/input/<project>/build_stream_credentials.yml
#
# The build_stream.yml playbook creates this file during deployment.
# --set-domain-creds checks the server first; if creds already exist
# there, prompting is skipped.
# ─────────────────────────────────────────────────────────────────────────────

# Check if domain credentials already exist on the target server
_check_server_creds_exist() {
    local oim_ip
    oim_ip=$(grep -E '^oim_server_ip:' "$TEST_CONFIG" 2>/dev/null | sed 's/^oim_server_ip:[[:space:]]*//; s/["'\''[:space:]]//g' || true)
    if [ -z "$oim_ip" ]; then
        return 1  # can't check server, proceed with prompts
    fi

    local server_creds_path="/opt/omnia/build_stream/input/project_default/build_stream_credentials.yml"

    # Try SSH to check if the file exists and has content
    local ssh_result
    ssh_result=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 \
        "$oim_ip" "test -s ${server_creds_path} && echo 'exists'" 2>/dev/null || true)

    if [ "$ssh_result" = "exists" ]; then
        return 0  # creds exist on server
    fi
    return 1  # creds don't exist or SSH failed
}

if [ "$DOMAIN_CREDS_STDIN" = true ]; then
    info "Reading domain credentials from standard input"
    _credential_cli write-fields \
        --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --fields-stdin < "$CREDENTIAL_STDIN_FILE" >/dev/null
    ok "Domain credentials saved: test_creds.yml (encrypted)"

elif [ "$UPDATE_DOMAIN_CREDS" = true ] || [ "$SET_DOMAIN_CREDS" = true ]; then
    if [ "$SET_DOMAIN_CREDS" = true ] && _check_server_creds_exist; then
        ok "Domain credentials already configured on the target server."
        ok "Source: /opt/omnia/build_stream/input/project_default/build_stream_credentials.yml"
        ok "Test cases will read credentials directly from the server."
        ok "To force a local update, use --update-domain-creds."
        SET_DOMAIN_CREDS=false
    fi

    if [ "$UPDATE_DOMAIN_CREDS" = true ] || [ "$SET_DOMAIN_CREDS" = true ]; then
        if [ "$SET_DOMAIN_CREDS" = true ]; then
            info "Server credentials not found — prompting for domain credentials"
        fi
        _prompt_domain_creds
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# No credential flags — status report
# ─────────────────────────────────────────────────────────────────────────────
if [ "$PASSWORD_STDIN" = false ] && [ "$UPDATE_PASSWORD" = false ] && [ "$SET_PASSWORD" = false ] \
   && [ "$DOMAIN_CREDS_STDIN" = false ] && [ "$SET_DOMAIN_CREDS" = false ] \
   && [ "$UPDATE_DOMAIN_CREDS" = false ]; then
    if _credential_fields_are_set oim_password; then
        ok "SSH credentials: test_creds.yml (encrypted)"
    else
        warn "No SSH credentials (test_creds.yml)"
        warn "  Set with: bash setup_env.sh --set-password"
    fi
    if _credential_fields_are_set gitlab_root_password gitlab_ssh_password; then
        ok "Build Stream domain credentials: test_creds.yml (encrypted)"
    else
        warn "Build Stream domain credentials are incomplete"
        warn "  Set with: bash setup_env.sh --set-domain-creds"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Register run_validation + tab completion (venv modes only)
# ─────────────────────────────────────────────────────────────────────────────
_inject_tab_completion() {
    local activate_script="$1"
    local marker="# >>> build-stream-test >>>"
    local marker_end="# <<< build-stream-test <<<"
    local module_dir="$SCRIPT_DIR"

    # Remove any previous block (idempotent)
    if grep -q "${marker}" "${activate_script}" 2>/dev/null; then
        sed -i "/${marker}/,/${marker_end}/d" "${activate_script}"
    fi

    cat >> "${activate_script}" << BSM_ACTIVATE_EOF

${marker}
# Added by setup_env.sh — shell function and tab-completion

# Shell function so run_validation works without ./
run_validation() {
    "${module_dir}/run_validation.sh" "\$@"
}

# Tab-completion for run_validation
_run_validation_completions() {
    local cur prev
    cur="\${COMP_WORDS[COMP_CWORD]}"
    prev="\${COMP_WORDS[COMP_CWORD-1]}"
    local fvt_dir="${module_dir}/fvt"
    local scenarios=""
    if [ -d "\${fvt_dir}" ]; then
        for d in "\${fvt_dir}"/*/; do
            [ -d "\$d" ] || continue
            local name
            name="\$(basename "\$d")"
            [ "\$name" = "__pycache__" ] && continue
            scenarios="\${scenarios} \${name}"
        done
    fi
    local commands="deploy verify test"
    local special="all list help --config --help"
    local options="--suite --marker -v --verbose --debug"
    local markers="sanity functional regression deploy"
    case "\$COMP_CWORD" in
        1) COMPREPLY=( \$(compgen -W "\${scenarios} \${special}" -- "\$cur") ) ;;
        2)
            case "\$prev" in
                list|help|--help|-h|--config) COMPREPLY=() ;;
                *) COMPREPLY=( \$(compgen -W "\${commands}" -- "\$cur") ) ;;
            esac ;;
        *)
            case "\$prev" in
                --suite)
                    local scenario="\${COMP_WORDS[1]}"
                    local suites=""
                    if [ -d "\${fvt_dir}/\${scenario}" ]; then
                        for d in "\${fvt_dir}/\${scenario}"/*/; do
                            [ -d "\$d" ] || continue
                            local name
                            name="\$(basename "\$d")"
                            [ "\$name" = "__pycache__" ] && continue
                            suites="\${suites} \${name}"
                        done
                    fi
                    COMPREPLY=( \$(compgen -W "\${suites}" -- "\$cur") ) ;;
                --marker) COMPREPLY=( \$(compgen -W "\${markers}" -- "\$cur") ) ;;
                *) COMPREPLY=( \$(compgen -W "\${options}" -- "\$cur") ) ;;
            esac ;;
    esac
}
complete -F _run_validation_completions run_validation

${marker_end}
BSM_ACTIVATE_EOF
}

if [ "$INSTALL_MODE" = "venv" ]; then
    _inject_tab_completion "${VENV_DIR}/bin/activate"
    ok "Registered run_validation + tab-completion in .venv/bin/activate"
elif [ "$INSTALL_MODE" = "active-venv" ]; then
    _inject_tab_completion "${VIRTUAL_ENV}/bin/activate"
    ok "Registered run_validation + tab-completion in ${VIRTUAL_ENV}/bin/activate"
else
    # Baremetal — create a sourceable shell snippet
    SHELL_SNIPPET="${SCRIPT_DIR}/.run_validation_rc"
    _inject_tab_completion_baremetal() {
        cat > "$SHELL_SNIPPET" << BARE_EOF
# Source this file to get run_validation + tab-completion
# Usage: source ${SHELL_SNIPPET}

run_validation() {
    "${SCRIPT_DIR}/run_validation.sh" "\$@"
}

_run_validation_completions() {
    local cur prev
    cur="\${COMP_WORDS[COMP_CWORD]}"
    prev="\${COMP_WORDS[COMP_CWORD-1]}"
    local fvt_dir="${SCRIPT_DIR}/fvt"
    local scenarios=""
    if [ -d "\${fvt_dir}" ]; then
        for d in "\${fvt_dir}"/*/; do
            [ -d "\$d" ] || continue
            local name
            name="\$(basename "\$d")"
            [ "\$name" = "__pycache__" ] && continue
            scenarios="\${scenarios} \${name}"
        done
    fi
    local commands="deploy verify test"
    local special="all list help --config --help"
    local options="--suite --marker -v --verbose --debug"
    local markers="sanity functional regression deploy"
    case "\$COMP_CWORD" in
        1) COMPREPLY=( \$(compgen -W "\${scenarios} \${special}" -- "\$cur") ) ;;
        2)
            case "\$prev" in
                list|help|--help|-h|--config) COMPREPLY=() ;;
                *) COMPREPLY=( \$(compgen -W "\${commands}" -- "\$cur") ) ;;
            esac ;;
        *)
            case "\$prev" in
                --suite)
                    local scenario="\${COMP_WORDS[1]}"
                    local suites=""
                    if [ -d "\${fvt_dir}/\${scenario}" ]; then
                        for d in "\${fvt_dir}/\${scenario}"/*/; do
                            [ -d "\$d" ] || continue
                            local name
                            name="\$(basename "\$d")"
                            [ "\$name" = "__pycache__" ] && continue
                            suites="\${suites} \${name}"
                        done
                    fi
                    COMPREPLY=( \$(compgen -W "\${suites}" -- "\$cur") ) ;;
                --marker) COMPREPLY=( \$(compgen -W "\${markers}" -- "\$cur") ) ;;
                *) COMPREPLY=( \$(compgen -W "\${options}" -- "\$cur") ) ;;
            esac ;;
    esac
}
complete -F _run_validation_completions run_validation
BARE_EOF
    }
    _inject_tab_completion_baremetal
    ok "Created shell snippet: .run_validation_rc"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Make scripts executable
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
        echo "    run_validation --help"
        echo "    run_validation gitlab_install verify --marker sanity"
        ;;
    active-venv)
        echo "  Next steps (venv already active):"
        echo "    run_validation --help"
        echo "    run_validation gitlab_install verify --marker sanity"
        ;;
    baremetal)
        echo "  Next steps:"
        echo "    source .run_validation_rc              # Load run_validation + tab-completion"
        echo "    run_validation --help"
        echo "    run_validation gitlab_install verify --marker sanity"
        ;;
esac

echo ""
echo "  Credentials (two separate types):"
echo ""
echo "    1. SSH credentials (test_creds.yml) — for REMOTE test execution only:"
if _credential_fields_are_set oim_password; then
    echo "       SSH credentials are set (encrypted)"
    echo "       To update:  bash setup_env.sh --set-password"
    echo "       Force update: bash setup_env.sh --update-password"
else
    echo "       No SSH credentials set."
    echo "       For remote mode: bash setup_env.sh --set-password"
fi
echo ""
echo "    2. Domain credentials (GitLab / BSM / Postgres):"
echo "       Used by the build_stream playbook for deployment."
echo "       To set/update: bash setup_env.sh --set-domain-creds"
echo "       Force update:  bash setup_env.sh --update-domain-creds"

echo ""
echo "================================================================="
echo ""
