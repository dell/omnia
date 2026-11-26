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
"""
Omnia Domain Completion Checker - automated scoring tool.

Scans an Omnia domain directory and produces a scored compliance report
against the Galaxy collection structure, coding standards, and domain
independence rules.

Usage:
    python check_domain.py <domain_path>
    python check_domain.py src/repo_manager
    python check_domain.py src/image_build_manager --json
"""

import argparse
import ast
import io
import json
import os
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from pathlib import Path
from typing import Optional


@dataclass
class CheckResult:
    """Result of a single check."""
    name: str
    max_points: int
    score: int = 0
    status: str = "FAIL"
    details: list = field(default_factory=list)


@dataclass
class CategoryResult:
    """Result of a scored category."""
    category_id: int
    name: str
    weight: int
    checks: list = field(default_factory=list)
    score: int = 0
    max_score: int = 0
    status: str = "FAIL"


BOOTSTRAP_NOT_APPLICABLE = {
    1: "src/main is the bootstrap/CLI layer, not a Galaxy collection",
    2: "src/main does not provide Ansible modules",
    3: "src/main does not provide Ansible roles",
    4: "src/main has no domain input-validation contract",
    5: "src/main dispatches domains and has no domain playbook entry point",
    6: "src/main is the integration layer being integrated with",
    7: "src/main has no Ansible task files",
    8: "src/main does not execute as an Ansible domain",
    10: "cross-domain coordination is the responsibility of src/main",
    11: "domain-specific static gates do not apply to the bootstrap/CLI layer",
}

class CheckStatus(Enum):
    """Canonical compliance status labels."""

    PASS = auto()


# The enum name is the external report label; no credential is involved.
CHECK_STATUS_PASSED = CheckStatus.PASS.name


def finalize_category(category: CategoryResult) -> CategoryResult:
    """Recalculate a category after excluding N/A checks."""
    applicable = [check for check in category.checks if check.status != "N/A"]
    category.score = sum(check.score for check in applicable)
    category.max_score = sum(check.max_points for check in applicable)
    if not applicable:
        category.status = "N/A"
    elif all(check.status == CHECK_STATUS_PASSED for check in applicable):
        category.status = CHECK_STATUS_PASSED
    elif any(check.status == "FAIL" for check in applicable):
        category.status = "FAIL"
    else:
        category.status = "PARTIAL"
    return category


def mark_category_not_applicable(category: CategoryResult, reason: str) -> None:
    """Mark every check in a category as not applicable."""
    for check in category.checks:
        check.score = 0
        check.max_points = 0
        check.status = "N/A"
        check.details = [reason]
    finalize_category(category)


def apply_domain_profile(domain: Path, categories: list[CategoryResult]) -> str:
    """Apply explicit component profiles without hiding domain failures."""
    if domain.name != "main":
        return "galaxy-domain"

    for category in categories:
        reason = BOOTSTRAP_NOT_APPLICABLE.get(category.category_id)
        if reason:
            mark_category_not_applicable(category, reason)
        elif category.category_id == 9:
            for check in category.checks:
                if check.name in {"Architecture or design docs", "Contract docs quality"}:
                    check.score = 0
                    check.max_points = 0
                    check.status = "N/A"
                    check.details = [
                        "bootstrap design and integration contracts are maintained in repository-level docs"
                    ]
            finalize_category(category)
    return "bootstrap"


def report_totals(categories: list[CategoryResult]) -> tuple[int | float, int, int]:
    """Return normalized score plus applicable earned and maximum points."""
    earned = sum(category.score for category in categories)
    applicable = sum(category.max_score for category in categories)
    normalized = round(100 * earned / applicable, 2) if applicable else 0
    if isinstance(normalized, float) and normalized.is_integer():
        normalized = int(normalized)
    return normalized, earned, applicable


def find_files(base: Path, pattern: str, recursive: bool = True) -> list:
    """Find files matching a glob pattern."""
    if recursive:
        return list(base.rglob(pattern))
    return list(base.glob(pattern))


def file_contains(filepath: Path, pattern: str) -> bool:
    """Check if a file contains a regex pattern."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
        return bool(re.search(pattern, text, re.MULTILINE))
    except (OSError, UnicodeDecodeError):
        return False


def count_pattern_in_files(files: list, pattern: str) -> int:
    """Count how many files contain a pattern."""
    return sum(1 for f in files if file_contains(f, pattern))


def repository_root(path: Path) -> Path:
    """Locate the repository that contains a scanned domain."""
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists() or (candidate / ".github/workflows").is_dir():
            return candidate
    return path.parent


# Defensive fallback defaults that keep an omnia.env path variable
# overridable (e.g. OMNIA_DATA_PATH, OMNIA_VENV_PATH) are not hardcoding.
OPT_OMNIA_FALLBACK_RE = re.compile(
    r"default\(\s*['\"]?/opt/omnia|"
    r"(?:getenv|environ\.get|environ\.setdefault)\(\s*['\"]OMNIA_[A-Z_]+['\"]\s*,"
    r"\s*['\"]/opt/omnia|"
    r"\$\{OMNIA_[A-Z_]+:?[-=]/opt/omnia|"
    r"OMNIA_[A-Z_]+:?[-=]/opt/omnia"
)

# Inline waiver for a non-host path that must stay literal, e.g.
#   path: "/opt/omnia"  # opt-omnia-waiver: container-internal mount target
# A reason is mandatory; waived lines are listed in the report.
OPT_OMNIA_WAIVER_RE = re.compile(r"#\s*opt-omnia-waiver:\s*(\S.*)$")

GALAXY_DOC_BLOCKS = {"DOCUMENTATION", "EXAMPLES", "RETURN"}


def python_runtime_text(content: str) -> str:
    """Return Python source with comments, docstrings, and Galaxy doc blocks blanked."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return content
    drop: set[int] = set()
    for node in ast.walk(tree):
        is_docstring = (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        is_doc_block = isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in GALAXY_DOC_BLOCKS for t in node.targets
        )
        if is_docstring or is_doc_block:
            drop.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    lines = content.splitlines()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(content).readline):
            if tok.type == tokenize.COMMENT:
                row, col = tok.start
                lines[row - 1] = lines[row - 1][:col]
    except (tokenize.TokenError, IndentationError):
        pass
    return "\n".join(
        line for number, line in enumerate(lines, 1) if number not in drop
    )


def task_block(text: str, pos: int) -> str:
    """Return the YAML task (``- name:`` to next ``- name:``) containing ``pos``."""
    starts = [m.start() for m in re.finditer(r"^\s*- name:", text, re.MULTILINE)]
    begin = max((s for s in starts if s <= pos), default=0)
    end = min((s for s in starts if s > pos), default=len(text))
    return text[begin:end]


def has_python_statements(path: Path) -> bool:
    """Return False for modules containing only comments (pylint gives no score)."""
    try:
        return bool(ast.parse(path.read_text(encoding="utf-8", errors="ignore")).body)
    except (OSError, SyntaxError):
        return True


def tracked_files(domain: Path, repo: Path, pattern: str) -> list:
    """Return git-tracked files under ``domain`` matching ``pattern``.

    Untracked local artifacts (caches, test debris) are not part of the
    domain. Falls back to a filesystem glob outside a git checkout.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z", "--", str(domain)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return find_files(domain, pattern)
    files = [repo / name for name in result.stdout.split("\0") if name]
    return [f for f in files if f.match(pattern) and f.is_file()]


def sibling_domains(domain: Path) -> set[str]:
    """Return the names of the other Galaxy domains beside ``domain``."""
    parent = domain.parent
    if not parent.is_dir():
        return set()
    return {
        d.name for d in parent.iterdir()
        if d.is_dir() and d != domain and (d / "galaxy.yml").exists()
    }


def read_without_comments(path: Path) -> str:
    """Read a YAML/Jinja2 file with comment-only lines removed."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith(("#", "{#"))
    )


