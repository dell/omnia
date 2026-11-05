#!/usr/bin/env python3
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

"""Advisory secure-code review of the lines added by a pull request.

Each rule encodes a class of finding that was fixed in this repository
(pentest / Code Guardian remediations). Only ADDED lines are inspected.
Writes a Markdown checklist and always exits 0 (never blocks a PR).

Usage: secure_code_review.py <base-ref> [output.md]
"""

import fnmatch
import re
import subprocess
import sys

MARKER = "<!-- secure-code-review -->"
PY, YML, SH = ["*.py"], ["*.yml", "*.yaml", "*.j2"], ["*.sh"]
DOCKER = ["*Dockerfile*", "*Containerfile*", "*.container"]
REQS = ["*requirements*.txt"]
MAX_SHOWN = 10

# (id, title, CWE, guideline, file globs, regex, ignore-regex or None)
RULES = [
    ("SEC-01", "No hardcoded credentials", "CWE-798",
     "Read secrets from the vault/credential utilities, never from literals.",
     PY + YML + SH,
     r"(?i)\b(password|passwd|secret|token|api_?key)\w*\s*[:=]\s*[\"'][^\"'{}$\s]{6,}[\"']",
     r"(?i)(example|changeme|placeholder|dummy|test|<.*>|\bnone\b|vault|\.yml|\.yaml|\.json|path|file|regex|pattern)"),
    ("SEC-02", "TLS verification not disabled", "CWE-295",
     "Do not use verify=False / validate_certs: false / curl -k; if unavoidable "
     "(self-signed BMC) document with '# nosec B501'.",
     PY + YML + SH,
     r"verify\s*=\s*False|validate_certs\s*:\s*(false|no)\b|\bcurl\b[^\n]*\s(-k|--insecure)\b|"
     r"InsecureRequestWarning",
     r"nosec"),
    ("SEC-03", "SSH host-key checking stays enabled", "CWE-295",
     "Use StrictHostKeyChecking=accept-new and a persistent known_hosts "
     "(no UserKnownHostsFile=/dev/null).",
     PY + YML + SH + ["*.cfg", "*.j2", "*.conf"],
     r"StrictHostKeyChecking[ =]+no|UserKnownHostsFile=/dev/null|host_key_checking\s*=\s*(false|no)",
     None),
    ("SEC-04", "No shell / command injection sinks", "CWE-78",
     "Avoid shell=True, os.system, eval/exec; pass argv lists to subprocess.",
     PY, r"shell\s*=\s*True|\bos\.(system|popen)\s*\(|(?<![\w.])(eval|exec)\s*\(", r"nosec"),
    ("SEC-05", "Ansible shell/command variables are quoted", "CWE-78",
     "Use argv lists or '| quote' for every templated value in shell:/command: "
     "lines; prefer ansible.builtin.command with argv.",
     YML,
     r"^\s*(ansible\.builtin\.)?(shell|command|cmd|_raw_params)\s*:[^\n]*\{\{(?![^}]*\|\s*(quote|int|bool|length)\b)[^}]*\}\}",
     None),
    ("SEC-06", "No unsafe Jinja lookups", "CWE-94",
     "Avoid lookup('pipe'|'env'), eval-style filters and template of untrusted "
     "input; load user YAML as literal data (no Jinja evaluation).",
     YML, r"lookup\(\s*['\"](pipe|env)['\"]|\|\s*(eval|safe)\b|ansible_eval", None),
    ("SEC-07", "YAML parsed safely", "CWE-502",
     "Use yaml.safe_load; never yaml.load without SafeLoader, pickle or marshal.",
     PY, r"yaml\.load\s*\((?![^)]*Safe)|yaml\.unsafe_load|\bpickle\.loads?\(|\bmarshal\.loads?\(", r"nosec"),
    ("SEC-08", "Vault decrypt does not leave plaintext on disk", "CWE-459/CWE-522",
     "Use 'ansible-vault decrypt --output' to a private tmpfs file (/dev/shm) "
     "inside block/rescue/always cleanup; no in-place decrypt, no failed_when: false.",
     YML + SH,
     r"ansible-vault\s+decrypt\b(?![^\n]*--output)|ansible-vault\s+view\b[^\n]*>\s*\S+", None),
    ("SEC-09", "Secrets not passed on command line (argv)", "CWE-214",
     "Pass credentials via files/stdin/env with restrictive perms, not "
     "--password/-p arguments visible in process lists.",
     PY + YML + SH,
     r"(?i)--(password|passwd|token|secret|api-key)[= ]+\S|\s-p\s+['\"]?\{\{|"
     r"sshpass\s+-p|mysql\b[^\n]*\s-p\S", r"(?i)(no_log|prompt|help|description)"),
    ("SEC-10", "Credential tasks declare no_log", "CWE-532",
     "Any task handling passwords/tokens/secrets must set no_log: true.",
     YML, "__NOLOG__", None),
    ("SEC-11", "Secrets not written to logs or errors", "CWE-532/CWE-209",
     "Never log credentials; return generic errors without internal paths/state.",
     PY + SH,
     r"(?i)(log(ger)?\.\w+|print|echo)\s*\(?[^\n]*(password|passwd|secret|token|api_?key)",
     r"(?i)(redact|mask|\*{3}|len\(|not set|missing|invalid|required|prompt|'\s*%|file|path)"),
    ("SEC-12", "Swallowed exceptions are logged", "CWE-390/CWE-703",
     "Do not use bare 'except:' or 'except ...: pass'; log or re-raise.",
     PY, r"^\s*except\s*:\s*(#.*)?$|^\s*except[^:\n]*:\s*pass\b", r"nosec"),
    ("SEC-13", "Safe permissions on files and directories", "CWE-732",
     "No world-writable modes (777/666/o+w); credential files 0600, dirs 0700/0750.",
     PY + YML + SH,
     r"\bmode\s*[:=]\s*['\"]?0?o?(777|666|776|766)['\"]?\b|chmod\s+(-R\s+)?(0?777|0?666|a\+w|o\+w)\b|"
     r"os\.chmod\([^)]*0o?(777|666)", None),
    ("SEC-14", "Secure temporary files", "CWE-377/CWE-379",
     "Use tempfile.mkstemp/NamedTemporaryFile or 'mktemp' (tmpfs for secrets); "
     "no predictable /tmp paths or tempfile.mktemp.",
     PY + YML + SH, r"tempfile\.mktemp\(|[\"' =]/tmp/[\w{$.-]+|[\"' =]/var/tmp/[\w{$.-]+",
     r"(?i)(mktemp|mkstemp|tmpfs|nosec|NamedTemporary|TemporaryDirectory|path_join|dirname)"),
    ("SEC-15", "Path inputs validated against traversal", "CWE-22/CWE-73",
     "Resolve user-supplied paths/names (realpath + prefix check, allowlist "
     "regex) and reject '..'; do not join raw input into paths.",
     PY,
     r"os\.path\.join\([^)]*(request|args\.|argv|input\(|project_name|user_)|"
     r"open\([^)]*(request|argv|input\()|extractall\(", r"(?i)(realpath|resolve|commonpath|validate|sanitiz|nosec)"),
    ("SEC-16", "Input validated before shell/SSH/config use", "CWE-20/CWE-77",
     "Validate CSV/user-derived hostnames, IPs, NIC names, tags and registry "
     "strings with allowlist regex before use in commands or config files.",
     YML + SH,
     r"(?i)(lineinfile|blockinfile|replace)\b[^\n]*\{\{\s*(item|hostname|ip|nic|ib_nic|domain)\w*\s*\}\}", r"quote|regex_replace|validated"),
    ("SEC-17", "Container base images pinned by digest", "CWE-494",
     "Pin FROM/Image= references with @sha256:<digest>, not mutable tags.",
     DOCKER,
     r"^\s*(FROM|Image\s*=)\s*(?!scratch\b)(?![^\n]*@sha256:)\S+", r"(?i)(AS\s+\w+\s*$.*\$\{|^\s*FROM\s+\$\{?\w+\}?\s*$|--from=)"),
    ("SEC-18", "Python dependencies pinned to exact versions", "CWE-1104",
     "Use 'pkg==x.y.z' in requirements and pip install commands.",
     REQS + ["*Dockerfile*", "*Containerfile*"],
     r"^\s*(pip3?\s+install\s+(?!-r|--upgrade pip)[^\n=]*\b[A-Za-z][\w.-]*\s*$|[A-Za-z][\w.\[\]-]*\s*(>=|~=|<=|>|<)[^,\n]*$|[A-Za-z][\w.-]+\s*$)",
     r"^\s*(#|-r|-c|--|$)"),
    ("SEC-19", "Kubernetes / pod hardening", "CWE-250/CWE-269",
     "No privileged containers, hostPID/hostNetwork, or privilege escalation; "
     "set seccompProfile RuntimeDefault, drop ALL caps.",
     YML + ["*.container"],
     r"privileged\s*:\s*true|allowPrivilegeEscalation\s*:\s*true|hostPID\s*:\s*true|"
     r"hostNetwork\s*:\s*true|hostIPC\s*:\s*true|SYS_ADMIN|PrivilegedContainer|Privileged\s*=\s*true",
     None),
    ("SEC-20", "Firewall / network exposure not widened", "CWE-284/CWE-923",
     "Do not bind services to 0.0.0.0 or open broad firewall zones without "
     "a documented need; isolate container interfaces in dedicated zones.",
     PY + YML + SH,
     r"(?i)bind\w*\s*[:=]\s*['\"]?0\.0\.0\.0|host\s*=\s*['\"]0\.0\.0\.0|--add-port=\S+|"
     r"firewall-cmd[^\n]*--set-default-zone|zone\s*:\s*trusted", r"nosec"),
    ("SEC-21", "Strong crypto and token handling", "CWE-327/CWE-330/CWE-613",
     "No md5/sha1 for security, no 'random' for secrets (use 'secrets'), no "
     "non-expiring tokens (set a TTL).",
     PY + YML + SH,
     r"hashlib\.(md5|sha1)\(|\brandom\.(random|randint|choice|choices)\([^\n]*(token|pass|secret|key)|"
     r"(?i:token[_-]?ttl)\s*[:=]\s*['\"]?0\b|--ttl[= ]0\b", r"nosec|usedforsecurity\s*=\s*False"),
    ("SEC-22", "CSV/injection-safe output", "CWE-1236",
     "Neutralise leading =,+,-,@ in values written to CSV/spreadsheets; "
     "do not echo user input into logs without sanitising newlines.",
     PY, r"csv\.(writer|DictWriter)\(", r"(?i)(sanitiz|escape|nosec)"),
]

