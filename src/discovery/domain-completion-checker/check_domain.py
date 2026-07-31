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
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
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


# Category Checkers -------------------------------------------------------

def check_galaxy_structure(domain: Path) -> CategoryResult:
    """Category 1: Galaxy Structure (20 points)."""
    cat = CategoryResult(1, "Galaxy Structure", 20, max_score=20)

    # galaxy.yml
    galaxy_yml = domain / "galaxy.yml"
    c = CheckResult("galaxy.yml exists", 5)
    if galaxy_yml.exists():
        c.score = 5
        c.status = "PASS"
    else:
        c.details.append("Missing galaxy.yml")
    cat.checks.append(c)

    # meta/runtime.yml
    runtime_yml = domain / "meta" / "runtime.yml"
    c = CheckResult("meta/runtime.yml exists", 2)
    if runtime_yml.exists():
        c.score = 2
        c.status = "PASS"
    else:
        c.details.append("Missing meta/runtime.yml")
    cat.checks.append(c)

    # plugins/modules/
    c = CheckResult("plugins/modules/ directory", 4)
    plugins_modules = domain / "plugins" / "modules"
    library_modules = domain / "library" / "modules"
    if plugins_modules.is_dir():
        c.score = 4
        c.status = "PASS"
    elif library_modules.is_dir():
        c.score = 1
        c.status = "PARTIAL"
        c.details.append("Uses legacy library/modules/ - migrate to plugins/modules/")
    else:
        c.details.append("No modules directory found")
    cat.checks.append(c)

    # plugins/module_utils/
    c = CheckResult("plugins/module_utils/ directory", 4)
    plugins_mu = domain / "plugins" / "module_utils"
    library_mu = domain / "library" / "module_utils"
    if plugins_mu.is_dir():
        c.score = 4
        c.status = "PASS"
    elif library_mu.is_dir():
        c.score = 1
        c.status = "PARTIAL"
        c.details.append("Uses legacy library/module_utils/ - migrate to plugins/module_utils/")
    else:
        c.score = 4
        c.status = "PASS"
        c.details.append("No module_utils needed (acceptable for small domains)")
    cat.checks.append(c)

    # plugins/callback/ (optional, 2 pts if present or not needed)
    c = CheckResult("plugins/callback/ or not needed", 2)
    plugins_cb = domain / "plugins" / "callback"
    legacy_cb = domain / "callback_plugins"
    if plugins_cb.is_dir():
        c.score = 2
        c.status = "PASS"
    elif legacy_cb.is_dir():
        c.score = 0
        c.status = "FAIL"
        c.details.append("Uses legacy callback_plugins/ - migrate to plugins/callback/")
    else:
        c.score = 2
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
    """Category 2: Module Documentation (15 points)."""
    cat = CategoryResult(2, "Module Documentation", 15, max_score=15)

    # Find modules in plugins/modules/ or library/modules/
    modules_dir = domain / "plugins" / "modules"
    if not modules_dir.is_dir():
        modules_dir = domain / "library" / "modules"

    if not modules_dir.is_dir():
        cat.score = 15
        cat.status = "PASS"
        cat.checks.append(CheckResult("No modules directory", 15, 15, "PASS",
                                       ["No modules to check - full marks"]))
        return cat

    py_files = [f for f in modules_dir.glob("*.py") if f.name != "__init__.py"]
    if not py_files:
        cat.score = 15
        cat.status = "PASS"
        cat.checks.append(CheckResult("No module files", 15, 15, "PASS",
                                       ["No modules to check - full marks"]))
        return cat

    total = len(py_files)
    has_doc = count_pattern_in_files(py_files, r"^DOCUMENTATION\s*=")
    has_ex = count_pattern_in_files(py_files, r"^EXAMPLES\s*=")
    has_ret = count_pattern_in_files(py_files, r"^RETURN\s*=")

    c_doc = CheckResult("DOCUMENTATION block", 5)
    c_doc.score = int((has_doc / total) * 5) if total else 5
    c_doc.status = "PASS" if has_doc == total else ("PARTIAL" if has_doc > 0 else "FAIL")
    c_doc.details.append(f"{has_doc}/{total} modules have DOCUMENTATION")
    cat.checks.append(c_doc)

    c_ex = CheckResult("EXAMPLES block", 5)
    c_ex.score = int((has_ex / total) * 5) if total else 5
    c_ex.status = "PASS" if has_ex == total else ("PARTIAL" if has_ex > 0 else "FAIL")
    c_ex.details.append(f"{has_ex}/{total} modules have EXAMPLES")
    cat.checks.append(c_ex)

    c_ret = CheckResult("RETURN block", 5)
    c_ret.score = int((has_ret / total) * 5) if total else 5
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
    """Category 4: Input Validation Structure (15 points)."""
    cat = CategoryResult(4, "Input Validation Structure", 15, max_score=15)

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
            cat.score = 15
            cat.status = "PASS"
            cat.checks.append(CheckResult("No input validation needed", 15, 15, "PASS",
                                           ["Domain has no input/ directory - no config to validate"]))
            return cat
        else:
            cat.checks.append(CheckResult("input_validation directory", 0, 0, "FAIL",
                                           ["Has input/ but no validation module found"]))
            return cat

    # Check four-directory structure
    c_core = CheckResult("core/ directory with validation_engine.py", 4)
    core_dir = iv_dir / "core"
    if core_dir.is_dir():
        engine = core_dir / "validation_engine.py"
        if engine.exists():
            c_core.score = 4
            c_core.status = "PASS"
        else:
            c_core.score = 2
            c_core.status = "PARTIAL"
            c_core.details.append("core/ exists but missing validation_engine.py")
    else:
        c_core.details.append("Missing core/ directory")
    cat.checks.append(c_core)

    c_msg = CheckResult("messages/ directory with constants", 4)
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
                c_msg.score = 4
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

    c_schema = CheckResult("schema/ directory with .json files", 3)
    schema_dir = iv_dir / "schema"
    if schema_dir.is_dir():
        json_files = list(schema_dir.glob("*.json"))
        if json_files:
            c_schema.score = 3
            c_schema.status = "PASS"
            c_schema.details.append(f"{len(json_files)} schema files found")
        else:
            c_schema.score = 1
            c_schema.status = "PARTIAL"
            c_schema.details.append("schema/ exists but no .json files")
    else:
        c_schema.details.append("Missing schema/ directory")
    cat.checks.append(c_schema)

    c_val = CheckResult("validators/ directory with validate()", 4)
    val_dir = iv_dir / "validators"
    if val_dir.is_dir():
        py_files = [f for f in val_dir.glob("*.py") if f.name != "__init__.py"]
        if py_files:
            has_validate = any(file_contains(f, r'def validate\(') for f in py_files)
            if has_validate:
                c_val.score = 4
                c_val.status = "PASS"
            else:
                c_val.score = 2
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
        deduction = min(3, inline_count)
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
    standard_tags = {"precheck", "validate", "prepare", "execute", "build", "cleanup", "setup"}
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
    """Category 6: Domain Integration (10 points)."""
    cat = CategoryResult(6, "Domain Integration", 10, max_score=10)
    domain_name = domain.name

    # copy-input.sh
    c_copy = CheckResult("copy-input.sh exists", 3)
    if (domain / "copy-input.sh").exists():
        c_copy.score = 3
        c_copy.status = "PASS"
    else:
        c_copy.details.append("Missing copy-input.sh")
    cat.checks.append(c_copy)

    # Status file writer
    c_status = CheckResult("Status file writer", 3)
    yml_files = list(domain.rglob("*.yml")) + list(domain.rglob("*.yaml"))
    status_found = any(
        file_contains(f, r"_status\.yml|status_file|write.*status")
        for f in yml_files
    )
    if status_found:
        c_status.score = 3
        c_status.status = "PASS"
    else:
        c_status.details.append("No status file writer found in tasks")
    cat.checks.append(c_status)

    # Setup role
    c_setup = CheckResult("Setup role exists", 2)
    roles_dir = domain / "roles"
    if roles_dir.is_dir():
        setup_roles = [d for d in roles_dir.iterdir()
                       if d.is_dir() and ("setup" in d.name or "validation" in d.name)]
        if setup_roles:
            c_setup.score = 2
            c_setup.status = "PASS"
            c_setup.details.append(f"Found: {', '.join(r.name for r in setup_roles)}")
        else:
            c_setup.details.append("No setup/validation role found")
    else:
        c_setup.details.append("No roles directory")
    cat.checks.append(c_setup)

    # Contract docs
    c_contract = CheckResult("Input/output contract docs", 2)
    docs_dir = domain / "docs"
    contracts_dir = domain / "docs" / "contracts"
    has_contracts = False
    if contracts_dir.is_dir():
        has_contracts = True
    elif docs_dir.is_dir():
        contract_files = find_files(docs_dir, "*contract*")
        has_contracts = len(contract_files) > 0
    # Also check for CONTRACTS.md at root
    if (domain / "CONTRACTS.md").exists() or (domain / "INPUT_CONTRACT.md").exists():
        has_contracts = True

    if has_contracts:
        c_contract.score = 2
        c_contract.status = "PASS"
    else:
        c_contract.details.append("No contract documentation found")
    cat.checks.append(c_contract)

    cat.score = sum(ch.score for ch in cat.checks)
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


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

    for f in task_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for line_num, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("-"):
                    continue
                for bare in bare_builtins:
                    if stripped.startswith(bare) and "ansible.builtin." not in stripped:
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

    # No hardcoded absolute paths
    c_paths = CheckResult("No hardcoded absolute paths", 2)
    hardcoded = re.findall(r"/opt/omnia", text)
    if not hardcoded:
        c_paths.score = 2
        c_paths.status = "PASS"
    else:
        c_paths.details.append(f"Found {len(hardcoded)} hardcoded /opt/omnia references")
    cat.checks.append(c_paths)

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

    # README.md
    c_readme = CheckResult("Domain-level README.md", 3)
    if (domain / "README.md").exists():
        c_readme.score = 3
        c_readme.status = "PASS"
    else:
        c_readme.details.append("Missing domain README.md")
    cat.checks.append(c_readme)

    # docs/ directory
    c_docs = CheckResult("docs/ directory with content", 2)
    docs_dir = domain / "docs"
    if docs_dir.is_dir() and any(docs_dir.iterdir()):
        c_docs.score = 2
        c_docs.status = "PASS"
    else:
        c_docs.details.append("Missing or empty docs/ directory")
    cat.checks.append(c_docs)

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

    # Communicates via YAML contracts only
    c_yaml = CheckResult("Communicates via YAML contracts", 2)
    yml_files = list(domain.rglob("*.yml")) + list(domain.rglob("*.yaml"))
    direct_refs = 0
    for f in yml_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            # Check for direct references to other domains' source directories
            src_parent = domain.parent
            for sibling in src_parent.iterdir():
                if sibling.is_dir() and sibling != domain and sibling.name != "common":
                    if sibling.name in text and f"src/{sibling.name}" in text:
                        direct_refs += 1
        except (OSError, UnicodeDecodeError):
            pass

    if direct_refs == 0:
        c_yaml.score = 2
        c_yaml.status = "PASS"
    else:
        c_yaml.details.append(f"{direct_refs} direct references to other domain source dirs")
    cat.checks.append(c_yaml)

    cat.score = sum(ch.score for ch in cat.checks)
    cat.status = "PASS" if cat.score == cat.max_score else ("PARTIAL" if cat.score > 0 else "FAIL")
    return cat


