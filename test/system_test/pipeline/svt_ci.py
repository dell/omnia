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

Every job of the SVT project's .gitlab-ci-svt-<theme>.yml is one call; the SVT itself
runs on the OIM over SSH, through the same scripts a user runs by hand. With
SVT_CLUSTER (multi-cluster projects) every variable <PREFIX>_<NAME> of that
cluster is used as <NAME> and the inputs come from clusters/<name>/svt/::

    svt_ci.py preflight          SSH to the OIM, OpenBao reachable, then the checkout below
    svt_ci.py checkout           clone / update / recreate / keep the Omnia checkout, copy the
                                 svt/ inputs of every theme of the run
    svt_ci.py initialization     the shared clean start, once, for the first theme:
                                 ./setup_env.sh --configure, --install --yes [--force] (cleanup
                                 first, then omnia.sh -s), --domain-creds-stdin (OpenBao JSON on
                                 stdin), ./setup_env.sh --stage-files (PowerScale CSI files,
                                 only when enabled), then ./run_validation.sh svt_<theme>
                                 initialization (readiness)
    svt_ci.py stage <stage>      ./run_validation.sh svt_<theme> <stage> --retry. The first
                                 stage job of a theme after the first one starts that theme's
                                 run first (--configure, --install --yes: no cleanup)
    svt_ci.py theme-result       the theme's SVT summary and verdict, kept for the summary
    svt_ci.py summary            every theme's result, ONE report (svt_report/svt_report.html:
                                 an overview and one page per theme) and one email; fails
                                 when any job or stage failed
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
SVT_THEME, SVT_USER_INPUTS (name of the cluster's inputs file in clusters/<name>/svt/,
default user_inputs.yml), SVT_CLEAN_REINSTALL (empty: SVT_INIT_DEFAULT_CLEAN_REINSTALL_<THEME>, the
default of the first theme of the run, from the cluster pipeline), SVT_POLL_SECONDS, SVT_JOB_ORDER,
SVT_CATALOG_PLAN (catalog themes), SVT_CREDENTIAL_DOMAINS, SVT_LABEL,
BAO_SERVER_URL, BAO_AUTH_ROLE,
BAO_DATA_PATH, BAO_CACERT (optional file variable: verify OpenBao with this CA;
BAO_TLS_SKIP_VERIFY=false: verify with the system CA store),
BAO_TLS_SKIP_VERIFY, VAULT_ID_TOKEN, EMAIL_RECIPIENTS, EMAIL_SENDER,
SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD. No secret is printed,
written to a file or passed as an argument.
"""

import functools
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
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

import svt_report_page

STATE_DIR = "svt_ci"
STATUS_DIR = "pipeline_job_status"
REPORT_DIR = "svt_report"
RC_MARK = b"__SVT_CI_RC__="
# A larger HTML report is attached gzip-compressed (mail servers limit message size).
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
SSH_RETRIES = 20
SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SAFE_PATH = re.compile(r"^/[A-Za-z0-9._/-]+$")
TABLE_STYLE = "border-collapse:collapse;width:100%"
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


USER_INPUTS = "user_inputs.yml"
# PowerScale CSI files of a cluster: clusters/<name>/svt/secret.yaml and values.yaml in the
# project, copied next to user_inputs.yml. ./setup_env.sh --stage-files then
# moves them to the paths of omnia_config.yml, but only when enable_powerscale_csi is true.
POWERSCALE_FILES = ("secret.yaml", "values.yaml")
USER_INPUTS_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\.ya?ml")


def _inputs_name() -> str:
    """Return the file of the project folder that holds this cluster's inputs.

    SVT_USER_INPUTS (the cluster's variable <PREFIX>_SVT_USER_INPUTS) names it; empty means
    user_inputs.yml. It is a file name, never a path, so it cannot leave the folder.
    """
    name = _env("SVT_USER_INPUTS") or USER_INPUTS
    if not USER_INPUTS_NAME.fullmatch(name) or ".." in name:
        _fail(f"SVT_USER_INPUTS must be the name of a .yml/.yaml file (letters, digits, _ . -), "
              f"no folder, got {name!r}")
    return name


def _inputs_dir() -> str:
    """Return the project folder of this cluster's SVT inputs."""
    cluster = _env("SVT_CLUSTER")
    return os.path.join("clusters", cluster, "svt") if cluster else "svt"


def _fail(message: str) -> None:
    print(f"ERROR: {message}", flush=True)
    job = re.sub(r"[^A-Za-z0-9_.-]", "_", os.environ.get("CI_JOB_NAME", ""))
    if job:
        try:
            os.makedirs(os.path.join(STATE_DIR, "errors"), exist_ok=True)
            with open(os.path.join(STATE_DIR, "errors", f"{job}.txt"), "w",
                      encoding="utf-8") as stream:
                stream.write(message)
        except OSError:
            pass
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


class LogFilter:
    """Keep a job's log under the runner's size limit (GitLab Runner stops collecting a job log
    at 4096 KB; the SVT streams whole playbook logs).

    * a line that is only base64 (an Ansible task dumping a slurped file) is hidden, counted;
    * a line longer than MAX_LINE characters is cut, with the number of characters left out;
    * after the budget (SVT_LOG_LIMIT_KB, default 2500, shared by every log of the job; the
      runner adds a timestamp to each line, about 30 % more) the rest is not printed: the
      full log stays on the OIM, and the last lines are shown when the job ends.
    """

    remaining: Optional[int] = None

    MAX_LINE = 600
    BASE64 = re.compile(rb"^[\s\xe2\x94\x82]*[A-Za-z0-9+/=]{80,}\s*$")

    def __init__(self, budgeted: bool = True) -> None:
        if LogFilter.remaining is None:
            LogFilter.remaining = max(256, int(_env("SVT_LOG_LIMIT_KB", "2500") or 2500)) * 1024
        self.budgeted = budgeted
        self.carry, self.hidden, self.clipped = b"", 0, 0
        self.muted = budgeted and LogFilter.remaining <= 0

    def _line(self, line: bytes) -> Optional[bytes]:
        if self.BASE64.match(line):
            self.hidden += 1
            return None
        if len(line) > self.MAX_LINE:
            self.clipped += 1
            return (line[:self.MAX_LINE]
                    + f" ...[{len(line) - self.MAX_LINE} more characters]".encode())
        return line

    def feed(self, chunk: bytes, final: bool = False) -> bytes:
        """Return what to print for ``chunk`` (a partial last line is kept for the next call)."""
        lines = (self.carry + chunk).split(b"\n")
        self.carry = b"" if final else lines.pop()
        kept = [line for line in map(self._line, lines) if line is not None]
        out = b"".join(line + b"\n" for line in kept)
        if self.muted:
            return b""
        if not self.budgeted:
            return out
        if len(out) > LogFilter.remaining:
            self.muted = True
            cut, LogFilter.remaining = out[:LogFilter.remaining], 0
            return cut + (
                b"\n[svt-ci] log limit reached (SVT_LOG_LIMIT_KB): the rest is not printed here; "
                b"the full log is on the OIM, the last lines follow when the job ends\n")
        LogFilter.remaining -= len(out)
        return out

    def summary(self) -> str:
        """Return what was left out ("" when nothing)."""
        parts = [f"{self.hidden} base64 lines hidden" if self.hidden else "",
                 f"{self.clipped} long lines cut" if self.clipped else "",
                 "output after the log limit not printed" if self.muted else ""]
        return ", ".join(part for part in parts if part)


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
    logfilter = LogFilter()
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
        code = out[index + len(RC_MARK) + 1:].strip()
        sys.stdout.buffer.write(logfilter.feed(chunk, final=bool(code)))
        sys.stdout.flush()
        offset += len(chunk)
        if code:
            left_out = logfilter.summary()
            if left_out:
                _say(f"{job}: {left_out}; the full log is on the OIM: {log}")
            if logfilter.muted:
                _, tail = remote(f"tail -n 40 {shlex.quote(log)}", capture=True, timeout=120)
                sys.stdout.buffer.write(LogFilter(budgeted=False).feed(tail, final=True))
                sys.stdout.flush()
            return int(code) if code.isdigit() else 1
        time.sleep(poll)


# ----------------------------------------------------------------- openbao
@functools.lru_cache(maxsize=None)
def _bao_context() -> ssl.SSLContext:
    """The TLS context for OpenBao (built once): the certificate is checked with BAO_CACERT
    (an optional File variable) or, when BAO_TLS_SKIP_VERIFY=false, with the system CA store;
    otherwise it is not checked (a self-signed OpenBao), with one warning."""
    cafile = _env("BAO_CACERT")
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    if _env("BAO_TLS_SKIP_VERIFY").lower() == "false":
        return ssl.create_default_context()
    print("WARNING: the OpenBao TLS certificate is not verified (BAO_TLS_SKIP_VERIFY is not "
          "false); set the File variable BAO_CACERT to verify it", flush=True)
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
    except urllib.error.HTTPError as exc:
        try:
            reason = "; ".join(json.load(exc).get("errors", []))
        except (OSError, ValueError, AttributeError):
            reason = ""
        _fail(f"OpenBao: could not read the credentials: HTTP {exc.code} for "
              f"{exc.url.replace(server, '')} ({reason or 'no detail'}); check "
              "BAO_SERVER_URL, BAO_AUTH_ROLE, BAO_DATA_PATH and the JWT role")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        _fail(f"OpenBao: could not read the credentials ({type(exc).__name__}); check "
              "BAO_SERVER_URL, BAO_AUTH_ROLE, BAO_DATA_PATH and the JWT role")
    _say(f"OpenBao: credentials read for {', '.join(payload)}")
    return json.dumps(payload).encode()


# -------------------------------------------------------------------- jobs
def preflight() -> int:
    """The preflight job: the checks, then the Omnia checkout (one stage, one SSH session less)."""
    return _checks() or checkout()


def _check_theme_inputs() -> None:
    """Fail before anything is cleaned when a theme file of the project has its own cleanup.

    The cleanup is one block of the cluster's user inputs file, shared by every theme.
    """
    own = []
    for theme in _themes():
        path = os.path.join(_inputs_dir(), f"{theme}_test_config.yml")
        try:
            with open(path, "r", encoding="utf-8") as stream:
                if re.search(r"^cleanup\s*:", stream.read(), re.MULTILINE):
                    own.append(path)
        except OSError:
            continue
    if own:
        _fail(f"{', '.join(own)} has its own cleanup block. HOW TO FIX: the cleanup is one "
              f"block at the bottom of {_inputs_name()}, shared by every theme; move the "
              "settings there and delete the block from the theme file")


def _checks() -> int:
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
    _check_theme_inputs()
    return 0


def _check_svt_scripts(svt_dir: str) -> None:
    """Fail now, with the reason, when the checkout has no usable SVT setup script.

    The jobs call ./setup_env.sh (configure, --install, --domain-creds-stdin) and
    ./run_validation.sh; a branch without the SVT, or with an older setup script, would
    otherwise fail later with a less clear error.
    """
    rc, _ = remote(
        f"cd {svt_dir} && test -x setup_env.sh && test -x run_validation.sh && "
        "h=$(./setup_env.sh --help 2>&1) && "
        "printf '%s' \"$h\" | grep -q -e '--configure' && "
        "printf '%s' \"$h\" | grep -q -e '--domain-creds-stdin'",
        capture=True, timeout=120)
    if rc != 0:
        _fail("the checkout has no usable SVT: test/system_test/setup_env.sh (with "
              "--configure and --domain-creds-stdin) and run_validation.sh must exist and be "
              "executable. HOW TO FIX: use an Omnia branch that has the system test "
              "(clusters.<name>.omnia.branch), or checkout_mode: update")


CHECKOUT_MODES = ("update", "recreate", "keep")
# Folders a checkout is never deleted from (recreate), nor anything below them.
PROTECTED_PATHS = ("/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/lib64", "/media",
                   "/mnt", "/opt", "/opt/omnia", "/proc", "/root", "/run", "/sbin", "/srv",
                   "/sys",
                   "/tmp",  # nosec B108  # a deny list of folders never deleted, not a temp file
                   "/usr", "/var")
PROTECTED_TREES = ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib64", "/opt/omnia", "/proc",
                   "/run", "/sbin", "/sys", "/usr", "/var")

