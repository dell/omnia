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


"""Constants of the pipeline HTML report (library/functions/report_func.py)."""

import re

# A job log longer than this keeps its head and its tail.
MAX_LOG_CHARS = 200000
LOG_HEAD_CHARS = 20000

# The copy of the report attached to the mail keeps less of each log (the artifact has the full one).
MAIL_LOG_CHARS = 40000
MAIL_LOG_HEAD_CHARS = 8000

# Job status (GitLab): (label, css class).
STATUS_LABELS = {
    "success": ("PASSED", "pass"),
    "failed": ("FAILED", "fail"),
    "canceled": ("CANCELED", "skip"),
    "skipped": ("NOT RUN", "skip"),
    "running": ("RUNNING", "run"),
    "manual": ("MANUAL", "skip"),
    "created": ("NOT RUN", "skip"),
    "pending": ("PENDING", "run"),
}
UNKNOWN_LABEL = ("NOT RUN", "skip")

# Secrets hidden in the job logs of the report: (compiled pattern, replacement).
REDACT_PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "***REDACTED PRIVATE KEY***"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*", re.S), "***REDACTED PRIVATE KEY***"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 ***REDACTED***"),
    (re.compile(r"\b(glpat|ghp|gho|ghs|github_pat)[-_][A-Za-z0-9_-]{10,}"), "***REDACTED TOKEN***"),
    (re.compile(
        r"(?i)([\w-]*(?:password|passwd|secret|_key|token|credential|private_key)[\w-]*"
        r"\s*[:=]\s*)[\"']?(?!\*\*\*)(\S+?)(?=[\"',}\]\s]|$)"), r"\1***REDACTED***"),
)

# Name of the theme choice kept by the browser.
THEME_KEY = "omnia-pipeline-report-theme"

CSS = """
:root{--bg:#f3f5fa;--card:#fff;--text:#1b2433;--muted:#64748b;--border:#d9e0ec;--brand:#4f46e5;
--brand2:#7c3aed;--pass:#198754;--fail:#dc3545;--skip:#6c757d;--run:#0d6efd;--warn:#b7791f;
--log-bg:#0f172a;--log-fg:#e2e8f0;--shadow:0 1px 3px rgba(15,23,42,.12);--err-bg:#fdf1f2}
[data-theme="dark"]{--bg:#0b1020;--card:#141b2d;--text:#e6ebf5;--muted:#93a1ba;--border:#25304a;
--brand:#818cf8;--brand2:#a78bfa;--log-bg:#070b16;--log-fg:#d6deeb;--shadow:0 1px 3px rgba(0,0,0,.5);
--err-bg:#2a1418}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--brand)}
.header{background:linear-gradient(135deg,var(--brand),var(--brand2));color:#fff;padding:26px 32px;
display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between}
.header h1{margin:0;font-size:22px;letter-spacing:.2px}
.header .sub{opacity:.9;font-size:13px;margin-top:4px}
.header a{color:#fff}
.verdict{display:inline-block;padding:6px 18px;border-radius:999px;font-weight:700;letter-spacing:.5px;
background:#fff;color:var(--skip)}
.verdict.pass{color:var(--pass)}.verdict.fail{color:var(--fail)}
.theme-btn{background:rgba(255,255,255,.18);color:#fff;border:1px solid rgba(255,255,255,.4);
border-radius:8px;padding:7px 14px;cursor:pointer;font-size:13px}
.theme-btn:hover{background:rgba(255,255,255,.3)}
.container{max-width:1280px;margin:0 auto;padding:22px}
.panel{background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow);
margin-bottom:20px;overflow:hidden}
.panel h2{margin:0;padding:14px 18px;font-size:15px;border-bottom:1px solid var(--border)}
.info{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:0}
.info div{padding:10px 18px;border-bottom:1px solid var(--border);word-break:break-word}
.info b{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--border);border-top:4px solid var(--skip);
border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.card .n{font-size:28px;font-weight:700}.card .l{color:var(--muted);font-size:12px;
text-transform:uppercase;letter-spacing:.6px}
.card.pass{border-top-color:var(--pass)}.card.fail{border-top-color:var(--fail)}
.card.total{border-top-color:var(--brand)}.card.time{border-top-color:var(--run)}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:14px 18px;
border-bottom:1px solid var(--border)}
.toolbar input{flex:1;min-width:200px;padding:8px 12px;border:1px solid var(--border);border-radius:8px;
background:var(--bg);color:var(--text)}
.chip,.btn{border:1px solid var(--border);background:var(--bg);color:var(--text);border-radius:999px;
padding:6px 14px;cursor:pointer;font-size:12px;font-weight:600}
.chip.active{background:var(--brand);color:#fff;border-color:var(--brand)}
.btn{border-radius:8px}
details.stage{border-bottom:1px solid var(--border)}
details.stage>summary{display:flex;align-items:center;gap:12px;padding:12px 18px;cursor:pointer;
list-style:none}
details.stage>summary::-webkit-details-marker{display:none}
details.stage>summary::before{content:"\\25B6";font-size:10px;color:var(--muted);transition:transform .15s}
details.stage[open]>summary::before{transform:rotate(90deg)}
details.stage>summary:hover{background:var(--bg)}
.idx{color:var(--muted);width:26px;text-align:right}
.name{font-weight:600;flex:1;word-break:break-all}
.dur{color:var(--muted);font-size:12px;min-width:70px;text-align:right}
.badge{font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;color:#fff;background:var(--skip)}
.badge.pass{background:var(--pass)}.badge.fail{background:var(--fail)}.badge.run{background:var(--run)}
.body{padding:4px 18px 18px}
.meta{display:flex;flex-wrap:wrap;gap:6px 22px;color:var(--muted);font-size:12px;margin:6px 0 10px}
.reason{border-left:4px solid var(--fail);background:var(--err-bg);padding:10px 14px;margin:8px 0 12px;
border-radius:6px;color:var(--fail);word-break:break-word}
.logbar{display:flex;gap:8px;margin-bottom:6px}
pre.log{margin:0;background:var(--log-bg);color:var(--log-fg);padding:14px 16px;border-radius:8px;
font:12px/1.55 "Cascadia Code","Fira Code",Consolas,Menlo,monospace;max-height:65vh;overflow:auto;
white-space:pre;tab-size:4;border:1px solid var(--border);scrollbar-width:thin}
.wrap pre.log{white-space:pre-wrap;word-break:break-word}
pre.log::-webkit-scrollbar{width:11px;height:11px}
pre.log::-webkit-scrollbar-thumb{background:#64748b;border-radius:6px}
.e{color:#ff6b6b;font-weight:600}.w{color:#fbbf24}.o{color:#4ade80}.s{color:#7dd3fc}
.empty{color:var(--muted);font-style:italic}
.footer{text-align:center;color:var(--muted);font-size:12px;padding:10px 0 26px}
.hidden{display:none!important}
@media print{.toolbar,.theme-btn,.logbar{display:none}details.stage .body{display:block}
pre.log{max-height:none;white-space:pre-wrap}body{background:#fff;color:#000}}
"""

