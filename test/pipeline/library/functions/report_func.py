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


"""
HTML report of a pipeline: its information, the stages and the log of every stage.

Pure functions, no network: the caller gives the jobs (from the GitLab API), the logs and the
failure reasons. The page is one file without external assets: a day and a night theme (the
system setting, with a button), collapsible stages with a scrollable log each, a filter and a
search. Everything that comes from a log is escaped.
"""

import html
import re
from datetime import datetime
from typing import Any, Dict, List, Mapping, Sequence

from .email_func import verdict_of
from ..vars.report_vars import (
    CSS, JS, LOG_HEAD_CHARS, MAX_LOG_CHARS, REDACT_PATTERNS, STATUS_LABELS, THEME_KEY,
    UNKNOWN_LABEL,
)

Job = Dict[str, Any]

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_SECTION_RE = re.compile(r"section_(?:start|end):\d+:[A-Za-z0-9_.-]+(?:\[[^\]]*\])?")
_ERROR_RE = re.compile(r"\b(ERROR|FAILED|FATAL|fatal:|Traceback|failed=[1-9])", re.IGNORECASE)
_WARN_RE = re.compile(r"\b(WARNING|WARN)\b")
_OK_RE = re.compile(r"(^ok:|\bPASSED\b|\bsuccess(?:ful|fully)?\b)", re.IGNORECASE)


def clean_log(text: str) -> str:
    """Remove the runner control sequences, the colours and the carriage returns."""
    text = _SECTION_RE.sub("", _ANSI_RE.sub("", text))
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))


def trim_log(text: str, limit: int = MAX_LOG_CHARS, head: int = LOG_HEAD_CHARS) -> str:
    """Keep the head and the tail of a very long log."""
    if len(text) <= limit:
        return text
    tail = limit - head
    omitted = len(text) - limit
    return (f"{text[:head]}\n\n... {omitted} characters omitted (open the job page for "
            f"the whole log) ...\n\n{text[-tail:]}")


def _line_class(line: str) -> str:
    if _ERROR_RE.search(line):
        return "e"
    if _WARN_RE.search(line):
        return "w"
    if _OK_RE.search(line):
        return "o"
    return "s" if line.startswith(("$ ", "=====", "TASK [", "PLAY [")) else ""


def redact_log(text: str) -> str:
    """Hide secrets that a job log may hold: key=value pairs of password-like names, bearer and
    GitLab tokens, and private key blocks. The page is a job artifact and is mailed."""
    for pattern, replacement in REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def render_log(text: str, limit: int = MAX_LOG_CHARS, head: int = LOG_HEAD_CHARS) -> str:
    """Return the escaped log with the error, warning and ok lines marked."""
    rows: List[str] = []
    for line in trim_log(redact_log(clean_log(text)), limit, head).split("\n"):
        cls = _line_class(line)
        escaped = html.escape(line)
        rows.append(f'<span class="{cls}">{escaped}</span>' if cls else escaped)
    return "\n".join(rows)


def safe_url(url: str) -> str:
    """Return the URL when it is http(s), else an empty string."""
    return url if re.match(r"^https?://[^\s\"'<>]+$", url or "") else ""


def link(url: str, text: str) -> str:
    """Return an anchor for a safe URL, or the escaped text."""
    safe = safe_url(url)
    return (f'<a href="{html.escape(safe)}" target="_blank" rel="noopener">{html.escape(text)}</a>'
            if safe else html.escape(text))


def _label(status: str):
    return STATUS_LABELS.get(status, UNKNOWN_LABEL)


def _parse_time(value: str):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def format_duration(seconds: Any) -> str:
    """Return 1h 02m 03s style text for a number of seconds, or a dash."""
    try:
        total = int(round(float(seconds)))
    except (TypeError, ValueError):
        return "-"
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def pipeline_span(jobs: Sequence[Job]) -> float:
    """Seconds from the first start to the last end of the jobs (0 when unknown)."""
    starts = [t for t in (_parse_time(j.get("started_at")) for j in jobs) if t]
    ends = [t for t in (_parse_time(j.get("finished_at")) for j in jobs) if t]
    return (max(ends) - min(starts)).total_seconds() if starts and ends else 0.0


def _ordered(jobs: Sequence[Job], order: Sequence[str]) -> List[Job]:
    rank = {name: i for i, name in enumerate(order)}
    return sorted(jobs, key=lambda j: (rank.get(j["name"], len(rank)), j.get("id", 0)))


def _stage_html(index: int, job: Job, log: str, reason: str, limit: int = MAX_LOG_CHARS,
                head: int = LOG_HEAD_CHARS) -> str:
    label, cls = _label(job["status"])
    name = html.escape(job["name"])
    meta = [f"<span>Job {html.escape(str(job.get('id', '-')))}</span>",
            f"<span>Started {html.escape(str(job.get('started_at') or '-'))}</span>",
            f"<span>Finished {html.escape(str(job.get('finished_at') or '-'))}</span>"]
    if job.get("runner"):
        meta.append(f"<span>Runner {html.escape(str(job['runner']))}</span>")
    if job.get("allow_failure") and job["status"] == "failed":
        meta.append("<span>Failure allowed: the pipeline goes on</span>")
    if job.get("url"):
        meta.append(f"<span>{link(job['url'], 'Open the job in GitLab')}</span>")
    body = f'<div class="meta">{"".join(meta)}</div>'
    if reason:
        body += f'<div class="reason"><b>Why it failed:</b> {html.escape(reason)}</div>'
    if log.strip():
        body += ('<div class="logbar"><button class="btn copy" type="button">Copy log</button></div>'
                 f'<pre class="log" tabindex="0">{render_log(log, limit, head)}</pre>')
    elif job["status"] in ("skipped", "created", "manual"):
        body += '<div class="empty">This stage did not run.</div>'
    else:
        body += '<div class="empty">No log is available for this stage.</div>'
    opened = " open" if job["status"] == "failed" else ""
    return (f'<details class="stage" data-status="{cls}" data-name="{name}"{opened}>'
            f'<summary><span class="idx">{index}</span><span class="name">{name}</span>'
            f'<span class="dur">{format_duration(job.get("duration"))}</span>'
            f'<span class="badge {cls}">{label}</span></summary>'
            f'<div class="body">{body}</div></details>')


