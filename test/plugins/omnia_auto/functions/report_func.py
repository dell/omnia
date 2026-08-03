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
Test Report Generator for the main module validation tests.

Generates JSON and HTML reports with:
- Dark/light theme toggle
- SVG donut charts with pass rate
- Scenario bar charts with hover tooltips
- Scenario trend sparklines across runs
- Duration bar charts for slowest scenarios
- Deploy/Verify section split
- Playbook log viewer
- Expandable test items with output and error details
- Server setup panel
- KPI cards

Reports are organized by server (IP/hostname) and stored under
the configured report_path (default: main/reports/).
"""

import json
import os
import re
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional


def _resolve_report_dir(report_path: str) -> str:
    """Ensure the report directory exists and return its absolute path."""
    os.makedirs(report_path, exist_ok=True)
    return report_path


def _load_report(report_dir: str, report_name: str) -> Dict[str, Any]:
    """Load existing report JSON if present."""
    report_file = os.path.join(report_dir, f"{report_name}.json")
    if os.path.exists(report_file):
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"servers": {}}
    return {"servers": {}}


def _save_json(data: Dict[str, Any], report_dir: str, report_name: str):
    """Save report data as JSON."""
    with open(os.path.join(report_dir, f"{report_name}.json"), "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)


_ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (color codes) from text."""
    return _ANSI_RE.sub('', text)


def _escape_html(text: str) -> str:
    """Strip ANSI codes then escape HTML special characters."""
    text = _strip_ansi(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# =============================================================================
# SVG CHART HELPERS
# =============================================================================

def _donut_svg(passed: int, failed: int, skipped: int, size: int = 160) -> str:
    """Return an inline SVG donut chart — text stays upright via counter-rotate."""
    total = passed + failed + skipped
    if total == 0:
        return ""
    r = 58
    cx = cy = size // 2
    circ = 2 * 3.14159265 * r
    arcs = []
    palette = [("#3fb950", passed, "Passed"), ("#f85149", failed, "Failed"), ("#e3b341", skipped, "Skipped")]
    offset = 0
    for color, count, label in palette:
        if count == 0:
            continue
        dash = circ * count / total
        gap = circ - dash
        arcs.append(
            f'<circle r="{r}" cx="{cx}" cy="{cy}" fill="none" stroke="{color}" '
            f'stroke-width="20" stroke-dasharray="{dash:.2f} {gap:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" stroke-linecap="round" class="donut-arc">'
            f'<title>{label}: {count} / {total}</title></circle>'
        )
        offset += dash
    executed = passed + failed
    pct = int(passed / executed * 100) if executed else (100 if skipped > 0 else 0)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" class="donut-chart">'
        + "".join(arcs)
        + f'<g transform="rotate(90 {cx} {cy})">'
        f'<text x="{cx}" y="{cy-8}" text-anchor="middle" dominant-baseline="central" '
        f'class="donut-pct">{pct}%</text>'
        f'<text x="{cx}" y="{cy+12}" text-anchor="middle" class="donut-lbl">pass rate</text>'
        f'</g></svg>'
    )


def _mini_donut(p: int, f: int, s: int) -> str:
    """Tiny 40px donut for hover tooltips."""
    t = p + f + s
    if t == 0:
        return ""
    r, cx, cy, sz = 14, 20, 20, 40
    circ = 2 * 3.14159265 * r
    arcs = []
    off = 0
    for col, n in [("#3fb950", p), ("#f85149", f), ("#e3b341", s)]:
        if n == 0:
            continue
        d = circ * n / t
        arcs.append(f'<circle r="{r}" cx="{cx}" cy="{cy}" fill="none" stroke="{col}" '
                     f'stroke-width="6" stroke-dasharray="{d:.1f} {circ-d:.1f}" '
                     f'stroke-dashoffset="{-off:.1f}"/>')
        off += d
    ex = p + f
    pct = int(p / ex * 100) if ex else (100 if s > 0 else 0)
    return (f'<svg width="{sz}" height="{sz}" viewBox="0 0 {sz} {sz}" '
            f'style="transform:rotate(-90deg);flex-shrink:0">'
            + "".join(arcs)
            + f'<text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central" '
            f'fill="var(--fg)" font-size="9" font-weight="700" '
            f'style="transform:rotate(90deg);transform-origin:{cx}px {cy}px">{pct}%</text></svg>')


def _scenario_bar_chart(modules: List[Dict[str, Any]]) -> str:
    """Stacked-bar rows per scenario with hover popup showing mini donut + details."""
    if not modules:
        return ""
    rows = ""
    for m in modules:
        s = m.get("summary") or {}
        p, f, sk = s.get("passed", 0), s.get("failed", 0), s.get("skipped", 0)
        t = p + f + sk or 1
        name = m.get("module", "unknown")
        dot_cls = "dot-pass" if f == 0 else "dot-fail"
        mini = _mini_donut(p, f, sk)
        suite_val = m.get("suite", "all")
        marker_val = m.get("marker", "")
        cmd_val = m.get("exec_command", "")
        ctx_lines = f'<div class="tip-ctx">Suite: <b>{suite_val}</b></div>'
        if marker_val:
            ctx_lines += f'<div class="tip-ctx">Marker: <b>{marker_val}</b></div>'
        if cmd_val:
            ctx_lines += f'<div class="tip-ctx">Command: <b>{cmd_val}</b></div>'
        rows += (
            f'<div class="bar-row">'
            f'<span class="bar-dot {dot_cls}"></span>'
            f'<span class="bar-label">{name}</span>'
            f'<div class="bar-track">'
            f'<div class="bar-seg bar-pass" style="width:{p/t*100:.1f}%"></div>'
            f'<div class="bar-seg bar-fail" style="width:{f/t*100:.1f}%"></div>'
            f'<div class="bar-seg bar-skip" style="width:{sk/t*100:.1f}%"></div>'
            f'</div>'
            f'<span class="bar-nums"><span class="c-pass">{p}</span>'
            f'<span class="c-fail">{f}</span>'
            f'<span class="c-skip">{sk}</span></span>'
            f'<div class="bar-tip">'
            f'<div class="tip-head">{name}</div>'
            f'{ctx_lines}'
            f'<div class="tip-body">{mini}'
            f'<div class="tip-stats">'
            f'<div class="tip-r"><span class="tip-d" style="background:var(--green)"></span>Passed<b>{p}</b></div>'
            f'<div class="tip-r"><span class="tip-d" style="background:var(--red)"></span>Failed<b>{f}</b></div>'
            f'<div class="tip-r"><span class="tip-d" style="background:var(--yellow)"></span>Skipped<b>{sk}</b></div>'
            f'</div></div></div>'
            f'</div>'
        )
    return f'<div class="scenario-bars">{rows}</div>'