NOLOG_WORDS = re.compile(r"(?i)password|passwd|secret|token|credential|vault_pass|api_?key|private_key")


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout


def added_lines(base):
    """Return {file: [(lineno, text)]} for lines added vs merge-base."""
    diff = run("git", "diff", "--unified=0", "--no-color", "--diff-filter=ACMR", f"{base}...HEAD")
    out, cur, ln = {}, None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            cur = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            ln = int(m.group(1)) if m else 0
        elif cur and raw.startswith("+") and not raw.startswith("+++"):
            out.setdefault(cur, []).append((ln, raw[1:]))
            ln += 1
    return out


def matches(path, globs):
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(name, g) or fnmatch.fnmatch(path, g) for g in globs)


def skip(path):
    return path.startswith(("test/", ".github/")) or "/tests/" in path or "/test/" in path or "/docs/" in path


def check_nolog(path):
    """Tasks in changed YAML that touch credentials without no_log."""
    try:
        import yaml
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception:  # pylint: disable=broad-except
        return []
    found = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            is_task = any(k in node for k in ("command", "shell", "ansible.builtin.command",
                                              "ansible.builtin.shell", "ansible.builtin.uri", "uri",
                                              "ansible.builtin.debug", "debug", "ansible.builtin.copy", "copy"))
            if is_task and "no_log" not in node:
                body = {k: v for k, v in node.items() if k not in ("name", "when", "tags", "register")}
                if NOLOG_WORDS.search(str(body)) and not re.search(r"(?i)no_log|_path|_file", str(body.get("no_log", ""))):
                    found.append(str(node.get("name", "<unnamed task>")))
            for v in node.values():
                walk(v)
    walk(data)
    return found


