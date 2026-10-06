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
"""Registry image pin and lifecycle reconciliation contracts."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ROLES_ROOT = REPO_ROOT / "src" / "image_build_manager" / "roles"
DEPLOY_ROLE = ROLES_ROOT / "deploy_registry"
CLEANUP_ROLE = ROLES_ROOT / "cleanup_build_artifacts"
EXPECTED_REGISTRY_IMAGE = "docker.io/library/registry"
EXPECTED_REGISTRY_TAG = "3.1.2"


def _load_yaml(path: Path):
    """Load a tracked Ansible YAML file."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _task_named(tasks: list[dict], name: str) -> dict:
    """Return one task by its stable Ansible display name."""
    return next(task for task in tasks if task.get("name") == name)


def test_registry_image_pin_is_aligned_across_lifecycle():
    """Deploy, Quadlet, and cleanup must use registry 3.1.2 consistently."""
    deploy_vars = _load_yaml(DEPLOY_ROLE / "vars" / "main.yml")
    cleanup_vars = _load_yaml(CLEANUP_ROLE / "vars" / "main.yml")

    for role_vars in (deploy_vars, cleanup_vars):
        assert role_vars["registry_image"] == EXPECTED_REGISTRY_IMAGE
        assert role_vars["registry_tag"] == EXPECTED_REGISTRY_TAG

    quadlet = (
        DEPLOY_ROLE / "templates" / "registry" / "registry.service.j2"
    ).read_text(encoding="utf-8")
    assert "Image={{ registry_image }}:{{ registry_tag }}" in quadlet

    cleanup_tasks = _load_yaml(CLEANUP_ROLE / "tasks" / "cleanup_registry.yml")
    remove_image = _task_named(cleanup_tasks, "Remove registry container image")
    assert remove_image["ansible.builtin.command"]["argv"][-1] == (
        "{{ registry_image }}:{{ registry_tag }}"
    )


def test_registry_deploy_reconciles_pin_changes_for_active_service():
    """Prepare must restart an active registry when its pin changes."""
    deploy_tasks = _load_yaml(DEPLOY_ROLE / "tasks" / "main.yml")
    rendered = _task_named(
        deploy_tasks, "Render registry Quadlet service file"
    )
    pulled = _task_named(
        deploy_tasks, "Pre-pull registry image to avoid quadlet pull timeout"
    )
    reconciled = _task_named(
        deploy_tasks, "Reconcile registry service with the configured image"
    )

    assert rendered["register"] == "registry_quadlet"
    assert pulled["register"] == "registry_image_pull"
    service_state = reconciled["ansible.builtin.systemd_service"]["state"]
    assert "registry_quadlet.changed" in service_state
    assert "registry_image_pull.changed" in service_state
    assert "restarted" in service_state
    assert all("registry_service_status" not in repr(task) for task in deploy_tasks)
