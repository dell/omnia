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

"""Build Stream FVT — execute pipeline constants and command templates."""

import os
import re
import threading

from .common_vars import MODULE_ROOT


# =============================================================================
# SUITE IDENTITY AND LAYOUT
# =============================================================================


REPO_ROOT = os.path.dirname(os.path.dirname(MODULE_ROOT))


# =============================================================================
# OMNIA ENVIRONMENT (/etc/omnia/omnia.env)
# =============================================================================
OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
ENV_CATALOG_FILE_PATH = "CATALOG_FILE_PATH"


# =============================================================================
# PREPARE BASE
# =============================================================================

# =============================================================================
# INSTALLATION — CATALOG PLACEMENT AND build_stream.yml
# =============================================================================
CATALOG_SAMPLES_DIR = "src/main/samples"
CATALOG_VARIANTS_DIR = "src/main/samples/catalogs"
CATALOG_DEFAULT_FILE = "catalog_rhel.json"
CATALOG_SECTION = "catalog"
CATALOG_VERSION_KEY = "version"
CATALOG_IDENTIFIER_KEY = "identifier"
CATALOG_VERSION_RE = re.compile(r"(\d+)\.(\d+)")
CATALOG_MAX_VERSION_ATTEMPTS = 100

BSM_DOMAIN = "build_stream"
DEFAULT_POLL_INTERVAL = 30

# omnia.sh and playbooks run until they finish: the omnia_auto streaming
# watchdog requires a value, so the largest timer the platform supports is used.
NO_TIMEOUT = threading.TIMEOUT_MAX

# =============================================================================
# BUILDSTREAM RUNTIME (read from build_stream_config.yml / credentials)
# =============================================================================
BSM_CONFIG_FILE = "build_stream_config.yml"
BSM_CREDENTIALS_FILE = "build_stream_credentials.yml"
BSM_CREDENTIALS_KEY = ".build_stream_credentials_key"
# Self-signed API certificate build_stream.yml generates under OMNIA_DATA_PATH
# (deploy_bsm build_stream_ssl_cert; pipelines use it as BSM_API_CERT).
BSM_TLS_CERT = "build_stream/ssl/bs_cert.pem"
BSM_CONFIG_KEYS = {
    "enabled": "enable_build_stream",
    "api_host": "build_stream_host_ip",
    "api_port": "build_stream_port",
    "gitlab_host": "gitlab_host",
    "gitlab_port": "gitlab_https_port",
    "gitlab_branch": "gitlab_default_branch",
    "cadence": "cadence",
}
BSM_CREDENTIAL_KEYS = {
    "gitlab_token": "gitlab_root_token",
    "gitlab_project_id": "gitlab_project_id",
}
BSM_CI_CLIENT_ID_VAR = "BSM_CLIENT_ID"
BSM_CI_CLIENT_SECRET_VAR = "BSM_CLIENT_SECRET"

BSM_CONTAINER = "omnia_build_stream"
BSM_POSTGRES_CONTAINER = "omnia_postgres"
BSM_POSTGRES_DB = "build_stream_db"
BSM_PLAYBOOK_WATCHER_SERVICE = "playbook-watcher.service"

BSM_API_PREFIX = "/api/v1"
BSM_API_TOKEN_PATH = "/api/v1/auth/token"
BSM_API_JOB_PATH = "/api/v1/jobs/{job_id}"
BSM_API_ARTIFACT_PATH = "/api/v1/jobs/{job_id}/artifacts/{label}"
BSM_API_GRANT_TYPE = "client_credentials"

HTTP_TIMEOUT = 30
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
IMAGE_GROUP_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
# GitLab CI/CD variable keys: letters, digits and underscores, up to 255 chars.
CI_VARIABLE_KEY_RE = re.compile(r"[A-Za-z0-9_]{1,255}")