def detect_upstream_domains(domain: Path) -> set[str]:
    """Detect domains whose published output contracts this domain consumes.

    An upstream contract is another domain's *output* artifact (for example
    ``<OMNIA_DATA_PATH>/repo_manager/output/<project>/repo_status.yml``) or a
    ``samples/<other_domain>_*`` contract sample. Reading another domain's
    operator input files, or a sample of the domain's own status output, is
    not an upstream contract dependency.
    """
    siblings = sibling_domains(domain)
    if not siblings:
        return set()
    found: set[str] = set()
    output_ref = re.compile(
        r"/(" + "|".join(map(re.escape, sorted(siblings))) + r")/output\b"
    )
    for sub in ("roles", "playbooks"):
        base = domain / sub
        if not base.is_dir():
            continue
        for ext in ("*.yml", "*.yaml", "*.j2"):
            for path in base.rglob(ext):
                found.update(output_ref.findall(read_without_comments(path)))
    samples = domain / "samples"
    if samples.is_dir():
        for entry in samples.iterdir():
            for name in siblings:
                if entry.name.startswith(f"{name}_"):
                    found.add(name)
    return found


def precheck_verifies_domain(precheck_roles: list, upstream: str) -> bool:
    """Return True when a precheck role stats an artifact of ``upstream``."""
    for role in precheck_roles:
        texts = []
        for sub in ("tasks", "vars", "defaults"):
            sub_dir = role / sub
            if sub_dir.is_dir():
                texts.extend(
                    read_without_comments(p)
                    for p in list(sub_dir.rglob("*.yml")) + list(sub_dir.rglob("*.yaml"))
                )
        combined = "\n".join(texts)
        if upstream in combined and re.search(r"ansible\.builtin\.stat\b", combined):
            return True
    return False


# Category Checkers -------------------------------------------------------

def check_galaxy_structure(domain: Path) -> CategoryResult:
    """Category 1: Galaxy Structure (15 points)."""
    cat = CategoryResult(1, "Galaxy Structure", 15, max_score=15)

    # galaxy.yml
    galaxy_yml = domain / "galaxy.yml"
    c = CheckResult("galaxy.yml exists", 4)
    if galaxy_yml.exists():
        c.score = 4
        c.status = "PASS"
    else:
        c.details.append("Missing galaxy.yml")
    cat.checks.append(c)

    # meta/runtime.yml
    runtime_yml = domain / "meta" / "runtime.yml"
    c = CheckResult("meta/runtime.yml exists", 1)
    if runtime_yml.exists():
        c.score = 1
        c.status = "PASS"
    else:
        c.details.append("Missing meta/runtime.yml")
    cat.checks.append(c)

    # plugins/modules/
    c = CheckResult("plugins/modules/ directory", 3)
    plugins_modules = domain / "plugins" / "modules"
    library_modules = domain / "library" / "modules"
    if plugins_modules.is_dir():
        c.score = 3
        c.status = "PASS"
    elif library_modules.is_dir():
        c.score = 1
        c.status = "PARTIAL"
        c.details.append("Uses legacy library/modules/ - migrate to plugins/modules/")
    else:
        c.details.append("No modules directory found")
    cat.checks.append(c)

    # plugins/module_utils/
    c = CheckResult("plugins/module_utils/ directory", 3)
    plugins_mu = domain / "plugins" / "module_utils"
    library_mu = domain / "library" / "module_utils"
    if plugins_mu.is_dir():
        c.score = 3
        c.status = "PASS"
    elif library_mu.is_dir():
        c.score = 1
        c.status = "PARTIAL"
        c.details.append("Uses legacy library/module_utils/ - migrate to plugins/module_utils/")
    else:
        c.score = 3
        c.status = "PASS"
        c.details.append("No module_utils needed (acceptable for small domains)")
    cat.checks.append(c)

    # plugins/callback/ (optional, 2 pts if present or not needed)
    c = CheckResult("plugins/callback/ or not needed", 1)
    plugins_cb = domain / "plugins" / "callback"
    legacy_cb = domain / "callback_plugins"
    if plugins_cb.is_dir():
        c.score = 1
        c.status = "PASS"
    elif legacy_cb.is_dir():
        c.score = 0
        c.status = "FAIL"
        c.details.append("Uses legacy callback_plugins/ - migrate to plugins/callback/")
    else:
        c.score = 1
        c.status = "PASS"
        c.details.append("No callback plugins (acceptable)")
    cat.checks.append(c)

    # requirements.txt
    c = CheckResult("requirements.txt exists", 1)
    if (domain / "requirements.txt").exists():
        c.score = 1
        c.status = "PASS"
    else:
        c.details.append("Missing requirements.txt")
    cat.checks.append(c)

    # requirements.yml
    c = CheckResult("requirements.yml exists", 1)
    if (domain / "requirements.yml").exists():
        c.score = 1
        c.status = "PASS"
    else:
        c.details.append("Missing requirements.yml")
    cat.checks.append(c)

    # CHANGELOG.md
    c = CheckResult("CHANGELOG.md exists", 1)
    if (domain / "CHANGELOG.md").exists():
        c.score = 1
        c.status = "PASS"
    else:
        c.details.append("Missing CHANGELOG.md")
    cat.checks.append(c)

    cat.score = sum(ch.score for ch in cat.checks)
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


def check_module_documentation(domain: Path) -> CategoryResult:
    """Category 2: Module Documentation (10 points)."""
    cat = CategoryResult(2, "Module Documentation", 10, max_score=10)

    # Find modules in plugins/modules/ or library/modules/
    modules_dir = domain / "plugins" / "modules"
    if not modules_dir.is_dir():
        modules_dir = domain / "library" / "modules"

    if not modules_dir.is_dir():
        cat.score = 10
        cat.status = "PASS"
        cat.checks.append(CheckResult("No modules directory", 10, 10, "PASS",
                                       ["No modules to check - full marks"]))
        return cat

    py_files = [f for f in modules_dir.glob("*.py") if f.name != "__init__.py"]
    if not py_files:
        cat.score = 10
        cat.status = "PASS"
        cat.checks.append(CheckResult("No module files", 10, 10, "PASS",
                                       ["No modules to check - full marks"]))
        return cat

    total = len(py_files)
    has_doc = count_pattern_in_files(py_files, r"^DOCUMENTATION\s*=")
    has_ex = count_pattern_in_files(py_files, r"^EXAMPLES\s*=")
    has_ret = count_pattern_in_files(py_files, r"^RETURN\s*=")

    c_doc = CheckResult("DOCUMENTATION block", 4)
    c_doc.score = int((has_doc / total) * 4) if total else 4
    c_doc.status = "PASS" if has_doc == total else ("PARTIAL" if has_doc > 0 else "FAIL")
    c_doc.details.append(f"{has_doc}/{total} modules have DOCUMENTATION")
    cat.checks.append(c_doc)

    c_ex = CheckResult("EXAMPLES block", 3)
    c_ex.score = int((has_ex / total) * 3) if total else 3
    c_ex.status = "PASS" if has_ex == total else ("PARTIAL" if has_ex > 0 else "FAIL")
    c_ex.details.append(f"{has_ex}/{total} modules have EXAMPLES")
    cat.checks.append(c_ex)

    c_ret = CheckResult("RETURN block", 3)
    c_ret.score = int((has_ret / total) * 3) if total else 3
    c_ret.status = "PASS" if has_ret == total else ("PARTIAL" if has_ret > 0 else "FAIL")
    c_ret.details.append(f"{has_ret}/{total} modules have RETURN")
    cat.checks.append(c_ret)

    # List modules missing blocks
    for f in py_files:
        missing = []
        if not file_contains(f, r"^DOCUMENTATION\s*="):
            missing.append("DOCUMENTATION")
        if not file_contains(f, r"^EXAMPLES\s*="):
            missing.append("EXAMPLES")
        if not file_contains(f, r"^RETURN\s*="):
            missing.append("RETURN")
        if missing:
            cat.checks.append(CheckResult(
                f.name, 0, 0, "FAIL",
                [f"Missing: {', '.join(missing)}"]
            ))

    cat.score = sum(ch.score for ch in cat.checks[:3])
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


