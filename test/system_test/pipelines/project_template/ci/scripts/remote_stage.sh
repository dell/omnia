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
# remote_stage.sh - run one SVT stage on the cluster's OIM (GitLab job wrapper)
# =============================================================================
# Usage: bash ci/scripts/remote_stage.sh [--stop]
#
# Job variables (set by render_pipeline.py): SVT_CLUSTER SVT_STAGE SVT_THEME
# SVT_RUN_ID [SVT_CASE SVT_FULL_LOG SVT_CREDENTIAL_MODULES]; SVT_ID_TOKEN comes
# from id_tokens. Steps:
#   1. OIM SSH access from OpenBao (<openbao_path>/oim: ssh_private_key, else
#      password) into a private temp directory; host key pinned when
#      oim_host_key is set
#   2. initialization only: clone/fetch clone_url, check out clone_ref (the
#      resolved commit is printed), upload user_inputs.yml and test_config.yml
#   3. start "run_svt.sh <stage> --quiet" as a transient systemd unit (it
#      survives SSH drops; RuntimeMaxSec = the job timeout)
#   4. follow it: one progress line per minute, or the complete log when
#      SVT_FULL_LOG=true; on failure print the last lines and the log paths
#   5. environment_setup only: pipe each module's OpenBao secret to
#      test/build_stream/setup_env.sh --domain-creds-stdin over SSH stdin
#   6. copy the run reports into svt-reports/<cluster>/ (job artifacts)
# --stop (after_script): stop the unit when the job did not succeed; a cancelled
# job also releases the cluster lock.
# Cluster lock: /run/lock/svt-<cluster> on the OIM holds the run id from
# initialization (or the first stage of a resumed run) until summary, so two
# pipelines never interleave stages on one OIM.
# Secrets never reach arguments, environment values, logs or artifacts.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
: "${SVT_CLUSTER:?}" "${SVT_STAGE:?}" "${SVT_THEME:?}" "${SVT_RUN_ID:?}"
CASE="${SVT_CASE:-}"
FULL_LOG="${SVT_FULL_LOG:-false}"
POLL_SECONDS=60
TAIL_LINES=150
CHUNK_BYTES=5242880
MAX_REPORT_BYTES=524288000
MAX_SSH_FAILURES=10

note() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
die() { note "ERROR: $*" >&2; exit 1; }
q() { printf '%q' "$1"; }
cfg() { python3 "${SCRIPT_DIR}/cluster_config.py" "$SVT_CLUSTER" "$1"; }

STOP_ONLY=false
[ "${1:-}" = "--stop" ] && STOP_ONLY=true
if [ "$STOP_ONLY" = true ] && [ "${CI_JOB_STATUS:-}" = "success" ]; then
    exit 0
fi

HOST="$(cfg oim_host)"
LOGIN="$(cfg oim_user)"
PORT="$(cfg oim_port)"
HOST_KEY="$(cfg oim_host_key)"
CLONE_PATH="$(cfg clone_path)"
SVT_DIR="${CLONE_PATH}/test/system_test"
RUN_DIR="${SVT_DIR}/reports/${SVT_RUN_ID}"
LABEL="$SVT_STAGE"
[ "$SVT_STAGE" = "system_verification" ] && [ -n "$CASE" ] && LABEL="system_verification-${CASE}"
UNIT="svt-${SVT_RUN_ID}-${LABEL}"
LOCK="/run/lock/svt-${SVT_CLUSTER}"
REPORT_DIR="${ROOT}/svt-reports/${SVT_CLUSTER}"

WORK="$(mktemp -d)"
chmod 700 "$WORK"
# shellcheck disable=SC2317  # called through the EXIT trap
cleanup_work() { rm -rf -- "$WORK"; }
trap cleanup_work EXIT

# ----------------------------------------------------------------- SSH access
KNOWN_HOSTS="${WORK}/known_hosts"
STRICT="yes"
if [ -n "$HOST_KEY" ]; then
    printf '%s\n' "$HOST_KEY" > "$KNOWN_HOSTS"
else
    : > "$KNOWN_HOSTS"
    STRICT="accept-new"
    note "WARNING: oim_host_key is empty; the OIM host key is trusted on first use"
fi
SSH_OPTS=(-p "$PORT" -o "StrictHostKeyChecking=${STRICT}" -o "UserKnownHostsFile=${KNOWN_HOSTS}"
          -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=4)
PASS_FILE=""
set +e
python3 "${SCRIPT_DIR}/bao_fetch.py" --cluster "$SVT_CLUSTER" --secret oim \
    --field ssh_private_key --out "${WORK}/oim_key"
key_rc=$?
set -e
if [ "$key_rc" -eq 0 ]; then
    SSH_OPTS+=(-i "${WORK}/oim_key" -o BatchMode=yes -o IdentitiesOnly=yes)
