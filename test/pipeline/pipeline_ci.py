#!/usr/bin/env python3
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

"""Job logic of the Omnia GitLab pipeline (test/pipeline), standard library only.

The generated jobs of the cluster pipeline are one-line calls to this script, so
the logic is testable and the YAML stays small.  Every command runs on the OIM
over SSH:

    initialize            the whole initialization stage: init, checkout and, where the shares are
                          emptied later, nfs-check; leaves the marker the cleanup jobs need
    init                  check the CI/CD variables, the SSH trust and the inputs
    checkout              record the commit of the clone and copy omnia.env (the clone itself is
                          made by the bootstrap of the initialization job)
    nfs-check             read-only: every Slurm/K8s NFS share of the OIM's storage_config.yml mounts
    cleanup <domain>      the cleanup playbook of the domain: ./omnia.sh --run <domain> --tags
                          <cleanup tag> with the variables of the test_config.yml, in the Omnia venv
                          (no test runs here)
    cleanup-verify <domain>
                          fvt_<domain> cleanup verify in the Omnia venv: what the cleanup must have
                          left (orchestrator: its nfs_shares suite empties the NFS shares selected
                          by cleanup_slurm and cleanup_k8s)
    cleanup-omnia         one stage: omnia.sh --cleanup --all (fvt_main cleanup exec); not run when
                          a cleanup or a cleanup test failed
    cleanup-omnia-verify  fvt_main cleanup verify: what the Omnia reset must have left
    setup-main            one stage: omnia.sh -s, then copy clusters/<cluster>/inputs/<domain>/ of
                          every deploy domain to <data>/<domain>/input/<project>/ and the catalog
    install               omnia.sh -s only (recreates the Omnia venv, runs every domain-init)
    inputs                the input copy only
    credentials <domain>  OpenBao credentials of the domain, vault-encrypted on the OIM
    deploy <domain>       credentials, then every playbook tag, one by one, with
                          ./omnia.sh --run <domain> --tags <tag> (<DOMAIN>_TAGS overrides)
    pxeboot               orchestrator --tags pxeboot, its own stage after the orchestrator stage
    stage <domain> <tag>  fvt_<domain> <tag> exec
    verify <domain|main>  test config and credentials, then TEST_<DOMAIN>_CMD (default
                          ./run_validation.sh fvt_<domain> verify)
    summary               status of every job and the email; fails the pipeline when any job failed
                          (a failed test included)
    prepare-base          the credentials of repo_manager, image_build_manager and orchestrator, then
                          omnia.sh --prepare-base (build stream pipeline)
    setup-utils           omnia.sh -s, then the inputs of the utils domain (utils pipeline)

Every FVT run of the pipeline gets the pipeline id as its report id (run_id of test_config.yml and
CI_PIPELINE_ID), so the reports of all domains and phases carry the same id.

DRY_RUN=true prints what would run on the OIM and changes nothing.

The OIM password is read only from the cluster CI/CD variable and handed to ssh
through SSHPASS; it is never written to a file, an artifact or a command line.
A host key is required: PIPELINE_SSH_KNOWN_HOSTS (a File variable with the OIM host
key line), or PIPELINE_SSH_SKIP_HOST_KEY=true to accept the risk of an unchecked key.
"""

import glob
import json
import os
import re
import shlex
import shutil
import smtplib
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

DOMAINS = ("repo_manager", "image_build_manager", "discovery", "orchestrator", "telemetry",
           "utils", "build_stream")
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
SAFE_PATH = re.compile(r"^/[A-Za-z0-9._/-]+$")
SAFE_BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")
SAFE_TAG = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SAFE_URL = re.compile(r"^(https?://|git@)[A-Za-z0-9._:/@~+-]+$")
PROTECTED_PATHS = ("/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/lib64", "/media",
                   "/mnt", "/opt", "/opt/omnia", "/proc", "/root", "/run", "/sbin", "/srv",
                   "/sys", "/tmp",  # nosec B108
                   "/usr", "/var")  # deny list entries, never used as a path
STATUS_DIR = "pipeline_job_status"
ERROR_DIR = f"{STATUS_DIR}/errors"
MAX_REASON = 600
COMMIT_FILE = "actual_commit_sha.txt"
REPORT_DIR = "pipeline_reports"
REPORTS_DEFAULT = "/automation"
REPORTS_KEEP_DAYS = 30
REPORT_NAME = "omnia_fvt_pipeline_report"
TEST_MODULES = ("main", "repo_manager", "image_build_manager", "discovery", "orchestrator",
                "telemetry", "utils", "build_stream")
SAFE_TEST_CMD = re.compile(r"^\./run_validation\.sh [A-Za-z0-9_./ =:,@-]{1,200}$")
DOMAIN_STEPS = {
    "repo_manager": ("precheck", "prepare", "execute", "status"),
    "image_build_manager": ("validate", "prepare", "build"),
    "discovery": ("precheck", "validate", "execute"),
    "orchestrator": ("precheck", "prepare", "provision"),
    "telemetry": ("precheck", "validate", "deploy"),
    "build_stream": ("",),
    "utils": ("collect", "backup_oim_logs"),
}
CREDENTIAL_FILES = {
    "repo_manager": "repo_manager_config_credentials.yml",
    "image_build_manager": "image_build_credentials.yml",
    "discovery": "discovery_credentials.yml",
    "orchestrator": "orchestrator_credentials.yml",
    "telemetry": "telemetry_credentials.yml",
    "build_stream": "build_stream_credentials.yml",
    "utils": "install_os_credentials.yml",
}
OPTIONAL_CREDENTIALS = ("discovery",)
CLEANUP_TAGS = {
    "repo_manager": "cleanup_pulp",
    "image_build_manager": "cleanup",
    "discovery": "cleanup",
    "orchestrator": "cleanup",
    "telemetry": "cleanup",
    "utils": "cleanup",
    "build_stream": "cleanup",
}
SAFE_EXTRA_VAR = re.compile(r"^[A-Za-z0-9_]{1,40}=(true|false)$")
TEST_CREDENTIALS = ("orchestrator", "telemetry")
BAO_TIMEOUT = 30
SSH_RETRIES = 5
SSH_RETRY_WAIT = 10
LOG_DIR = "pipeline_job_logs"
HTML_REPORT_DIR = "pipeline_report"
MAX_LOG_BYTES = 3000000
SENSITIVE_INPUTS = ("pxe_mapping_file.csv",)
PRIVATE_INPUTS = ("secret.yaml",)
UNRESOLVED_INPUTS = ("secret.yaml", "values.yaml")
PLACEHOLDER_RE = re.compile(r"\$(?:\{(OMNIA_DATA_PATH|OMNIA_PROJECT_NAME)\}|(OMNIA_DATA_PATH|OMNIA_PROJECT_NAME)\b)")
NFS_PORT = 2049
PIP_INSTALL = """pip install -q -r requirements.txt
pip install -q --force-reinstall --no-deps ../plugins/dist/omnia_auto-*.whl"""
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


class Layout:
    """Where the files of a cluster are in the project, under clusters/<cluster>/inputs/.

    New layout: inputs/src/<domain>/ (the input files of a domain), inputs/src/main/omnia.env,
    inputs/src/main/catalog_rhel.json and inputs/test/<domain>/. Older projects keep
    inputs/<domain>/, inputs/omnia.env and catalogs/catalog_rhel.json (inputs/test is the same).
    """

    def __init__(self, cluster: str):
        self.cluster_root = f"clusters/{cluster}"
        self.root = f"{self.cluster_root}/inputs"
        self.new = os.path.isdir(f"{self.root}/src")

    def domain_dir(self, domain: str) -> str:
        return f"{self.root}/src/{domain}" if self.new else f"{self.root}/{domain}"

    def test_dir(self, domain: str) -> str:
        return f"{self.root}/test/{domain}"

    @property
    def env_file(self) -> str:
        return f"{self.root}/src/main/omnia.env" if self.new else f"{self.root}/omnia.env"

    @property
    def catalog(self) -> str:
        return (f"{self.root}/src/main/catalog_rhel.json" if self.new
                else f"{self.cluster_root}/catalogs/catalog_rhel.json")

    @property
    def storage_config(self) -> str:
        return self.domain_dir("orchestrator") + "/storage_config.yml"

    @property
    def name(self) -> str:
        return "inputs/src and inputs/test" if self.new else "inputs/<domain> (older layout)"


