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

"""Source, test, SVT and pipeline compliance gate.

Runs the vendored checkers (scripts/compliance/) for every src/<domain> and
test/<domain>, plus structural profiles for the SVT (test/system_test) and the
test pipeline (test/pipeline). Findings listed in compliance/exceptions.yml are
waived; the gate fails on an unwaived critical test failure, on a score below
compliance/baseline.json, or on a checker error.
"""
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
GITHUB = HERE.parent
ROOT = GITHUB.parent
DOMAINS = ["build_stream", "discovery", "image_build_manager", "main",
           "orchestrator", "repo_manager", "telemetry", "utils"]
TOLERANCE = 0.01
HEADER = re.compile(r"Licensed under the Apache License, Version 2\.0")
SVT_ID = re.compile(r"^SVT_[A-Z0-9]+(?:_[A-Z0-9]+)*_\d{3}$")
ID_FIELD = re.compile(r"[\"']id[\"']\s*:\s*[\"']([^\"']+)[\"']")
SECRET_ASSIGN = re.compile(r"(?i)^\s*\w*(password|passwd|secret|token|api_?key)\w*\s*[:=]\s*[\"']([^\"'$<{]{4,})[\"']")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
OK_STATES = {"PASS", "SUCCESS", "WARN"}
ID_CODES = {"build_stream": "BSM", "discovery": "DISCOVERY", "image_build_manager": "IMGBM", "main": "MAIN",
            "orchestrator": "ORCH", "repo_manager": "RM", "telemetry": "TEL", "utils": "UTILS"}
COMMENT_LIMIT = 60000
COMMENT_MARKER = "<!-- compliance-gate -->"
LEGACY_ID = re.compile(r"^(?:TC_[A-Z]{2}_\d{3}|(?:NFT|UT)_\d{3})$")


def hermetic_env():
    """Environment exposing only python3 and git, so linter-dependent checks are N/A everywhere.

    pylint, ansible-lint, gitleaks, shellcheck and bandit have their own workflows; leaving them
    discoverable would make scores differ between a laptop and a CI runner.
    """
    bindir = tempfile.mkdtemp(prefix="compliance-bin-")
    os.symlink(sys.executable, os.path.join(bindir, "python3"))
    os.symlink(shutil.which("git"), os.path.join(bindir, "git"))
    env = os.environ.copy()
    env["PATH"] = bindir
    return env


def run_checker(script, target, timeout, env):
    """Run one vendored checker and return its parsed JSON report."""
    proc = subprocess.run([sys.executable, str(HERE / "compliance" / script), target, "--json"],
                          cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False, env=env)
    data = json.loads(proc.stdout)
    return data["domains"][0] if "domains" in data else data


def normalise(scope, domain, raw):
    """Convert a checker report to categories and flat checks with OK/FAIL/N/A states."""
    categories, checks = [], []
    for cat in raw.get("categories", []):
        group = []
        for chk in cat.get("checks", []):
            status = chk["status"]
            detail = chk.get("detail")
            if detail is None:
                detail = "; ".join(chk.get("details", []))
            maximum = chk.get("max_points")
            group.append({
                "category": cat["name"], "name": chk["name"],
                "status": "N/A" if status == "N/A" else "OK" if status in OK_STATES else "FAIL",
                "detail": detail, "critical": bool(chk.get("critical")), "waived": None,
                "points": (chk.get("score", 0), maximum) if maximum is not None else None,
                "advisory": scope == "src" and maximum == 0 and "advisory" in cat["name"].lower()})
        categories.append({"name": cat["name"], "weight": cat.get("weight", 0), "checks": group})
        checks.extend(group)
    return {"scope": scope, "domain": domain, "score": float(raw.get("score", 0)), "adjusted": None,
            "totals": (raw.get("applicable_score"), raw.get("applicable_max_score")),
            "categories": categories, "checks": checks}


def split_items(detail, scope):
    """Split a checker detail into individual findings (src details contain commas)."""
    pattern = r"; |\n" if scope == "src" else r"[;,] |\n"
    return [i.strip() for i in re.split(pattern, detail) if i.strip()]