# =============================================================================
# GITLAB REPOSITORY CONTRACT (.gitlab-ci.yml)
# =============================================================================
GITLAB_API = "/api/v4"
GITLAB_CATALOG_FILE = "catalog_rhel.json"
GITLAB_CADENCE_CATALOG_FILE = "cadence_catalog_rhel.json"
PXE_MAPPING_FILE = "pxe_mapping_file.csv"
GITLAB_PXE_MAPPING_FILE = f"input/orchestrator/{PXE_MAPPING_FILE}"
GITLAB_BRIDGE_BUILD = "build_pipeline"
GITLAB_BRIDGE_DEPLOY = "deploy_pipeline"
GITLAB_BRIDGE_CADENCE = "cadence_pipeline"
GITLAB_BRIDGE_DEPLOY_CHILD = "trigger_deploy"
# Cleanup pipeline (.gitlab-ci.yml cleanup_pipeline -> .gitlab-ci-cleanup.yml
# list_images + trigger_cleanup -> generated child: select_image (one manual
# job per image group), cleanup (manual), summary).
GITLAB_BRIDGE_CLEANUP = "cleanup_pipeline"
GITLAB_BRIDGE_CLEANUP_CHILD = "trigger_cleanup"
GITLAB_CLEANUP_JOB = "cleanup"
GITLAB_CLEANUP_SUMMARY_SUCCESS = re.compile(r"Status:\s+SUCCESS")
# The cleanup job polls the API up to MAX_POLL_ATTEMPTS x POLL_INTERVAL (10 min).
CLEANUP_JOB_TIMEOUT = 1800
# cleanup_job.py / state_machine.py: DELETE /api/v1/jobs accepts these statuses.
IMAGE_GROUP_CLEANABLE = ("BUILT", "PASSED", "FAILED")
# Build outputs (build_artifacts_func): Repo Manager repo_status.yml and Image
# Build Manager build_status.yml under <domain data>/output/<project>/.
REPO_MANAGER_DOMAIN = "repo_manager"
IMAGE_BUILD_MANAGER_DOMAIN = "image_build_manager"
REPO_STATUS_FILE = "repo_status.yml"
BUILD_STATUS_FILE = "build_status.yml"
# build_status.yml keys of the three boot files each functional group needs.
BOOT_ARTIFACT_KEYS = ("image", "kernel", "initrd")
GITLAB_SELECT_IMAGE_STAGE = "select_image"
GITLAB_DEPLOY_JOB = "deploy"
# Deploy child pipeline summary job and its success line
# (.gitlab-ci-deploy-child-template.yml).
GITLAB_SUMMARY_JOB = "summary"
GITLAB_SUMMARY_PASSED = "RESULT:  PASSED"
GITLAB_BUSY_STATUSES = ("created", "waiting_for_resource", "preparing",
                        "pending", "running")
GITLAB_FAILED_STATUSES = ("failed", "canceled", "skipped")
GITLAB_SUCCESS = "success"
GITLAB_MANUAL = "manual"
PIPELINE_DETECT_TIMEOUT = 300
PIPELINE_DETECT_INTERVAL = 10
SELECT_JOBS_TIMEOUT = 600
JOB_DB_TIMEOUT = 600
COMMIT_MESSAGE_BUILD = "system: bump {file} to v{version}"
COMMIT_MESSAGE_DEPLOY = "system: swap pxe mapping rows {first} and {second}"
# [skip ci] stops GitLab from creating a pipeline for the upload commit; the
# cadence cycle's own bump commit is what triggers the cadence pipeline.
COMMIT_MESSAGE_CADENCE_UPLOAD = "system: upload {file} v{version} for cadence [skip ci]"
# Seconds to wait after the [skip ci] upload before checking no pipeline exists.
CADENCE_UPLOAD_PIPELINE_CHECK = 15
# Manual mode commits with this marker (no auto-trigger), then triggers the
# pipeline through the API with PIPELINE_TYPE.
SKIP_CI = "[skip ci]"
# The first build pipeline registers an OAuth client and stores it as these
# CI/CD variables; the deploy, cadence and cleanup pipelines authenticate
# with them (.gitlab-ci-*.yml: "The Build Pipeline must have run at least once").
BSM_CI_CLIENT_VARIABLES = ("BSM_CLIENT_ID", "BSM_CLIENT_SECRET")
# auth/service.py: registered OAuth client IDs start with this prefix.
BSM_CLIENT_ID_PREFIX = "bld_"

