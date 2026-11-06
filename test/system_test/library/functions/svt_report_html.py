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
# pylint: disable=line-too-long
"""HTML page of the SVT report (one self-contained file, the omnia_auto look).

Top to bottom:

- header: the theme name, the run, the OIM, the commit; light/dark toggle
- overall banner: PASSED, FAILED or RUNNING, with the stages run so far
- summary cards: stages, then SVT steps passed / failed / skipped and the pass rate
- run details: theme, run, the repository (clone URL), branch and commit as links
- stage overview: one row per stage (status, SVT steps passed / failed / skipped,
  pass rate)
- stage details: one collapsible block per stage. Initialization holds the
  setup phases (Cleanup, Install) and the readiness checks. Each SVT step opens
  to its command, its FVT results (the same table as the FVT report: TC ID,
  test, status, duration, details and error) and its screen output. The counts
  everywhere above the steps are SVT steps; FVT test counts appear only inside
  the step that ran them.

Only the data in the report JSON is used (svt_report_func.py); secrets and IPs
are masked with omnia_auto's redaction.
"""

import html
import re
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import quote

# The same masking omnia_auto applies to its own HTML report.
from omnia_auto.functions.report_html import _redact_sensitive as redact

from .process_func import format_duration
from ..vars.common_vars import FIRST_STAGE
from ..vars.theme_vars import stage_info

RUNNING = "Running"
# Characters of a step's screen output shown in the HTML (its tail); the JSON
# keeps more (MAX_OUTPUT_CHARS) and the stage/setup logs keep everything.
HTML_OUTPUT_CHARS = 200_000
LONG_WORD = 200
LONG_WORD_RE = re.compile(r"\w{%d,}" % (LONG_WORD + 1))
# Sections shown inside the Initialization stage (./setup_env.sh steps).
INITIALIZATION_PHASES = ("cleanup", "install")
BADGE = {"Passed": "pass", "Failed": "fail", "Skipped": "skip", RUNNING: "run"}

