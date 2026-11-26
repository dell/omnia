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
    stage <domain> <tag>  fvt_<domain> <tag> exec

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
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Deque, Dict, List, Optional, Sequence, Tuple

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
REPORTS_DEFAULT = "/automation"
REPORTS_KEEP_DAYS = 30
REPORT_NAME = "omnia_fvt_pipeline_report"
TEST_MODULES = ("main", "repo_manager", "image_build_manager", "discovery", "orchestrator",
                "telemetry", "utils", "build_stream")
DOMAIN_STEPS = {
    "repo_manager": ("precheck", "prepare", "execute", "status"),
    "image_build_manager": ("validate", "prepare", "build"),
    "discovery": ("precheck", "validate", "execute"),
    "orchestrator": ("precheck", "prepare", "provision", "pxeboot"),
    "telemetry": ("precheck", "validate", "deploy"),
    "build_stream": ("",),
    "utils": ("collect", "backup_oim_logs"),
}
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
MAX_LOG_BYTES = 3000000
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
    return rc


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
    if blocked and _env("DRY_RUN").lower() != "true":
        _say(f"ERROR: {', '.join(blocked)} failed, so the Omnia cleanup was not run and the Omnia "
             "venv is kept for the next try (the orchestrator ones empty the NFS shares)")
        _record_error(f"{', '.join(blocked)} failed, so the Omnia cleanup was not run")
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
    if not server.startswith("https://") and not server.startswith("http://"):
        _say("ERROR: BAO_SERVER_URL is not set. HOW TO FIX: set the BAO_* CI/CD variables")
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


def main(argv: List[str]) -> int:
    one = {"cleanup": cleanup, "cleanup-verify": cleanup_verify}
    none = {"initialize": initialize, "init": init, "checkout": checkout,
            "nfs-check": nfs_preflight, "cleanup-omnia": cleanup_omnia,
            "cleanup-omnia-verify": cleanup_omnia_verify}
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
