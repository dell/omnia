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
"""
HTML Report Generation for omnia-auto test reports.

This module contains the HTML/CSS templates and generation logic.
Line length rules are relaxed due to embedded HTML/CSS content.
"""

import re
from datetime import datetime
from typing import Any, Dict

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return _ANSI_RE.sub("", text)


def _escape_html(text: str) -> str:
    """Strip ANSI codes then escape HTML special characters."""
    text = _strip_ansi(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_details(details: str, detail_fields: list) -> str:
    """Escape details and style only exact structured key/value lines."""
    if not detail_fields:
        return _escape_html(details)

    structured_lines = {
        f"{field.get('key', '')}: {field.get('value', '')}": field
        for field in detail_fields
        if isinstance(field, dict)
    }
    rendered_lines = []
    for raw_line in _strip_ansi(details).split("\n"):
        content = raw_line.lstrip()
        if content.startswith("\u2502 "):
            content = content[2:]
        field = structured_lines.get(content)
        if field is None:
            rendered_lines.append(_escape_html(raw_line))
            continue
        prefix = raw_line[: len(raw_line) - len(content)]
        rendered_lines.append(
            f'{_escape_html(prefix)}<span class="detail-key">'
            f'{_escape_html(str(field.get("key", "")))}:</span> '
            f'<span class="detail-value">'
            f'{_escape_html(str(field.get("value", "")))}</span>'
        )
    return "\n".join(rendered_lines)


# SVG Icons
SVG_CHECK = '<svg viewBox="0 0 16 16"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>'
SVG_X = '<svg viewBox="0 0 16 16"><path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z"/></svg>'
SVG_SKIP = '<svg viewBox="0 0 16 16"><path d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/><path d="M4.5 7.25h7a.75.75 0 010 1.5h-7a.75.75 0 010-1.5z"/></svg>'

# Module marker for setup tests
SETUP_MODULE = "oim_prereq_test"


def _donut_svg(passed: int, failed: int, skipped: int, size: int = 160) -> str:
    """Return an inline SVG donut chart."""
    total = passed + failed + skipped
    if total == 0:
        return ""
    r = 58
    cx = cy = size // 2
    circ = 2 * 3.14159265 * r
    arcs = []
    palette = [
        ("#3fb950", passed, "Passed"),
        ("#f85149", failed, "Failed"),
        ("#e3b341", skipped, "Skipped"),
    ]
    offset = 0
    for color, count, label in palette:
        if count == 0:
            continue
        dash = circ * count / total
        gap = circ - dash
        arcs.append(
            f'<circle class="donut-arc" cx="{cx}" cy="{cy}" r="{r}" '
            f'fill="none" stroke="{color}" stroke-width="16" '
            f'stroke-dasharray="{dash:.2f} {gap:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}"><title>{label}: {count}</title></circle>'
        )
        offset += dash

    executed = passed + failed
    pct = int(passed / executed * 100) if executed else (100 if skipped else 0)
    return (
        f'<svg class="donut-chart" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'{"".join(arcs)}'
        f'<text class="donut-pct" x="{cx}" y="{cy}" text-anchor="middle" '
        f'dominant-baseline="central" transform="rotate(90 {cx} {cy})">{pct}%</text>'
        f'<text class="donut-lbl" x="{cx}" y="{cy+22}" text-anchor="middle" '
        f'transform="rotate(90 {cx} {cy})">pass rate</text>'
        f"</svg>"
    )


def _scenario_bars(modules: list) -> str:
    """Generate scenario bar chart HTML."""
    if not modules:
        return ""
    rows = []
    for m in modules:
        name = m.get("module", "unknown")
        s = m.get("summary") or {}
        p, f, sk = s.get("passed", 0), s.get("failed", 0), s.get("skipped", 0)
        t = p + f + sk
        if t == 0:
            continue
        pw = int(p / t * 100)
        fw = int(f / t * 100)
        sw = 100 - pw - fw
        dot_cls = "dot-pass" if f == 0 else "dot-fail"
        rows.append(
            f'<div class="bar-row">'
            f'<div class="bar-dot {dot_cls}"></div>'
            f'<div class="bar-label" title="{name}">{name}</div>'
            f'<div class="bar-track">'
            f'<div class="bar-seg bar-pass" style="width:{pw}%"></div>'
            f'<div class="bar-seg bar-fail" style="width:{fw}%"></div>'
            f'<div class="bar-seg bar-skip" style="width:{sw}%"></div>'
            f"</div>"
            f'<div class="bar-nums">'
            f'<span class="c-pass">{p}</span>/'
            f'<span class="c-fail">{f}</span>/'
            f'<span class="c-skip">{sk}</span>'
            f"</div>"
            f'<div class="bar-tip">'
            f'<div class="tip-head">{name}</div>'
            f'<div class="tip-body">'
            f'<div class="tip-stats">'
            f'<div class="tip-r"><div class="tip-d" style="background:#3fb950"></div>Passed<b>{p}</b></div>'
            f'<div class="tip-r"><div class="tip-d" style="background:#f85149"></div>Failed<b>{f}</b></div>'
            f'<div class="tip-r"><div class="tip-d" style="background:#e3b341"></div>Skipped<b>{sk}</b></div>'
            f"</div></div></div></div>"
        )
    return f'<div class="scenario-bars">{"".join(rows)}</div>'


def _fmt_run_id(rid: str) -> str:
    """Format run ID for display."""
    if len(rid) == 14 and rid.isdigit():
        try:
            dt = datetime.strptime(rid, "%Y%m%d%H%M%S")
            return dt.strftime("%b %d, %Y %H:%M")
        except ValueError:
            pass
    return rid


def _marker_folder_breakdown(modules: list) -> str:
    """Generate marker/folder breakdown tables."""
    marker_stats: Dict[str, Dict[str, int]] = {}
    folder_stats: Dict[str, Dict[str, int]] = {}

    for m in modules:
        if m.get("module") == SETUP_MODULE:
            continue
        for r in m.get("results", []):
            st = r.get("status", "FAILED")
            markers = r.get("markers", [])
            for mk in markers:
                if mk not in marker_stats:
                    marker_stats[mk] = {"passed": 0, "failed": 0, "skipped": 0}
                if st == "PASSED":
                    marker_stats[mk]["passed"] += 1
                elif st == "FAILED":
                    marker_stats[mk]["failed"] += 1
                else:
                    marker_stats[mk]["skipped"] += 1

            tname = r.get("test_name", "")
            parts = tname.split("::")
            if len(parts) >= 2:
                folder = parts[0].replace("fvt/", "").rsplit("/", 1)[0]
            else:
                folder = "root"
            if folder not in folder_stats:
                folder_stats[folder] = {"passed": 0, "failed": 0, "skipped": 0}
            if st == "PASSED":
                folder_stats[folder]["passed"] += 1
            elif st == "FAILED":
                folder_stats[folder]["failed"] += 1
            else:
                folder_stats[folder]["skipped"] += 1

    html = '<div class="breakdown">'

    if marker_stats:
        html += '<div class="bd-section"><div class="bd-title">By Marker</div>'
        html += '<table class="bd-table"><tr><th>Marker</th><th>P</th><th>F</th><th>S</th></tr>'
        for mk, st in sorted(marker_stats.items()):
            row_cls = "bd-pass" if st["failed"] == 0 else "bd-fail"
            html += (
                f'<tr class="{row_cls}">'
                f'<td class="bd-name">{mk}</td>'
                f'<td style="color:var(--green)">{st["passed"]}</td>'
                f'<td style="color:var(--red)">{st["failed"]}</td>'
                f'<td style="color:var(--yellow)">{st["skipped"]}</td>'
                f"</tr>"
            )
        html += "</table></div>"

    if folder_stats:
        html += '<div class="bd-section"><div class="bd-title">By Folder</div>'
        html += '<table class="bd-table"><tr><th>Folder</th><th>P</th><th>F</th><th>S</th></tr>'
        for fld, st in sorted(folder_stats.items()):
            row_cls = "bd-pass" if st["failed"] == 0 else "bd-fail"
            html += (
                f'<tr class="{row_cls}">'
                f'<td class="bd-name">{fld}</td>'
                f'<td style="color:var(--green)">{st["passed"]}</td>'
                f'<td style="color:var(--red)">{st["failed"]}</td>'
                f'<td style="color:var(--yellow)">{st["skipped"]}</td>'
                f"</tr>"
            )
        html += "</table></div>"

    html += "</div>"
    return html


def _render_test_item(test_id: int, test: dict, icls: str, isvg: str) -> str:
    """Render a single test item row."""
    name = test.get("test_name", "unknown")
    tc_id = test.get("tc_id", "")
    display_name = f"[{tc_id}] {name}" if tc_id else name
    dur = test.get("duration_seconds", 0)
    details = test.get("details", "")
    detail_fields = test.get("detail_fields", [])
    error = test.get("error", "")

    html = (
        f'<div class="ti" id="t-{test_id}">'
        f'<div class="tr" onclick="togT(event,{test_id})">'
        f'<span class="tr-arr">&#9654;</span>'
        f'<div class="tr-icon {icls}">{isvg}</div>'
        f'<span class="tr-name">{_escape_html(display_name)}</span>'
        f'<span class="tr-dur">{dur:.2f}s</span>'
        f"</div>"
        f'<div class="ti-out">'
    )

    if details:
        html += f'<div class="obox">{_render_details(details, detail_fields)}</div>'
    if error:
        html += f'<div class="ebox">{_escape_html(error)}</div>'
    if not details and not error:
        html += '<div class="obox" style="color:var(--fg-muted)">No output</div>'

    html += "</div></div>"
    return html


def get_css() -> str:
    """Return the CSS styles for the report."""
    return """
/* Theme variables */
[data-theme="dark"] {
  --bg-canvas:#0d1117; --bg-card:#161b22; --bg-header:#1c2128;
  --bg-hover:#21262d; --border:#30363d; --fg:#e6edf3; --fg-muted:#7d8590;
  --green:#3fb950; --green-bg:rgba(63,185,80,.15);
  --red:#f85149; --red-bg:rgba(248,81,73,.15);
  --yellow:#e3b341; --yellow-bg:rgba(227,179,65,.15);
  --blue:#58a6ff; --blue-bg:rgba(88,166,255,.12);
  --purple:#bc8cff; --purple-bg:rgba(188,140,255,.12);
  --orange:#f0883e; --shadow:rgba(0,0,0,.3);
}
[data-theme="light"] {
  --bg-canvas:#f6f8fa; --bg-card:#ffffff; --bg-header:#f0f3f6;
  --bg-hover:#e8ecf0; --border:#d0d7de; --fg:#1f2328; --fg-muted:#656d76;
  --green:#1a7f37; --green-bg:rgba(26,127,55,.12);
  --red:#cf222e; --red-bg:rgba(207,34,46,.1);
  --yellow:#9a6700; --yellow-bg:rgba(154,103,0,.1);
  --blue:#0969da; --blue-bg:rgba(9,105,218,.08);
  --purple:#8250df; --purple-bg:rgba(130,80,223,.08);
  --orange:#bc4c00; --shadow:rgba(0,0,0,.08);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg-canvas);color:var(--fg);line-height:1.6;font-size:15px}
.container{max-width:1480px;margin:0 auto;padding:24px}
.hdr{background:var(--bg-card);padding:24px 32px;border-radius:12px;margin-bottom:24px;border:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.hdr-left{display:flex;align-items:center;gap:14px}
.hdr h1{font-size:1.5em;font-weight:700}
.logo{width:38px;height:38px;background:linear-gradient(135deg,var(--green),var(--blue));border-radius:10px;display:grid;place-items:center;font-size:20px;color:#fff}
.hdr .sub{color:var(--fg-muted);font-size:.85em}
.theme-btn{background:var(--bg-hover);border:1px solid var(--border);border-radius:8px;padding:8px 14px;cursor:pointer;color:var(--fg);font-size:.85em;display:flex;align-items:center;gap:6px}
.theme-btn:hover{background:var(--blue-bg);border-color:var(--blue)}
.lay{display:flex;gap:22px}
.side{width:280px;flex-shrink:0}
.main{flex:1;min-width:0}
.srv-list{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;overflow:hidden;position:sticky;top:20px}
.srv-list h3{padding:14px 18px;background:var(--bg-header);font-size:.82em;letter-spacing:.5px;text-transform:uppercase;color:var(--fg-muted);border-bottom:1px solid var(--border)}
.srv{padding:14px 18px;border-bottom:1px solid var(--border);cursor:pointer}
.srv:last-child{border-bottom:none}
.srv:hover{background:var(--bg-hover)}
.srv.act{background:var(--blue-bg);border-left:3px solid var(--blue)}
.srv-ip{font-family:monospace;font-size:.92em;color:var(--blue);font-weight:600}
.srv-host{font-size:.8em;color:var(--fg-muted);margin-top:2px}
.srv-stats{display:flex;gap:12px;margin-top:6px;font-size:.78em;font-weight:600}
.srv-stats .p{color:var(--green)} .srv-stats .f{color:var(--red)} .srv-stats .s{color:var(--yellow)}
.panel{display:none} .panel.act{display:block}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:22px}
.kpi{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px 14px;text-align:center;position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px}
.kpi.kp::before{background:var(--green)} .kpi.kf::before{background:var(--red)}
.kpi.ks::before{background:var(--yellow)} .kpi.kt::before{background:var(--blue)}
.kpi .n{font-size:2.2em;font-weight:800;line-height:1}
.kpi.kp .n{color:var(--green)} .kpi.kf .n{color:var(--red)}
.kpi.ks .n{color:var(--yellow)} .kpi.kt .n{color:var(--blue)}
.kpi .l{color:var(--fg-muted);text-transform:uppercase;font-size:.68em;letter-spacing:1.2px;margin-top:4px;font-weight:600}
.run{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;margin-bottom:16px;overflow:hidden}
.run-h{padding:16px 20px;cursor:pointer;display:flex;align-items:center;gap:12px}
.run-h:hover{background:var(--bg-hover)}
.run-h .arr{color:var(--fg-muted);font-size:.75em;width:18px}
.run.shut .arr{transform:rotate(-90deg)} .run.shut .run-b{display:none}
.run-title{font-weight:600;font-size:.95em;flex:1;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.run-title .rid{font-family:monospace;color:var(--purple);font-weight:700;font-size:.95em}
.pill{display:inline-flex;align-items:center;gap:4px;padding:3px 12px;border-radius:20px;font-size:.78em;font-weight:700}
.pill.pp{background:var(--green-bg);color:var(--green)}
.pill.pf{background:var(--red-bg);color:var(--red)}
.pill.ps{background:var(--yellow-bg);color:var(--yellow)}
.run-info{display:flex;gap:14px;font-size:.8em;color:var(--fg-muted);padding:0 20px 10px 50px}
.run-b{border-top:1px solid var(--border)}
.mod{border-bottom:1px solid var(--border)}
.mod:last-child{border-bottom:none}
.mod-h{display:flex;align-items:center;padding:12px 20px;cursor:pointer;gap:10px}
.mod-h:hover{background:var(--bg-hover)}
.mod-arr{color:var(--fg-muted);font-size:.75em;width:16px}
.mod.shut .mod-arr{transform:rotate(-90deg)} .mod.shut .mod-b{display:none}
.mod-icon{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-size:12px;background:var(--orange);color:#fff}
.mod-name{font-family:monospace;font-size:.92em;color:var(--blue);font-weight:600}
.mod-dur{color:var(--fg-muted);font-size:.8em;margin-left:auto;font-family:monospace}
.mod-b{background:var(--bg-canvas)}
.mod-meta{display:flex;gap:8px;padding:6px 20px 6px 52px;font-size:.78em;color:var(--fg-muted);border-bottom:1px solid var(--border);background:var(--bg-header)}
.meta-tag{background:var(--purple-bg);color:var(--purple);padding:2px 10px;border-radius:12px;font-weight:600;font-size:.82em}
.dv-sec{border-top:1px solid var(--border)}
.dv-hdr{display:flex;align-items:center;gap:8px;padding:8px 20px;cursor:pointer;font-size:.85em;font-weight:600;color:var(--fg-muted);background:var(--bg-header);border-bottom:1px solid var(--border)}
.dv-hdr:hover{background:var(--bg-hover)}
.dv-hdr .dv-arr{font-size:.65em;width:14px;color:var(--fg-muted)}
.dv-icon{width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-size:10px;color:#fff}
.dv-icon.dv-deploy{background:var(--blue)}
.dv-icon.dv-verify{background:var(--green)}
.dv-icon.dv-skip{background:var(--fg-muted)}
.dv-body{} .dv-sec.shut .dv-body{display:none} .dv-sec.shut .dv-arr{transform:rotate(-90deg)}
.dv-skip-msg{padding:12px 20px 12px 52px;font-size:.85em;color:var(--fg-muted);font-style:italic}
.ti{border-bottom:1px solid var(--border)}
.ti:last-child{border-bottom:none}
.tr{display:flex;align-items:center;padding:10px 20px 10px 32px;cursor:pointer;gap:10px}
.tr:hover{background:var(--bg-hover)}
.tr-arr{color:var(--fg-muted);font-size:.65em;width:14px}
.ti.open .tr-arr{transform:rotate(90deg)}
.tr-icon{width:24px;height:24px;border-radius:50%;display:grid;place-items:center}
.tr-icon.ip{background:var(--green);color:#fff} .tr-icon.if{background:var(--red);color:#fff}
.tr-icon.is{background:var(--yellow);color:#000}
.tr-icon svg{width:14px;height:14px;fill:currentColor}
.tr-name{flex:1;font-size:.92em}
.tr-dur{color:var(--fg-muted);font-size:.8em;font-family:monospace;min-width:60px;text-align:right}
.ti-out{display:none;padding:8px 20px 12px 56px}
.ti.open .ti-out{display:block}
.obox{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px;font-family:monospace;font-size:.8em;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow-y:auto}
.detail-key{color:var(--blue);font-weight:700}
.detail-value{color:var(--fg);font-weight:600}
.ebox{background:var(--red-bg);border:1px solid rgba(248,81,73,.3);border-radius:8px;padding:12px;margin-top:8px;font-family:monospace;font-size:.8em;white-space:pre-wrap;max-height:160px;overflow-y:auto;color:var(--red)}
.legend{display:flex;gap:16px;padding:10px 24px;font-size:.82em;color:var(--fg-muted);border-bottom:1px solid var(--border);background:var(--bg-header)}
.legend-item{display:flex;align-items:center;gap:5px}
.legend-dot{width:10px;height:10px;border-radius:50%}
.breakdown{display:flex;gap:16px;padding:16px 20px;flex-wrap:wrap;border-bottom:1px solid var(--border);background:var(--bg-header)}
.bd-section{flex:1;min-width:260px}
.bd-title{font-size:.82em;font-weight:700;color:var(--fg-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.bd-table{width:100%;border-collapse:collapse;font-size:.82em;font-family:monospace}
.bd-table th{text-align:left;padding:6px 10px;border-bottom:2px solid var(--border);font-weight:700;font-size:.78em;text-transform:uppercase;color:var(--fg-muted)}
.bd-table td{padding:5px 10px;border-bottom:1px solid var(--border)}
.bd-table tr:hover{background:var(--bg-hover)}
.bd-name{font-weight:600;color:var(--fg);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bd-pass td:first-child{border-left:3px solid var(--green)}
.bd-fail td:first-child{border-left:3px solid var(--red)}
.bar-row{display:flex;align-items:center;gap:10px;padding:5px 0;font-size:.85em;position:relative}
.bar-dot{width:8px;height:8px;border-radius:50%}
.dot-pass{background:var(--green)} .dot-fail{background:var(--red)}
.bar-label{width:160px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:monospace;font-size:.9em;color:var(--fg);font-weight:500}
.bar-track{flex:1;height:10px;background:var(--bg-hover);border-radius:5px;overflow:hidden;display:flex}
.bar-seg{height:100%}
.bar-pass{background:var(--green)} .bar-fail{background:var(--red)} .bar-skip{background:var(--yellow)}
.bar-nums{font-size:.82em;font-family:monospace;width:80px;text-align:right;display:flex;gap:5px;justify-content:flex-end;font-weight:600}
.c-pass{color:var(--green)} .c-fail{color:var(--red)} .c-skip{color:var(--yellow)}
.bar-tip{display:none;position:absolute;top:100%;left:50%;transform:translateX(-50%);z-index:100;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px;min-width:200px}
.bar-row:hover .bar-tip{display:block}
.tip-head{font-weight:700;font-size:.9em;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border);color:var(--blue)}
.tip-body{display:flex;align-items:center;gap:12px}
.tip-stats{display:flex;flex-direction:column;gap:4px}
.tip-r{display:flex;align-items:center;gap:6px;font-size:.82em}
.tip-r b{margin-left:auto;font-weight:700;min-width:20px;text-align:right}
.tip-d{width:8px;height:8px;border-radius:50%}
.setup-panel{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;margin-bottom:16px;overflow:hidden}
.setup-hdr{display:flex;align-items:center;gap:10px;padding:14px 20px;border-bottom:1px solid var(--border);background:var(--bg-header)}
.setup-icon{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;font-size:14px;color:#fff}
.setup-icon.sok{background:var(--green)} .setup-icon.serr{background:var(--red)} .setup-icon.swarn{background:var(--yellow)}
.setup-title{font-weight:700;font-size:.95em;flex:1}
.setup-status{font-size:.82em;font-weight:600;padding:4px 14px;border-radius:20px}
.setup-status.s-pass{background:var(--green-bg);color:var(--green)}
.setup-status.s-fail{background:var(--red-bg);color:var(--red)}
.setup-status.s-warn{background:var(--yellow-bg);color:var(--yellow)}
.setup-body{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;padding:16px 20px}
.setup-check{display:flex;align-items:center;gap:8px;padding:10px 14px;border-radius:8px;border:1px solid var(--border);background:var(--bg-canvas);font-size:.85em}
.setup-dot{width:10px;height:10px;border-radius:50%}
.setup-dot.dp{background:var(--green)} .setup-dot.df{background:var(--red)} .setup-dot.ds{background:var(--yellow)}
.setup-cname{flex:1;font-family:monospace;font-size:.9em}
.setup-cdur{color:var(--fg-muted);font-size:.8em;font-family:monospace}
.setup-summary{display:flex;gap:16px;padding:10px 20px;border-top:1px solid var(--border);font-size:.82em;color:var(--fg-muted);background:var(--bg-header)}
.ft{text-align:center;padding:20px;color:var(--fg-muted);font-size:.82em;border-top:1px solid var(--border);margin-top:32px}
.donut-chart{transform:rotate(-90deg)}
.donut-arc:hover{opacity:.75}
.donut-pct{fill:var(--fg);font-size:30px;font-weight:800;font-family:system-ui}
.donut-lbl{fill:var(--fg-muted);font-size:11px;font-family:system-ui}
.scenario-bars{flex:1;min-width:260px}
@media(max-width:920px){.lay{flex-direction:column}.side{width:100%}.breakdown{flex-direction:column}}
"""


def get_js() -> str:
    """Return the JavaScript for the report."""
    return """
function showSrv(ip){
  document.querySelectorAll('.srv').forEach(e=>e.classList.remove('act'));
  document.querySelectorAll('.panel').forEach(e=>e.classList.remove('act'));
  document.querySelector(`.srv[onclick="showSrv('${ip}')"]`).classList.add('act');
  document.getElementById('p-'+ip.replace(/\\./g,'-')).classList.add('act');
}
function togRun(id){document.getElementById('r-'+id).classList.toggle('shut')}
function togMod(id){document.getElementById('m-'+id).classList.toggle('shut')}
function togDV(id){var el=document.getElementById('dv-'+id);if(el)el.classList.toggle('shut')}
function togT(e,id){
  if(e){e.preventDefault();e.stopPropagation();}
  var el=document.getElementById('t-'+id);
  if(el){
    el.classList.toggle('open');
    var out=el.querySelector('.ti-out');
    if(out) out.style.display=el.classList.contains('open')?'block':'none';
  }
}
function togLogs(id){
  var b=document.getElementById('lg-'+id);
  if(!b) return;
  var c=b.parentElement;
  c.classList.toggle('shut');
  b.style.display=c.classList.contains('shut')?'none':'block';
}
function toggleTheme(){
  var h=document.documentElement;
  var d=h.getAttribute('data-theme')==='dark'?'light':'dark';
  h.setAttribute('data-theme',d);
  document.getElementById('theme-icon').innerHTML=d==='dark'?'\\u263E':'\\u2600';
  document.getElementById('theme-label').textContent=d==='dark'?'Light':'Dark';
}
"""


def generate_html(data: Dict[str, Any]) -> str:
    """Generate the complete HTML report."""
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Omnia Test Report</title>
<style>{get_css()}</style>
</head>
<body>
<div class="container">
<div class="hdr">
  <div class="hdr-left">
    <div class="logo">&#9889;</div>
    <div><h1>Omnia Test Report</h1><div class="sub">Generated {generated}</div></div>
  </div>
  <button class="theme-btn" onclick="toggleTheme()">
    <span id="theme-icon">&#9790;</span> <span id="theme-label">Light</span>
  </button>
</div>
"""

    servers = data.get("servers", {})
    if not servers:
        html += (
            '<div style="text-align:center;padding:60px 20px;color:var(--fg-muted)">'
        )
        html += "No test results yet. Run tests to generate report.</div>"
    else:
        html += _generate_servers_html(servers)

    html += f"""
<div class="ft">Omnia Automation Framework &mdash; Test Report</div>
</div>
<script>{get_js()}</script>
</body>
</html>"""

    return html


def _generate_servers_html(servers: Dict[str, Any]) -> str:
    """Generate the servers section HTML."""
    html = '<div class="lay"><div class="side"><div class="srv-list"><h3>Targets</h3>'

    first_server = True
    for sip, sd in servers.items():
        hostname = sd.get("hostname", "")
        runs = sd.get("runs", [])
        tp = tf = ts = 0
        for r in runs:
            for m in r.get("modules") or []:
                if m.get("module") == SETUP_MODULE:
                    continue
                ms = m.get("summary") or {}
                tp += ms.get("passed", 0)
                tf += ms.get("failed", 0)
                ts += ms.get("skipped", 0)
            if not r.get("modules") and "summary" in r:
                s = r["summary"] or {}
                tp += s.get("passed", 0)
                tf += s.get("failed", 0)
                ts += s.get("skipped", 0)
        act = "act" if first_server else ""
        dip = sip if sip and sip != "localhost" else "localhost"
        html += (
            f'<div class="srv {act}" onclick="showSrv(\'{sip}\')">'
            f'<div class="srv-ip">{dip}</div>'
            f'<div class="srv-host">{hostname}</div>'
            f'<div class="srv-stats">'
            f'<span class="p">{tp} passed</span>'
            f'<span class="f">{tf} failed</span>'
            f'<span class="s">{ts} skipped</span></div></div>'
        )
        first_server = False

    html += '</div></div><div class="main">'

    first_server = True
    test_id = 0
    for sip, sd in servers.items():
        runs = sd.get("runs", [])
        setup_results_all = []
        for r in runs:
            for m in r.get("modules") or []:
                if m.get("module") == SETUP_MODULE:
                    setup_results_all.extend(m.get("results", []))

        tp = tf = tsk = 0
        for r in runs:
            modules = r.get("modules") or []
            if not modules and "results" in r:
                modules = [
                    {"module": r.get("module", "unknown"), "summary": r["summary"]}
                ]
            for m in modules:
                if m.get("module") == SETUP_MODULE:
                    continue
                ms = m.get("summary") or {}
                tp += ms.get("passed", 0)
                tf += ms.get("failed", 0)
                tsk += ms.get("skipped", 0)
        ttl = tp + tf + tsk
        act = "act" if first_server else ""

        executed_total = tp + tf
        pass_rate = (
            int(tp / executed_total * 100)
            if executed_total
            else (100 if tsk > 0 else 0)
        )
        total_dur = sum(
            sum(
                m.get("duration_seconds", 0) or 0
                for m in (
                    r.get("modules")
                    or [{"duration_seconds": r.get("total_duration_seconds", 0)}]
                )
            )
            for r in runs
        )

        html += (
            f'<div class="panel {act}" id="p-{sip.replace(".","-")}">'
            f'<div class="cards">'
            f'<div class="kpi kt"><div class="n">{ttl}</div><div class="l">Total</div></div>'
            f'<div class="kpi kp"><div class="n">{tp}</div><div class="l">Passed</div></div>'
            f'<div class="kpi kf"><div class="n">{tf}</div><div class="l">Failed</div></div>'
            f'<div class="kpi ks"><div class="n">{tsk}</div><div class="l">Skipped</div></div>'
            f'<div class="kpi kp"><div class="n">{pass_rate}%</div><div class="l">Pass Rate</div></div>'
            f'<div class="kpi kt"><div class="n">{len(runs)}</div><div class="l">Runs</div></div>'
            f'<div class="kpi kt"><div class="n">{total_dur:.0f}s</div><div class="l">Duration</div></div>'
            f"</div>"
        )

        if setup_results_all:
            html += _generate_setup_panel(setup_results_all)

        for run_idx, run in enumerate(reversed(runs), 1):
            html += _generate_run_html(run, run_idx, sip, test_id)
            test_id += len(run.get("modules", [{}])[0].get("results", []))

        html += "</div>"
        first_server = False

    html += "</div></div>"
    return html


def _generate_setup_panel(setup_results: list) -> str:
    """Generate the setup panel HTML."""
    s_pass = sum(1 for r in setup_results if r.get("status") == "PASSED")
    s_fail = sum(1 for r in setup_results if r.get("status") == "FAILED")
    s_skip = sum(1 for r in setup_results if r.get("status") == "SKIPPED")
    s_total = len(setup_results)

    if s_fail > 0:
        s_icon_cls, s_icon = "serr", "&#10007;"
        s_stat_cls, s_stat_txt = "s-fail", f"{s_fail} check(s) failed"
    elif s_skip > 0 and s_pass == 0:
        s_icon_cls, s_icon = "swarn", "&#8212;"
        s_stat_cls, s_stat_txt = "s-warn", "Checks skipped"
    else:
        s_icon_cls, s_icon = "sok", "&#10003;"
        s_stat_cls, s_stat_txt = "s-pass", "All checks passed"

    html = (
        f'<div class="setup-panel"><div class="setup-hdr">'
        f'<div class="setup-icon {s_icon_cls}">{s_icon}</div>'
        f'<span class="setup-title">Server Setup</span>'
        f'<span class="setup-status {s_stat_cls}">{s_stat_txt}</span>'
        f'</div><div class="setup-body">'
    )

    for sr in setup_results:
        st = sr.get("status", "FAILED")
        dot = "dp" if st == "PASSED" else ("ds" if st == "SKIPPED" else "df")
        name = sr.get("test_name", "unknown").split("::")[-1]
        name = name.replace("test_", "").replace("_", " ").title()
        dur = sr.get("duration_seconds", 0)
        html += (
            f'<div class="setup-check">'
            f'<div class="setup-dot {dot}"></div>'
            f'<span class="setup-cname">{name}</span>'
            f'<span class="setup-cdur">{dur:.1f}s</span></div>'
        )

    html += (
        f'</div><div class="setup-summary">'
        f"<span><b>{s_pass}</b> passed</span>"
        f"<span><b>{s_fail}</b> failed</span>"
        f"<span><b>{s_skip}</b> skipped</span>"
        f'<span style="margin-left:auto"><b>{s_total}</b> checks</span>'
        f"</div></div>"
    )
    return html


def _generate_run_html(run: dict, run_idx: int, sip: str, test_id_start: int) -> str:
    """Generate HTML for a single run."""
    rs = run.get("summary") or {}
    rp, rf, rsk = rs.get("passed", 0), rs.get("failed", 0), rs.get("skipped", 0)

    pills = f'<span class="pill pp">{rp} passed</span>'
    if rf:
        pills += f' <span class="pill pf">{rf} failed</span>'
    if rsk:
        pills += f' <span class="pill ps">{rsk} skipped</span>'

    shut = "shut" if run_idx > 1 else ""
    uid = f"{sip.replace('.', '-')}-{run_idx}"

    modules = run.get("modules", [])
    if not modules and "results" in run:
        modules = [
            {
                "module": run.get("module", "unknown"),
                "results": run["results"],
                "summary": run["summary"],
                "duration_seconds": run.get("total_duration_seconds", 0),
            }
        ]

    tdur = sum(m.get("duration_seconds", 0) for m in modules)
    rid = run.get("report_id", "")
    disp_rid = _fmt_run_id(rid)

    html = (
        f'<div class="run {shut}" id="r-{uid}">'
        f'<div class="run-h" onclick="togRun(\'{uid}\')">'
        f'<span class="arr">&#9660;</span>'
        f'<div class="run-title">'
        f'<span class="rid">{rid}</span>'
        f'<span style="color:var(--fg-muted);font-size:.82em">{disp_rid}</span>'
        f"{pills}"
        f'<span style="color:var(--fg-muted);font-size:.8em;margin-left:8px">'
        f"{len(modules)} scenario(s)</span>"
        f"</div></div>"
        f'<div class="run-info">&#9201; {tdur:.1f}s</div>'
        f'<div class="run-b">'
        f'<div class="legend">'
        f'<div class="legend-item">'
        f'<div class="legend-dot" style="background:var(--green)"></div>Passed</div>'
        f'<div class="legend-item">'
        f'<div class="legend-dot" style="background:var(--red)"></div>Failed</div>'
        f'<div class="legend-item">'
        f'<div class="legend-dot" style="background:var(--yellow)"></div>Skipped</div>'
        f"</div>"
        f"{_marker_folder_breakdown(modules)}"
    )

    test_id = test_id_start
    for mi, mod in enumerate(modules):
        html += _generate_module_html(mod, mi, uid, test_id)
        test_id += len(mod.get("results", []))

    html += "</div></div>"
    return html


def _generate_module_html(mod: dict, mi: int, uid: str, test_id_start: int) -> str:
    """Generate HTML for a single module."""
    ms = mod.get("summary") or {}
    mp, mf, msk = ms.get("passed", 0), ms.get("failed", 0), ms.get("skipped", 0)
    mpills = f'<span class="pill pp">{mp}</span>'
    if mf:
        mpills += f' <span class="pill pf">{mf}</span>'
    if msk:
        mpills += f' <span class="pill ps">{msk}</span>'
    mid = f"{uid}-m{mi}"

    html = (
        f'<div class="mod" id="m-{mid}">'
        f'<div class="mod-h" onclick="togMod(\'{mid}\')">'
        f'<span class="mod-arr">&#9660;</span>'
        f'<div class="mod-icon">&#9670;</div>'
        f'<span class="mod-name">{mod["module"]}</span>'
        f'<span style="margin-left:10px">{mpills}</span>'
        f'<span class="mod-dur">{mod.get("duration_seconds", 0):.1f}s</span>'
        f'</div><div class="mod-b">'
    )

    m_suite = mod.get("suite", "all")
    m_marker = mod.get("marker", "")
    m_cmd = mod.get("exec_command", "")
    meta_tags = f'<span class="meta-tag">suite: {m_suite}</span>'
    if m_marker:
        meta_tags += f' <span class="meta-tag">marker: {m_marker}</span>'
    if m_cmd:
        meta_tags += f' <span class="meta-tag">cmd: {m_cmd}</span>'
    html += f'<div class="mod-meta">{meta_tags}</div>'

    all_results = mod.get("results", [])
    deploy_results = [
        r
        for r in all_results
        if r.get("category") == "deploy"
        or (
            not r.get("category")
            and (
                "deploy" in r.get("test_name", "").lower()
                or "playbook" in r.get("test_name", "").lower()
            )
        )
    ]
    verify_results = [r for r in all_results if r not in deploy_results]

    test_id = test_id_start
    html += _generate_dv_section(deploy_results, mid, "deploy", test_id)
    test_id += len(deploy_results)
    html += _generate_dv_section(verify_results, mid, "verify", test_id)

    html += "</div></div>"
    return html


def _generate_dv_section(
    results: list, mid: str, section: str, test_id_start: int
) -> str:
    """Generate deploy/verify section HTML."""
    dv_id = f"{mid}-{section}"
    has_results = bool(results)

    if section == "deploy":
        icon_cls = "dv-deploy"
        icon = "&#9654;"
        label = "Deploy"
    else:
        icon_cls = "dv-verify"
        icon = SVG_CHECK
        label = "Verify"

    if has_results:
        html = (
            f'<div class="dv-sec" id="dv-{dv_id}">'
            f'<div class="dv-hdr" onclick="togDV(\'{dv_id}\')">'
            f'<span class="dv-arr">&#9660;</span>'
            f'<div class="dv-icon {icon_cls}">{icon}</div>'
            f"<span>{label}</span>"
            f'<span class="pill pp" style="margin-left:auto">{len(results)} test(s)</span>'
            f'</div><div class="dv-body">'
        )
        test_id = test_id_start
        for test in results:
            st = test.get("status", "FAILED")
            if st == "PASSED":
                icls, isvg = "ip", SVG_CHECK
            elif st == "SKIPPED":
                icls, isvg = "is", SVG_SKIP
            else:
                icls, isvg = "if", SVG_X
            html += _render_test_item(test_id, test, icls, isvg)
            test_id += 1
        html += "</div></div>"
    else:
        html = (
            f'<div class="dv-sec shut" id="dv-{dv_id}">'
            f'<div class="dv-hdr" onclick="togDV(\'{dv_id}\')">'
            f'<span class="dv-arr">&#9660;</span>'
            f'<div class="dv-icon dv-skip">&#8212;</div>'
            f"<span>{label}</span>"
            f'<span class="pill ps" style="margin-left:auto">skipped</span>'
            f'</div><div class="dv-body">'
            f'<div class="dv-skip-msg">No {section} tests executed</div>'
            f"</div></div>"
        )

    return html
