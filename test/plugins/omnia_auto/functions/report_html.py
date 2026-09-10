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
Enterprise HTML Report Generation for omnia-auto test reports.

Generates a flat suite-based layout matching the omnia-containers
enterprise standard with:
- Dark/light theme toggle with localStorage persistence
- Overall PASSED/FAILED status banner
- Summary cards with click-to-filter
- CSS conic-gradient donut chart
- Suite breakdown table with progress bars
- Detailed test results with search/filter/collapse
- Playbook execution logs accordion with CRITICAL/WARNING highlighting
- Skip classification badges
- Sensitive data redaction in displayed output
- Print-friendly and responsive layout

Line length rules are relaxed due to embedded HTML/CSS content.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Status constants
_STATUS_PASS = "pass"
_STATUS_PASS_UPPER = "PASS"
_STATUS_SKIP = "skip"
_STATUS_SKIP_UPPER = "SKIP"
_STATUS_FAIL = "fail"
_STATUS_FAIL_UPPER = "FAIL"

_FAILURE_INDICATORS = [
    "failed=1", "unreachable=1", "fatal:", "failed: [",
    "molecule converge: failed", "molecule verify: failed",
    "molecule test: failed",
]


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


# ── Sensitive Data Redaction (for HTML display) ─────────────────────────────

_REDACT_PATTERNS = None


def _compile_redact_patterns():
    """Compile regex patterns for sensitive data redaction."""
    return [
        (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '***REDACTED_IP***'),
        (re.compile(
            r'(?i)([\w]*(?:password|passwd|hashed_passwd|secret|_key|token|'
            r'credential|api_key|ssh_key|private_key|auth_token)[\w]*'
            r'\s*[:=]\s*)["\']?(\S+?)(?=["\',}\]\s]|$)'
        ), r'\1***REDACTED***'),
        (re.compile(r'(?i)(nfs_server_share_path\s*[:=]\s*)["\']?[^"\'\s,}\]]+'), r'\1***REDACTED***'),
        (re.compile(r'(?i)((?:domain_name|hostname)\s*[:=]\s*)["\']?[^"\'\s,}\]]+'), r'\1***REDACTED***'),
    ]


def _redact_sensitive(text: str) -> str:
    """Redact sensitive data from text for display."""
    global _REDACT_PATTERNS  # pylint: disable=global-statement
    if not text:
        return text
    if _REDACT_PATTERNS is None:
        _REDACT_PATTERNS = _compile_redact_patterns()
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── Skip Classification ─────────────────────────────────────────────────────

def _classify_skip(details: str = "", error: str = "") -> str:
    """Classify a skipped test."""
    text = ((details or "") + " " + (error or "")).lower()
    if not text.strip():
        return "unexpected"
    framework_kw = [
        "fixture", "setup failed", "import error", "conftest",
        "collection error", "module not found", "no module named",
        "parametrize", "setup error", "teardown error",
    ]
    if any(kw in text for kw in framework_kw):
        return "framework"
    expected_kw = [
        "not enabled", "not configured", "disabled", "not supported",
        "not available", "not applicable", "not installed", "feature not",
        "requires", "only applies", "not present", "skipping",
        "condition", "marker", "prerequisite",
    ]
    if any(kw in text for kw in expected_kw):
        return "expected"
    return "unexpected"


# ── Log Issue Counter ────────────────────────────────────────────────────────

def _count_log_issues(logs: str) -> dict:
    """Count CRITICAL and WARNING occurrences in logs."""
    if not logs:
        return {"critical": 0, "warning": 0}
    upper = logs.upper()
    lines = upper.split('\n')
    return {
        "critical": sum(1 for ln in lines if 'CRITICAL' in ln),
        "warning": sum(1 for ln in lines if 'WARNING' in ln or '[WARN]' in ln),
    }


# ── HTML Report Generator ──────────────────────────────────────────────────

