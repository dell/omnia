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

"""Stage playbook log discovery, live streaming and console helpers.

The playbook watcher names every stage attempt log
``<stage>_<playbook>_<YYYYmmdd_HHMMSS UTC>_attempt<N>.log``. Ansible writes
it live under ``/var/log/omnia/<domain>/`` and the watcher copies it to
``<OMNIA_DATA_PATH>/build_stream/log/<job_id>/`` when the attempt ends.
``find_stage_log`` keeps only logs started inside the monitoring window and
picks the highest attempt (then the newest timestamp), so logs of earlier
jobs and superseded attempts are never streamed.
"""

import posixpath
import subprocess
import textwrap
import threading
import time
from typing import Any, Callable, Iterable, List, Optional, Tuple

from omnia_auto import (Colors, Symbols, get_setting, is_local_execution,
                        load_test_config, load_test_credentials)
from omnia_auto.functions.process_security import descriptor_tuple, sshpass_pipe
from omnia_auto.functions.runner_func import _wrap_ssh

from .probe_func import render_cmd, run_cmd
from ..vars.common_vars import (
    LOG_FOLLOW_SETTLE,
    LOG_FOLLOW_SETTLE_MAX,
    LOG_FOLLOW_STOP_TIMEOUT,
    PLAYBOOK_LOG_BASE_DIR,
    STAGE_LOG_RE,
    STAGE_LOG_WINDOW_SLACK,
)

_WRAP_WIDTH = 94


def mark(ok: bool, label: str) -> str:
    """Prefix ``label`` with a check (ok) or cross mark."""
    return f"{Symbols.CHECK if ok else Symbols.CROSS} {label}"


def failure_fields(failures: Iterable[str]) -> List[Tuple[str, str]]:
    """Render failures as crossed report fields."""
    return [(mark(False, "Failure"), item) for item in failures]


def print_log_line(line: str) -> None:
    """Print one streamed log line with the playbook-output pipe prefix."""
    print(f"    {Colors.GRAY}{Symbols.PIPE}{Colors.RESET} {line}", flush=True)


def skip_test(tl: Any, message: str) -> str:
    """Log a skip without truncation (wrapped onto pipe lines); return it.

    Usage: ``pytest.skip(skip_test(tl, message))``.
    """
    lines = textwrap.wrap(message, _WRAP_WIDTH) or [message]
    tl.skipped(lines[0], "\n".join(lines[1:]) or None)
    return message


def find_stage_log(host: Any, stage: str, since_epoch: int, job_dir: str = "",
                   attempt: Any = "", known_path: str = "") -> str:
    """Return the log of the current attempt of ``stage`` (or "").

    Candidates come from ``/var/log/omnia/*/`` (live) and ``job_dir`` (copy
    made when an attempt ends). A candidate is kept when its UTC timestamp
    is not older than ``since_epoch`` minus the window slack. When the DB
    ``attempt`` is known, only that attempt is considered if present. The
    highest (attempt, timestamp) wins; the live copy wins a tie.
    ``known_path`` (job_stages.log_file_path) is used when nothing matches.
    """
    listing = run_cmd(host, "stage_log_candidates", base=PLAYBOOK_LOG_BASE_DIR,
                      job_dir=job_dir or PLAYBOOK_LOG_BASE_DIR, stage=stage).stdout
    floor = time.strftime("%Y%m%d_%H%M%S", time.gmtime(since_epoch - STAGE_LOG_WINDOW_SLACK))
    candidates = []
    for path in listing.split():
        name = posixpath.basename(path)
        match = STAGE_LOG_RE.search(name)
        if not match or not name.startswith(f"{stage}_") or match["ts"] < floor:
            continue
        live = path.startswith(f"{PLAYBOOK_LOG_BASE_DIR}/")
        candidates.append((int(match["attempt"]), match["ts"], live, path))
    wanted = str(attempt).strip()
    if wanted.isdigit() and any(item[0] == int(wanted) for item in candidates):
        candidates = [item for item in candidates if item[0] == int(wanted)]
    if candidates:
        return max(candidates)[3]
    return known_path


def _spawn(command: str) -> subprocess.Popen:
    """Start ``command`` on the OIM (locally or over SSH) with piped stdio."""
    options = {"stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
               "stderr": subprocess.DEVNULL, "text": True, "bufsize": 1,
               "errors": "replace"}
    if is_local_execution():
        return subprocess.Popen(["bash", "-c", command], **options)
    credentials = load_test_credentials()
    with sshpass_pipe(credentials.get("oim_password", "")) as auth_fd:
        ssh_cmd = _wrap_ssh(command, load_test_config(), credentials, auth_fd=auth_fd)
        return subprocess.Popen(["bash", "-c", ssh_cmd],
                                pass_fds=descriptor_tuple(auth_fd), **options)


class LogFollower:
    """Stream a remote log file live, line by line, like ``tail -F``.

    A background ``tail -F`` runs on the OIM and a reader thread prints every
    line the moment Ansible writes it (no polling interval). Long lines are
    wrapped at ``line_width`` like playbook output. The remote tail exits when
    its stdin closes, so stopping never leaves a tail behind on the OIM.
    Following the job-directory copy of the log already being streamed
    (same file name) keeps the live tail, so no line is printed twice.
    """

    def __init__(self, host: Any, printer: Callable[[str], None] = print_log_line):
        self.host = host
        self.printer = printer
        self.path = ""
        self.lines = 0
        self._last_line = 0.0
        self._process: Optional[subprocess.Popen] = None
        self._reader: Optional[threading.Thread] = None

    def follow(self, path: str) -> bool:
        """Start streaming ``path``; return True when it is a new log."""
        if not path or path == self.path:
            return False
        if posixpath.basename(path) == posixpath.basename(self.path):
            return False
        self._stop()
        self.path, self.lines, self._last_line = path, 0, time.time()
        self._process = _spawn(render_cmd("follow_file", path=path))
        self._reader = threading.Thread(target=self._read, args=(self._process,),
                                        daemon=True)
        self._reader.start()
        return True

    def _read(self, process: subprocess.Popen) -> None:
        for line in process.stdout:
            self.lines += 1
            self._last_line = time.time()
            print_wrapped(line.rstrip("\n"), self.printer)

    def _stop(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        try:
            process.stdin.close()
            process.wait(timeout=LOG_FOLLOW_STOP_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
            process.wait()
        if self._reader is not None:
            self._reader.join(timeout=LOG_FOLLOW_STOP_TIMEOUT)

    def drain(self, final: bool = False) -> int:
        """With ``final``, let the last lines arrive, then stop the stream.

        Waits until the log has been quiet for ``LOG_FOLLOW_SETTLE`` seconds
        (at most ``LOG_FOLLOW_SETTLE_MAX``). Returns the lines streamed.
        """
        if final and self._process is not None:
            deadline = time.time() + LOG_FOLLOW_SETTLE_MAX
            while time.time() < deadline and time.time() - self._last_line < LOG_FOLLOW_SETTLE:
                time.sleep(0.5)
            self._stop()
        return self.lines


def print_wrapped(line: str, printer: Callable[[str], None] = print_log_line) -> None:
    """Print ``line`` in ``line_width`` chunks (as playbook output is)."""
    width = get_setting("line_width", 160)
    for start in range(0, max(len(line), 1), width):
        printer(line[start:start + width])


def sleep_streaming(seconds: float, follower: Optional[LogFollower]) -> None:
    """Sleep ``seconds``; a follower keeps streaming live in the background."""
    del follower
    time.sleep(seconds)
