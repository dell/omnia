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

"""Build Stream — build pipeline outputs on the OIM (execute tag).

Repo Manager: ``<repo_manager data>/output/<project>/repo_status.yml``
(written by create-local-repository) must report ``overall_status: success``.

Image Build Manager: ``<image_build_manager data>/output/<project>/
<image_group>/build_status.yml`` (written by build-image) lists, per
functional group, the rootfs image, kernel and initrd. Every one must be in
``s3://boot-images/`` and the image must be a repository in the registry.
build_status.yml is authoritative because an up-to-date image can be reused
from an earlier build, so its name need not contain the current job.
"""

import posixpath
from typing import Any, Dict, List, Set, Tuple

from omnia_auto import read_remote_yaml

from .execute_probe_func import domain_data_path, project_name, run_cmd
from ..vars.execute_vars import (
    BOOT_ARTIFACT_KEYS,
    IMAGE_BUILD_MANAGER_DOMAIN,
    REPO_MANAGER_DOMAIN,
    REPO_STATUS_FILE,
    BUILD_STATUS_FILE,
    S3CMD_CONFIG,
)
from ..vars.common_vars import REGISTRY_PORT, S3_BOOT_IMAGES_BUCKET


def check_repo_status(host: Any) -> Dict[str, Any]:
    """Read repo_status.yml and check ``overall_status`` is ``success``.

    Returns:
        Dict with keys: success, path, overall_status, error.
    """
    result = {"success": False, "path": "", "overall_status": "", "error": ""}
    try:
        result["path"] = (f"{domain_data_path(host, REPO_MANAGER_DOMAIN)}/output/"
                          f"{project_name(host)}/{REPO_STATUS_FILE}")
        status = read_remote_yaml(host, result["path"]) or {}
    except (OSError, RuntimeError, ValueError) as exc:
        result["error"] = f"cannot read {result['path'] or REPO_STATUS_FILE}: {exc}"
        return result
    overall = str(status.get("overall_status", "")) if isinstance(status, dict) else ""
    result["overall_status"] = overall
    result["success"] = overall.lower() == "success"
    if not result["success"]:
        result["error"] = (f"overall_status is '{overall or 'missing'}' in {result['path']} "
                           "(expected 'success')")
    return result


def build_status_images(host: Any, image_group_id: str) -> Dict[str, Any]:
    """Return ``{functional_group: {image, kernel, initrd}}`` from build_status.yml.

    Returns:
        Dict with keys: success, path, images, error.
    """
    result = {"success": False, "path": "", "images": {}, "error": ""}
    try:
        result["path"] = (f"{domain_data_path(host, IMAGE_BUILD_MANAGER_DOMAIN)}/output/"
                          f"{project_name(host)}/{image_group_id}/{BUILD_STATUS_FILE}")
        status = read_remote_yaml(host, result["path"]) or {}
    except (OSError, RuntimeError, ValueError) as exc:
        result["error"] = f"cannot read {result['path'] or BUILD_STATUS_FILE}: {exc}"
        return result
    groups = status.get("functional_group_images", []) if isinstance(status, dict) else []
    for architecture in groups if isinstance(groups, list) else []:
        for images in (architecture.values() if isinstance(architecture, dict) else []):
            for image in images if isinstance(images, list) else []:
                if isinstance(image, dict) and image.get("functional_group"):
                    result["images"][image["functional_group"]] = image
    result["success"] = bool(result["images"])
    if not result["success"]:
        result["error"] = f"no functional-group images in {result['path']}"
    return result


def _expected_s3_paths(image: Dict[str, Any]) -> List[str]:
    """Return the s3:// paths of a functional group's image, kernel and initrd."""
    return [f"s3://{str(image.get(key, '')).lstrip('/')}" for key in BOOT_ARTIFACT_KEYS
            if image.get(key)]


def _registry_repo_name(image: Dict[str, Any]) -> str:
    """Return the registry repository name of a functional group's image path."""
    parts = posixpath.normpath(str(image.get("image", ""))).split("/")
    return parts[-3] if len(parts) >= 3 else ""


def _list_registry_and_s3(host: Any, errors: List[str]) -> Tuple[List[str], Set[str]]:
    """List the local registry repositories and the boot-images S3 keys.

    A failed listing is appended to ``errors``.
    """
    registry = f"{run_cmd(host, 'hostname').stdout.strip()}:{REGISTRY_PORT}"
    repos_cmd = run_cmd(host, "regctl_repo_ls", registry=registry)
    s3_cmd = run_cmd(host, "s3_list_recursive", config=S3CMD_CONFIG, bucket=S3_BOOT_IMAGES_BUCKET)
    for label, cmd in (("regctl repo ls", repos_cmd), ("s3cmd ls -r", s3_cmd)):
        if cmd.rc != 0:
            errors.append(f"{label} failed (rc={cmd.rc})")
    repos = [line.strip() for line in repos_cmd.stdout.splitlines() if line.strip()]
    keys = {f"s3://{line.split('s3://', 1)[1].strip()}" for line in s3_cmd.stdout.splitlines()
            if "s3://" in line}
    return repos, keys


def verify_build_artifacts(host: Any, image_group_id: str, roles: List[str]) -> Dict[str, Any]:
    """Check every role's registry repository and S3 boot files.

    Returns:
        Dict with keys: success, registry ({role: bool}), s3 ({role: bool}),
        errors (list).
    """
    result: Dict[str, Any] = {"success": False, "registry": {}, "s3": {}, "errors": []}
    status = build_status_images(host, image_group_id)
    if not status["success"]:
        result["errors"].append(status["error"])
        return result
    repos, keys = _list_registry_and_s3(host, result["errors"])
    for role in roles:
        image = status["images"].get(role, {})
        name = _registry_repo_name(image)
        result["registry"][role] = bool(name) and any(
            repo == name or repo.endswith(f"/{name}") for repo in repos)
        expected = _expected_s3_paths(image)
        result["s3"][role] = len(expected) == len(BOOT_ARTIFACT_KEYS) and set(expected) <= keys
    result["success"] = (not result["errors"] and all(result["registry"].values())
                         and all(result["s3"].values()))
    return result
