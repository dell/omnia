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

"""GitLab runner side of the SVT pipeline (standard library only).

Every job of the SVT project's .gitlab-ci-svt.yml is one call; the SVT itself
runs on the OIM over SSH, through the same scripts a user runs by hand. With
SVT_CLUSTER (multi-cluster projects) every variable <PREFIX>_<NAME> of that
cluster is used as <NAME> and the inputs come from clusters/<name>/svt/::

    svt_ci.py preflight          SSH to the OIM, OpenBao reachable
    svt_ci.py checkout           clone / update / keep the Omnia checkout, copy svt/ inputs
    svt_ci.py initialization     ./setup_env.sh --configure, --install --yes [--force]
                                 (cleanup first), --domain-creds-stdin (OpenBao JSON on
                                 stdin), then ./run_validation.sh svt_<theme> initialization
    svt_ci.py stage <stage>      ./run_validation.sh svt_<theme> <stage> --retry
    svt_ci.py summary            ./run_validation.sh svt_<theme> summary, the SVT report,
                                 the email; fails when any job or stage failed
    svt_ci.py after-job          (after_script) record the job status; stop a stage
                                 still running on the OIM when the job ended

A long stage runs detached on the OIM (setsid, its own log and exit code under
test/system_test/reports/ci/<pipeline id>/), and this job streams its log, so
a dropped SSH connection does not stop it.

Environment (CI/CD variables, see svt_pipeline_config.yml): SVT_TARGET_IP,
SVT_TARGET_USER, SVT_TARGET_PASS (masked) or SVT_SSH_KEY (file variable),
SVT_SSH_KNOWN_HOSTS (file variable; checks the OIM host key; required unless
SVT_SSH_SKIP_HOST_KEY=true),
SVT_OMNIA_REPO, SVT_OMNIA_BRANCH, SVT_OMNIA_INSTALL_PATH, SVT_CHECKOUT_MODE,
SVT_THEME, SVT_CLEAN_REINSTALL, SVT_POLL_SECONDS, SVT_JOB_ORDER,
SVT_CREDENTIAL_DOMAINS, SVT_LABEL, BAO_SERVER_URL, BAO_AUTH_ROLE,
BAO_DATA_PATH, BAO_CACERT (optional file variable: verify OpenBao with this CA;
BAO_TLS_SKIP_VERIFY=false: verify with the system CA store),
BAO_TLS_SKIP_VERIFY, VAULT_ID_TOKEN, EMAIL_RECIPIENTS, EMAIL_SENDER,
SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD. No secret is printed,
written to a file or passed as an argument.
"""

import glob
import gzip
import html
import json
import os
import re
import shlex
import smtplib
import ssl
import subprocess  # nosec B404  # fixed argument lists, no shell on the runner
import sys
import time
import urllib.request
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

STATE_DIR = "svt_ci"
STATUS_DIR = "pipeline_job_status"
REPORT_DIR = "svt_report"
RC_MARK = b"__SVT_CI_RC__="
# A larger HTML report is attached gzip-compressed (mail servers limit message size).
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
SSH_RETRIES = 20
SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SAFE_PATH = re.compile(r"^/[A-Za-z0-9._/-]+$")
SAFE_BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def apply_cluster() -> None:
    """Multi-cluster: make <PREFIX>_<NAME> of SVT_CLUSTER the value of <NAME>.

    Every cluster of the project has its own variables (CLUSTER1_SVT_TARGET_IP,
    CLUSTER1_SVT_TARGET_PASS, CLUSTER1_BAO_DATA_PATH ...); the child pipeline of
    a cluster only gets SVT_CLUSTER, so its secrets are never passed between
    pipelines. A cluster variable that is empty keeps the global value.
    """
    cluster = _env("SVT_CLUSTER")
    if not cluster:
        return
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", cluster):
        _fail(f"invalid SVT_CLUSTER {cluster!r}")
    head = re.sub(r"[^A-Z0-9]", "_", cluster.upper()) + "_"
    for key, value in list(os.environ.items()):
        if key.startswith(head) and value.strip():
            os.environ[key[len(head):]] = value
    os.environ.setdefault("SVT_LABEL", cluster)


def _inputs_dir() -> str:
    """Return the project folder of this cluster's SVT inputs."""
    cluster = _env("SVT_CLUSTER")
    return os.path.join("clusters", cluster, "svt") if cluster else "svt"