# =============================================================================
# PIPELINE STAGES (BuildStream job_stages.stage_name)
# =============================================================================
# The upload stage writes the committed catalog to CATALOG_FILE_PATH on the host.
BUILD_UPLOAD_STAGE = "upload"
# The validate stage stores the run_validation counts in
# job_stages.result_detail.test_summary (result_poller.py).
VALIDATE_STAGE = "validate"
TEST_SUMMARY_KEYS = ("total", "passed", "failed", "skipped", "errors")

STAGE_COMPLETED = "COMPLETED"
STAGE_FAILED = "FAILED"
STAGE_SKIPPED = "SKIPPED"
STAGE_TERMINAL = (STAGE_COMPLETED, STAGE_FAILED, STAGE_SKIPPED)
JOB_TERMINAL_FAILED = ("FAILED", "CANCELLED")
# GET /api/v1/jobs/{id} reports job_state under display names, not the jobs.job_state
# value in the database (api/jobs/routes.py: _map_job_state_to_api_state).
API_JOB_STATE = {
    "CREATED": "PENDING",
    "IN_PROGRESS": "RUNNING",
    "COMPLETED": "SUCCEEDED",
    "FAILED": "FAILED",
    "CANCELLED": "CLEANED",
}

IMAGE_GROUP_BUILT = "BUILT"
IMAGE_GROUP_PASSED = "PASSED"
IMAGE_GROUP_AFTER_BUILD = ("BUILT", "DEPLOYING", "DEPLOYED", "RESTARTING",
                           "RESTARTED", "VALIDATING", "PASSED")

# =============================================================================
# CADENCE (playbook-watcher journal contract, cadence_manager.py)
# =============================================================================
CADENCE_TRIGGER_SCRIPT = "build_stream/playbook-watcher/trigger_cadence.sh"
CADENCE_LOG_ROOT = "build_stream/log"
CADENCE_SYNC_STAGE = "cadence-repo-sync"
# A disabled cycle is skipped right after the config reload; wait this long
# for "Cadence polling is disabled" before reporting the toggle as not live.
CADENCE_DISABLED_TIMEOUT = 300
CADENCE_JOURNAL_EVENTS = (
    # (event key, journal substring, terminal outcome or None)
    ("triggered", "Cadence manual trigger requested via SIGUSR1", None),
    ("cycle_started", "Cadence polling cycle started", None),
    ("config_reloaded", "Cadence config reloaded: enabled", None),
    ("disabled", "Cadence polling is disabled", "failed"),
    ("suppressed", "Cadence sync suppressed", "failed"),
    ("catalog_fetched", "Cadence catalog fetched from GitLab", None),
    ("sync_submitted", "Submitted cadence repo sync request", None),
    ("sync_playbook_done", "stage=cadence-repo-sync", None),
    ("sync_result", "Cadence sync result received", None),
    ("sync_succeeded", "Repo sync succeeded", None),
    ("sync_failed", "Repo sync failed", "failed"),
    ("sync_timeout", "Repo sync did not complete in time", "failed"),
    ("no_change", "No package count change detected", None),
    ("changes", "Package count changes detected", None),
    ("committed", "Cadence catalog updated via GitLab API", None),
    ("completed", "Cadence cycle completed", "success"),
)
CADENCE_ERROR_MARKERS = (" - ERROR - ", " - CRITICAL - ")
CADENCE_LOGGER_NAME = "cadence_manager"
# journalctl -o short-iso prefix ("<iso time> <host> <ident>[<pid>]: ").
JOURNAL_PREFIX_RE = re.compile(r"^\S+ \S+ [^\s:]+\[\d+\]: ")
# playbook-watcher application record ("<time> - <logger> - <LEVEL> - <msg>").
JOURNAL_RECORD_RE = re.compile(r" - [\w.]+ - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - ")
CADENCE_VERSION_RE = re.compile(r"bumped to v(\S+)")
CADENCE_HEARTBEAT_POLLS = 4

