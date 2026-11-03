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

    meta:     theme, description, run_id, started_at, state, previous_run, commit, oim
    sections: [{kind: setup | stage, name, title, status, started_at, duration,
                items: [item, ...]}, ...]          # in the order they ran
    item:     {id, name, status, duration, command, note, error, output,
               results: [{name, status, duration, details}, ...]}

A setup section (cleanup, install) has one item per sub-step; a stage section
has one item per SVT test. ``output`` is what the command printed on the
screen (the playbook output of an ``exec`` step, the test output of a
``verify`` step); ``results`` are the FVT results the step added to the FVT
report. The HTML is rendered from the JSON after every change: run details on
top, the summary per section, then each section top to bottom. Secrets and
IPs are masked in the HTML with omnia_auto's redaction.
"""

import html
import json
import os
import re
import socket
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from omnia_auto import build_report_name
# The same masking omnia_auto applies to its own HTML report.
from omnia_auto.functions.report_html import _redact_sensitive as redact

from .process_func import capture_command, format_duration
from ..vars.common_vars import FVT_REPORT_DIR, FVT_REPORT_NAME, MAX_OUTPUT_CHARS, REPO_ROOT
from ..vars.theme_vars import STAGE_TITLES, THEMES

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
STATUSES = ("Passed", "Failed", "Skipped")
RUNNING = "Running"
KIND_TITLES = {"setup": "Setup", "stage": "Stage"}


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
                "status": status_of(result.get("status")),
                "duration": float(result.get("duration_seconds") or result.get("duration")
                                  or 0.0),
                "details": clean_output("\n".join(
                    part for part in (str(result.get("details") or ""),
                                      str(result.get("error") or "")) if part))}
               for result in row.get("results") or []]
    return {"id": row.get("id", ""), "name": row.get("name", ""),
            "status": status_of(row.get("status")),
            "duration": round(float(row.get("duration") or 0.0), 1),
            "command": row.get("command", ""), "note": row.get("details", "") or "",
            "error": row.get("error", "") or "", "output": clean_output(row.get("output", "")),
            "results": results}


# ---------------------------------------------------------------- sections
def _unique_name(report: Dict[str, Any], name: str) -> str:
    taken = {section["name"] for section in report["sections"]}
    if name not in taken:
        return name
    number = 2
    while f"{name} ({number})" in taken:
        number += 1
    return f"{name} ({number})"


def open_section(settings: Dict[str, str], kind: str, name: str) -> str:
    """Start a section (a stage while it runs); return its name (``name (2)`` when repeated)."""
    report = _load(settings)
    unique = _unique_name(report, name)
    report["sections"].append({"kind": kind, "name": unique,
                               "title": STAGE_TITLES.get(name, name.replace("_", " ").title()),
                               "status": RUNNING, "started_at": _now(), "duration": 0.0,
                               "items": []})
    _save(settings, report)
    return unique


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
                  status: Optional[str] = None) -> None:
    """Finish a section: its duration and status (from its items unless given)."""
    report = _load(settings)
    for entry in report["sections"]:
        if entry["name"] == section:
            entry["duration"] = round(float(duration), 1)
            entry["status"] = status_of(status) if status else section_status(entry["items"])
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


def failed_parts(settings: Dict[str, str]) -> List[str]:
    """Return what failed in the run: SVT sections and FVT modules (also run by hand)."""
    failed = [section["name"] for section in _load(settings)["sections"]
              if section.get("status") == "Failed"]
    fvt = fvt_report_settings(settings)
    data = load_json(fvt_report_file(fvt["report_path"], fvt["report_name"]))
    failed.extend(f"FVT {module.get('module', '')}"
                  for server in data.get("servers", {}).values()
                  for run in server.get("runs", []) if run.get("run_id") == settings["run_id"]
                  for module in run.get("modules", [])
                  if int((module.get("summary") or {}).get("failed", 0) or 0) > 0)
    return list(dict.fromkeys(failed))


def run_meta(theme: str, run: Dict[str, Any]) -> Dict[str, Any]:
    """Return the run details shown on top of the report (``run``: run_func.load_run())."""
    failed = run.get("failed") or {}
    previous = run.get("previous") or {}
    return {"theme": theme, "description": THEMES[theme]["description"],
            "run_id": run.get("run_id", ""), "started_at": run.get("started_at", ""),
            "state": f"Failed at {failed['step']}" if failed.get("step") else "Open",
            "previous_run": (f"{previous['run_id']} ({previous.get('state', '')})"
                             if previous.get("run_id") else ""),
            "commit": capture_command(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT),
            "oim": socket.gethostname()}


# -------------------------------------------------------------------- HTML
CSS = """
body{font-family:Segoe UI,Helvetica,Arial,sans-serif;margin:0;background:#f4f6f8;color:#1f2933}
main{max-width:1280px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 16px}
h2{font-size:17px;margin:28px 0 8px;padding-bottom:4px;border-bottom:2px solid #d9e2ec}
table{border-collapse:collapse;width:100%;background:#fff;margin:8px 0}
th,td{border:1px solid #d9e2ec;padding:6px 10px;text-align:left;font-size:13px;vertical-align:top}
th{background:#eef2f7;font-weight:600}
table.details th{width:180px}
.badge{display:inline-block;min-width:64px;text-align:center;padding:2px 8px;border-radius:10px;
font-size:12px;font-weight:600;color:#fff}
.Passed{background:#2f9e44}.Failed{background:#e03131}.Skipped{background:#868e96}
.Running{background:#f08c00}.Open{background:#1971c2}
details.item{background:#fff;border:1px solid #d9e2ec;border-radius:6px;margin:6px 0}
details.item>summary{cursor:pointer;padding:8px 12px;font-size:14px}
details.item>div{padding:4px 14px 12px}
details.inner{margin:6px 0}
details.inner>summary{cursor:pointer;font-size:13px;color:#334e68}
pre{background:#102a43;color:#d9e2ec;padding:10px 12px;border-radius:4px;font-size:12px;
white-space:pre-wrap;word-break:break-word;max-height:640px;overflow:auto;margin:6px 0}
.meta{color:#52606d;font-size:12px}
.error{background:#fff5f5;border:1px solid #ffc9c9;padding:6px 10px;border-radius:4px;
font-size:13px;white-space:pre-wrap}
"""


def _text(value: Any) -> str:
    return html.escape(redact(str(value if value is not None else "")))


def _badge(status: str) -> str:
    return f'<span class="badge {html.escape(status)}">{html.escape(status)}</span>'


def _counts(items: List[Dict[str, Any]]) -> Dict[str, int]:
    return {state: sum(1 for item in items if item.get("status") == state) for state in STATUSES}


def _section_heading(section: Dict[str, Any], number: int) -> str:
    kind = KIND_TITLES.get(section.get("kind"), "")
    label = f"{kind} {number}: " if section.get("kind") == "stage" else f"{kind}: "
    return label + section.get("title", section["name"]) + (
        section["name"][len(section["name"].split(" (")[0]):] if " (" in section["name"] else "")


def _run_table(meta: Dict[str, Any], sections: List[Dict[str, Any]]) -> str:
    items = [item for section in sections for item in section.get("items", [])]
    counts = _counts(items)
    rows = (("Theme", meta.get("theme")), ("Description", meta.get("description")),
            ("Run ID", meta.get("run_id")), ("Run State", meta.get("state")),
            ("Started", meta.get("started_at")), ("Last Updated", meta.get("updated_at")),
            ("Previous Run", meta.get("previous_run") or "-"),
            ("Commit", meta.get("commit")), ("OIM", meta.get("oim")),
            ("Tests", f"{len(items)} ({counts['Passed']} passed, {counts['Failed']} failed, "
                      f"{counts['Skipped']} skipped)"))
    body = "".join(f"<tr><th>{html.escape(label)}</th><td>{_text(value)}</td></tr>"
                   for label, value in rows)
    return f'<table class="details">{body}</table>'


def _summary_table(sections: List[Dict[str, Any]], headings: List[str]) -> str:
    head = ("<tr><th>Section</th><th>Status</th><th>Tests</th><th>Passed</th><th>Failed</th>"
            "<th>Skipped</th><th>Duration</th><th>Started</th></tr>")
    body = ""
    for index, section in enumerate(sections):
        counts = _counts(section.get("items", []))
        body += (f'<tr><td><a href="#section-{index}">{html.escape(headings[index])}</a></td>'
                 f"<td>{_badge(section.get('status', ''))}</td>"
                 f"<td>{len(section.get('items', []))}</td><td>{counts['Passed']}</td>"
                 f"<td>{counts['Failed']}</td><td>{counts['Skipped']}</td>"
                 f"<td>{format_duration(section.get('duration') or 0)}</td>"
                 f"<td>{_text(section.get('started_at', ''))}</td></tr>")
    return f"<table>{head}{body}</table>"


def _results_table(results: List[Dict[str, Any]]) -> str:
    if not results:
        return ""
    rows = "".join(
        f"<tr><td>{_text(result['name'])}"
        + (f'<details class="inner"><summary>Details</summary><pre>{_text(result["details"])}'
           f"</pre></details>" if result.get("details") else "")
        + f"</td><td>{_badge(result['status'])}</td>"
          f"<td>{format_duration(result.get('duration') or 0)}</td></tr>"
        for result in results)
    return ("<p><strong>FVT Results</strong></p><table><tr><th>Test</th>"
            f"<th>Status</th><th>Duration</th></tr>{rows}</table>")


def _item(item: Dict[str, Any]) -> str:
    title = f"{item['id']} - {item['name']}" if item.get("id") else item.get("name", "")
    parts = []
    if item.get("command"):
        parts.append(f"<p><strong>Command:</strong> <code>{_text(item['command'])}</code></p>")
    if item.get("note"):
        parts.append(f'<p class="meta">{_text(item["note"])}</p>')
    if item.get("error"):
        parts.append(f'<div class="error"><strong>Error:</strong> {_text(item["error"])}</div>')
    parts.append(_results_table(item.get("results") or []))
    if item.get("output"):
        opened = " open" if item.get("status") == "Failed" else ""
        parts.append(f'<details class="inner"{opened}><summary>Screen Output '
                     f'({len(item["output"])} characters)</summary>'
                     f"<pre>{_text(item['output'])}</pre></details>")
    return (f'<details class="item"><summary>{_badge(item["status"])} {_text(title)} '
            f'<span class="meta">({format_duration(item.get("duration") or 0)})</span>'
            f"</summary><div>{''.join(parts)}</div></details>")


def render_html(report: Dict[str, Any]) -> str:
    """Return the HTML page of a report (see the module doc for the layout)."""
    meta, sections = report.get("meta") or {}, report.get("sections") or []
    headings, stage = [], 0
    for section in sections:
        stage += section.get("kind") == "stage"
        headings.append(_section_heading(section, stage))
    blocks = "".join(
        f'<h2 id="section-{index}">{html.escape(headings[index])} '
        f"{_badge(section.get('status', ''))}</h2>"
        + "".join(_item(item) for item in section.get("items", []))
        for index, section in enumerate(sections))
    title = f"Omnia System Verification Report - {meta.get('theme', '')} - {meta.get('run_id', '')}"
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main>"
            f"<h1>Omnia System Verification Report</h1><h2>Run Details</h2>"
            f"{_run_table(meta, sections)}<h2>Summary</h2>{_summary_table(sections, headings)}"
            f"{blocks}</main></body></html>\n")


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