CSS = """
:root{--bg:#f8fafc;--bg-card:#fff;--bg-panel:#f1f5f9;--text:#1e293b;--text-sec:#64748b;--text-muted:#94a3b8;
--border:#e2e8f0;--border-strong:#cbd5e1;--shadow:0 4px 6px -1px rgba(0,0,0,.1),0 2px 4px -1px rgba(0,0,0,.06);
--clr-pass:#10b981;--clr-fail:#ef4444;--clr-skip:#f59e0b;--clr-run:#3b82f6;--clr-brand:#3b82f6;--clr-brand-dk:#1d4ed8;
--badge-pass-bg:#dcfce7;--badge-pass-fg:#166534;--badge-fail-bg:#fee2e2;--badge-fail-fg:#991b1b;
--badge-skip-bg:#fef3c7;--badge-skip-fg:#92400e;--badge-run-bg:#dbeafe;--badge-run-fg:#1e40af;
--log-bg:#1e293b;--log-fg:#e2e8f0;--err-bg:#fef2f2;--err-fg:#991b1b;--err-border:#fecaca}
[data-theme="dark"]{--bg:#0f172a;--bg-card:#1e293b;--bg-panel:#334155;--text:#f1f5f9;--text-sec:#cbd5e1;--text-muted:#94a3b8;
--border:#334155;--border-strong:#475569;--shadow:0 4px 6px -1px rgba(0,0,0,.3);
--clr-pass:#34d399;--clr-fail:#f87171;--clr-skip:#fbbf24;--clr-run:#60a5fa;
--badge-pass-bg:#064e3b;--badge-pass-fg:#6ee7b7;--badge-fail-bg:#7f1d1d;--badge-fail-fg:#fca5a5;
--badge-skip-bg:#78350f;--badge-skip-fg:#fde68a;--badge-run-bg:#1e3a8a;--badge-run-fg:#bfdbfe;
--log-bg:#0f172a;--err-bg:#450a0a;--err-fg:#fca5a5;--err-border:#7f1d1d}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.5}
.header{background:linear-gradient(135deg,var(--clr-brand) 0%,var(--clr-brand-dk) 100%);color:#fff;padding:24px 40px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.header h1{font-size:22px;font-weight:700}
.header .theme-name{font-size:17px;font-weight:600;margin-top:4px}
.header .subtitle{font-size:12px;opacity:.9;margin-top:2px}
.header-right{display:flex;align-items:center;gap:20px}
.header-meta{text-align:right;font-size:12px;line-height:1.5}.header-meta span{display:block}
.theme-toggle{position:relative;width:56px;height:30px;background:rgba(255,255,255,.2);border:2px solid rgba(255,255,255,.4);border-radius:20px;cursor:pointer}
.theme-toggle::after{content:'';position:absolute;width:22px;height:22px;border-radius:50%;background:#fff;left:2px;top:2px;transition:left .3s}
[data-theme="dark"] .theme-toggle::after{left:28px}
.banner{text-align:center;padding:12px;font-size:15px;font-weight:700;letter-spacing:1px}
.banner.pass{background:#d1fae5;color:#065f46;border-bottom:3px solid var(--clr-pass)}
.banner.fail{background:#fee2e2;color:#991b1b;border-bottom:3px solid var(--clr-fail)}
.banner.run{background:#dbeafe;color:#1e40af;border-bottom:3px solid var(--clr-run)}
.banner.skip{background:#fef3c7;color:#92400e;border-bottom:3px solid var(--clr-skip)}
.banner small{display:block;font-weight:500;letter-spacing:0;font-size:12px;margin-top:2px}
.container{max-width:1440px;margin:24px auto;padding:0 24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:24px}
.card{background:var(--bg-card);border-radius:12px;padding:16px;text-align:center;box-shadow:var(--shadow);border-top:4px solid var(--clr-brand)}
.card.clickable{cursor:pointer}.card .value{font-size:30px;font-weight:700;margin:4px 0}
.card .label{font-size:11px;text-transform:uppercase;color:var(--text-sec);letter-spacing:.8px;font-weight:600}
.card .sub{font-size:11px;color:var(--text-muted)}
.card.passed{border-top-color:var(--clr-pass)}.card.passed .value{color:var(--clr-pass)}
.card.failed{border-top-color:var(--clr-fail)}.card.failed .value{color:var(--clr-fail)}
.card.skipped{border-top-color:var(--clr-skip)}.card.skipped .value{color:var(--clr-skip)}
.card.rate .value{color:var(--clr-brand)}.card.duration .value{font-size:22px}
.panel{background:var(--bg-card);border-radius:12px;margin-bottom:24px;box-shadow:var(--shadow);overflow:hidden}
.panel-header{padding:14px 22px;background:var(--bg-panel);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.panel-header h2{font-size:16px;font-weight:600}
table{width:100%;border-collapse:collapse}
th{background:var(--bg-panel);padding:10px 14px;text-align:left;font-size:11px;text-transform:uppercase;color:var(--text-sec);letter-spacing:.6px;font-weight:600;border-bottom:2px solid var(--border-strong)}
td{padding:10px 14px;border-bottom:1px solid var(--border);font-size:13px;vertical-align:top}
table.details th{width:200px;text-transform:none;font-size:12px;letter-spacing:0;border-bottom:1px solid var(--border)}
.center{text-align:center}.td-pass{color:var(--clr-pass);font-weight:600}.td-fail{color:var(--clr-fail);font-weight:600}.td-skip{color:var(--clr-skip);font-weight:600}
.text-muted{color:var(--text-muted)}
a{color:var(--clr-brand);text-decoration:none}a:hover{text-decoration:underline}
.badge{padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;display:inline-block;white-space:nowrap;text-transform:uppercase;letter-spacing:.3px}
.badge-pass{background:var(--badge-pass-bg);color:var(--badge-pass-fg)}.badge-fail{background:var(--badge-fail-bg);color:var(--badge-fail-fg)}
.badge-skip{background:var(--badge-skip-bg);color:var(--badge-skip-fg)}.badge-run{background:var(--badge-run-bg);color:var(--badge-run-fg)}
.chip{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600;background:var(--bg-panel);color:var(--text-sec);border:1px solid var(--border);margin-right:4px}
.chip.exec{background:#ede9fe;color:#5b21b6;border-color:#ddd6fe}.chip.verify{background:#e0f2fe;color:#075985;border-color:#bae6fd}.chip.test{background:#fce7f3;color:#9d174d;border-color:#fbcfe8}
.progress-bar{background:var(--border);border-radius:8px;height:18px;overflow:hidden;min-width:80px}
.progress-fill{height:100%;color:#fff;font-size:10px;font-weight:600;display:flex;align-items:center;justify-content:center;min-width:32px}
.stage{border:1px solid var(--border);border-radius:8px;margin-bottom:12px;overflow:hidden}
.stage.fail{border-left:4px solid var(--clr-fail)}.stage.pass{border-left:4px solid var(--clr-pass)}.stage.skip{border-left:4px solid var(--clr-skip)}.stage.run{border-left:4px solid var(--clr-run)}
.stage-header{display:flex;align-items:center;gap:10px;padding:12px 16px;background:var(--bg-panel);cursor:pointer;flex-wrap:wrap}
.stage-header .title{font-size:15px;font-weight:700}
.stage-desc{font-size:12px;color:var(--text-sec);width:100%;padding-left:22px}
.stats{display:flex;gap:12px;margin-left:auto;font-size:12px;flex-wrap:wrap}
.arrow{font-size:10px;color:var(--text-sec);width:12px;display:inline-block}
.stage-body{padding:10px 16px 14px}
.phase{margin:10px 0 4px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text-sec);border-bottom:1px solid var(--border);padding-bottom:4px}
.phase span{font-weight:400;text-transform:none;letter-spacing:0;margin-left:8px}
.step{margin:8px 0 8px 8px;border-left:3px solid var(--border);padding-left:10px}
.step.fail{border-left-color:var(--clr-fail)}.step.pass{border-left-color:var(--clr-pass)}.step.skip{border-left-color:var(--clr-skip)}
.step-header{cursor:pointer;padding:8px 10px;background:var(--bg-panel);border-radius:4px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.step-header .name{font-size:13px;font-weight:600}
.step-body{padding:8px 4px}
.check{display:flex;gap:8px;align-items:flex-start;padding:6px 10px;margin:4px 0 4px 8px;font-size:13px;border-bottom:1px solid var(--border)}
.check .detail{color:var(--text-sec);font-size:12px}
.cmd{font-family:'Cascadia Code','Fira Code',Consolas,monospace;font-size:12px;background:var(--bg-panel);padding:6px 10px;border-radius:4px;margin:4px 0;word-break:break-all}
.note{font-size:12px;color:var(--text-sec);margin:4px 0}
tr.test-row{cursor:pointer}tr.test-row:hover{background:var(--bg-panel)}
tr.test-row.fail{border-left:3px solid var(--clr-fail)}tr.test-row.pass{border-left:3px solid var(--clr-pass)}tr.test-row.skip{border-left:3px solid var(--clr-skip)}
.log-row td{padding:0}
.log-content{background:var(--log-bg);color:var(--log-fg);padding:12px 16px;font-family:'Cascadia Code','Fira Code',Consolas,monospace;font-size:12px;max-height:360px;overflow:auto}
.log-pre{background:var(--log-bg);color:var(--log-fg);padding:12px 16px;border-radius:6px;font-family:'Cascadia Code','Fira Code',Consolas,monospace;font-size:11px;white-space:pre-wrap;word-break:break-word;max-height:480px;overflow:auto;margin:6px 0}
.error-block{background:var(--err-bg);color:var(--err-fg);border:1px solid var(--err-border);border-radius:6px;padding:10px 14px;margin:6px 0;font-family:'Cascadia Code','Fira Code',Consolas,monospace;font-size:11px;white-space:pre-wrap;word-break:break-word;max-height:240px;overflow:auto}
details.output{margin:6px 0}details.output>summary{cursor:pointer;font-size:12px;font-weight:600;color:var(--clr-brand)}
.log-link{color:var(--clr-brand);font-size:12px;font-weight:600;text-decoration:underline}
.filter-btn{padding:5px 12px;border:1px solid var(--border-strong);border-radius:8px;background:var(--bg-card);color:var(--text-sec);font-size:11px;cursor:pointer;font-weight:600;text-transform:uppercase}
.filter-btn.active{background:var(--clr-brand);color:#fff;border-color:var(--clr-brand)}
.search-box{padding:7px 14px;border:1px solid var(--border-strong);border-radius:8px;font-size:13px;width:220px;background:var(--bg-card);color:var(--text)}
.footer{text-align:center;padding:18px;color:var(--text-muted);font-size:11px}
@media print{.theme-toggle,.filter-btn,.search-box{display:none}.stage-body,.step-body{display:block!important}}
"""