def check_role_metadata(domain: Path) -> CategoryResult:
    """Category 3: Role Metadata (10 points)."""
    cat = CategoryResult(3, "Role Metadata", 10, max_score=10)

    roles_dir = domain / "roles"
    if not roles_dir.is_dir():
        cat.score = 10
        cat.status = "PASS"
        cat.checks.append(CheckResult("No roles directory", 10, 10, "PASS",
                                       ["No roles to check - full marks"]))
        return cat

    roles = [d for d in roles_dir.iterdir() if d.is_dir() and d.name != "__pycache__"]
    if not roles:
        cat.score = 10
        cat.status = "PASS"
        return cat

    total = len(roles)
    has_readme = sum(1 for r in roles if (r / "README.md").exists())
    has_meta = sum(1 for r in roles if (r / "meta" / "main.yml").exists())

    c_readme = CheckResult("README.md in every role", 5)
    c_readme.score = int((has_readme / total) * 5) if total else 5
    c_readme.status = "PASS" if has_readme == total else ("PARTIAL" if has_readme > 0 else "FAIL")
    c_readme.details.append(f"{has_readme}/{total} roles have README.md")
    cat.checks.append(c_readme)

    c_meta = CheckResult("meta/main.yml in every role", 5)
    c_meta.score = int((has_meta / total) * 5) if total else 5
    c_meta.status = "PASS" if has_meta == total else ("PARTIAL" if has_meta > 0 else "FAIL")
    c_meta.details.append(f"{has_meta}/{total} roles have meta/main.yml")
    cat.checks.append(c_meta)

    # List roles missing metadata
    for r in roles:
        missing = []
        if not (r / "README.md").exists():
            missing.append("README.md")
        if not (r / "meta" / "main.yml").exists():
            missing.append("meta/main.yml")
        if missing:
            cat.checks.append(CheckResult(
                r.name, 0, 0, "FAIL",
                [f"Missing: {', '.join(missing)}"]
            ))

    cat.score = sum(ch.score for ch in cat.checks[:2])
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


def check_input_validation(domain: Path) -> CategoryResult:
    """Category 4: Input Validation Structure (10 points)."""
    cat = CategoryResult(4, "Input Validation Structure", 10, max_score=10)

    # Find input_validation dir
    iv_dir: Optional[Path] = None
    for base in ["plugins/module_utils", "library/module_utils"]:
        candidate = domain / base / "input_validation"
        if candidate.is_dir():
            iv_dir = candidate
            break

    # Also check non-standard naming
    if iv_dir is None:
        for base in ["plugins/module_utils", "library/module_utils"]:
            base_path = domain / base
            if base_path.is_dir():
                for d in base_path.iterdir():
                    if d.is_dir() and "validation" in d.name.lower():
                        iv_dir = d
                        break

    if iv_dir is None:
        # Check if domain even has config files to validate
        input_dir = domain / "input"
        if not input_dir.is_dir():
            cat.score = 10
            cat.status = "PASS"
            cat.checks.append(CheckResult("No input validation needed", 10, 10, "PASS",
                                           ["Domain has no input/ directory - no config to validate"]))
            return cat
        else:
            cat.checks.append(CheckResult("input_validation directory", 0, 0, "FAIL",
                                           ["Has input/ but no validation module found"]))
            return cat

    # Check four-directory structure
    c_core = CheckResult("core/ directory with validation_engine.py", 3)
    core_dir = iv_dir / "core"
    if core_dir.is_dir():
        engine = core_dir / "validation_engine.py"
        if engine.exists():
            c_core.score = 3
            c_core.status = "PASS"
        else:
            c_core.score = 1
            c_core.status = "PARTIAL"
            c_core.details.append("core/ exists but missing validation_engine.py")
    else:
        c_core.details.append("Missing core/ directory")
    cat.checks.append(c_core)

    c_msg = CheckResult("messages/ directory with constants", 3)
    msg_dir = iv_dir / "messages"
    if msg_dir.is_dir():
        py_files = list(msg_dir.glob("*.py"))
        msg_files = [f for f in py_files if f.name != "__init__.py"]
        if msg_files:
            # Check at least one uses UPPER_SNAKE_CASE constants
            has_constants = any(
                file_contains(f, r'^[A-Z][A-Z0-9_]+_MSG\s*=')
                for f in msg_files
            )
            if has_constants:
                c_msg.score = 3
                c_msg.status = "PASS"
            else:
                c_msg.score = 2
                c_msg.status = "PARTIAL"
                c_msg.details.append("messages/ exists but no UPPER_SNAKE_CASE constants found")
        else:
            c_msg.score = 1
            c_msg.status = "PARTIAL"
            c_msg.details.append("messages/ exists but is empty")
    else:
        c_msg.details.append("Missing messages/ directory")
    cat.checks.append(c_msg)

    c_schema = CheckResult("schema/ directory with .json files", 2)
    schema_dir = iv_dir / "schema"
    if schema_dir.is_dir():
        json_files = list(schema_dir.glob("*.json"))
        if json_files:
            c_schema.score = 2
            c_schema.status = "PASS"
            c_schema.details.append(f"{len(json_files)} schema files found")
        else:
            c_schema.score = 1
            c_schema.status = "PARTIAL"
            c_schema.details.append("schema/ exists but no .json files")
    else:
        c_schema.details.append("Missing schema/ directory")
    cat.checks.append(c_schema)

    c_val = CheckResult("validators/ directory with validate()", 2)
    val_dir = iv_dir / "validators"
    if val_dir.is_dir():
        py_files = [f for f in val_dir.glob("*.py") if f.name != "__init__.py"]
        if py_files:
            has_validate = any(file_contains(f, r'def validate\(') for f in py_files)
            if has_validate:
                c_val.score = 2
                c_val.status = "PASS"
            else:
                c_val.score = 1
                c_val.status = "PARTIAL"
                c_val.details.append("validators/ has files but none expose validate()")
        else:
            c_val.score = 1
            c_val.status = "PARTIAL"
            c_val.details.append("validators/ exists but is empty")
    else:
        c_val.details.append("Missing validators/ directory")
    cat.checks.append(c_val)

    # Deductions: inline messages
    all_py = list(iv_dir.rglob("*.py"))
    validator_files = [f for f in all_py
                       if f.parent.name not in ("messages", "schema", "__pycache__")
                       and f.name != "__init__.py"
                       and "message" not in f.name.lower()]
    inline_count = 0
    for f in validator_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            # Count lines with inline error strings in append() calls
            for line in text.splitlines():
                if "errors.append(" in line and ("'" in line or '"' in line):
                    if "msg." not in line and "messages." not in line and "_MSG" not in line:
                        inline_count += 1
        except (OSError, UnicodeDecodeError):
            pass

    if inline_count > 0:
        deduction = min(2, inline_count)
        c_inline = CheckResult("Inline error messages deduction", 0)
        c_inline.score = -deduction
        c_inline.status = "FAIL"
        c_inline.details.append(f"{inline_count} inline error strings found in validators (-{deduction})")
        cat.checks.append(c_inline)

    cat.score = max(0, sum(ch.score for ch in cat.checks))
    cat.score = min(cat.max_score, cat.score)
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


def check_entry_point(domain: Path) -> CategoryResult:
    """Category 5: Entry Point & Tags (10 points)."""
    cat = CategoryResult(5, "Entry Point & Tags", 10, max_score=10)
    domain_name = domain.name

    # Top-level playbook
    playbooks_dir = domain / "playbooks"
    c_entry = CheckResult("Entry point playbook exists", 3)
    entry_playbook = None
    if playbooks_dir.is_dir():
        for pattern in [f"{domain_name}.yml", f"{domain_name}.yaml", "main.yml"]:
            candidate = playbooks_dir / pattern
            if candidate.exists():
                entry_playbook = candidate
                break
        if entry_playbook is None:
            yamls = list(playbooks_dir.glob("*.yml")) + list(playbooks_dir.glob("*.yaml"))
            if yamls:
                entry_playbook = yamls[0]

    # Also check root
    if entry_playbook is None:
        for pattern in [f"{domain_name}.yml", f"{domain_name}.yaml"]:
            candidate = domain / pattern
            if candidate.exists():
                entry_playbook = candidate
                break

    if entry_playbook:
        c_entry.score = 3
        c_entry.status = "PASS"
        c_entry.details.append(f"Found: {entry_playbook.relative_to(domain)}")
    else:
        c_entry.details.append("No entry point playbook found")
    cat.checks.append(c_entry)

    # Uses import_playbook/import_role
    c_import = CheckResult("Uses import_playbook/import_role", 2)
    if entry_playbook and entry_playbook.exists():
        has_import = file_contains(entry_playbook, r"import_playbook:|import_role:")
        if has_import:
            c_import.score = 2
            c_import.status = "PASS"
        else:
            c_import.details.append("Entry point does not use import_playbook/import_role")
    else:
        c_import.details.append("No entry point to check")
    cat.checks.append(c_import)

    # Tags
    c_tags = CheckResult("Uses standard tags", 3)
    standard_tags = {"precheck", "validate", "prepare", "execute", "build", "cleanup", "setup", "upgrade", "rollback"}
    if entry_playbook and entry_playbook.exists():
        text = entry_playbook.read_text(encoding="utf-8", errors="ignore")
        found_tags = set()
        for tag in standard_tags:
            if tag in text:
                found_tags.add(tag)
        if found_tags:
            c_tags.score = min(3, len(found_tags))
            c_tags.status = "PASS" if c_tags.score == 3 else "PARTIAL"
            c_tags.details.append(f"Tags found: {', '.join(sorted(found_tags))}")
        else:
            c_tags.details.append("No standard tags found")
    else:
        c_tags.details.append("No entry point to check")
    cat.checks.append(c_tags)

    # No duplicate flat playbooks
    c_dup = CheckResult("No duplicate flat playbooks", 2)
    c_dup.score = 2
    c_dup.status = "PASS"
    if playbooks_dir and playbooks_dir.is_dir():
        root_ymls = {f.name for f in domain.glob("*.yml") if f.name != "galaxy.yml"}
        sub_ymls = {f.name for f in playbooks_dir.rglob("*.yml")}
        duplicates = root_ymls & sub_ymls
        if duplicates:
            c_dup.score = 0
            c_dup.status = "FAIL"
            c_dup.details.append(f"Duplicate playbooks at root and playbooks/: {', '.join(duplicates)}")
    cat.checks.append(c_dup)

    cat.score = sum(ch.score for ch in cat.checks)
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


