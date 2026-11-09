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

"""Constants of the SVT report (library/functions/svt_report_func.py, svt_report_html.py)."""

import re

# Terminal colour codes removed from a step's output.
ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Status of a section or stage that has not finished.
RUNNING = "Running"

# "user:token@" of a clone URL, removed before the URL is shown.
CREDENTIALS_RE = re.compile(r"^(https?://)[^/@]+@")

# Characters of a step's screen output shown in the HTML (its tail); the JSON
# keeps more (MAX_OUTPUT_CHARS) and the stage/setup logs keep everything.
HTML_OUTPUT_CHARS = 200_000

# A run of this many word characters is cut into lines before masking (omnia_auto's
# redaction is quadratic on one long unbroken word).
LONG_WORD = 200

LONG_WORD_RE = re.compile(r"\w{%d,}" % (LONG_WORD + 1))

# Sections shown inside the Initialization stage (./setup_env.sh steps).
INITIALIZATION_PHASES = ("cleanup", "install")

# Status -> CSS class.
BADGE = {"Passed": "pass", "Failed": "fail", "Skipped": "skip", RUNNING: "run"}

# Stylesheet and script of the self-contained HTML report.
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