elif [ "$key_rc" -eq 3 ]; then
    python3 "${SCRIPT_DIR}/bao_fetch.py" --cluster "$SVT_CLUSTER" --secret oim \
        --field password --out "${WORK}/oim_pass" \
        || die "OpenBao <openbao_path>/oim has neither ssh_private_key nor password"
    command -v sshpass >/dev/null 2>&1 || die "password login needs sshpass on the runner"
    PASS_FILE="${WORK}/oim_pass"
    SSH_OPTS+=(-o PubkeyAuthentication=no -o PreferredAuthentications=password)
else
    die "cannot read the OIM access secret from OpenBao (bao_fetch rc=${key_rc})"
fi

# Remote command strings are built with q() (printf %q); client-side expansion is intended.
# shellcheck disable=SC2029
remote() {
    if [ -n "$PASS_FILE" ]; then
        sshpass -f "$PASS_FILE" ssh "${SSH_OPTS[@]}" "${LOGIN}@${HOST}" "$1"
    else
        ssh "${SSH_OPTS[@]}" "${LOGIN}@${HOST}" "$1"
    fi
}

stop_unit() {
    remote "systemctl stop $(q "$UNIT") 2>/dev/null; systemctl reset-failed $(q "$UNIT") 2>/dev/null; true" || true
}

release_lock() {
    remote "[ \"\$(cat $(q "${LOCK}/owner") 2>/dev/null)\" = $(q "$SVT_RUN_ID") ] && rm -rf -- $(q "$LOCK"); true" || true
}

if [ "$STOP_ONLY" = true ]; then
    note "job ${CI_JOB_STATUS:-unknown}: stopping ${UNIT} on ${HOST}"
    stop_unit
    [ "${CI_JOB_STATUS:-}" = "canceled" ] && release_lock
    exit 0
fi

# -------------------------------------------------------------- cluster lock
if [ "$SVT_STAGE" != "summary" ]; then
    owner="$(remote "mkdir -p /run/lock && if mkdir $(q "$LOCK") 2>/dev/null; then
        echo $(q "$SVT_RUN_ID") > $(q "${LOCK}/owner"); fi; cat $(q "${LOCK}/owner") 2>/dev/null; true")"
    [ "$owner" = "$SVT_RUN_ID" ] || die "cluster ${SVT_CLUSTER} is busy with run '${owner:-unknown}' on ${HOST}. HOW TO FIX: wait for it, or remove the stale lock on the OIM: rm -rf ${LOCK}"
fi

# ------------------------------------------------------------ initialization
STAGE_ARGS=()
if [ "$SVT_STAGE" = "initialization" ]; then
    CLONE_URL="$(cfg clone_url)"
    CLONE_REF="$(cfg clone_ref)"
    note "checkout ${CLONE_URL} ${CLONE_REF} -> ${HOST}:${CLONE_PATH}"
    commit="$(remote "set -e
        if [ ! -d $(q "$CLONE_PATH")/.git ]; then
            mkdir -p \"\$(dirname $(q "$CLONE_PATH"))\"
            git clone --quiet $(q "$CLONE_URL") $(q "$CLONE_PATH")
        fi
        cd $(q "$CLONE_PATH")
        git remote set-url origin $(q "$CLONE_URL")
        git fetch --quiet --tags --force origin
        sha=\$(git rev-parse --verify --quiet $(q "origin/${CLONE_REF}^{commit}") \
              || git rev-parse --verify $(q "${CLONE_REF}^{commit}"))
        git checkout --quiet --force \"\$sha\"
        echo \"\$sha\"")" || die "checkout of ${CLONE_REF} failed on ${HOST}"
    note "commit ${commit}"
    remote "mkdir -p $(q "${RUN_DIR}/inputs") && chmod 750 $(q "$RUN_DIR")"
    for name in user_inputs.yml test_config.yml; do
        remote "cat > $(q "${RUN_DIR}/inputs/${name}")" < "${ROOT}/clusters/${SVT_CLUSTER}/${name}"
    done
    STAGE_ARGS=(--inputs "${RUN_DIR}/inputs/user_inputs.yml"
                --test-config "${RUN_DIR}/inputs/test_config.yml")
fi
[ -n "$CASE" ] && STAGE_ARGS+=(--case "$CASE")
[ "${SVT_RESUME:-false}" = true ] && STAGE_ARGS+=(--resume)

# ---------------------------------------------------------------- start stage
seconds="${CI_JOB_TIMEOUT:-14400}"
[[ "$seconds" =~ ^[0-9]+$ ]] || seconds=14400
command_line="/usr/bin/bash $(q "${SVT_DIR}/run_svt.sh") $(q "$SVT_STAGE") --run-id $(q "$SVT_RUN_ID") --theme $(q "$SVT_THEME") --quiet"
for arg in "${STAGE_ARGS[@]}"; do
    command_line+=" $(q "$arg")"
done
remote "mkdir -p $(q "$RUN_DIR") && rm -f $(q "${RUN_DIR}/${LABEL}.status")
    systemctl reset-failed $(q "$UNIT") 2>/dev/null || true
    systemd-run --unit=$(q "$UNIT") --collect --quiet --property=RuntimeMaxSec=$(q "$seconds") \
        --setenv=HOME=\"\$HOME\" --working-directory=$(q "$SVT_DIR") ${command_line}" \
    || die "cannot start ${UNIT} on ${HOST}"
