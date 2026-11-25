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

"""The one report of an SVT cluster pipeline (standard library only).

``build_report`` returns ONE self-contained HTML file: an overview page that explains the
run (verdict, what every step did, what failed and what to do next, how to read the report),
then one page per theme that holds that theme's own SVT report. A top bar with
Previous / Next buttons, a tab per page, the arrow keys and the address hash (``#build_stream``)
move between the pages; no network, script file or style file is needed to open it.
"""

import html
import re
from typing import Any, Dict, List, Tuple

STAGE_TEXT = {
    "cleanup": "The previous installation removed: each suite's cleanup tests, then "
               "omnia.sh --cleanup.",
    "install": "omnia.sh -s: the Omnia venv, every domain-init, the catalog; then the test "
               "requirements.",
    "initialization": "Readiness checks: inputs configured, Omnia installed, test "
                      "requirements and every credential store present.",
    "prepare_build_stream": "Base domains (repo_manager, image_build_manager, orchestrator), "
                            "then BuildStream, Postgres, GitLab and the playbook watcher.",
    "build_deploy": "A real image build and deploy through the BuildStream pipelines.",
    "cadence": "A cadence cycle: the scheduled rebuild of the image groups.",
    "automatic_cleanup": "The automated cleanup pass of old images and pipelines.",
    "summary": "The run printed and its report rendered.",
}
CATALOG_TEXT = ("Select the catalog (./omnia.sh --select-catalog), then the repo_manager and "
                "image_build_manager steps: exec, then verify.")
JOB_TEXT = {
    "preflight": ("Preflight",
                  "Checks before anything is changed: SSH to the OIM, OpenBao reachable, the "
                  "Omnia checkout (clone, update or recreate) and the project inputs copied "
                  "to the OIM."),
    "initialization": ("Initialization",
                       "One shared clean start for every theme: cleanup of the previous "
                       "installation (every domain and the NFS shares), omnia.sh installation "
                       "with the Omnia environment, the credentials from OpenBao and the "
                       "readiness checks."),
    "summary": ("Summary",
                "Collects the result of every theme, builds this report and the email, and "
                "fails the pipeline when anything failed."),
}
STATUS_WORDS = {"passed": "ok", "success": "ok", "failed": "bad", "canceled": "bad",
                "skipped": "warn", "running": "run", "manual": "warn"}


def esc(value: Any) -> str:
    """Return ``value`` as escaped text."""
    return html.escape(str(value if value is not None else ""))


def _tone(status: str) -> str:
    return STATUS_WORDS.get(str(status).lower(), "none")


def duration_text(seconds: Any) -> str:
    """Return 3725 as ``1h 02m``, 61 as ``1m 01s`` and unknown values as an empty text."""
    try:
        total = int(round(float(seconds)))
    except (TypeError, ValueError):
        return ""
    if total <= 0:
        return "<1s"
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def pill(status: str, label: str = "") -> str:
    """Return a coloured status pill."""
    text = label or {"success": "passed"}.get(str(status).lower(), str(status) or "not run")
    return f'<span class="pill {_tone(status)}">{esc(text.upper())}</span>'


def stage_description(name: str) -> str:
    """Return what a report section (stage) does."""
    if name.startswith("catalog_"):
        return CATALOG_TEXT
    return STAGE_TEXT.get(name, "")