SCRIPT = """
function toggleTheme(){var h=document.documentElement,n=h.getAttribute('data-theme')==='dark'?'light':'dark';h.setAttribute('data-theme',n);try{localStorage.setItem('omnia-svt-report-theme',n)}catch(e){}}
(function(){try{var s=localStorage.getItem('omnia-svt-report-theme');if(s)document.documentElement.setAttribute('data-theme',s)}catch(e){}})();
function toggle(id){var el=document.getElementById(id),a=document.getElementById('arrow-'+id);if(!el)return;var open=el.style.display==='none';el.style.display=open?'':'none';if(a)a.innerHTML=open?'&#9660;':'&#9654;'}
function toggleLog(id){var el=document.getElementById(id);if(el)el.style.display=el.style.display==='none'?'table-row':'none'}
function openStage(id){var el=document.getElementById(id);if(el&&el.style.display==='none')toggle(id);var s=document.getElementById('card-'+id);if(s)s.scrollIntoView({behavior:'smooth',block:'start'})}
function setAll(open){document.querySelectorAll('.stage-body,.step-body').forEach(function(el){if((el.style.display==='none')===open)toggle(el.id)})}
function filterBy(status,btn){document.querySelectorAll('.filter-btn').forEach(function(b){b.classList.toggle('active',b.getAttribute('data-status')===status)});
document.querySelectorAll('.step').forEach(function(s){s.style.display=(status==='all'||s.getAttribute('data-status')===status||s.querySelector('tr.test-row.'+status))?'':'none'});
document.querySelectorAll('tr.test-row').forEach(function(r){r.style.display=(status==='all'||r.classList.contains(status))?'':'none'});
document.querySelectorAll('tr.log-row').forEach(function(r){r.style.display='none'});
if(status!=='all')setAll(true)}
function search(){var q=document.getElementById('searchBox').value.toLowerCase();document.querySelectorAll('.step,.check').forEach(function(s){s.style.display=s.textContent.toLowerCase().indexOf(q)>=0?'':'none'});if(q)setAll(true)}
"""


