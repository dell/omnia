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
# BuildStream System Test — Environment Setup
# =============================================================================
# Installs test automation dependencies and configures credentials.
#
# Credential stores (all Ansible Vault encrypted, 0600):
#   1. test_creds.yml (this directory) — OIM SSH password for remote mode.
#   2. Domain credential stores, at <DOMAIN>_DATA_PATH (or
#      OMNIA_DATA_PATH/<domain>)/input/<OMNIA_PROJECT_NAME>/ from omnia.env,
#      in the order the suite needs them:
#        repo_manager         repo_manager_config_credentials.yml
#        image_build_manager  image_build_credentials.yml
#        orchestrator         orchestrator_credentials.yml
#        build_stream         build_stream_credentials.yml
#      The playbooks prompt when a store is missing; setting them here
#      lets the whole suite run unattended.
#
# Usage:
#   ./setup_env.sh --venv                  Create .venv and install dependencies
#   ./setup_env.sh                         Install into the active/.venv and show
#                                          credential status
#   ./setup_env.sh --set-creds             Prompt for the OIM SSH password
#   ./setup_env.sh --update-creds          Update existing test credentials
#   test-credential-json-provider | ./setup_env.sh --creds-stdin
#   ./setup_env.sh --set-domain-creds      Prompt every domain store in order
#   ./setup_env.sh --set-domain-creds --domain build_stream
#   ./setup_env.sh --update-domain-creds [--domain <name>]
#   credential-json-provider | ./setup_env.sh --domain-creds-stdin
#       JSON keyed by domain, e.g. {"repo_manager": {"pulp_password": "..."},
#       "build_stream": {...}}; only the listed domains are written.
#   ./setup_env.sh --help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"
TEST_CONFIG="${SCRIPT_DIR}/test_config.yml"
OMNIA_ENV_FILE="/etc/omnia/omnia.env"
cd "$SCRIPT_DIR"

# ── Test credentials (local) ──
CREDS_FILE="${SCRIPT_DIR}/test_creds.yml"
CREDS_KEY="${SCRIPT_DIR}/.test_creds.key"
TEST_CRED_SPEC='[
  {"field":"oim_password","label":"OIM SSH Password","group":"Remote OIM","secret":true,"confirm":true,"min_length":1}
]'

# ── Domain credentials (at env-var path), in suite order ──
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
declare -A DOMAIN_CRED_SPEC=(
    [repo_manager]='[
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
  {"field":"build_stream_auth_password","label":"BuildStream Auth Password","secret":true,"confirm":true},
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
# Step 1: Arguments
# ─────────────────────────────────────────────────────────────────────────────
USE_VENV=false
SET_CREDS=false
UPDATE_CREDS=false
CREDS_FROM_STDIN=false
SET_DOMAIN_CREDS=false
UPDATE_DOMAIN_CREDS=false
DOMAIN_CREDS_FROM_STDIN=false
SELECTED_DOMAIN=""

while [ $# -gt 0 ]; do
    case "$1" in
        --venv)                USE_VENV=true; shift ;;
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
        -h|--help)             usage; exit 0 ;;
        *)                     usage; fail "Unknown option: $1" ;;
    esac
done

test_actions=0
for flag in "$SET_CREDS" "$UPDATE_CREDS" "$CREDS_FROM_STDIN"; do
    [ "$flag" = true ] && test_actions=$((test_actions + 1))
done
domain_actions=0
for flag in "$SET_DOMAIN_CREDS" "$UPDATE_DOMAIN_CREDS" "$DOMAIN_CREDS_FROM_STDIN"; do
    [ "$flag" = true ] && domain_actions=$((domain_actions + 1))
done
[ "$test_actions" -le 1 ] || fail "Use only one test credential action per invocation."
[ "$domain_actions" -le 1 ] || fail "Use only one domain credential action per invocation."
if [ "$CREDS_FROM_STDIN" = true ] && [ "$DOMAIN_CREDS_FROM_STDIN" = true ]; then
    fail "Only one credential payload can be read from stdin per invocation."
fi

SELECTED_DOMAINS=("${DOMAINS[@]}")
if [ -n "$SELECTED_DOMAIN" ]; then
    [ -n "${DOMAIN_CREDS_FILE[$SELECTED_DOMAIN]+set}" ] \
        || fail "Unknown domain '$SELECTED_DOMAIN'. Use one of: ${DOMAINS[*]}"
    SELECTED_DOMAINS=("$SELECTED_DOMAIN")
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Python environment
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}=================================================================${NC}"
echo -e "${CYAN}  BuildStream System Test — Environment Setup${NC}"
echo -e "${CYAN}=================================================================${NC}"

command -v python3 >/dev/null 2>&1 || fail "python3 is required"
if [ "$USE_VENV" = true ]; then
    [ -d "$VENV_DIR" ] || { info "Creating virtual environment: $VENV_DIR"; python3 -m venv "$VENV_DIR"; }
    PYTHON_CMD="$VENV_DIR/bin/python"
    INSTALL_MODE="venv"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
    PYTHON_CMD="${VIRTUAL_ENV}/bin/python"
    INSTALL_MODE="active-venv"
elif [ -x "$VENV_DIR/bin/python" ]; then
    PYTHON_CMD="$VENV_DIR/bin/python"
    INSTALL_MODE="venv"