def stage_rows(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return one row per section of an SVT report: name, status, duration, steps, tests."""
    rows = []
    for section in report.get("sections") or []:
        items = section.get("items") or []
        tests = [r for item in items for r in item.get("results") or []]

        def count(entries: List[Dict[str, Any]], wanted: str) -> int:
            return sum(1 for entry in entries if str(entry.get("status")) == wanted)

        failed = [item for item in items if item.get("status") == "Failed"]
        rows.append({
            "name": str(section.get("name", "")), "status": str(section.get("status", "")),
            "kind": str(section.get("kind", "")), "duration": section.get("duration"),
            "steps": len(items), "steps_failed": count(items, "Failed"),
            "passed": count(tests, "Passed"), "failed": count(tests, "Failed"),
            "skipped": count(tests, "Skipped"), "tests": len(tests),
            "failures": [(str(item.get("name", "")), str(item.get("error") or "").strip())
                         for item in failed][:6]})
    return rows


def totals(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """Return the sums over stage rows."""
    keys = ("steps", "steps_failed", "passed", "failed", "skipped", "tests")
    result: Dict[str, float] = {key: sum(row[key] for row in rows) for key in keys}
    result["stages"] = len(rows)
    result["stages_failed"] = sum(1 for row in rows if row["status"] == "Failed")
    result["stages_passed"] = sum(1 for row in rows if row["status"] == "Passed")
    result["seconds"] = sum(float(row["duration"] or 0) for row in rows)
    return result


def _segments(rows: List[Dict[str, Any]]) -> str:
    """Return the thin stage bar: one coloured segment per stage."""
    if not rows:
        return '<div class="seg"><i class="none" style="flex:1"></i></div>'
    cells = "".join(
        f'<i class="{_tone(row["status"])}" title="{esc(row["name"])}: {esc(row["status"])}"'
        ' style="flex:1"></i>' for row in rows)
    return f'<div class="seg">{cells}</div>'


def _link(url: str, text: str, klass: str = "") -> str:
    if not url:
        return esc(text)
    return (f'<a class="{klass}" href="{esc(url)}" target="_blank" rel="noopener">'
            f'{esc(text)}</a>')


def _tile(value: Any, label: str, note: str = "", tone: str = "") -> str:
    return (f'<div class="tile {tone}"><div class="num">{esc(value)}</div>'
            f'<div class="lbl">{esc(label)}</div><div class="note">{esc(note)}</div></div>')


def _flow(ctx: Dict[str, Any]) -> str:
    """Return the step by step story of the run: preflight, initialization, themes, summary."""
    common = {job["name"]: job for job in ctx.get("common") or []}
    steps: List[Tuple[str, str, str, str, str, str]] = []
    for name in ("preflight", "initialization"):
        job = common.get(name) or {}
        title, text = JOB_TEXT[name]
        steps.append((title, text, job.get("status", ""), duration_text(job.get("duration")),
                      job.get("url", ""), job.get("reason", "")))
    for index, theme in enumerate(ctx["themes"]):
        rows = stage_rows(theme.get("report") or {})
        first = index == 0
        how = ("It starts directly with its first stage: the initialization already cleaned "
               "and installed." if first else
               "It starts a new run on the same installation (no new cleanup) and goes "
               "straight to its first stage.")
        steps.append((f"Theme {index + 1}: {theme['title']}",
                      f"{(theme.get('description') or '').rstrip('. ')}. {how}".lstrip(". "),
                      {"PASSED": "success", "FAILED": "failed"}.get(theme.get("verdict", ""), ""),
                      duration_text(totals(rows)["seconds"]), theme.get("pipeline_url", ""),
                      "; ".join(theme.get("problems") or [])))
    job = common.get("summary") or {}
    title, text = JOB_TEXT["summary"]
    steps.append((title, text, "success" if ctx["verdict"] == "PASSED" else "failed",
                  duration_text(job.get("duration")), job.get("url", ""), ""))
    out = []
    for number, (title, text, status, took, url, reason) in enumerate(steps, 1):
        tone = _tone(status)
        out.append(
            f'<li class="step {tone}"><span class="dot">{number}</span><div class="sb">'
            f'<div class="st"><b>{esc(title)}</b> {pill(status)}'
            f'{f" <span class=took>{esc(took)}</span>" if took else ""}'
            f'</div><div class="sx">{esc(text)}</div>'
            + (f'<div class="sr">{esc(reason)}</div>' if reason and tone == "bad" else "")
            + (f'<div class="sl">{_link(url, "Open in GitLab")}</div>' if url else "")
            + "</div></li>")
    return f'<ol class="flow">{"".join(out)}</ol>'


def _theme_card(index: int, theme: Dict[str, Any], page: int) -> str:
    rows = stage_rows(theme.get("report") or {})
    total = totals(rows)
    verdict = theme.get("verdict") or "NOT RUN"
    tone = {"PASSED": "ok", "FAILED": "bad"}.get(verdict, "none")
    failed_rows = [row for row in rows if row["status"] == "Failed"]
    why = ""
    for row in failed_rows[:4]:
        lines = "".join(f"<li><b>{esc(name)}</b>{': ' + esc(err[:160]) if err else ''}</li>"
                        for name, err in row["failures"])
        why += (f'<div class="why"><b>{esc(row["name"])}</b> failed'
                f'{f"<ul>{lines}</ul>" if lines else ""}</div>')
    if not rows:
        reason = "; ".join(theme.get("problems") or []) or "this theme did not run"
        why = f'<div class="why">No SVT report: {esc(reason)}</div>'
    numbers = (f'<span class="ok">{int(total["passed"])} passed</span> '
               f'<span class="bad">{int(total["failed"])} failed</span> '
               f'<span class="warn">{int(total["skipped"])} skipped</span>')
    open_link = (f'<a class="btn" href="#{esc(theme["name"])}" data-go="{page}">Open the '
                 'theme report &rarr;</a>' if theme.get("page_html") else "")
    return (
        f'<div class="card {tone}"><div class="ch"><span class="idx">{index + 1}</span>'
        f'<div><div class="ct">{esc(theme["title"])}</div><div class="cs">theme '
        f'<code>{esc(theme["name"])}</code></div></div>{pill(verdict)}</div>'
        f'<p class="cd">{esc(theme.get("description") or "")}</p>{_segments(rows)}'
        f'<div class="cn">{int(total["stages_passed"])} of {int(total["stages"])} stages '
        f'passed &middot; {int(total["steps"])} steps &middot; tests: {numbers} &middot; '
        f'{esc(duration_text(total["seconds"]) or "no time recorded")}</div>{why}'
        f'<div class="ca">{open_link}'
        f'{_link(theme.get("pipeline_url", ""), "Theme pipeline", "ghost")}'
        f'<span class="run">run {esc(theme.get("run_id") or "not started")}</span></div></div>')


def _stage_table(theme: Dict[str, Any]) -> str:
    rows = stage_rows(theme.get("report") or {})
    if not rows:
        return ""
    body = ""
    for row in rows:
        text = stage_description(row["name"])
        body += (f'<tr class="{_tone(row["status"])}"><td><b>{esc(row["name"])}</b>'
                 f'<div class="mut">{esc(text)}</div></td><td>{pill(row["status"])}</td>'
                 f'<td>{row["steps"]}</td><td class="ok">{row["passed"]}</td>'
                 f'<td class="bad">{row["failed"]}</td><td class="warn">{row["skipped"]}</td>'
                 f'<td>{esc(duration_text(row["duration"]))}</td></tr>')
    return ('<table class="tbl"><thead><tr><th>Stage</th><th>Status</th><th>Steps</th>'
            '<th>Passed</th><th>Failed</th><th>Skipped</th><th>Time</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def _advice(ctx: Dict[str, Any]) -> str:
    """Return the "what went wrong, what to do" block ("" when the run passed)."""
    problems = ctx.get("problems") or []
    if not problems:
        return ""
    reasons = ctx.get("reasons") or {}
    items = ""
    for problem in problems:
        first = problem.split(" ")[0]
        if first in ("preflight", "initialization"):
            action = ("Open that job's log in GitLab: the cause is printed at its end (SSH, "
                      "OpenBao, the checkout, the cleanup, the install or a readiness "
                      "check). No theme ran after it. Fix it, then run the pipeline again.")
        elif problem.startswith("theme "):
            action = ("Open the theme page of this report: the failed stage and step are "
                      "listed there with their output. To run only the failed stage again "
                      "in the same run, use Retry on that job in the theme pipeline; the "
                      "summary and this report are made again by themselves.")
        else:
            action = "Open the job in GitLab and read the end of its log."
        extra = "".join(f'<div class="sr">{esc(reasons[job])}</div>'
                        for job in reasons if problem.startswith(f"{job} "))
        items += (f'<li><div class="pt">{esc(problem)}</div>{extra}'
                  f'<div class="pa">What to do: {esc(action)}</div></li>')
    return (f'<section class="sec"><h2>What went wrong and what to do</h2>'
            f'<ul class="adv">{items}</ul></section>')


GUIDE = (
    ("What the verdict means",
     "<b>PASSED</b>: every job of the cluster pipeline passed and every theme finished without "
     "a failed stage. <b>FAILED</b>: at least one job or stage failed; the list above says "
     "which. A failed theme never stops the next one, but a failed initialization stops them "
     "all, because nothing is installed."),
    ("How the run is built",
     "<b>Preflight</b> and <b>Initialization</b> run once. The initialization is the shared "
     "clean start: it cleans the OIM completely, installs Omnia and brings up the Omnia "
     "environment with the credentials. Every theme then runs directly on that installation, "
     "starting with its first stage; a theme after the first one only starts its own run, it "
     "does not clean again. <b>Summary</b> builds this report."),
    ("Stage, step and test",
     "A <b>stage</b> is one job of a theme (for example prepare_build_stream). A stage is made "
     "of <b>steps</b> (one command or one FVT step), and a step holds the <b>tests</b> its FVT "
     "run reported. Skipped means it was not needed or an earlier failure stopped it."),
    ("Moving through this report",
     "Use the tabs, the Previous and Next buttons or the left and right arrow keys. A page "
     "has an address (<code>#build_stream</code>), so a link to it opens that page. The moon "
     "button switches light and dark for every page."),
    ("Where the logs are",
     "Every stage's full log is in the job artifacts of the summary job "
     "(<code>svt_report/&lt;theme&gt;/logs</code>) and on the OIM under "
     "<code>test/system_test/reports/ci/&lt;pipeline id&gt;/</code>. JUnit files are in "
     "<code>svt_report/junit</code>."),
)


def _guide() -> str:
    parts = "".join(f"<details><summary>{esc(title)}</summary><p>{text}</p></details>"
                    for title, text in GUIDE)
    return f'<section class="sec"><h2>How to read this report</h2><div class="gd">{parts}</div>' \
           '</section>'


def _details(ctx: Dict[str, Any]) -> str:
    info = ctx.get("info") or {}
    rows = [("OIM / cluster", esc(ctx["label"])),
            ("Repository", _link(info.get("repo_url", ""), info.get("repo", "") or "-")),
            ("Branch", _link(info.get("branch_url", ""), info.get("branch", "") or "-")),
            ("Commit", _link(info.get("commit_url", ""), (info.get("commit") or "")[:12] or "-")),
            ("Pipeline", _link(info.get("pipeline_url", ""), info.get("pipeline_url", "") or "-")),
            ("Report made", esc(ctx.get("generated", "")))]
    body = "".join(f"<tr><th>{name}</th><td>{value}</td></tr>" for name, value in rows)
    return f'<section class="sec"><h2>Run details</h2><table class="kv">{body}</table></section>'


def _overview(ctx: Dict[str, Any]) -> str:
    themes = ctx["themes"]
    all_rows = [row for theme in themes for row in stage_rows(theme.get("report") or {})]
    total = totals(all_rows)
    passed_themes = sum(1 for theme in themes if theme.get("verdict") == "PASSED")
    ok = ctx["verdict"] == "PASSED"
    first_page = 1 if themes else 0
    tiles = "".join([
        _tile(f"{passed_themes}/{len(themes)}", "Themes passed", "one pipeline each",
              "ok" if passed_themes == len(themes) else "bad"),
        _tile(f"{int(total['stages_passed'])}/{int(total['stages'])}", "Stages passed",
              "jobs of the themes", "ok" if not total["stages_failed"] else "bad"),
        _tile(int(total["steps_failed"]), "Steps failed", f"of {int(total['steps'])} steps",
              "bad" if total["steps_failed"] else "ok"),
        _tile(int(total["passed"]), "Tests passed", f"of {int(total['tests'])} reported", "ok"),
        _tile(int(total["failed"]), "Tests failed", f"{int(total['skipped'])} skipped",
              "bad" if total["failed"] else "ok"),
        _tile(duration_text(total["seconds"]) or "-", "Time in themes", "stages added up"),
    ])
    cards = "".join(_theme_card(index, theme, index + 1) for index, theme in enumerate(themes))
    tables = "".join(f'<h3>{esc(theme["title"])}</h3>{_stage_table(theme)}'
                     for theme in themes if stage_rows(theme.get("report") or {}))
    start = (f'<a class="btn big" href="#{esc(themes[0]["name"])}" data-go="{first_page}">'
             'Start with the first theme &rarr;</a>' if themes else "")
    info = ctx.get("info") or {}
    return (
        f'<div class="hero {"ok" if ok else "bad"}"><div class="hi"><div class="eyebrow">'
        'Omnia System Verification</div>'
        f'<h1>{esc(ctx["label"])}: {esc(ctx["verdict"])}</h1>'
        f'<p>{esc(" then ".join(theme["title"] for theme in themes))}</p>'
        f'<div class="hm">{_link(info.get("repo_url", ""), info.get("repo", ""), "hl")} '
        f'&middot; branch {_link(info.get("branch_url", ""), info.get("branch", "-"), "hl")} '
        f'&middot; commit '
        f'{_link(info.get("commit_url", ""), (info.get("commit") or "-")[:12], "hl")}'
        f'</div><div class="hb">{start}'
        f'{_link(info.get("pipeline_url", ""), "Open the pipeline", "btn light")}</div></div>'
        f'<div class="seal">{"&#10004;" if ok else "&#10008;"}</div></div>'
        f'<div class="tiles">{tiles}</div>'
        f'<section class="sec"><h2>What this run did, step by step</h2>{_flow(ctx)}</section>'
        f'<section class="sec"><h2>The themes</h2><div class="cards">{cards}</div></section>'
        f'{_advice(ctx)}'
        + (f'<section class="sec"><h2>Every stage of every theme</h2>{tables}</section>'
           if tables else "")
        + _guide() + _details(ctx))


def _theme_page(index: int, theme: Dict[str, Any], count: int) -> str:
    rows = stage_rows(theme.get("report") or {})
    total = totals(rows)
    verdict = theme.get("verdict") or "NOT RUN"
    meta = (theme.get("report") or {}).get("meta") or {}
    head = (
        f'<div class="th"><div><div class="eyebrow">Theme {index + 1} of {count}</div>'
        f'<h2>{esc(theme["title"])} {pill(verdict)}</h2>'
        f'<div class="mut">{esc(theme.get("description") or "")}</div></div>'
        f'<div class="tm"><span>run <code>{esc(theme.get("run_id") or "-")}</code></span>'
        f'<span>{int(total["stages_passed"])}/{int(total["stages"])} stages passed</span>'
        f'<span>{esc(duration_text(total["seconds"]) or "")}</span>'
        f'<span>{esc(meta.get("state") or "")}</span>'
        f'{_link(theme.get("pipeline_url", ""), "Theme pipeline", "ghost")}'
        '<a class="ghost" href="#overview" data-go="0">Overview</a></div></div>'
        f'{_segments(rows)}')
    if theme.get("page_html"):
        frame = (f'<iframe class="frame" title="{esc(theme["title"])}" '
                 f'srcdoc="{html.escape(theme["page_html"], quote=True)}"></iframe>')
    else:
        reason = "; ".join(theme.get("problems") or []) or "the theme did not run"
        frame = (f'<div class="empty"><h3>No SVT report for this theme</h3><p>{esc(reason)}</p>'
                 '<p>The theme left no report on the OIM. Open the theme pipeline to see which '
                 'job stopped and why.</p></div>')
    return head + frame


CSS = """
:root{--bg:#f4f6fb;--card:#fff;--panel:#eef2f9;--text:#1b2433;--mut:#64748b;--line:#e2e8f0;
--ok:#10b981;--bad:#ef4444;--warn:#f59e0b;--run:#3b82f6;--brand:#4f46e5;--bar:#111827;
--ok-bg:#dcfce7;--ok-fg:#166534;--bad-bg:#fee2e2;--bad-fg:#991b1b;--warn-bg:#fef3c7;
--warn-fg:#92400e;--none-bg:#e5e7eb;--none-fg:#374151;--shadow:0 6px 18px rgba(15,23,42,.08)}
[data-theme=dark]{--bg:#0b1020;--card:#141b2d;--panel:#1b2540;--text:#e6ebf5;--mut:#93a1ba;
--line:#26314f;--ok-bg:#064e3b;--ok-fg:#6ee7b7;--bad-bg:#7f1d1d;--bad-fg:#fca5a5;
--warn-bg:#78350f;--warn-fg:#fde68a;--none-bg:#334155;--none-fg:#cbd5e1;--bar:#050814;
--shadow:0 6px 18px rgba(0,0,0,.4)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 Inter,"Segoe UI",Arial,sans-serif}
a{color:var(--brand)}code{background:var(--panel);padding:1px 5px;border-radius:4px;font-size:12px}
.bar{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:10px;padding:8px 18px;
background:var(--bar);color:#fff}
.bar .brand{font-weight:700;letter-spacing:.3px;margin-right:6px;white-space:nowrap}
.tabs{display:flex;gap:6px;flex:1;overflow-x:auto}
.tab{border:0;background:#ffffff14;color:#cbd5e1;padding:6px 12px;border-radius:999px;
cursor:pointer;font:inherit;white-space:nowrap;display:flex;gap:6px;align-items:center}
.tab:hover{background:#ffffff26}.tab.on{background:#fff;color:#111827;font-weight:700}
.tab i{width:9px;height:9px;border-radius:50%;background:#94a3b8;display:inline-block}
.tab i.ok{background:var(--ok)}.tab i.bad{background:var(--bad)}.tab i.warn{background:var(--warn)}
.nav{display:flex;gap:6px;align-items:center}
.nb{border:1px solid #ffffff33;background:transparent;color:#fff;padding:6px 12px;
border-radius:8px;cursor:pointer;font:inherit}.nb:hover:not(:disabled){background:#ffffff22}
.nb:disabled{opacity:.35;cursor:default}.pg{color:#cbd5e1;font-size:12px;min-width:70px;text-align:center}
.page{display:none}.page.on{display:block}
.wrap{max-width:1180px;margin:0 auto;padding:22px 24px 60px}
.hero{display:flex;align-items:center;justify-content:space-between;gap:20px;color:#fff;
border-radius:16px;padding:30px 34px;box-shadow:var(--shadow);margin-bottom:20px}
.hero.ok{background:linear-gradient(120deg,#047857,#10b981 60%,#34d399)}
.hero.bad{background:linear-gradient(120deg,#991b1b,#dc2626 60%,#f87171)}
.hero h1{margin:4px 0 6px;font-size:30px}.hero p{margin:0 0 10px;opacity:.95;font-size:15px}
.eyebrow{text-transform:uppercase;letter-spacing:1.4px;font-size:11px;opacity:.85}
.hm{opacity:.95;margin-bottom:14px}.hl{color:#fff}.hb{display:flex;gap:10px;flex-wrap:wrap}
.seal{font-size:78px;line-height:1;opacity:.35}
.btn{display:inline-block;background:var(--brand);color:#fff;text-decoration:none;padding:8px 14px;
border-radius:8px;font-weight:600}.btn.big{background:#fff;color:#111827;padding:10px 18px}
.btn.light{background:#ffffff26;color:#fff}.ghost{color:var(--brand);text-decoration:none;
padding:6px 10px;border:1px solid var(--line);border-radius:8px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;
margin-bottom:8px}
.tile{background:var(--card);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow);
border-left:5px solid var(--line)}.tile.ok{border-color:var(--ok)}.tile.bad{border-color:var(--bad)}
.tile.warn{border-color:var(--warn)}.num{font-size:28px;font-weight:800}
.lbl{font-weight:600}.note{color:var(--mut);font-size:12px}
.sec{margin-top:28px}.sec h2{font-size:19px;margin:0 0 12px}.sec h3{margin:22px 0 8px;font-size:15px}
.flow{list-style:none;margin:0;padding:0;position:relative}
.flow:before{content:"";position:absolute;left:17px;top:8px;bottom:8px;width:3px;background:var(--line)}
.step{display:flex;gap:14px;position:relative;margin-bottom:12px}
.dot{flex:none;width:36px;height:36px;border-radius:50%;background:var(--none-bg);color:var(--none-fg);
display:flex;align-items:center;justify-content:center;font-weight:700;z-index:1}
.step.ok .dot{background:var(--ok);color:#fff}.step.bad .dot{background:var(--bad);color:#fff}
.step.warn .dot{background:var(--warn);color:#fff}
.sb{background:var(--card);border-radius:12px;padding:10px 14px;box-shadow:var(--shadow);flex:1}
.st{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.took{color:var(--mut);font-size:12px}
.sx{color:var(--mut);margin-top:3px}.sr{margin-top:6px;color:var(--bad-fg);background:var(--bad-bg);
padding:6px 10px;border-radius:8px;font-size:12.5px}.sl{margin-top:6px;font-size:12.5px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700;
background:var(--none-bg);color:var(--none-fg)}.pill.ok{background:var(--ok-bg);color:var(--ok-fg)}
.pill.bad{background:var(--bad-bg);color:var(--bad-fg)}.pill.warn{background:var(--warn-bg);
color:var(--warn-fg)}.pill.run{background:#dbeafe;color:#1e40af}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}
.card{background:var(--card);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow);
border-top:5px solid var(--line)}.card.ok{border-color:var(--ok)}.card.bad{border-color:var(--bad)}
.ch{display:flex;gap:12px;align-items:center}.ch .pill{margin-left:auto}
.idx{width:30px;height:30px;border-radius:8px;background:var(--panel);display:flex;
align-items:center;justify-content:center;font-weight:800}.ct{font-weight:700;font-size:16px}
.cs,.mut{color:var(--mut);font-size:12.5px}.cd{color:var(--mut);margin:8px 0}
.seg{display:flex;gap:3px;height:10px;margin:8px 0}.seg i{border-radius:3px;background:var(--none-bg)}
.seg i.ok{background:var(--ok)}.seg i.bad{background:var(--bad)}.seg i.warn{background:var(--warn)}
.cn{font-size:12.5px;color:var(--mut)}.cn .ok{color:var(--ok)}.cn .bad{color:var(--bad)}
.cn .warn{color:var(--warn)}.why{margin-top:10px;background:var(--bad-bg);color:var(--bad-fg);
padding:8px 12px;border-radius:8px;font-size:12.5px}.why ul{margin:4px 0 0 16px;padding:0}
.ca{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap}
.run{margin-left:auto;color:var(--mut);font-size:12px}
.adv{list-style:none;margin:0;padding:0}.adv li{background:var(--card);border-left:5px solid var(--bad);
border-radius:10px;padding:10px 14px;margin-bottom:10px;box-shadow:var(--shadow)}
.pt{font-weight:700}.pa{margin-top:6px;color:var(--mut)}
.tbl{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;overflow:hidden;
box-shadow:var(--shadow)}.tbl th,.tbl td{padding:8px 12px;border-bottom:1px solid var(--line);
text-align:left;vertical-align:top}.tbl th{background:var(--panel);font-size:12px;
text-transform:uppercase;letter-spacing:.6px}.tbl td.ok{color:var(--ok);font-weight:700}
.tbl td.bad{color:var(--bad);font-weight:700}.tbl td.warn{color:var(--warn);font-weight:700}
.gd details{background:var(--card);border-radius:10px;margin-bottom:8px;padding:10px 14px;
box-shadow:var(--shadow)}.gd summary{cursor:pointer;font-weight:700}.gd p{margin:8px 0 2px;color:var(--mut)}
.kv{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;overflow:hidden;
box-shadow:var(--shadow)}.kv th{width:170px;text-align:left;padding:9px 14px;background:var(--panel)}
.kv td{padding:9px 14px;word-break:break-all}
.th{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;flex-wrap:wrap;
padding:16px 24px 6px;background:var(--card);border-bottom:1px solid var(--line)}
.th h2{margin:2px 0}.tm{display:flex;gap:10px;align-items:center;flex-wrap:wrap;color:var(--mut)}
.page .seg{margin:0;border-radius:0;height:6px;gap:0}.page .seg i{border-radius:0}
.frame{display:block;width:100%;height:calc(100vh - 150px);min-height:520px;border:0;background:#fff}
.empty{max-width:760px;margin:40px auto;padding:0 24px}
@media print{.bar{display:none}.page{display:block!important}.frame{height:auto}}
"""

SCRIPT = """
(function(){
var pages=[].slice.call(document.querySelectorAll('.page')),tabs=[].slice.call(
document.querySelectorAll('.tab')),cur=0;
function names(){return pages.map(function(p){return p.getAttribute('data-name');});}
function show(i,push){
 if(i<0||i>=pages.length){return;}cur=i;
 pages.forEach(function(p,k){p.classList.toggle('on',k===i);});
 tabs.forEach(function(t,k){t.classList.toggle('on',k===i);});
 document.getElementById('prev').disabled=i===0;
 document.getElementById('next').disabled=i===pages.length-1;
 document.getElementById('pg').textContent='page '+(i+1)+' of '+pages.length;
 if(push){history.replaceState(null,'','#'+names()[i]);}
 window.scrollTo(0,0);
}
tabs.forEach(function(t,k){t.addEventListener('click',function(){show(k,true);});});
document.getElementById('prev').addEventListener('click',function(){show(cur-1,true);});
document.getElementById('next').addEventListener('click',function(){show(cur+1,true);});
[].forEach.call(document.querySelectorAll('[data-go]'),function(a){
 a.addEventListener('click',function(e){e.preventDefault();show(parseInt(a.getAttribute('data-go'),10),true);});});
document.addEventListener('keydown',function(e){
 if(e.target&&/INPUT|TEXTAREA/.test(e.target.tagName)){return;}
 if(e.key==='ArrowRight'){show(cur+1,true);}else if(e.key==='ArrowLeft'){show(cur-1,true);}});
function theme(t){document.documentElement.setAttribute('data-theme',t);
 [].forEach.call(document.querySelectorAll('iframe.frame'),function(f){try{
 f.contentDocument.documentElement.setAttribute('data-theme',t);}catch(e){}});}
document.getElementById('mode').addEventListener('click',function(){
 theme(document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark');});
if(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches){theme('dark');}
[].forEach.call(document.querySelectorAll('iframe.frame'),function(f){f.addEventListener('load',function(){
 f.contentDocument.documentElement.setAttribute('data-theme',document.documentElement.getAttribute('data-theme'));});});
var start=names().indexOf(location.hash.replace('#',''));show(start>=0?start:0,false);
})();
"""


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", name) or "theme"


def build_report(ctx: Dict[str, Any]) -> str:
    """Return the one self-contained HTML report of a cluster pipeline.

    ``ctx`` keys: ``label``, ``verdict`` (PASSED or FAILED), ``generated``, ``info`` (repo,
    repo_url, branch, branch_url, commit, commit_url, pipeline_url), ``common`` (the jobs
    preflight, initialization and summary: name, status, duration, url, reason), ``problems``,
    ``reasons`` and ``themes`` (name, title, description, verdict, run_id, pipeline_url,
    problems, report (the SVT report JSON), page_html (the theme's own HTML report)).
    """
    themes = ctx["themes"]
    for theme in themes:
        theme["name"] = _safe_name(theme["name"])
    tabs = ['<button class="tab on" type="button"><i class="' +
            ("ok" if ctx["verdict"] == "PASSED" else "bad") + '"></i>Overview</button>']
    sections = [f'<section class="page on" data-name="overview"><div class="wrap">'
                f'{_overview(ctx)}</div></section>']
    for index, theme in enumerate(themes):
        tone = {"PASSED": "ok", "FAILED": "bad"}.get(theme.get("verdict", ""), "")
        tabs.append(f'<button class="tab" type="button"><i class="{tone}"></i>'
                    f'{index + 1}. {esc(theme["title"])}</button>')
        sections.append(f'<section class="page" data-name="{esc(theme["name"])}">'
                        f'{_theme_page(index, theme, len(themes))}</section>')
    return (
        '<!DOCTYPE html><html lang="en" data-theme="light"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Omnia SVT report - {esc(ctx["label"])} - {esc(ctx["verdict"])}</title>'
        f'<style>{CSS}</style></head><body>'
        '<header class="bar"><span class="brand">Omnia SVT</span>'
        f'<nav class="tabs">{"".join(tabs)}</nav><div class="nav">'
        '<button class="nb" id="prev" type="button">&#9664; Previous</button>'
        '<span class="pg" id="pg"></span>'
        '<button class="nb" id="next" type="button">Next &#9654;</button>'
        '<button class="nb" id="mode" type="button" title="Light / dark">&#9790;</button>'
        f'</div></header>{"".join(sections)}<script>{SCRIPT}</script></body></html>')
