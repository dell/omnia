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

"""Product state of a theme (THEMES[theme]["state_probe"]), read-only.

- Before and after every theme stage: the rows the stage created or changed
  are its outputs (build_stream: image group, job, statuses), kept in run.json
  and shown under the stage in the report, so a rerun can be traced.
- In summary: the rows created since the run started, and the ones the run
  left behind (``leftover`` statuses: build_stream BUILT/FAILED groups, jobs
  still IN_PROGRESS). Reported only; it never fails the run.

A probe that cannot run (product not installed) yields None: nothing is shown.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .process_func import capture_command
from ..vars.common_vars import REPO_ROOT
from ..vars.theme_vars import THEMES

Rows = Dict[str, Dict[str, str]]


def probe(theme: str) -> Optional[Rows]:
    """Return the probe rows keyed by their identity (None when the probe failed)."""
    spec = THEMES[theme].get("state_probe")
    if not spec:
        return None
    output = capture_command(list(spec["command"]), cwd=REPO_ROOT)
    if not output:
        return None
    columns = spec["columns"]
    rows: Rows = {}
    for line in output.splitlines():
        values = line.split("|")
        if len(values) != len(columns):
            continue
        row = dict(zip(columns, (value.strip() for value in values)))
        rows[row[spec["key"]]] = row
    return rows


def changed(before: Optional[Rows], after: Optional[Rows]) -> List[Dict[str, str]]:
    """Return the rows that are new or differ in ``after`` (the outputs of a stage)."""
    if after is None:
        return []
    before = before or {}
    return [row for key, row in after.items() if before.get(key) != row]


def _when(text: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(text.strip().replace(" ", "T"))
    except ValueError:
        return None


def run_state(theme: str, started_at: str) -> Optional[Dict[str, Any]]:
    """Return the state block of the report: rows created in the run and leftovers."""
    spec = THEMES[theme].get("state_probe")
    rows = probe(theme)
    if not spec or rows is None:
        return None
    start = _when(started_at)
    created = []
    for row in rows.values():
        when = _when(row.get(spec["created"], ""))
        if start is None or when is None or when.timestamp() >= start.timestamp():
            created.append(row)
    leftover = [row for row in created
                if any(row.get(column) in statuses
                       for column, statuses in (spec.get("leftover") or {}).items())]
    return {"label": spec["label"], "columns": list(spec["columns"]), "rows": created,
            "leftover": leftover, "total": len(rows)}