trap 'note "cancelled: stopping ${UNIT}"; stop_unit; exit 1' TERM INT
note "started ${UNIT} on ${HOST} (log ${RUN_DIR}/${LABEL}.log)"

# ----------------------------------------------------------------- follow it
LOG="${RUN_DIR}/${LABEL}.log"
started=$(date +%s)
offset=0
failures=0
last_progress=""
status=""
[ "$FULL_LOG" = true ] && printf '\e[0Ksection_start:%s:svt_output\r\e[0K%s\n' "$(date +%s)" "SVT output (${LABEL})"
flush_log() {
    if remote "tail -c +$((offset + 1)) $(q "$LOG") 2>/dev/null | head -c ${CHUNK_BYTES}" > "${WORK}/chunk"; then
        cat "${WORK}/chunk"
        offset=$((offset + $(wc -c < "${WORK}/chunk")))
        failures=0
        return 0
    fi
    return 1
}
while true; do
    sleep "$POLL_SECONDS"
    if [ "$FULL_LOG" = true ]; then
        while flush_log && [ "$(wc -c < "${WORK}/chunk")" -ge "$CHUNK_BYTES" ]; do :; done
    else
        progress="$(remote "cat $(q "${RUN_DIR}/${LABEL}.progress") 2>/dev/null" || true)"
        elapsed=$(( ($(date +%s) - started) / 60 ))
        if [ -n "$progress" ] && [ "$progress" != "$last_progress" ]; then
            note "[in progress ${elapsed}m] ${progress}"
            last_progress="$progress"
        elif (( elapsed % 10 == 0 )); then
            note "[in progress ${elapsed}m]"
        fi
    fi
    if ! status="$(remote "cat $(q "${RUN_DIR}/${LABEL}.status") 2>/dev/null; true")"; then
        failures=$((failures + 1))
        [ "$failures" -ge "$MAX_SSH_FAILURES" ] && die "lost SSH access to ${HOST} (${failures} attempts)"
        continue
    fi
    failures=0
    [ -n "$status" ] && break
    state="$(remote "systemctl is-active $(q "$UNIT") 2>/dev/null; true" || echo unknown)"
    case "$state" in
        active|activating|unknown) ;;
        *)
            # The unit may have written its status file just after the first read.
            status="$(remote "cat $(q "${RUN_DIR}/${LABEL}.status") 2>/dev/null; true" || true)"
            [ -n "$status" ] || status="failed (unit ${state} without a status file)"
            break ;;
    esac
done
if [ "$FULL_LOG" = true ]; then
    while flush_log && [ "$(wc -c < "${WORK}/chunk")" -ge "$CHUNK_BYTES" ]; do :; done
    printf '\e[0Ksection_end:%s:svt_output\r\e[0K\n' "$(date +%s)"
fi
note "${LABEL}: ${status} after $(( ($(date +%s) - started) / 60 ))m"

# ------------------------------------------------------- domain credentials
if [ "$SVT_STAGE" = "environment_setup" ] && [[ "$status" != failed* ]]; then
    for module in ${SVT_CREDENTIAL_MODULES:-}; do
        python3 "${SCRIPT_DIR}/bao_fetch.py" --cluster "$SVT_CLUSTER" --secret "$module" \
            --json --out "${WORK}/creds.json" || die "OpenBao secret ${module} is missing"
        remote "cd $(q "${CLONE_PATH}/test/build_stream") &&
            venv=\$(sed -n 's/^OMNIA_VENV_PATH=//p' /etc/omnia/omnia.env | tr -d '\"') &&
            VIRTUAL_ENV=\"\$venv\" PATH=\"\$venv/bin:\$PATH\" ./setup_env.sh --domain-creds-stdin --domain $(q "$module") >/dev/null" \
            < "${WORK}/creds.json" || die "storing the ${module} credentials failed"
        rm -f -- "${WORK}/creds.json"
        note "credentials stored for ${module}"
    done
fi

# ------------------------------------------------------------------- reports
mkdir -p "$REPORT_DIR"
if remote "tar -C $(q "$RUN_DIR") -czf - --exclude=inputs . 2>/dev/null" \
        | head -c "$MAX_REPORT_BYTES" > "${REPORT_DIR}/reports.tgz"; then
    tar -xzf "${REPORT_DIR}/reports.tgz" -C "$REPORT_DIR" --wildcards '*.xml' '*.json' 2>/dev/null || true
    note "reports: ${REPORT_DIR}/reports.tgz (job artifacts); on the OIM: ${RUN_DIR}"
fi

[ "$SVT_STAGE" = "summary" ] && release_lock

if [[ "$status" == failed* ]]; then
    if [ "$FULL_LOG" != true ]; then
        note "last ${TAIL_LINES} lines of ${LOG}:"
        remote "tail -n ${TAIL_LINES} $(q "$LOG")" || true
    fi
    note "FAILED: full log on ${HOST}: ${LOG}"
    exit 1
fi
exit 0
