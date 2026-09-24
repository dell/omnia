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

set -euo pipefail

UTILITY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${UTILITY_DIR}/openldap_server_config.yml"
CREDENTIAL_FILE="${UTILITY_DIR}/openldap_server_credentials.yml"
CREDENTIAL_KEY_FILE="${UTILITY_DIR}/.openldap_server_credentials.key"
PYTHON_BIN="${OMNIA_LDAP_PYTHON_BIN:-python3}"
DEPLOY=false
PLAIN_FILE=""
VAULT_TEMP_FILE=""

usage() {
    cat <<'EOF'
Create the encrypted credential store for the standalone OpenLDAP test server.

Usage: ./utility/setup_ldap_server.sh [--deploy]

  --deploy  Run LDAP server reconciliation after creating and validating the
            encrypted credential store. Without this option, no LDAP server
            state is changed.
  --help    Display this help.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --deploy) DEPLOY=true; shift ;;
        --help|-h) usage; exit 0 ;;
        *) echo "ERROR: Unsupported option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

cleanup() {
    if [[ -n "$PLAIN_FILE" ]]; then
        rm -f -- "$PLAIN_FILE"
    fi
    if [[ -n "$VAULT_TEMP_FILE" ]]; then
        rm -f -- "$VAULT_TEMP_FILE"
    fi
}
trap cleanup EXIT HUP INT TERM
umask 077

for command_name in ansible-vault openssl "$PYTHON_BIN"; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "ERROR: Required command is unavailable: $command_name" >&2
        exit 1
    fi
done

if [[ -e "$CREDENTIAL_FILE" ]]; then
    read -r -p "Encrypted LDAP credentials already exist. Replace them? [y/N]: " replace
    if [[ ! "$replace" =~ ^[Yy]$ ]]; then
        echo "No changes were made."
        exit 0
    fi
fi

read_name() {
    local prompt="$1"
    local default_value="$2"
    local value=""
    while true; do
        read -r -p "$prompt [$default_value]: " value
        value="${value:-$default_value}"
        if [[ "$value" =~ ^[A-Za-z_][A-Za-z0-9_.-]*$ ]]; then
            REPLY="$value"
            return
        fi
        echo "Use letters, numbers, underscore, period, or hyphen; the first character must be a letter or underscore."
    done
}

read_required_secret() {
    local label="$1"
    local first=""
    local second=""
    while true; do
        read -r -s -p "$label: " first
        echo
        if [[ -z "$first" ]]; then
            echo "A value is required."
            continue
        fi
        read -r -s -p "Confirm $label: " second
        echo
        if [[ "$first" == "$second" ]]; then
            REPLY="$first"
            return
        fi
        echo "Values do not match; try again."
    done
}

read_optional_secret() {
    local label="$1"
    local first=""
    local second=""
    while true; do
        read -r -s -p "$label (press Enter to skip): " first
        echo
        if [[ -z "$first" ]]; then
            REPLY=""
            return
        fi
        read -r -s -p "Confirm $label: " second
        echo
        if [[ "$first" == "$second" ]]; then
            REPLY="$first"
            return
        fi
        echo "Values do not match; try again."
    done
}

yaml_quote() {
    local value="$1"
    value="${value//\'/\'\'}"
    printf "'%s'" "$value"
}

echo "Standalone OpenLDAP credential setup"
echo "Sensitive input is hidden and stored only in an ignored Ansible Vault file."
echo

read_name "Directory administrator username" "admin"
admin_username="$REPLY"
read_required_secret "Directory administrator password"
admin_credential="$REPLY"
read_optional_secret "Remote SSH password"
ssh_credential="$REPLY"

while true; do
    read -r -p "Number of LDAP test users to create [1]: " user_count
    user_count="${user_count:-1}"
    if [[ "$user_count" =~ ^[0-9]+$ ]] \
        && (( user_count >= 1 && user_count <= 100 )); then
        break
    fi
    echo "Enter a whole number from 1 through 100."
done

declare -a ldap_usernames=()
declare -a ldap_credentials=()
for ((index = 1; index <= user_count; index++)); do
    echo
    read_name "LDAP test user ${index} username" "ldapuser${index}"
    username="$REPLY"
    for existing_username in "${ldap_usernames[@]:-}"; do
        if [[ "$username" == "$existing_username" ]]; then
            echo "ERROR: LDAP usernames must be unique: $username" >&2
            exit 1
        fi
    done
    read_required_secret "LDAP test user ${index} password"
    ldap_usernames+=("$username")
    ldap_credentials+=("$REPLY")
done

PLAIN_FILE="$(mktemp /tmp/omnia-openldap-credentials.XXXXXX)"
{
    printf 'openldap_admin_username: '
    yaml_quote "$admin_username"
    printf '\nopenldap_admin_credential: '
    yaml_quote "$admin_credential"
    printf '\nopenldap_server_ssh_credential: '
    yaml_quote "$ssh_credential"
    printf '\nopenldap_users:\n'
    for ((index = 0; index < user_count; index++)); do
        printf '  - username: '
        yaml_quote "${ldap_usernames[$index]}"
        printf '\n    credential: '
        yaml_quote "${ldap_credentials[$index]}"
        printf '\n'
    done
} > "$PLAIN_FILE"
chmod 0600 "$PLAIN_FILE"

if [[ ! -f "$CREDENTIAL_KEY_FILE" ]]; then
    openssl rand -base64 48 > "$CREDENTIAL_KEY_FILE"
fi
chmod 0600 "$CREDENTIAL_KEY_FILE"

VAULT_TEMP_FILE="$(mktemp "${UTILITY_DIR}/.openldap-server-vault.XXXXXX")"
ansible-vault encrypt \
    --vault-password-file "$CREDENTIAL_KEY_FILE" \
    --output "$VAULT_TEMP_FILE" \
    "$PLAIN_FILE" >/dev/null
chmod 0600 "$VAULT_TEMP_FILE"
mv -f -- "$VAULT_TEMP_FILE" "$CREDENTIAL_FILE"
VAULT_TEMP_FILE=""

if ! head -n 1 "$CREDENTIAL_FILE" | grep -q "^\$ANSIBLE_VAULT;"; then
    echo "ERROR: Credential encryption verification failed." >&2
    exit 1
fi

echo
echo "Encrypted credentials created: $CREDENTIAL_FILE"
echo "Local vault key created/reused: $CREDENTIAL_KEY_FILE"

utility_arguments=(
    "$UTILITY_DIR/create_ldap_server.py"
    --config "$CONFIG_FILE"
    --credentials "$CREDENTIAL_FILE"
    --credentials-key "$CREDENTIAL_KEY_FILE"
)

if [[ "$DEPLOY" == true ]]; then
    "$PYTHON_BIN" "${utility_arguments[@]}"
else
    "$PYTHON_BIN" "${utility_arguments[@]}" --check
    echo
    echo "Configuration is ready. Deploy with:"
    echo "  python3 utility/create_ldap_server.py"
fi