# =============================================================================
# STAGE PLAYBOOK LOGS (playbook_watcher_service.build_stage_log_path)
# =============================================================================
# Ansible writes each stage attempt live to
#   /var/log/omnia/<domain>/<stage>_<playbook>_<YYYYmmdd_HHMMSS UTC>_attempt<N>.log
# and the watcher copies it to <OMNIA_DATA_PATH>/build_stream/log/<job_id>/
# only when the attempt finishes.
PLAYBOOK_LOG_BASE_DIR = "/var/log/omnia"
BSM_JOB_LOG_ROOT = "build_stream/log"
STAGE_LOG_RE = re.compile(r"_(?P<ts>\d{8}_\d{6})_attempt(?P<attempt>\d+)\.log$")
# Logs older than (stage monitoring start - slack) belong to earlier jobs.
STAGE_LOG_WINDOW_SLACK = 900
# debug_mode streams logs live with a background tail -F (no read interval).
# On stage end the stream stops once the log is quiet for LOG_FOLLOW_SETTLE
# seconds (at most LOG_FOLLOW_SETTLE_MAX).
LOG_FOLLOW_SETTLE = 2
LOG_FOLLOW_SETTLE_MAX = 15
LOG_FOLLOW_STOP_TIMEOUT = 10

# =============================================================================
# AUTOMATED CLEANUP (cleanup_cron.py, run by AutoCleanupScheduler in the
# omnia_build_stream container; ER-BSM-002 Story 4)
# =============================================================================
# One pass = the same entry point the scheduler calls, with a stdout log
# handler so every INFO line can be monitored (a bare run logs nothing).
# podman exec starts in the image WORKDIR (APP_DIR), where cleanup_cron.py
# lives, so no application path is hardcoded here.
AUTO_CLEANUP_TRIGGER_CODE = (
    "import logging, os, sys; "
    "logging.basicConfig(level=logging.INFO, stream=sys.stdout, "
    "format='%(asctime)s - %(levelname)s - %(message)s'); "
    "sys.path.insert(0, os.getcwd()); "
    "import cleanup_cron; sys.exit(cleanup_cron.main())"
)
# cleanup_cron.main() exit codes: 0 clean, 1 some groups failed, 2 fatal.
AUTO_CLEANUP_FATAL_RC = 2
RETENTION_SECTION = "retention"
# Built-in defaults and minimums of orchestrator/cleanup/retention_config.py.
RETENTION_DEFAULTS = {
    "auto_cleanup_enabled": True,
    "retention_age_days": 90,
    "min_keep_count": 5,
    "evaluation_interval_hours": 24,
}
RETENTION_MINIMUMS = {
    "retention_age_days": 1,
    "min_keep_count": 0,
    "evaluation_interval_hours": 1,
}
SECONDS_PER_DAY = 86400
# Groups this close to the age cutoff may flip between snapshot and pass.
AUTO_CLEANUP_BORDERLINE_SECONDS = 300
IMAGE_GROUP_FAILED = "FAILED"
IMAGE_GROUP_CLEANING = "CLEANING"
IMAGE_GROUP_CLEANED = "CLEANED"
IMAGE_GROUP_CLEANUP_FAILED = "CLEANUP_FAILED"
IMAGE_GROUP_NOT_COUNTED = (IMAGE_GROUP_CLEANED, IMAGE_GROUP_CLEANING)
# cleanup_job.py ACTIVE_STATUSES: cleanup is refused while a stage runs.
IMAGE_GROUP_ACTIVE = ("DEPLOYING", "RESTARTING", "VALIDATING")
UNKNOWN_CATALOG_IDENTIFIER = "__unknown__"
AUDIT_CLEANUP_SUBMITTED = "JOB_CLEANUP_SUBMITTED"
AUDIT_CLEANED = "JOB_CLEANED"
AUDIT_CLEANUP_FAILED = "JOB_CLEANUP_FAILED"
AUDIT_RETENTION_DELETED = "RETENTION_DELETED"
# cleanup_job.py submits image_build_manager.yml --tags cleanup_images with
# stage_name "cleanup"; the watcher logs it as cleanup_<playbook>_<ts>_attempt<N>.log.
CLEANUP_LOG_STAGE = "cleanup"
S3CMD_CONFIG = "/root/.s3cfg"
NFS_ARTIFACTS_DIR = "build_stream/build_stream_root/artifacts"
# pxe_buildstream_manager: per-job restart_state.json lists the nodes booted by
# earlier restart attempts; a retry PXE-boots only the remaining nodes.
RESTART_STATE_DIR = "build_stream/build_stream_root/restart_state"
RESTART_STATE_FILE = "restart_state.json"
# pxe_mapping_file.csv column that keys node_results.json (bmc_ip).
PXE_BMC_IP_COLUMN = "BMC_IP"
# cleanup_cron.py / cleanup_job.py log lines (emitted through log_secure_info).
AUTO_CLEANUP_LOG_RE = {
    "failed_phase": re.compile(
        r"FAILED phase\) complete: total=(\d+), cleaned=(\d+), errors=(\d+)"),
    "retention_started": re.compile(
        r"Retention evaluation started: retention_age_days=(\d+), min_keep_count=(\d+)"),
    "retention_eligible": re.compile(r"Retention evaluation: (\d+) ImageGroups eligible"),
    "submitted": re.compile(r"Cleanup playbook submitted: image_group=([^,\s]+)"),
    "retention_deleted": re.compile(r"RETENTION_DELETED: image_group_id=([^,\s]+)"),
    "error": re.compile(r" - (?:ERROR|CRITICAL) - (.*)"),
}

