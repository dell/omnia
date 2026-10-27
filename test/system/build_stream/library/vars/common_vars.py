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

"""BuildStream system test — suite-wide constants and command templates."""

import os
import re
import threading


# =============================================================================
# SUITE IDENTITY AND LAYOUT
# =============================================================================
DOMAIN_NAME = "system_build_stream"

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(MODULE_ROOT)))

# Global pytest order bands (@pytest.mark.order): one per SVT scenario.
# auto_cleanup needs the installed BuildStream, so it runs before cleanup.
# Inside a band: +1 precheck (exec), +2 entry point (exec), +100 per verify
# suite (verify phase).
ORDER_BANDS = {"prepare_base": 1000, "installation": 2000, "auto_cleanup": 3000,
               "cleanup": 4000}
ORDER_UNSET = 9999

# =============================================================================
# OMNIA ENVIRONMENT (/etc/omnia/omnia.env)
# =============================================================================
OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"
ENV_CATALOG_FILE_PATH = "CATALOG_FILE_PATH"
ENV_OMNIA_VENV_PATH = "OMNIA_VENV_PATH"
# Variables omnia.sh and every domain playbook require (no fallback values).
REQUIRED_ENV_VARS = (ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME, ENV_OMNIA_VENV_PATH)
VENV_ACTIVATE_FILE = "bin/activate"

# Per-scenario exec -> verify hand-off (exec and verify are separate pytest
# processes). Stored on the runner host under reports/ (git-ignored).
RUN_STATE_DIR = os.path.join(MODULE_ROOT, "reports", "state")
RUN_STATE_FILE = "{scenario}.json"
RUN_STATE_MODE = 0o600
# Scenarios whose verify tests read exec facts (state file names).
SCENARIO_AUTO_CLEANUP = "auto_cleanup"
SCENARIO_CLEANUP = "cleanup"

# =============================================================================
# PREPARE BASE
# =============================================================================
OMNIA_SH_WORKDIR = "src/main"
OMNIA_SH_FILE = "omnia.sh"
OMNIA_SH_PREPARE_BASE_ARGS = "--prepare-base"
PREPARE_BASE_DOMAINS = ("repo_manager", "image_build_manager", "orchestrator")

# =============================================================================
# INSTALLATION — CATALOG PLACEMENT AND build_stream.yml
# =============================================================================
CATALOG_SAMPLES_DIR = "src/main/samples"
CATALOG_VARIANTS_DIR = "src/main/samples/catalogs"
CATALOG_DEFAULT_FILE = "catalog_rhel.json"
CATALOG_BACKUP_SUFFIX = ".backup.{timestamp}"
CATALOG_SECTION = "catalog"
CATALOG_VERSION_KEY = "version"
CATALOG_IDENTIFIER_KEY = "identifier"
CATALOG_VERSION_RE = re.compile(r"(\d+)\.(\d+)")
CATALOG_MAX_VERSION_ATTEMPTS = 100

BSM_DOMAIN = "build_stream"
BSM_PLAYBOOK = "build_stream.yml"
BSM_PLAYBOOK_WORKDIR = "src/build_stream/playbooks"
# build_stream.yml --tags precheck: repo_manager and image_build_manager are
# ready for BuildStream (precheck_build_stream role). Never runs by default.
BSM_PRECHECK_TAG = "precheck"
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
BSM_TLS_CERT = "build_stream_ssl/ssl/bs_cert.pem"
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
BSM_PLAYBOOK_WATCHER_UNIT_FILE = "/etc/systemd/system/playbook-watcher.service"
BSM_EXPECTED_TABLES = (
    "alembic_version",
    "artifact_metadata",
    "audit_events",
    "idempotency_keys",
    "image_groups",
    "images",
    "job_stages",
    "jobs",
)

BSM_API_HEALTH_PATH = "/health"
BSM_API_HEALTHY = "healthy"
BSM_API_TOKEN_PATH = "/api/v1/auth/token"
BSM_API_JOB_PATH = "/api/v1/jobs/{job_id}"
BSM_API_GRANT_TYPE = "client_credentials"

HTTP_TIMEOUT = 30
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
IMAGE_GROUP_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