def _fail(message: str) -> None:
    print(f"ERROR: {message}", flush=True)
    sys.exit(1)


def _say(message: str) -> None:
    print(f"[svt-ci] {message}", flush=True)


def _theme() -> str:
    theme = _env("SVT_THEME", "build_stream")
    if not SAFE_NAME.fullmatch(theme):
        _fail(f"invalid SVT_THEME {theme!r}")
    return theme


def _install_path() -> str:
    path = _env("SVT_OMNIA_INSTALL_PATH").rstrip("/")
    if not SAFE_PATH.fullmatch(path) or ".." in path.split("/") or path.count("/") < 2:
        _fail(f"SVT_OMNIA_INSTALL_PATH must be an absolute path below /, got {path!r}")
    return path


def _svt_dir() -> str:
    return f"{_install_path()}/test/system_test"


def _ci_dir() -> str:
    pipeline = _env("CI_PIPELINE_ID", "local")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", pipeline):
        _fail("invalid CI_PIPELINE_ID")
    return f"{_svt_dir()}/reports/ci/{pipeline}"


# --------------------------------------------------------------------- ssh
_WARNED: set = set()


def _warn_once(message: str) -> None:
    if message not in _WARNED:
        _WARNED.add(message)
        print(f"WARNING: {message}", flush=True)


def _ssh_command() -> Tuple[List[str], Dict[str, str]]:
    """Return the ssh argument list and its environment (password via SSHPASS only)."""
    target = f"{_env('SVT_TARGET_USER', 'root')}@{_env('SVT_TARGET_IP')}"
    known_hosts = _env("SVT_SSH_KNOWN_HOSTS")
    if known_hosts:
        host_check = ["-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={known_hosts}"]
    elif _env("SVT_SSH_SKIP_HOST_KEY").lower() == "true":
        _warn_once("SVT_SSH_SKIP_HOST_KEY=true: the OIM host key is not checked, so the "
                   "connection can be intercepted (man in the middle) and the OIM password "
                   "and credentials captured. Set SVT_SSH_KNOWN_HOSTS instead.")
        host_check = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    else:
        _fail("SVT_SSH_KNOWN_HOSTS (a File variable with the OIM host key line) is required. "
              "HOW TO FIX: ./setup_svt_project.py --update --scan-host-keys stores it, or "
              "ssh-keyscan -t ed25519 <OIM> and add it by hand; SVT_SSH_SKIP_HOST_KEY=true "
              "accepts the risk of an unchecked host key")
        host_check = []
    options = [*host_check, "-o", "LogLevel=ERROR", "-o", "ServerAliveInterval=30",
               "-o", "ServerAliveCountMax=10", "-o", "ConnectTimeout=30"]
    env = dict(os.environ)
    key = _env("SVT_SSH_KEY")
    if key:
        return ["ssh", "-i", key, "-o", "BatchMode=yes", *options, target], env
    env["SSHPASS"] = os.environ.get("SVT_TARGET_PASS", "")
    return ["sshpass", "-e", "ssh", *options, target], env


def remote(command: str, stdin: Optional[bytes] = None, capture: bool = False,
           timeout: Optional[int] = None) -> Tuple[int, bytes]:
    """Run ``command`` on the OIM; stream (or capture) its output; return (rc, output)."""
    ssh, env = _ssh_command()
    kwargs: Dict[str, Any] = {"env": env, "timeout": timeout, "check": False,
                              "input": stdin if stdin is not None else b""}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
    try:
        # pylint: disable-next=subprocess-run-check  # check=False is in kwargs
        done = subprocess.run([*ssh, command], **kwargs)  # nosec B603  # list args, no shell
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"ssh failed: {type(exc).__name__}", flush=True)
        return 255, b""
    return done.returncode, done.stdout or b""