def build_report(info: Mapping[str, str], jobs: Sequence[Job], logs: Mapping[str, str],
                 reasons: Mapping[str, str], order: Sequence[str],
                 log_limit: int = MAX_LOG_CHARS, log_head: int = LOG_HEAD_CHARS) -> str:
    """Return the HTML report.

    Args:
        info: cluster, mode, domains, repo, branch, commit, pipeline_url, pipeline_id, user,
            generated (text).
        jobs: dicts with name, status, id, url, duration, started_at, finished_at, runner,
            allow_failure.
        logs: {job name: its log}.
        reasons: {job name: why it failed}.
        order: the job names in pipeline order.
        log_limit, log_head: a log longer than log_limit keeps its first log_head characters and
            the rest of the limit from its end.
    """
    ordered = _ordered(jobs, order)
    verdict = verdict_of([(j["name"], j["status"], j.get("url", "")) for j in ordered])
    counts = {"pass": 0, "fail": 0, "skip": 0, "run": 0}
    for job in ordered:
        counts[_label(job["status"])[1]] += 1
    vclass = {"PASSED": "pass", "FAILED": "fail"}.get(verdict, "")
    repo = info.get("repo", "").removesuffix(".git")
    rows = [("Cluster", html.escape(info.get("cluster", "-"))),
            ("Mode", html.escape(info.get("mode", "-"))),
            ("Domains", html.escape(info.get("domains", "-"))),
            ("Repository", link(repo, repo or "-")),
            ("Branch", html.escape(info.get("branch", "-"))),
            ("Commit", html.escape(info.get("commit") or "not checked out")),
            ("Pipeline", link(info.get("pipeline_url", ""), f"#{info.get('pipeline_id', '-')}")),
            ("Triggered by", html.escape(info.get("user", "-") or "-")),
            ("Started", html.escape(info.get("trigger_time", "-") or "-"))]
    info_html = "".join(f"<div><b>{k}</b>{v}</div>" for k, v in rows)
    cards = [("total", len(ordered), "Stages"), ("pass", counts["pass"], "Passed"),
             ("fail", counts["fail"], "Failed"), ("", counts["skip"], "Not run"),
             ("time", format_duration(pipeline_span(ordered)), "Duration")]
    cards_html = "".join(f'<div class="card {c}"><div class="n">{n}</div><div class="l">{label}</div>'
                         "</div>" for c, n, label in cards)
    stages_html = "".join(_stage_html(i, job, logs.get(job["name"], ""), reasons.get(job["name"], ""),
                                      log_limit, log_head)
                          for i, job in enumerate(ordered, 1))
    title = f"Omnia FVT Pipeline {info.get('cluster', '')}".strip()
    theme_script = (f"<script>try{{var t=localStorage.getItem('{THEME_KEY}')||(window.matchMedia&&"
                    "matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');"
                    "document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>")
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title>{theme_script}<style>{CSS}</style></head><body>"
            f'<div class="header"><div><h1>Omnia FVT Pipeline Report</h1><div class="sub">'
            f"{html.escape(info.get('cluster', ''))} &middot; pipeline "
            f"{link(info.get('pipeline_url', ''), '#' + str(info.get('pipeline_id', '-')))}</div></div>"
            f'<div><span class="verdict {vclass}">{verdict}</span> '
            f'<button class="theme-btn" id="themeBtn" type="button">Night theme</button></div></div>'
            f'<div class="container"><div class="panel"><h2>Pipeline</h2><div class="info">{info_html}'
            f'</div></div><div class="cards">{cards_html}</div><div class="panel"><h2>Stages</h2>'
            '<div class="toolbar"><input id="q" type="search" placeholder="Search stages and logs...">'
            '<button class="chip active" data-filter="all" type="button">All</button>'
            '<button class="chip" data-filter="fail" type="button">Failed</button>'
            '<button class="chip" data-filter="pass" type="button">Passed</button>'
            '<button class="chip" data-filter="skip" type="button">Not run</button>'
            '<button class="btn" id="expand" type="button">Expand all</button>'
            '<button class="btn" id="collapse" type="button">Collapse all</button>'
            '<button class="btn" id="wrap" type="button">Wrap lines</button>'
            f'<span id="shown" class="empty"></span></div>{stages_html}</div>'
            f'<div class="footer">Generated {html.escape(info.get("generated", ""))} &middot; '
            "the log of this summary stage is not part of the report (it is still running)</div>"
            f'</div><script>{JS.replace("@KEY@", THEME_KEY)}</script></body></html>')