ACTIVATE = """DATA=$(grep '^OMNIA_DATA_PATH=' {install}/src/main/omnia.env 2>/dev/null | cut -d= -f2)
DATA="${{DATA:-/opt/omnia}}"; DATA="${{DATA%/}}"
if [ ! -f "$DATA/activate-omnia.sh" ]; then {missing}; fi
source "$DATA/activate-omnia.sh"
"""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


_LOGGED = [0]


def _log(text: str) -> None:
    """Keep what this job printed (an artifact), for the HTML report of the summary."""
    job = _env("CI_JOB_NAME")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", job) or _LOGGED[0] > MAX_LOG_BYTES:
        return
    text = _redact(ANSI_RE.sub("", text))
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(f"{LOG_DIR}/{job}.log", "a", encoding="utf-8") as handle:
            handle.write(text)
        _LOGGED[0] += len(text)
    except OSError:
        pass


def _say(message: str) -> None:
    print(message, flush=True)
    _log(message + "\n")


def _record_error(message: str) -> None:
    """Keep why this job failed (an artifact), so the summary mail can show it."""
    job = _env("CI_JOB_NAME")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", job):
        return
    try:
        os.makedirs(ERROR_DIR, exist_ok=True)
        with open(f"{ERROR_DIR}/{job}.txt", "w", encoding="utf-8") as handle:
            handle.write(_redact(message)[:MAX_REASON])
    except OSError:
        pass


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr, flush=True)
    _log(f"ERROR: {message}\n")
    _record_error(message)
    raise SystemExit(1)


def apply_cluster() -> str:
    """Map <PREFIX>_TARGET_* of the cluster to PIPELINE_TARGET_*; return the cluster name."""
    cluster = _env("CLUSTER")
    if not SAFE_NAME.match(cluster):
        _fail("CLUSTER is empty or not a plain name. HOW TO FIX: the parent trigger job passes it")
    prefix = cluster.upper().replace("-", "_")
    for name in ("IP", "USER", "PASS"):
        value = os.environ.get(f"{prefix}_TARGET_{name}", "")
        if not value:
            _fail(f"{prefix}_TARGET_{name} is not set. HOW TO FIX: add it as a CI/CD variable "
                  "(setup_gitlab_project.py --update sets them)")
        os.environ[f"PIPELINE_TARGET_{name}"] = value
    known = os.environ.get(f"{prefix}_SSH_KNOWN_HOSTS", "")
    if known and not _env("PIPELINE_SSH_KNOWN_HOSTS"):
        os.environ["PIPELINE_SSH_KNOWN_HOSTS"] = known
    return cluster


def install_path() -> str:
    path = _env("OMNIA_INSTALL_PATH", "/root/omnia").rstrip("/")
    if not SAFE_PATH.match(path) or path in PROTECTED_PATHS:
        _fail(f"OMNIA_INSTALL_PATH '{path}' is not a safe folder (a folder of its own, "
              "e.g. /root/omnia or /pipeline)")
    return path


def _ssh_options() -> List[str]:
    check: List[str] = []
    known = _env("PIPELINE_SSH_KNOWN_HOSTS")
    if known:
        check = ["-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={known}"]
    elif _env("PIPELINE_SSH_SKIP_HOST_KEY").lower() == "true":
        _say("WARNING: PIPELINE_SSH_SKIP_HOST_KEY=true, the OIM host key is not checked, so the "
             "connection can be intercepted. Set PIPELINE_SSH_KNOWN_HOSTS instead.")
        check = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    else:
        _fail("PIPELINE_SSH_KNOWN_HOSTS (a File variable with the OIM host key line) is required. "
              "HOW TO FIX: ssh-keyscan -t ed25519 <OIM> and add the line as the variable, or set "
              "PIPELINE_SSH_SKIP_HOST_KEY=true to accept the risk")
    return [*check, "-o", "LogLevel=ERROR", "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=10",
            "-o", f"ConnectTimeout={_env('SSH_CONNECT_TIMEOUT', '30')}"]


def _target() -> str:
    return f"{_env('PIPELINE_TARGET_USER', 'root')}@{_env('PIPELINE_TARGET_IP')}"


def _environment() -> Dict[str, str]:
    env = dict(os.environ)
    env["SSHPASS"] = os.environ.get("PIPELINE_TARGET_PASS", "")
    return env


def ssh_command() -> List[str]:
    return ["sshpass", "-e", "ssh", *_ssh_options(), _target()]


def _redact(text: str) -> str:
    secret = os.environ.get("PIPELINE_TARGET_PASS", "")
    return text.replace(secret, "********") if len(secret) >= 4 else text


LAST_OUTPUT: Deque[str] = deque(maxlen=6)


def remote(script: str, stdin: Optional[bytes] = None, capture: bool = False,
           retry: bool = False) -> Tuple[int, str]:
    """Run a bash script on the OIM (script on stdin of `bash -s`); stream or capture output."""
    attempts = SSH_RETRIES if retry else 1
    rc, out = 255, ""
    for attempt in range(1, attempts + 1):
        command = [*ssh_command(), "bash", "-s"] if stdin is None else [*ssh_command(), script]
        data = script.encode() if stdin is None else stdin
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, env=_environment())
        assert proc.stdin and proc.stdout
        proc.stdin.write(data)
        proc.stdin.close()
        lines: List[str] = []
        for raw in proc.stdout:
            line = _redact(raw.decode(errors="replace"))
            if line.strip():
                LAST_OUTPUT.append(line.strip())
            if capture:
                lines.append(line)
            else:
                print(line, end="", flush=True)
                _log(line)
        rc = proc.wait()
        out = "".join(lines)
        if rc != 255 or attempt == attempts:
            break
        _say(f"SSH connection failed, retry {attempt}/{attempts - 1} in {SSH_RETRY_WAIT}s")
        time.sleep(SSH_RETRY_WAIT)
    return rc, out


def _dry_run(what: str, script: str = "") -> bool:
    """With DRY_RUN=true print what would run on the OIM and return True."""
    if _env("DRY_RUN").lower() != "true":
        return False
    _say(f"DRY_RUN: would run on the OIM: {what}")
    if script:
        _say(script)
    return True


def _run(script: str, what: str) -> int:
    if _dry_run(what, script):
        return 0
    LAST_OUTPUT.clear()
    rc, _ = remote(script)
    if rc != 0:
        _say(f"ERROR: {what} failed (exit code {rc})")
        _record_error(f"{what} failed (exit code {rc}): " + " | ".join(list(LAST_OUTPUT)[-3:]))
    return rc


def _domain(name: str) -> str:
    if name not in DOMAINS:
        _fail(f"unknown domain '{name}'. Valid: {', '.join(DOMAINS)}")
    return name


def _tag(name: str) -> str:
    if not SAFE_TAG.match(name):
        _fail(f"'{name}' is not a plain tag name")
    return name


def _verbosity() -> str:
    """With VERBOSE=true: pytest -v and ansible -vvv for the FVT runs."""
    return "-v --ansible-verbosity 3" if _env("VERBOSE").lower() == "true" else ""


def _activate(missing: str) -> str:
    return ACTIVATE.format(install=shlex.quote(install_path()), missing=missing)


def init() -> int:
    cluster = apply_cluster()
    _ssh_options()
    install_path()
    for name, pattern in (("OMNIA_REPO", SAFE_URL), ("OMNIA_BRANCH", SAFE_BRANCH)):
        if not pattern.match(_env(name)):
            _fail(f"{name} is empty or has unsafe characters. HOW TO FIX: set the CI/CD variable")
    layout = Layout(cluster)
    if not os.path.isfile(layout.env_file):
        _fail(f"{layout.env_file} not found in the project")
    present = [d for d in DOMAIN_STEPS if os.path.isdir(layout.domain_dir(d))]
    _say(f"Cluster {cluster}: OIM {_env('PIPELINE_TARGET_IP')}, user {_env('PIPELINE_TARGET_USER')}")
    _say(f"Omnia {_env('OMNIA_REPO')} branch {_env('OMNIA_BRANCH')} at {install_path()}")
    _say(f"Project layout: {layout.name}")
    _say(f"Input folders in the project: {', '.join(present) or 'none'}")
    rc, _ = remote("echo SSH connection successful", retry=True)
    return rc