FOCUS = [
    (r"\.py$", "Python: input validation, safe_load, subprocess argv, logging of secrets/exceptions"),
    (r"\.(ya?ml|j2)$", "Ansible: no_log on credential tasks, quoted shell vars, no failed_when: false on critical tasks, vault tmpfs pattern"),
    (r"\.(sh|bash)$", "Shell: quoted variables, strict mode (set -euo pipefail), no eval, secure temp files"),
    (r"(Dockerfile|Containerfile|\.container$)", "Containers: digest-pinned base images, non-root, dropped capabilities"),
    (r"(^|/)(requirements[^/]*\.txt)$", "Dependencies: exact version pins, no unvetted new packages"),
    (r"\.(cfg|conf|toml|ini)$", "Config: no secrets, SSH host-key checking, safe defaults"),
]


def focus_areas(paths):
    return [msg for rx, msg in FOCUS if any(re.search(rx, p) for p in paths)]


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/staging"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "secure-code-review.md"
    changes = {p: l for p, l in added_lines(base).items() if not skip(p)}
    results = []
    for rid, title, cwe, guide, globs, rx, ign in RULES:
        hits = []
        for path, lines in changes.items():
            if not matches(path, globs):
                continue
            if rx == "__NOLOG__":
                hits += [(path, 0, f"task '{t}' has no no_log") for t in check_nolog(path)
                         if any(NOLOG_WORDS.search(txt) for _, txt in lines)]
                continue
            rc, ic = re.compile(rx), re.compile(ign) if ign else None
            for ln, text in lines:
                if text.lstrip().startswith("#"):
                    continue
                if rc.search(text) and not (ic and ic.search(text)):
                    hits.append((path, ln, text.strip()[:110]))
        results.append((rid, title, cwe, guide, hits))

    failed = [r for r in results if r[4]]
    lines = [MARKER, "## Secure Code Review", "",
             "_Advisory only: this check never blocks the PR. It scans the lines added by this PR against "
             "secure-coding rules derived from recent security fixes in this repository._", ""]
    if not changes:
        lines.append("No reviewable source changes (tests, docs and workflows are excluded).")
    lines.append(f"**Result: {len(results) - len(failed)} passed, {len(failed)} failed** "
                 f"({len(changes)} file(s) scanned)\n")
    lines.append("### Checklist")
    for rid, title, cwe, _, hits in results:
        lines.append(f"- [{'x' if not hits else ' '}] {'PASS' if not hits else 'FAIL'} **{rid}** {title} ({cwe})"
                     + (f" - {len(hits)} finding(s)" if hits else ""))
    if failed:
        lines += ["", "### Failed checks - details"]
        for rid, title, cwe, guide, hits in failed:
            lines += ["", f"<details><summary><b>{rid}</b> {title} ({cwe}) - {len(hits)} finding(s)</summary>", "",
                      f"**Guideline:** {guide}", ""]
            for path, ln, text in hits[:MAX_SHOWN]:
                text = text.replace("`", "'").replace("|", "\\|")
                lines.append(f"- `{path}{':' + str(ln) if ln else ''}` `{text}`")
            if len(hits) > MAX_SHOWN:
                lines.append(f"- ... and {len(hits) - MAX_SHOWN} more")
            lines += ["", "</details>"]
    areas = focus_areas(list(changes))
    if areas:
        lines += ["", "### Manual review focus (based on changed files)"] + [f"- {a}" for a in areas]
    lines += ["", "_Findings are heuristic; reviewers should confirm each one. Suppress a justified finding "
              "with a `# nosec` comment and a short reason._"]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
