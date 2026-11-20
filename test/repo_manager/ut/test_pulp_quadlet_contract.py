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
"""Pulp Quadlet least-privilege contracts."""

from pathlib import Path

import jinja2
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ROLE = REPO_ROOT / "src" / "repo_manager" / "roles" / "deploy_pulp"
QUADLET = ROLE / "templates" / "https_quadlet.j2"
DEPLOY_TASKS = ROLE / "tasks" / "deploy_container_https.yml"
ROLE_VARS = ROLE / "vars" / "main.yml"


def _render_quadlet():
    """Render the Pulp Quadlet with minimal inputs."""
    env = jinja2.Environment(trim_blocks=True, undefined=jinja2.StrictUndefined)
    return env.from_string(QUADLET.read_text(encoding="utf-8")).render(
        pulp_image="docker.io/pulp/pulp:test",
        pulp_container_name="pulp",
        device_name="/dev/fuse:/dev/fuse:rwm",
        volumes_https=["/srv/settings:/etc/pulp:z"],
        pulp_deployment_defaults={"container_mounts": {"settings_path": "/etc/pulp"}},
        arg_list=["-e PULP_WORKERS=4"],
        pulp_publish_port="192.0.2.10:2225:443",
    )


def _task_names():
    """Return deploy task names in execution order."""
    return [task["name"] for task in yaml.safe_load(DEPLOY_TASKS.read_text(encoding="utf-8"))]


def test_pulp_quadlet_is_not_privileged():
    """Pulp must not run privileged; only /dev/fuse is passed through."""
    rendered = _render_quadlet()
    assert "--privileged" not in rendered
    assert "Privileged" not in rendered
    assert "AddDevice=/dev/fuse:/dev/fuse:rwm" in rendered


def test_pulp_quadlet_keeps_selinux_confinement():
    """Pulp must stay SELinux-confined on every storage type."""
    template = QUADLET.read_text(encoding="utf-8")
    assert "SecurityLabelDisable" not in template
    assert "label=disable" not in template


def test_selinux_storage_check_runs_before_pulp_changes():
    """Storage checks need existing paths and must stop before Pulp is changed."""
    names = _task_names()
    order = [
        "Create Pulp runtime directories",
        "Detect Pulp host storage filesystem types",
        "Identify SELinux booleans required by Pulp network storage",
        "Read SELinux booleans required by Pulp network storage",
        "Require SELinux access for confined Pulp network storage",
        "Render Pulp settings",
        "Deploy Pulp HTTPS Quadlet",
        "Start or restart Pulp service and enable it for reboot",
    ]
    positions = [names.index(name) for name in order]
    assert positions == sorted(positions)


def test_network_filesystems_map_to_selinux_booleans():
    """NFS needs virt_use_nfs; local filesystems need no boolean."""
    role_vars = yaml.safe_load(ROLE_VARS.read_text(encoding="utf-8"))
    booleans = role_vars["pulp_network_fs_selinux_booleans"]
    assert booleans == {"nfs": "virt_use_nfs", "nfs4": "virt_use_nfs"}
    for fstype in ("xfs", "ext4", "btrfs", "tmpfs", "overlay"):
        assert fstype not in booleans
    assert "deploy_pulp_require_selinux_network_storage_boolean_msg" in role_vars