def _mark(name: str, rc: int) -> int:
    """Leave the marker artifact of a passed job (the always-running cleanup jobs check them)."""
    if rc == 0:
        os.makedirs(STATUS_DIR, exist_ok=True)
        with open(f"{STATUS_DIR}/{name}.ok", "w", encoding="utf-8") as handle:
            handle.write("ok\n")
    return rc


def _skipped(word: str) -> bool:
    """Return whether SKIP_STAGES (comma or space separated words) names exactly this word."""
    return word in re.split(r"[ ,]+", _env("SKIP_STAGES"))


def require_ready() -> None:
    """Fail fast when a job the cleanups depend on did not pass (its marker is missing).

    The cleanup jobs run even after another cleanup failed, so GitLab alone cannot stop them
    when initialization (the clone, the checks, the NFS check) failed.
    """
    if not os.path.isfile(f"{STATUS_DIR}/initialization.ok") and _env("DRY_RUN").lower() != "true":
        _fail("initialization did not pass, so nothing was cleaned. HOW TO FIX: fix that job "
              "(SSH, variables, an unreachable NFS share) and run the pipeline again")


def tolerated_jobs() -> List[str]:
    """Return the jobs whose failure is tolerated: the words of TOLERATE_FAILURES (job names).

    A tolerated job still runs and is shown as failed in the report and the mail, but it neither
    blocks the install nor fails the pipeline. Nothing is tolerated by default.
    """
    return [w for w in re.split(r"[ ,]+", _env("TOLERATE_FAILURES")) if SAFE_NAME.match(w)]


def failed_cleanups() -> List[str]:
    """Return the cleanup jobs and cleanup verifications that failed (tolerated ones do not count)."""
    return [name for name, status, _ in _statuses()
            if status == "failed" and name.startswith(("cleanup_", "test_cleanup_"))
            and name not in tolerated_jobs()]


def missing_cleanup_markers() -> List[str]:
    """Return the selected cleanups and cleanup tests that left no pass marker.

    Skipped jobs (SKIP_STAGES) and tolerated ones are not required. A job that died before it could
    report is missing here, which a status file saying ``failed`` alone would not show.
    """
    tolerated = tolerated_jobs()
    missing: List[str] = []
    for domain in CLEANUP_TAGS:
        for name, group in ((f"cleanup_{domain}", "cleanup"),
                            (f"test_cleanup_{domain}", "test_cleanup")):
            if any(_skipped(word) for word in (domain, name, group)) or name in tolerated:
                continue
            if not os.path.isfile(f"{STATUS_DIR}/{name}.ok"):
                missing.append(name)
    return missing


def require_cleanups_ok() -> None:
    """Fail when a cleanup failed, so nothing is installed or deployed after it.

    The cleanup jobs are allowed to fail so that every cleanup runs; this is the gate that
    stops the install, and so every stage after it, with a red pipeline.
    """
    failed = failed_cleanups()
    if failed and _env("DRY_RUN").lower() != "true":
        _fail(f"{', '.join(failed)} failed, so nothing is installed or deployed. HOW TO FIX: "
              "read the log of that cleanup job, fix the cause and run the pipeline again")


def checkout() -> int:
    """Finish the checkout the initialization job cloned: record the commit, copy omnia.env."""
    cluster = apply_cluster()
    path = install_path()
    if _dry_run(f"record the commit of {path} and copy omnia.env"):
        return 0
    rc, out = remote(f"git -C {shlex.quote(path)} rev-parse HEAD", capture=True, retry=True)
    commit = out.strip().splitlines()[-1].strip() if out.strip() else ""
    if rc or not re.fullmatch(r"[0-9a-f]{40}", commit):
        _say(f"ERROR: {path} on the OIM is not a git checkout. HOW TO FIX: the initialization "
             "job clones it; run the pipeline again")
        return rc or 1
    _say(f"Omnia commit {commit}")
    with open(COMMIT_FILE, "w", encoding="utf-8") as handle:
        handle.write(commit + "\n")
    with open(Layout(cluster).env_file, "rb") as handle:
        rc, _ = remote(f"cat > {shlex.quote(path)}/src/main/omnia.env", stdin=handle.read())
    return rc or prepare_reports()


def _domain_selected(domain: str) -> bool:
    """Return whether DOMAINS (default, or a regex) selects the domain."""
    selected = _env("DOMAINS")
    if selected in ("", "default"):
        return True
    try:
        return re.search(selected, domain) is not None
    except re.error:
        return True


def initialize() -> int:
    """The whole initialization stage: checks, commit and omnia.env, the NFS check.

    The marker the cleanup jobs need is left only when every step passed. The NFS check runs
    when the orchestrator is selected (its shares are mounted and, in cleanup and default
    mode, emptied later) unless SKIP_STAGES names nfs_check.
    """
    for step in (init, checkout):
        rc = step()
        if rc:
            return rc
    if (_env("PIPELINE_KIND") != "utils" and _domain_selected("orchestrator")
            and not _skipped("nfs_check")):
        rc = nfs_preflight()
        if rc:
            return rc
    return _mark("initialization", 0)


def _test_setting(cluster: str, domain: str, key: str, default: bool, block: str = "") -> bool:
    """Return the true/false setting ``key`` of the cluster's test_config.yml of the domain.

    ``block`` names a top-level mapping that holds the key (build_stream: ``cleanup``). The
    default of the test suite is returned when the file or the key is absent.
    """
    path = os.path.join(Layout(cluster).test_dir(domain), "test_config.yml")
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return default
    inside = not block
    for line in lines:
        if block and re.match(rf"^{re.escape(block)}:\s*(#.*)?$", line):
            inside = True
            continue
        if block and inside and re.match(r"^\S", line) and not line.startswith("#"):
            inside = False
        pattern = rf"^{'  ' if block else ''}{re.escape(key)}:\s*(true|false)\s*(#.*)?$"
        match = re.match(pattern, line) if inside else None
        if match:
            return match.group(1) == "true"
    return default


def cleanup_playbook_vars(cluster: str, domain: str) -> List[str]:
    """Return the ``key=value`` extra variables of the cleanup playbook of a domain.

    The same variables the FVT cleanup of the domain passes, from the cluster's test_config.yml
    (defaults of the suites when absent): orchestrator and build_stream pass every flag
    explicitly, the others only what differs from the playbook default.
    """
    def flag(key: str, default: bool, block: str = "") -> bool:
        return _test_setting(cluster, domain, key, default, block)

    def text(value: bool) -> str:
        return "true" if value else "false"

    if domain == "orchestrator":
        return [f"{k}={text(flag(k, True))}" for k in ("cleanup_credentials", "cleanup_slurm",
                                                       "cleanup_k8s")]
    if domain == "build_stream":
        return [f"postgres_backup={text(flag('postgres_backup', False, 'cleanup'))}",
                f"cleanup_credentials={text(flag('cleanup_credentials', True, 'cleanup'))}"]
    if domain == "telemetry":
        found = ["Delete_sinks_volume=true"] if flag("delete_sinks_volume", False) else []
        found += [f"{k}=false" for k in ("cleanup_credentials", "cleanup_logs")
                  if not flag(k, True)]
        return found
    if domain in ("repo_manager", "image_build_manager") and not flag("cleanup_credentials", True):
        return ["cleanup_credentials=false"]
    return []


def cleanup(domain: str) -> int:
    """Run the cleanup playbook of the domain with ``./omnia.sh --run <domain> --tags <tag>``.

    No test runs here: the next stage, ``cleanup_verify``, checks what the cleanup left. The tag
    and the extra variables are the ones the FVT cleanup of the domain uses
    (``CLEANUP_TAGS``, ``cleanup_playbook_vars``). A passed cleanup leaves the marker that stage
    needs. An OIM without an Omnia venv (the first run) has nothing to clean and passes.
    """
    cluster = apply_cluster()
    _domain(domain)
    require_ready()
    missing = f"echo 'No Omnia venv on the OIM, nothing to clean for {domain}'; exit 0"
    rc = _omnia_run(domain, CLEANUP_TAGS[domain], cleanup_playbook_vars(cluster, domain), missing)
    return _mark(f"cleanup_{domain}", rc)


