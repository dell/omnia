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

"""Static deployment checks for authenticated playbook queue wiring."""

from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
ROLE_ROOT = REPOSITORY_ROOT / "src" / "build_stream" / "roles"
DEPLOY_ROLE = ROLE_ROOT / "deploy_bsm"


def _read(relative_path: str) -> str:
    return (DEPLOY_ROLE / relative_path).read_text(encoding="utf-8")


def test_queue_secret_and_replay_state_are_host_local():
    variables = yaml.safe_load(_read("vars/main.yml"))

    assert variables["build_stream_queue_auth_dir"].startswith("/etc/")
    assert variables["build_stream_queue_replay_dir"].startswith("/var/lib/")
    assert variables["build_stream_queue_api_state_dir"].startswith("/var/lib/")
    assert "omnia_path" not in variables["build_stream_queue_auth_dir"]
    assert "omnia_path" not in variables["build_stream_queue_replay_dir"]
    assert "omnia_path" not in variables["build_stream_queue_api_state_dir"]


def test_api_receives_read_only_secret_and_authenticated_queue_configuration():
    quadlet = _read("templates/build_stream.j2")

    assert "Environment=PLAYBOOK_QUEUE_BASE=" in quadlet
    assert "Environment=PLAYBOOK_QUEUE_AUTH_KEY_FILE=" in quadlet
    assert "Environment=PLAYBOOK_QUEUE_API_STATE_DIR=" in quadlet
    assert (
        "Volume={{ build_stream_queue_auth_key }}:"
        "{{ build_stream_container_queue_auth_key }}:ro"
    ) in quadlet
    assert (
        "Volume={{ build_stream_queue_api_state_dir }}:"
        "{{ build_stream_container_queue_api_state_dir }}:rw"
    ) in quadlet


def test_watcher_is_started_only_after_authenticated_api_is_deployed():
    main_tasks = yaml.safe_load(_read("tasks/main.yml"))
    task_names = [task["name"] for task in main_tasks]

    assert task_names.index("Provision playbook watcher service") < task_names.index(
        "Deploy omnia_build_stream container"
    )
    assert task_names.index("Deploy omnia_build_stream container") < task_names.index(
        "Start playbook watcher after authenticated producer deployment"
    )


def test_deployment_refuses_legacy_backlog_and_preserves_existing_key():
    enable_tasks = _read("tasks/enable_watcher_service.yml")

    assert "Refuse mixed unsigned and authenticated queue deployment" in enable_tasks
    assert "not queue_auth_key_stat.stat.exists" in enable_tasks
    assert "queue_transition_files.matched | default(0) | int > 0" in enable_tasks
    assert 'creates: "{{ build_stream_queue_auth_key }}"' in enable_tasks
    assert 'mode: "{{ build_stream_secret_file_mode }}"' in enable_tasks


def test_cleanup_removes_host_local_queue_security_state():
    cleanup_vars_path = ROLE_ROOT / "cleanup_build_stream" / "vars" / "main.yml"
    cleanup_vars = yaml.safe_load(cleanup_vars_path.read_text(encoding="utf-8"))

    cleanup_paths = cleanup_vars["build_stream_cleanup_directory"]
    assert "/var/lib/omnia/build_stream" in cleanup_paths
    assert "/etc/omnia/build_stream" in cleanup_paths