def run_detached(job: str, command: str) -> int:
    """Run ``command`` in test/system_test on the OIM in its own session; stream its log."""
    directory = _ci_dir()
    log, rc_file, pid_file = (f"{directory}/{job}.{ext}" for ext in ("log", "rc", "pid"))
    qlog, qrc, qpid = shlex.quote(log), shlex.quote(rc_file), shlex.quote(pid_file)
    inner = (f"{command} > {qlog} 2>&1 < /dev/null; echo $? > {qrc}.tmp; "
             f"mv {qrc}.tmp {qrc}")
    start = (f"mkdir -p {shlex.quote(directory)} && rm -f {qlog} {qrc} {qpid} && "
             f"cd {shlex.quote(_svt_dir())} && "
             f"(setsid bash -c {shlex.quote(inner)} > /dev/null 2>&1 & echo $! > {qpid})")
    _say(f"on the OIM: {command}")
    rc, _ = remote(start)
    if rc != 0:
        _fail(f"could not start {job} on the OIM (ssh rc={rc})")
    offset, failures, poll = 0, 0, max(5, int(_env("SVT_POLL_SECONDS", "30") or 30))
    probe = (f"tail -c +{{offset}} {shlex.quote(log)} 2>/dev/null; "
             f"printf '\\n{RC_MARK.decode()}%s\\n' \"$(cat {shlex.quote(rc_file)} 2>/dev/null)\"")
    while True:
        rc, out = remote(probe.format(offset=offset + 1), capture=True, timeout=600)
        index = out.rfind(b"\n" + RC_MARK)
        if rc != 0 or index < 0:
            failures += 1
            if failures >= SSH_RETRIES:
                _fail(f"lost the OIM for {failures} polls; {job} may still run there ({log})")
            time.sleep(poll)
            continue
        failures = 0
        chunk = out[:index]
        sys.stdout.buffer.write(chunk)
        sys.stdout.flush()
        offset += len(chunk)
        code = out[index + len(RC_MARK) + 1:].strip()
        if code:
            return int(code) if code.isdigit() else 1
        time.sleep(poll)


# ----------------------------------------------------------------- openbao
def _bao_context() -> ssl.SSLContext:
    """The TLS context for OpenBao, like test/pipeline (which uses curl -k): the certificate
    is not checked unless BAO_CACERT (an optional File variable) names a CA file, or
    BAO_TLS_SKIP_VERIFY=false asks for the system CA store."""
    cafile = _env("BAO_CACERT")
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    if _env("BAO_TLS_SKIP_VERIFY").lower() == "false":
        return ssl.create_default_context()
    print("WARNING: the OpenBao certificate is not verified (as in test/pipeline); give the "
          "File variable BAO_CACERT to verify it", flush=True)
    # pylint: disable-next=protected-access
    return ssl._create_unverified_context()  # nosec B323  # explicit opt-out only