def cleanup_verify(domain: str) -> int:
    """fvt_<domain> cleanup verify: what the cleanup must have left, in the Omnia venv.

    Runs right after the cleanup of the domain and before the Omnia cleanup, which removes the Omnia venv. It
    needs the Omnia venv and the test requirements (``_fvt`` activates and installs them). The
    orchestrator verification also empties the NFS shares (its ``nfs_shares`` suite).
    """
    cluster = apply_cluster()
    _domain(domain)
    require_ready()
    if not os.path.isfile(f"{STATUS_DIR}/cleanup_{domain}.ok") and _env("DRY_RUN").lower() != "true":
        _fail(f"cleanup_{domain} did not pass, so its result is not verified. HOW TO FIX: read the "
              f"log of cleanup_{domain}, fix the cause and run the pipeline again")
    extra = "--marker cleanup" if domain == "utils" else ""
    missing = f"echo 'No Omnia venv on the OIM, nothing to verify for {domain}'; exit 0"
    rc = _stage_test_files(cluster, domain)
    if not rc:
        rc = _fvt(domain, "cleanup", "verify", extra, missing)
    return _mark(f"test_cleanup_{domain}", rc)


NFS_SOURCE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9.-]{0,252}):(/[A-Za-z0-9._/-]{0,250})$")
NFS_CHECK = """check_one() {
  name=$1; source=$2; host=${2%%:*}
  if ! timeout 8 bash -c "exec 3<>/dev/tcp/$host/@PORT@" 2>/dev/null; then
    echo "FAIL $name $source: the NFS server $host does not answer on port @PORT@"; return 1
  fi
  d=$(mktemp -d /run/pipeline-nfs.XXXXXX) || { echo "FAIL $name $source: no temp folder"; return 1; }
  if ! err=$(timeout 90 mount -t nfs -o ro,soft,timeo=50,retrans=2 "$source" "$d" 2>&1); then
    echo "FAIL $name $source: the mount was refused: $err"; rmdir "$d" 2>/dev/null; return 1
  fi
  umount "$d" 2>/dev/null || umount -l "$d" 2>/dev/null; rmdir "$d" 2>/dev/null
  echo "OK   $name $source: reachable and mountable (read-only test)"
}
rc=0
command -v mount.nfs >/dev/null || { echo "ERROR: mount.nfs is missing on the OIM (install nfs-utils)"; exit 1; }
"""


def _nfs_mounts(layout: "Layout") -> List[Tuple[str, str]]:
    """Return (name, source) of every NFS entry of the project's storage_config.yml."""
    if not os.path.isfile(layout.storage_config):
        return []
    found: List[Tuple[str, str]] = []
    current: Dict[str, str] = {}

    def flush() -> None:
        if current.get("fs_type", "").lower() == "nfs" and current.get("source"):
            found.append((current.get("name", "?"), current["source"]))

    with open(layout.storage_config, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.split("#", 1)[0].rstrip()
            match = re.match(r"^\s*-\s*name:\s*[\"']?([^\"'\s]+)[\"']?\s*$", line)
            if match:
                flush()
                current = {"name": match.group(1)}
                continue
            match = re.match(r"^\s+(source|fs_type):\s*[\"']?([^\"']*)[\"']?\s*$", line)
            if match:
                current[match.group(1)] = match.group(2).strip()
    flush()
    return found


def nfs_preflight() -> int:
    """Check from the OIM that every NFS share of the storage config answers and mounts.

    Reads the project's storage_config.yml (no Omnia venv is needed, so it works on the first
    run). Every share is checked; a read-only mount test follows the port check. Fails the
    stage with one line per share.
    """
    cluster = apply_cluster()
    shares = _nfs_mounts(Layout(cluster))
    if not shares:
        _say("No NFS mount in the project's storage_config.yml: no share to check")
        return 0
    for name, source in shares:
        match = NFS_SOURCE.fullmatch(source)
        if not match or ".." in match.group(2).split("/") or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name):
            _fail(f"the NFS source '{source}' of {name} in storage_config.yml is not host:/export "
                  "of plain characters. HOW TO FIX: correct the mount")
    _say("NFS check from the OIM: " + ", ".join(f"{n} {s}" for n, s in shares))
    calls = "".join(f"check_one {shlex.quote(n)} {shlex.quote(s)} || rc=1\n" for n, s in shares)
    return _run(NFS_CHECK.replace("@PORT@", str(NFS_PORT)) + calls + "exit $rc\n", "the NFS check")


def _main_cleanup(command: str) -> int:
    """Run ``fvt_main cleanup <command>`` (exec or verify) of test/main with cleanup_all true.

    test/main uses its own venv (``./setup_env.sh --venv``), because the Omnia cleanup removes the
    Omnia venv and ``fvt_main cleanup`` refuses to run from it.
    """
    cluster = apply_cluster()
    path = install_path()
    rc = _stage_test_files(cluster, "main")
    if rc:
        return rc
    return _run(f"""set -e
cd {shlex.quote(path)}/test/main
grep -q '^cleanup_all:' test_config.yml && sed -i -E 's/^cleanup_all:.*/cleanup_all: true/' test_config.yml || echo 'cleanup_all: true' >> test_config.yml
chmod +x setup_env.sh run_validation.sh
./setup_env.sh --venv
source .venv/bin/activate
{_run_id_script()}./run_validation.sh fvt_main cleanup {command} {_verbosity()}
""", f"fvt_main cleanup {command} (omnia.sh --cleanup --all)")


def cleanup_omnia() -> int:
    """Reset Omnia (omnia.sh --cleanup --all): ``fvt_main cleanup exec`` from the test/main venv.

    It runs only when every cleanup and every cleanup test before it passed (the orchestrator ones
    empty the Slurm and K8s NFS shares); otherwise the Omnia venv is kept for the next try. A
    passed reset leaves the marker the next stage, ``cleanup_omnia_verify``, needs.
    """
    apply_cluster()
    require_ready()
    blocked = failed_cleanups()
    blocked += [name for name in missing_cleanup_markers() if name not in blocked]
    if blocked and _env("DRY_RUN").lower() != "true":
        _say(f"ERROR: {', '.join(blocked)} failed or left no pass marker, so the Omnia cleanup was "
             "not run and the Omnia venv is kept for the next try (the orchestrator ones empty the "
             "NFS shares)")
        _record_error(f"{', '.join(blocked)} did not pass, so the Omnia cleanup was not run")
        return 1
    return _mark("cleanup_omnia", _main_cleanup("exec"))


def cleanup_omnia_verify() -> int:
    """Check the Omnia reset: ``fvt_main cleanup verify`` from the test/main venv."""
    apply_cluster()
    require_ready()
    if not os.path.isfile(f"{STATUS_DIR}/cleanup_omnia.ok") and _env("DRY_RUN").lower() != "true":
        _fail("cleanup_omnia did not pass, so its result is not verified. HOW TO FIX: read the log "
              "of cleanup_omnia, fix the cause and run the pipeline again")
    return _main_cleanup("verify")


def install() -> int:
    apply_cluster()
    path = install_path()
    return _run(f"""set -e
cd {shlex.quote(path)}/src/main && chmod +x omnia.sh
./omnia.sh -s
DATA=$(grep '^OMNIA_DATA_PATH=' omnia.env 2>/dev/null | cut -d= -f2); DATA="${{DATA:-/opt/omnia}}"
DATA="${{DATA%/}}"
source "$DATA/activate-omnia.sh"
python3 --version
ansible --version | head -1
""", "omnia.sh -s")


def _resolve_layout() -> Tuple[str, str]:
    """Return (OMNIA_DATA_PATH, OMNIA_PROJECT_NAME) of the OIM, with the Omnia venv active."""
    missing = "echo 'ERROR: no Omnia venv, run the install stage first' >&2; exit 1"
    rc, out = remote(f"""set -e
{_activate(missing)}
echo "$OMNIA_DATA_PATH"
echo "${{OMNIA_PROJECT_NAME:-project_default}}"
""", capture=True)
    lines = [x.strip().rstrip("/") for x in out.splitlines() if x.strip()]
    if rc or len(lines) < 2:
        _fail("could not resolve OMNIA_DATA_PATH and OMNIA_PROJECT_NAME on the OIM")
    data, project = lines[-2], lines[-1]
    if not SAFE_PATH.match(data) or not SAFE_NAME.match(project):
        _fail("OMNIA_DATA_PATH or OMNIA_PROJECT_NAME on the OIM has unsafe characters")
    return data, project


