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

"""One SVT step at a time on this OIM: the lock, its heartbeat, interrupted steps.

Every ./setup_env.sh action and every ./run_validation.sh stage holds
reports/svt.lock while it runs: pid, host, step, run id, start and a
heartbeat refreshed every LOCK_HEARTBEAT_SECONDS.

- A second step while the holder is alive is refused (exit 2).
- A lock whose process is gone (kill -9, a dropped SSH session, a reboot) or
  whose heartbeat stopped is stale: the step it names is recorded as
  interrupted (the run is marked failed at it), then the lock is taken.
- Ctrl-C is recorded by the drivers themselves (_setup.py, _run.py).

Other test processes on the OIM (an FVT suite run by hand, an
ansible-playbook of another checkout) cannot take this lock; they are listed
as a warning when a step starts.
"""

import json
import os
import socket
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from . import run_func
from .svt_report_func import load_json, write_atomic
from ..messages.svt_msgs import LOCK_MSGS
from ..vars.common_vars import (
    LOCK_FILE,
    LOCK_HEARTBEAT_SECONDS,
    LOCK_STALE_SECONDS,
    REPORT_ROOT,
)

Emit = Callable[[str], None]


class LockError(RuntimeError):
    """Another SVT step holds the lock; the message names it."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_lock() -> Dict[str, Any]:
    """Return the lock record ({} when no step holds it)."""
    return load_json(LOCK_FILE)


def lock_state(lock: Dict[str, Any]) -> str:
    """Return "free", "held" or "stale" for a lock record."""
    if not lock.get("pid"):
        return "free"
    if lock.get("host") != socket.gethostname():
        return "held"
    beat = lock.get("heartbeat_epoch") or 0
    if not _alive(int(lock["pid"])) or time.time() - float(beat) > LOCK_STALE_SECONDS:
        return "stale"
    return "held"


def other_test_processes() -> List[str]:
    """Return FVT runners and ansible-playbook processes not started by this step."""
    mine = {os.getpid(), os.getppid()}
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) in mine:
            continue
        try:
            with open(f"/proc/{entry}/cmdline", "rb") as stream:
                args = stream.read().split(b"\0")
        except OSError:
            continue
        text = " ".join(part.decode(errors="replace") for part in args if part)
        if ("_run.py fvt_" in text or "/ansible-playbook " in text) and "_run.py svt_" not in text:
            found.append(f"pid {entry}: {text[:160]}")
    return found


class StepLock:
    """Context manager: hold reports/svt.lock for one step, with a heartbeat."""

    def __init__(self, step: str, emit: Optional[Emit] = None):
        self.step, self.emit = step, emit or print
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.record: Dict[str, Any] = {}

    def _write(self) -> None:
        self.record["heartbeat"] = _now()
        self.record["heartbeat_epoch"] = time.time()
        write_atomic(LOCK_FILE, json.dumps(self.record, indent=2))

    def _beat(self) -> None:
        while not self._stop.wait(LOCK_HEARTBEAT_SECONDS):
            try:
                self._write()
            except OSError:
                pass

    def __enter__(self) -> "StepLock":
        os.makedirs(REPORT_ROOT, mode=0o750, exist_ok=True)
        held = read_lock()
        state = lock_state(held)
        if state == "held":
            raise LockError(LOCK_MSGS["held"].format(
                step=held.get("step"), pid=held.get("pid"), run_id=held.get("run_id"),
                heartbeat=held.get("heartbeat")))
        if state == "stale":
            record_interrupted(held, self.emit)
        run = run_func.load_run()
        self.record = {"pid": os.getpid(), "host": socket.gethostname(), "step": self.step,
                       "run_id": run.get("run_id", ""), "started_at": _now()}
        self._write()
        for line in other_test_processes():
            self.emit(LOCK_MSGS["other_process"].format(process=line))
        self._thread = threading.Thread(target=self._beat, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._stop.set()
        if read_lock().get("pid") == os.getpid():
            try:
                os.unlink(LOCK_FILE)
            except FileNotFoundError:
                pass


def record_interrupted(lock: Dict[str, Any], emit: Emit) -> None:
    """Record the step of a stale lock as interrupted (run marked failed at it)."""
    step = str(lock.get("step") or "unknown step")
    error = LOCK_MSGS["interrupted"].format(step=step, pid=lock.get("pid"),
                                            heartbeat=lock.get("heartbeat", ""))
    emit(error)
    run = run_func.load_run()
    if run.get("run_id") and run.get("run_id") == lock.get("run_id"):
        message = run_func.mark_failed(f"{step} (interrupted)", error)
        if message:
            emit(message)
    interrupted = os.path.join(REPORT_ROOT, "interrupted.json")
    history = load_json(interrupted).get("steps") or []
    history.append({**{k: lock.get(k) for k in ("step", "pid", "run_id", "started_at",
                                                  "heartbeat")}, "found_at": _now()})
    write_atomic(interrupted, json.dumps({"steps": history[-50:]}, indent=2))


def describe_lock() -> str:
    """Return one line about the lock for the status box."""
    lock = read_lock()
    state = lock_state(lock)
    if state == "free":
        return "lock   free"
    return (f"lock   {state}: {lock.get('step')} (pid {lock.get('pid')}, run "
            f"{lock.get('run_id')}, heartbeat {lock.get('heartbeat')})")