def _e(value: Any) -> str:
    """Escape for HTML after masking secrets and IPs.

    omnia_auto's redaction is quadratic on one long run of word characters
    (20k characters: ~25 s), so such runs (hashes, encoded blobs) are broken
    into lines of LONG_WORD characters first; ordinary output is unchanged.
    """
    text = LONG_WORD_RE.sub(lambda match: "\n".join(
        match.group(0)[start:start + LONG_WORD]
        for start in range(0, len(match.group(0)), LONG_WORD)),
        str(value if value is not None else ""))
    return html.escape(redact(text))


def _badge(status: str) -> str:
    return f'<span class="badge badge-{BADGE.get(status, "skip")}">{html.escape(status)}</span>'


def _counts(results: List[Dict[str, Any]]) -> Dict[str, int]:
    return {state: sum(1 for item in results if item.get("status") == state)
            for state in ("Passed", "Failed", "Skipped")}


def _rate(counts: Dict[str, int]) -> float:
    executed = counts["Passed"] + counts["Failed"]
    return round(counts["Passed"] / executed * 100, 1) if executed else 0.0


def _bar(rate: float, any_run: bool) -> str:
    if not any_run:
        return '<span class="text-muted">&mdash;</span>'
    color = ("var(--clr-pass)" if rate >= 90 else "var(--clr-skip)" if rate >= 70
             else "var(--clr-fail)")
    return (f'<div class="progress-bar"><div class="progress-fill" '
            f'style="width:{rate}%;background:{color}">{rate}%</div></div>')


def combined_status(states: List[str]) -> str:
    """Return Running, Failed, Passed or Skipped for a list of section/item states."""
    if RUNNING in states:
        return RUNNING
    if "Failed" in states:
        return "Failed"
    return "Passed" if "Passed" in states else "Skipped"