def _push_folder(source: str, destination: str) -> int:
    """tar the local folder through ssh into destination (a safe path)."""
    tar = subprocess.Popen(["tar", "-C", source, "-czf", "-", "."], stdout=subprocess.PIPE)
    command = [*ssh_command(), f"mkdir -p {shlex.quote(destination)} && "
                               f"tar --no-same-owner -xzf - -C {shlex.quote(destination)}"]
    rc = subprocess.run(command, stdin=tar.stdout, env=_environment(), check=False).returncode
    tar.stdout.close()
    return rc or tar.wait()


def _refuse_symlinks(folder: str) -> None:
    """Fail when an input folder holds a symbolic link (it could point outside the project)."""
    for base, dirs, files in os.walk(folder):
        for name in dirs + files:
            if os.path.islink(os.path.join(base, name)):
                _fail(f"{os.path.join(base, name)} is a symbolic link. HOW TO FIX: put the real "
                      "file in the project input folder")


def _resolved_copy(folder: str, values: Dict[str, str]) -> Tuple[str, int]:
    """Return (folder to push, files rewritten): placeholders of the input YAML files resolved.

    ``$OMNIA_DATA_PATH``, ``${OMNIA_DATA_PATH}``, ``$OMNIA_PROJECT_NAME`` and
    ``${OMNIA_PROJECT_NAME}`` in the ``.yml`` / ``.yaml`` files are replaced with the values of the
    OIM, so a path such as the PowerScale ``csi_powerscale_driver_secret_file_path`` follows the
    data path and project of the OIM (Omnia itself needs an absolute path that exists). The
    secret and values files are never rewritten. When nothing needs resolving the folder itself is
    returned; otherwise a private copy (mode 700) that the caller removes.
    """
    hits: List[str] = []
    for base, _, files in os.walk(folder):
        for name in files:
            if name.endswith((".yml", ".yaml")) and name not in UNRESOLVED_INPUTS:
                path = os.path.join(base, name)
                with open(path, encoding="utf-8", errors="surrogateescape") as handle:
                    if PLACEHOLDER_RE.search(handle.read()):
                        hits.append(path)
    if not hits:
        return folder, 0
    copy = os.path.join(tempfile.mkdtemp(prefix="pipeline-inputs-"), "inputs")
    shutil.copytree(folder, copy, symlinks=False)
    for path in hits:
        target = os.path.join(copy, os.path.relpath(path, folder))
        with open(path, encoding="utf-8", errors="surrogateescape") as handle:
            text = PLACEHOLDER_RE.sub(lambda m: values[m.group(1) or m.group(2)], handle.read())
        with open(target, "w", encoding="utf-8", errors="surrogateescape") as handle:
            handle.write(text)
    return copy, len(hits)


def inputs(only: Sequence[str] = ()) -> int:
    """Copy the input folder of every domain (of the domains in ``only`` when given) and the catalog."""
    cluster = apply_cluster()
    if _dry_run("copy the input folder of every domain and the catalog to the OIM"):
        return 0
    data, project = _resolve_layout()
    layout = Layout(cluster)
    folders = [d for d in DOMAIN_STEPS if (not only or d in only)
               and os.path.isdir(layout.domain_dir(d))]
    if not folders:
        _fail(f"no domain input folder in the project. HOW TO FIX: add "
              f"{layout.domain_dir('<domain>')}/")
    failed = []
    for domain in folders:
        _refuse_symlinks(layout.domain_dir(domain))
    for domain in folders:
        destination = f"{data}/{domain}/input/{project}"
        _say(f"Copy {layout.domain_dir(domain)}/ -> {destination}/")
        source, resolved = _resolved_copy(layout.domain_dir(domain), {
            "OMNIA_DATA_PATH": data, "OMNIA_PROJECT_NAME": project})
        if resolved:
            _say(f"Resolved $OMNIA_DATA_PATH and $OMNIA_PROJECT_NAME in {resolved} file(s) of {domain}")
        try:
            pushed = _push_folder(source, destination)
        finally:
            if source != layout.domain_dir(domain):
                shutil.rmtree(os.path.dirname(source), ignore_errors=True)
        if pushed:
            failed.append(domain)
            continue
        protect = " ".join(shlex.quote(f"{destination}/{name}") for name in SENSITIVE_INPUTS)
        private = " ".join(shlex.quote(f"{destination}/{name}") for name in PRIVATE_INPUTS)
        remote(f"for f in {protect}; do [ -f \"$f\" ] && chmod 640 \"$f\"; done; "
               f"for f in {private}; do [ -f \"$f\" ] && chmod 600 \"$f\"; done; true")
    catalog = layout.catalog
    if os.path.isfile(catalog):
        with open(catalog, "rb") as handle:
            rc, _ = remote(f"mkdir -p {shlex.quote(data)}/catalog && "
                           f"cat > {shlex.quote(data)}/catalog/catalog_rhel.json",
                           stdin=handle.read())
        if rc:
            failed.append("catalog")
    else:
        _say(f"No catalog at {catalog}, skipped")
    if failed:
        _say(f"ERROR: copy failed for: {', '.join(failed)}")
        return 1
    _say(f"Inputs copied for: {', '.join(folders)}")
    return 0


def setup_main() -> int:
    """Stage setup_main: omnia.sh -s (default mode, or ENABLE_SETUP=true), then the inputs.

    The inputs of every deploy domain are copied after omnia.sh -s created the domain folders,
    in default and deploy mode (not in cleanup mode); SKIP_STAGES=inputs skips only that step.
    """
    apply_cluster()
    require_cleanups_ok()
    mode = _env("PIPELINE_MODE")
    if mode == "default" or _env("ENABLE_SETUP").lower() == "true":
        rc = install()
        if rc:
            return rc
    if mode in ("default", "deploy") and not _skipped("inputs"):
        return inputs()
    return 0


def setup_utils() -> int:
    """Stage setup_utils of the utils pipeline: omnia.sh -s, then the inputs of the utils domain."""
    apply_cluster()
    rc = install()
    return rc or inputs(("utils",))


_NO_VENV = "echo 'ERROR: no Omnia venv, run the install stage first' >&2; exit 1"


def _put(path: str, data: bytes, mode: str = "600") -> int:
    """Write data to a file on the OIM (private by default)."""
    folder = os.path.dirname(path)
    rc, _ = remote(f"umask 077; mkdir -p {shlex.quote(folder)} && cat > {shlex.quote(path)} && "
                   f"chmod {mode} {shlex.quote(path)}", stdin=data)
    return rc