# =============================================================================
# GITLAB REPOSITORY CONTRACT (.gitlab-ci.yml)
# =============================================================================
GITLAB_API = "/api/v4"
GITLAB_CATALOG_FILE = "catalog_rhel.json"
GITLAB_CADENCE_CATALOG_FILE = "cadence_catalog_rhel.json"
PXE_MAPPING_FILE = "pxe_mapping_file.csv"
GITLAB_PXE_MAPPING_FILE = f"input/orchestrator/{PXE_MAPPING_FILE}"
# GitLab CI files pushed by build_stream.yml
# (src/build_stream/roles/hosted_gitlab/files, tasks/push_ci_files.yml).
GITLAB_CI_FILES = (
    ".gitlab-ci.yml",
    ".gitlab-ci-build.yml",
    ".gitlab-ci-deploy.yml",
    ".gitlab-ci-cadence.yml",
    ".gitlab-ci-cleanup.yml",
    ".gitlab-ci-deploy-child-template.yml",
    ".gitlab-ci-cleanup-child-template.yml",
)
# omnia.env placed at repository root by build_stream.yml.
GITLAB_OMNIA_ENV = "omnia.env"
# Domain input files synced to input/<domain>/<file> (hosted_gitlab
# vars gitlab_input_files). A file is pushed only when it exists in the
# domain input directory on the OIM, and then with identical content.
GITLAB_INPUT_DIR = "input"
GITLAB_INPUT_FILES = (
    ("repo_manager", "repo_manager_config.yml"),
    ("repo_manager", "repo_manager_endpoint_config.yml"),
    ("image_build_manager", "image_build_config.yml"),
    ("image_build_manager", "package_groups.yml"),
    ("orchestrator", "omnia_config.yml"),
    ("orchestrator", "orchestrator_config.yml"),
    ("orchestrator", "network_spec.yml"),
    ("orchestrator", "security_config.yml"),
    ("orchestrator", "storage_config.yml"),
    ("orchestrator", "additional_cloud_init.yml"),
    ("orchestrator", "pxe_mapping_file.csv"),
    ("orchestrator", "set_pxe_boot_config.yml"),
)
# The deploy pipeline swaps two node rows of this file, so it needs two.
PXE_MAPPING_MIN_NODES = 2
GITLAB_BRIDGE_BUILD = "build_pipeline"
GITLAB_BRIDGE_DEPLOY = "deploy_pipeline"
GITLAB_BRIDGE_CADENCE = "cadence_pipeline"
GITLAB_BRIDGE_DEPLOY_CHILD = "trigger_deploy"
GITLAB_SELECT_IMAGE_STAGE = "select_image"
GITLAB_DEPLOY_JOB = "deploy"
GITLAB_ACTIVE_STATUSES = ("created", "waiting_for_resource", "preparing",
                          "pending", "running", "manual", "scheduled")
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

# =============================================================================
# PIPELINE STAGES (BuildStream job_stages.stage_name)
# =============================================================================
# The upload stage writes the committed catalog to CATALOG_FILE_PATH on the host.
BUILD_UPLOAD_STAGE = "upload"
BUILD_STAGES = (BUILD_UPLOAD_STAGE, "parse-catalog", "create-local-repository", "build-image")
DEPLOY_STAGES = ("deploy", "restart", "validate")
CADENCE_STAGES = BUILD_STAGES + DEPLOY_STAGES

STAGE_COMPLETED = "COMPLETED"
STAGE_FAILED = "FAILED"
STAGE_SKIPPED = "SKIPPED"
STAGE_TERMINAL = (STAGE_COMPLETED, STAGE_FAILED, STAGE_SKIPPED)
JOB_TERMINAL_FAILED = ("FAILED", "CANCELLED")

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
S3_BOOT_IMAGES_BUCKET = "s3://boot-images/"
S3CMD_CONFIG = "/root/.s3cfg"
NFS_ARTIFACTS_DIR = "build_stream_root/artifacts"
# cleanup_cron.py / cleanup_job.py log lines (emitted through log_secure_info).
AUTO_CLEANUP_LOG_RE = {
    "failed_found": re.compile(r"found (\d+) FAILED ImageGroups"),
    "failed_phase": re.compile(
        r"FAILED phase\) complete: total=(\d+), cleaned=(\d+), errors=(\d+)"),
    "retention_started": re.compile(
        r"Retention evaluation started: retention_age_days=(\d+), min_keep_count=(\d+)"),
    "retention_eligible": re.compile(r"Retention evaluation: (\d+) ImageGroups eligible"),
    "retention_done": re.compile(
        r"Retention evaluation complete: eligible=(\d+), deleted=(\d+), errors=(\d+)"),
    "submitted": re.compile(r"Cleanup playbook submitted: image_group=([^,\s]+)"),
    "retention_deleted": re.compile(r"RETENTION_DELETED: image_group_id=([^,\s]+)"),
    "error": re.compile(r" - (?:ERROR|CRITICAL) - (.*)"),
}