# Report Generation -------------------------------------------------------

def generate_report(domain_name: str, categories: list) -> str:
    """Generate a Markdown compliance report."""
    total_score = sum(c.score for c in categories)
    max_score = sum(c.max_score for c in categories)

    if total_score <= 30:
        status = "NOT_STARTED"
    elif total_score <= 70:
        status = "IN_PROGRESS"
    else:
        status = "COMPLIANT"

    lines = [
        f"# Domain Completion Report: {domain_name}",
        "",
        f"**Date**: {date.today().isoformat()}",
        f"**Score**: {total_score}/{max_score}",
        f"**Status**: {status}",
        "",
        "## Score Breakdown",
        "",
        "| # | Category | Weight | Score | Max | Status |",
        "|---|----------|--------|-------|-----|--------|",
    ]

    for c in categories:
        lines.append(
            f"| {c.category_id} | {c.name} | {c.weight} | {c.score} | {c.max_score} | {c.status} |"
        )
    lines.append(
        f"| | **Total** | | **{total_score}** | **{max_score}** | |"
    )
    lines.append("")

    # Detailed findings
    lines.append("## Detailed Findings")
    lines.append("")
    for c in categories:
        lines.append(f"### {c.category_id}. {c.name} ({c.score}/{c.max_score})")
        lines.append("")
        for ch in c.checks:
            icon = "PASS" if ch.status == "PASS" else ("PARTIAL" if ch.status == "PARTIAL" else "FAIL")
            lines.append(f"- **{ch.name}**: {icon} ({ch.score}/{ch.max_points})")
            for d in ch.details:
                lines.append(f"  - {d}")
        lines.append("")

    # Priority action items
    action_items = []
    for c in categories:
        if c.status != "PASS":
            for ch in c.checks:
                if ch.status != "PASS":
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


def generate_json_report(domain_name: str, categories: list) -> dict:
    """Generate a JSON compliance report."""
    total_score = sum(c.score for c in categories)
    max_score = sum(c.max_score for c in categories)

    if total_score <= 30:
        status = "NOT_STARTED"
    elif total_score <= 70:
        status = "IN_PROGRESS"
    else:
        status = "COMPLIANT"

    return {
        "domain": domain_name,
        "date": date.today().isoformat(),
        "score": total_score,
        "max_score": max_score,
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
    ]

    if output_json:
        return json.dumps(generate_json_report(domain_name, categories), indent=2)
    return generate_report(domain_name, categories)


def main():
    parser = argparse.ArgumentParser(
        description="Omnia Domain Completion Checker - Galaxy compliance scoring tool"
    )
    parser.add_argument("domain_path", help="Path to the domain directory (e.g., src/repo_manager)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    args = parser.parse_args()

    result = run(args.domain_path, output_json=args.json)
    print(result)


if __name__ == "__main__":
    main()
