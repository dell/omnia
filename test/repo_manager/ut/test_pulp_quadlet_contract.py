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

import re
from pathlib import Path

import jinja2
import jinja2.nativetypes
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ROLE = REPO_ROOT / "src" / "repo_manager" / "roles" / "deploy_pulp"
QUADLET = ROLE / "templates" / "https_quadlet.j2"
DEPLOY_TASKS = ROLE / "tasks" / "deploy_container_https.yml"
ROLE_VARS = ROLE / "vars" / "main.yml"
DEFAULT_VARS = REPO_ROOT / "src" / "repo_manager" / "vars" / "default.yml"


def _render_quadlet():
    """Render the Pulp Quadlet with minimal inputs."""
    env = jinja2.Environment(trim_blocks=True, undefined=jinja2.StrictUndefined)
    return env.from_string(QUADLET.read_text(encoding="utf-8")).render(
        pulp_image="docker.io/pulp/pulp:test",
        pulp_container_name="pulp",
        device_name="/dev/fuse:/dev/fuse:rwm",
        pulp_container_capabilities=_role_vars()["pulp_container_capabilities"],
        volumes_https=["/srv/settings:/etc/pulp:z"],
        pulp_deployment_defaults={"container_mounts": {"settings_path": "/etc/pulp"}},
        arg_list=["-e PULP_WORKERS=4"],
        pulp_publish_port="192.0.2.10:2225:443",
    )


def _task_names():
    """Return deploy task names in execution order."""
    return [task["name"] for task in yaml.safe_load(DEPLOY_TASKS.read_text(encoding="utf-8"))]


def _task(name):
    """Return one deploy task by name."""
    tasks = yaml.safe_load(DEPLOY_TASKS.read_text(encoding="utf-8"))
    return next(task for task in tasks if task["name"] == name)


def _role_vars():
    """Return the deploy_pulp role variables."""
    return yaml.safe_load(ROLE_VARS.read_text(encoding="utf-8"))


STORAGE_PATHS = {
    "settings": "/srv/pulp/settings",
    "content": "/srv/pulp/content",
    "database": "/srv/pulp/pgsql",
    "container_work": "/srv/pulp/containers",
    "service_logs": "/srv/pulp/log",
    "cli_config": "/srv/pulp/cli",
}


def _select_relabel_paths(fstypes, selinux_status="enabled"):
    """Evaluate the real relabel-selection expression for given fstypes."""
    expression = _task("Select Pulp storage paths that need SELinux relabeling")[
        "ansible.builtin.set_fact"]["_pulp_selinux_relabel_paths"]
    results = [
        {"item": {"name": name, "path": path}, "stdout": fstypes[name]}
        for name, path in STORAGE_PATHS.items()
    ]
    env = jinja2.nativetypes.NativeEnvironment(undefined=jinja2.StrictUndefined)
    return env.from_string(expression).render(
        _pulp_storage_fstypes={"results": results},
        pulp_network_fs_selinux_booleans=_role_vars()["pulp_network_fs_selinux_booleans"],
        ansible_selinux={"status": selinux_status},
    )


def _render_volumes(relabel_paths):
    """Render volumes_https from role vars for a set of relabeled paths."""
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    context = {
        "pulp_settings_dir": STORAGE_PATHS["settings"],
        "pulp_content_dir": STORAGE_PATHS["content"],
        "pulp_database_dir": STORAGE_PATHS["database"],
        "pulp_container_work_dir": STORAGE_PATHS["container_work"],
        "pulp_logs_dir": STORAGE_PATHS["service_logs"],
        "pulp_ha_dir": STORAGE_PATHS["cli_config"],
        "deploy_pulp_nginx_timeout_file": "/srv/pulp/settings/nginx/timeouts.conf",
        "deploy_pulp_nginx_timeout_container_file": "/etc/nginx/pulp/timeouts.conf",
        "pulp_deployment_defaults": {
            "container_mounts": {
                "settings_path": "/etc/pulp",
                "content_path": "/var/lib/pulp",
                "database_path": "/var/lib/pgsql",
                "container_work_path": "/var/lib/containers",
                "service_log_path": "/var/log/pulp",
                "cli_config_path": "/root/.config/pulp",
            }
        },
        "_pulp_selinux_relabel_paths": relabel_paths,
    }
    rendered = [
        env.from_string(vol).render(context).strip()
        for vol in _role_vars()["volumes_https"]
    ]
    return {vol.split(":", 1)[0]: vol for vol in rendered}