def waiver_for(item, exceptions, scope, domain, check):
    """Return the exception that waives one finding, or None."""
    for exc in exceptions:
        if exc["scope"] != scope or exc["domain"] != domain or exc["check"] not in ("*", check):
            continue
        if exc["match"] == "*" or exc["match"] in item:
            return exc
    return None


def apply_exceptions(result, exceptions):
    """Mark failing checks as waived when every finding in them is covered."""
    for chk in result["checks"]:
        chk["waived"] = None
        if chk["status"] != "FAIL" or chk["advisory"]:
            continue
        items = split_items(chk["detail"], result["scope"]) or [chk["detail"]]
        found = [waiver_for(i, exceptions, result["scope"], result["domain"], chk["name"]) for i in items]
        if all(found):
            kinds = {f["kind"] for f in found}
            chk["waived"] = "known-debt" if "known-debt" in kinds else "false-positive"


def parse_locations(detail):
    """Split 'path:line, path:line' into (path, line) pairs."""
    pairs = []
    for item in split_items(detail, "test"):
        path, _, line = item.rpartition(":")
        if path and line.isdigit():
            pairs.append((path, int(line)))
    return pairs


def logging_helpers(root):
    """Names of non-test functions below root that construct a TestLogger."""
    names = set()
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("test_"):
                if "TestLogger(" in (ast.get_source_segment(text, node) or ""):
                    names.add(node.name)
    return names