else
    fail "No virtual environment. Run: ./setup_env.sh --venv"
fi
# The credential CLI calls ansible-vault from the same environment.
export PATH="$(dirname "$PYTHON_CMD"):${PATH}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Dependencies
# ─────────────────────────────────────────────────────────────────────────────
info "Installing dependencies from requirements.txt"
"$PYTHON_CMD" -m pip install --quiet --upgrade pip
"$PYTHON_CMD" -m pip install --quiet -r "$REQUIREMENTS"
ok "All dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Credential helpers (delegate to the omnia_auto credential CLI)
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

_domain_paths_known() { [ -n "$OMNIA_DATA_PATH_VALUE" ] && [ -n "$OMNIA_PROJECT_NAME_VALUE" ]; }
_require_domain_paths() {
    _domain_paths_known || fail "OMNIA_DATA_PATH and OMNIA_PROJECT_NAME must be set in ${OMNIA_ENV_FILE} (run ./omnia.sh --setup-venv)"
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

# Domain stores keep nested data the flat credential CLI cannot load, so they
# go through utility/domain_credentials.py (merges top-level fields only).
_domain_cli() {
    local _command="$1" _domain="$2"
    "$PYTHON_CMD" "${SCRIPT_DIR}/utility/domain_credentials.py" "$_command" \
        --creds-path "$(_domain_creds_path "$_domain")" \
        --key-path "$(_domain_creds_key_path "$_domain")" \
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

_test_credentials_are_set() {
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

# BuildStream stores an Argon2id hash of the auth password next to it
# (same parameters as the BuildStream domain suite and build_stream.yml).
_write_build_stream_auth_hash() {
    _domain_cli hash-auth build_stream </dev/null
    ok "BuildStream authentication password hash generated"
    warn "If BuildStream is already deployed, apply the change with: ./omnia.sh -r build_stream"
}

_after_domain_write() {
    local _domain="$1"
    chmod 0600 "$(_domain_creds_path "$_domain")" "$(_domain_creds_key_path "$_domain")"
    [ "$_domain" = build_stream ] && _write_build_stream_auth_hash
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
    _payload=$(cat)
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
# Step 5: Test credential dispatch (test_creds.yml)
# ─────────────────────────────────────────────────────────────────────────────
_prompt_test_credentials() {
    _credential_cli prompt-fields --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --spec "$TEST_CRED_SPEC" --require-complete </dev/tty
    chmod 0600 "$CREDS_FILE" "$CREDS_KEY"
    ok "Test credentials saved: test_creds.yml (encrypted)"
}

if [ "$CREDS_FROM_STDIN" = true ]; then
    info "Reading test credential JSON from standard input"
    _credential_cli write-fields --creds-path "$CREDS_FILE" --key-path "$CREDS_KEY" \
        --fields-stdin --spec "$TEST_CRED_SPEC" --require-complete >/dev/null
    chmod 0600 "$CREDS_FILE" "$CREDS_KEY"
    ok "Test credentials saved: test_creds.yml (encrypted)"
elif [ "$UPDATE_CREDS" = true ]; then
    _test_credentials_are_set || fail "No valid test credentials found. Use --set-creds first."
    _show_oim_server_ip
    _prompt_test_credentials
elif [ "$SET_CREDS" = true ]; then
    _show_oim_server_ip
    if _test_credentials_are_set && ! _ask_yes_no "  Test credentials exist. Update them?"; then
        ok "Test credential update skipped."
    else
        _prompt_test_credentials
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Domain credential dispatch (four domain stores)
# ─────────────────────────────────────────────────────────────────────────────
if [ "$DOMAIN_CREDS_FROM_STDIN" = true ] || [ "$UPDATE_DOMAIN_CREDS" = true ] \
        || [ "$SET_DOMAIN_CREDS" = true ]; then
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
info "Credential status"
if _test_credentials_are_set; then
    ok "Test credentials: test_creds.yml (encrypted)"
else
    warn "No test credentials (test_creds.yml) — needed only when oim_server_ip is set"
    warn "  Set with: ./setup_env.sh --set-creds"
fi
if ! _domain_paths_known; then
    warn "Domain credential status unavailable: OMNIA_DATA_PATH/OMNIA_PROJECT_NAME not set in ${OMNIA_ENV_FILE}"
    DOMAINS_TO_SHOW=()
else
    DOMAINS_TO_SHOW=("${DOMAINS[@]}")
fi
for domain in "${DOMAINS_TO_SHOW[@]}"; do
    if _domain_credentials_are_set "$domain"; then
        ok "${domain}: $(_domain_creds_path "$domain") (encrypted)"
    else
        warn "No ${domain} credentials: $(_domain_creds_path "$domain")"
        warn "  Set with: ./setup_env.sh --set-domain-creds --domain ${domain}"
    fi
done

chmod +x "${SCRIPT_DIR}/run_validation.sh" "${SCRIPT_DIR}/_run.py" 2>/dev/null || true

echo ""
echo -e "${GREEN}=================================================================${NC}"
echo -e "${GREEN}  Environment Ready  (${INSTALL_MODE})${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo ""
echo "  Next steps:"
[ "$INSTALL_MODE" = venv ] && echo "    source .venv/bin/activate"
echo "    ./run_validation.sh --help"
echo "    ./run_validation.sh e2e_build_stream list"
echo ""
