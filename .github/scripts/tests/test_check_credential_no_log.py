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

"""Tests for the credential no_log checker used by the credential-no-log workflow (CWE-532)."""

import importlib.util
from pathlib import Path


SCANNER = Path(__file__).resolve().parents[1] / "check_credential_no_log.py"
TELEMETRY_ROOT = Path(__file__).resolve().parents[3] / "src/telemetry"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("check_credential_no_log", SCANNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_telemetry_credential_module_args_declare_no_log():
    """Every credential-like telemetry module argument must declare no_log: True."""
    assert _load_scanner().check_modules(TELEMETRY_ROOT / "plugins/modules") == []


def test_telemetry_credential_tasks_declare_no_log():
    """Every task passing telemetry_credentials.* must set task-level no_log."""
    assert _load_scanner().check_tasks(TELEMETRY_ROOT) == []


def test_credential_checker_fails_closed(tmp_path):
    """Templated no_log values and unparseable files are violations, not passes."""
    scanner = _load_scanner()
    tasks_dir = tmp_path / "roles/demo/tasks"
    tasks_dir.mkdir(parents=True)
    task = "  debug:\n    msg: \"{{ telemetry_credentials.bmc_password }}\"\n"
    (tasks_dir / "safe.yml").write_text(f"- name: safe\n{task}  no_log: true\n", encoding="utf-8")
    (tasks_dir / "templated.yml").write_text(
        f"- name: templated\n{task}  no_log: \"{{{{ false }}}}\"\n", encoding="utf-8",
    )
    (tasks_dir / "broken.yml").write_text("- name: broken\n  debug: [unclosed\n", encoding="utf-8")
    modules_dir = tmp_path / "plugins/modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    task_violations = scanner.check_tasks(tmp_path)
    module_violations = scanner.check_modules(modules_dir)

    assert len(task_violations) == 2
    assert any("templated" in v for v in task_violations)
    assert any("broken.yml" in v and "cannot parse YAML" in v for v in task_violations)
    assert not any("safe.yml" in v for v in task_violations)
    assert len(module_violations) == 1 and "cannot parse module" in module_violations[0]