def delegates_logging(tree, line, helpers):
    """True when the test function at line calls a helper that logs through TestLogger."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno == line:
            called = {c.func.id if isinstance(c.func, ast.Name) else getattr(c.func, "attr", "")
                      for c in ast.walk(node) if isinstance(c, ast.Call)}
            return bool(called & helpers)
    return False


def set_finding(chk, remaining, ok_detail):
    """Update a check after a recheck left `remaining` findings."""
    chk["status"] = "FAIL" if remaining else "OK"
    chk["detail"] = ", ".join(remaining) if remaining else ok_detail


def refine_test(result):
    """Replace three checker verdicts that are stricter than docs/code-style/test_automation.md.

    - Canonical ID format: checked against <DOMAIN>_FVT_<TAG>_<E|V><SEQ>, <DOMAIN>_NFT_<SEQ> and
      <DOMAIN>_UT_<SEQ> for every domain (the checker knows the convention of only five domains).
    - TestLogger output: a test may delegate logging to a helper that constructs the TestLogger.
    - Registry lookup: helper modules without test functions are not tests.
    """
    root = ROOT / "test" / result["domain"]
    code = ID_CODES[result["domain"]]
    formats = (re.compile(rf"^{code}_FVT_[A-Z0-9]+(?:_[A-Z0-9]+)*_[EV]\d{{3}}$"),
               re.compile(rf"^{code}_NFT_\d{{3}}$"), re.compile(rf"^{code}_UT_\d{{3}}$"))
    helpers = logging_helpers(root)
    trees = {}

    def tree_of(rel):
        if rel not in trees:
            try:
                trees[rel] = ast.parse((root / rel).read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError):
                trees[rel] = None
        return trees[rel]

    for chk in result["checks"]:
        if chk["name"] == "Canonical ID format":
            registry = root / "library/vars/test_case_vars.py"
            ids = sorted(set(ID_FIELD.findall(registry.read_text(encoding="utf-8")))) if registry.is_file() else []
            bad = [i for i in ids if not LEGACY_ID.match(i) and not any(f.match(i) for f in formats)]
            set_finding(chk, bad, f"{len(ids)} ID(s) follow the style guide")
        elif chk["name"] == "TestLogger output" and chk["status"] == "FAIL":
            left = []
            for rel, line in parse_locations(chk["detail"]):
                tree = tree_of(rel)
                if tree is None or not delegates_logging(tree, line, helpers):
                    left.append(f"{rel}:{line}")
            set_finding(chk, left, "all tests log directly or through a helper")
        elif chk["name"] == "Registry lookup" and chk["status"] == "FAIL":
            left = []
            for rel in split_items(chk["detail"], "test"):
                tree = tree_of(rel)
                has_tests = tree is not None and any(
                    isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")
                    for n in ast.walk(tree))
                if has_tests:
                    left.append(rel)
            set_finding(chk, left, "all test files")


def adjust(result):
    """Score after refinements, treating false-positive waivers as passes (known debt still counts)."""
    def passed(chk):
        return chk["status"] == "OK" or chk["waived"] == "false-positive"
    if result["scope"] == "test":
        earned = applicable = 0.0
        for cat in result["categories"]:
            live = [c for c in cat["checks"] if c["status"] != "N/A"]
            if live:
                earned += cat["weight"] * sum(1 for c in live if passed(c)) / len(live)
                applicable += cat["weight"]
        result["adjusted"] = round(100 * earned / applicable, 2) if applicable else 0.0
    elif result["scope"] == "src" and result["totals"][1]:
        score, maximum = result["totals"]
        gain = sum(c["points"][1] - c["points"][0] for c in result["checks"]
                   if c["waived"] == "false-positive" and c["points"] and c["points"][1] > c["points"][0])
        result["adjusted"] = round(min(100.0, 100 * (score + gain) / maximum), 2)
    else:
        result["adjusted"] = result["score"]


def check_files(scope_dir, required, issues):
    """Append a message for every missing required path."""
    for rel in required:
        if not (scope_dir / rel).exists():
            issues.append(("Layout", rel, "missing"))


def py_hygiene(scope_dir, issues):
    """Header, docstring and syntax checks for every Python file below a directory."""
    for path in sorted(scope_dir.rglob("*.py")):
        if any(p in {"__pycache__", ".venv"} for p in path.parts):
            continue
        rel = str(path.relative_to(scope_dir))
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            issues.append(("Python syntax", rel, f"line {exc.lineno}"))
            continue
        if text.strip() and not HEADER.search(text[:1200]):
            issues.append(("Copyright header", rel, "missing Apache 2.0 header"))
        if tree.body and not ast.get_docstring(tree):
            issues.append(("Module docstring", rel, "missing"))
        for lineno, line in enumerate(text.splitlines(), 1):
            hit = SECRET_ASSIGN.match(line)
            if hit and not ENV_NAME.match(hit.group(2)):
                issues.append(("Secrets", rel, f"line {lineno} literal secret-like value"))


def profile_result(scope, issues, total_checks):
    """Build a normalised result from profile issues."""
    checks = [{"category": c, "name": n, "status": "FAIL", "detail": d, "critical": c == "Secrets",
               "waived": None, "points": None, "advisory": False} for c, n, d in issues]
    score = round(100.0 * max(total_checks - len(issues), 0) / total_checks, 2)
    return {"scope": scope, "domain": scope, "score": score, "adjusted": None, "totals": (None, None),
            "categories": [], "checks": checks}


def svt_profile():
    """Structural profile for test/system_test (themes, SVT_ IDs, pipeline)."""
    base = ROOT / "test" / "system_test"
    issues, total = [], 0
    required = ["README.md", "conftest.py", "pytest.ini", "requirements.txt", "run_validation.sh",
                "setup_env.sh", "user_inputs.yml", ".gitignore", "svt/test_svt.py", "docs",
                "library/functions/__init__.py", "library/messages/__init__.py",
                "library/vars/__init__.py", "library/vars/test_case_vars.py",
                "library/vars/theme_vars.py", "dataset_generator/generate_dataset.py",
                "dataset_generator/profiles", "pipeline/svt_ci.py", "pipeline/setup_svt_project.py",
                "pipeline/cleanup_svt_project.py", "pipeline/svt_pipeline_config.yml", "pipeline/README.md"]
    check_files(base, required, issues)
    total += len(required)
    registry = base / "library/vars/test_case_vars.py"
    ids = ID_FIELD.findall(registry.read_text(encoding="utf-8")) if registry.is_file() else []
    bad = [i for i in ids if not SVT_ID.match(i)]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    total += 3
    if not ids:
        issues.append(("Test metadata", "test_case_vars.py", "no SVT IDs"))
    if bad:
        issues.append(("Test metadata", "SVT ID format", ", ".join(bad[:10])))
    if dup:
        issues.append(("Test metadata", "Unique IDs", ", ".join(dup)))
    themes_file = base / "library/vars/theme_vars.py"
    themes = []
    if themes_file.is_file():
        block = themes_file.read_text(encoding="utf-8").split("THEMES", 1)[-1]
        themes = re.findall(r'^    "([a-z0-9_]+)": \{', block, re.M)
    total += max(len(themes), 1)
    if not themes:
        issues.append(("Test metadata", "THEMES", "no themes found"))
    for theme in themes:
        if not (base / f"{theme}_test_config.yml").is_file():
            issues.append(("Layout", f"{theme}_test_config.yml", "theme config missing"))
    test_files = list((base / "svt").glob("test_*.py"))
    total += len(test_files) + len(list(base.rglob("*.py")))
    py_hygiene(base, issues)
    return profile_result("svt", issues, total)


def pipeline_profile():
    """Structural profile for test/pipeline."""
    base = ROOT / "test" / "pipeline"
    issues = []
    required = ["README.md", "pipeline_config.yml", "send_email.py", "setup_gitlab_project.py", "docs/README.md"]
    check_files(base, required, issues)
    py_hygiene(base, issues)
    cfg = base / "pipeline_config.yml"
    if cfg.is_file():
        try:
            yaml.safe_load(cfg.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            issues.append(("YAML syntax", "pipeline_config.yml", str(exc).splitlines()[0]))
    return profile_result("pipeline", issues, len(required) + len(list(base.rglob("*.py"))) + 1)


ALL_SCOPES = [("test", d) for d in DOMAINS] + [("src", d) for d in DOMAINS] + [("svt", "svt"), ("pipeline", "pipeline")]
RUN_ALL_PREFIXES = ("docs/code-style/",)


def scopes_for(files):
    """Map changed file paths to the (scope, domain) pairs that must be re-checked."""
    scopes = set()
    for path in files:
        parts = path.split("/")
        if path.startswith(RUN_ALL_PREFIXES):
            return set(ALL_SCOPES)
        if len(parts) < 2 or parts[0] not in ("src", "test"):
            continue
        top, name = parts[0], parts[1]
        if top == "src" and name in DOMAINS:
            scopes.add(("src", name))
        elif top == "test" and name in DOMAINS:
            scopes.add(("test", name))
        elif top == "test" and name == "system_test":
            scopes.add(("svt", "svt"))
        elif top == "test" and name == "pipeline":
            scopes.add(("pipeline", "pipeline"))
        elif top == "test" and name == "plugins":
            scopes.update(("test", d) for d in DOMAINS)
    return scopes


def changed_files(base):
    """Return paths changed between the merge-base with base and HEAD."""
    proc = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], cwd=ROOT,
                          capture_output=True, text=True, check=True)
    return [line for line in proc.stdout.splitlines() if line]


def collect(timeout, scopes):
    """Run the selected checks in parallel and return normalised results."""
    jobs = [("test", d, "check_tests.py", f"test/{d}") for d in DOMAINS if ("test", d) in scopes]
    jobs += [("src", d, "check_domain.py", f"src/{d}") for d in DOMAINS if ("src", d) in scopes]
    results, errors = [], []
    env = hermetic_env()

    def one(job):
        scope, domain, script, target = job
        try:
            return normalise(scope, domain, run_checker(script, target, timeout, env))
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, OSError) as exc:
            errors.append(f"{scope}/{domain}: {type(exc).__name__}: {exc}")
            return None

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
        results = [r for r in pool.map(one, jobs) if r]
    if ("svt", "svt") in scopes:
        results.append(svt_profile())
    if ("pipeline", "pipeline") in scopes:
        results.append(pipeline_profile())
    return results, errors


def domain_problems(res, base):
    """Return (unwaived critical checks, problem labels) for one result."""
    crit = [c for c in res["checks"] if c["status"] == "FAIL" and c["critical"] and not c["waived"]]
    problems = []
    if crit:
        problems.append("critical")
    if base is None:
        problems.append("no baseline")
    elif res["adjusted"] + TOLERANCE < base:
        problems.append("regression")
    return crit, problems


def change_summary(files):
    """Group changed paths into readable areas for the no-domain-change comment."""
    areas = {}
    for path in files:
        parts = path.split("/")
        if path.startswith(".github/workflows/"):
            area = "workflows (.github/workflows)"
        elif parts[0] == ".github":
            area = ".github (scripts, config, templates)"
        elif parts[0] == "docs" or path.endswith(".md"):
            area = "documentation"
        else:
            area = parts[0] if len(parts) > 1 else "repository root files"
        areas[area] = areas.get(area, 0) + 1
    return [f"{name}: {count} file(s)" for name, count in sorted(areas.items())]


def render_no_domain_comment(files):
    """Render the PR comment used when the PR changes no src, test, SVT or pipeline domain."""
    lines = [COMMENT_MARKER, "## Compliance Gate", "",
             "**Result: no domain changes found**", "",
             "- [x] Nothing to check: this PR does not change any `src/<domain>`, `test/<domain>`, "
             "SVT (`test/system_test`) or pipeline (`test/pipeline`) path.", ""]
    summary = change_summary(files)
    if summary:
        lines += ["Changed areas:"] + [f"- {item}" for item in summary] + [""]
    lines.append("The gate checks all domains when a PR changes the shared test plugin or `docs/code-style/**`; "
                 "run the workflow manually to check everything.")
    return "\n".join(lines)


def render_comment(results, baseline, errors, skipped, reason):
    """Render the PR comment: one section per checked domain, marked passed or not passed."""
    ordered = sorted(results, key=lambda r: (r["scope"], r["domain"]))
    verdicts = {(r["scope"], r["domain"]): domain_problems(r, baseline.get(r["scope"], {}).get(r["domain"])) for r in ordered}
    failed = [k for k, (_, probs) in verdicts.items() if probs]
    lines = [COMMENT_MARKER, "## Compliance Gate", "",
             f"**Result: {len(ordered) - len(failed)} passed, {len(failed)} not passed** "
             f"({len(ordered)} domain scope(s) checked; unchanged domains are skipped)", ""]
    if skipped:
        lines += [f"Not checked ({reason}): " + ", ".join(f"{s}/{d}" for s, d in sorted(skipped)), ""]
    for res in ordered:
        key = (res["scope"], res["domain"])
        crit, problems = verdicts[key]
        base = baseline.get(res["scope"], {}).get(res["domain"])
        open_rows = [c for c in res["checks"] if c["status"] == "FAIL" and not c["advisory"] and not c["waived"]]
        state = "NOT PASSED" if problems else "PASSED"
        lines += [f"### {res['scope']}/{res['domain']}: {state}", "",
                  f"- [{' ' if problems else 'x'}] **{state}** score {res['adjusted']:.1f}, baseline "
                  f"{'-' if base is None else format(base, '.1f')}"
                  + (f" ({', '.join(problems)})" if problems else "")]
        for chk in res["checks"]:
            if chk["status"] != "FAIL":
                continue
            if chk["advisory"]:
                tag, box = "ADVISORY", "x"
            elif chk["waived"] == "false-positive":
                tag, box = "WAIVED false positive", "x"
            elif chk["waived"] == "known-debt":
                tag, box = "KNOWN DEBT", " "
            else:
                tag, box = ("OPEN critical" if chk["critical"] else "OPEN"), " "
            lines.append(f"- [{box}] {tag}: {chk['category']} / {chk['name']}: {chk['detail'][:160]}")
        if not any(c["status"] == "FAIL" for c in res["checks"]):
            lines.append("- [x] No findings")
        lines.append(f"- Open findings: {len(open_rows)}")
        lines.append("")
    if errors:
        lines += ["### Checker errors", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines)


def report(results, baseline, errors, skipped, reason):
    """Render the markdown report and return (text, failures)."""
    failures = list(errors)
    ordered = sorted(results, key=lambda r: (r["scope"], r["domain"]))
    lines = ["## Compliance Gate: src, test, SVT, pipeline", "",
             "Adjusted = checker score after the gate's rechecks, counting false-positive waivers as passes.", "",
             "| Scope | Domain | Checker | Adjusted | Baseline | Unwaived critical | Waived (fp/debt) | Result |",
             "|---|---|---:|---:|---:|---|---|---|"]
    for res in ordered:
        base = baseline.get(res["scope"], {}).get(res["domain"])
        crit, problems = domain_problems(res, base)
        fp = sum(1 for c in res["checks"] if c["waived"] == "false-positive")
        debt = sum(1 for c in res["checks"] if c["waived"] == "known-debt")
        if problems:
            failures.append(f"{res['scope']}/{res['domain']}: {', '.join(problems)}")
        lines.append(f"| {res['scope']} | {res['domain']} | {res['score']:.1f} | {res['adjusted']:.1f} | "
                     f"{'-' if base is None else format(base, '.1f')} | "
                     f"{', '.join(c['name'] for c in crit) or '-'} | {fp}/{debt} | "
                     f"{'FAIL' if problems else 'PASS'} |")
    if skipped:
        lines += ["", f"Not checked ({reason}): " + ", ".join(f"{sc}/{dm}" for sc, dm in sorted(skipped))]
    lines += ["", "### Findings", ""]
    for res in ordered:
        rows = [c for c in res["checks"] if c["status"] == "FAIL"]
        if not rows:
            continue
        lines.append(f"**{res['scope']}/{res['domain']}**")
        for chk in rows:
            tag = "advisory" if chk["advisory"] else {"known-debt": "waived: known debt",
                                                      "false-positive": "waived: false positive"}.get(chk["waived"], "OPEN")
            lines.append(f"- [{tag}] {chk['category']} / {chk['name']}: {chk['detail'][:240]}")
        lines.append("")
    if errors:
        lines += ["### Checker errors", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines), failures


def main():
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=int, default=1200, help="per-checker timeout in seconds")
    ap.add_argument("--update-baseline", action="store_true", help="rewrite compliance/baseline.json")
    ap.add_argument("--no-fail", action="store_true", help="report only; always exit 0")
    ap.add_argument("--base", help="git ref; check only domains changed since its merge-base with HEAD")
    ap.add_argument("--comment-file", type=Path, help="write the per-domain PR comment markdown to this file")
    ap.add_argument("--changed-files", type=Path, help="file with one changed path per line (instead of --base)")
    args = ap.parse_args()
    exceptions = yaml.safe_load((GITHUB / "compliance" / "exceptions.yml").read_text(encoding="utf-8"))["exceptions"]
    for exc in exceptions:
        exc.setdefault("match", "*")
    for exc in exceptions:
        if not exc.get("reason") or exc.get("kind") not in {"false-positive", "known-debt"}:
            sys.exit(f"::error::exception needs reason and kind (false-positive|known-debt): {exc}")
    if args.changed_files:
        files = args.changed_files.read_text(encoding="utf-8").split()
    elif args.base:
        files = changed_files(args.base)
    else:
        files = None
    scopes = set(ALL_SCOPES) if files is None else scopes_for(files)
    skipped = set(ALL_SCOPES) - scopes
    reason = "no changes in that domain" if files is not None else ""
    results, errors = collect(args.timeout, scopes)
    for res in results:
        if res["scope"] == "test":
            refine_test(res)
        apply_exceptions(res, exceptions)
        adjust(res)
    base_path = GITHUB / "compliance" / "baseline.json"
    if args.update_baseline:
        data = json.loads(base_path.read_text(encoding="utf-8")) if base_path.is_file() else {}
        for res in results:
            data.setdefault(res["scope"], {})[res["domain"]] = round(res["adjusted"], 2)
        base_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    baseline = json.loads(base_path.read_text(encoding="utf-8"))
    text, failures = report(results, baseline, errors, skipped, reason)
    if files is not None and not scopes:
        text += "\n\nNo src/test/SVT/pipeline domain changed in this PR; nothing to check."
    print(text)
    if args.comment_file:
        if files is not None and not scopes:
            comment = render_no_domain_comment(files)
        else:
            comment = render_comment(results, baseline, errors, skipped, reason)
        if len(comment) > COMMENT_LIMIT:
            comment = comment[:COMMENT_LIMIT] + "\n\n... truncated; see the job summary for the full report."
        args.comment_file.write_text(comment + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    for failure in failures:
        print(f"::error::{failure}")
    return 0 if args.no_fail or not failures else 1


if __name__ == "__main__":
    sys.exit(main())
