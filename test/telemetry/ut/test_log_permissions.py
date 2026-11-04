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

"""Contract tests keeping persisted telemetry Ansible logs restricted (CWE-532)."""

from pathlib import Path

import yaml


TELEMETRY_ROOT = Path(__file__).resolve().parents[3] / "src/telemetry"
SETUP_ROLE = TELEMETRY_ROOT / "roles/telemetry_setup"
DOMAIN_INIT = TELEMETRY_ROOT / "domain-init.sh"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_telemetry_log_dir_and_files_are_restricted():
    """Ansible log dir/files must not be world-readable."""
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

    domain_init = _read(DOMAIN_INIT)
    assert 'chmod 0750 "$ansible_log_dir"' in domain_init
    assert "-exec chmod 0640 {} +" in domain_init
