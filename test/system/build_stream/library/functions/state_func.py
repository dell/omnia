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

"""Exec -> verify hand-off for scenarios whose verification needs exec facts.

The runner starts the exec and verify phases as separate pytest processes.
Facts that only exist before or during the entry point (cleanup baselines,
the pre-pass image-group snapshot) are written here by the exec test and
read by the verify tests. Files live on the runner host under
``reports/state/`` (git-ignored), mode 0600, and never hold secrets.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict

from ..vars.common_vars import RUN_STATE_DIR, RUN_STATE_FILE, RUN_STATE_MODE


def _state_path(scenario: str) -> str:
    """Return the state file path of ``scenario``."""
    return os.path.join(RUN_STATE_DIR, RUN_STATE_FILE.format(scenario=scenario))


def clear_run_state(scenario: str) -> None:
    """Remove a previous exec state so verify never reads a stale one."""
    try:
        os.unlink(_state_path(scenario))
    except FileNotFoundError:
        pass


def save_run_state(scenario: str, data: Dict[str, Any]) -> str:
    """Atomically write the exec facts of ``scenario``.

    Returns:
        The state file path.
    """
    os.makedirs(RUN_STATE_DIR, exist_ok=True)
    payload = {"saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "data": data}
    fd, temp = tempfile.mkstemp(prefix=f".{scenario}.", dir=RUN_STATE_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
        os.chmod(temp, RUN_STATE_MODE)
        os.replace(temp, _state_path(scenario))
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return _state_path(scenario)


def load_run_state(scenario: str) -> Dict[str, Any]:
    """Read the exec facts of ``scenario``.

    Returns:
        Dict with keys: success, data, saved_at, path, error. success is
        false when the exec phase has not recorded this scenario.
    """
    path = _state_path(scenario)
    try:
        with open(path, "r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except FileNotFoundError:
        return {"success": False, "data": {}, "saved_at": "", "path": path,
                "error": f"no exec state at {path}"}
    except (OSError, json.JSONDecodeError) as exc:
        return {"success": False, "data": {}, "saved_at": "", "path": path,
                "error": f"unreadable exec state {path}: {exc}"}
    return {"success": True, "data": payload.get("data") or {},
            "saved_at": payload.get("saved_at", ""), "path": path, "error": ""}