def _bao_context() -> ssl.SSLContext:
    ca = _env("BAO_CA_CERT")
    if ca:
        return ssl.create_default_context(cafile=ca)
    if _env("BAO_TLS_SKIP_VERIFY", "true").lower() == "false":
        return ssl.create_default_context()
    _say("WARNING: OpenBao TLS is not verified (like test/pipeline always did). Set BAO_CA_CERT "
         "or BAO_TLS_SKIP_VERIFY=false to verify it.")
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _bao_call(url: str, data: Optional[dict] = None, token: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers,
                                     method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(request, timeout=BAO_TIMEOUT,  # nosec B310  # https url
                                    context=_bao_context()) as response:
            return json.loads(response.read().decode())
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RuntimeError(f"OpenBao request failed: {exc.__class__.__name__}") from exc


def bao_secret(name: str) -> Optional[str]:
    """Return the credential file text of OpenBao secret `name`, or None (names only in logs)."""
    server, role = _env("BAO_SERVER_URL").rstrip("/"), _env("BAO_AUTH_ROLE")
    jwt, path = _env("VAULT_ID_TOKEN"), _env("BAO_DATA_PATH").strip("/")
    if not server:
        _say("ERROR: BAO_SERVER_URL is not set. HOW TO FIX: set the BAO_* CI/CD variables")
        return None
    if not server.startswith("https://"):
        _say("ERROR: BAO_SERVER_URL must start with https://, the credentials are not sent in "
             "clear text. HOW TO FIX: use the https URL of OpenBao, BAO_CA_CERT verifies its TLS")
        return None
    if not (jwt and role and path and SAFE_NAME.match(name)):
        _say("ERROR: VAULT_ID_TOKEN, BAO_AUTH_ROLE or BAO_DATA_PATH is missing")
        return None
    try:
        login = _bao_call(f"{server}/v1/auth/jwt/login", {"jwt": jwt, "role": role})
        token = login["auth"]["client_token"]
        reply = _bao_call(f"{server}/v1/{path}/{name}", token=token)
    except (RuntimeError, KeyError, TypeError) as exc:
        _say(f"ERROR: OpenBao: {exc}")
        return None
    data = reply.get("data") or {}
    fields = data["data"] if isinstance(data.get("data"), dict) else data
    fields = {k: v for k, v in fields.items() if k != "metadata"}
    if not fields:
        return None
    if len(fields) == 1 and isinstance(next(iter(fields.values())), str):
        return json.dumps(next(iter(fields.values()))) + "\n"
    return "".join(f"{key}: {json.dumps(value)}\n" for key, value in fields.items())


def _encrypt(file_path: str, key_path: str, venv: bool) -> str:
    """Remote script that vault-encrypts a credential file unless it already is."""
    return f"""{_activate(_NO_VENV) if venv else ""}
f={shlex.quote(file_path)}; k={shlex.quote(key_path)}
if [ -f "$f" ]; then
  if head -n1 "$f" | grep -q '$ANSIBLE_VAULT;'; then echo 'Credential file is already encrypted'
  else
    [ -f "$k" ] || {{ umask 077; openssl rand -base64 32 > "$k"; chmod 600 "$k"; }}
    ansible-vault encrypt --vault-password-file="$k" "$f" && echo 'Credential file encrypted'
  fi
fi
"""


def credentials(domain: str) -> int:
    """Fetch the domain credentials from OpenBao into <data>/<domain>/input/<project>/ (encrypted)."""
    apply_cluster()
    _domain(domain)
    name = CREDENTIAL_FILES.get(domain)
    if not name:
        return 0
    if _dry_run(f"fetch {domain} credentials from OpenBao and encrypt {name}"):
        return 0
    text = bao_secret(domain)
    if text is None:
        if domain in OPTIONAL_CREDENTIALS:
            _say(f"WARNING: no {domain} credentials in OpenBao, using the input files only")
            return 0
        _say(f"ERROR: could not fetch the {domain} credentials from OpenBao")
        return 1
    data, project = _resolve_layout()
    folder = f"{data}/{domain}/input/{project}"
    if _put(f"{folder}/{name}", text.encode()):
        return 1
    _say(f"{domain} credentials written ({len(text.splitlines())} fields), encrypting")
    return _run(_encrypt(f"{folder}/{name}", f"{folder}/.{name.replace('.yml', '')}_key", True),
                f"encrypt {name}")


SAFE_EXTRA = re.compile(r"^(--marker [a-z_]{1,32})?$")


def _reports_path() -> str:
    """Return the folder of the pipeline's one test report on the OIM (a safe absolute path)."""
    path = _env("TEST_REPORTS_PATH", REPORTS_DEFAULT).rstrip("/")
    if not SAFE_PATH.match(path) or path in PROTECTED_PATHS or ".." in path.split("/"):
        _fail(f"TEST_REPORTS_PATH '{path}' is not a safe folder of its own (e.g. {REPORTS_DEFAULT})")
    return path


def _report_settings_script() -> str:
    """Bash lines that point test_config.yml at the pipeline's one report.

    Every module gets the pipeline id as ``run_id``, the same ``report_name`` and the same
    ``report_path``, so all FVT runs of the pipeline (every cleanup, tag and verify) write into one
    report file ``<report_path>/<pipeline id>_<report_name>.json/.html``; each run is its own suite
    (``<domain>_<tag>`` or ``<domain>``). Every value is validated, nothing comes from a secret.
    Nothing is set outside CI.
    """
    pipeline_id = _env("CI_PIPELINE_ID")
    if not re.fullmatch(r"[0-9]{1,12}", pipeline_id):
        return ""
    values = (("run_id", pipeline_id), ("report_name", REPORT_NAME), ("report_path", _reports_path()))
    lines = f"export CI_PIPELINE_ID={pipeline_id}\n"
    for key, value in values:
        lines += (f"if grep -q '^{key}:' test_config.yml 2>/dev/null; then "
                  f"sed -i -E 's|^{key}:.*|{key}: \"{value}\"|' test_config.yml; "
                  f"else echo '{key}: \"{value}\"' >> test_config.yml; fi\n")
    return lines


_run_id_script = _report_settings_script


def prepare_reports() -> int:
    """Right after the clone: every module's test_config.yml reports into the one pipeline report.

    Creates the report folder (mode 750) and sets ``run_id``, ``report_name`` and ``report_path``
    in ``test/<module>/test_config.yml`` of the clone. The cluster's own test configs are copied
    later; those runs set the same three values again.
    """
    apply_cluster()
    script = _report_settings_script()
    if not script:
        _say("CI_PIPELINE_ID is not set: the test configs keep their report settings")
        return 0
    if _dry_run("point every test_config.yml at the pipeline report", script):
        return 0
    path = install_path()
    body = "".join(f"[ -d {shlex.quote(f'{path}/test/{m}')} ] && (cd {shlex.quote(f'{path}/test/{m}')}\n"
                   f"{script})\n" for m in TEST_MODULES)
    keep = _env("REPORTS_KEEP_DAYS", str(REPORTS_KEEP_DAYS))
    if not re.fullmatch(r"[0-9]{1,4}", keep) or int(keep) < 1:
        _fail(f"REPORTS_KEEP_DAYS '{keep}' is not a number of days (1 or more)")
    folder = shlex.quote(_reports_path())
    rc = _run(f"""set -e
umask 027; mkdir -p {folder}; chmod 750 {folder}
find {folder} -maxdepth 1 -type f -name '[0-9]*_{REPORT_NAME}.*' -mtime +{int(keep)} -delete || true
{body}true
""", "set run_id, report_name and report_path in every test_config.yml")
    if not rc:
        _say(f"Reports of this pipeline: {_reports_path()}/{_env('CI_PIPELINE_ID')}_{REPORT_NAME}.html")
    return rc


def _stage_test_files(cluster: str, domain: str, bao: bool = False) -> int:
    """Copy the cluster's test_config.yml, test_run_config.yml and test credentials to the OIM.

    The files of ``clusters/<cluster>/inputs/test/<domain>/`` replace the defaults of the
    checkout (an absent file keeps the default). The credentials come from the File variable
    ``<CLUSTER>_TEST_CREDS`` and, with ``bao`` (a job that has the OpenBao token), for
    orchestrator and telemetry from the OpenBao secret ``test_<domain>``, which wins. They are
    vault-encrypted on the OIM.
    """
    if _dry_run(f"copy the test config of {domain} to the OIM"):
        return 0
    target = f"{install_path()}/test/{domain}"
    source = Layout(cluster).test_dir(domain)
    for name in ("test_config.yml", "test_run_config.yml"):
        file_path = os.path.join(source, name)
        if os.path.isfile(file_path):
            with open(file_path, "rb") as handle:
                if _put(f"{target}/{name}", handle.read(), "644"):
                    return 1
        else:
            _say(f"{name} not in the project, using the defaults of the checkout")
    creds_file = _env(f"{cluster.upper().replace('-', '_')}_TEST_CREDS")
    placed = bool(creds_file and os.path.isfile(creds_file))
    if placed:
        with open(creds_file, "rb") as handle:
            if _put(f"{target}/test_creds.yml", handle.read()):
                return 1
    if bao and domain in TEST_CREDENTIALS:
        text = bao_secret(f"test_{domain}")
        if text is None:
            _say(f"WARNING: no test_{domain} credentials from OpenBao, using the existing ones")
        elif _put(f"{target}/test_creds.yml", text.encode()):
            return 1
        placed = True
    if placed:
        return _run(f"cd {shlex.quote(target)}\n" + _encrypt("test_creds.yml", ".test_creds.key", True),
                    "encrypt test_creds.yml")
    return 0


def _fvt(domain: str, tag: str, command: str, extra: str = "", missing: str = _NO_VENV) -> int:
    """Run ./run_validation.sh fvt_<domain> <tag> <command> [--marker <name>] in the Omnia venv."""
    apply_cluster()
    _domain(domain)
    if tag:
        _tag(tag)
    if not SAFE_EXTRA.match(extra) or (not tag and (extra or command != "exec")):
        _fail(f"'{extra}' is not a --marker option of plain characters")
    path = install_path()
    return _run(f"""set -e
{_activate(missing)}
cd {shlex.quote(path)}/test/{domain}
{PIP_INSTALL}
{_run_id_script()}./run_validation.sh fvt_{domain} {tag} {command} {extra} {_verbosity()}
""", f"fvt_{domain} {tag} {command} {extra}".replace("  ", " ").strip())


def _omnia_run(domain: str, tag: str, extra_vars: Sequence[str] = (), missing: str = "") -> int:
    """Run ./omnia.sh --run <domain> --tags <tag> [-e key=value ...] in the Omnia venv."""
    apply_cluster()
    _domain(domain)
    path = install_path()
    for item in extra_vars:
        if not SAFE_EXTRA_VAR.match(item):
            _fail(f"'{item}' is not a key=true|false extra variable")
    extras = "".join(f" -e {shlex.quote(item)}" for item in extra_vars)
    tags = f" --tags {_tag(tag)}" if tag else ""
    return _run(f"""set -e
{_activate(missing or _NO_VENV)}
cd {shlex.quote(path)}/src/main && chmod +x omnia.sh
./omnia.sh --run {domain}{tags}{extras}
""", f"omnia.sh --run {domain}{tags}{extras}")


def deploy(domain: str) -> int:
    """Domain stage: its credentials, then its playbook tags one by one with omnia.sh --run.

    The tags are the domain's DOMAIN_STEPS, or the comma list of <DOMAIN>_TAGS. The first tag that
    fails stops the stage. The verify stage afterwards still goes through run_validation.
    """
    apply_cluster()
    _domain(domain)
    require_cleanups_ok()
    if domain not in DOMAIN_STEPS:
        _fail(f"{domain} has no deploy steps. Valid: {', '.join(DOMAIN_STEPS)}")
    tags = [t.strip() for t in _env(f"{domain.upper()}_TAGS").split(",") if t.strip()]
    steps = tags or list(DOMAIN_STEPS[domain])
    if domain != "utils" or "install_os" in steps:
        rc = credentials(domain)
        if rc:
            return rc
    for tag in steps:
        _say(f"===== {domain}: {tag or 'the complete playbook'} "
             f"(omnia.sh --run {domain}{f' --tags {tag}' if tag else ''}) =====")
        rc = _omnia_run(domain, tag)
        if rc:
            return rc
    return 0


def pxeboot() -> int:
    """Orchestrator pxeboot stage: ./omnia.sh --run orchestrator --tags pxeboot.

    A stage of its own after the orchestrator stage. GitLab runs it only when the orchestrator
    stage passed, and the orchestrator verify stage only when this one passed. The credentials
    were put on the OIM by the orchestrator stage.
    """
    apply_cluster()
    require_cleanups_ok()
    _say("===== orchestrator: pxeboot (omnia.sh --run orchestrator --tags pxeboot) =====")
    return _omnia_run("orchestrator", "pxeboot")


def prepare_base() -> int:
    """Stage prepare_base of the build stream pipeline: the credentials of the base domains, then
    ``./omnia.sh --prepare-base`` (repo_manager, image_build_manager and orchestrator)."""
    apply_cluster()
    require_cleanups_ok()
    for domain in ("repo_manager", "image_build_manager", "orchestrator"):
        rc = credentials(domain)
        if rc:
            return rc
    return _run(f"""set -e
{_activate(_NO_VENV)}
cd {shlex.quote(install_path())}/src/main && chmod +x omnia.sh
./omnia.sh --prepare-base
""", "omnia.sh --prepare-base")


def _test_command(domain: str) -> str:
    command = _env(f"TEST_{domain.upper()}_CMD") or f"./run_validation.sh fvt_{domain} verify"
    if not SAFE_TEST_CMD.match(command):
        _fail(f"TEST_{domain.upper()}_CMD is not a ./run_validation.sh command of plain characters")
    return command


def verify_domain(domain: str) -> int:
    """Test stage: the cluster's test config and credentials, then the verify command."""
    cluster = apply_cluster()
    if domain != "main":
        _domain(domain)
    path = install_path()
    command = _test_command(domain)
    if _dry_run(f"copy the test config and run: {command}"):
        return 0
    target = f"{path}/test/{domain}"
    rc = _stage_test_files(cluster, domain, bao=True)
    if rc:
        return rc
    return _run(f"""set -e
{_activate(_NO_VENV)}
cd {shlex.quote(target)}
{PIP_INSTALL}
export CI_PIPELINE_ID={shlex.quote(_env("CI_PIPELINE_ID", "0"))}
{_run_id_script()}{command}
""", command)


def _statuses() -> List[Tuple[str, str, str]]:
    """Return (job, status, url) of every job that left a status file (the latest per job)."""
    found: Dict[str, Tuple[str, str, str]] = {}
    for name in sorted(glob.glob(f"{STATUS_DIR}/**/*.json", recursive=True)):
        try:
            with open(name, encoding="utf-8") as handle:
                item = json.load(handle)
            found[str(item["name"])] = (str(item["name"]), str(item["status"]),
                                        str(item.get("url", "")))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return list(found.values())


def _api_get(path: str, token: str, header: str, raw: bool = False) -> Any:
    """GET a path of the GitLab API of this project (JSON, or the text with raw=True)."""
    context = ssl.create_default_context(cafile=_env("CI_SERVER_TLS_CA_FILE") or None)
    request = urllib.request.Request(  # nosec B310  # GitLab API of this project (https)
        f"{_env('CI_API_V4_URL')}{path}", headers={header: token})
    with urllib.request.urlopen(request, context=context, timeout=30) as response:  # nosec B310
        data = response.read()
    return data.decode(errors="replace") if raw else json.loads(data)


def _api_job_details() -> List[Dict[str, Any]]:
    """Return the jobs of this pipeline from the GitLab API, without the summary job.

    It lists the jobs GitLab skipped too (they leave no status file). Best effort: [] when the
    API is not reachable or the job token is refused.
    """
    token = os.environ.get("CI_JOB_TOKEN", "")
    if not (_env("CI_API_V4_URL") and token and _env("CI_PROJECT_ID") and _env("CI_PIPELINE_ID")):
        return []
    try:
        items = _api_get(f"/projects/{_env('CI_PROJECT_ID')}/pipelines/{_env('CI_PIPELINE_ID')}"
                         "/jobs?per_page=100", token, "JOB-TOKEN")
        return [{"id": j.get("id"), "name": str(j["name"]), "status": str(j["status"]),
                 "url": str(j.get("web_url", "")), "duration": j.get("duration"),
                 "started_at": j.get("started_at"), "finished_at": j.get("finished_at"),
                 "allow_failure": bool(j.get("allow_failure")),
                 "runner": (j.get("runner") or {}).get("description", "")}
                for j in items if j.get("name") != "summary"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []


def _api_jobs() -> List[Tuple[str, str, str]]:
    """Return (job, status, page) of every job of this pipeline from the GitLab API."""
    return [(j["name"], j["status"], j["url"]) for j in _api_job_details()]


def _job_logs(jobs: List[Dict[str, Any]]) -> Dict[str, str]:
    """Return {job: its log}: from the GitLab API with PIPELINE_API_TOKEN, else as the job kept it."""
    token = os.environ.get("PIPELINE_API_TOKEN", "")
    logs: Dict[str, str] = {}
    from_api = 0
    for job in jobs:
        text = ""
        if token and job.get("id") and _env("CI_PROJECT_ID"):
            try:
                text = _api_get(f"/projects/{_env('CI_PROJECT_ID')}/jobs/{job['id']}/trace",
                                token, "PRIVATE-TOKEN", raw=True)
                from_api += bool(text)
            except (OSError, ValueError):
                text = ""
        if not text:
            try:
                with open(f"{LOG_DIR}/{job['name']}.log", encoding="utf-8") as handle:
                    text = handle.read()
            except OSError:
                text = ""
        logs[job["name"]] = _redact(text)
    _say(f"Stage logs for the report: {from_api} from the GitLab API, "
         f"{sum(1 for t in logs.values() if t) - from_api} as the jobs kept them"
         + ("" if token else " (PIPELINE_API_TOKEN is not set, so the GitLab runner lines are missing)"))
    return logs


def _build_html_report(jobs: List[Dict[str, Any]]) -> Optional[Tuple[str, bytes, bytes]]:
    """Write pipeline_report/pipeline_<id>.html and return (name, content); None when it fails."""
    pipeline_id = _env("CI_PIPELINE_ID", "0")
    if not re.fullmatch(r"[0-9]{1,12}", pipeline_id):
        return None
    commit = ""
    if os.path.isfile(COMMIT_FILE):
        with open(COMMIT_FILE, encoding="utf-8") as handle:
            commit = handle.read().strip()
    info = {"cluster": _env("CLUSTER"), "mode": _env("PIPELINE_MODE"), "domains": _env("DOMAINS"),
            "repo": _env("OMNIA_REPO"), "branch": _env("OMNIA_BRANCH"), "commit": commit,
            "pipeline_url": _env("CI_PIPELINE_URL"), "pipeline_id": pipeline_id,
            "user": _env("GITLAB_USER_LOGIN"), "trigger_time": _env("CI_PIPELINE_CREATED_AT"),
            "generated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    try:
        from library.functions import report_func  # pylint: disable=import-outside-toplevel
        from library.vars.report_vars import (  # pylint: disable=import-outside-toplevel
            MAIL_LOG_CHARS, MAIL_LOG_HEAD_CHARS)
        order = [x for x in _env("PIPELINE_JOB_ORDER").split(",") if x]
        logs, reasons = _job_logs(jobs), _reasons()
        page = report_func.build_report(info, jobs, logs, reasons, order)
        mail_page = report_func.build_report(info, jobs, logs, reasons, order,
                                             MAIL_LOG_CHARS, MAIL_LOG_HEAD_CHARS)
    except (ImportError, OSError, ValueError, KeyError, TypeError) as exc:
        _say(f"WARNING: the HTML report was not built: {type(exc).__name__}: {exc}")
        return None
    name = f"pipeline_{pipeline_id}_report.html"
    os.makedirs(HTML_REPORT_DIR, exist_ok=True)
    with open(f"{HTML_REPORT_DIR}/{name}", "w", encoding="utf-8") as handle:
        handle.write(page)
    _say(f"HTML report of the stages and their logs: {HTML_REPORT_DIR}/{name} ({len(page) // 1024} KB)")
    return name, page.encode(), mail_page.encode()


def _reasons() -> Dict[str, str]:
    """Return {job: why it failed} from the files the failed jobs left."""
    found: Dict[str, str] = {}
    for name in glob.glob(f"{ERROR_DIR}/*.txt"):
        try:
            with open(name, encoding="utf-8") as handle:
                found[os.path.basename(name)[:-4]] = handle.read().strip()
        except OSError:
            continue
    return found


def _fetch_reports() -> List[Tuple[str, bytes]]:
    """Copy the pipeline's one test report (HTML and JSON) from the OIM to pipeline_reports/.

    Every test run of the pipeline writes into ``<report folder>/<pipeline id>_<report name>``;
    that is the only report fetched, once, by the summary.
    """
    path = _reports_path()
    pipeline_id = _env("CI_PIPELINE_ID")
    if (_env("DRY_RUN").lower() == "true" or not SAFE_PATH.match(path)
            or not re.fullmatch(r"[0-9]{1,12}", pipeline_id)):
        return []
    reports: List[Tuple[str, bytes]] = []
    os.makedirs(REPORT_DIR, exist_ok=True)
    for extension in ("html", "json"):
        name = f"{pipeline_id}_{REPORT_NAME}.{extension}"
        rc, content = remote(f"cat {shlex.quote(f'{path}/{name}')}", capture=True)
        if rc == 0 and content.strip():
            with open(os.path.join(REPORT_DIR, name), "w", encoding="utf-8") as handle:
                handle.write(content)
            reports.append((name, content.encode()))
    _say(f"{len(reports)} test report file(s) fetched from the OIM ({path}/{pipeline_id}_{REPORT_NAME}.*)")
    return reports


def _mail_attachments(reports: List[Tuple[str, bytes]],
                      stages_report: Optional[Tuple[str, bytes, bytes]]) -> List[Tuple[str, bytes]]:
    """Return the two files of the mail: the test report (HTML) and the report of the stages.

    The JSON of the test report and the full stage report stay in the job artifacts.
    """
    files = [item for item in reports if item[0].endswith(".html")]
    if stages_report:
        files.append((stages_report[0], stages_report[2]))
    return files


def _send_summary_email(jobs: List[Tuple[str, str, str]], reports: List[Tuple[str, bytes]]) -> bool:
    """Send the summary email; True when it is not configured or was sent."""
    recipients = [r.strip() for r in _env("EMAIL_RECIPIENTS").split(",") if r.strip()]
    server, sender = _env("SMTP_SERVER"), _env("EMAIL_SENDER")
    if not (recipients and server and sender):
        _say("email not configured (EMAIL_RECIPIENTS, EMAIL_SENDER, SMTP_SERVER): not sent")
        return True
    from library.functions import email_func  # pylint: disable=import-outside-toplevel
    commit = ""
    if os.path.isfile(COMMIT_FILE):
        with open(COMMIT_FILE, encoding="utf-8") as handle:
            commit = handle.read().strip()
    info = {"cluster": _env("CLUSTER"), "mode": _env("PIPELINE_MODE"), "domains": _env("DOMAINS"),
            "repo": _env("OMNIA_REPO"), "branch": _env("OMNIA_BRANCH"), "commit": commit,
            "pipeline_url": _env("CI_PIPELINE_URL"), "job_url": _env("CI_JOB_URL"),
            "trigger_time": _env("CI_PIPELINE_CREATED_AT")}
    order = [x for x in _env("PIPELINE_JOB_ORDER").split(",") if x]
    message = email_func.build_message(sender=sender, recipients=recipients, info=info, jobs=jobs,
                                       order=order, attachments=reports, reasons=_reasons())
    try:
        email_func.send_message(message, server, int(_env("SMTP_PORT", "25") or 25),
                                _env("SMTP_USER"), os.environ.get("SMTP_PASSWORD"))
    except (OSError, ValueError, smtplib.SMTPException) as exc:
        _say("=" * 72 + f"\nERROR: the summary email was NOT sent to {', '.join(recipients)}: "
             f"{type(exc).__name__}: {exc}\n" + "=" * 72)
        return False
    _say(f"email sent to {', '.join(recipients)}")
    return True


def summary() -> int:
    """Print the status of every job, send the summary email, fail when a job failed."""
    try:
        apply_cluster()
        on_oim = True
    except SystemExit:
        on_oim = False
        _say("WARNING: the cluster variables are missing, so the test reports cannot be fetched "
             "from the OIM; the job table and the mail are still produced")
    details = _api_job_details()
    local = {name: (name, status, url) for name, status, url in _statuses()}
    api = {j["name"]: (j["name"], j["status"], j["url"] or local.get(j["name"], ("", "", ""))[2])
           for j in details}
    jobs = list(({**local, **api}).values())
    width = max([len(n) for n, _, _ in jobs] + [4])
    _say(f"Pipeline summary, cluster {_env('CLUSTER')}")
    for name, status, _ in jobs:
        _say(f"  {name:<{width}}  {status}")
    failed = [n for n, st, _ in jobs if st == "failed"]
    _say(f"{len(jobs)} jobs, {len(failed)} failed" + (f": {', '.join(failed)}" if failed else ""))
    attachments = _fetch_reports() if on_oim else []
    built = _build_html_report(details or [
        {"id": None, "name": n, "status": st, "url": url} for n, st, url in jobs])
    _send_summary_email(jobs, _mail_attachments(attachments, built))
    tolerated = [n for n in failed if n in tolerated_jobs()]
    if tolerated:
        _say(f"Failures tolerated (TOLERATE_FAILURES): {', '.join(tolerated)}")
    blocking = [n for n in failed if n not in tolerated_jobs()]
    if blocking:
        _say(f"The pipeline fails because of: {', '.join(blocking)}")
    return 1 if blocking else 0


def main(argv: List[str]) -> int:
    one = {"cleanup": cleanup, "cleanup-verify": cleanup_verify, "credentials": credentials,
           "deploy": deploy, "verify": verify_domain}
    none = {"initialize": initialize, "init": init, "checkout": checkout,
            "nfs-check": nfs_preflight, "cleanup-omnia": cleanup_omnia,
            "cleanup-omnia-verify": cleanup_omnia_verify, "pxeboot": pxeboot,
            "setup-main": setup_main, "install": install, "inputs": inputs, "summary": summary,
            "setup-utils": setup_utils, "prepare-base": prepare_base}
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    name, args = argv[0], argv[1:]
    if name in none and not args:
        return none[name]()
    if name in one and len(args) == 1:
        return one[name](args[0])
    if name == "stage" and len(args) == 2:
        return _fvt(args[0], args[1], "exec")
    print(f"usage error: {' '.join(argv)}\n\n{__doc__}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