def _bao_request(url: str, data: Optional[dict] = None,
                 token: str = "") -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    request = urllib.request.Request(  # nosec B310  # https URL from the CI configuration
        url, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    context = _bao_context()
    with urllib.request.urlopen(request, context=context, timeout=30) as response:  # nosec B310
        return json.load(response)


def bao_credentials() -> bytes:
    """Return {"<domain>": {field: value}} from OpenBao for the theme's credential stores."""
    server = _env("BAO_SERVER_URL").rstrip("/")
    domains = [d for d in _env("SVT_CREDENTIAL_DOMAINS").split(",") if d.strip()]
    if not server.startswith("https://") or not domains:
        return b""
    try:
        login = _bao_request(f"{server}/v1/auth/jwt/login",
                             {"jwt": os.environ.get("VAULT_ID_TOKEN", ""),
                              "role": _env("BAO_AUTH_ROLE", "gitlab-role")})
        token = login["auth"]["client_token"]
        payload = {}
        for domain in domains:
            domain = domain.strip()
            data = _bao_request(f"{server}/v1/{_env('BAO_DATA_PATH').strip('/')}/{domain}",
                                token=token).get("data", {})
            secret = data.get("data") if isinstance(data.get("data"), dict) else data
            payload[domain] = {key: str(value) for key, value in secret.items()
                               if key != "metadata"}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        _fail(f"OpenBao: could not read the credentials ({type(exc).__name__}); check "
              "BAO_SERVER_URL, BAO_AUTH_ROLE, BAO_DATA_PATH and the JWT role")
    _say(f"OpenBao: credentials read for {', '.join(payload)}")
    return json.dumps(payload).encode()


# -------------------------------------------------------------------- jobs
def preflight() -> int:
    """Check the CI variables, SSH to the OIM and OpenBao."""
    missing = [name for name in ("SVT_TARGET_IP", "SVT_OMNIA_INSTALL_PATH")
               if not _env(name)]
    if not (_env("SVT_SSH_KEY") or os.environ.get("SVT_TARGET_PASS")):
        missing.append("SVT_TARGET_PASS or SVT_SSH_KEY")
    if missing:
        _fail(f"missing CI/CD variables: {', '.join(missing)}")
    _install_path()
    _say(f"theme {_theme()}, OIM {_env('SVT_LABEL')}, checkout {_install_path()}")
    rc, out = remote("hostname -s && command -v git python3 >/dev/null && echo ready",
                     capture=True, timeout=120)
    if rc != 0 or b"ready" not in out:
        _fail("SSH to the OIM failed or git/python3 is missing there")
    _say(f"OIM reachable: {out.decode(errors='replace').split()[0]}")
    server = _env("BAO_SERVER_URL")
    if server:
        try:
            _bao_request(f"{server.rstrip('/')}/v1/sys/health")
        except (OSError, ValueError) as exc:
            _fail(f"OpenBao {server} is not reachable ({type(exc).__name__})")
        _say("OpenBao reachable")
    return 0


def _check_svt_scripts(svt_dir: str) -> None:
    """Fail now, with the reason, when the checkout has no usable SVT setup script.

    The jobs call ./setup_env.sh (configure, --install, --domain-creds-stdin) and
    ./run_validation.sh; a branch without the SVT, or with an older setup script, would
    otherwise fail later with a less clear error.
    """
    rc, out = remote(
        f"cd {svt_dir} && test -x setup_env.sh && test -x run_validation.sh && "
        "./setup_env.sh --help 2>&1 | grep -c -e '--configure' -e '--domain-creds-stdin'",
        capture=True, timeout=120)
    if rc != 0 or out.decode(errors="replace").strip() != "2":
        _fail("the checkout has no usable SVT: test/system_test/setup_env.sh (with "
              "--configure and --domain-creds-stdin) and run_validation.sh must exist and be "
              "executable. HOW TO FIX: use an Omnia branch that has the system test "
              "(clusters.<name>.omnia.branch), or checkout_mode: update")


def checkout() -> int:
    """Clone, update or keep the Omnia checkout; copy the svt/ inputs into it."""
    path, mode = _install_path(), _env("SVT_CHECKOUT_MODE", "update")
    repo, branch = _env("SVT_OMNIA_REPO"), _env("SVT_OMNIA_BRANCH")
    if mode not in ("update", "clone", "keep"):
        _fail(f"SVT_CHECKOUT_MODE must be update, clone or keep, got {mode!r}")
    if mode != "keep" and (not repo or not SAFE_BRANCH.fullmatch(branch)):
        _fail("SVT_OMNIA_REPO and a valid SVT_OMNIA_BRANCH are required")
    qpath, qrepo, qbranch = shlex.quote(path), shlex.quote(repo), shlex.quote(branch)
    clone = (f"mkdir -p {shlex.quote(os.path.dirname(path))} && "
             f"git clone -b {qbranch} {qrepo} {qpath}")
    script = {
        "clone": f"rm -rf -- {qpath} && {clone}",
        "update": (f"if [ -d {qpath}/.git ]; then cd {qpath} && git fetch origin {qbranch} && "
                   f"git checkout --force -B {qbranch} FETCH_HEAD; else {clone}; fi"),
        "keep": f"test -d {qpath}/.git",
    }[mode]
    _say(f"checkout ({mode}): {path} {branch}")
    rc, _ = remote(script)
    if rc != 0:
        _fail(f"checkout failed (rc={rc})")
    os.makedirs(STATE_DIR, exist_ok=True)
    _, commit = remote(f"git -C {qpath} rev-parse HEAD", capture=True)
    with open(os.path.join(STATE_DIR, "commit.txt"), "w", encoding="utf-8") as stream:
        stream.write(commit.decode(errors="replace").strip())
    _check_svt_scripts(shlex.quote(_svt_dir()))
    theme = _theme()
    for name in ("user_inputs.yml", f"{theme}_test_config.yml"):
        local = os.path.join(_inputs_dir(), name)
        if not os.path.isfile(local):
            _say(f"{local} not in the project: the checkout's own file is used")
            continue
        with open(local, "rb") as stream:
            content = stream.read()
        rc, _ = remote(f"cat > {shlex.quote(_svt_dir() + '/' + name)}", stdin=content)
        if rc != 0:
            _fail(f"could not copy {local} to the OIM")
        _say(f"{local} -> {_svt_dir()}/{name}")
    return 0


def _when(text: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _record_run() -> None:
    """Keep the run started by this pipeline (the summary reports only that run).

    A run started before this pipeline (configure failed) is not recorded.
    """
    rc, out = remote(f"cat {shlex.quote(_svt_dir() + '/reports/current_run.json')}",
                     capture=True)
    try:
        run = json.loads(out.decode(errors="replace")) if rc == 0 else {}
    except ValueError:
        run = {}
    started, created = _when(str(run.get("started_at", ""))), _when(_env("CI_PIPELINE_CREATED_AT"))
    if not run.get("run_id") or (started and created and started < created):
        _say("no new SVT run was started by ./setup_env.sh --configure")
        return
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "run.json"), "w", encoding="utf-8") as stream:
        json.dump(run, stream)
    _say(f"SVT run {run['run_id']} (report {run.get('report_path')})")


