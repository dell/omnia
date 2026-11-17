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

"""The SVT report of a run: one JSON and one HTML, in the SVT's own format.

``<run folder>/<report_name>.json`` holds::

    meta:     theme, theme_title, description, stages, run_id, started_at, state,
              previous_run, repo_url, branch, commit, commit_full, oim, updated_at
    sections: [{kind: setup | stage, name, stage, status, started_at, duration,
                items: [item, ...]}, ...]          # in the order they ran
    item:     {id, name, status, duration, command, note, error, output,
               fvt: {suite, domain, tag, action, options},
               results: [{name, tc_id, module, status, duration, details, error,
                          reason}, ...]}

A setup section (cleanup, install) has one item per sub-step; a stage section
has one item per SVT test. ``output`` is what the command printed on the
screen (the playbook output of an ``exec`` step, the test output of a
``verify`` step); ``results`` are the FVT results of the step. The HTML
(svt_report_html.py) is rendered from the JSON after every change. Secrets and
IPs are masked in the HTML with omnia_auto's redaction.
"""

import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from omnia_auto import build_report_name

from .process_func import capture_command
from .svt_report_html import render_html
from ..vars.common_vars import (
    FIRST_STAGE,
    FVT_REPORT_DIR,
    FVT_REPORT_NAME,
    MAX_OUTPUT_CHARS,
    REPO_ROOT,
)
from ..vars.theme_vars import THEMES, theme_title

from ..vars.report_vars import (
    ANSI_RE,
    CREDENTIALS_RE,
    RUNNING,
)


# ------------------------------------------------------------------- files
def report_files(settings: Dict[str, str]) -> Dict[str, str]:
    """Return the JSON and HTML paths of the SVT report of the run."""
    base = os.path.join(settings["report_path"], settings["report_name"])
    return {"json": f"{base}.json", "html": f"{base}.html"}


def fvt_report_settings(settings: Dict[str, str]) -> Dict[str, str]:
    """Return the report settings the FVT suites get: <run folder>/fvt/fvt_report."""
    return {"report_path": os.path.join(settings["report_path"], FVT_REPORT_DIR),
            "report_name": FVT_REPORT_NAME, "run_id": settings["run_id"]}


def fvt_report_file(report_path: str, report_name: str) -> str:
    """Return the JSON file omnia_auto writes for ``report_path`` / ``report_name``."""
    return os.path.join(report_path, f"{build_report_name(report_name)}.json")


def load_json(path: str) -> Dict[str, Any]:
    """Return the JSON mapping in ``path`` ({} when missing or not a mapping)."""
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_atomic(path: str, text: str) -> None:
    """Replace ``path`` with ``text`` in one step (temporary file, then rename)."""
    handle, temp = tempfile.mkstemp(prefix=".tmp.", dir=os.path.dirname(path))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(settings: Dict[str, str]) -> Dict[str, Any]:
    report = load_json(report_files(settings)["json"])
    report.setdefault("sections", [])
    return report


def _save(settings: Dict[str, str], report: Dict[str, Any]) -> None:
    os.makedirs(settings["report_path"], mode=0o750, exist_ok=True)
    write_atomic(report_files(settings)["json"], json.dumps(report, indent=1, default=str))


# ------------------------------------------------------------------ status
def status_of(value: Any) -> str:
    """Return Passed, Failed or Skipped for any spelling (PASSED, passed, ok ...)."""
    text = str(value or "").strip().lower()
    if text in ("passed", "pass", "ok", "success"):
        return "Passed"
    if text in ("skipped", "skip"):
        return "Skipped"
    return "Failed"


def section_status(items: List[Dict[str, Any]]) -> str:
    """Return Failed when an item failed, Passed when one passed, else Skipped."""
    states = {item.get("status") for item in items}
    if "Failed" in states:
        return "Failed"
    return "Passed" if "Passed" in states else "Skipped"


def clean_output(text: str) -> str:
    """Return ``text`` without ANSI codes, cut to the last MAX_OUTPUT_CHARS characters."""
    text = ANSI_RE.sub("", text or "")
    cut = len(text) - MAX_OUTPUT_CHARS
    return f"... (first {cut} characters cut)\n{text[-MAX_OUTPUT_CHARS:]}" if cut > 0 else text