def check_domain_integration(domain: Path) -> CategoryResult:
    """Category 6: Domain Integration (15 points).

    Checks domain-level integration with src/main (omnia.sh, omnia-cli,
    omnia.env), input/output handling, precheck role, and
    validate_system_environment as defined in:
      - docs/design/domain-integration.md
      - docs/design/omnia-domain-repo-design.md §3-§11
    """
    cat = CategoryResult(6, "Domain Integration", 15, max_score=15)
    domain_name = domain.name

    # domain-init.sh exists (2 pts)
    init_script = domain / "domain-init.sh"
    legacy_script = domain / "copy-input.sh"
    c_init = CheckResult("domain-init.sh exists", 2)
    if init_script.exists():
        c_init.score = 2
        c_init.status = "PASS"
    elif legacy_script.exists():
        c_init.score = 1
        c_init.status = "PARTIAL"
        c_init.details.append("Uses legacy copy-input.sh — rename to domain-init.sh")
    else:
        c_init.details.append("Missing domain-init.sh (required by omnia.sh --init)")
    cat.checks.append(c_init)

    # domain-init.sh copies input files (1 pt)
    actual_init = init_script if init_script.exists() else legacy_script
    c_cpinput = CheckResult("domain-init.sh copies input files", 1)
    if actual_init.exists():
        if file_contains(actual_init, r'cp |rsync |copy_input'):
            c_cpinput.score = 1
            c_cpinput.status = "PASS"
        else:
            c_cpinput.details.append("domain-init.sh does not copy input files")
    else:
        c_cpinput.details.append("No init script to check")
    cat.checks.append(c_cpinput)

    # input/ is FLAT — no project subdirectory in source (1 pt)
    c_input_flat = CheckResult("input/ is flat (no project subdirs)", 1)
    input_dir = domain / "input"
    if input_dir.is_dir():
        subdirs = [d for d in input_dir.iterdir() if d.is_dir()
                   and d.name != "__pycache__"]
        if not subdirs:
            c_input_flat.score = 1
            c_input_flat.status = "PASS"
        else:
            c_input_flat.details.append(
                f"input/ has subdirectories (must be flat templates): "
                f"{', '.join(d.name for d in subdirs)}"
            )
    else:
        c_input_flat.score = 1
        c_input_flat.status = "PASS"
        c_input_flat.details.append("No input/ directory (acceptable for some domains)")
    cat.checks.append(c_input_flat)

    # Status file writer (1 pt) — domain writes <domain>_status.yml
    c_status = CheckResult("Status file writer", 1)
    yml_files = list(domain.rglob("*.yml")) + list(domain.rglob("*.yaml"))
    status_found = any(
        file_contains(f, r"_status\.yml|status_file|write.*status")
        for f in yml_files
    )
    if status_found:
        c_status.score = 1
        c_status.status = "PASS"
    else:
        c_status.details.append("No status file writer found (omnia-cli reads <domain>_status.yml)")
    cat.checks.append(c_status)

    # Output goes to output_project_dir (1 pt)
    c_output = CheckResult("Output uses output_project_dir", 1)
    output_ref_found = any(
        file_contains(f, r"output_project_dir|shared_path.*output")
        for f in yml_files
    )
    if output_ref_found:
        c_output.score = 1
        c_output.status = "PASS"
    else:
        c_output.details.append("No references to output_project_dir in tasks")
    cat.checks.append(c_output)

    # Setup role (1 pt)
    roles_dir = domain / "roles"
    c_setup = CheckResult("Setup role exists", 1)
    setup_roles = []
    if roles_dir.is_dir():
        setup_roles = [d for d in roles_dir.iterdir()
                       if d.is_dir() and ("setup" in d.name or "validation" in d.name)]
        if setup_roles:
            c_setup.score = 1
            c_setup.status = "PASS"
            c_setup.details.append(f"Found: {', '.join(r.name for r in setup_roles)}")
        else:
            c_setup.details.append("No setup/validation role found")
    else:
        c_setup.details.append("No roles directory")
    cat.checks.append(c_setup)

    # Precheck role exists (2 pts)
    c_precheck = CheckResult("Precheck role exists", 2)
    precheck_roles = []
    if roles_dir.is_dir():
        precheck_roles = [d for d in roles_dir.iterdir()
                          if d.is_dir() and "precheck" in d.name]
        if precheck_roles:
            c_precheck.score = 2
            c_precheck.status = "PASS"
            c_precheck.details.append(f"Found: {', '.join(r.name for r in precheck_roles)}")
        else:
            c_precheck.details.append(
                "No precheck role found (every domain MUST have precheck_environment or similar)"
            )
    else:
        c_precheck.details.append("No roles directory")
    cat.checks.append(c_precheck)

    # Precheck calls validate_system_environment (1 pt)
    c_vsenv = CheckResult("Precheck calls validate_system_environment", 1)
    vsenv_found = False
    for pr in precheck_roles:
        tasks_dir = pr / "tasks"
        if tasks_dir.is_dir():
            for tf in list(tasks_dir.rglob("*.yml")) + list(tasks_dir.rglob("*.yaml")):
                if file_contains(tf, r"validate_system_environment"):
                    vsenv_found = True
                    break
        if vsenv_found:
            break
    # Also search in setup roles if no precheck roles found
    if not vsenv_found:
        for sr in setup_roles:
            tasks_dir = sr / "tasks"
            if tasks_dir.is_dir():
                for tf in list(tasks_dir.rglob("*.yml")) + list(tasks_dir.rglob("*.yaml")):
                    if file_contains(tf, r"validate_system_environment"):
                        vsenv_found = True
                        break
            if vsenv_found:
                break
    if vsenv_found:
        c_vsenv.score = 1
        c_vsenv.status = "PASS"
    else:
        c_vsenv.details.append(
            "No call to validate_system_environment module found in precheck/setup roles"
        )
    cat.checks.append(c_vsenv)

    # Precheck verifies upstream contracts (1 pt, N/A without upstream deps)
    c_upstream = CheckResult("Precheck verifies upstream contracts", 1)
    upstream = detect_upstream_domains(domain)
    if not upstream:
        c_upstream.max_points = 0
        c_upstream.status = "N/A"
        c_upstream.details.append(
            "No upstream output contract consumed (no other-domain output "
            "paths in roles/playbooks and no samples/<domain>_* contract samples)"
        )
    else:
        unverified = sorted(
            name for name in upstream
            if not precheck_verifies_domain(precheck_roles, name)
        )
        if not unverified:
            c_upstream.score = 1
            c_upstream.status = "PASS"
            c_upstream.details.append(
                f"Upstream domains verified by precheck: {', '.join(sorted(upstream))}"
            )
        else:
            c_upstream.details.append(
                "Upstream domains referenced but not verified by a precheck "
                f"stat/readiness check: {', '.join(unverified)}"
            )
    cat.checks.append(c_upstream)

    # samples/ directory (1 pt)
    c_samples = CheckResult("samples/ directory exists", 1)
    if (domain / "samples").is_dir():
        c_samples.score = 1
        c_samples.status = "PASS"
    else:
        c_samples.details.append("Missing samples/ directory (optional)")
    cat.checks.append(c_samples)

    # Environment vars usage (1 pt) — reads OMNIA_DATA_PATH, SYSTEM_* via lookup('env', ...)
    c_env = CheckResult("Uses omnia.env variables via lookup('env', ...)", 1)
    env_patterns = [r"lookup\(\s*['\"]env['\"]", r"OMNIA_DATA_PATH", r"SYSTEM_HOSTNAME",
                    r"SYSTEM_ADMIN_NIC_IPV4", r"SYSTEM_DOMAIN_NAME"]
    env_hits = 0
    for f in yml_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for pat in env_patterns:
                if re.search(pat, text):
                    env_hits += 1
                    break
        except (OSError, UnicodeDecodeError):
            pass
    if env_hits > 0:
        c_env.score = 1
        c_env.status = "PASS"
        c_env.details.append(f"{env_hits} files reference omnia.env variables")
    else:
        c_env.details.append("No files use lookup('env', ...) for system env vars")
    cat.checks.append(c_env)

    # omnia.sh compatibility (2 pts) — playbooks/ entry point + ansible-playbook invocable
    c_omnia = CheckResult("omnia.sh compatibility", 2)
    playbooks_dir = domain / "playbooks"
    has_entry = False
    if playbooks_dir.is_dir():
        for pattern in [f"{domain_name}.yml", f"{domain_name}.yaml", "main.yml"]:
            if (playbooks_dir / pattern).exists():
                has_entry = True
                break
    # Also check for ansible.cfg (needed for omnia.sh --run)
    has_cfg = (domain / "ansible.cfg").exists()
    if has_entry and has_cfg:
        c_omnia.score = 2
        c_omnia.status = "PASS"
    elif has_entry or has_cfg:
        c_omnia.score = 1
        c_omnia.status = "PARTIAL"
        if not has_entry:
            c_omnia.details.append("No playbooks/<domain>.yml entry point for omnia.sh --run")
        if not has_cfg:
            c_omnia.details.append("No ansible.cfg (needed for omnia.sh --run)")
    else:
        c_omnia.details.append("Missing playbooks/<domain>.yml and ansible.cfg for omnia.sh")
    cat.checks.append(c_omnia)

    return finalize_category(cat)