def test_pulp_quadlet_is_not_privileged():
    """Pulp must not run privileged; only /dev/fuse is passed through."""
    rendered = _render_quadlet()
    assert "--privileged" not in rendered
    assert "Privileged" not in rendered
    assert "AddDevice=/dev/fuse:/dev/fuse:rwm" in rendered


def test_pulp_quadlet_drops_capabilities_to_documented_minimum():
    """Pulp drops all capabilities and adds back only the documented list."""
    rendered = _render_quadlet()
    caps = _role_vars()["pulp_container_capabilities"]
    assert "DropCapability=ALL" in rendered
    assert f"AddCapability={' '.join(caps)}" in rendered
    assert caps == [
        "CHOWN", "DAC_OVERRIDE", "SETUID", "SETGID", "KILL",
        "NET_BIND_SERVICE",
    ]
    for forbidden in ("ALL", "FOWNER", "SYS_ADMIN", "NET_ADMIN", "NET_RAW",
                      "MKNOD", "SYS_PTRACE", "SYS_MODULE", "DAC_READ_SEARCH"):
        assert forbidden not in caps


def test_pulp_quadlet_blocks_privilege_escalation():
    """Pulp processes cannot gain privileges through setuid or file capabilities."""
    assert "NoNewPrivileges=true" in _render_quadlet()


def test_pulp_image_is_pinned_by_digest():
    """The Pulp image is pinned to an immutable sha256 digest."""
    defaults = yaml.safe_load(DEFAULT_VARS.read_text(encoding="utf-8"))
    image = defaults["pulp_deployment_defaults"]["image"]
    assert re.fullmatch(r"docker\.io/pulp/pulp:[\w.]+@sha256:[0-9a-f]{64}", image)


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
        "Select Pulp storage paths that need SELinux relabeling",
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


def test_selinux_relabel_paths_follow_detected_filesystems():
    """Local paths are relabeled under SELinux; NFS paths and disabled SELinux are not."""
    mixed = {
        "settings": "xfs",
        "content": "nfs4",
        "database": "ext4",
        "container_work": "xfs",
        "service_logs": "xfs",
        "cli_config": "nfs",
    }
    assert _select_relabel_paths(mixed) == [
        STORAGE_PATHS["settings"],
        STORAGE_PATHS["database"],
        STORAGE_PATHS["container_work"],
        STORAGE_PATHS["service_logs"],
    ]
    all_nfs = dict.fromkeys(STORAGE_PATHS, "nfs4")
    assert _select_relabel_paths(all_nfs) == []
    all_local = dict.fromkeys(STORAGE_PATHS, "xfs")
    assert _select_relabel_paths(all_local) == list(STORAGE_PATHS.values())
    assert _select_relabel_paths(all_local, selinux_status="disabled") == []


def test_pulp_volumes_apply_relabel_per_storage_path():
    """Rendered volumes carry :z only for paths selected for relabeling."""
    nginx_file = "/srv/pulp/settings/nginx/timeouts.conf"

    all_local = _render_volumes(list(STORAGE_PATHS.values()))
    for path in STORAGE_PATHS.values():
        assert all_local[path].endswith(":z")
    assert all_local[nginx_file].endswith(":ro,z")

    no_relabel = _render_volumes([])
    for path in STORAGE_PATHS.values():
        assert not no_relabel[path].endswith(":z")
    assert no_relabel[nginx_file].endswith(":ro")

    mixed = _render_volumes(
        [path for name, path in STORAGE_PATHS.items() if name != "content"]
    )
    assert mixed[STORAGE_PATHS["content"]] == f"{STORAGE_PATHS['content']}:/var/lib/pulp"
    assert mixed[STORAGE_PATHS["database"]].endswith(":z")
    assert mixed[STORAGE_PATHS["settings"]].endswith(":z")
    assert mixed[nginx_file].endswith(":ro,z")


def test_pulp_volumes_do_not_use_global_selinux_option():
    """Pulp volumes must not fall back to the global selinux_option flag."""
    for vol in _role_vars()["volumes_https"]:
        assert "selinux_option" not in vol