def make_item(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return a report item from a step row or an SVT test result (see the module doc)."""
    results = [{"name": str(result.get("test_name") or result.get("name") or ""),
                "tc_id": str(result.get("tc_id") or ""),
                "module": str(result.get("module") or ""),
                "status": status_of(result.get("status")),
                "duration": float(result.get("duration_seconds") or result.get("duration")
                                  or 0.0),
                "details": clean_output(str(result.get("details") or "")),
                "error": clean_output(str(result.get("error") or "")),
                "reason": str(result.get("reason") or "")}
               for result in row.get("results") or []]
    return {"id": row.get("id", ""), "name": row.get("name", ""),
            "status": status_of(row.get("status")),
            "duration": round(float(row.get("duration") or 0.0), 1),
            "command": row.get("command", ""), "note": row.get("details", "") or "",
            "error": row.get("error", "") or "", "output": clean_output(row.get("output", "")),
            "fvt": dict(row.get("fvt") or {}), "results": results}


# ---------------------------------------------------------------- sections
def _archive_attempt(settings: Dict[str, str], section: Dict[str, Any]) -> None:
    """Keep a section that a retry replaces as a file of the run folder, not in the report.

    The report shows the latest attempt of a stage only; the earlier attempts (steps, results,
    output) stay in ``<run folder>/attempts/<stage>-attempt-<n>.json`` with the other artifacts.
    """
    directory = os.path.join(os.path.dirname(report_files(settings)["json"]), "attempts")
    os.makedirs(directory, exist_ok=True)
    name = f"{section['name']}-attempt-{int(section.get('attempt') or 1)}.json"
    if section.get("status") == RUNNING:
        section = {**section, "status": "Interrupted"}
    write_atomic(os.path.join(directory, name), json.dumps(section, indent=2))


def open_section(settings: Dict[str, str], kind: str, name: str) -> str:
    """Start a section (a stage while it runs); return its name.

    A section run again in the same run (a retry) takes the place of the earlier one: the
    report keeps one section per stage, the latest attempt, numbered ``attempt``. The earlier
    attempt is archived in the run folder (``_archive_attempt``).
    """
    report = _load(settings)
    sections = report["sections"]
    index = next((i for i in range(len(sections) - 1, -1, -1)
                  if sections[i]["name"] == name), None)
    attempt = 1
    if index is not None:
        _archive_attempt(settings, sections[index])
        attempt = int(sections[index].get("attempt") or 1) + 1
    section = {"kind": kind, "name": name, "stage": name, "status": RUNNING,
               "started_at": _now(), "duration": 0.0, "items": [], "attempt": attempt}
    if index is None:
        sections.append(section)
    else:
        sections[index] = section
    _save(settings, report)
    return name


def section_attempt(settings: Dict[str, str], name: str) -> int:
    """Return the attempt number of the latest section called ``name`` (1 when none)."""
    for section in reversed(_load(settings)["sections"]):
        if section["name"] == name:
            return int(section.get("attempt") or 1)
    return 1


def supersede_failed(settings: Dict[str, str], names: List[str]) -> List[str]:
    """Mark the failed sections called ``names`` as replaced by a retry; return their names.

    A superseded section no longer fails the run; the retry's section takes its place.
    """
    report = _load(settings)
    done = []
    for section in report["sections"]:
        if section["name"] in names and section.get("status") == "Failed":
            section["superseded"] = True
            done.append(section["name"])
    if done:
        _save(settings, report)
    return done


def add_item(settings: Dict[str, str], section: str, item: Dict[str, Any]) -> None:
    """Append ``item`` to the section named ``section``."""
    report = _load(settings)
    for entry in report["sections"]:
        if entry["name"] == section:
            entry["items"].append(item)
            break
    else:
        raise KeyError(f"report section {section!r} not found")
    _save(settings, report)


def close_section(settings: Dict[str, str], section: str, duration: float,
                  status: Optional[str] = None,
                  outputs: Optional[List[Dict[str, str]]] = None) -> None:
    """Finish a section: its duration, status (from its items unless given) and the
    product rows it created or changed (state_func)."""
    report = _load(settings)
    for entry in report["sections"]:
        if entry["name"] == section:
            entry["duration"] = round(float(duration), 1)
            entry["status"] = status_of(status) if status else section_status(entry["items"])
            if outputs:
                entry["outputs"] = outputs
    _save(settings, report)


def set_state(settings: Dict[str, str], state: Dict[str, Any]) -> None:
    """Store the product state at summary (state_func.run_state) in the report."""
    report = _load(settings)
    report["state"] = state
    _save(settings, report)


def add_section(settings: Dict[str, str], done: Dict[str, Any]) -> None:
    """Add a finished section with one item per row.

    ``done`` keys: kind (setup | stage), name, rows, started_at, duration
    (seconds), status (None = from the items).
    """
    section = open_section(settings, done["kind"], done["name"])
    report = _load(settings)
    entry = next(item for item in report["sections"] if item["name"] == section)
    entry["items"] = [make_item(row) for row in done["rows"]]
    entry["started_at"] = done.get("started_at") or entry["started_at"]
    _save(settings, report)
    close_section(settings, section, done.get("duration") or 0.0, done.get("status"))


# ------------------------------------------------------------ run checks
def report_theme(settings: Dict[str, str]) -> str:
    """Return the theme the report of this run was written for ("" when none yet)."""
    return str((_load(settings).get("meta") or {}).get("theme") or "")


def failed_parts(settings: Dict[str, str], ignore: Tuple[str, ...] = ()) -> List[str]:
    """Return the SVT sections of the run that failed, except the ones named in ``ignore``.

    Only the SVT's own sections count: each SVT step holds exactly the FVT
    results it produced, so an FVT suite run by hand or the BuildStream
    validate stage writing into the same FVT report never fails the run.
    """
    return list(dict.fromkeys(section["name"] for section in _load(settings)["sections"]
                              if section.get("status") == "Failed"
                              and not section.get("superseded")
                              and section["name"] not in ignore))


def repo_meta() -> Dict[str, str]:
    """Return the checkout the run tests: clone URL (credentials removed), branch, commit.

    ``branch`` is "" on a detached HEAD.
    """
    def git(*arguments: str) -> str:
        return capture_command(["git", *arguments], cwd=REPO_ROOT)
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    return {"repo_url": CREDENTIALS_RE.sub(r"\1", git("remote", "get-url", "origin")),
            "branch": "" if branch == "HEAD" else branch,
            "commit": git("rev-parse", "--short", "HEAD"),
            "commit_full": git("rev-parse", "HEAD")}


def run_meta(theme: str, run: Dict[str, Any]) -> Dict[str, Any]:
    """Return the run details shown on top of the report (``run``: run_func.load_run())."""
    failed = run.get("failed") or {}
    previous = run.get("previous") or {}
    return {"theme": theme, "theme_title": theme_title(theme),
            "description": THEMES[theme]["description"],
            "stages": [FIRST_STAGE, *THEMES[theme]["stages"]],
            "run_id": run.get("run_id", ""), "started_at": run.get("started_at", ""),
            "state": f"Failed at {failed['step']}" if failed.get("step") else "Open",
            "previous_run": (f"{previous['run_id']} ({previous.get('state', '')})"
                             if previous.get("run_id") else ""),
            **repo_meta(),
            "oim": socket.gethostname()}


# -------------------------------------------------------------------- render
def render(settings: Dict[str, str], meta: Dict[str, Any]) -> str:
    """Store ``meta`` (run_meta) in the report and rewrite its HTML; return the HTML path.

    Raises:
        ValueError: The report belongs to another theme.
    """
    report = _load(settings)
    held = str((report.get("meta") or {}).get("theme") or "")
    if held and held != meta.get("theme"):
        raise ValueError(f"{report_files(settings)['json']} belongs to theme {held}, not "
                         f"{meta.get('theme')}: start a new run (./setup_env.sh --configure)")
    report["meta"] = {**meta, "updated_at": _now()}
    failed = failed_parts(settings)
    if failed and report["meta"].get("state") == "Open":
        report["meta"]["state"] = f"Failed: {', '.join(failed)}"
    _save(settings, report)
    path = report_files(settings)["html"]
    write_atomic(path, render_html(report))
    return path