def generate_html(data: Dict[str, Any]) -> str:
    """Generate enterprise-grade HTML report with suite-based layout,
    dark/light theme, skip classification, and sensitive-data redaction."""

    # ── 1. Flatten data across all servers / runs / modules ─────────────
    servers = data.get("servers", {})
    all_tests: List[Dict[str, Any]] = []
    suite_stats: Dict[str, Dict] = defaultdict(
        lambda: {"pass": 0, "fail": 0, "skip": 0, "duration": 0.0}
    )
    playbook_logs_by_suite: Dict[str, Dict] = {}
    server_info_list: List[str] = []

    for server_ip, server_data in servers.items():
        hostname = server_data.get("hostname", "")
        if hostname:
            server_info_list.append(_redact_sensitive(hostname))
        else:
            server_info_list.append(_redact_sensitive(server_ip))

        for run in server_data.get("runs", []):
            run_id = run.get("report_id", "unknown")
            modules = run.get("modules", [])
            if not modules and "results" in run:
                modules = [{
                    "module": run.get("module", "unknown"),
                    "results": run["results"],
                    "summary": run.get("summary", {}),
                    "duration_seconds": run.get("total_duration_seconds", 0),
                    "playbook_logs": run.get("playbook_logs"),
                    "command_type": run.get("command_type"),
                }]

            for module in modules:
                suite = module.get("module", "unknown")

                # Capture playbook logs per suite (first occurrence)
                if module.get("playbook_logs") and suite not in playbook_logs_by_suite:
                    raw_logs = module["playbook_logs"]
                    log_lower = raw_logs.lower()
                    playbook_logs_by_suite[suite] = {
                        "logs": _redact_sensitive(raw_logs),
                        "command": (module.get("command_type") or "execution").upper(),
                        "failed": any(ind in log_lower for ind in _FAILURE_INDICATORS),
                        "issues": module.get("log_issues") or _count_log_issues(raw_logs),
                    }

                for result in module.get("results", []):
                    status_raw = (result.get("status") or "FAILED").upper()
                    if status_raw == "PASSED":
                        suite_stats[suite]["pass"] += 1
                    elif status_raw == "SKIPPED":
                        suite_stats[suite]["skip"] += 1
                    else:
                        suite_stats[suite]["fail"] += 1

                    dur = float(result.get("duration_seconds", 0))
                    suite_stats[suite]["duration"] += dur

                    all_tests.append({
                        "test_name": result.get("test_name", "<unknown>"),
                        "suite": suite,
                        "status": status_raw,
                        "duration": dur,
                        "details": _redact_sensitive(result.get("details", "")),
                        "error": _redact_sensitive(result.get("error", "")),
                        "server": server_ip,
                        "skip_type": result.get("skip_type", ""),
                        "tc_id": result.get("tc_id", ""),
                        "run_id": run_id,
                    })

    # ── 2. Compute summary ──────────────────────────────────────────────
    total_passed = sum(s["pass"] for s in suite_stats.values())
    total_failed = sum(s["fail"] for s in suite_stats.values())
    total_skipped = sum(s["skip"] for s in suite_stats.values())
    total_tests = total_passed + total_failed + total_skipped
    total_executed = total_passed + total_failed
    pass_rate = round(total_passed / max(total_executed, 1) * 100, 1)
    total_duration = sum(s["duration"] for s in suite_stats.values())
    duration_str = str(timedelta(seconds=int(total_duration)))
    overall_status = "PASSED" if total_failed == 0 else "FAILED"
    overall_class = _STATUS_PASS if overall_status == "PASSED" else _STATUS_FAIL

    timestamp = datetime.now().strftime("%B %d, %Y %I:%M %p")
    servers_display = ", ".join(server_info_list) if server_info_list else "N/A"

    # Donut chart angles (only passed and failed, excluding skipped)
    _t = max(total_executed, 1)
    deg_pass = round(total_passed / _t * 360)
    deg_fail = deg_pass + round(total_failed / _t * 360)

    # ── 3. Build suite breakdown rows ───────────────────────────────────
    suite_rows_html = ""
    suite_bar_html = ""
    for suite_name in sorted(suite_stats.keys()):
        s = suite_stats[suite_name]
        st = s["pass"] + s["fail"] + s["skip"]
        st_executed = s["pass"] + s["fail"]
        rate = round(s["pass"] / max(st_executed, 1) * 100, 1)
        bar_clr = "var(--clr-pass)" if rate >= 90 else "var(--clr-skip)" if rate >= 70 else "var(--clr-fail)"
        dur_str_s = f'{s["duration"]:.1f}s'
        esc_name = _escape_html(suite_name)

        suite_rows_html += f'''
            <tr>
              <td class="suite-name">{esc_name}</td>
              <td class="center">{st}</td>
              <td class="center td-pass">{s["pass"]}</td>
              <td class="center td-fail">{s["fail"]}</td>
              <td class="center td-skip">{s["skip"]}</td>
              <td class="center"><div class="progress-bar"><div class="progress-fill" style="width:{rate}%;background:{bar_clr}">{rate}%</div></div></td>
            </tr>'''

        suite_bar_html += f'''
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
              <span style="min-width:140px;font-size:13px;font-weight:500;">{esc_name}</span>
              <div class="progress-bar" style="flex:1;"><div class="progress-fill" style="width:{rate}%;background:{bar_clr}">{rate}%</div></div>
            </div>'''

    # ── 4. Build detailed test sections (grouped by suite, then by run_id) ────
    tests_by_suite: Dict[str, List] = defaultdict(list)
    for idx, t in enumerate(all_tests):
        t["_idx"] = idx
        tests_by_suite[t["suite"]].append(t)

    detailed_sections_html = ""
    global_idx = 0
    for suite_name in sorted(tests_by_suite.keys()):
        suite_tests = tests_by_suite[suite_name]
        s = suite_stats[suite_name]
        suite_status = _STATUS_PASS if s["fail"] == 0 else _STATUS_FAIL
        esc_name = _escape_html(suite_name)
        section_id = f"scenario-{suite_name.replace(' ', '_').replace('/', '_')}"

        # Group tests by run_id within the suite
        tests_by_run: Dict[str, List] = defaultdict(list)
        for t in suite_tests:
            run_id = t.get("run_id", "unknown")
            tests_by_run[run_id].append(t)

        # Build HTML for each run within the suite
        run_sections_html = ""
        for run_id in sorted(tests_by_run.keys()):
            run_tests = tests_by_run[run_id]
            run_id_short = run_id[-8:] if len(run_id) > 8 else run_id
            run_section_id = f"run-{suite_name.replace(' ', '_').replace('/', '_')}-{run_id_short}"

            run_rows = ""
            for t in run_tests:
                idx = global_idx
                global_idx += 1
                status_raw = t["status"]
                if status_raw == "PASSED":
                    sc = _STATUS_PASS
                    sl = _STATUS_PASS_UPPER
                elif status_raw == "SKIPPED":
                    sc = _STATUS_SKIP
                    sl = _STATUS_SKIP_UPPER
                else:
                    sc = _STATUS_FAIL
                    sl = _STATUS_FAIL_UPPER

                has_log = bool(t.get("details") or t.get("error"))
                log_icon = '<span class="log-link">View</span>' if has_log else '<span class="text-muted">&mdash;</span>'

                # Skip type badge
                skip_badge = ""
                if status_raw == "SKIPPED" and t.get("skip_type"):
                    skip_cls = {
                        "expected": "badge-skip",
                        "unexpected": "badge-warn",
                        "framework": "badge-fail",
                    }.get(t["skip_type"], "badge-skip")
                    skip_badge = f' <span class="badge {skip_cls}" style="font-size:9px;padding:1px 6px;">{_escape_html(t["skip_type"])}</span>'

                # TC ID display
                tc_prefix = f"[{_escape_html(t['tc_id'])}] " if t.get("tc_id") else ""

                log_section = ""
                if has_log:
                    log_parts = ""
                    if t.get("details"):
                        det = _escape_html(t["details"])
                        det = det.replace("PASS:", "<span style='color:var(--clr-pass);font-weight:600;'>PASS:</span>")
                        det = det.replace("FAIL:", "<span style='color:var(--clr-fail);font-weight:600;'>FAIL:</span>")
                        det = det.replace("SKIP:", "<span style='color:var(--clr-skip);font-weight:600;'>SKIP:</span>")
                        log_parts += f'<pre class="log-pre">{det}</pre>'
                    if t.get("error"):
                        err = _escape_html(t["error"][:2000])
                        log_parts += f'<div class="error-block"><strong>Error:</strong>\n{err}</div>'
                    log_section = f'''
                        <tr class="log-row" id="log-{idx}" style="display:none;">
                          <td colspan="5"><div class="log-content">{log_parts}</div></td>
                        </tr>'''

                run_rows += f'''
                    <tr class="test-row {sc}" onclick="toggleLog('log-{idx}')"
                        data-status="{sc}" data-suite="{esc_name}">
                      <td>{tc_prefix}{_escape_html(t["test_name"])}</td>
                      <td class="center"><span class="badge badge-{sc}">{sl}</span>{skip_badge}</td>
                      <td class="center">{t["duration"]:.2f}s</td>
                      <td class="center">{log_icon}</td>
                    </tr>{log_section}'''

            # Run header with collapsible section
            run_sections_html += f'''
            <div class="run-section" style="margin-left:20px;margin-top:10px;border-left:3px solid var(--border);padding-left:10px;">
              <div class="run-header" onclick="toggleRun('{run_section_id}')" style="cursor:pointer;padding:8px;background:var(--bg-panel);border-radius:4px;margin-bottom:8px;">
                <span class="run-arrow" id="arrow-{run_section_id}">&#9660;</span>
                <strong style="font-size:12px;">Run ID: {_escape_html(run_id_short)}</strong>
              </div>
              <div class="run-body" id="{run_section_id}">
                <table class="scenario-table" style="margin-top:8px;">
                  <thead><tr>
                    <th>Test Name</th><th class="center">Status</th>
                    <th class="center">Duration</th><th class="center">Logs</th>
                  </tr></thead>
                  <tbody>{run_rows}</tbody>
                </table>
              </div>
            </div>'''

        detailed_sections_html += f'''
          <div class="scenario-section" data-scenario="{esc_name}">
            <div class="scenario-header" onclick="toggleScenario('{section_id}')">
              <span class="pb-arrow" id="arrow-{section_id}">&#9660;</span>
              <strong>{esc_name}</strong>
              <span class="badge badge-{suite_status}" style="margin-left:6px;">{suite_status.upper()}</span>
              <span class="scenario-stats">
                <span class="td-pass">{s["pass"]} passed</span>
                <span class="td-fail">{s["fail"]} failed</span>
                <span class="td-skip">{s["skip"]} skipped</span>
                <span class="text-muted">{s["duration"]:.1f}s</span>
              </span>
            </div>
            <div class="scenario-body" id="{section_id}">
              {run_sections_html}
            </div>
          </div>'''

    # ── 5. Playbook logs (not displayed in HTML, kept for email/export) ────
    # Note: Playbook logs are captured in the report data but not displayed
    # in the HTML report since playbooks are run from source, not from tests.
    # They will be available in the JSON report and can be used in email
    # notifications to show pipeline stage failure details.

    # ── 6. Assemble full HTML ───────────────────────────────────────────
    html = f'''<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Test Execution Report - Omnia</title>
<style>
  /* ===== CSS Variables (Light) ===== */
  :root {{
    --bg: #f8fafc; --bg-card: #ffffff; --bg-panel: #f1f5f9;
    --text: #1e293b; --text-sec: #64748b; --text-muted: #94a3b8;
    --border: #e2e8f0; --border-strong: #cbd5e1;
    --shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    --shadow-xl: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
    --clr-pass: #10b981; --clr-fail: #ef4444; --clr-skip: #f59e0b;
    --clr-brand: #3b82f6; --clr-brand-dk: #1d4ed8;
    --badge-pass-bg: #dcfce7; --badge-pass-fg: #166534;
    --badge-fail-bg: #fee2e2; --badge-fail-fg: #991b1b;
    --badge-skip-bg: #fef3c7; --badge-skip-fg: #92400e;
    --badge-warn-bg: #fef3c7; --badge-warn-fg: #92400e;
    --log-bg: #1e293b; --log-fg: #e2e8f0;
    --err-bg: #fef2f2; --err-fg: #991b1b; --err-border: #fecaca;
    --banner-pass-bg: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); --banner-pass-fg: #065f46;
    --banner-fail-bg: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); --banner-fail-fg: #991b1b;
    --row-hover: #f8fafc; --card-hover: translateY(-4px) scale(1.02);
  }}
  /* ===== CSS Variables (Dark) ===== */
  [data-theme="dark"] {{
    --bg: #0f172a; --bg-card: #1e293b; --bg-panel: #334155;
    --text: #f1f5f9; --text-sec: #cbd5e1; --text-muted: #64748b;
    --border: #334155; --border-strong: #475569;
    --shadow: 0 4px 6px -1px rgba(0,0,0,0.3), 0 2px 4px -1px rgba(0,0,0,0.2);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.3), 0 4px 6px -2px rgba(0,0,0,0.2);
    --shadow-xl: 0 20px 25px -5px rgba(0,0,0,0.3), 0 10px 10px -5px rgba(0,0,0,0.2);
    --clr-pass: #34d399; --clr-fail: #f87171; --clr-skip: #fbbf24;
    --clr-brand: #60a5fa; --clr-brand-dk: #3b82f6;
    --badge-pass-bg: #064e3b; --badge-pass-fg: #6ee7b7;
    --badge-fail-bg: #7f1d1d; --badge-fail-fg: #fca5a5;
    --badge-skip-bg: #78350f; --badge-skip-fg: #fde68a;
    --badge-warn-bg: #78350f; --badge-warn-fg: #fde68a;
    --log-bg: #0f172a; --log-fg: #e2e8f0;
    --err-bg: #450a0a; --err-fg: #fca5a5; --err-border: #7f1d1d;
    --banner-pass-bg: linear-gradient(135deg, #064e3b 0%, #065f46 100%); --banner-pass-fg: #6ee7b7;
    --banner-fail-bg: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%); --banner-fail-fg: #fca5a5;
    --row-hover: #1e293b; --card-hover: translateY(-4px) scale(1.02);
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif; background:var(--bg); color:var(--text); line-height:1.6; -webkit-font-smoothing:antialiased; }}

  /* Header */
  .header {{ background:linear-gradient(135deg, var(--clr-brand) 0%, var(--clr-brand-dk) 100%); color:#fff; padding:28px 40px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; box-shadow:var(--shadow-lg); position:relative; overflow:hidden; }}
  .header::before {{ content:''; position:absolute; top:0; left:0; right:0; bottom:0; background:linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%); pointer-events:none; }}
  .header h1 {{ font-size:24px; font-weight:700; letter-spacing:-0.5px; position:relative; }}
  .header .subtitle {{ font-size:13px; opacity:0.9; margin-top:4px; font-weight:400; position:relative; }}
  .header-right {{ display:flex; align-items:center; gap:20px; position:relative; }}
  .header-meta {{ text-align:right; font-size:12px; opacity:0.95; line-height:1.4; }}
  .header-meta span {{ display:block; }}

  /* Theme toggle switch */
  .theme-toggle {{ position:relative; width:60px; height:32px; background:rgba(255,255,255,0.2); border:2px solid rgba(255,255,255,0.4); border-radius:20px; cursor:pointer; transition:all 0.3s ease; padding:0; font-size:0; display:flex; align-items:center; }}
  .theme-toggle::after {{ content:''; position:absolute; width:26px; height:26px; border-radius:50%; background:#fff; transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1); left:2px; box-shadow:0 2px 4px rgba(0,0,0,0.2); z-index:2; }}
  [data-theme="dark"] .theme-toggle {{ background:rgba(255,255,255,0.3); }}
  [data-theme="dark"] .theme-toggle::after {{ left:32px; }}
  .theme-toggle:hover {{ background:rgba(255,255,255,0.4); box-shadow:0 0 12px rgba(255,255,255,0.3); }}

  /* Banner */
  .overall-banner {{ text-align:center; padding:14px; font-size:16px; font-weight:700; letter-spacing:1px; box-shadow:var(--shadow); }}
  .overall-banner.pass {{ background:var(--banner-pass-bg); color:var(--banner-pass-fg); border-bottom:3px solid var(--clr-pass); }}
  .overall-banner.fail {{ background:var(--banner-fail-bg); color:var(--banner-fail-fg); border-bottom:3px solid var(--clr-fail); }}

  /* Container */
  .container {{ max-width:1440px; margin:24px auto; padding:0 24px; }}

  /* Summary cards */
  .summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:16px; margin-bottom:28px; }}
  .card {{ background:var(--bg-card); border-radius:12px; padding:20px; text-align:center; box-shadow:var(--shadow); border-top:4px solid var(--clr-brand); transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position:relative; overflow:hidden; }}
  .card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent); }}
  .card:hover {{ transform:var(--card-hover); box-shadow:var(--shadow-xl); }}
  .card.clickable {{ cursor:pointer; }}
  .card .value {{ font-size:36px; font-weight:700; margin:6px 0; }}
  .card .label {{ font-size:11px; text-transform:uppercase; color:var(--text-sec); letter-spacing:0.8px; font-weight:600; }}
  .card.total {{ border-top-color:var(--clr-brand); }}
  .card.passed {{ border-top-color:var(--clr-pass); }} .card.passed .value {{ color:var(--clr-pass); }}
  .card.failed {{ border-top-color:var(--clr-fail); }} .card.failed .value {{ color:var(--clr-fail); }}
  .card.skipped {{ border-top-color:var(--clr-skip); }} .card.skipped .value {{ color:var(--clr-skip); }}
  .card.rate .value {{ color:var(--clr-brand); }}
  .card.duration .value {{ font-size:24px; color:var(--text); }}

  /* Charts */
  .chart-section {{ display:flex; gap:24px; margin-bottom:28px; flex-wrap:wrap; }}
  .chart-card {{ flex:1; min-width:300px; background:var(--bg-card); border-radius:12px; padding:24px; box-shadow:var(--shadow); transition:all 0.3s ease; }}
  .chart-card:hover {{ box-shadow:var(--shadow-lg); transform:translateY(-2px); }}
  .chart-card h3 {{ margin-bottom:18px; font-size:16px; color:var(--text); font-weight:600; }}
  .donut-container {{ display:flex; align-items:center; justify-content:center; gap:32px; }}
  .donut {{ width:160px; height:160px; border-radius:50%; position:relative; background:conic-gradient(var(--clr-pass) 0deg {deg_pass}deg, var(--clr-fail) {deg_pass}deg {deg_fail}deg, var(--border) {deg_fail}deg 360deg); box-shadow:var(--shadow-lg); transition:transform 0.3s ease; }}
  .donut:hover {{ transform:scale(1.05); }}
  .donut-center {{ position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:100px; height:100px; border-radius:50%; background:var(--bg-card); display:flex; align-items:center; justify-content:center; font-size:28px; font-weight:700; color:var(--text); box-shadow:inset 0 2px 8px rgba(0,0,0,0.05); }}
  .donut-legend {{ font-size:14px; color:var(--text); }}
  .donut-legend div {{ margin:8px 0; display:flex; align-items:center; gap:10px; padding:4px 8px; border-radius:6px; transition:background 0.2s; }}
  .donut-legend div:hover {{ background:var(--bg-panel); }}
  .legend-color {{ width:14px; height:14px; border-radius:4px; display:inline-block; }}

  /* Scenario sections */
  .scenario-section {{ border:1px solid var(--border); border-radius:6px; margin-bottom:10px; overflow:hidden; }}
  .scenario-header {{ display:flex; align-items:center; gap:10px; padding:12px 16px; background:var(--bg-panel); cursor:pointer; flex-wrap:wrap; }}
  .scenario-header:hover {{ opacity:0.9; }}
  .scenario-stats {{ display:flex; gap:12px; margin-left:auto; font-size:12px; }}
  .scenario-body {{ border-top:1px solid var(--border); }}
  .scenario-table {{ margin:0; }}

  /* Panels */
  .panel {{ background:var(--bg-card); border-radius:12px; margin-bottom:24px; box-shadow:var(--shadow); overflow:hidden; transition:box-shadow 0.3s ease; }}
  .panel:hover {{ box-shadow:var(--shadow-lg); }}
  .panel-header {{ padding:16px 24px; background:var(--bg-panel); border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; }}
  .panel-header h2 {{ font-size:16px; color:var(--text); font-weight:600; }}

  /* Filter / search */
  .filter-controls {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .filter-btn {{ padding:6px 14px; border:1px solid var(--border-strong); border-radius:8px; background:var(--bg-card); color:var(--text-sec); font-size:11px; cursor:pointer; transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1); font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }}
  .filter-btn:hover {{ transform:translateY(-1px); box-shadow:0 2px 8px rgba(0,0,0,0.1); }}
  .filter-btn.active {{ background:linear-gradient(135deg, var(--clr-brand) 0%, var(--clr-brand-dk) 100%); color:#fff; border-color:var(--clr-brand); box-shadow:0 4px 12px rgba(59,130,246,0.3); }}
  .search-box {{ padding:8px 16px; border:1px solid var(--border-strong); border-radius:8px; font-size:13px; width:220px; background:var(--bg-card); color:var(--text); transition:all 0.3s ease; outline:none; }}
  .search-box:focus {{ border-color:var(--clr-brand); box-shadow:0 0 0 3px rgba(59,130,246,0.1); }}

  /* Tables */
  table {{ width:100%; border-collapse:collapse; }}
  th {{ background:var(--bg-panel); padding:12px 16px; text-align:left; font-size:11px; text-transform:uppercase; color:var(--text-sec); letter-spacing:0.6px; font-weight:600; border-bottom:2px solid var(--border-strong); }}
  td {{ padding:12px 16px; border-bottom:1px solid var(--border); font-size:13px; color:var(--text); transition:background 0.2s ease; }}
  .center {{ text-align:center; }}
  .suite-name {{ font-weight:600; }}
  .td-pass {{ color:var(--clr-pass); font-weight:600; }}
  .td-fail {{ color:var(--clr-fail); font-weight:600; }}
  .td-skip {{ color:var(--clr-skip); font-weight:600; }}
  tr.test-row {{ cursor:pointer; transition:all 0.2s ease; }}
  tr.test-row:hover {{ background:var(--row-hover); }}
  tr.test-row.fail {{ border-left:3px solid var(--clr-fail); background:rgba(239,68,68,0.02); }}
  tr.test-row.pass {{ border-left:3px solid var(--clr-pass); }}
  tr.test-row.skip {{ border-left:3px solid var(--clr-skip); }}
  .text-muted {{ color:var(--text-muted); }}

  /* Badges */
  .badge {{ padding:3px 10px; border-radius:4px; font-size:11px; font-weight:600; display:inline-block; white-space:nowrap; text-transform:uppercase; letter-spacing:0.3px; }}
  .badge-pass {{ background:var(--badge-pass-bg); color:var(--badge-pass-fg); }}
  .badge-fail {{ background:var(--badge-fail-bg); color:var(--badge-fail-fg); }}
  .badge-skip {{ background:var(--badge-skip-bg); color:var(--badge-skip-fg); }}
  .badge-warn {{ background:var(--badge-warn-bg); color:var(--badge-warn-fg); }}

  /* Progress bars */
  .progress-bar {{ background:var(--border); border-radius:8px; height:22px; overflow:hidden; min-width:80px; }}
  .progress-fill {{ height:100%; border-radius:8px; color:#fff; font-size:11px; font-weight:600; display:flex; align-items:center; justify-content:center; min-width:35px; transition:width 0.8s cubic-bezier(0.4, 0, 0.2, 1); }}

  /* Log rows */
  .log-row td {{ padding:0; }}
  .log-content {{ background:var(--log-bg); color:var(--log-fg); padding:16px 20px; font-family:'Cascadia Code','Fira Code',Consolas,monospace; font-size:12px; max-height:350px; overflow-y:auto; line-height:1.6; }}
  .log-pre {{ background:var(--log-bg); color:var(--log-fg); padding:14px 18px; border-radius:6px; font-family:'Cascadia Code','Fira Code',Consolas,monospace; font-size:11px; white-space:pre-wrap; word-break:break-word; max-height:300px; overflow-y:auto; line-height:1.6; border:1px solid var(--border); }}
  .error-block {{ background:var(--err-bg); color:var(--err-fg); border:1px solid var(--err-border); border-radius:6px; padding:12px 16px; margin-top:8px; font-family:'Cascadia Code','Fira Code',Consolas,monospace; font-size:11px; white-space:pre-wrap; word-break:break-word; max-height:200px; overflow-y:auto; }}
  .log-link {{ color:var(--clr-brand); font-size:12px; font-weight:600; text-decoration:underline; cursor:pointer; transition:color 0.2s; }}
  .log-link:hover {{ color:var(--clr-brand-dk); }}
  .log-critical {{ color:var(--clr-fail); font-weight:700; }}
  .log-warning {{ color:var(--clr-skip); font-weight:700; }}

  /* Playbook sections */
  .pb-section {{ margin-bottom:12px; border:1px solid var(--border); border-radius:8px; overflow:hidden; transition:box-shadow 0.3s ease; }}
  .pb-section:hover {{ box-shadow:var(--shadow); }}
  .pb-header {{ display:flex; align-items:center; gap:10px; padding:12px 16px; background:var(--bg-panel); cursor:pointer; flex-wrap:wrap; transition:background 0.2s ease; }}
  .pb-header:hover {{ background:var(--border); }}
  .pb-arrow {{ font-size:10px; color:var(--text-sec); transition:transform 0.3s ease; }}

  /* Footer */
  .footer {{ text-align:center; padding:18px; color:var(--text-muted); font-size:11px; }}

  /* Responsive */
  @media (max-width:768px) {{
    .header {{ padding:16px; flex-direction:column; text-align:center; }}
    .header-meta {{ text-align:center; }}
    .summary-grid {{ grid-template-columns:repeat(2,1fr); }}
    table {{ font-size:11px; }}
    td, th {{ padding:6px 8px; }}
  }}
  @media print {{
    body {{ background:#fff; }}
    .header {{ background:var(--clr-brand-dk) !important; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    .filter-controls, .search-box, .theme-toggle {{ display:none; }}
    .card {{ break-inside:avoid; }}
  }}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div>
    <h1>Test Execution Report</h1>
    <div class="subtitle">Omnia Automation Framework</div>
  </div>
  <div class="header-right">
    <div class="header-meta">
      <span><strong>Servers:</strong> {_escape_html(servers_display)}</span>
      <span><strong>Date:</strong> {timestamp}</span>
      <span><strong>Duration:</strong> {duration_str}</span>
    </div>
    <button class="theme-toggle" onclick="toggleTheme()" id="themeBtn" title="Toggle theme"></button>
  </div>
</div>

<!-- OVERALL STATUS -->
<div class="overall-banner {overall_class}">OVERALL STATUS: {overall_status}</div>

<div class="container">

  <!-- SUMMARY CARDS -->
  <div class="summary-grid">
    <div class="card total"><div class="label">Total Tests</div><div class="value">{total_tests}</div></div>
    <div class="card passed clickable" onclick="filterFromCard('pass')"><div class="label">Passed</div><div class="value">{total_passed}</div></div>
    <div class="card failed clickable" onclick="filterFromCard('fail')"><div class="label">Failed</div><div class="value">{total_failed}</div></div>
    <div class="card skipped clickable" onclick="filterFromCard('skip')"><div class="label">Skipped</div><div class="value">{total_skipped}</div></div>
    <div class="card rate"><div class="label">Pass Rate</div><div class="value">{pass_rate}%</div></div>
    <div class="card duration"><div class="label">Duration</div><div class="value">{duration_str}</div></div>
  </div>

  <!-- CHARTS -->
  <div class="chart-section">
    <div class="chart-card">
      <h3>Results Distribution</h3>
      <div class="donut-container">
        <div class="donut"><div class="donut-center">{pass_rate}%</div></div>
        <div class="donut-legend">
          <div><span class="legend-color" style="background:var(--clr-pass)"></span> Passed ({total_passed})</div>
          <div><span class="legend-color" style="background:var(--clr-fail)"></span> Failed ({total_failed})</div>
          <div><span class="legend-color" style="background:var(--clr-skip)"></span> Skipped ({total_skipped})</div>
        </div>
      </div>
    </div>
    <div class="chart-card">
      <h3>Suite Pass Rates</h3>
      <div style="padding:8px 0;">{suite_bar_html if suite_bar_html else '<p class="text-muted">No suites.</p>'}</div>
    </div>
  </div>

  <!-- SUITE BREAKDOWN -->
  <div class="panel">
    <div class="panel-header"><h2>Suite Breakdown</h2></div>
    <table>
      <thead><tr>
        <th>Suite</th><th class="center">Total</th><th class="center">Pass</th>
        <th class="center">Fail</th><th class="center">Skip</th><th class="center">Pass Rate</th>
      </tr></thead>
      <tbody>{suite_rows_html}</tbody>
    </table>
  </div>

  <!-- DETAILED RESULTS -->
  <div class="panel" id="detailedPanel">
    <div class="panel-header">
      <h2>Detailed Test Results</h2>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
        <input type="text" class="search-box" id="searchBox" placeholder="Search tests..." onkeyup="filterTests()">
        <div class="filter-controls">
          <button class="filter-btn active" data-status="all" onclick="filterByStatus('all',this)">All</button>
          <button class="filter-btn" data-status="pass" onclick="filterByStatus('pass',this)">Pass</button>
          <button class="filter-btn" data-status="fail" onclick="filterByStatus('fail',this)">Fail</button>
          <button class="filter-btn" data-status="skip" onclick="filterByStatus('skip',this)">Skip</button>
        </div>
      </div>
    </div>
    <div style="padding:16px;" id="scenarioContainer">
      {detailed_sections_html}
    </div>
  </div>

</div>

<!-- FOOTER -->
<div class="footer">Generated by Omnia Automation Framework &nbsp;|&nbsp; {timestamp}</div>

<script>
  /* Theme toggle */
  function toggleTheme() {{
    var html = document.documentElement;
    var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    try {{ localStorage.setItem('omnia-report-theme', next); }} catch(e) {{}}
  }}
  (function() {{
    try {{
      var saved = localStorage.getItem('omnia-report-theme');
      if (saved) document.documentElement.setAttribute('data-theme', saved);
    }} catch(e) {{}}
  }})();

  /* Toggle log rows */
  function toggleLog(id) {{
    var el = document.getElementById(id);
    if (el) el.style.display = el.style.display === 'none' ? 'table-row' : 'none';
  }}

  /* Filter by status */
  function filterByStatus(status, btn) {{
    document.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
    if (btn) btn.classList.add('active');
    else {{
      document.querySelectorAll('.filter-btn').forEach(function(b) {{
        if (b.getAttribute('data-status') === status) b.classList.add('active');
      }});
    }}
    document.querySelectorAll('#scenarioContainer .test-row').forEach(function(row) {{
      if (status === 'all' || row.getAttribute('data-status') === status) {{
        row.style.display = '';
      }} else {{
        row.style.display = 'none';
      }}
    }});
    document.querySelectorAll('#scenarioContainer .log-row').forEach(function(r) {{ r.style.display = 'none'; }});
    document.querySelectorAll('.scenario-section').forEach(function(sec) {{
      var hasVisible = sec.querySelectorAll('.test-row:not([style*="display: none"])').length > 0
                    || sec.querySelectorAll('.test-row:not([style*="display:none"])').length > 0;
      if (status === 'all') hasVisible = true;
      sec.style.display = hasVisible ? '' : 'none';
    }});
  }}

  /* Filter from clicking a summary card */
  function filterFromCard(status) {{
    filterByStatus(status, null);
    var panel = document.getElementById('detailedPanel');
    if (panel) panel.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}

  /* Toggle scenario collapse */
  function toggleScenario(id) {{
    var el = document.getElementById(id);
    var arrow = document.getElementById('arrow-' + id);
    if (el.style.display === 'none') {{
      el.style.display = '';
      if (arrow) arrow.innerHTML = '&#9660;';
    }} else {{
      el.style.display = 'none';
      if (arrow) arrow.innerHTML = '&#9654;';
    }}
  }}

  /* Toggle run collapse */
  function toggleRun(id) {{
    var el = document.getElementById(id);
    var arrow = document.getElementById('arrow-' + id);
    if (el.style.display === 'none') {{
      el.style.display = '';
      if (arrow) arrow.innerHTML = '&#9660;';
    }} else {{
      el.style.display = 'none';
      if (arrow) arrow.innerHTML = '&#9654;';
    }}
  }}

  /* Search tests */
  function filterTests() {{
    var query = document.getElementById('searchBox').value.toLowerCase();
    document.querySelectorAll('#scenarioContainer .test-row').forEach(function(row) {{
      row.style.display = row.textContent.toLowerCase().includes(query) ? '' : 'none';
    }});
    document.querySelectorAll('.scenario-section').forEach(function(sec) {{
      var hasVisible = sec.querySelectorAll('.test-row:not([style*="display: none"])').length > 0
                    || sec.querySelectorAll('.test-row:not([style*="display:none"])').length > 0;
      sec.style.display = hasVisible ? '' : 'none';
    }});
  }}


</script>
</body>
</html>'''

    return html
