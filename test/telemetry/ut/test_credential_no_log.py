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

"""Contract tests keeping telemetry credentials out of persisted Ansible logs (CWE-532)."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
TELEMETRY_ROOT = REPO_ROOT / "src/telemetry"
MODULES_DIR = TELEMETRY_ROOT / "plugins/modules"
SETUP_ROLE = TELEMETRY_ROOT / "roles/telemetry_setup"
DOMAIN_INIT = TELEMETRY_ROOT / "domain-init.sh"
SCANNER = REPO_ROOT / ".github/scripts/check_credential_no_log.py"

SENTINEL_USER = "SENTINEL_USER_c4f1e9"
SENTINEL_PASSWORD = "SENTINEL_PASS_c4f1e9"


def _read(path):
    return path.read_text(encoding="utf-8")


def _load_scanner():
    spec = importlib.util.spec_from_file_location("check_credential_no_log", SCANNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_telemetry_credential_module_args_declare_no_log():
    """Every credential-like module argument must declare no_log: True."""
    assert _load_scanner().check_modules(MODULES_DIR) == []


def test_telemetry_credential_tasks_declare_no_log():
    """Every task passing telemetry_credentials.* must set task-level no_log."""
    assert _load_scanner().check_tasks(TELEMETRY_ROOT) == []


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)
def test_module_failure_does_not_log_sentinel_credentials(tmp_path):
    """A failing module run must not write sentinel credentials to the log file."""
    playbook = tmp_path / "sentinel.yml"
    log_file = tmp_path / "telemetry.log"
    ansible_cfg = tmp_path / "ansible.cfg"
    ansible_cfg.write_text("[defaults]\n", encoding="utf-8")
    playbook.write_text(yaml.safe_dump([{
        "hosts": "localhost",
        "connection": "local",
        "gather_facts": False,
        "tasks": [
            {
                "name": "Force enable_telemetry_service failure",
                "enable_telemetry_service": {
                    "idrac_ips": [],
                    "username": SENTINEL_USER,
                    "password": SENTINEL_PASSWORD,
                },
                "failed_when": True,
                "ignore_errors": True,
            },
            {
                "name": "Force idrac_telemetry_filter failure",
                "idrac_telemetry_filter": {
                    "bmc_ip_list": [],
                    "bmc_username": SENTINEL_USER,
                    "bmc_password": SENTINEL_PASSWORD,
                    "min_firmware_version_reqd": 1,
                },
                "failed_when": True,
                "ignore_errors": True,
            },
        ],
    }]), encoding="utf-8")
    env = {
        **os.environ,
        "ANSIBLE_CONFIG": str(ansible_cfg),
        "ANSIBLE_LOG_PATH": str(log_file),
        "ANSIBLE_LIBRARY": str(MODULES_DIR),
        "ANSIBLE_STDOUT_CALLBACK": "default",
        # Older ansible-core always returned module_args in results; force it on.
        "ANSIBLE_INJECT_INVOCATION": "True",
        "ANSIBLE_NOCOLOR": "1",
    }

    result = subprocess.run(
        ["ansible-playbook", "-i", "localhost,", str(playbook), "-vvv"],
        env=env, capture_output=True, text=True, timeout=300, check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ignored=2" in result.stdout
    log_text = log_file.read_text(encoding="utf-8")
    for sentinel in (SENTINEL_USER, SENTINEL_PASSWORD):
        assert sentinel not in log_text
        assert sentinel not in result.stdout


def test_telemetry_log_dir_and_files_are_restricted():
    """Ansible log dir/files must not be world-readable and must be rotated."""
    setup_vars = yaml.safe_load(_read(SETUP_ROLE / "vars/main.yml"))
    tasks = yaml.safe_load(_read(SETUP_ROLE / "tasks/create_directories.yml"))
    by_name = {task["name"]: task for task in tasks}

    assert setup_vars["telemetry_log_dir_mode"] == "0750"
    assert setup_vars["telemetry_log_file_mode"] == "0640"
    log_dir_task = by_name["Ensure Ansible log directory exists with restricted permissions"]
    assert log_dir_task["ansible.builtin.file"]["mode"] == "{{ telemetry_log_dir_mode }}"
    runtime_dirs = by_name["Ensure telemetry runtime directories exist"]["loop"]
    assert "{{ telemetry_log_dir }}" not in runtime_dirs
    file_task = by_name["Restrict permissions on existing Ansible log files"]
    assert file_task["ansible.builtin.file"]["mode"] == "{{ telemetry_log_file_mode }}"
    rotate_task = by_name["Configure log rotation for Ansible log files"]
    assert "create {{ telemetry_log_file_mode }}" in rotate_task["ansible.builtin.copy"]["content"]

    domain_init = _read(DOMAIN_INIT)
    assert 'chmod 0750 "$ansible_log_dir"' in domain_init
    assert "-exec chmod 0640 {} +" in domain_init
