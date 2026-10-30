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

"""Fail when credential-bearing module arguments or tasks lack no_log (CWE-532).

Checks performed under each domain root (default: src/telemetry):
  1. Custom module argument specs (plugins/modules/*.py): every argument whose
     name looks like a credential must declare ``no_log: True``.
  2. Role/playbook tasks (*.yml): every task that references a credential
     variable (e.g. ``telemetry_credentials.*``) must set task-level
     ``no_log``.

Usage:
  python3 .github/scripts/check_credential_no_log.py [DOMAIN_ROOT ...]
"""

import ast
import re
import sys
from pathlib import Path

import yaml

CREDENTIAL_ARG_RE = re.compile(
    r"(^|_)(password|passwd|username|user|token|secret)$", re.IGNORECASE
)
# Matches variable access (telemetry_credentials.bmc_password / ['x']) but not
# the credential file name (telemetry_credentials.yml).
CREDENTIAL_VAR_RE = re.compile(r"\btelemetry_credentials\s*(\.(?!ya?ml\b)\w|\[)")
# Task keywords that are evaluated by Ansible itself and never reach a
# module invocation, so a credential reference there cannot leak.
NON_LEAKING_KEYWORDS = {
    "name", "when", "changed_when", "failed_when", "until", "tags",
    "no_log", "register", "block", "rescue", "always",
}
BLOCK_KEYWORDS = ("block", "rescue", "always")


def _const(node):
    return node.value if isinstance(node, ast.Constant) else None


def _spec_entries(tree):
    """Yield (arg_name, options_dict_or_None, lineno) for argument-spec entries."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                name = _const(key) if key is not None else None
                if not isinstance(name, str):
                    continue
                if isinstance(value, ast.Dict):
                    opts = {_const(k): v for k, v in zip(value.keys, value.values) if k is not None}
                elif isinstance(value, ast.Call) and getattr(value.func, "id", "") == "dict":
                    opts = {kw.arg: kw.value for kw in value.keywords}
                else:
                    continue
                if "type" in opts:
                    yield name, opts, key.lineno
        elif isinstance(node, ast.Call) and getattr(node.func, "id", "") == "dict":
            for kw in node.keywords:
                value = kw.value
                if isinstance(value, ast.Call) and getattr(value.func, "id", "") == "dict":
                    opts = {k.arg: k.value for k in value.keywords}
                    if "type" in opts:
                        yield kw.arg, opts, value.lineno


def check_modules(modules_dir):
    """Return violations for credential arguments without no_log=True."""
    violations = []
    for path in sorted(Path(modules_dir).glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, opts, lineno in _spec_entries(tree):
            if not CREDENTIAL_ARG_RE.search(name):
                continue
            if _const(opts.get("no_log")) is not True:
                violations.append(
                    f"{path}:{lineno}: module argument '{name}' must declare no_log: True"
                )
    return violations


def _iter_tasks(items):
    for task in items or []:
        if not isinstance(task, dict):
            continue
        yield task
        for key in BLOCK_KEYWORDS:
            if isinstance(task.get(key), list):
                yield from _iter_tasks(task[key])


def _references_credentials(task):
    payload = {k: v for k, v in task.items() if k not in NON_LEAKING_KEYWORDS}
    return bool(CREDENTIAL_VAR_RE.search(yaml.safe_dump(payload, default_flow_style=True)))


def _no_log_enabled(value):
    return value is True or (isinstance(value, str) and "{{" in value)


def check_tasks(domain_root):
    """Return violations for tasks referencing credentials without no_log."""
    violations = []
    for path in sorted(Path(domain_root).rglob("*.yml")):
        if not ({"tasks", "handlers", "playbooks"} & set(path.parts)):
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, list):
            continue
        plays_or_tasks = []
        for item in data:
            if isinstance(item, dict) and ("hosts" in item or "import_playbook" in item):
                for section in ("pre_tasks", "tasks", "post_tasks", "handlers"):
                    plays_or_tasks.extend(item.get(section) or [])
            else:
                plays_or_tasks.append(item)
        for task in _iter_tasks(plays_or_tasks):
            if _references_credentials(task) and not _no_log_enabled(task.get("no_log")):
                task_name = task.get("name", "<unnamed>")
                violations.append(
                    f"{path}: task '{task_name}' references credentials without no_log"
                )
    return violations


def main(argv):
    """Run all checks and return a process exit code."""
    roots = [Path(p) for p in argv] or [Path("src/telemetry")]
    violations = []
    for root in roots:
        violations.extend(check_modules(root / "plugins" / "modules"))
        violations.extend(check_tasks(root))
    for violation in violations:
        print(violation)
    if violations:
        print(f"\n{len(violations)} credential no_log violation(s) found (CWE-532).")
        return 1
    print("No credential no_log violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