def initialization() -> int:
    """Clean reinstall, credentials, then the initialization stage of the theme.

    configure and install (with --force: cleanup first) run detached, so a
    dropped SSH connection does not stop them; only the short credential step
    runs attached, because the OpenBao JSON goes on its stdin.
    """
    theme = _theme()
    force = _env("SVT_CLEAN_REINSTALL", "true").lower() == "true"
    payload = bao_credentials()
    rc = run_detached("configure", f"./setup_env.sh --theme {theme} --configure")
    _record_run()
    if rc == 0:
        rc = run_detached("install", f"./setup_env.sh --theme {theme} --install --yes"
                          + (" --force" if force else ""))
    if rc == 0 and payload:
        _say("on the OIM: ./setup_env.sh --domain-creds-stdin (credentials from OpenBao "
             "on stdin)")
        rc, _ = remote(f"cd {shlex.quote(_svt_dir())} && ./setup_env.sh --theme {theme} "
                       "--domain-creds-stdin", stdin=payload)
    elif rc == 0:
        _say("BAO_SERVER_URL not set: the credential stores already on the OIM are used")
    if rc != 0:
        _say(f"./setup_env.sh failed (rc={rc}); the summary still reports the run")
        return rc
    return run_detached("initialization", f"./run_validation.sh svt_{theme} initialization")


def stage(name: str) -> int:
    """One theme stage of the SVT.

    --retry makes GitLab's Retry button on a failed stage job continue the same run: the
    stage runs again and its new attempt replaces the failed one in the report. On a first
    attempt it changes nothing.
    """
    if not SAFE_NAME.fullmatch(name):
        _fail(f"invalid stage {name!r}")
    return run_detached(name, f"./run_validation.sh svt_{_theme()} {name} --retry")


def after_job() -> int:
    """Record this job's status; stop its detached run on the OIM if it is still running."""
    job, status = _env("CI_JOB_NAME"), _env("CI_JOB_STATUS", "unknown")
    directory = os.path.join(STATUS_DIR, _env("CI_PIPELINE_ID", "local"))
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, f"{job}.json"), "w", encoding="utf-8") as stream:
        json.dump({"name": job, "status": status}, stream)
    if status != "success" and _env("SVT_TARGET_IP"):
        # Every detached run of this pipeline without an exit code is still running
        # (one job at a time: the pipeline holds the OIM's resource group).
        directory = shlex.quote(_ci_dir())
        remote(f"for pid in {directory}/*.pid; do [ -f \"$pid\" ] || continue; "
               f"[ -f \"${{pid%.pid}}.rc\" ] && continue; "
               f"kill -TERM -- -\"$(cat \"$pid\")\" 2>/dev/null && "
               f"echo \"stopped $(basename \"${{pid%.pid}}\") on the OIM\"; done; true",
               timeout=120)
    return 0