# recreate, on the OIM: stop what still runs from the folder (a step of an earlier run keeps
# writing into it and makes the delete fail with "Directory not empty"), delete it (a few
# tries), and show what is left when it cannot be deleted. $1 is the folder.
RECREATE_DELETE = r"""d="$1"
holders() { for p in /proc/[0-9]*; do pid=${p#/proc/}; [ "$pid" = "$$" ] && continue
  cwd=$(readlink "$p/cwd" 2>/dev/null); case "$cwd" in "$d"|"$d"/*) echo "$pid";; esac; done; }
pids=$(holders)
if [ -n "$pids" ]; then echo "stopping what still runs in $d: $(echo $pids)"
  kill -TERM $pids 2>/dev/null; sleep 3; kill -KILL $(holders) 2>/dev/null; sleep 1; fi
for try in 1 2 3 4 5; do rm -rf -- "$d" 2>/dev/null; [ -e "$d" ] || exit 0; sleep 2; done
echo "ERROR: $d could not be deleted. Still running there: $(echo $(holders))"
grep -F " $d" /proc/mounts && echo "(a mount inside the folder: unmount it)"
find "$d" -maxdepth 3 2>/dev/null | head -20; exit 1"""


def _deletable(path: str) -> bool:
    """Return whether ``path`` may be deleted by checkout_mode recreate."""
    return path not in PROTECTED_PATHS and not any(
        path == tree or path.startswith(tree + "/") for tree in PROTECTED_TREES)