# =============================================================================
# CLEANUP
# =============================================================================
CLEANUP_ORDER = (
    "cleanup_build_stream",
    "cleanup_orchestrator",
    "cleanup_image_build_manager",
    "cleanup_repo_manager",
)

# supported_vars: every extra variable the playbook honours, with its
#                 playbook default (None = interactive prompt).
# config_flags:   the flags a cleanup block in test_config.yml may set, with
#                 the value used when the block omits them.
# fixed_vars:     always passed so the playbook runs unattended.
# skip_tag_vars:  variables applied as --skip-tags <tag> when false instead
#                 of -e (the playbook gates them by tag, not by variable).
CLEANUP_DOMAINS = {
    "cleanup_build_stream": {
        "domain": "build_stream",
        "playbook": "build_stream.yml",
        "workdir": "src/build_stream/playbooks",
        "tag": "cleanup",
        "supported_vars": {"postgres_backup": True, "cleanup_credentials": True},
        "config_flags": {"postgres_backup": False, "cleanup_credentials": True},
        "fixed_vars": {},
        "skip_tag_vars": {"cleanup_credentials": "credentials"},
    },
    "cleanup_orchestrator": {
        "domain": "orchestrator",
        "playbook": "orchestrator.yml",
        "workdir": "src/orchestrator/playbooks",
        "tag": "cleanup",
        "supported_vars": {
            "skip_approval": False,
            "dry_run": False,
            "cleanup_credentials": True,
            "cleanup_slurm": None,
            "cleanup_k8s": None,
        },
        "config_flags": {"cleanup_credentials": True, "cleanup_slurm": True,
                         "cleanup_k8s": True},
        "fixed_vars": {"skip_approval": True},
        "skip_tag_vars": {},
    },
    "cleanup_image_build_manager": {
        "domain": "image_build_manager",
        "playbook": "image_build_manager.yml",
        "workdir": "src/image_build_manager/playbooks",
        "tag": "cleanup",
        "supported_vars": {"cleanup_credentials": True},
        "config_flags": {"cleanup_credentials": True},
        "fixed_vars": {},
        "skip_tag_vars": {"cleanup_credentials": "cleanup_credentials"},
    },
    "cleanup_repo_manager": {
        "domain": "repo_manager",
        "playbook": "repo_manager.yml",
        "workdir": "src/repo_manager/playbooks",
        "tag": "cleanup_pulp",
        "supported_vars": {"cleanup_logs": True, "cleanup_credentials": True},
        "config_flags": {"cleanup_logs": False, "cleanup_credentials": True},
        "fixed_vars": {},
        "skip_tag_vars": {},
    },
}

BSM_RUNTIME_DIRS = (
    "build_stream/log",
    "build_stream/playbook_queue",
    "playbook_queue",
    "build_stream_ssl",
    "build_stream_inv",
)
BSM_POSTGRES_DATA_DIR = "postgres"
BSM_CREDENTIAL_FILES = (
    "build_stream_credentials.yml",
    ".build_stream_credentials_key",
    "build_stream_oauth_credentials.yml",
    ".build_stream_oauth_credentials_key",
)

# OpenCHAMI deployment, from the product's own component specification
# (src/orchestrator/roles/cleanup/components/openchami/vars/component_spec.yml).
# Long-running containers (running after prepare, removed by cleanup).
ORCH_OPENCHAMI_CONTAINERS = (
    "boot-service",
    "coresmd-coredhcp",
    "coresmd-coredns",
    "haproxy",
    "metadata-service",
    "postgres",
    "smd",
    "step-ca",
    "tokensmith",
)
# One-shot init container: runs once at start, not kept running.
ORCH_OPENCHAMI_INIT_CONTAINER = "smd-init"
# Units active after prepare (one-shot units stay "active (exited)").
ORCH_OPENCHAMI_UNITS = (
    "openchami.target",
    "acme-deploy.service",
    "acme-register.service",
    "boot-service.service",
    "coresmd-coredhcp.service",
    "coresmd-coredns.service",
    "haproxy.service",
    "metadata-service.service",
    "openchami-cert-trust.service",
    "postgres.service",
    "smd-init.service",
    "smd.service",
    "step-ca.service",
    "tokensmith.service",
)
# Certificate renewal runs from a timer; its service is idle between runs.
ORCH_OPENCHAMI_TIMER = "openchami-cert-renewal.timer"
# Data volumes (component spec) plus the HAProxy certificate volume the
# validate_openchami role asserts.
ORCH_OPENCHAMI_VOLUMES = (
    "boot-service-data",
    "metadata-service-data",
    "postgres-data",
    "haproxy-certs",
)
# OpenLDAP (component spec openldap): deployed only when the catalog enables
# it; orchestrator_setup records openldap_support in orchestrator_state.yml.
ORCH_OPENLDAP_CONTAINER = "omnia_auth"
ORCH_OPENLDAP_SERVICE = "omnia_auth.service"
ORCH_OPENLDAP_QUADLET = "/etc/containers/systemd/omnia_auth.container"
ORCH_STATE_FILE = "output/{project}/orchestrator_state.yml"
ORCH_OPENLDAP_FLAG = "openldap_support"
ORCH_CREDENTIAL_FILES = (
    "orchestrator_credentials.yml",
    ".orchestrator_credentials_key",
)