def _sparkline_svg(rates: List[float], w: int = 120, h: int = 28) -> str:
    """Inline SVG sparkline of pass-rate history (0-100) across runs."""
    if not rates:
        return ""
    if len(rates) == 1:
        rates = [rates[0], rates[0]]
    n = len(rates)
    pad = 3
    span_w = w - 2 * pad
    span_h = h - 2 * pad
    pts = []
    for i, r in enumerate(rates):
        x = pad + (span_w * i / (n - 1))
        y = pad + span_h * (1 - max(0.0, min(100.0, r)) / 100.0)
        pts.append((x, y))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad},{h - pad} " + line + f" {w - pad},{h - pad}"
    last_x, last_y = pts[-1]
    last_rate = rates[-1]
    stroke = "#3fb950" if last_rate >= 99.9 else ("#e3b341" if last_rate >= 50 else "#f85149")
    return (
        f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<polygon points="{area}" fill="{stroke}" opacity="0.12"/>'
        f'<polyline points="{line}" fill="none" stroke="{stroke}" '
        f'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.6" fill="{stroke}"/>'
        f'</svg>'
    )


def _aggregate_scenarios(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse all runs into per-scenario history (chronological order)."""
    order: List[str] = []
    agg: Dict[str, Dict[str, Any]] = {}
    for run in runs:
        modules = run.get("modules", [])
        if not modules and "results" in run:
            modules = [{
                "module": run.get("module", "unknown"),
                "summary": run.get("summary", {}),
                "duration_seconds": run.get("total_duration_seconds", 0),
            }]
        for m in modules:
            name = m.get("module", "unknown")
            s = m.get("summary") or {}
            p, f, sk = s.get("passed", 0), s.get("failed", 0), s.get("skipped", 0)
            executed = p + f
            rate = (p / executed * 100) if executed else (100.0 if sk > 0 else 0.0)
            if name not in agg:
                order.append(name)
                agg[name] = {
                    "module": name, "history": [], "runs": 0,
                    "passed": 0, "failed": 0, "skipped": 0, "duration": 0.0,
                    "suite": m.get("suite", "all"), "marker": m.get("marker", ""),
                }
            entry = agg[name]
            entry["history"].append(round(rate, 1))
            entry["runs"] += 1
            entry["passed"], entry["failed"], entry["skipped"] = p, f, sk
            entry["duration"] += m.get("duration_seconds", 0) or 0
    return [agg[n] for n in order]


def _scenario_trends(runs: List[Dict[str, Any]]) -> str:
    """Scenario-centric trend panel: sparkline of pass-rate history per scenario."""
    scenarios = _aggregate_scenarios(runs)
    if not scenarios:
        return ""
    rows = ""
    for sc in scenarios:
        name = sc["module"]
        hist = sc["history"]
        latest = hist[-1] if hist else 0.0
        prev = hist[-2] if len(hist) > 1 else latest
        delta = latest - prev
        if delta > 0.05:
            trend_cls, trend_sym = "tr-up", "&#9650;"
        elif delta < -0.05:
            trend_cls, trend_sym = "tr-down", "&#9660;"
        else:
            trend_cls, trend_sym = "tr-flat", "&#9644;"
        rate_cls = "c-pass" if latest >= 99.9 else ("c-skip" if latest >= 50 else "c-fail")
        rows += (
            f'<div class="trend-row">'
            f'<span class="trend-name">{name}</span>'
            f'<span class="trend-suite">{sc["suite"]}</span>'
            f'{_sparkline_svg(hist)}'
            f'<span class="trend-rate {rate_cls}">{latest:.0f}%</span>'
            f'<span class="trend-delta {trend_cls}">{trend_sym} {abs(delta):.0f}%</span>'
            f'<span class="trend-runs">{sc["runs"]} run(s)</span>'
            f'</div>'
        )
    return (
        '<div class="trend-card">'
        '<div class="trend-hdr"><span>Scenario Trends</span>'
        '<span class="trend-sub">pass-rate history across runs</span></div>'
        f'<div class="trend-body">{rows}</div>'
        '</div>'
    )


def _duration_bars(modules: List[Dict[str, Any]], top: int = 8) -> str:
    """Horizontal bar chart of the slowest scenarios in a run (by duration)."""
    if not modules:
        return ""
    items = [(m.get("module", "unknown"), float(m.get("duration_seconds", 0) or 0)) for m in modules]
    items = [it for it in items if it[1] > 0]
    if not items:
        return ""
    items.sort(key=lambda x: x[1], reverse=True)
    items = items[:top]
    peak = items[0][1] or 1
    rows = ""
    for name, dur in items:
        pct = dur / peak * 100
        rows += (
            f'<div class="dur-row">'
            f'<span class="dur-name">{name}</span>'
            f'<div class="dur-track"><div class="dur-fill" style="width:{pct:.1f}%"></div></div>'
            f'<span class="dur-val">{dur:.1f}s</span>'
            f'</div>'
        )
    return (
        '<div class="dur-chart">'
        '<div class="dur-hdr">Slowest Scenarios</div>'
        f'{rows}</div>'
    )


def _marker_folder_breakdown(modules: List[Dict[str, Any]]) -> str:
    """Generate a marker and folder breakdown table for the run."""
    if not modules:
        return ""

    # Collect all results with their markers and folders
    marker_stats: Dict[str, Dict[str, int]] = {}
    folder_stats: Dict[str, Dict[str, int]] = {}

    for mod in modules:
        results = mod.get("results", [])
        for r in results:
            st = r.get("status", "FAILED")
            # Folder breakdown from test_name path
            tname = r.get("test_name", "")
            parts = tname.split("::")[0].split("/") if "::" in tname else []
            folder = "/".join(parts[:-1]) if len(parts) > 1 else mod.get("module", "unknown")
            if folder not in folder_stats:
                folder_stats[folder] = {"passed": 0, "failed": 0, "skipped": 0}
            folder_stats[folder][st.lower()] = folder_stats[folder].get(st.lower(), 0) + 1

            # Marker breakdown from test markers (stored in result)
            markers = r.get("markers", [])
            if not markers:
                markers = ["unmarked"]
            for mk in markers:
                if mk not in marker_stats:
                    marker_stats[mk] = {"passed": 0, "failed": 0, "skipped": 0}
                marker_stats[mk][st.lower()] = marker_stats[mk].get(st.lower(), 0) + 1

    # Collect suite/marker from modules for summary
    suites_used = set()
    markers_used = set()
    for mod in modules:
        s = mod.get("suite", "")
        m = mod.get("marker", "")
        if s:
            suites_used.add(s)
        if m:
            markers_used.add(m)

    html = '<div class="breakdown">'

    # Suite/Marker summary line
    suite_str = ", ".join(sorted(suites_used)) if suites_used else "all"
    marker_str = ", ".join(sorted(markers_used)) if markers_used else "none"
    html += (
        f'<div style="width:100%;font-size:.82em;color:var(--fg-muted);padding-bottom:8px;border-bottom:1px solid var(--border);margin-bottom:8px">'
        f'<b>Suite:</b> <span style="color:var(--blue)">{suite_str}</span>'
        f'&nbsp;&nbsp;&bull;&nbsp;&nbsp;<b>Marker:</b> <span style="color:var(--purple)">{marker_str}</span>'
        f'</div>'
    )

    # Folder breakdown
    if folder_stats:
        html += '<div class="bd-section"><div class="bd-title">&#128193; Folder Breakdown</div><table class="bd-table">'
        html += '<tr><th>Folder</th><th class="c-pass">Pass</th><th class="c-fail">Fail</th><th class="c-skip">Skip</th><th>Total</th></tr>'
        for folder, stats in sorted(folder_stats.items()):
            p, f, s = stats.get("passed", 0), stats.get("failed", 0), stats.get("skipped", 0)
            t = p + f + s
            row_cls = "bd-fail" if f > 0 else "bd-pass"
            html += f'<tr class="{row_cls}"><td class="bd-name">{folder}</td><td>{p}</td><td>{f}</td><td>{s}</td><td><b>{t}</b></td></tr>'
        html += '</table></div>'

    # Marker breakdown
    if marker_stats:
        html += '<div class="bd-section"><div class="bd-title">&#127991; Marker Breakdown</div><table class="bd-table">'
        html += '<tr><th>Marker</th><th class="c-pass">Pass</th><th class="c-fail">Fail</th><th class="c-skip">Skip</th><th>Total</th></tr>'
        for mk, stats in sorted(marker_stats.items()):
            p, f, s = stats.get("passed", 0), stats.get("failed", 0), stats.get("skipped", 0)
            t = p + f + s
            row_cls = "bd-fail" if f > 0 else "bd-pass"
            html += f'<tr class="{row_cls}"><td class="bd-name">{mk}</td><td>{p}</td><td>{f}</td><td>{s}</td><td><b>{t}</b></td></tr>'
        html += '</table></div>'

    html += '</div>'
    return html


def _fmt_run_id(rid: str) -> str:
    """Format compact run ID 20260708131458 into 2026-07-08 13:14:58."""
    if len(rid) == 14 and rid.isdigit():
        return f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}  {rid[8:10]}:{rid[10:12]}:{rid[12:14]}"
    return rid


def _render_test_item(test_id: int, test: Dict[str, Any], icls: str, isvg: str) -> str:
    """Render a single test item row with expandable details."""
    html = (
        f'<div class="ti" id="t-{test_id}">'
        f'<div class="tr" onclick="togT(event,{test_id})">'
        f'<span class="tr-arr">&#9654;</span>'
        f'<div class="tr-icon {icls}">{isvg}</div>'
        f'<div class="tr-name">{test["test_name"]}</div>'
        f'<div class="tr-dur">{test.get("duration_seconds",0)}s</div>'
        f'</div><div class="ti-out">'
    )
    if test.get("details") or test.get("error"):
        if test.get("details"):
            o = _escape_html(test["details"])
            o = o.replace("\u2714 PASS:", "<span class='hi-p'>\u2714 PASS:</span>")
            o = o.replace("\u2718 FAIL:", "<span class='hi-f'>\u2718 FAIL:</span>")
            o = o.replace("\u21b7 SKIP:", "<span class='hi-s'>\u21b7 SKIP:</span>")
            o = o.replace("SKIP:", "<span class='hi-s'>SKIP:</span>")
            o = o.replace("\u2192", "<span class='hi-a'>\u2192</span>")
            html += f'<div class="obox">{o}</div>'
        if test.get("error"):
            html += f'<div class="ebox">{_escape_html(test["error"][:800])}</div>'
    else:
        html += '<div class="obox" style="color:var(--fg-muted)">No detailed output available</div>'
    html += '</div></div>'
    return html


# =============================================================================
# HTML GENERATION
# =============================================================================

def _generate_html(data: Dict[str, Any]) -> str:
    """Generate modern HTML report with theme toggle, hover charts, polished UI."""
    generated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html = f'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Omnia Test Report</title>
<style>
/* -- Theme variables -- */
[data-theme="dark"] {{
  --bg-canvas:#0d1117; --bg-card:#161b22; --bg-header:#1c2128;
  --bg-hover:#21262d; --border:#30363d; --fg:#e6edf3; --fg-muted:#7d8590;
  --green:#3fb950; --green-bg:rgba(63,185,80,.15);
  --red:#f85149; --red-bg:rgba(248,81,73,.15);
  --yellow:#e3b341; --yellow-bg:rgba(227,179,65,.15);
  --blue:#58a6ff; --blue-bg:rgba(88,166,255,.12);
  --purple:#bc8cff; --purple-bg:rgba(188,140,255,.12);
  --orange:#f0883e; --shadow:rgba(0,0,0,.3);
}}
[data-theme="light"] {{
  --bg-canvas:#f6f8fa; --bg-card:#ffffff; --bg-header:#f0f3f6;
  --bg-hover:#e8ecf0; --border:#d0d7de; --fg:#1f2328; --fg-muted:#656d76;
  --green:#1a7f37; --green-bg:rgba(26,127,55,.12);
  --red:#cf222e; --red-bg:rgba(207,34,46,.1);
  --yellow:#9a6700; --yellow-bg:rgba(154,103,0,.1);
  --blue:#0969da; --blue-bg:rgba(9,105,218,.08);
  --purple:#8250df; --purple-bg:rgba(130,80,223,.08);
  --orange:#bc4c00; --shadow:rgba(0,0,0,.08);
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg-canvas);color:var(--fg);line-height:1.6;font-size:15px;transition:background .25s,color .25s}}
.container{{max-width:1480px;margin:0 auto;padding:24px}}
.hdr{{background:var(--bg-card);padding:24px 32px;border-radius:12px;margin-bottom:24px;border:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;box-shadow:0 2px 8px var(--shadow)}}
.hdr-left{{display:flex;align-items:center;gap:14px}}
.hdr h1{{font-size:1.5em;font-weight:700}}
.logo{{width:38px;height:38px;background:linear-gradient(135deg,var(--green),var(--blue));border-radius:10px;display:grid;place-items:center;font-size:20px;color:#fff;flex-shrink:0}}
.hdr .sub{{color:var(--fg-muted);font-size:.85em;margin-top:2px}}
.theme-btn{{background:var(--bg-hover);border:1px solid var(--border);border-radius:8px;padding:8px 14px;cursor:pointer;color:var(--fg);font-size:.85em;display:flex;align-items:center;gap:6px;transition:all .15s}}
.theme-btn:hover{{background:var(--blue-bg);border-color:var(--blue)}}
.lay{{display:flex;gap:22px}}
.side{{width:280px;flex-shrink:0}}
.main{{flex:1;min-width:0}}
.srv-list{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;overflow:hidden;position:sticky;top:20px;box-shadow:0 1px 4px var(--shadow)}}
.srv-list h3{{padding:14px 18px;background:var(--bg-header);font-size:.82em;letter-spacing:.5px;text-transform:uppercase;color:var(--fg-muted);border-bottom:1px solid var(--border)}}
.srv{{padding:14px 18px;border-bottom:1px solid var(--border);cursor:pointer;transition:all .15s}}
.srv:last-child{{border-bottom:none}}
.srv:hover{{background:var(--bg-hover)}}
.srv.act{{background:var(--blue-bg);border-left:3px solid var(--blue)}}
.srv-ip{{font-family:'Cascadia Code','SF Mono',monospace;font-size:.92em;color:var(--blue);font-weight:600}}
.srv-host{{font-size:.8em;color:var(--fg-muted);margin-top:2px}}
.srv-stats{{display:flex;gap:12px;margin-top:6px;font-size:.78em;font-weight:600}}
.srv-stats .p{{color:var(--green)}} .srv-stats .f{{color:var(--red)}} .srv-stats .s{{color:var(--yellow)}}
.panel{{display:none}} .panel.act{{display:block}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:22px}}
.kpi{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px 14px;text-align:center;position:relative;overflow:hidden;box-shadow:0 1px 4px var(--shadow);transition:transform .15s,box-shadow .15s}}
.kpi:hover{{transform:translateY(-2px);box-shadow:0 4px 12px var(--shadow)}}
.kpi::before{{content:'';position:absolute;left:0;top:0;bottom:0;width:4px}}
.kpi.kp::before{{background:var(--green)}} .kpi.kf::before{{background:var(--red)}}
.kpi.ks::before{{background:var(--yellow)}} .kpi.kt::before{{background:var(--blue)}}
.kpi .n{{font-size:2.2em;font-weight:800;line-height:1}}
.kpi.kp .n{{color:var(--green)}} .kpi.kf .n{{color:var(--red)}}
.kpi.ks .n{{color:var(--yellow)}} .kpi.kt .n{{color:var(--blue)}}
.kpi .l{{color:var(--fg-muted);text-transform:uppercase;font-size:.68em;letter-spacing:1.2px;margin-top:4px;font-weight:600}}
.run{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;margin-bottom:16px;overflow:hidden;box-shadow:0 1px 4px var(--shadow)}}
.run-h{{padding:16px 20px;cursor:pointer;transition:background .15s;display:flex;align-items:center;gap:12px}}
.run-h:hover{{background:var(--bg-hover)}}
.run-h .arr{{color:var(--fg-muted);font-size:.75em;transition:transform .2s;width:18px}}
.run.shut .arr{{transform:rotate(-90deg)}} .run.shut .run-b{{display:none}}
.run-title{{font-weight:600;font-size:.95em;flex:1;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.run-title .rid{{font-family:'Cascadia Code',monospace;color:var(--purple);font-weight:700;font-size:.95em}}
.pill{{display:inline-flex;align-items:center;gap:4px;padding:3px 12px;border-radius:20px;font-size:.78em;font-weight:700;transition:transform .1s}}
.pill:hover{{transform:scale(1.05)}}
.pill.pp{{background:var(--green-bg);color:var(--green)}}
.pill.pf{{background:var(--red-bg);color:var(--red)}}
.pill.ps{{background:var(--yellow-bg);color:var(--yellow)}}
.run-info{{display:flex;gap:14px;font-size:.8em;color:var(--fg-muted);padding:0 20px 10px 50px}}
.run-b{{border-top:1px solid var(--border)}}
.overview{{display:flex;gap:28px;padding:22px 24px;align-items:center;background:var(--bg-header);border-bottom:1px solid var(--border);flex-wrap:wrap}}
.donut-chart{{transform:rotate(-90deg)}}
.donut-arc{{transition:opacity .15s}} .donut-arc:hover{{opacity:.75}}
.donut-pct{{fill:var(--fg);font-size:30px;font-weight:800;font-family:system-ui,sans-serif}}
.donut-lbl{{fill:var(--fg-muted);font-size:11px;font-family:system-ui,sans-serif}}
.scenario-bars{{flex:1;min-width:260px}}
.bar-row{{display:flex;align-items:center;gap:10px;padding:5px 0;font-size:.85em;position:relative}}
.bar-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.dot-pass{{background:var(--green)}} .dot-fail{{background:var(--red)}}
.bar-label{{width:160px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:'Cascadia Code',monospace;font-size:.9em;color:var(--fg);font-weight:500}}
.bar-track{{flex:1;height:10px;background:var(--bg-hover);border-radius:5px;overflow:hidden;display:flex}}
.bar-seg{{height:100%;transition:width .4s ease}}
.bar-pass{{background:var(--green)}} .bar-fail{{background:var(--red)}} .bar-skip{{background:var(--yellow)}}
.bar-nums{{font-size:.82em;font-family:monospace;width:80px;text-align:right;flex-shrink:0;display:flex;gap:5px;justify-content:flex-end;font-weight:600}}
.c-pass{{color:var(--green)}} .c-fail{{color:var(--red)}} .c-skip{{color:var(--yellow)}}
.bar-tip{{display:none;position:absolute;top:100%;left:50%;transform:translateX(-50%);z-index:100;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px;min-width:200px;box-shadow:0 8px 24px var(--shadow);pointer-events:none}}
.bar-row:hover .bar-tip{{display:block}}
.tip-head{{font-weight:700;font-size:.9em;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border);color:var(--blue)}}
.tip-body{{display:flex;align-items:center;gap:12px}}
.tip-stats{{display:flex;flex-direction:column;gap:4px}}
.tip-r{{display:flex;align-items:center;gap:6px;font-size:.82em}}
.tip-r b{{margin-left:auto;font-weight:700;min-width:20px;text-align:right}}
.tip-d{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.tip-ctx{{font-size:.78em;color:var(--fg-muted);padding:2px 0}}
.tip-ctx b{{color:var(--fg);font-weight:600;margin-left:4px}}
.mod{{border-bottom:1px solid var(--border)}}
.mod:last-child{{border-bottom:none}}
.mod-h{{display:flex;align-items:center;padding:12px 20px;cursor:pointer;transition:background .15s;gap:10px}}
.mod-h:hover{{background:var(--bg-hover)}}
.mod-arr{{color:var(--fg-muted);font-size:.75em;transition:transform .15s;width:16px}}
.mod.shut .mod-arr{{transform:rotate(-90deg)}} .mod.shut .mod-b{{display:none}}
.mod-icon{{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-size:12px;background:var(--orange);color:#fff;flex-shrink:0}}
.mod-name{{font-family:'Cascadia Code',monospace;font-size:.92em;color:var(--blue);font-weight:600}}
.mod-dur{{color:var(--fg-muted);font-size:.8em;margin-left:auto;font-family:monospace}}
.mod-b{{background:var(--bg-canvas)}}
.mod-meta{{display:flex;gap:8px;align-items:center;padding:6px 20px 6px 52px;font-size:.78em;color:var(--fg-muted);border-bottom:1px solid var(--border);background:var(--bg-header)}}
.meta-tag{{background:var(--purple-bg);color:var(--purple);padding:2px 10px;border-radius:12px;font-weight:600;font-size:.82em}}
.dv-sec{{border-top:1px solid var(--border)}}
.dv-hdr{{display:flex;align-items:center;gap:8px;padding:8px 20px;cursor:pointer;font-size:.85em;font-weight:600;color:var(--fg-muted);background:var(--bg-header);border-bottom:1px solid var(--border);transition:background .15s}}
.dv-hdr:hover{{background:var(--bg-hover)}}
.dv-hdr .dv-arr{{font-size:.65em;transition:transform .15s;width:14px;color:var(--fg-muted)}}
.dv-icon{{width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-size:10px;color:#fff;flex-shrink:0}}
.dv-icon.dv-deploy{{background:var(--blue)}}
.dv-icon.dv-verify{{background:var(--green)}}
.dv-icon.dv-skip{{background:var(--fg-muted)}}
.dv-body{{}} .dv-sec.shut .dv-body{{display:none}} .dv-sec.shut .dv-arr{{transform:rotate(-90deg)}}
.dv-skip-msg{{padding:12px 20px 12px 52px;font-size:.85em;color:var(--fg-muted);font-style:italic}}
.plogs{{border-top:1px solid var(--border)}}
.plogs-h{{display:flex;align-items:center;padding:10px 20px;cursor:pointer;gap:10px;transition:background .15s}}
.plogs-h:hover{{background:var(--bg-hover)}}
.plogs-arr{{color:var(--fg-muted);font-size:.75em;transition:transform .15s}}
.plogs.shut .plogs-arr{{transform:rotate(0deg)}}
.plogs:not(.shut) .plogs-arr{{transform:rotate(90deg)}}
.plogs.shut .plogs-b{{display:none !important}}
.plogs-title{{flex:1;font-size:.88em;color:var(--fg-muted)}}
.plogs-b pre{{background:var(--bg-canvas);border:1px solid var(--border);border-radius:8px;padding:14px;font-family:'Cascadia Code',monospace;font-size:.78em;white-space:pre-wrap;word-break:break-word;max-height:400px;overflow-y:auto;line-height:1.4;margin:10px 16px 14px}}
.ti{{border-bottom:1px solid var(--border)}}
.ti:last-child{{border-bottom:none}}
.tr{{display:flex;align-items:center;padding:10px 20px 10px 32px;cursor:pointer;transition:background .12s;gap:10px}}
.tr:hover{{background:var(--bg-hover)}}
.tr-arr{{color:var(--fg-muted);font-size:.65em;transition:transform .15s;width:14px}}
.ti.open .tr-arr{{transform:rotate(90deg)}}
.tr-icon{{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;flex-shrink:0}}
.tr-icon.ip{{background:var(--green);color:#fff}} .tr-icon.if{{background:var(--red);color:#fff}}
.tr-icon.is{{background:var(--yellow);color:#000}}
.tr-icon svg{{width:14px;height:14px;fill:currentColor}}
.tr-name{{flex:1;font-size:.92em}}
.tr-dur{{color:var(--fg-muted);font-size:.8em;font-family:monospace;min-width:60px;text-align:right}}
.ti-out{{display:none;padding:8px 20px 12px 56px}}
.ti.open .ti-out{{display:block}}
.obox{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px;font-family:'Cascadia Code',monospace;font-size:.8em;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow-y:auto;line-height:1.45}}
.ebox{{background:var(--red-bg);border:1px solid rgba(248,81,73,.3);border-radius:8px;padding:12px;margin-top:8px;font-family:monospace;font-size:.8em;white-space:pre-wrap;word-break:break-all;max-height:160px;overflow-y:auto;color:var(--red)}}
.obox .hi-p{{color:var(--green);font-weight:700}} .obox .hi-f{{color:var(--red);font-weight:700}}
.obox .hi-s{{color:var(--yellow)}} .obox .hi-a{{color:var(--blue)}}
.sdot{{width:18px;height:18px;border-radius:50%;display:grid;place-items:center;flex-shrink:0}}
.sdot.sp{{background:var(--green);color:#fff}} .sdot.sf{{background:var(--red);color:#fff}}
.sdot svg{{width:10px;height:10px;fill:currentColor}}
.legend{{display:flex;gap:16px;padding:10px 24px;font-size:.82em;color:var(--fg-muted);border-bottom:1px solid var(--border);background:var(--bg-header)}}
.legend-item{{display:flex;align-items:center;gap:5px}}
.legend-dot{{width:10px;height:10px;border-radius:50%}}
.trend-card{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;margin-bottom:22px;overflow:hidden;box-shadow:0 1px 4px var(--shadow)}}
.trend-hdr{{display:flex;align-items:baseline;gap:10px;padding:14px 20px;background:var(--bg-header);border-bottom:1px solid var(--border)}}
.trend-hdr span:first-child{{font-weight:700;font-size:.95em}}
.trend-sub{{color:var(--fg-muted);font-size:.78em}}
.trend-body{{padding:6px 12px}}
.trend-row{{display:flex;align-items:center;gap:12px;padding:8px 8px;border-bottom:1px solid var(--border)}}
.trend-row:last-child{{border-bottom:none}}
.trend-row:hover{{background:var(--bg-hover)}}
.trend-name{{width:200px;flex-shrink:0;font-family:'Cascadia Code',monospace;font-size:.85em;color:var(--blue);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.trend-suite{{width:70px;flex-shrink:0;font-size:.72em;color:var(--fg-muted);text-transform:uppercase;letter-spacing:.4px}}
.spark{{flex-shrink:0}}
.trend-rate{{width:52px;text-align:right;font-weight:800;font-size:.95em;font-family:monospace}}
.trend-delta{{width:64px;text-align:right;font-size:.78em;font-weight:700;font-family:monospace}}
.tr-up{{color:var(--green)}} .tr-down{{color:var(--red)}} .tr-flat{{color:var(--fg-muted)}}
.trend-runs{{margin-left:auto;font-size:.76em;color:var(--fg-muted)}}
.dur-chart{{flex:1;min-width:260px}}
.dur-hdr{{font-size:.82em;font-weight:600;color:var(--fg-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
.dur-row{{display:flex;align-items:center;gap:10px;padding:3px 0;font-size:.82em}}
.dur-name{{width:150px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:'Cascadia Code',monospace;font-size:.9em;color:var(--fg)}}
.dur-track{{flex:1;height:8px;background:var(--bg-hover);border-radius:4px;overflow:hidden}}
.dur-fill{{height:100%;background:linear-gradient(90deg,var(--blue),var(--purple));border-radius:4px;transition:width .4s ease}}
.dur-val{{width:60px;text-align:right;font-family:monospace;font-size:.85em;color:var(--fg-muted);flex-shrink:0}}
.setup-panel{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;margin-bottom:16px;overflow:hidden;box-shadow:0 1px 4px var(--shadow)}}
.setup-hdr{{display:flex;align-items:center;gap:10px;padding:14px 20px;border-bottom:1px solid var(--border);background:var(--bg-header)}}
.setup-icon{{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;font-size:14px;color:#fff;flex-shrink:0}}
.setup-icon.sok{{background:var(--green)}} .setup-icon.serr{{background:var(--red)}} .setup-icon.swarn{{background:var(--yellow)}}
.setup-title{{font-weight:700;font-size:.95em;flex:1}}
.setup-status{{font-size:.82em;font-weight:600;padding:4px 14px;border-radius:20px}}
.setup-status.s-pass{{background:var(--green-bg);color:var(--green)}}
.setup-status.s-fail{{background:var(--red-bg);color:var(--red)}}
.setup-status.s-warn{{background:var(--yellow-bg);color:var(--yellow)}}
.setup-body{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;padding:16px 20px}}
.setup-check{{display:flex;align-items:center;gap:8px;padding:10px 14px;border-radius:8px;border:1px solid var(--border);background:var(--bg-canvas);font-size:.85em;transition:transform .12s}}
.setup-check:hover{{transform:translateY(-1px);box-shadow:0 2px 8px var(--shadow)}}
.setup-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.setup-dot.dp{{background:var(--green)}} .setup-dot.df{{background:var(--red)}} .setup-dot.ds{{background:var(--yellow)}}
.setup-cname{{flex:1;font-family:'Cascadia Code',monospace;font-size:.9em}}
.setup-cdur{{color:var(--fg-muted);font-size:.8em;font-family:monospace}}
.setup-summary{{display:flex;gap:16px;padding:10px 20px;border-top:1px solid var(--border);font-size:.82em;color:var(--fg-muted);background:var(--bg-header)}}
.ft{{text-align:center;padding:20px;color:var(--fg-muted);font-size:.82em;border-top:1px solid var(--border);margin-top:32px}}
.breakdown{{display:flex;gap:16px;padding:16px 20px;flex-wrap:wrap;border-bottom:1px solid var(--border);background:var(--bg-header)}}
.bd-section{{flex:1;min-width:260px}}
.bd-title{{font-size:.82em;font-weight:700;color:var(--fg-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
.bd-table{{width:100%;border-collapse:collapse;font-size:.82em;font-family:'Cascadia Code',monospace}}
.bd-table th{{text-align:left;padding:6px 10px;border-bottom:2px solid var(--border);font-weight:700;font-size:.78em;text-transform:uppercase;letter-spacing:.3px;color:var(--fg-muted)}}
.bd-table td{{padding:5px 10px;border-bottom:1px solid var(--border)}}
.bd-table tr:hover{{background:var(--bg-hover)}}
.bd-name{{font-weight:600;color:var(--fg);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.bd-pass td:first-child{{border-left:3px solid var(--green)}}
.bd-fail td:first-child{{border-left:3px solid var(--red)}}
@media(max-width:920px){{.lay{{flex-direction:column}}.side{{width:100%}}.breakdown{{flex-direction:column}}}}
</style>
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
'''

    svg_check = '<svg viewBox="0 0 16 16"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>'
    svg_x = '<svg viewBox="0 0 16 16"><path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z"/></svg>'
    svg_skip = '<svg viewBox="0 0 16 16"><path d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/><path d="M4.5 7.25h7a.75.75 0 010 1.5h-7a.75.75 0 010-1.5z"/></svg>'

    servers = data.get("servers", {})
    if not servers:
        html += '<div style="text-align:center;padding:60px 20px;color:var(--fg-muted);font-size:1.1em">No test results yet. Run tests to generate report.</div>'
    else:
        html += '<div class="lay"><div class="side"><div class="srv-list"><h3>Targets</h3>'

        _SETUP_MODULE = "oim_prereq_test"

        first_server = True
        for sip, sd in servers.items():
            hostname = sd.get("hostname", "")
            runs = sd.get("runs", [])
            tp = tf = ts = 0
            for r in runs:
                for m in (r.get("modules") or []):
                    if m.get("module") == _SETUP_MODULE:
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
                for m in (r.get("modules") or []):
                    if m.get("module") == _SETUP_MODULE:
                        setup_results_all.extend(m.get("results", []))

            tp = tf = tsk = 0
            for r in runs:
                modules = r.get("modules") or []
                if not modules and "results" in r:
                    modules = [{"module": r.get("module", "unknown"), "summary": r["summary"]}]
                for m in modules:
                    if m.get("module") == _SETUP_MODULE:
                        continue
                    ms = m.get("summary") or {}
                    tp += ms.get("passed", 0)
                    tf += ms.get("failed", 0)
                    tsk += ms.get("skipped", 0)
            ttl = tp + tf + tsk
            act = "act" if first_server else ""

            executed_total = tp + tf
            pass_rate = int(tp / executed_total * 100) if executed_total else (100 if tsk > 0 else 0)
            total_dur = sum(
                sum(m.get("duration_seconds", 0) or 0 for m in (
                    r.get("modules") or [{"duration_seconds": r.get("total_duration_seconds", 0)}]
                ))
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
                f'</div>'
            )

            if setup_results_all:
                s_pass = sum(1 for r in setup_results_all if r.get("status") == "PASSED")
                s_fail = sum(1 for r in setup_results_all if r.get("status") == "FAILED")
                s_skip = sum(1 for r in setup_results_all if r.get("status") == "SKIPPED")
                s_total = len(setup_results_all)
                if s_fail > 0:
                    s_icon_cls, s_icon, s_stat_cls, s_stat_txt = "serr", "&#10007;", "s-fail", f"{s_fail} check(s) failed"
                elif s_skip > 0 and s_pass == 0:
                    s_icon_cls, s_icon, s_stat_cls, s_stat_txt = "swarn", "&#8212;", "s-warn", "Checks skipped"
                else:
                    s_icon_cls, s_icon, s_stat_cls, s_stat_txt = "sok", "&#10003;", "s-pass", "All checks passed"

                html += (
                    f'<div class="setup-panel"><div class="setup-hdr">'
                    f'<div class="setup-icon {s_icon_cls}">{s_icon}</div>'
                    f'<span class="setup-title">Server Setup</span>'
                    f'<span class="setup-status {s_stat_cls}">{s_stat_txt}</span>'
                    f'</div><div class="setup-body">'
                )
                for sr in setup_results_all:
                    st = sr.get("status", "FAILED")
                    dot = "dp" if st == "PASSED" else ("ds" if st == "SKIPPED" else "df")
                    name = sr.get("test_name", "unknown").split("::")[-1].replace("test_", "").replace("_", " ").title()
                    dur = sr.get("duration_seconds", 0)
                    html += (
                        f'<div class="setup-check">'
                        f'<div class="setup-dot {dot}"></div>'
                        f'<span class="setup-cname">{name}</span>'
                        f'<span class="setup-cdur">{dur:.1f}s</span></div>'
                    )
                html += (
                    f'</div><div class="setup-summary">'
                    f'<span><b>{s_pass}</b> passed</span>'
                    f'<span><b>{s_fail}</b> failed</span>'
                    f'<span><b>{s_skip}</b> skipped</span>'
                    f'<span style="margin-left:auto"><b>{s_total}</b> checks</span>'
                    f'</div></div>'
                )

            run_idx = 0
            for run in reversed(runs):
                run_idx += 1
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
                    modules = [{"module": run.get("module", "unknown"), "results": run["results"],
                                "summary": run["summary"], "duration_seconds": run.get("total_duration_seconds", 0)}]

                tdur = sum(m.get("duration_seconds", 0) for m in modules)
                rid = run.get("report_id", "")
                disp_rid = _fmt_run_id(rid)

                html += (
                    f'<div class="run {shut}" id="r-{uid}">'
                    f'<div class="run-h" onclick="togRun(\'{uid}\')">'
                    f'<span class="arr">&#9660;</span>'
                    f'<div class="run-title">'
                    f'<span class="rid">{rid}</span>'
                    f'<span style="color:var(--fg-muted);font-size:.82em">{disp_rid}</span>'
                    f'{pills}'
                    f'<span style="color:var(--fg-muted);font-size:.8em;margin-left:8px">{len(modules)} scenario(s)</span>'
                    f'</div></div>'
                    f'<div class="run-info">&#9201; {tdur:.1f}s</div>'
                    f'<div class="run-b">'
                    f'<div class="legend">'
                    f'<div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Passed</div>'
                    f'<div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div>Failed</div>'
                    f'<div class="legend-item"><div class="legend-dot" style="background:var(--yellow)"></div>Skipped</div>'
                    f'</div>'
                    f'{_marker_folder_breakdown(modules)}'
                )

                for mi, mod in enumerate(modules):
                    ms = mod.get("summary") or {}
                    mp, mf, msk = ms.get("passed", 0), ms.get("failed", 0), ms.get("skipped", 0)
                    mpills = f'<span class="pill pp">{mp}</span>'
                    if mf:
                        mpills += f' <span class="pill pf">{mf}</span>'
                    if msk:
                        mpills += f' <span class="pill ps">{msk}</span>'
                    mid = f"{uid}-m{mi}"

                    html += (
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
                    deploy_results = [r for r in all_results if r.get("category") == "deploy"
                                      or (not r.get("category") and (
                                          "deploy" in r.get("test_name", "").lower()
                                          or "playbook" in r.get("test_name", "").lower()))]
                    verify_results = [r for r in all_results if r not in deploy_results]

                    has_deploy = bool(deploy_results) or bool(mod.get("playbook_logs"))
                    has_verify = bool(verify_results)

                    dv_deploy_id = f"{mid}-deploy"
                    if has_deploy:
                        html += (
                            f'<div class="dv-sec" id="dv-{dv_deploy_id}">'
                            f'<div class="dv-hdr" onclick="togDV(\'{dv_deploy_id}\')">'
                            f'<span class="dv-arr">&#9660;</span>'
                            f'<div class="dv-icon dv-deploy">&#9654;</div>'
                            f'<span>Deploy</span>'
                            f'<span class="pill pp" style="margin-left:auto">{len(deploy_results)} test(s)</span>'
                            f'</div><div class="dv-body">'
                        )
                        for test in deploy_results:
                            test_id += 1
                            st = test.get("status", "FAILED")
                            if st == "PASSED":
                                icls, isvg = "ip", svg_check
                            elif st == "SKIPPED":
                                icls, isvg = "is", svg_skip
                            else:
                                icls, isvg = "if", svg_x
                            html += _render_test_item(test_id, test, icls, isvg)
                        html += '</div></div>'
                    else:
                        html += (
                            f'<div class="dv-sec shut" id="dv-{dv_deploy_id}">'
                            f'<div class="dv-hdr" onclick="togDV(\'{dv_deploy_id}\')">'
                            f'<span class="dv-arr">&#9660;</span>'
                            f'<div class="dv-icon dv-skip">&#8212;</div>'
                            f'<span>Deploy</span>'
                            f'<span class="pill ps" style="margin-left:auto">skipped</span>'
                            f'</div><div class="dv-body">'
                            f'<div class="dv-skip-msg">No deploy tests executed for this scenario</div>'
                            f'</div></div>'
                        )

                    dv_verify_id = f"{mid}-verify"
                    if has_verify:
                        html += (
                            f'<div class="dv-sec" id="dv-{dv_verify_id}">'
                            f'<div class="dv-hdr" onclick="togDV(\'{dv_verify_id}\')">'
                            f'<span class="dv-arr">&#9660;</span>'
                            f'<div class="dv-icon dv-verify">{svg_check}</div>'
                            f'<span>Verify</span>'
                            f'<span class="pill pp" style="margin-left:auto">{len(verify_results)} test(s)</span>'
                            f'</div><div class="dv-body">'
                        )
                        for test in verify_results:
                            test_id += 1
                            st = test.get("status", "FAILED")
                            if st == "PASSED":
                                icls, isvg = "ip", svg_check
                            elif st == "SKIPPED":
                                icls, isvg = "is", svg_skip
                            else:
                                icls, isvg = "if", svg_x
                            html += _render_test_item(test_id, test, icls, isvg)
                        html += '</div></div>'
                    else:
                        html += (
                            f'<div class="dv-sec shut" id="dv-{dv_verify_id}">'
                            f'<div class="dv-hdr" onclick="togDV(\'{dv_verify_id}\')">'
                            f'<span class="dv-arr">&#9660;</span>'
                            f'<div class="dv-icon dv-skip">&#8212;</div>'
                            f'<span>Verify</span>'
                            f'<span class="pill ps" style="margin-left:auto">skipped</span>'
                            f'</div><div class="dv-body">'
                            f'<div class="dv-skip-msg">No verify tests executed for this scenario</div>'
                            f'</div></div>'
                        )

                    html += '</div></div>'  # mod-b, mod

                html += '</div></div>'  # run-b, run

            html += '</div>'  # panel
            first_server = False

        html += '</div></div>'  # main, lay

    html += '''
<div class="ft">Omnia Automation Framework &mdash; Test Report</div>
</div>
<script>
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
</script>
</body>
</html>'''

    return html


# =============================================================================
# TEST REPORT CLASS
# =============================================================================

class TestReport:
    """Test report generator — organizes results by server.

    All required values must be passed by the consumer.
    No config files are read internally.
    """

    def __init__(
        self,
        module_name: str,
        report_path: str,
        report_name: str,
        server_ip: str,
        report_id: Optional[str] = None,
        server_hostname: Optional[str] = None,
        suite: Optional[str] = None,
        marker: Optional[str] = None,
        exec_command: Optional[str] = None,
    ):
        """Initialise a test report.

        Args:
            module_name: Scenario / module name (e.g. ``prepare``).
            report_path: Absolute directory where JSON/HTML are saved.
            report_name: Base filename without extension.
            server_ip: Target server IP address.
            report_id: Unique run identifier (default: timestamp).
            server_hostname: Target hostname (resolved from IP if omitted).
            suite: Suite filter label (informational).
            marker: Marker filter label (informational).
            exec_command: Execution command label (informational).
        """
        self.module_name = module_name
        self.report_path = _resolve_report_dir(report_path)
        self.report_name = report_name
        self.report_id = report_id or datetime.now().strftime("%Y%m%d%H%M%S")
        self.start_time = datetime.now()
        self.results: List[Dict[str, Any]] = []
        self.playbook_logs = None
        self.command_type = None
        self.playbook_duration = None

        # Resolve hostname
        if not server_hostname:
            try:
                server_hostname = (
                    socket.gethostbyaddr(server_ip)[0]
                    if server_ip not in ("", "localhost")
                    else "localhost"
                )
            except (socket.herror, socket.gaierror, OSError):
                server_hostname = server_ip

        self.server_info = {"ip": server_ip, "hostname": server_hostname}
        self.suite = suite or os.environ.get("OMNIA_SUITE", "all")
        self.marker = marker or os.environ.get("OMNIA_MARKER", "")
        self.exec_command = exec_command or os.environ.get("OMNIA_COMMAND_TYPE", "")

        print(f"\n\u250c{'\u2500'*68}\u2510")
        print(f"\u2502  {'SERVER:':<12} {self.server_info['ip']:<52} \u2502")
        print(f"\u2502  {'MODULE:':<12} {module_name:<52} \u2502")
        print(f"\u2502  {'REPORT ID:':<12} {self.report_id:<52} \u2502")
        print(f"\u2514{'\u2500'*68}\u2518\n")

    def _get_playbook_logs(self) -> tuple:
        """Get playbook execution logs and command type."""
        log_file = os.environ.get('OMNIA_LOG_FILE')
        command_type = os.environ.get('OMNIA_COMMAND', 'execution')
        if log_file and os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    clean_content = _strip_ansi(content)
                    test_start_markers = [
                        "test session starts",
                        "collecting ...",
                        "\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510"
                    ]
                    playbook_only = clean_content
                    for marker in test_start_markers:
                        if marker in clean_content:
                            playbook_only = clean_content.split(marker)[0].strip()
                            break
                    return playbook_only, command_type
            except Exception:
                return None, command_type
        return None, command_type

    def add_result(self, test_name: Any, passed: bool = False, duration: float = 0.0,
                   details: str = None, error: str = None, status: str = None):
        """Add a test result to the report."""
        if isinstance(test_name, dict):
            payload = test_name
            normalized_status = str(payload.get("status") or "").strip().upper()
            if normalized_status not in {"PASSED", "FAILED", "SKIPPED"}:
                payload_passed = bool(payload.get("passed"))
                normalized_status = "PASSED" if payload_passed else "FAILED"

            duration_seconds = payload.get("duration_seconds")
            if duration_seconds is None:
                duration_seconds = payload.get("duration", 0.0)

            result = {
                "test_name": payload.get("test_name") or payload.get("name") or "<unknown>",
                "status": normalized_status,
                "timestamp": payload.get("timestamp") or datetime.now().isoformat(),
                "duration_seconds": round(float(duration_seconds or 0.0), 3),
            }
            if payload.get("details"):
                result["details"] = payload.get("details")
            if payload.get("error"):
                result["error"] = payload.get("error")
            if payload.get("category"):
                result["category"] = payload.get("category")
            if payload.get("markers"):
                result["markers"] = payload.get("markers")
            self.results.append(result)
            return

        normalized_status = (status or "").strip().upper()
        if normalized_status not in {"PASSED", "FAILED", "SKIPPED"}:
            normalized_status = "PASSED" if passed else "FAILED"
        result = {
            "test_name": test_name,
            "status": normalized_status,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 3),
        }
        if details:
            result["details"] = details
        if error:
            result["error"] = error
        self.results.append(result)

    def save(self) -> str:
        """Save the report as JSON and HTML. Returns the HTML file path."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        skipped = sum(1 for r in self.results if r["status"] == "SKIPPED")

        if self.playbook_logs is None:
            self.playbook_logs, self.command_type = self._get_playbook_logs()

        module_data = {
            "module": self.module_name,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 3),
            "summary": {"total": len(self.results), "passed": passed, "failed": failed, "skipped": skipped},
            "results": self.results,
            "playbook_logs": self.playbook_logs,
            "command_type": self.command_type,
            "suite": self.suite,
            "marker": self.marker,
            "exec_command": self.exec_command,
        }

        report = _load_report(self.report_path, self.report_name)
        server_ip = self.server_info["ip"]

        if "servers" not in report:
            report["servers"] = {}

        if server_ip not in report["servers"]:
            report["servers"][server_ip] = {"runs": []}

        report["servers"][server_ip]["hostname"] = self.server_info["hostname"]

        runs = report["servers"][server_ip]["runs"]
        existing_run_idx = next(
            (i for i, r in enumerate(runs) if r.get("report_id") == self.report_id),
            None
        )

        if existing_run_idx is not None:
            run = runs[existing_run_idx]
            if "modules" not in run:
                run["modules"] = []

            existing_mod_idx = next(
                (i for i, m in enumerate(run["modules"]) if m.get("module") == self.module_name),
                None
            )

            if existing_mod_idx is not None:
                run["modules"][existing_mod_idx]["results"].extend(self.results)
                run["modules"][existing_mod_idx]["playbook_logs"] = self.playbook_logs
                run["modules"][existing_mod_idx]["command_type"] = self.command_type
                all_results = run["modules"][existing_mod_idx]["results"]
                run["modules"][existing_mod_idx]["summary"] = {
                    "total": len(all_results),
                    "passed": sum(1 for r in all_results if r["status"] == "PASSED"),
                    "failed": sum(1 for r in all_results if r["status"] == "FAILED"),
                    "skipped": sum(1 for r in all_results if r["status"] == "SKIPPED"),
                }
            else:
                run["modules"].append(module_data)

            run["end_time"] = end_time.isoformat()
            all_passed = sum(m["summary"]["passed"] for m in run["modules"])
            all_failed = sum(m["summary"]["failed"] for m in run["modules"])
            all_skipped = sum((m.get("summary") or {}).get("skipped", 0) for m in run["modules"])
            run["summary"] = {
                "total": all_passed + all_failed + all_skipped,
                "passed": all_passed, "failed": all_failed, "skipped": all_skipped,
            }
        else:
            run_data = {
                "report_id": self.report_id,
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "summary": {"total": len(self.results), "passed": passed, "failed": failed, "skipped": skipped},
                "modules": [module_data],
            }
            runs.append(run_data)

        _save_json(report, self.report_path, self.report_name)

        # Use accumulated run-level totals for the banner
        current_run = next(
            (r for r in runs if r.get("report_id") == self.report_id),
            None,
        )
        if current_run:
            run_summary = current_run.get("summary", {})
            banner_passed = run_summary.get("passed", passed)
            banner_failed = run_summary.get("failed", failed)
            banner_skipped = run_summary.get("skipped", skipped)
            banner_duration = sum(
                m.get("duration_seconds", 0)
                for m in current_run.get("modules", [])
            )
        else:
            banner_passed, banner_failed, banner_skipped = passed, failed, skipped
            banner_duration = duration

        json_path = os.path.join(self.report_path, f"{self.report_name}.json")
        html_path = os.path.join(self.report_path, f"{self.report_name}.html")

        html_file = html_path
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(_generate_html(report))

        status_color = "\033[92m" if banner_failed == 0 else "\033[91m"
        reset = "\033[0m"

        print(f"\n\u250c{'\u2500'*68}\u2510")
        print(f"\u2502  {'REPORT SAVED':<64} \u2502")
        print(f"\u251c{'\u2500'*68}\u2524")
        print(f"\u2502  {'Server:':<14} {server_ip:<50} \u2502")
        print(f"\u2502  {'Report ID:':<14} {self.report_id:<50} \u2502")
        print(f"\u2502  {'Duration:':<14} {banner_duration:.2f}s{'':<46} \u2502")
        print(f"\u2502  {'Results:':<14} {status_color}{banner_passed} passed, {banner_failed} failed{reset}, {banner_skipped} skipped{'':<26} \u2502")
        print(f"\u251c{'\u2500'*68}\u2524")
        print(f"\u2502  JSON: {json_path:<60} \u2502")
        print(f"\u2502  HTML: {html_path:<60} \u2502")
        print(f"\u2514{'\u2500'*68}\u2518\n")

        return html_file


_current_report: Optional[TestReport] = None


def get_current_report() -> Optional[TestReport]:
    """Get the current active test report."""
    return _current_report


def set_current_report(report: TestReport):
    """Set the current active test report."""
    global _current_report
    _current_report = report