def checkout() -> int:
    """Update, recreate or keep the Omnia checkout; copy the svt/ inputs into it."""
    path, mode = _install_path(), _env("SVT_CHECKOUT_MODE", "update")
    chosen = _inputs_name()
    if chosen != USER_INPUTS and not os.path.isfile(os.path.join(_inputs_dir(), chosen)):
        _fail(f"{os.path.join(_inputs_dir(), chosen)} is not in the project: SVT_USER_INPUTS names "
              f"it; add the file or clear the variable to use {USER_INPUTS}")
    repo, branch = _env("SVT_OMNIA_REPO"), _env("SVT_OMNIA_BRANCH")
    if mode not in CHECKOUT_MODES:
        _fail(f"SVT_CHECKOUT_MODE must be {', '.join(CHECKOUT_MODES)}, got {mode!r}")
    if mode == "recreate" and not _deletable(path):
        _fail(f"checkout_mode recreate deletes the folder: {path} is a system folder, use a "
              "folder of its own (clusters.<name>.omnia.install_path)")
    if mode != "keep" and (not repo or not SAFE_BRANCH.fullmatch(branch)):
        _fail("SVT_OMNIA_REPO and a valid SVT_OMNIA_BRANCH are required")
    qpath, qrepo, qbranch = shlex.quote(path), shlex.quote(repo), shlex.quote(branch)
    clone = (f"mkdir -p {shlex.quote(os.path.dirname(path))} && "
             f"git clone -b {qbranch} {qrepo} {qpath}")
    script = {
        "recreate": f"bash -c {shlex.quote(RECREATE_DELETE)} _ {qpath} && {clone}",
        "update": (f"if [ -d {qpath}/.git ]; then cd {qpath} && "
                   f"git remote set-url origin {qrepo} && git fetch origin {qbranch} && "
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
    names = _themes() if _env("SVT_THEME_ORDER") else [_theme()]
    for source, name in ((chosen, USER_INPUTS), *((f"{t}_test_config.yml",) * 2 for t in names)):
        local = os.path.join(_inputs_dir(), source)
        if not os.path.isfile(local):
            _say(f"{local} not in the project: the checkout's own file is used")
            continue
        with open(local, "rb") as stream:
            content = stream.read()
        rc, _ = remote(f"cat > {shlex.quote(_svt_dir() + '/' + name)}", stdin=content)
        if rc != 0:
            _fail(f"could not copy {local} to the OIM")
        _say(f"{local} -> {_svt_dir()}/{name}")
    _copy_powerscale_files()
    return 0


def _copy_powerscale_files() -> None:
    """Make the PowerScale files on the OIM the ones of the project (plaintext, mode 0600,
    content on stdin only); a file that is not in the project is removed there.

    Whether they are used is decided on the OIM by ./setup_env.sh --stage-files (only when
    enable_powerscale_csi is true, then both must exist). They are copied again on every run:
    the orchestrator encrypts its copy in place with a key a clean reinstall deletes.
    """
    for name in POWERSCALE_FILES:
        local = os.path.join(_inputs_dir(), name)
        target = shlex.quote(f"{_svt_dir()}/{name}")
        if not os.path.isfile(local):
            remote(f"rm -f {target}")
            continue
        with open(local, "rb") as stream:
            content = stream.read()
        rc, _ = remote(f"umask 077 && cat > {target}", stdin=content)
        if rc != 0:
            _fail(f"could not copy {local} to the OIM")
        _say(f"{local} -> {_svt_dir()}/{name}")


def _when(text: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _since() -> str:
    """Return the time this theme's run must not be older than: the start of the cluster pipeline
    for the first theme (its run is started by the initialization job), else of this pipeline."""
    if int(_env("SVT_THEME_INDEX", "0") or 0) == 0 and _env("SVT_CLUSTER_PIPELINE_CREATED_AT"):
        return _env("SVT_CLUSTER_PIPELINE_CREATED_AT")
    return _env("CI_PIPELINE_CREATED_AT")


def _current_run() -> Dict[str, Any]:
    """Return the run the OIM is on (reports/current_run.json), {} when there is none."""
    return _read_json(f"{_svt_dir()}/reports/current_run.json")


def _run_since(run: Dict[str, Any], since: str) -> bool:
    """Return whether ``run`` has an id and started at or after ``since``."""
    started, created = _when(str(run.get("started_at", ""))), _when(since)
    return bool(run.get("run_id")) and not (started and created and started < created)


def _record_run() -> None:
    """Keep the run this theme uses (the summary reports only that run).

    A run started before the pipeline began (configure failed) is not recorded.
    """
    run = _current_run()
    if not _run_since(run, _since()):
        _say("no new SVT run was started by ./setup_env.sh --configure")
        return
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "run.json"), "w", encoding="utf-8") as stream:
        json.dump(run, stream)
    _say(f"SVT run {run['run_id']} (report {run.get('report_path')})")


def _check_catalog_plan(theme: str) -> None:
    """Catalog themes: the plan --configure wrote on the OIM must be the rendered jobs.

    setup_svt_project.py renders one job per catalog (SVT_CATALOG_PLAN, or
    SVT_CATALOG_PLAN_<THEME> in the cluster pipeline, <stage>=<catalog>); a catalog list edited in the project, or a branch with
    other bundled catalogs, gives another plan, whose catalogs would have no job.
    """
    expected = _env(f"SVT_CATALOG_PLAN_{theme.upper()}") or _env("SVT_CATALOG_PLAN")
    if not expected:
        return
    path = _svt_dir() + "/reports/catalog_build_plan.json"
    rc, out = remote(f"cat {shlex.quote(path)}", capture=True)
    entries: List[Dict[str, Any]] = []
    if rc == 0:
        try:
            entries = json.loads(out.decode(errors="replace")).get("entries") or []
        except (ValueError, AttributeError):
            entries = []
    actual = ",".join(f"{entry.get('stage')}={entry.get('catalog')}" for entry in entries)
    if actual != expected:
        _fail("the catalog plan of this run on the OIM differs from the pipeline jobs:\n"
              f"  pipeline: {expected.replace(',', ', ')}\n"
              f"  OIM:      {actual.replace(',', ', ') or '(no plan: ' + path + ')'}\n"
              "Run ./setup_svt_project.py --update (with --update-inputs when the catalog "
              "list changed in this checkout) so the jobs match the catalog list.")
    _say(f"catalog plan matches the pipeline jobs ({len(entries)} catalog(s))")


def _readiness_skipped(theme: str) -> bool:
    """Whether the initialization stage (readiness checks) is left out: the default of ``theme``
    (the first theme of the run), or SVT_SKIP_STAGES (empty = the default, "none" = every stage
    runs)."""
    raw = _env("SVT_SKIP_STAGES")
    names = [name.strip() for name in
             (raw or _env(f"SVT_INIT_DEFAULT_SKIP_STAGES_{theme.upper()}")).split(",")]
    return "initialization" in names


def _themes() -> List[str]:
    """Return the themes of this run in order: SVT_THEME_ORDER (rendered from the config),
    narrowed by the cluster's variable SVT_THEMES when it is set, without the themes left out
    with ``theme_<name>`` in SVT_SKIP_STAGES (their trigger job does not run)."""
    order = [item for item in _env("SVT_THEME_ORDER").split(",") if item]
    chosen = [item.strip() for item in _env("SVT_THEMES").split(",") if item.strip()]
    skipped = {item.strip() for item in _env("SVT_SKIP_STAGES").split(",")}
    themes = [item for item in order
              if (not chosen or item in chosen) and f"theme_{item}" not in skipped]
    for theme in themes:
        if not SAFE_NAME.fullmatch(theme):
            _fail(f"invalid theme {theme!r}")
    return themes


def _group_dir() -> str:
    """Return the OIM folder of this cluster pipeline's theme results."""
    pipeline = _env("SVT_CLUSTER_PIPELINE_ID") or _env("CI_PIPELINE_ID", "local")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", pipeline):
        _fail("invalid pipeline id")
    return f"{_svt_dir()}/reports/ci/{pipeline}"


def _credentials_and_files(theme: str, payload: bytes) -> int:
    """Store the OpenBao credentials on the OIM and stage the PowerScale CSI files."""
    rc = 0
    if payload:
        _say("on the OIM: ./setup_env.sh --domain-creds-stdin (credentials from OpenBao "
             "on stdin)")
        rc, _ = remote(f"cd {shlex.quote(_svt_dir())} && ./setup_env.sh --theme {theme} "
                       "--domain-creds-stdin", stdin=payload)
    else:
        _say("BAO_SERVER_URL not set: the credential stores already on the OIM are used")
    if rc == 0:
        _say("on the OIM: ./setup_env.sh --stage-files (PowerScale CSI files, only when enabled)")
        rc, _ = remote(f"cd {shlex.quote(_svt_dir())} && ./setup_env.sh --theme {theme} "
                       "--stage-files")
    return rc


def _clean_install_themes() -> List[str]:
    """Return the themes that start from scratch (SVT_CLEAN_INSTALL_THEMES, rendered)."""
    return [item for item in _env("SVT_CLEAN_INSTALL_THEMES").split(",") if item]


def initialization() -> int:
    """The initialization shared by the themes that do not start from scratch, once.

    It runs with the first of those themes (build_stream does its own clean_install job), so a
    run of build_stream alone has nothing to do here.
    """
    themes = _themes()
    if not themes:
        _fail("no theme selected: clusters.<name>.themes and <CLUSTER>_SVT_THEMES are empty")
    shared = [theme for theme in themes if theme not in _clean_install_themes()]
    if not shared:
        _say(f"themes of this run: {', '.join(themes)}; each starts from scratch in its own "
             "clean_install job, nothing to initialize here")
        return 0
    return _initialize(shared[0], themes)


def clean_install() -> int:
    """First job of a theme that starts from scratch (build_stream): the same complete
    initialization again, for this theme alone: the shared cleanup, omnia.sh -s, the Omnia
    environment, the credentials, the CSI files and the readiness stage."""
    theme = _theme()
    return _initialize(theme, [theme])


def _initialize(first: str, themes: List[str]) -> int:
    """The complete initialization with theme ``first``.

    configure (the first theme's run), then the clean reinstall (``--install --force``: the shared
    cleanup of user_inputs.yml, then omnia.sh -s and the Omnia environment), the credentials from
    OpenBao, the PowerScale CSI files and the readiness stage. The first theme then goes straight
    to its first stage; a later theme starts its own run on this installation without a cleanup.
    SVT_CLEAN_REINSTALL=false installs only what changed (no cleanup). configure and install run
    detached, so a dropped SSH connection does not stop them; only the short credential step
    runs attached, because the OpenBao JSON goes on its stdin.
    """
    reinstall = (_env("SVT_CLEAN_REINSTALL")
                 or _env(f"SVT_INIT_DEFAULT_CLEAN_REINSTALL_{first.upper()}", "true"))
    force = reinstall.lower() == "true"
    _say(f"themes of this run: {', '.join(themes)}; initialization with theme {first}"
         + ("" if force else " (SVT_CLEAN_REINSTALL=false: no cleanup)"))
    payload = bao_credentials()
    rc = run_detached("configure", f"./setup_env.sh --theme {first} --configure")
    _record_run()
    if rc == 0:
        _check_catalog_plan(first)
        rc = run_detached("install", f"./setup_env.sh --theme {first} --install --yes"
                          + (" --force" if force else ""))
    if rc == 0:
        rc = _credentials_and_files(first, payload)
    if rc != 0:
        _say(f"./setup_env.sh failed (rc={rc}); the summary still reports the run")
        return rc
    if _readiness_skipped(first):
        _say("initialization stage left out (theme default or SVT_SKIP_STAGES); setup is done")
        return 0
    return run_detached("initialization", f"./run_validation.sh svt_{first} initialization")


def _start_theme_run() -> int:
    """Make sure this theme's run exists before its first stage; return 0 or a failure code.

    The first theme's run was started by the initialization job (nothing to do but record it).
    A later theme starts its own run on the installation the initialization made: configure and
    install without --force (no cleanup, only what the theme's inputs changed). The credential
    stores and the installation are kept by a new run. It is idempotent: when the OIM is already
    on a run of this theme newer than this pipeline (an earlier job, or a retry of the first
    stage), that run is used, so a retry continues the same run.
    """
    theme = _theme()
    run = _current_run()
    if run.get("theme") == theme and _run_since(run, _since()):
        _record_run()
        return 0
    if int(_env("SVT_THEME_INDEX", "0") or 0) == 0 or theme in _clean_install_themes():
        job = "clean_install" if theme in _clean_install_themes() else "initialization"
        _fail(f"the SVT run of theme {theme} was not started by the {job} job. HOW "
              f"TO FIX: open the {job} job and run it again")
    _say(f"theme {theme}: its own run on the installation of the initialization (no cleanup)")
    rc = run_detached("configure", f"./setup_env.sh --theme {theme} --configure")
    _record_run()
    if rc == 0:
        _check_catalog_plan(theme)
        rc = run_detached("install", f"./setup_env.sh --theme {theme} --install --yes")
    if rc == 0:
        _say("on the OIM: ./setup_env.sh --stage-files (PowerScale CSI files, only when enabled)")
        rc, _ = remote(f"cd {shlex.quote(_svt_dir())} && ./setup_env.sh --theme {theme} "
                       "--stage-files")
    if rc != 0:
        _say(f"the run of theme {theme} could not be started (rc={rc})")
    return rc


def _read_json(path: str) -> Dict[str, Any]:
    """Return the JSON file ``path`` of the OIM ({} when it is missing or invalid)."""
    rc, out = remote(f"cat {shlex.quote(path)}", capture=True)
    try:
        data = json.loads(out.decode(errors="replace")) if rc == 0 else {}
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def theme_result() -> int:
    """Run the theme's SVT summary on the OIM and keep the theme's verdict for the cluster summary.

    The record (verdict, problems, job statuses, run, links) is written on the OIM in the
    folder of the cluster pipeline; this job never fails, so the cluster summary decides.
    """
    theme = _theme()
    statuses = _job_statuses()
    order = [job for job in _env("SVT_JOB_ORDER").split(",") if job and job != "theme_result"]
    problems = [f"{job} {statuses[job]}" for job in order
                if statuses.get(job) in ("failed", "canceled")]
    run: Dict[str, Any] = {}
    try:
        with open(os.path.join(STATE_DIR, "run.json"), "r", encoding="utf-8") as stream:
            run = json.load(stream)
    except (OSError, ValueError):
        problems.append("no SVT run was started")
    report: Dict[str, Any] = {}
    if run and _env("SVT_TARGET_IP"):
        rc, _ = remote(f"cd {shlex.quote(_svt_dir())} && ./run_validation.sh svt_{theme} summary")
        if rc != 0:
            problems.append(f"SVT summary rc={rc}")
        report = _read_json(f"{run['report_path']}/{run['report_name']}.json")
        problems += [f"{section.get('stage')} failed in the SVT report"
                     for section in report.get("sections") or []
                     if section.get("status") == "Failed" and section.get("stage")
                     and not any(item.startswith(f"{section['stage']} ") for item in problems)]
    record = {"theme": theme, "verdict": "FAILED" if problems else "PASSED", "problems": problems,
              "statuses": statuses, "order": order, "run": run, "ci_dir": _ci_dir(),
              "pipeline_url": _env("CI_PIPELINE_URL"), "index": _env("SVT_THEME_INDEX", "0")}
    group = _group_dir()
    rc, _ = remote(f"mkdir -p {shlex.quote(group)} && cat > "
                   f"{shlex.quote(group + '/theme_' + theme + '.json')}",
                   stdin=json.dumps(record).encode())
    _say(f"theme {theme}: {record['verdict']}" + (f" ({'; '.join(problems)})" if problems else "")
         + ("" if rc == 0 else " - the result could not be written on the OIM"))
    return 0


def stage(name: str) -> int:
    """One theme stage of the SVT (the theme's run is started first when it is not yet).

    --retry makes GitLab's Retry button on a failed stage job continue the same run: the
    stage runs again and its new attempt replaces the failed one in the report. On a first
    attempt it changes nothing.
    """
    if not SAFE_NAME.fullmatch(name):
        _fail(f"invalid stage {name!r}")
    rc = _start_theme_run()
    if rc != 0:
        return rc
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
    rerun_summary()
    return 0


UNFINISHED = ("created", "pending", "running", "waiting_for_resource", "preparing", "scheduled")


def _api(method: str, path: str, token: str, header: str) -> Any:
    """Call the GitLab API of this project with ``token`` (header JOB-TOKEN or PRIVATE-TOKEN)."""
    context = ssl.create_default_context(cafile=_env("CI_SERVER_TLS_CA_FILE") or None)
    request = urllib.request.Request(  # nosec B310  # GitLab API of this project
        f"{_env('CI_API_V4_URL')}{path}", method=method, headers={header: token})
    with urllib.request.urlopen(request, context=context, timeout=20) as response:  # nosec B310
        return json.load(response)


def rerun_summary() -> None:
    """Run the summary job again when a retried job was the last one to finish.

    GitLab does not run a job again that already ran: retry a failed stage after the pipeline
    ended and its summary (report and email) still shows the old failure. The last job to end
    asks GitLab to retry the summary; nothing happens while another job of the pipeline is
    unfinished or before the summary ran. The token is the optional masked, protected CI/CD
    variable SVT_API_TOKEN (a project access token with the api scope), else the job token.
    Best effort: a refusal is printed with the way to do it by hand, the job is never failed.
    """
    if _env("CI_JOB_NAME") in ("summary", "preflight") or not _env("CI_API_V4_URL"):
        return
    key = os.environ.get("SVT_API_TOKEN", "")
    token, header = (key, "PRIVATE-TOKEN") if key else (os.environ.get("CI_JOB_TOKEN", ""),
                                                        "JOB-TOKEN")
    base = f"/projects/{_env('CI_PROJECT_ID')}"
    try:
        jobs = _api("GET", f"{base}/pipelines/{_env('CI_PIPELINE_ID')}/jobs?per_page=100",
                    token, header)
        done = next((job for job in jobs if job["name"] == "summary"), None)
        if not done or done["status"] in UNFINISHED:
            return
        if any(job["status"] in UNFINISHED for job in jobs
               if job["name"] != "summary" and str(job["id"]) != _env("CI_JOB_ID")):
            return
        _api("POST", f"{base}/jobs/{done['id']}/retry", token, header)
        _say(f"{_env('CI_JOB_NAME')} was the last job to end after the summary ran: the "
             "summary job was started again")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reason = (f"HTTP {exc.code}" if isinstance(exc, urllib.error.HTTPError)
                  else type(exc).__name__)
        _say(f"the summary job could not be started again ({reason}): retry it by hand, or give "
             "the project access token (api scope) as the masked, protected CI/CD variable "
             "SVT_API_TOKEN")


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


def _section_rows(report: Dict[str, Any], cell: str = "padding:6px") -> str:
    rows = ""
    for section in report.get("sections") or []:
        results = [r for item in section.get("items") or [] for r in item.get("results") or []]
        count = {s: sum(1 for r in results if r.get("status") == s)
                 for s in ("Passed", "Failed", "Skipped")}
        rows += (f"<tr><td style='{cell}'>{html.escape(section.get('name', ''))}</td>"
                 f"<td style='{cell}'>{_status_cell(section.get('status', ''))}</td>"
                 f"<td style='{cell}'>{len(section.get('items') or [])}</td>"
                 f"<td style='{cell};color:#198754'>{count['Passed']}</td>"
                 f"<td style='{cell};color:#dc3545'>{count['Failed']}</td>"
                 f"<td style='{cell};color:#fd7e14'>{count['Skipped']}</td></tr>")
    return rows


def _status_cell(status: str) -> str:
    color = {"success": "#28a745", "passed": "#28a745", "failed": "#dc3545",
             "running": "#007bff"}.get(status.lower(), "#6c757d")
    return f"<b style='color:{color}'>{html.escape(status.upper() or 'NOT RUN')}</b>"


def _web_base(clone_url: str) -> str:
    """Return the https web address of a clone URL (https, ssh:// or git@host:path), or ""."""
    clone_url = re.sub(r"^(https?://)[^/@]+@", r"\1", clone_url.strip())
    match = (re.fullmatch(r"https?://([^/\s]+)/(.+?)(?:\.git)?/?", clone_url)
             or re.fullmatch(r"(?:ssh://)?[\w.-]+@([^/:\s]+)[:/](.+?)(?:\.git)?/?", clone_url))
    return f"https://{match.group(1)}/{match.group(2)}" if match else ""


def _git_links(repo: str, branch: str, commit: str) -> Tuple[str, str, str]:
    """Return the web links of the repository, the branch and the commit ("" when unknown)."""
    base = _web_base(repo)
    marker = "/-" if "gitlab" in base else ""
    tree = f"{base}{marker}/tree/{urllib.parse.quote(branch, safe='/')}"
    return (base, tree if base and branch else "",
            f"{base}{marker}/commit/{commit}" if base and commit else "")


def _anchor(url: str, text: str) -> str:
    return (f"<a href='{html.escape(url, quote=True)}' style='color:#0b5ed7'>"
            f"{html.escape(text)}</a>" if url else html.escape(text))


def _button(url: str, text: str, color: str = "#0b5ed7") -> str:
    return (f"<a href='{html.escape(url, quote=True)}' style='display:inline-block;"
            f"padding:8px 14px;margin:0 8px 8px 0;background:{color};color:#fff;"
            f"text-decoration:none;border-radius:4px;font-size:13px'>{html.escape(text)}</a>"
            if url else "")


def _job_reasons() -> Dict[str, str]:
    """Return {job: the error its job recorded} (jobs that failed through _fail)."""
    reasons = {}
    for path in glob.glob(os.path.join(STATE_DIR, "errors", "*.txt")):
        try:
            with open(path, "r", encoding="utf-8") as stream:
                reasons[os.path.basename(path)[:-4]] = stream.read().strip()
        except OSError:
            continue
    return reasons


def _job_details() -> Dict[str, Dict[str, Any]]:
    """Return {job: {url, status, duration}} of this pipeline (best effort: {} when the API call
    is refused or fails; the report and the email then link the pipeline only)."""
    api, pipeline = _env("CI_API_V4_URL"), _env("CI_PIPELINE_ID")
    token = os.environ.get("CI_JOB_TOKEN", "")
    if not (api and token and pipeline and _env("CI_PROJECT_ID")):
        return {}
    cafile = _env("CI_SERVER_TLS_CA_FILE")
    try:
        context = ssl.create_default_context(cafile=cafile or None)
        request = urllib.request.Request(  # nosec B310  # GitLab API of this project
            f"{api}/projects/{_env('CI_PROJECT_ID')}/pipelines/{pipeline}/jobs?per_page=100",
            headers={"JOB-TOKEN": token})
        with urllib.request.urlopen(request, context=context, timeout=20) as response:  # nosec B310
            return {job["name"]: {"url": job["web_url"], "status": job.get("status", ""),
                                  "duration": job.get("duration")} for job in json.load(response)}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _job_links() -> Dict[str, str]:
    """Return {job: its page in GitLab} for this pipeline ({} when the API is not reachable)."""
    return {name: item["url"] for name, item in _job_details().items()}


def _read_commit() -> str:
    try:
        with open(os.path.join(STATE_DIR, "commit.txt"), "r", encoding="utf-8") as stream:
            return stream.read().strip()
    except OSError:
        return ""


def _fetch_theme_report(theme: str, run: Dict[str, Any]) -> Dict[str, Any]:
    """Copy the SVT report, the JUnit files and the logs of a theme's run into svt_report/;
    return the report JSON."""
    folder = os.path.join(REPORT_DIR, theme)
    os.makedirs(folder, exist_ok=True)
    data: Dict[str, Any] = {}
    for ext in ("html", "json"):
        source = f"{run['report_path']}/{run['report_name']}.{ext}"
        rc, content = remote(f"cat {shlex.quote(source)}", capture=True)
        if rc == 0 and content:
            with open(os.path.join(folder, f"{run['report_name']}.{ext}"), "wb") as stream:
                stream.write(content)
            if ext == "json":
                data = json.loads(content.decode(errors="replace") or "{}")
    _fetch_files(f"{run['report_path']}/junit_*.xml", os.path.join(REPORT_DIR, "junit"))
    if SAFE_PATH.fullmatch(str(run.get("ci_dir", ""))):
        _fetch_files(f"{run['ci_dir']}/*.log", os.path.join(folder, "logs"))
    _fetch_files(f"{run['report_path']}/*.log", os.path.join(folder, "logs", "run"))
    _say(f"theme {theme}: SVT report of run {run.get('run_id')} -> {folder}/")
    return data


def _theme_title(theme: str, report: Dict[str, Any]) -> str:
    return str((report.get("meta") or {}).get("theme_title") or theme)


REPORT_NAME = "svt_report.html"


def _common_jobs() -> Tuple[str, ...]:
    """Return the cluster jobs of the report: preflight, initialization (left out when every theme
    starts from scratch) and summary."""
    order = [job for job in _env("SVT_JOB_ORDER").split(",") if job]
    return tuple(job for job in ("preflight", "initialization", "summary")
                 if not order or job in order)


def _report_context(themes: List[str], records: Dict[str, Dict[str, Any]],
                    reports: Dict[str, Dict[str, Any]], verdict: str,
                    problems: List[str], statuses: Dict[str, str]) -> Dict[str, Any]:
    """Return what svt_report_page.build_report needs: the run, its jobs and every theme."""
    repo, branch, commit = _env("SVT_OMNIA_REPO"), _env("SVT_OMNIA_BRANCH"), _read_commit()
    _, branch_url, commit_url = _git_links(repo, branch, commit)
    details, reasons = _job_details(), _job_reasons()
    common = [{"name": job, "status": statuses.get(job, ""), "reason": reasons.get(job, ""),
               "url": (details.get(job) or {}).get("url", ""),
               "duration": (details.get(job) or {}).get("duration")}
              for job in _common_jobs()]
    entries = []
    for theme in themes:
        record, report = records.get(theme) or {}, reports.get(theme) or {}
        run, meta = record.get("run") or {}, report.get("meta") or {}
        source = os.path.join(REPORT_DIR, theme, f"{run.get('report_name', '')}.html")
        page = ""
        if run and os.path.isfile(source):
            with open(source, "r", encoding="utf-8", errors="replace") as stream:
                page = stream.read()
            os.remove(source)
        entries.append({"name": theme, "title": _theme_title(theme, report),
                        "description": meta.get("description", ""),
                        "verdict": record.get("verdict") or "NOT RUN",
                        "run_id": run.get("run_id", ""), "problems": record.get("problems") or [],
                        "pipeline_url": record.get("pipeline_url", ""), "report": report,
                        "page_html": page})
    return {"label": _env("SVT_LABEL") or _env("SVT_CLUSTER"), "verdict": verdict,
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "info": {"repo": _web_base(repo) or repo, "repo_url": _web_base(repo),
                     "branch": branch, "branch_url": branch_url, "commit": commit,
                     "commit_url": commit_url, "pipeline_url": _env("CI_PIPELINE_URL")},
            "common": common, "problems": problems, "reasons": reasons, "themes": entries}


def _write_report(context: Dict[str, Any]) -> str:
    """Write svt_report/svt_report.html, the ONE report (overview and a page per theme)."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, REPORT_NAME)
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(svt_report_page.build_report(context))
    _say(f"report: {path} ({os.path.getsize(path) // 1024} KB, {len(context['themes']) + 1} "
         "pages: the overview and one per theme)")
    return path


def _send_cluster_email(verdict: str, statuses: Dict[str, str], themes: List[str],
                        records: Dict[str, Dict[str, Any]], reports: Dict[str, Dict[str, Any]],
                        problems: List[str]) -> bool:
    """Send the one email of the cluster pipeline; False only when it was configured and failed."""
    recipients = [r.strip() for r in _env("EMAIL_RECIPIENTS").split(",") if r.strip()]
    server, sender = _env("SMTP_SERVER"), _env("EMAIL_SENDER")
    if not (recipients and server and sender):
        _say("email not configured (EMAIL_RECIPIENTS, EMAIL_SENDER, SMTP_SERVER): not sent")
        return True
    label = _env("SVT_LABEL")
    message = MIMEMultipart("mixed")
    message["From"], message["To"] = sender, ", ".join(recipients)
    names = ", ".join(themes)
    message["Subject"] = f"Omnia SVT [{label}] {names} - {verdict}"
    commit, branch, repo = _read_commit(), _env("SVT_OMNIA_BRANCH"), _env("SVT_OMNIA_REPO")
    repo_url, branch_url, commit_url = _git_links(repo, branch, commit)
    pipeline_url, job_url = _env("CI_PIPELINE_URL"), _env("CI_JOB_URL")
    attachments = [os.path.join(REPORT_DIR, REPORT_NAME)] if os.path.isfile(
        os.path.join(REPORT_DIR, REPORT_NAME)) else []
    report_url = f"{job_url}/artifacts/browse/svt_report/" if job_url and attachments else ""
    reasons, links = _job_reasons(), _job_links()
    color = "#198754" if verdict == "PASSED" else "#dc3545"
    cell = "padding:6px 10px;border:1px solid #dee2e6;font-size:13px"
    head = f"{cell};background:#f1f3f5;text-align:left"
    esc = html.escape
    info = [("OIM", esc(label or "-")), ("Themes", esc(" -> ".join(themes))),
            ("Repository", _anchor(repo_url, _web_base(repo) or repo or "-")),
            ("Branch", _anchor(branch_url, branch or "-")),
            ("Commit", _anchor(commit_url, commit[:12]) if commit else "not checked out"),
            ("Pipeline", _anchor(pipeline_url, pipeline_url or "-"))]
    info_rows = "".join(f"<tr><td style='{head};width:110px'><b>{n}</b></td>"
                        f"<td style='{cell}'>{v}</td></tr>" for n, v in info)
    why = ""
    if problems:
        items = "".join(
            f"<li style='margin-bottom:4px'>{esc(item)}"
            + "".join(f"<br><span style='color:#842029'>{esc(reasons[job])}</span>"
                      for job in reasons if item.startswith(f"{job} ")) + "</li>"
            for item in problems)
        why = ("<div style='border-left:4px solid #dc3545;background:#fdf1f2;padding:10px 14px;"
               f"margin:16px 0'><b>Problems:</b><ul style='margin:6px 0 0 18px;padding:0'>{items}"
               "</ul></div>")
    rows, detail = [], []
    for index, theme in enumerate(themes):
        record, report = records.get(theme) or {}, reports.get(theme) or {}
        state = record.get("verdict") or "NOT RUN"
        run = (record.get("run") or {}).get("run_id", "-")
        job_state = {"PASSED": "success", "FAILED": "failed"}.get(state, "")
        link = _anchor(record.get("pipeline_url", ""), "pipeline")
        rows.append(f"<tr><td style='{cell}'>{index + 1}. {esc(_theme_title(theme, report))} "
                    f"({esc(theme)})</td><td style='{cell}'>{_status_cell(job_state)}</td>"
                    f"<td style='{cell}'>{esc(str(run))}</td><td style='{cell}'>{link}</td></tr>")
        if report.get("sections"):
            detail.append(
                f"<h3 style='margin:18px 0 6px;font-size:15px'>{esc(theme)}: SVT sections</h3>"
                f"<table cellpadding='0' cellspacing='0' style='{TABLE_STYLE}'>"
                f"<tr><th style='{head}'>Section</th><th style='{head}'>Status</th>"
                f"<th style='{head}'>Steps</th><th style='{head}'>Passed</th>"
                f"<th style='{head}'>Failed</th><th style='{head}'>Skipped</th></tr>"
                f"{_section_rows(report, cell)}</table>")
    jobs = "".join(f"<tr><td style='{cell}'>{_anchor(links.get(job, ''), job)}</td>"
                   f"<td style='{cell}'>{_status_cell(statuses.get(job, ''))}</td></tr>"
                   for job in _common_jobs())
    buttons = (_button(pipeline_url, "Open the pipeline") + _button(report_url, "Browse the report")
               + _button(f"{job_url}/artifacts/download" if job_url else "",
                         "Download all artifacts", "#6c757d"))
    body = (
        "<html><body style='margin:0;padding:16px;background:#f8f9fa;"
        "font-family:Arial,Helvetica,sans-serif;color:#212529'>"
        "<table role='presentation' width='700' cellpadding='0' cellspacing='0' "
        "style='max-width:700px;margin:0 auto;background:#fff;border:1px solid #dee2e6'>"
        f"<tr><td style='background:{color};color:#fff;padding:16px 20px'>"
        f"<div style='font-size:12px;opacity:.85'>Omnia System Verification</div>"
        f"<div style='font-size:20px;font-weight:bold'>{esc(label)}: {esc(verdict)}</div></td></tr>"
        "<tr><td style='padding:16px 20px'>"
        f"<table cellpadding='0' cellspacing='0' style='border-collapse:collapse;width:100%'>"
        f"{info_rows}</table>{why}<p style='margin:16px 0 8px'>{buttons}</p>"
        "<h3 style='margin:18px 0 6px;font-size:15px'>Themes (run order)</h3>"
        "<table cellpadding='0' cellspacing='0' style='border-collapse:collapse;width:100%'>"
        f"<tr><th style='{head}'>Theme</th><th style='{head}'>Status</th>"
        f"<th style='{head}'>Run</th><th style='{head}'>Pipeline</th></tr>{''.join(rows)}</table>"
        "<h3 style='margin:18px 0 6px;font-size:15px'>Common jobs</h3>"
        "<table cellpadding='0' cellspacing='0' style='border-collapse:collapse;width:100%'>"
        f"<tr><th style='{head}'>Job</th><th style='{head}'>Status</th></tr>{jobs}</table>"
        f"{''.join(detail)}<p style='margin:16px 0 0;font-size:12px;color:#6c757d'>"
        + (f"One report is attached: {REPORT_NAME}. Open it in a browser: an overview first, "
           "then a page per theme (use Next, Previous or the tabs)." if attachments else
           "No SVT report is attached: none was produced.")
        + "</p></td></tr></table></body></html>")
    text = "\n".join([
        f"Omnia SVT [{label}] {names}: {verdict}", "",
        f"Repository: {_web_base(repo) or repo or '-'}",
        f"Branch:     {branch or '-'}", f"Commit:     {commit[:12] or 'not checked out'}",
        f"Pipeline:   {pipeline_url}", *([f"Report:     {report_url}"] if report_url else []), "",
        *(["Problems:", *[f"  {item}" for item in problems], ""] if problems else []),
        "Themes (run order):",
        *(f"  {i + 1}. {theme:<20} {(records.get(theme) or {}).get('verdict') or 'NOT RUN'}"
          for i, theme in enumerate(themes))])
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(text, "plain", "utf-8"))
    alternative.attach(MIMEText(body, "html", "utf-8"))
    message.attach(alternative)
    for path in attachments:
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
    """The one summary of the cluster pipeline: collect every theme's result and report, write
    the ONE report (an overview and a page per theme), send one email, fail on any failure."""
    statuses = _job_statuses()
    themes = _themes()
    problems = [f"{job} {statuses[job]}" for job in ("preflight", "initialization")
                if statuses.get(job) in ("failed", "canceled")]
    records: Dict[str, Dict[str, Any]] = {}
    reports: Dict[str, Dict[str, Any]] = {}
    for theme in themes:
        record = _read_json(f"{_group_dir()}/theme_{theme}.json") if _env("SVT_TARGET_IP") else {}
        records[theme] = record
        if not record:
            problems.append(f"theme {theme} did not run or left no result")
            continue
        if record.get("verdict") != "PASSED":
            detail = "; ".join(record.get("problems") or [])
            problems.append(f"theme {theme} FAILED" + (f" ({detail})" if detail else ""))
        if record.get("run"):
            reports[theme] = _fetch_theme_report(
                theme, {**record["run"], "ci_dir": record.get("ci_dir", "")})
    verdict = "FAILED" if problems else "PASSED"
    statuses["summary"] = "failed" if problems else "success"
    _write_report(_report_context(themes, records, reports, verdict, problems, statuses))
    _say(f"overall: {verdict}" + (f" ({'; '.join(problems)})" if problems else ""))
    sent = _send_cluster_email(verdict, statuses, themes, records, reports, problems)
    if not sent and _env("SVT_EMAIL_REQUIRED").lower() == "true":
        _say("SVT_EMAIL_REQUIRED=true: the summary job fails because the email was not sent")
        return 1
    return 1 if problems else 0


def main(argv: List[str]) -> int:
    """Dispatch one job."""
    apply_cluster()
    jobs = {"preflight": preflight, "checkout": checkout, "initialization": initialization,
            "clean-install": clean_install, "theme-result": theme_result, "summary": summary,
            "after-job": after_job}
    if len(argv) == 2 and argv[0] == "stage":
        return stage(argv[1])
    if len(argv) == 1 and argv[0] in jobs:
        return jobs[argv[0]]()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