# ----------------------------------------------------------------- summary
def _job_statuses() -> Dict[str, str]:
    statuses = {}
    for path in glob.glob(os.path.join(STATUS_DIR, _env("CI_PIPELINE_ID", "local"), "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as stream:
                item = json.load(stream)
            statuses[item["name"]] = item.get("status", "unknown")
        except (OSError, ValueError, KeyError):
            continue
    return statuses


def _fetch_report() -> Dict[str, Any]:
    """Copy the SVT report of this pipeline's run into svt_report/; return its JSON."""
    try:
        with open(os.path.join(STATE_DIR, "run.json"), "r", encoding="utf-8") as stream:
            run = json.load(stream)
    except (OSError, ValueError):
        _say("no SVT run was started by this pipeline: no report")
        return {}
    os.makedirs(REPORT_DIR, exist_ok=True)
    data: Dict[str, Any] = {}
    for ext in ("html", "json"):
        source = f"{run['report_path']}/{run['report_name']}.{ext}"
        rc, content = remote(f"cat {shlex.quote(source)}", capture=True)
        if rc == 0 and content:
            with open(os.path.join(REPORT_DIR, f"{run['report_name']}.{ext}"), "wb") as stream:
                stream.write(content)
            if ext == "json":
                data = json.loads(content.decode(errors="replace") or "{}")
    _fetch_files(f"{run['report_path']}/junit_*.xml", os.path.join(REPORT_DIR, "junit"))
    _fetch_files(f"{_ci_dir()}/*.log", os.path.join(REPORT_DIR, "logs"))
    _fetch_files(f"{run['report_path']}/*.log", os.path.join(REPORT_DIR, "logs", "run"))
    _say(f"SVT report, JUnit files and logs of run {run.get('run_id')} -> {REPORT_DIR}/")
    return data


def _fetch_files(pattern: str, local_dir: str) -> None:
    """Copy the files matching ``pattern`` on the OIM (plain names only) into ``local_dir``."""
    directory, glob_part = pattern.rsplit("/", 1)
    rc, listing = remote(f"cd {shlex.quote(directory)} 2>/dev/null && ls -1 -- {glob_part} "
                         "2>/dev/null", capture=True)
    names = [name for name in listing.decode(errors="replace").split()
             if rc == 0 and re.fullmatch(r"[A-Za-z0-9._-]+", name)]
    for name in names:
        rc, content = remote(f"cat {shlex.quote(directory + '/' + name)}", capture=True)
        if rc == 0:
            os.makedirs(local_dir, exist_ok=True)
            with open(os.path.join(local_dir, name), "wb") as stream:
                stream.write(content)


def _section_rows(report: Dict[str, Any]) -> str:
    rows = ""
    for section in report.get("sections") or []:
        results = [r for item in section.get("items") or [] for r in item.get("results") or []]
        count = {s: sum(1 for r in results if r.get("status") == s)
                 for s in ("Passed", "Failed", "Skipped")}
        rows += (f"<tr><td>{html.escape(section.get('name', ''))}</td>"
                 f"<td>{_status_cell(section.get('status', ''))}</td>"
                 f"<td>{len(section.get('items') or [])}</td><td style='color:green'>"
                 f"{count['Passed']}</td><td style='color:red'>{count['Failed']}</td>"
                 f"<td style='color:orange'>{count['Skipped']}</td></tr>")
    return rows


def _status_cell(status: str) -> str:
    color = {"success": "#28a745", "passed": "#28a745", "failed": "#dc3545",
             "running": "#007bff"}.get(status.lower(), "#6c757d")
    return f"<b style='color:{color}'>{html.escape(status.upper() or 'NOT RUN')}</b>"


def _send_email(verdict: str, statuses: Dict[str, str], report: Dict[str, Any]) -> bool:
    """Send the summary email; return False only when it was configured and could not be sent."""
    recipients = [r.strip() for r in _env("EMAIL_RECIPIENTS").split(",") if r.strip()]
    server, sender = _env("SMTP_SERVER"), _env("EMAIL_SENDER")
    if not (recipients and server and sender):
        _say("email not configured (EMAIL_RECIPIENTS, EMAIL_SENDER, SMTP_SERVER): not sent")
        return True
    meta = report.get("meta") or {}
    title = meta.get("theme_title") or _theme()
    label = _env("SVT_LABEL")
    message = MIMEMultipart()
    message["From"], message["To"] = sender, ", ".join(recipients)
    message["Subject"] = f"Omnia SVT [{label}] {title} - {verdict}"
    jobs = "".join(f"<tr><td>{html.escape(job)}</td><td>{_status_cell(statuses.get(job, ''))}"
                   f"</td></tr>" for job in _env("SVT_JOB_ORDER").split(",") if job)
    commit = ""
    try:
        with open(os.path.join(STATE_DIR, "commit.txt"), "r", encoding="utf-8") as stream:
            commit = stream.read().strip()
    except OSError:
        pass
    style = "border-collapse:collapse;border:1px solid #ddd"
    url = html.escape(_env("CI_PIPELINE_URL"))
    body = (f"<html><body style='font-family:Arial,sans-serif'>"
            f"<h2>Omnia System Verification - {html.escape(title)}</h2>"
            f"<p><b>Status:</b> {_status_cell(verdict)} &nbsp; <b>OIM:</b> {html.escape(label)}"
            f" &nbsp; <b>Theme:</b> {html.escape(_theme())} &nbsp; <b>Run:</b> "
            f"{html.escape(str(meta.get('run_id', '')))}</p>"
            f"<p><b>Branch:</b> {html.escape(_env('SVT_OMNIA_BRANCH'))} &nbsp; <b>Commit:</b> "
            f"{html.escape(commit)}</p><p><b>Pipeline:</b> <a href='{url}'>{url}</a></p>"
            f"<h3>Pipeline Jobs</h3><table border='1' cellpadding='6' style='{style}'>"
            f"<tr><th>Job</th><th>Status</th></tr>{jobs}</table>"
            f"<h3>SVT Sections</h3><table border='1' cellpadding='6' style='{style}'>"
            f"<tr><th>Section</th><th>Status</th><th>Steps</th><th>Passed</th><th>Failed</th>"
            f"<th>Skipped</th></tr>{_section_rows(report)}</table>"
            f"<p>The SVT report is attached.</p></body></html>")
    message.attach(MIMEText(body, "html"))
    for path in glob.glob(os.path.join(REPORT_DIR, "*.html")):
        with open(path, "rb") as stream:
            content = stream.read()
        name = os.path.basename(path)
        if len(content) > MAX_ATTACHMENT_BYTES:
            part = MIMEApplication(gzip.compress(content), "gzip")
            name += ".gz"
        else:
            part = MIMEText(content.decode("utf-8", errors="replace"), "html", "utf-8")
        part.add_header("Content-Disposition", "attachment", filename=name)
        message.attach(part)
    port = int(_env("SMTP_PORT", "25") or 25)
    try:
        smtp_class = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
        with smtp_class(server, port, timeout=60) as smtp:
            if port == 587:
                smtp.starttls(context=ssl.create_default_context())
            if _env("SMTP_USER") and os.environ.get("SMTP_PASSWORD"):
                smtp.login(_env("SMTP_USER"), os.environ["SMTP_PASSWORD"])
            smtp.send_message(message)
        _say(f"email sent to {', '.join(recipients)}")
    except (OSError, smtplib.SMTPException) as exc:
        print("=" * 72 + f"\nERROR: the summary email was NOT sent to {', '.join(recipients)}: "
              f"{type(exc).__name__}: {exc}\nThe report is in the job artifacts "
              "(svt_report/).\n" + "=" * 72, flush=True)
        return False
    return True


def summary() -> int:
    """Run the SVT summary on the OIM, collect the report, email; fail on any failure."""
    statuses = _job_statuses()
    order = [job for job in _env("SVT_JOB_ORDER").split(",") if job and job != "summary"]
    problems = [f"{job} {statuses[job]}" for job in order
                if statuses.get(job) in ("failed", "canceled")]
    rc = 1
    if _env("SVT_TARGET_IP") and os.path.isfile(os.path.join(STATE_DIR, "run.json")):
        rc, _ = remote(f"cd {shlex.quote(_svt_dir())} && "
                       f"./run_validation.sh svt_{_theme()} summary")
    if rc != 0:
        problems.append(f"SVT summary rc={rc}")
    report = _fetch_report()
    verdict = "FAILED" if problems else "PASSED"
    statuses["summary"] = "failed" if problems else "success"
    _say(f"overall: {verdict}" + (f" ({'; '.join(problems)})" if problems else ""))
    sent = _send_email(verdict, statuses, report)
    if not sent and _env("SVT_EMAIL_REQUIRED").lower() == "true":
        _say("SVT_EMAIL_REQUIRED=true: the summary job fails because the email was not sent")
        return 1
    return 1 if problems else 0


def main(argv: List[str]) -> int:
    """Dispatch one job."""
    apply_cluster()
    jobs = {"preflight": preflight, "checkout": checkout, "initialization": initialization,
            "summary": summary, "after-job": after_job}
    if len(argv) == 2 and argv[0] == "stage":
        return stage(argv[1])
    if len(argv) == 1 and argv[0] in jobs:
        return jobs[argv[0]]()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