def check_fqcn_usage(domain: Path) -> CategoryResult:
    """Category 7: FQCN Usage (5 points)."""
    cat = CategoryResult(7, "FQCN Usage", 5, max_score=5)

    yml_files = list(domain.rglob("*.yml")) + list(domain.rglob("*.yaml"))
    task_files = [f for f in yml_files if "tasks" in str(f) or "playbooks" in str(f)]

    if not task_files:
        cat.score = 5
        cat.status = "PASS"
        cat.checks.append(CheckResult("No task files", 5, 5, "PASS"))
        return cat

    # Bare builtin modules (common ones that should use ansible.builtin.*)
    bare_builtins = [
        "file:", "copy:", "template:", "command:", "shell:", "debug:",
        "set_fact:", "include_tasks:", "include_role:", "stat:",
        "lineinfile:", "blockinfile:", "yum:", "dnf:", "apt:",
        "service:", "systemd:", "user:", "group:", "mount:",
        "get_url:", "uri:", "pip:", "package:", "wait_for:",
        "assert:", "fail:", "meta:", "pause:", "raw:",
        "slurp:", "fetch:", "synchronize:", "unarchive:",
    ]

    total_module_refs = 0
    bare_refs = 0
    bare_examples = []

    # Parameter names that look like bare modules (e.g. "file:" as a
    # parameter of include_vars/slurp/stat) — these are NOT module calls.
    param_false_positives = {"file:", "group:", "user:", "command:", "shell:", "meta:"}

    for f in task_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            lines_list = text.splitlines()
            for line_num, line in enumerate(lines_list, 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("-"):
                    continue
                for bare in bare_builtins:
                    if stripped.startswith(bare) and "ansible.builtin." not in stripped:
                        # Skip known parameter-name false positives: if
                        # the line is indented deeper than the surrounding
                        # "name:" or "ansible.builtin.*" line, it is a
                        # parameter, not a module invocation.
                        if bare in param_false_positives:
                            indent = len(line) - len(line.lstrip())
                            is_param = False
                            for back in range(line_num - 2, max(line_num - 8, -1), -1):
                                if 0 <= back < len(lines_list):
                                    prev = lines_list[back]
                                    prev_indent = len(prev) - len(prev.lstrip())
                                    if prev_indent < indent and (
                                        "ansible.builtin." in prev
                                        or "ansible.posix." in prev
                                        or "community." in prev
                                        or "containers." in prev
                                        or prev.strip().startswith("name:")
                                    ):
                                        is_param = True
                                        break
                            if is_param:
                                continue

                        bare_refs += 1
                        total_module_refs += 1
                        if len(bare_examples) < 5:
                            bare_examples.append(
                                f"{f.relative_to(domain)}:{line_num}: {stripped[:60]}"
                            )
                    elif f"ansible.builtin.{bare[:-1]}" in stripped:
                        total_module_refs += 1
        except (OSError, UnicodeDecodeError):
            pass

    if total_module_refs == 0:
        cat.score = 5
        cat.status = "PASS"
    else:
        fqcn_pct = ((total_module_refs - bare_refs) / total_module_refs) * 100
        if fqcn_pct >= 95:
            cat.score = 5
            cat.status = "PASS"
        elif fqcn_pct >= 80:
            cat.score = 3
            cat.status = "PARTIAL"
        else:
            cat.score = 0
            cat.status = "FAIL"

    c = CheckResult("FQCN module references", 5, cat.score, cat.status)
    if bare_refs > 0:
        c.details.append(f"{bare_refs} bare module references found (non-FQCN)")
        c.details.extend(bare_examples)
    else:
        c.details.append("All module references use FQCN")
    cat.checks.append(c)

    return cat


def check_ansible_cfg(domain: Path) -> CategoryResult:
    """Category 8: ansible.cfg Compliance (5 points)."""
    cat = CategoryResult(8, "ansible.cfg Compliance", 5, max_score=5)

    cfg = domain / "ansible.cfg"
    if not cfg.exists():
        cat.checks.append(CheckResult("ansible.cfg", 0, 0, "FAIL",
                                       ["No ansible.cfg found"]))
        return cat

    text = cfg.read_text(encoding="utf-8", errors="ignore")

    # No hardcoded absolute paths in ansible.cfg
    c_paths = CheckResult("No hardcoded /opt/omnia in ansible.cfg", 1)
    hardcoded_cfg = re.findall(r"/opt/omnia", text)
    if not hardcoded_cfg:
        c_paths.score = 1
        c_paths.status = "PASS"
    else:
        c_paths.details.append(f"Found {len(hardcoded_cfg)} hardcoded /opt/omnia references in ansible.cfg")
    cat.checks.append(c_paths)

    # No hardcoded /opt/omnia/ paths in runtime code (scan entire domain)
    # Excluded: docs/, samples/, DOCUMENTATION/EXAMPLES/RETURN docstrings,
    # comments, and default-value fallbacks like default('/opt/omnia').
    c_global = CheckResult("No hardcoded /opt/omnia in runtime code", 1)
    scan_exts = ("*.yml", "*.yaml", "*.py", "*.sh", "*.j2", "*.cfg")
    # Directories that contain reference/documentation content, not runtime code
    doc_dirs = {"docs", "samples", "README.md"}
    hardcoded_files = []
    waived = []
    for ext in scan_exts:
        for fpath in domain.rglob(ext):
            try:
                rel = fpath.relative_to(domain)
                # Skip documentation and sample directories
                rel_parts = rel.parts
                if rel_parts and rel_parts[0] in doc_dirs:
                    continue

                content = fpath.read_text(encoding="utf-8", errors="ignore")

                # For Python files, scan only executable code: drop comments,
                # docstrings, and the Galaxy DOCUMENTATION/EXAMPLES/RETURN
                # blocks (these contain example paths, not runtime code).
                if fpath.suffix == ".py":
                    content = python_runtime_text(content)

                # Skip comment-only references in YAML, shell, Jinja2, and
                # configuration files. They document defaults but do not create
                # runtime coupling to the default path.
                if fpath.suffix in (".yml", ".yaml", ".sh", ".j2", ".cfg"):
                    content = "\n".join(
                        line for line in content.splitlines()
                        if not line.strip().startswith(("#", ";", "{#"))
                    )

                # Lines carrying an explicit, justified waiver (for example a
                # container-internal mount target fixed by the image layout)
                # are excluded and reported so reviewers can audit them.
                kept_lines = []
                for line in content.splitlines():
                    waiver = OPT_OMNIA_WAIVER_RE.search(line)
                    if waiver and "/opt/omnia" in line:
                        waived.append(f"{rel}: {waiver.group(1).strip()}")
                    else:
                        kept_lines.append(line)
                content = "\n".join(kept_lines)

                # Count remaining runtime references. Compatibility defaults
                # are acceptable only when an OMNIA_* env variable stays overridable.
                matches = re.findall(r"/opt/omnia", content)
                fallback_matches = OPT_OMNIA_FALLBACK_RE.findall(content)
                net_matches = len(matches) - len(fallback_matches)
                if net_matches > 0:
                    hardcoded_files.append(
                        f"{rel} ({net_matches} runtime occurrence(s), "
                        f"{len(fallback_matches)} acceptable fallback(s))"
                    )
            except (OSError, UnicodeDecodeError):
                pass
    if not hardcoded_files:
        c_global.score = 1
        c_global.status = "PASS"
        for entry in waived:
            c_global.details.append(f"Waived: {entry}")
    else:
        c_global.details.append(
            f"Found /opt/omnia hardcoding in {len(hardcoded_files)} runtime files "
            "(must use OMNIA_DATA_PATH env var):"
        )
        for hf in hardcoded_files[:10]:  # limit output
            c_global.details.append(f"  - {hf}")
        if len(hardcoded_files) > 10:
            c_global.details.append(f"  ... and {len(hardcoded_files) - 10} more")
    cat.checks.append(c_global)

    # Uses collections_path
    c_coll = CheckResult("Uses collections_path", 1)
    if "collections_path" in text or "collections_paths" in text:
        c_coll.score = 1
        c_coll.status = "PASS"
    else:
        c_coll.details.append("No collections_path setting")
    cat.checks.append(c_coll)

    # Points to plugins/ not library/
    c_plugins = CheckResult("Points to plugins/ not library/", 2)
    if "library" in text and "plugins" not in text:
        c_plugins.details.append("ansible.cfg references library/ but not plugins/")
    else:
        c_plugins.score = 2
        c_plugins.status = "PASS"
    cat.checks.append(c_plugins)

    cat.score = sum(ch.score for ch in cat.checks)
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


def check_documentation(domain: Path) -> CategoryResult:
    """Category 9: Documentation (5 points)."""
    cat = CategoryResult(9, "Documentation", 5, max_score=5)

    # README.md (2 pts)
    c_readme = CheckResult("Domain-level README.md", 2)
    if (domain / "README.md").exists():
        c_readme.score = 2
        c_readme.status = "PASS"
    else:
        c_readme.details.append("Missing domain README.md")
    cat.checks.append(c_readme)

    # docs/ directory (1 pt)
    c_docs = CheckResult("docs/ directory with content", 1)
    docs_dir = domain / "docs"
    if docs_dir.is_dir() and any(docs_dir.iterdir()):
        c_docs.score = 1
        c_docs.status = "PASS"
    else:
        c_docs.details.append("Missing or empty docs/ directory")
    cat.checks.append(c_docs)

    # docs/architecture.md or design/ (1 pt)
    c_arch = CheckResult("Architecture or design docs", 1)
    has_arch = False
    if docs_dir.is_dir():
        arch_patterns = ["architecture.md", "design.md", "ARCHITECTURE.md"]
        for pattern in arch_patterns:
            if (docs_dir / pattern).exists():
                has_arch = True
                break
        if not has_arch and (docs_dir / "design").is_dir():
            has_arch = True
    if has_arch:
        c_arch.score = 1
        c_arch.status = "PASS"
    else:
        c_arch.details.append("Missing architecture/design documentation")
    cat.checks.append(c_arch)

    # docs/contracts/ quality (1 pt)
    c_contracts_doc = CheckResult("Contract docs quality", 1)
    contracts_dir = docs_dir / "contracts" if docs_dir.is_dir() else None
    if contracts_dir and contracts_dir.is_dir():
        contract_files = list(contracts_dir.glob("*.md"))
        if contract_files:
            c_contracts_doc.score = 1
            c_contracts_doc.status = "PASS"
            c_contracts_doc.details.append(f"{len(contract_files)} contract docs found")
        else:
            c_contracts_doc.details.append("contracts/ exists but no .md files")
    else:
        c_contracts_doc.details.append("Missing docs/contracts/ directory")
    cat.checks.append(c_contracts_doc)

    cat.score = sum(ch.score for ch in cat.checks)
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


def check_domain_independence(domain: Path) -> CategoryResult:
    """Category 10: Domain Independence (5 points)."""
    cat = CategoryResult(10, "Domain Independence", 5, max_score=5)

    # Check for cross-domain imports
    py_files = list(domain.rglob("*.py"))
    cross_imports = []
    common_imports = []

    for f in py_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # Check for common/ imports
                if "from ansible.module_utils.input_validation.common_utils" in stripped:
                    common_imports.append(f"{f.relative_to(domain)}: {stripped[:80]}")
                # Check for other domain imports (heuristic)
                if re.search(r"from\s+ansible\.module_utils\.\w+\.\w+", stripped):
                    # This is fine if it's within this domain
                    pass
        except (OSError, UnicodeDecodeError):
            pass

    c_no_common = CheckResult("No imports from common/library/", 3)
    if not common_imports:
        c_no_common.score = 3
        c_no_common.status = "PASS"
    else:
        c_no_common.details.append(f"{len(common_imports)} imports from common/")
        for imp in common_imports[:3]:
            c_no_common.details.append(f"  {imp}")
    cat.checks.append(c_no_common)

    # Detect executable cross-domain source coupling. Prose in messages and
    # operator guidance may name a source path without importing its code, so
    # only Ansible import/include directives and active roles_path entries count.
    c_yaml = CheckResult("No executable cross-domain source coupling", 2)
    coupling_files = (
        list(domain.rglob("*.yml"))
        + list(domain.rglob("*.yaml"))
        + list(domain.rglob("*.cfg"))
    )
    direct_refs = []
    src_parent = domain.parent
    for f in coupling_files:
        try:
            rel = f.relative_to(domain)
            if rel.parts and rel.parts[0] in ("docs", "samples"):
                continue
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith(("#", ";")):
                    continue
                for sibling in src_parent.iterdir():
                    if not sibling.is_dir() or sibling == domain or sibling.name == "common":
                        continue
                    source_ref = f"src/{sibling.name}/"
                    executable_directive = re.search(
                        r"(?:import_playbook|include_tasks|import_tasks|roles_path)\s*[=:]",
                        stripped,
                    )
                    relative_role_path = (
                        "roles_path" in stripped
                        and re.search(
                            rf"(?:^|[/.:]){re.escape(sibling.name)}/roles(?:$|[:/])",
                            stripped,
                        )
                    )
                    if executable_directive and (source_ref in stripped or relative_role_path):
                        direct_refs.append(f"{rel}: {stripped[:120]}")
                        break
        except (OSError, UnicodeDecodeError):
            pass

    if not direct_refs:
        c_yaml.score = 2
        c_yaml.status = "PASS"
    else:
        c_yaml.details.append(
            f"{len(direct_refs)} direct references to other domain source dirs"
        )
        for ref in direct_refs[:5]:
            c_yaml.details.append(f"  - {ref}")
    cat.checks.append(c_yaml)

    cat.score = sum(ch.score for ch in cat.checks)
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


def check_code_quality(domain: Path) -> CategoryResult:
    """Category 11: Code Quality & Security (10 points).

    Checks for tool availability and runs static analysis tools.
    If a tool is not available, the check is N/A and removed from scoring.
    """
    cat = CategoryResult(11, "Code Quality & Security", 10, max_score=10)

    # pylint (3 points)
    c_pylint = CheckResult("Python files pylint score >= 8.0", 3)
    repo = repository_root(domain)
    py_files = tracked_files(domain, repo, "*.py")
    # Empty package markers and header-only modules do not produce a
    # meaningful pylint score.
    py_files = [
        f for f in py_files
        if "__pycache__" not in str(f) and f.name != "__init__.py"
        and has_python_statements(f)
    ]
    # Score with the repository's own pylint configuration, as CI does.
    pylint_args = ["pylint", "--score=y", "--exit-zero"]
    for rc_name in (".pylintrc", "pylintrc"):
        if (repo / rc_name).is_file():
            pylint_args.append(f"--rcfile={repo / rc_name}")
            break
    failing_files = []
    if not py_files:
        c_pylint.max_points = 0
        c_pylint.status = "N/A"
        c_pylint.details.append("No .py files to check")
    else:
        try:
            passing = 0
            total = len(py_files)
            for pf in py_files:
                result = subprocess.run(
                    [*pylint_args, str(pf)],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, cwd=repo
                )
                # Parse score from output like "Your code has been rated at 8.50/10"
                score_match = re.search(r'rated at (-?[\d.]+)/10', result.stdout)
                if score_match and float(score_match.group(1)) >= 8.0:
                    passing += 1
                else:
                    rating = score_match.group(1) if score_match else "n/a"
                    failing_files.append(f"{pf.relative_to(domain)} ({rating})")
            # Full marks only when every file passes; rounding must not hide a failure.
            c_pylint.score = 3 if passing == total else min(2, round((passing / total) * 3))
            c_pylint.status = "PASS" if c_pylint.score == 3 else ("PARTIAL" if c_pylint.score > 0 else "FAIL")
            c_pylint.details.append(f"{passing}/{total} files pass pylint >= 8.0")
            for entry in failing_files[:10]:
                c_pylint.details.append(f"  - {entry}")
            if len(failing_files) > 10:
                c_pylint.details.append(f"  ... and {len(failing_files) - 10} more")
        except (FileNotFoundError, ImportError):
            c_pylint.max_points = 0
            c_pylint.status = "N/A"
            c_pylint.details.append("pylint not available")
    cat.checks.append(c_pylint)

    # ansible-lint (2 points)
    c_alint = CheckResult("Ansible-lint clean", 2)
    try:
        repo = repository_root(domain)
        lint_config = repo / ".config/ansible-lint.yml"
        lint_args = ["ansible-lint"]
        if lint_config.is_file():
            lint_args.extend(("--config", str(lint_config)))
        else:
            lint_args.extend(("--profile", "production"))
        lint_args.append(str(domain))
        lint_env = os.environ.copy()
        domain_config = domain / "ansible.cfg"
        if domain_config.is_file():
            lint_env["ANSIBLE_CONFIG"] = str(domain_config)
        result = subprocess.run(
            lint_args,
            cwd=repo,
            env=lint_env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            c_alint.score = 2
            c_alint.status = "PASS"
        else:
            output = (result.stdout + result.stderr).strip().splitlines()
            c_alint.details.append("ansible-lint failed")
            c_alint.details.extend(output[-10:])
    except (FileNotFoundError, ImportError):
        c_alint.max_points = 0
        c_alint.status = "N/A"
        c_alint.details.append("ansible-lint not available")
    cat.checks.append(c_alint)

    # gitleaks (2 points)
    c_leak = CheckResult("No hardcoded secrets (gitleaks)", 2)
    try:
        result = subprocess.run(
            ["gitleaks", "detect", "--source", str(domain), "--no-git"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
        )
        if result.returncode == 0:
            c_leak.score = 2
            c_leak.status = "PASS"
        else:
            c_leak.details.append("gitleaks found potential secrets")
    except (FileNotFoundError, ImportError):
        c_leak.max_points = 0
        c_leak.status = "N/A"
        c_leak.details.append("gitleaks not available")
    cat.checks.append(c_leak)

    # shellcheck (2 points)
    c_shell = CheckResult("Shell scripts pass shellcheck", 2)
    sh_files = find_files(domain, "*.sh")
    if not sh_files:
        c_shell.max_points = 0
        c_shell.status = "N/A"
        c_shell.details.append("No .sh files to check")
    else:
        try:
            passing = 0
            total = len(sh_files)
            for sf in sh_files:
                result = subprocess.run(
                    ["shellcheck", str(sf)],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
                )
                if result.returncode == 0:
                    passing += 1
            c_shell.score = round((passing / total) * 2)
            c_shell.status = "PASS" if c_shell.score == 2 else ("PARTIAL" if c_shell.score > 0 else "FAIL")
            c_shell.details.append(f"{passing}/{total} .sh files pass shellcheck")
        except (FileNotFoundError, ImportError):
            c_shell.max_points = 0
            c_shell.status = "N/A"
            c_shell.details.append("shellcheck not available")
    cat.checks.append(c_shell)

    # Checkmarx (1 point)
    c_cx = CheckResult("Checkmarx clean", 1)
    c_cx.max_points = 0
    c_cx.status = "N/A"
    c_cx.details.append("Checkmarx scan results not available in local environment")
    cat.checks.append(c_cx)

    return finalize_category(cat)


def check_code_style(domain: Path) -> CategoryResult:
    """Category 12: Code Style Compliance (bonus, 0-weight informational).

    Checks adherence to docs/code-style/ conventions. This is an advisory
    category — it does NOT affect the 100-point score but surfaces issues
    that code review would catch.
    """
    cat = CategoryResult(12, "Code Style Compliance (advisory)", 0, max_score=0)

    # --- Ansible: changed_when on command/shell tasks ---
    c_changed = CheckResult("changed_when on command/shell tasks", 0, 0, "INFO")
    task_files = []
    for d in ["roles", "playbooks"]:
        dd = domain / d
        if dd.is_dir():
            task_files.extend(dd.rglob("*.yml"))
            task_files.extend(dd.rglob("*.yaml"))

    cmd_tasks = 0
    cmd_with_changed = 0
    for f in task_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(
                r"ansible\.builtin\.(command|shell):", text
            ):
                cmd_tasks += 1
                # creates/removes make command tasks idempotent (ansible-lint
                # no-changed-when accepts them as change reporting).
                block = task_block(text, match.start())
                if re.search(r"^\s*(changed_when|creates|removes):", block, re.MULTILINE):
                    cmd_with_changed += 1
        except (OSError, UnicodeDecodeError):
            pass
    if cmd_tasks > 0:
        c_changed.details.append(
            f"{cmd_with_changed}/{cmd_tasks} command/shell tasks have changed_when"
        )
        c_changed.status = "PASS" if cmd_with_changed >= cmd_tasks else "PARTIAL"
    else:
        c_changed.details.append("No command/shell tasks found")
        c_changed.status = "PASS"
    cat.checks.append(c_changed)

    # --- Ansible: no_log on credential tasks ---
    c_nolog = CheckResult("no_log: true on credential tasks", 0, 0, "INFO")
    # References to secret *locations* (key/password files, stat results)
    # are not secret values and do not need no_log.
    not_a_value = r"(?!\w*_(?:file|path|stat|dir|exists)\b)"
    credential_patterns = [
        rf"vault_\w*password{not_a_value}", rf"vault_\w*secret{not_a_value}",
        rf"vault_\w*key{not_a_value}", rf"vault_\w*token{not_a_value}",
        r"registry_password", r"registry_user",
    ]
    cred_tasks = 0
    cred_with_nolog = 0
    # no_log is a task keyword: skip variable, metadata, and payload files.
    non_task_dirs = {"vars", "defaults", "meta", "files", "templates"}
    for f in task_files:
        if non_task_dirs.intersection(f.relative_to(domain).parts):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for pat in credential_patterns:
                for match in re.finditer(pat, text, re.IGNORECASE):
                    cred_tasks += 1
                    block = task_block(text, match.start())
                    if re.search(r"^\s*no_log:\s*(true|True)\b", block, re.MULTILINE):
                        cred_with_nolog += 1
        except (OSError, UnicodeDecodeError):
            pass
    if cred_tasks > 0:
        c_nolog.details.append(
            f"{cred_with_nolog}/{cred_tasks} credential references have no_log: true nearby"
        )
        c_nolog.status = "PASS" if cred_with_nolog >= cred_tasks else "PARTIAL"
    else:
        c_nolog.details.append("No credential variable references found in tasks")
        c_nolog.status = "PASS"
    cat.checks.append(c_nolog)

    # --- Ansible: boolean values (true/false not yes/no) ---
    c_bool = CheckResult("Boolean true/false (not yes/no)", 0, 0, "INFO")
    yesno_count = 0
    for f in task_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if re.search(r":\s+(yes|no)\s*$", stripped, re.IGNORECASE):
                    yesno_count += 1
        except (OSError, UnicodeDecodeError):
            pass
    if yesno_count == 0:
        c_bool.status = "PASS"
        c_bool.details.append("All booleans use true/false")
    else:
        c_bool.status = "PARTIAL"
        c_bool.details.append(f"{yesno_count} lines use yes/no instead of true/false")
    cat.checks.append(c_bool)

    # --- Python: copyright header ---
    c_copyright = CheckResult("Copyright header in .py files", 0, 0, "INFO")
    py_files = [f for f in find_files(domain, "*.py")
                if "__pycache__" not in str(f) and f.name != "__init__.py"]
    if py_files:
        has_header = sum(
            1 for f in py_files
            if file_contains(f, r"Copyright.*Dell")
        )
        c_copyright.details.append(f"{has_header}/{len(py_files)} .py files have copyright header")
        c_copyright.status = "PASS" if has_header == len(py_files) else "PARTIAL"
    else:
        c_copyright.details.append("No .py files to check")
        c_copyright.status = "PASS"
    cat.checks.append(c_copyright)

    # --- Python: type annotations on public functions ---
    c_types = CheckResult("Type annotations on public functions", 0, 0, "INFO")
    annotated = 0
    unannotated = 0
    unannotated_funcs = []
    for f in py_files:
        # Parse signatures so multi-line definitions are judged correctly.
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not node.name.startswith("_")):
                if node.returns is not None:
                    annotated += 1
                else:
                    unannotated += 1
                    unannotated_funcs.append(f"{f.relative_to(domain)}:{node.name}")
    total_funcs = annotated + unannotated
    if total_funcs > 0:
        c_types.details.append(
            f"{annotated}/{total_funcs} public functions have return type annotations"
        )
        for entry in unannotated_funcs[:10]:
            c_types.details.append(f"  - {entry}")
        if len(unannotated_funcs) > 10:
            c_types.details.append(f"  ... and {len(unannotated_funcs) - 10} more")
        c_types.status = "PASS" if unannotated == 0 else "PARTIAL"
    else:
        c_types.details.append("No public functions found")
        c_types.status = "PASS"
    cat.checks.append(c_types)

    # --- Jinja2: .j2 extension ---
    c_j2 = CheckResult("Templates use .j2 extension", 0, 0, "INFO")
    templates_dir = domain / "roles"
    j2_files = list(templates_dir.rglob("*.j2")) if templates_dir.is_dir() else []
    non_j2_templates = []
    if templates_dir.is_dir():
        for td in templates_dir.rglob("templates"):
            if td.is_dir():
                for tf in td.iterdir():
                    if tf.is_file() and not tf.name.endswith(".j2"):
                        non_j2_templates.append(str(tf.relative_to(domain)))
    if non_j2_templates:
        c_j2.status = "PARTIAL"
        c_j2.details.append(
            f"{len(non_j2_templates)} template files without .j2 extension"
        )
    else:
        c_j2.status = "PASS"
        c_j2.details.append(f"All {len(j2_files)} templates use .j2 extension")
    cat.checks.append(c_j2)

    # --- Shell: set -euo pipefail ---
    c_strict = CheckResult("Shell scripts use strict mode", 0, 0, "INFO")
    sh_files = find_files(domain, "*.sh")
    if sh_files:
        strict = sum(
            1 for f in sh_files
            if file_contains(f, r"set -euo pipefail")
        )
        c_strict.details.append(f"{strict}/{len(sh_files)} .sh files use set -euo pipefail")
        c_strict.status = "PASS" if strict == len(sh_files) else "PARTIAL"
    else:
        c_strict.details.append("No .sh files to check")
        c_strict.status = "PASS"
    cat.checks.append(c_strict)

    cat.score = 0  # advisory only
    # Overall status based on checks
    statuses = [ch.status for ch in cat.checks]
    if all(s == "PASS" for s in statuses):
        cat.status = "PASS"
    elif any(s == "FAIL" for s in statuses):
        cat.status = "FAIL"
    else:
        cat.status = "PARTIAL"
    return cat


# Report Generation -------------------------------------------------------

def generate_report(domain_name: str, categories: list, profile: str) -> str:
    """Generate a Markdown compliance report."""
    total_score, applicable_score, applicable_max = report_totals(categories)

    if total_score <= 30:
        status = "NOT_STARTED"
    elif total_score <= 95:
        status = "IN_PROGRESS"
    else:
        status = "COMPLIANT"

    lines = [
        f"# Domain Completion Report: {domain_name}",
        "",
        f"**Date**: {date.today().isoformat()}",
        f"**Profile**: {profile}",
        f"**Score**: {total_score}/100",
        f"**Applicable points**: {applicable_score}/{applicable_max}",
        f"**Status**: {status}",
        "",
        "## Score Breakdown",
        "",
        "| # | Category | Weight | Score | Max | Status |",
        "|---|----------|--------|-------|-----|--------|",
    ]

    for c in categories:
        category_score = "N/A" if c.status == "N/A" else str(c.score)
        lines.append(
            f"| {c.category_id} | {c.name} | {c.weight} | {category_score} | {c.max_score} | {c.status} |"
        )
    lines.append(
        f"| | **Normalized total** | | **{total_score}/100** | **{applicable_max} applicable** | |"
    )
    lines.append("")

    # Detailed findings
    lines.append("## Detailed Findings")
    lines.append("")
    for c in categories:
        category_score = "N/A" if c.status == "N/A" else f"{c.score}/{c.max_score}"
        lines.append(f"### {c.category_id}. {c.name} ({category_score})")
        lines.append("")
        for ch in c.checks:
            points = "N/A" if ch.status == "N/A" else f"{ch.score}/{ch.max_points}"
            lines.append(f"- **{ch.name}**: {ch.status} ({points})")
            for d in ch.details:
                lines.append(f"  - {d}")
        lines.append("")

    # Priority action items
    action_items = []
    for c in categories:
        if c.status not in {"PASS", "N/A"}:
            for ch in c.checks:
                if ch.status not in {"PASS", "N/A"}:
                    for d in ch.details:
                        if d and not d.startswith("Found:") and not d.startswith("Tags found:"):
                            action_items.append(f"[{c.name}] {d}")

    if action_items:
        lines.append("## Priority Action Items")
        lines.append("")
        for i, item in enumerate(action_items, 1):
            lines.append(f"{i}. {item}")
        lines.append("")

    return "\n".join(lines)


def generate_json_report(domain_name: str, categories: list, profile: str) -> dict:
    """Generate a JSON compliance report."""
    total_score, applicable_score, applicable_max = report_totals(categories)

    if total_score <= 30:
        status = "NOT_STARTED"
    elif total_score <= 95:
        status = "IN_PROGRESS"
    else:
        status = "COMPLIANT"

    return {
        "domain": domain_name,
        "date": date.today().isoformat(),
        "profile": profile,
        "score": total_score,
        "max_score": 100,
        "applicable_score": applicable_score,
        "applicable_max_score": applicable_max,
        "status": status,
        "categories": [
            {
                "id": c.category_id,
                "name": c.name,
                "weight": c.weight,
                "score": c.score,
                "max_score": c.max_score,
                "status": c.status,
                "checks": [
                    {
                        "name": ch.name,
                        "score": ch.score,
                        "max_points": ch.max_points,
                        "status": ch.status,
                        "details": ch.details,
                    }
                    for ch in c.checks
                ],
            }
            for c in categories
        ],
    }


def run(domain_path: str, output_json: bool = False) -> str:
    """Main entry point: scan domain and produce report."""
    domain = Path(domain_path).resolve()
    if not domain.is_dir():
        return f"ERROR: {domain} is not a directory"

    domain_name = domain.name

    categories = [
        check_galaxy_structure(domain),
        check_module_documentation(domain),
        check_role_metadata(domain),
        check_input_validation(domain),
        check_entry_point(domain),
        check_domain_integration(domain),
        check_fqcn_usage(domain),
        check_ansible_cfg(domain),
        check_documentation(domain),
        check_domain_independence(domain),
        check_code_quality(domain),
        check_code_style(domain),
    ]
    profile = apply_domain_profile(domain, categories)

    if output_json:
        return json.dumps(generate_json_report(domain_name, categories, profile), indent=2)
    return generate_report(domain_name, categories, profile)


def main():
    parser = argparse.ArgumentParser(
        description="Omnia Domain Completion Checker - Galaxy compliance scoring tool"
    )
    parser.add_argument("domain_path", help="Path to the domain directory (e.g., src/repo_manager)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    parser.add_argument("--output", type=Path, help="Write the report to this file")
    args = parser.parse_args()

    result = run(args.domain_path, output_json=args.json)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.rstrip() + "\n", encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__":
    main()