# =============================================================================
# CLEANUP
# =============================================================================


# =============================================================================
# PREPARE BASE READINESS (what each domain's prepare phase leaves running)
# =============================================================================
# repo_manager prepare: Pulp container from its quadlet.
# image_build_manager prepare: MinIO + registry (deploy_minio, deploy_registry).
# orchestrator prepare: every OpenCHAMI unit, container and volume
# (ORCH_OPENCHAMI_*), plus OpenLDAP when openldap_support is true.

# =============================================================================
# CLEANUP OUTCOMES (per domain, recorded by the cleanup exec test)
# =============================================================================

# =============================================================================
# SHELL COMMANDS — named placeholders; run_cmd() shell-quotes every value.
# =============================================================================
CMDS = {
    # --- Podman ---
    # Prints "<running> <health>"; health is empty without a healthcheck.
    "podman_volume_exists": "podman volume exists {name}",
    "podman_psql": (
        "podman exec {container} sh -c "
        "'psql -U \"$POSTGRES_USER\" -d \"$1\" -v ON_ERROR_STOP=1 -At -F \"|\" -c \"$2\"'"
        " psql {database} {sql}"
    ),
    # --- Systemd / journal ---
    "systemctl_is_active": "systemctl is-active {unit}",
    "journal_since": (
        "journalctl -u {unit} --since @{epoch} --no-pager -o short-iso"
    ),
    # --- Network ---
    "port_listening": "ss -Htln 'sport = :'{port}",
    # --- Files ---
    "path_exists": "test -e {path}",
    "file_exists": "test -f {path}",
    "cat_file": "cat {path}",
    # Same listing and order as omnia.sh _catalog_sources (variants only).
    "list_catalog_variants": (
        "find {directory} -type f -name '*.json' -print 2>/dev/null | sort"
    ),
    "s3_list_recursive": "s3cmd -c {config} ls -r {bucket}",
    "hostname": "hostname",
    "regctl_repo_ls": "regctl repo ls {registry}",
    "regctl_tag_ls": "regctl tag ls {registry}/{repo}",
    "container_python": "podman exec {container} python3 -c {code}",
    # Requests playbook-watcher is running now (cadence_manager.is_pipeline_busy).
    "newest_cadence_log_dir": "ls -1td {root}/cadence-* 2>/dev/null | head -n 1",
    "last_ansible_task": "grep -h 'TASK \\[' {directory}/*.log 2>/dev/null | tail -n 1",
    # Placeholders are quoted; the glob suffix stays outside the quotes.
    "stage_log_candidates": (
        "ls -1 {base}/*/{stage}_*_attempt*.log {job_dir}/{stage}_*_attempt*.log 2>/dev/null"
    ),
    # Live stream; the tail is killed when the caller closes stdin (EOF).
    "follow_file": (
        "tail -n +1 -F {path} 2>/dev/null & pid=$!; cat >/dev/null; "
        "kill $pid 2>/dev/null; wait $pid 2>/dev/null; exit 0"
    ),
    # Flip enabled: inside the top-level cadence: block (comments preserved).
    "cadence_enable": (
        "sed -i '/^cadence:/,/^[^[:space:]#]/ "
        "s/^\\([[:space:]]*enabled:[[:space:]]*\\).*/\\1true/' {path}"
    ),
    "cadence_disable": (
        "sed -i '/^cadence:/,/^[^[:space:]#]/ "
        "s/^\\([[:space:]]*enabled:[[:space:]]*\\).*/\\1false/' {path}"
    ),
    # --- System ---
    "epoch_now": "date +%s",
    "run_script": "bash {path}",
    "vault_view": (
        "set -a && . {env_file} && set +a && "
        "\"${{OMNIA_VENV_PATH:+$OMNIA_VENV_PATH/bin/}}ansible-vault\" view {path}"
        " --vault-password-file {key}"
    ),
    "omnia_sh": "cd {workdir} && ./omnia.sh {arguments}",
    "ansible_playbook": (
        "set -a && . {env_file} && set +a && "
        "if [ -n \"$OMNIA_VENV_PATH\" ]; then . \"$OMNIA_VENV_PATH/bin/activate\"; fi && "
        "cd {workdir} && ansible-playbook {playbook} {arguments}"
    ),
}