JS = """
(function(){
var root=document.documentElement,key='@KEY@';
function setTheme(t){root.setAttribute('data-theme',t);try{localStorage.setItem(key,t)}catch(e){}
var b=document.getElementById('themeBtn');if(b)b.textContent=t==='dark'?'Light theme':'Night theme';}
var saved=null;try{saved=localStorage.getItem(key)}catch(e){}
setTheme(saved||(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));
document.getElementById('themeBtn').onclick=function(){
setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark')};
var stages=[].slice.call(document.querySelectorAll('details.stage')),status='all';
function apply(){var q=document.getElementById('q').value.toLowerCase(),shown=0;
stages.forEach(function(s){var ok=status==='all'||s.getAttribute('data-status')===status;
if(ok&&q){var t=(s.getAttribute('data-name')||'').toLowerCase();
ok=t.indexOf(q)>-1||((s.querySelector('pre.log')||{textContent:''}).textContent.toLowerCase().indexOf(q)>-1);}
s.classList.toggle('hidden',!ok);if(ok)shown++;});
document.getElementById('shown').textContent=shown+' of '+stages.length+' stages';}
[].forEach.call(document.querySelectorAll('.chip'),function(c){c.onclick=function(){
[].forEach.call(document.querySelectorAll('.chip'),function(x){x.classList.remove('active')});
c.classList.add('active');status=c.getAttribute('data-filter');apply();}});
document.getElementById('q').oninput=apply;
document.getElementById('expand').onclick=function(){stages.forEach(function(s){
if(!s.classList.contains('hidden'))s.open=true})};
document.getElementById('collapse').onclick=function(){stages.forEach(function(s){s.open=false})};
document.getElementById('wrap').onclick=function(){document.body.classList.toggle('wrap')};
[].forEach.call(document.querySelectorAll('.copy'),function(b){b.onclick=function(){
var pre=b.closest('.body').querySelector('pre.log');if(!pre)return;
if(navigator.clipboard){navigator.clipboard.writeText(pre.textContent)}
else{var r=document.createRange();r.selectNodeContents(pre);var s=getSelection();
s.removeAllRanges();s.addRange(r);document.execCommand('copy');s.removeAllRanges();}
b.textContent='Copied';setTimeout(function(){b.textContent='Copy log'},1500);}});
apply();
})();
"""