IBM_CONTAINERS = ("minio-server", "registry")
IBM_SERVICES = ("minio.service", "registry.service")
IBM_PORTS = (9000, 9001, 5000)
IBM_BUILD_STATUS = "output/{project}/build_status.yml"
IBM_CREDENTIAL_FILES = (
    "image_build_credentials.yml",
    ".image_build_credentials_key",
)

RM_PULP_CONTAINER = "pulp"
RM_PULP_SERVICE = "pulp.service"
RM_PULP_QUADLET = "/etc/containers/systemd/pulp.container"
RM_PULP_DIRS = ("pulp_config",)
RM_LOG_DIRS = ("log",)
RM_CREDENTIAL_FILES = (
    "repo_manager_config_credentials.yml",
    ".repo_manager_config_credentials_key",
)

# Credential store (file, vault key) each domain playbook reads from its
# project input directory; a missing store makes the playbook prompt.
DOMAIN_CREDENTIAL_FILES = {
    "repo_manager": RM_CREDENTIAL_FILES,
    "image_build_manager": IBM_CREDENTIAL_FILES,
    "orchestrator": ORCH_CREDENTIAL_FILES,
    "build_stream": (BSM_CREDENTIALS_FILE, BSM_CREDENTIALS_KEY),
}

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
CLEANUP_STATUS_RAN = "ran"
CLEANUP_STATUS_FAILED = "failed"
CLEANUP_STATUS_DISABLED = "disabled"
CLEANUP_STATUS_NOT_RUN = "not_run"

# =============================================================================
# SHELL COMMANDS — named placeholders; run_cmd() shell-quotes every value.
# =============================================================================
CMDS = {
    # --- Podman ---
    "podman_container_exists": "podman container exists {name}",
    # Prints "<running> <health>"; health is empty without a healthcheck.
    "podman_container_running": (
        "podman inspect --format '{{{{.State.Running}}}} "
        "{{{{if .State.Health}}}}{{{{.State.Health.Status}}}}{{{{end}}}}' {name}"
    ),
    "podman_volume_exists": "podman volume exists {name}",
    "podman_postgres_volumes": (
        "podman volume ls --format '{{{{.Name}}}}' | grep -i postgres || true"
    ),
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
    "sha256_file": "sha256sum {path}",
    "copy_preserve": "cp -p -- {source} {target}",
    "install_file": "install -D -m 0644 -- {source} {target}",
    # Same listing and order as omnia.sh _catalog_sources (variants only).
    "list_catalog_variants": (
        "find {directory} -type f -name '*.json' -print 2>/dev/null | sort"
    ),
    "s3_list_recursive": "s3cmd -c {config} ls -r {bucket}",
    "container_python": "podman exec {container} python3 -c {code}",
    "newest_cadence_log_dir": "ls -1td {root}/cadence-* 2>/dev/null | head -n 1",
    "last_ansible_task": "grep -h 'TASK \\[' {directory}/*.log 2>/dev/null | tail -n 1",
    # Placeholders are quoted; the glob suffix stays outside the quotes.
    "stage_log_candidates": (
        "ls -1 {base}/*/{stage}_*_attempt*.log {job_dir}/{stage}_*_attempt*.log 2>/dev/null"
    ),
    "read_from_line": "tail -n +{start} {path} 2>/dev/null",
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
    "tables": (
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "ORDER BY tablename;"
    ),
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
    "newest_built_image_group": (
        "SELECT id, job_id, status, deploy_count, coalesce(last_deployed_at::text,''), "
        "coalesce(catalog_version,'') FROM image_groups WHERE status='BUILT' "
        "ORDER BY created_at DESC LIMIT 1;"
    ),
    "image_count": "SELECT count(*) FROM images WHERE image_group_id='{image_group_id}';",
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