# Templates whose {arguments} value is a pre-quoted argument string.
RAW_ARGUMENT_CMDS = ("omnia_sh", "ansible_playbook")

# =============================================================================
# SQL — values are validated before formatting (UUIDs, image group IDs).
# =============================================================================
SQL = {
    "now_epoch": "SELECT floor(extract(epoch FROM now()))::bigint;",
    "newest_job_since": (
        "SELECT job_id, job_state, created_at FROM jobs "
        "WHERE created_at >= to_timestamp({epoch}) "
        "ORDER BY created_at DESC LIMIT 1;"
    ),
    "job": "SELECT job_id, job_state, created_at, updated_at FROM jobs WHERE job_id='{job_id}';",
    "first_job_since": (
        "SELECT job_id, job_state, created_at FROM jobs "
        "WHERE created_at >= to_timestamp({epoch}) "
        "ORDER BY created_at ASC LIMIT 1;"
    ),
    "job_stages": (
        "SELECT stage_name, stage_state, attempt, coalesce(error_code,''), "
        "coalesce(replace(replace(error_summary, E'\\n', ' '), '|', '/'),''), "
        "coalesce(log_file_path,''), coalesce(started_at::text,'') "
        "FROM job_stages WHERE job_id='{job_id}';"
    ),
    "stage_test_summary": (
        "SELECT coalesce(result_detail->'test_summary'->>'total',''), "
        "coalesce(result_detail->'test_summary'->>'passed',''), "
        "coalesce(result_detail->'test_summary'->>'failed',''), "
        "coalesce(result_detail->'test_summary'->>'skipped',''), "
        "coalesce(result_detail->'test_summary'->>'errors','') "
        "FROM job_stages WHERE job_id='{job_id}' AND stage_name='{stage}';"
    ),
    "image_group_by_job": (
        "SELECT id, job_id, status, deploy_count, coalesce(last_deployed_at::text,''), "
        "coalesce(catalog_version,'') FROM image_groups WHERE job_id='{job_id}';"
    ),
    "catalog_versions": (
        "SELECT DISTINCT catalog_version FROM image_groups "
        "WHERE catalog_identifier='{identifier}' AND catalog_version IS NOT NULL;"
    ),
    "image_group_by_id": (
        "SELECT id, job_id, status, deploy_count, coalesce(last_deployed_at::text,''), "
        "coalesce(catalog_version,'') FROM image_groups WHERE id='{image_group_id}';"
    ),
    "image_count": "SELECT count(*) FROM images WHERE image_group_id='{image_group_id}';",
    "job_client_id": "SELECT coalesce(client_id,'') FROM jobs WHERE job_id='{job_id}';",
    # models.py: image_groups.job_id is UNIQUE, so a job owns at most one image group.
    "image_groups_for_job": (
        "SELECT id, job_id, status, deploy_count, coalesce(last_deployed_at::text,''), "
        "coalesce(catalog_version,'') FROM image_groups WHERE job_id='{job_id}' "
        "ORDER BY created_at;"
    ),
    "image_group_count": "SELECT count(*) FROM image_groups;",
    # cleanup_job.py / state_machine.py: cleanup accepts BUILT, PASSED, FAILED.
    "newest_cleanable_image_group": (
        "SELECT id, job_id, status, deploy_count, coalesce(last_deployed_at::text,''), "
        "coalesce(catalog_version,'') FROM image_groups "
        "WHERE status IN ('BUILT','PASSED','FAILED') ORDER BY created_at DESC LIMIT 1;"
    ),
    # The automated cleanup deletes FAILED groups only; the test marks its target FAILED.
    "mark_image_group_failed": (
        "UPDATE image_groups SET status='FAILED', updated_at=now() "
        "WHERE id='{image_group_id}' AND status IN ('BUILT','PASSED','FAILED');"
    ),
    "image_roles": (
        "SELECT DISTINCT role FROM images WHERE image_group_id='{image_group_id}' ORDER BY role;"
    ),
    "cleanup_audit_for_job": (
        "SELECT event_type FROM audit_events WHERE job_id='{job_id}' "
        "AND timestamp >= to_timestamp({epoch}) AND event_type IN "
        "('JOB_CLEANUP_SUBMITTED','JOB_CLEANED','JOB_CLEANUP_FAILED');"
    ),
    # --- automated cleanup (cleanup_cron.py eligibility inputs) ---
    "auto_cleanup_groups": (
        "SELECT id, job_id, status, deploy_count, is_protected, "
        "coalesce(catalog_identifier,''), floor(extract(epoch FROM created_at))::bigint "
        "FROM image_groups ORDER BY created_at;"
    ),
    "auto_cleanup_statuses": "SELECT id, status FROM image_groups;",
    "jobs_tombstoned": "SELECT job_id, tombstoned FROM jobs WHERE job_id IN ({job_ids});",
    "auto_cleanup_audit_since": (
        "SELECT event_type, job_id, coalesce(details->>'image_group_id','') "
        "FROM audit_events WHERE timestamp >= to_timestamp({epoch}) AND event_type IN "
        "('JOB_CLEANUP_SUBMITTED','JOB_CLEANED','JOB_CLEANUP_FAILED','RETENTION_DELETED');"
    ),
}