# ------------------------------------------------------------------ groups
def group_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return the stages of the report in run order.

    The setup phases (cleanup, install) belong to Initialization, which is the
    first stage of every theme; a stage run again in the same run is its own
    stage (``build_deploy (2)``).
    """
    groups: List[Dict[str, Any]] = []
    current = None  # the Initialization stage that still takes phases
    runs = 0
    for section in sections:
        stage = section.get("stage") or section["name"].split(" (")[0]
        if stage in INITIALIZATION_PHASES or stage == FIRST_STAGE:
            if current is None:
                runs += 1
                current = {"stage": FIRST_STAGE, "suffix": f" ({runs})" if runs > 1 else "",
                           "sections": []}
                groups.append(current)
            current["sections"].append(section)
            if stage == FIRST_STAGE:
                current = None
            continue
        current = None
        groups.append({"stage": stage, "suffix": section["name"][len(stage):],
                       "sections": [section]})
    for group in groups:
        items = [item for section in group["sections"] for item in section.get("items", [])]
        results = [result for item in items for result in item.get("results") or []]
        group.update(
            items=items, results=results,
            status=combined_status([section.get("status", "") for section in group["sections"]]),
            duration=sum(float(section.get("duration") or 0) for section in group["sections"]),
            started_at=group["sections"][0].get("started_at", ""),
            attempt=max(int(section.get("attempt") or 1) for section in group["sections"]))
    return groups


# -------------------------------------------------------------------- parts
def _header(meta: Dict[str, Any]) -> str:
    title = meta.get("theme_title") or meta.get("theme", "")
    updated = meta.get("updated_at") or datetime.now().isoformat(timespec="seconds")
    return (f'<div class="header"><div><h1>Omnia System Verification Report</h1>'
            f'<div class="theme-name">{_e(title)}</div>'
            f'<div class="subtitle">Theme <strong>{_e(meta.get("theme", ""))}</strong> &middot; '
            f'{_e(meta.get("description", ""))}</div></div>'
            f'<div class="header-right"><div class="header-meta">'
            f'<span><strong>Run:</strong> {_e(meta.get("run_id", ""))}</span>'
            f'<span><strong>OIM:</strong> {_e(meta.get("oim", ""))}</span>'
            f'<span><strong>Commit:</strong> {_e(meta.get("commit", ""))}</span>'
            f'<span><strong>Updated:</strong> {_e(updated)}</span></div>'
            f'<button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme"></button>'
            f"</div></div>")


def _banner(meta: Dict[str, Any], groups: List[Dict[str, Any]]) -> str:
    planned = list(meta.get("stages") or [])
    done = {group["stage"] for group in groups}
    status = combined_status([group["status"] for group in groups]) if groups else "Skipped"
    label = {"Passed": "PASSED", "Failed": "FAILED", RUNNING: "RUNNING"}.get(status, "NOT STARTED")
    progress = (f"{len([stage for stage in planned if stage in done])} of {len(planned)} stages "
                f"run" if planned else "")
    state = meta.get("state", "")
    detail = " &middot; ".join(part for part in (_e(progress), _e(f"Run state: {state}")
                                                 if state else "") if part)
    if status == "Passed" and planned and not set(planned) <= done:
        label = "PASSED SO FAR"
    return (f'<div class="banner {BADGE.get(status, "skip")}">OVERALL STATUS: {label}'
            f"<small>{detail}</small></div>")


def _cards(groups: List[Dict[str, Any]], meta: Dict[str, Any]) -> str:
    items = [item for group in groups for item in group["items"]]
    steps = _counts(items)
    duration = format_duration(sum(group["duration"] for group in groups))
    planned = len(meta.get("stages") or []) or len(groups)
    return (
        '<div class="cards">'
        f'<div class="card"><div class="label">Stages</div><div class="value">{len(groups)}</div>'
        f'<div class="sub">of {planned} planned</div></div>'
        f'<div class="card"><div class="label">SVT Steps</div><div class="value">{len(items)}</div>'
        f'<div class="sub">setup phases and stage tests</div></div>'
        f'<div class="card passed clickable" onclick="filterBy(\'pass\')"><div class="label">Passed</div>'
        f'<div class="value">{steps["Passed"]}</div></div>'
        f'<div class="card failed clickable" onclick="filterBy(\'fail\')"><div class="label">Failed</div>'
        f'<div class="value">{steps["Failed"]}</div></div>'
        f'<div class="card skipped clickable" onclick="filterBy(\'skip\')"><div class="label">Skipped</div>'
        f'<div class="value">{steps["Skipped"]}</div></div>'
        f'<div class="card rate"><div class="label">Pass Rate</div><div class="value">{_rate(steps)}%</div></div>'
        f'<div class="card duration"><div class="label">Duration</div><div class="value">{duration}</div></div>'
        "</div>")


class _Html(str):
    """Text that is already HTML (a link); everything else is escaped."""


def _web_base(clone_url: str) -> str:
    """Return the https web address of a clone URL (https, ssh:// or git@host:path), or ""."""
    match = (re.fullmatch(r"https?://([^/\s]+)/(.+?)(?:\.git)?/?", clone_url)
             or re.fullmatch(r"(?:ssh://)?[\w.-]+@([^/:\s]+)[:/](.+?)(?:\.git)?/?", clone_url))
    return f"https://{match.group(1)}/{match.group(2)}" if match else ""


def _link(url: str, text: str) -> str:
    """Return a link, or the plain masked text when the address holds something masked (an IP)."""
    if not url or redact(url) != url:
        return _e(text)
    return (f'<a href="{html.escape(url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{_e(text)}</a>')


def _repo_rows(meta: Dict[str, Any]) -> tuple:
    """Return the Run Details rows of the repository, branch and commit (links when known)."""
    clone, branch = str(meta.get("repo_url") or ""), str(meta.get("branch") or "")
    commit, full = str(meta.get("commit") or ""), str(meta.get("commit_full") or "")
    base = _web_base(clone)
    marker = "/-" if "gitlab" in base else ""
    return (
        ("Git Clone URL", _Html(_link(base, clone)) if clone else "-"),
        ("Branch", _Html(_link(f"{base}{marker}/tree/{quote(branch, safe='/')}", branch)
                         if base else _e(branch)) if branch else "- (detached HEAD)"),
        ("Commit", _Html(_link(f"{base}{marker}/commit/{full}", commit) if base and full
                         else _e(commit)) if commit else "-"))


def _run_panel(meta: Dict[str, Any]) -> str:
    rows = (("Theme", f'{meta.get("theme_title", "")} ({meta.get("theme", "")})'),
            ("Description", meta.get("description")), ("Run ID", meta.get("run_id")),
            ("Run State", meta.get("state")), ("Started", meta.get("started_at")),
            ("Last Updated", meta.get("updated_at")),
            ("Previous Run", meta.get("previous_run") or "-"), *_repo_rows(meta),
            ("OIM", meta.get("oim")),
            ("Stages", " → ".join(stage_info(meta.get("theme", ""), stage)[0]
                                  for stage in meta.get("stages") or [])))
    body = "".join(f"<tr><th>{html.escape(label)}</th>"
                   f"<td>{value if isinstance(value, _Html) else _e(value)}</td></tr>"
                   for label, value in rows)
    return (f'<div class="panel"><div class="panel-header"><h2>Run Details</h2></div>'
            f'<table class="details">{body}</table></div>')


def _heading(theme: str, group: Dict[str, Any], number: int) -> str:
    attempt = f" (attempt {group['attempt']})" if group.get("attempt", 1) > 1 else ""
    return f"Stage {number}: {stage_info(theme, group['stage'])[0]}{group['suffix']}{attempt}"


def _attempts_note(section: Dict[str, Any]) -> str:
    """Return the earlier attempts of a section (a retry replaced them) as a note."""
    lines = []
    for old in section.get("attempts") or []:
        failed = f"; failed: {', '.join(old['failed'])}" if old.get("failed") else ""
        lines.append(f"attempt {old.get('attempt', '?')}: {old.get('status', '')}, "
                     f"{old.get('steps', 0)} steps, {format_duration(old.get('duration') or 0)}, "
                     f"started {old.get('started_at', '')}{failed}")
    return ('<div class="note">Earlier attempts (replaced by a retry): '
            f'{_e(" | ".join(lines))}</div>') if lines else ""


def _overview(theme: str, groups: List[Dict[str, Any]], planned: List[str]) -> str:
    rows = ""
    for number, group in enumerate(groups, 1):
        steps = _counts(group["items"])
        rows += (f'<tr><td><a href="#card-stage-{number}" onclick="openStage(\'stage-{number}\')">'
                 f'{_e(_heading(theme, group, number))}</a></td>'
                 f'<td class="center">{_badge(group["status"])}</td>'
                 f'<td class="center">{len(group["items"])}</td>'
                 f'<td class="center td-pass">{steps["Passed"]}</td>'
                 f'<td class="center td-fail">{steps["Failed"]}</td>'
                 f'<td class="center td-skip">{steps["Skipped"]}</td>'
                 f'<td>{_bar(_rate(steps), bool(steps["Passed"] + steps["Failed"]))}</td>'
                 f'<td class="center">{format_duration(group["duration"])}</td>'
                 f'<td>{_e(group["started_at"])}</td></tr>')
    done = {group["stage"] for group in groups}
    for stage in planned:
        if stage not in done:
            rows += (f'<tr><td class="text-muted">{_e(stage_info(theme, stage)[0])}</td>'
                     f'<td class="center"><span class="text-muted">not run</span></td>'
                     + '<td class="center text-muted">&mdash;</td>' * 6 + "<td></td></tr>")
    return ('<div class="panel"><div class="panel-header"><h2>Stage Overview</h2></div><table>'
            '<thead><tr><th>Stage</th><th class="center">Status</th>'
            '<th class="center">SVT Steps</th>'
            '<th class="center">Passed</th><th class="center">Failed</th><th class="center">Skipped</th>'
            '<th>Pass Rate</th><th class="center">Duration</th><th>Started</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>")


class _Ids:  # pylint: disable=too-few-public-methods
    """Unique element ids within one page."""

    def __init__(self) -> None:
        self.count = 0

    def next(self, prefix: str) -> str:
        """Return a new id with ``prefix``."""
        self.count += 1
        return f"{prefix}-{self.count}"


def _results_table(results: List[Dict[str, Any]], ids: _Ids) -> str:
    """The FVT results of one step, the same rows as the omnia_auto FVT report."""
    rows = ""
    for result in results:
        css = BADGE.get(result.get("status", ""), "fail")
        detail = result.get("details") or ""
        if result.get("reason") and result.get("reason") not in detail:
            detail = f"{detail}\nSKIPPED: {result['reason']}".strip()
        has_log = bool(detail or result.get("error"))
        log_id = ids.next("log")
        tc_id = f"[{_e(result['tc_id'])}] " if result.get("tc_id") else ""
        module = (f' <span class="chip">{_e(result["module"])}</span>'
                  if result.get("module") else "")
        rows += (f'<tr class="test-row {css}"' + (f' onclick="toggleLog(\'{log_id}\')"' if has_log else "")
                 + f'><td>{tc_id}{_e(result.get("name", ""))}{module}</td>'
                 f'<td class="center">{_badge(result.get("status", ""))}</td>'
                 f'<td class="center">{float(result.get("duration") or 0):.2f}s</td>'
                 f'<td class="center">'
                 + ('<span class="log-link">View</span>' if has_log
                    else '<span class="text-muted">&mdash;</span>') + "</td></tr>")
        if has_log:
            parts = f'<pre class="log-pre">{_e(detail)}</pre>' if detail else ""
            if result.get("error"):
                parts += f'<div class="error-block"><strong>Error:</strong>\n{_e(result["error"])}</div>'
            rows += (f'<tr class="log-row" id="{log_id}" style="display:none;">'
                     f'<td colspan="4"><div class="log-content">{parts}</div></td></tr>')
    if not rows:
        return ""
    return ('<table><thead><tr><th>FVT Test</th><th class="center">Status</th>'
            '<th class="center">Duration</th><th class="center">Logs</th></tr></thead>'
            f"<tbody>{rows}</tbody></table>")


def _step(item: Dict[str, Any], ids: _Ids) -> str:
    """One SVT step: header with its FVT step, then results and screen output."""
    status = item.get("status", "")
    css = BADGE.get(status, "skip")
    results = item.get("results") or []
    counts = _counts(results)
    fvt = item.get("fvt") or {}
    chips = ""
    if fvt:
        action = str(fvt.get("action", ""))
        chips = (f'<span class="chip">{_e(fvt.get("suite", ""))}</span>'
                 f'<span class="chip">{_e(fvt.get("tag", ""))}</span>'
                 f'<span class="chip {html.escape(action)}">{_e(action.upper())}</span>'
                 + (f'<span class="chip">{_e(fvt["options"])}</span>' if fvt.get("options") else ""))
    if not (item.get("command") or item.get("output") or results or item.get("error")):
        detail = f'<div class="detail">{_e(item.get("note", ""))}</div>' if item.get("note") else ""
        return (f'<div class="check" data-status="{css}">{_badge(status)}'
                f'<div><div>{_e(item.get("name", ""))}</div>{detail}</div></div>')
    body_id = ids.next("step")
    opened = "" if status == "Failed" else ' style="display:none;"'
    title = f"{item['id']} - {item['name']}" if item.get("id") else item.get("name", "")
    stats = (f'<span class="stats"><span class="text-muted">FVT tests:</span>'
             f'<span class="td-pass">{counts["Passed"]} passed</span>'
             f'<span class="td-fail">{counts["Failed"]} failed</span>'
             f'<span class="td-skip">{counts["Skipped"]} skipped</span>'
             f'<span class="text-muted">{format_duration(item.get("duration") or 0)}</span></span>')
    parts = []
    if item.get("command"):
        parts.append(f'<div class="cmd">$ {_e(item["command"])}</div>')
    if item.get("note") and item.get("note") != item.get("command"):
        parts.append(f'<div class="note">{_e(item["note"])}</div>')
    if item.get("error"):
        parts.append(f'<div class="error-block"><strong>Error:</strong> {_e(item["error"])}</div>')
    parts.append(_results_table(results, ids))
    if item.get("output"):
        output = item["output"]
        cut = len(output) - HTML_OUTPUT_CHARS
        note = (f'<div class="note">Last {HTML_OUTPUT_CHARS} of {len(output)} characters; the '
                "complete output is in the stage or setup log of the run folder.</div>"
                if cut > 0 else "")
        parts.append(f'<details class="output"{" open" if status == "Failed" else ""}>'
                     f'<summary>Screen Output ({len(output)} characters)</summary>{note}'
                     f'<pre class="log-pre">{_e(output[-HTML_OUTPUT_CHARS:])}</pre></details>')
    arrow = "&#9660;" if status == "Failed" else "&#9654;"
    return (f'<div class="step {css}" data-status="{css}">'
            f'<div class="step-header" onclick="toggle(\'{body_id}\')">'
            f'<span class="arrow" id="arrow-{body_id}">{arrow}</span>{_badge(status)}'
            f'<span class="name">{_e(title)}</span>{chips}{stats}</div>'
            f'<div class="step-body" id="{body_id}"{opened}>{"".join(parts)}</div></div>')


def _rows_table(rows: List[Dict[str, Any]], columns: List[str] = None) -> str:
    """A plain table of product state rows (stage outputs, summary state)."""
    columns = columns or list(rows[0]) if rows else (columns or [])
    head = "".join(f"<th>{_e(column.replace('_', ' '))}</th>" for column in columns)
    body = "".join("<tr>" + "".join(f"<td>{_e(row.get(column, ''))}</td>" for column in columns)
                   + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _state_panel(state: Dict[str, Any]) -> str:
    """What this run left in the product (summary; report only)."""
    if not state:
        return ""
    columns = list(state.get("columns") or [])
    leftover = state.get("leftover") or []
    parts = [f'<div class="note">{len(state.get("rows") or [])} created in this run '
             f'(of {state.get("total", 0)}); {len(leftover)} left in a status a run should '
             "not leave behind. Reported only: it does not fail the run.</div>"]
    if leftover:
        parts.append(f"<p><strong>Left behind</strong></p>{_rows_table(leftover, columns)}")
    if state.get("rows"):
        parts.append(f'<details class="output"><summary>Created in this run '
                     f'({len(state["rows"])})</summary>{_rows_table(state["rows"], columns)}'
                     "</details>")
    return (f'<div class="panel"><div class="panel-header"><h2>Product State at Summary: '
            f'{_e(state.get("label", ""))}</h2></div><div style="padding:12px 16px;">'
            f'{"".join(parts)}</div></div>')


def _stage(theme: str, group: Dict[str, Any], number: int, ids: _Ids) -> str:
    """One stage block; Initialization lists its phases (Cleanup, Install, Readiness)."""
    stage_id = f"stage-{number}"
    status = group["status"]
    counts = _counts(group["items"])
    opened = status in ("Failed", RUNNING)
    body = ""
    phased = len(group["sections"]) > 1 or group["stage"] == FIRST_STAGE
    for section in group["sections"]:
        name = section.get("stage") or section["name"].split(" (")[0]
        if phased:
            phase = "readiness" if name == FIRST_STAGE else name
            title, desc = stage_info(theme, phase)
            suffix = section["name"][len(name):]
            body += (f'<div class="phase">{_e(title + suffix)} {_badge(section.get("status", ""))}'
                     f'<span>{_e(desc)} &middot; {format_duration(section.get("duration") or 0)}'
                     f"</span></div>")
        body += _attempts_note(section)
        body += "".join(_step(item, ids) for item in section.get("items", [])) or (
            '<div class="note">No step recorded yet.</div>')
    outputs = [row for section in group["sections"] for row in section.get("outputs") or []]
    if outputs:
        body = (f'<div class="phase">Stage outputs<span>product rows this stage created or '
                f"changed</span></div>{_rows_table(outputs)}") + body
    description = stage_info(theme, group["stage"])[1]
    hidden = "" if opened else ' style="display:none;"'
    return (f'<div class="stage {BADGE.get(status, "skip")}" id="card-{stage_id}">'
            f'<div class="stage-header" onclick="toggle(\'{stage_id}\')">'
            f'<span class="arrow" id="arrow-{stage_id}">{"&#9660;" if opened else "&#9654;"}</span>'
            f'<span class="title">{_e(_heading(theme, group, number))}</span>{_badge(status)}'
            f'<span class="stats"><span>{len(group["items"])} steps</span>'
            f'<span class="td-pass">{counts["Passed"]} passed</span>'
            f'<span class="td-fail">{counts["Failed"]} failed</span>'
            f'<span class="td-skip">{counts["Skipped"]} skipped</span>'
            f'<span class="text-muted">{format_duration(group["duration"])}</span></span>'
            f'<div class="stage-desc">{_e(description)}</div></div>'
            f'<div class="stage-body" id="{stage_id}"{hidden}>'
            f"{body}</div></div>")


def render_html(report: Dict[str, Any]) -> str:
    """Return the HTML page of an SVT report (see the module doc for the layout)."""
    meta, sections = report.get("meta") or {}, report.get("sections") or []
    theme = str(meta.get("theme", ""))
    groups = group_sections(sections)
    ids = _Ids()
    stages = "".join(_stage(theme, group, number, ids) for number, group in enumerate(groups, 1))
    title = (f"Omnia SVT Report - {meta.get('theme_title') or theme} - "
             f"{meta.get('run_id', '')}")
    controls = (
        '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">'
        '<input type="text" class="search-box" id="searchBox" placeholder="Search steps and tests..." '
        'onkeyup="search()">'
        + "".join(f'<button class="filter-btn{" active" if key == "all" else ""}" data-status="{key}" '
                  f'onclick="filterBy(\'{key}\',this)">{label}</button>'
                  for key, label in (("all", "All"), ("pass", "Pass"), ("fail", "Fail"),
                                     ("skip", "Skip")))
        + '<button class="filter-btn" onclick="setAll(true)">Expand all</button>'
          '<button class="filter-btn" onclick="setAll(false)">Collapse all</button></div>')
    return (
        f'<!DOCTYPE html><html lang="en" data-theme="light"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<title>{_e(title)}</title><style>{CSS}</style></head><body>"
        f"{_header(meta)}{_banner(meta, groups)}<div class=\"container\">"
        f"{_cards(groups, meta)}{_run_panel(meta)}"
        f"{_overview(theme, groups, list(meta.get('stages') or []))}"
        f"{_state_panel(report.get('state') or {})}"
        f'<div class="panel"><div class="panel-header"><h2>Stage Details</h2>{controls}</div>'
        f'<div style="padding:16px;">{stages or "<p class=text-muted>No stage has run yet.</p>"}'
        f"</div></div></div>"
        f'<div class="footer">Omnia System Verification &middot; {_e(meta.get("theme_title") or theme)}'
        f" &middot; generated {_e(meta.get('updated_at', ''))}</div>"
        f"<script>{SCRIPT}</script></body></html>\n")
