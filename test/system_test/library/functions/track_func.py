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


"""Track file of an SVT stage: which tests passed, so a retry resumes at the failed one.

``<run folder>/track/<stage>.json`` holds::

    {"stage": "<stage>", "passed": ["<test id>", ...], "failed": "<test id or empty>",
     "updated_at": "<UTC>"}

Every test records its result there. When a stage is retried (``--retry``, a report attempt
after the first) of a stage whose last attempt failed, the tests that already passed are not
run again: the retry starts at the test that failed, and the tests that passed stay passed,
even when the retry stops again later. A new run (``./setup_env.sh --configure``) has a new
folder and so no track file.
``SVT_NO_RESUME=1`` runs the whole stage again.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from .svt_report_func import report_files, write_atomic

NO_RESUME_ENV = "SVT_NO_RESUME"


def track_path(settings: Dict[str, str], stage: str) -> str:
    """Return the track file of ``stage`` in the run folder."""
    run_folder = os.path.dirname(report_files(settings)["json"])
    return os.path.join(run_folder, "track", f"{stage}.json")


def load(settings: Dict[str, str], stage: str) -> Dict[str, Any]:
    """Return the track of ``stage`` (empty when there is none or it cannot be read)."""
    try:
        with open(track_path(settings, stage), "r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, ValueError):
        data = {}
    return {"stage": stage, "passed": list(data.get("passed") or []),
            "failed": str(data.get("failed") or ""), "updated_at": data.get("updated_at", "")}


def record(settings: Dict[str, str], stage: str, test_id: str, passed: bool) -> None:
    """Record a test result: a pass is kept; a failure removes the pass and is the resume point."""
    track = load(settings, stage)
    track["passed"] = [item for item in track["passed"] if item != test_id]
    if passed:
        track["passed"].append(test_id)
        track["failed"] = "" if track["failed"] == test_id else track["failed"]
    else:
        track["failed"] = test_id
    track["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(track_path(settings, stage)), exist_ok=True)
    write_atomic(track_path(settings, stage), json.dumps(track, indent=2))


def resume_ids(settings: Dict[str, str], stage: str, attempt: int) -> Set[str]:
    """Return the tests of ``stage`` that a retry (attempt 2 or later) does not run again."""
    if attempt < 2 or os.environ.get(NO_RESUME_ENV):
        return set()
    track = load(settings, stage)
    return set(track["passed"]) if track["failed"] else set()


def resume_point(settings: Dict[str, str], stage: str) -> str:
    """Return the test the last attempt failed at (empty when none)."""
    return load(settings, stage)["failed"]


def passed_ids(settings: Dict[str, str], stage: str) -> List[str]:
    """Return the tests recorded as passed."""
    return load(settings, stage)["passed"]
