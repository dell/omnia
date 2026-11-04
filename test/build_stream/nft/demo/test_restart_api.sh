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
# Restart API demo: register a client, create a job and call the restart stage.
# =============================================================================
# Usage: BSM_HOST=<ip> [BSM_PORT=8010] [BSM_CACERT=<path>] ./test_restart_api.sh
#
# The BuildStream auth username and password are asked with hidden prompts.
# TLS is verified against BSM_CACERT (default
# /opt/omnia/build_stream/ssl/bs_cert.pem). Secrets reach curl only through a
# private (0600) config file, never the command line, and are never printed.
# =============================================================================
set -euo pipefail

BSM_HOST="${BSM_HOST:?Set BSM_HOST to the BuildStream API host}"
BSM_PORT="${BSM_PORT:-8010}"
BSM_CACERT="${BSM_CACERT:-/opt/omnia/build_stream/ssl/bs_cert.pem}"
BASE="https://${BSM_HOST}:${BSM_PORT}/api/v1"
[ -r "$BSM_CACERT" ] || { echo "BuildStream certificate not readable: $BSM_CACERT" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 1; }

umask 077
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT

read -r -p "BuildStream auth username: " BSM_USER
read -r -s -p "BuildStream auth password: " BSM_PASS
echo

# api <method> <path> <header-or-empty> [curl args...] -> body on stdout, HTTP code in $WORK/code
api() {
    local method="$1" path="$2" header="$3"
    shift 3
    : > "${WORK}/curl.conf"
    [ -n "$header" ] && printf 'header = "%s"\n' "$header" > "${WORK}/curl.conf"
    curl --silent --show-error --cacert "$BSM_CACERT" --config "${WORK}/curl.conf" \
        -X "$method" -o "${WORK}/body" -w '%{http_code}' "$@" "${BASE}${path}" > "${WORK}/code"
    cat "${WORK}/body"
}

basic="$(printf '%s:%s' "$BSM_USER" "$BSM_PASS" | base64 -w0)"
echo "=== Step 1: register a client"
api POST /auth/register "Authorization: Basic ${basic}" -H "Content-Type: application/json" \
    -d '{"client_name":"restart-demo","allowed_scopes":["job:write"],"grant_types":["client_credentials"]}' \
    > "${WORK}/client.json"
CLIENT_ID="$(jq -r .client_id "${WORK}/client.json")"
echo "HTTP $(cat "${WORK}/code"), client_id ${CLIENT_ID}"

echo "=== Step 2: get a token"
jq -r '"grant_type=client_credentials&client_id=\(.client_id)&client_secret=\(.client_secret)"' \
    "${WORK}/client.json" > "${WORK}/form"
api POST /auth/token "" -H "Content-Type: application/x-www-form-urlencoded" \
    --data "@${WORK}/form" > "${WORK}/token.json"
TOKEN="$(jq -r .access_token "${WORK}/token.json")"
echo "HTTP $(cat "${WORK}/code"), token received"

echo "=== Step 3: create a job"
api POST /jobs "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
    -H "Idempotency-Key: $(uuidgen)" -d "{\"client_id\":\"${CLIENT_ID}\"}" > "${WORK}/job.json"
JOB_ID="$(jq -r .job_id "${WORK}/job.json")"
echo "HTTP $(cat "${WORK}/code"), job_id ${JOB_ID}"

check() {  # check <title> <expected> <path> <header>
    echo "=== $1 (expect $2)"
    api POST "$3" "$4" | jq . 2>/dev/null || true
    echo "HTTP $(cat "${WORK}/code")"
}
check "TEST 1: trigger restart" 202 "/jobs/${JOB_ID}/stages/restart" "Authorization: Bearer ${TOKEN}"
check "TEST 2: duplicate restart" 409 "/jobs/${JOB_ID}/stages/restart" "Authorization: Bearer ${TOKEN}"
check "TEST 3: invalid job ID" 400 "/jobs/not-valid/stages/restart" "Authorization: Bearer ${TOKEN}"
check "TEST 4: unknown job" 404 "/jobs/$(uuidgen)/stages/restart" "Authorization: Bearer ${TOKEN}"
check "TEST 5: no auth" 401 "/jobs/${JOB_ID}/stages/restart" ""

echo "=== Playbook queue"
for dir in /opt/omnia/build_stream/playbook_queue/requests /opt/omnia/build_stream/playbook_queue/processing; do
    [ -d "$dir" ] && ls -la "$dir"
done
exit 0
