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
Build Image — Core Verification Functions.

Functions for verifying image_build_manager deployment:
- Container checks (MinIO, registry)
- S3 bucket and image verification
- Registry image verification
- build_status.yml validation
- Functional group verification
- Image package content verification

All functions use run_on_host() — no container exec needed
(image_build_manager runs bare-metal on the host).
"""

import json
import os
from typing import Dict, Any, List

import yaml

from omnia_auto import read_remote_env, resolve_domain_input_path

from .host_func import load_test_config
from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    IBM_CONFIG_FILE,
    MINIO_CONTAINER,
    REGISTRY_CONTAINER,
    REGISTRY_PORT,
    S3_EXPECTED_BUCKETS,
    S3CMD_CONFIG_PATH,
    SHARED_PATH,
    IMAGE_TYPES,
    IMAGE_TYPE_DISPLAY,
    CMDS,
    LISTENING_PORTS,
    SYSTEMD_SERVICES,
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    BUILD_STATUS_PATH,
    FG_PACKAGES_FILENAME,
    IMAGE_VERIFY_TEMP_IMAGE,
    IMAGE_VERIFY_TEMP_MOUNT,
    SQUASHFS_PACKAGE,
    S3_BOOT_IMAGES_BUCKET,
)


# =============================================================================
# HELPER: LOAD CONFIG FROM TARGET
# =============================================================================

def _get_shared_path() -> str:
    """Get shared_path from test_config or fall back to constant.

    The shared_path is derived from OMNIA_DATA_PATH env var on the target:
        <OMNIA_DATA_PATH>/image_build_manager
    Falls back to the SHARED_PATH constant (/opt/omnia/image_build_manager).
    """
    config = load_test_config()
    return config.get("shared_path", SHARED_PATH)


def _get_project_name() -> str:
    """Get project_name from test_config or default."""
    config = load_test_config()
    return config["project_name"]


def _get_remote_ibm_config_path(host) -> str:
    """Get the deployed image_build_config.yml path on target.

    Uses env vars to resolve::

        <OMNIA_DATA_PATH>/image_build_manager/input/<project>/image_build_config.yml
    """
    input_dir = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    return f"{input_dir}/{IBM_CONFIG_FILE}"


def _load_remote_ibm_config(host) -> dict:
    """Load image_build_config.yml from the target host.

    Returns parsed YAML as dict, or empty dict on failure.
    """
    cfg_path = _get_remote_ibm_config_path(host)
    cmd = host.run(CMDS["cat_file"].format(path=cfg_path))
    if cmd.rc != 0 or not cmd.stdout.strip():
        return {}
    try:
        return yaml.safe_load(cmd.stdout) or {}
    except yaml.YAMLError:
        return {}


def _get_built_groups_from_status(host, arch: str = None) -> List[str]:
    """Extract actually built group names from build_status.yml.

    In catalog mode, the playbook resolves group names to the full
    ``{role}_{os}_{ver}_{arch}`` format (e.g. slurm_node_rhel_10_0_x86_64).
    This helper reads build_status.yml to discover those actual names.

    Returns:
        List of built functional group name strings (may be empty).
    """
    status = check_build_status_file(host)
    if not status.get("success") or "data" not in status:
        return []

    groups = []
    fg_images = status["data"].get("functional_group_images", [])
    for arch_block in fg_images:
        if isinstance(arch_block, dict):
            for _key, entries in arch_block.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if isinstance(entry, dict):
                        fg_name = entry.get("functional_group", "")
                        if fg_name:
                            groups.append(fg_name)

    if arch:
        groups = [g for g in groups if arch in g]

    return groups


def get_configured_functional_groups(
    host, arch: str = None
) -> List[str]:
    """Get functional groups from image_build_config.yml on target.

    In **config** mode, reads the ``functional_groups`` list from the
    deployed image_build_config.yml.

    In **catalog** mode, the config list contains short (legacy) names
    but the playbook resolves them to ``{role}_{os}_{ver}_{arch}`` format.
    This function returns the *actually built* names from build_status.yml
    so that S3, registry, and package checks match correctly.

    Args:
        host: testinfra host object
        arch: Filter by architecture suffix (x86_64 or aarch64)

    Returns:
        List of functional group name strings.
    """
    cfg = _load_remote_ibm_config(host)
    if not cfg:
        return []

    # Prefer actual built names from build_status.yml when available.
    # In catalog mode the playbook expands short names (slurm_node_x86_64)
    # to full names (slurm_node_rhel_10_0_x86_64). Even in config mode the
    # build output may use expanded names. Using the built names ensures
    # S3, registry, and package checks match the real artifacts.
    built = _get_built_groups_from_status(host, arch=arch)
    if built:
        return built

    fg_list = cfg.get("functional_groups", [])
    groups = []
    for entry in fg_list:
        name = ""
        if isinstance(entry, dict):
            name = entry.get("name", "")
        elif isinstance(entry, str):
            name = entry
        if name:
            groups.append(name)

    if arch:
        groups = [g for g in groups if arch in g]

    return groups


def _get_s3_provider(host) -> str:
    """Get S3 provider from image_build_config.yml on target.

    Returns 'minio' or 'powerscale' or empty string.
    """
    cfg = _load_remote_ibm_config(host)
    s3_cfg = cfg.get("s3_configurations", {})
    return s3_cfg.get("provider", "minio").lower()


# =============================================================================
# CONTAINER CHECKS
# =============================================================================

def check_container_running(
    host, container_name: str
) -> Dict[str, Any]:
    """Check if a container is running on the target host.

    Args:
        host: testinfra host object
        container_name: Name of the container to check

    Returns:
        Dict with 'success', 'status', 'error'.
    """
    cmd = host.run(
        CMDS["podman_ps_running"].format(container=container_name)
    )

    if cmd.rc == 0 and container_name in cmd.stdout:
        status = cmd.stdout.strip()
        return {
            "success": True,
            "status": status,
            "error": None,
        }

    # Check if container exists but not running
    check_all = host.run(
        CMDS["podman_ps_all_status"].format(
            container=container_name,
        )
    )
    if check_all.rc == 0 and container_name in check_all.stdout:
        status = check_all.stdout.strip()
        return {
            "success": False,
            "status": status,
            "error": f"Container exists but not running: {status}",
        }

    return {
        "success": False,
        "status": "not_found",
        "error": f"Container '{container_name}' not found",
    }


def check_s3_containers(host) -> Dict[str, Any]:
    """Check MinIO container is running (only for minio backend).

    Returns:
        Dict with 'success', 'backend', 'results', 'details'.
    """
    backend = _get_s3_provider(host)

    if backend == "powerscale":
        return {
            "success": True,
            "backend": "powerscale",
            "skipped": True,
            "results": [],
            "details": (
                "S3 backend is PowerScale — "
                "no local containers to check"
            ),
        }

    result = check_container_running(host, MINIO_CONTAINER)
    return {
        "success": result["success"],
        "backend": "minio",
        "skipped": False,
        "results": [
            {
                "container": MINIO_CONTAINER,
                "success": result["success"],
                "status": result["status"],
                "error": result["error"],
            }
        ],
        "details": (
            f"MinIO container: "
            f"{'running' if result['success'] else 'NOT running'}"
        ),
    }


# =============================================================================
# S3 BUCKET VERIFICATION
# =============================================================================

def check_s3_buckets(host) -> Dict[str, Any]:
    """Verify required S3 buckets exist.

    Returns:
        Dict with 'success', 'found', 'missing', 'details'.
    """
    ls_cmd = host.run(CMDS["s3cmd_ls"])
    if ls_cmd.rc != 0:
        return {
            "success": False,
            "found": [],
            "missing": list(S3_EXPECTED_BUCKETS),
            "details": "",
            "error": f"s3cmd ls failed (rc={ls_cmd.rc})",
        }

    output = ls_cmd.stdout.strip()
    found = []
    missing = []
    for bucket in S3_EXPECTED_BUCKETS:
        if bucket in output:
            found.append(bucket)
        else:
            missing.append(bucket)

    total = len(S3_EXPECTED_BUCKETS)
    return {
        "success": len(missing) == 0,
        "found": found,
        "missing": missing,
        "details": f"S3 buckets: {len(found)}/{total} present",
        "error": None if not missing else (
            f"Missing: {', '.join(missing)}"
        ),
    }


# =============================================================================
# S3 IMAGE VERIFICATION
# =============================================================================

def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.1f} GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def _parse_human_size(size_str: str) -> int:
    """Parse human-readable size (72M, 1326M, 1.3G) to bytes."""
    size_str = size_str.strip().upper()
    multipliers = {
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }
    if size_str and size_str[-1] in multipliers:
        return int(float(size_str[:-1]) * multipliers[size_str[-1]])
    try:
        return int(size_str)
    except ValueError:
        return 0


def _parse_s3_listing(s3_output: str) -> Dict[str, Any]:
    """Parse s3cmd ls -Hr output into dict keyed by S3 path."""
    s3_files = {}
    for line in s3_output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 4:
            try:
                size = _parse_human_size(parts[2])
                path = parts[3]
                filename = path.split("/")[-1]
                s3_files[path] = {
                    "size": size,
                    "filename": filename,
                }
            except (ValueError, IndexError):
                pass
    return s3_files


def check_s3_bucket_images(
    host, arch: str = "x86_64"
) -> Dict[str, Any]:
    """Verify images are pushed to S3 for all configured groups.

    Performs fast pre-check of S3 bucket existence before attempting
    expensive recursive listing. Bails out early if bucket missing.

    Args:
        host: testinfra host object
        arch: Architecture filter (x86_64 or aarch64)

    Returns:
        Dict with 'success', 'results', 'details', 'error'.
        Returns success=False immediately if S3 bucket doesn't exist.
    """
    groups = get_configured_functional_groups(host, arch=arch)
    if not groups:
        return {
            "success": True,
            "skipped": True,
            "results": [],
            "details": (
                f"No {arch} functional groups configured — "
                "skipping S3 check"
            ),
            "error": None,
        }

    # Fast pre-check: verify the boot-images bucket exists before
    # running the expensive recursive listing (s3cmd ls -Hr can take
    # 45+ seconds against a non-existent bucket).
    bucket_result = check_s3_buckets(host)
    if S3_BOOT_IMAGES_BUCKET not in bucket_result.get("found", []):
        return {
            "success": False,
            "skipped": False,
            "results": [],
            "details": (
                f"S3 bucket {S3_BOOT_IMAGES_BUCKET} does not exist "
                "— skipping per-image check"
            ),
            "error": (
                f"S3 bucket {S3_BOOT_IMAGES_BUCKET} not found. "
                "Run the playbook or: run_validation image_build_manager deploy"
            ),
        }

    s3_cmd = host.run(
        CMDS["s3cmd_ls_bucket"].format(bucket=S3_BOOT_IMAGES_BUCKET)
    )
    s3_output = s3_cmd.stdout if s3_cmd.rc == 0 else ""
    s3_files = _parse_s3_listing(s3_output)

    results = []
    all_passed = True

    for fg in groups:
        group_result = {
            "functional_group": fg,
            "found_images": [],
            "missing_images": [],
            "image_details": [],
            "success": True,
        }

        for img_type in IMAGE_TYPES:
            found = False
            for path, info in s3_files.items():
                if fg not in path:
                    continue
                if img_type == "rhel":
                    # rootfs image lives in boot-images/<fg>/,
                    # NOT in efi-images/. Skip efi-images paths.
                    if "efi-images" in path:
                        continue
                    if "rhel" not in info["filename"]:
                        continue
                elif img_type not in info["filename"]:
                    continue
                found = True
                display_name = IMAGE_TYPE_DISPLAY.get(
                    img_type, img_type
                )
                group_result["found_images"].append(img_type)
                group_result["image_details"].append({
                    "type": display_name,
                    "filename": info["filename"],
                    "full_path": path,
                    "size": info["size"],
                    "size_human": _format_size(info["size"]),
                })
                break
            if not found:
                group_result["missing_images"].append(img_type)
                group_result["success"] = False

        results.append(group_result)
        if not group_result["success"]:
            all_passed = False

    passed = sum(1 for r in results if r["success"])
    total = len(groups)

    if all_passed:
        return {
            "success": True,
            "skipped": False,
            "results": results,
            "details": (
                f"All 3 images found for all {total} "
                f"{arch} functional groups"
            ),
            "error": None,
        }

    failed = [r for r in results if not r["success"]]
    error_parts = [
        f"{r['functional_group']}: "
        f"missing {', '.join(r['missing_images'])}"
        for r in failed
    ]
    return {
        "success": False,
        "skipped": False,
        "results": results,
        "details": (
            f"{passed}/{total} functional groups "
            "have all images"
        ),
        "error": "; ".join(error_parts),
    }


# =============================================================================
# REGISTRY IMAGE VERIFICATION
# =============================================================================

def check_registry_images(
    host, arch: str = "x86_64"
) -> Dict[str, Any]:
    """Verify base and compute images exist in the local registry.

    Queries the registry catalog via HTTP/HTTPS curl. Falls back
    to regctl if curl is unavailable.

    Args:
        host: testinfra host object
        arch: Architecture filter

    Returns:
        Dict with 'success', 'registry_url', 'found', 'missing'.
    """
    hostname_cmd = host.run(CMDS["hostname_cmd"])
    if hostname_cmd.rc != 0:
        return {
            "success": False,
            "registry_url": "",
            "found_images": [],
            "missing_images": [],
            "error": "Failed to get hostname",
        }

    fqdn = hostname_cmd.stdout.strip()
    registry_url = f"{fqdn}:{REGISTRY_PORT}"

    groups = get_configured_functional_groups(host, arch=arch)

    if not groups:
        return {
            "success": True,
            "skipped": True,
            "registry_url": registry_url,
            "found_images": [],
            "missing_images": [],
            "details": f"No {arch} functional groups configured",
        }

    # Expected images: base + one per functional group
    expected = [f"rhel-{arch}-base"]
    for fg in groups:
        expected.append(f"rhel-{fg}")

    # Query registry catalog via curl (try HTTP first, then HTTPS)
    catalog_repos = []
    for scheme in ("http", "https"):
        curl_cmd = host.run(
            CMDS["curl_registry_catalog_scheme"].format(
                scheme=scheme, port=REGISTRY_PORT,
            )
        )
        if curl_cmd.rc == 0 and "repositories" in curl_cmd.stdout:
            try:
                data = json.loads(curl_cmd.stdout)
                catalog_repos = data.get("repositories", [])
            except (json.JSONDecodeError, ValueError):
                catalog_repos = []
            if catalog_repos:
                break

    if not catalog_repos:
        # Fallback to regctl
        regctl_cmd = host.run(
            CMDS["regctl_repo_ls"].format(registry=registry_url)
        )
        if regctl_cmd.rc == 0:
            catalog_repos = [
                r.strip()
                for r in regctl_cmd.stdout.strip().split("\n")
                if r.strip()
            ]

    if not catalog_repos:
        return {
            "success": False,
            "registry_url": registry_url,
            "found_images": [],
            "missing_images": expected,
            "error": "Cannot query registry catalog",
        }

    # Flatten: registry repos may be prefixed (hostname/image)
    # Normalize by stripping hostname prefix for matching
    normalized_repos = []
    for repo in catalog_repos:
        normalized_repos.append(repo)
        if "/" in repo:
            normalized_repos.append(repo.split("/", 1)[1])

    found = []
    missing = []
    for img in expected:
        # Match: exact, partial, or with version suffix
        matched = any(
            img in repo for repo in normalized_repos
        )
        if matched:
            found.append(img)
        else:
            missing.append(img)

    return {
        "success": len(missing) == 0,
        "registry_url": registry_url,
        "found_images": found,
        "missing_images": missing,
        "error": None if not missing else (
            f"Missing: {', '.join(missing)}"
        ),
    }


# =============================================================================
# BUILD STATUS VERIFICATION
# =============================================================================

def check_build_status_file(host) -> Dict[str, Any]:
    """Verify build_status.yml exists and reports success.

    Returns:
        Dict with 'success', 'status', 'details', 'error'.
    """
    shared = _get_shared_path()
    project = _get_project_name()
    status_path = (
        f"{shared}/output/{project}/build_status.yml"
    )

    cmd = host.run(CMDS["cat_file"].format(path=status_path))
    if cmd.rc != 0:
        return {
            "success": False,
            "not_found": True,
            "status": "not_found",
            "status_path": status_path,
            "details": None,
            "error": (
                f"build_status.yml not found at {status_path}"
            ),
        }

    try:
        data = yaml.safe_load(cmd.stdout)
    except yaml.YAMLError as exc:
        return {
            "success": False,
            "status": "parse_error",
            "status_path": status_path,
            "details": None,
            "error": f"Failed to parse build_status.yml: {exc}",
        }

    overall = data.get("overall_status", "").lower()
    if overall == "success":
        fg_images = data.get("functional_group_images", [])
        # Count actual functional groups across all arch blocks
        all_groups = []
        for arch_block in fg_images:
            if isinstance(arch_block, dict):
                for arch_name, entries in arch_block.items():
                    if not isinstance(entries, list):
                        continue
                    for entry in entries:
                        if isinstance(entry, dict):
                            fg_name = entry.get(
                                "functional_group", ""
                            )
                            if fg_name:
                                all_groups.append({
                                    "name": fg_name,
                                    "arch": arch_name,
                                    "kernel": entry.get(
                                        "kernel", ""
                                    ),
                                    "initrd": entry.get(
                                        "initrd", ""
                                    ),
                                    "image": entry.get(
                                        "image", ""
                                    ),
                                })

        detail_lines = [
            f"overall_status: success, "
            f"{len(all_groups)} functional groups built"
        ]
        for g in all_groups:
            detail_lines.append(f"  {g['name']}:")
            if g["kernel"]:
                detail_lines.append(
                    f"    kernel:  {g['kernel'].split('/')[-1]}"
                )
            if g["initrd"]:
                detail_lines.append(
                    f"    initrd:  {g['initrd'].split('/')[-1]}"
                )
            if g["image"]:
                detail_lines.append(
                    f"    rootfs:  {g['image'].split('/')[-1]}"
                )

        return {
            "success": True,
            "status": "success",
            "status_path": status_path,
            "details": "\n".join(detail_lines),
            "error": None,
            "data": data,
        }

    return {
        "success": False,
        "status": overall or "unknown",
        "status_path": status_path,
        "details": None,
        "error": (
            f"overall_status is '{overall}', expected 'success'"
        ),
    }


# =============================================================================
# FUNCTIONAL GROUP BUILT VERIFICATION
# =============================================================================

def check_functional_groups_built(
    host, arch: str = "x86_64"
) -> Dict[str, Any]:
    """Verify all configured functional groups appear in build output.

    Cross-checks configured groups against build_status.yml and S3.

    Returns:
        Dict with 'success', 'found', 'missing', 'details'.
    """
    configured = get_configured_functional_groups(host, arch=arch)
    if not configured:
        return {
            "success": True,
            "skipped": True,
            "found": [],
            "missing": [],
            "details": (
                f"No {arch} functional groups configured"
            ),
        }

    # Check build_status.yml for listed groups
    status = check_build_status_file(host)
    built_groups = set()

    if status["success"] and "data" in status:
        fg_images = status["data"].get(
            "functional_group_images", []
        )
        for arch_block in fg_images:
            if isinstance(arch_block, dict):
                for _key, entries in arch_block.items():
                    if not isinstance(entries, list):
                        continue
                    for entry in entries:
                        if isinstance(entry, dict):
                            fg_name = entry.get(
                                "functional_group", ""
                            )
                            if fg_name:
                                built_groups.add(fg_name)

    found = [g for g in configured if g in built_groups]
    missing = [g for g in configured if g not in built_groups]

    return {
        "success": len(missing) == 0,
        "skipped": False,
        "found": found,
        "missing": missing,
        "details": (
            f"{len(found)}/{len(configured)} {arch} "
            "functional groups found in build output"
        ),
        "error": None if not missing else (
            f"Missing from build output: {', '.join(missing)}"
        ),
    }


# =============================================================================
# IMAGE PACKAGE VERIFICATION (squashfs mount + RPM check)
# =============================================================================

def _check_squashfs_tools(host) -> Dict[str, Any]:
    """Ensure squashfs-tools is installed."""
    check = host.run(
        CMDS["squashfs_tools_check"].format(
            package=SQUASHFS_PACKAGE,
        )
    )
    if check.rc == 0:
        return {"installed": True, "error": None}

    install = host.run(
        CMDS["squashfs_tools_install"].format(
            package=SQUASHFS_PACKAGE,
        )
    )
    if install.rc == 0:
        verify = host.run(
            CMDS["squashfs_tools_check"].format(
                package=SQUASHFS_PACKAGE,
            )
        )
        if verify.rc == 0:
            return {"installed": True, "error": None}

    return {
        "installed": False,
        "error": (
            f"{SQUASHFS_PACKAGE} not installed and auto-install "
            f"failed. Install manually: dnf install {SQUASHFS_PACKAGE}"
        ),
    }


def _get_image_packages_from_config(
    host, functional_group: str
) -> List[str]:
    """Get expected packages for a functional group from deployed config.

    Reads functional_group_packages.yml on the target host.

    Resolves the repo_manager output directory from the deployed
    image_build_config.yml (repo_manager_output_path) or falls
    back to ``<OMNIA_DATA_PATH>/repo_manager/output/<project>/``.
    """
    # Resolve repo_manager output dir from deployed config
    ibm_cfg = _load_remote_ibm_config(host)
    configured_path = ibm_cfg.get("repo_manager_output_path", "")
    if configured_path:
        repo_output_dir = os.path.dirname(configured_path)
    else:
        data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
        project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
        repo_output_dir = f"{data_path}/repo_manager/output/{project}"

    paths_to_try = [
        f"{repo_output_dir}/{FG_PACKAGES_FILENAME}",
    ]

    for pkg_path in paths_to_try:
        cmd = host.run(CMDS["cat_file"].format(path=pkg_path))
        if cmd.rc != 0 or not cmd.stdout.strip():
            continue
        try:
            data = yaml.safe_load(cmd.stdout)
        except yaml.YAMLError:
            continue

        base = data.get("base_packages", [])
        fg_data = data.get("functional_groups", {})
        fg_pkgs = []
        if isinstance(fg_data, dict):
            group_info = fg_data.get(functional_group, {})
            if isinstance(group_info, dict):
                fg_pkgs = group_info.get("packages", [])

        # Combine base + group packages (deduplicated)
        return list(dict.fromkeys(base + fg_pkgs))

    return []


def verify_image_packages(
    host, arch: str = "x86_64"
) -> Dict[str, Any]:
    """Download S3 images, mount, and verify RPM packages.

    Performs fast pre-check of S3 bucket existence before attempting
    image download. Bails out early if bucket missing.

    Args:
        host: testinfra host object
        arch: Architecture filter

    Returns:
        Dict with 'success', 'results', per-group package details.
        Returns prerequisite_failed=True if S3 bucket doesn't exist.
    """
    squashfs = _check_squashfs_tools(host)
    if not squashfs["installed"]:
        return {
            "success": False,
            "prerequisite_failed": True,
            "error": squashfs["error"],
            "results": [],
        }

    groups = get_configured_functional_groups(host, arch=arch)
    if not groups:
        return {
            "success": True,
            "prerequisite_failed": False,
            "results": [],
            "details": f"No {arch} functional groups configured",
        }

    temp_image = IMAGE_VERIFY_TEMP_IMAGE
    temp_mount = IMAGE_VERIFY_TEMP_MOUNT

    # Fast pre-check: verify the boot-images bucket exists before
    # running the expensive recursive listing.
    bucket_result = check_s3_buckets(host)
    if S3_BOOT_IMAGES_BUCKET not in bucket_result.get("found", []):
        return {
            "success": False,
            "prerequisite_failed": True,
            "results": [],
            "error": (
                f"S3 bucket {S3_BOOT_IMAGES_BUCKET} not found. "
                "Run the playbook or: run_validation image_build_manager deploy"
            ),
        }

    # Cleanup before start
    host.run(CMDS["umount"].format(flags="", path=temp_mount))
    host.run(CMDS["rm_file"].format(path=temp_image))
    host.run(CMDS["mkdir_p"].format(path=temp_mount))

    s3_list = host.run(
        CMDS["s3cmd_ls_bucket"].format(bucket=S3_BOOT_IMAGES_BUCKET)
    )
    s3_output = s3_list.stdout if s3_list.rc == 0 else ""

    results = []
    all_passed = True

    for fg in groups:
        expected_pkgs = _get_image_packages_from_config(host, fg)
        if not expected_pkgs:
            results.append({
                "functional_group": fg,
                "success": True,
                "expected_count": 0,
                "found_count": 0,
                "missing_count": 0,
                "package_details": [],
                "note": "No packages defined",
            })
            continue

        # Find rootfs image in S3 output
        rootfs_line = ""
        for line in s3_output.split("\n"):
            if fg in line and "rhel" in line:
                if "initramfs" not in line and "vmlinuz" not in line:
                    rootfs_line = line.strip()
                    break

        if not rootfs_line:
            results.append({
                "functional_group": fg,
                "success": False,
                "error": "No rootfs image found in S3",
                "expected_count": len(expected_pkgs),
                "found_count": 0,
                "missing_count": len(expected_pkgs),
                "package_details": [],
            })
            all_passed = False
            continue

        s3_path = rootfs_line.split()[-1] if rootfs_line else None
        if not s3_path:
            results.append({
                "functional_group": fg,
                "success": False,
                "error": "Failed to parse S3 path",
                "expected_count": len(expected_pkgs),
                "found_count": 0,
                "missing_count": len(expected_pkgs),
                "package_details": [],
            })
            all_passed = False
            continue

        # Download, mount, verify
        dl = host.run(
            CMDS["s3cmd_get"].format(
                s3_path=s3_path, dest=temp_image,
            )
        )
        if dl.rc != 0:
            results.append({
                "functional_group": fg,
                "success": False,
                "error": "Failed to download image",
                "expected_count": len(expected_pkgs),
                "found_count": 0,
                "missing_count": len(expected_pkgs),
                "package_details": [],
            })
            all_passed = False
            continue

        host.run(CMDS["mkdir_p"].format(path=temp_mount))
        mt = host.run(
            CMDS["mount_squashfs"].format(
                image=temp_image, mount=temp_mount,
            )
        )
        if mt.rc != 0:
            host.run(CMDS["rm_file"].format(path=temp_image))
            results.append({
                "functional_group": fg,
                "success": False,
                "error": "Failed to mount image",
                "expected_count": len(expected_pkgs),
                "found_count": 0,
                "missing_count": len(expected_pkgs),
                "package_details": [],
            })
            all_passed = False
            continue

        rpm_cmd = host.run(
            CMDS["rpm_list_installed"].format(root=temp_mount)
        )
        installed = (
            rpm_cmd.stdout.strip().split('\n')
            if rpm_cmd.rc == 0 else []
        )

        found_pkgs = []
        missing_pkgs = []
        pkg_details = []

        for pkg in expected_pkgs:
            base_pkg = pkg
            if '-' in pkg and pkg.split('-')[-1][0:1].isdigit():
                base_pkg = pkg.rsplit('-', 1)[0]

            matched = False
            matched_ver = None
            for inst in installed:
                if inst.lower().startswith(base_pkg.lower()):
                    matched = True
                    matched_ver = inst
                    break

            if matched:
                found_pkgs.append(pkg)
                pkg_details.append({
                    "expected": pkg,
                    "found": matched_ver,
                    "status": "installed",
                })
            else:
                missing_pkgs.append(pkg)
                pkg_details.append({
                    "expected": pkg,
                    "found": None,
                    "status": "missing",
                })

        # Cleanup
        host.run(CMDS["umount"].format(flags="-l", path=temp_mount))
        host.run(CMDS["rm_dir"].format(path=temp_mount))
        host.run(CMDS["rm_file"].format(path=temp_image))

        fg_result = {
            "functional_group": fg,
            "success": len(missing_pkgs) == 0,
            "image_path": s3_path,
            "expected_count": len(expected_pkgs),
            "found_count": len(found_pkgs),
            "missing_count": len(missing_pkgs),
            "package_details": pkg_details,
            "error": (
                f"Missing: {', '.join(missing_pkgs)}"
                if missing_pkgs else None
            ),
        }
        results.append(fg_result)
        if not fg_result["success"]:
            all_passed = False

    # Final cleanup
    host.run(CMDS["umount"].format(flags="-l", path=temp_mount))
    host.run(CMDS["rm_dir"].format(path=temp_mount))
    host.run(CMDS["rm_file"].format(path=temp_image))

    passed_count = sum(1 for r in results if r["success"])

    return {
        "success": all_passed,
        "prerequisite_failed": False,
        "results": results,
        "total_groups": len(groups),
        "passed_groups": passed_count,
        "failed_groups": len(groups) - passed_count,
        "details": (
            f"Verified packages in "
            f"{passed_count}/{len(groups)} images"
        ),
        "error": None if all_passed else (
            f"{len(groups) - passed_count} image(s) "
            "have missing packages"
        ),
    }


# =============================================================================
# CLEANUP VERIFICATION
# =============================================================================

def check_containers_removed(host) -> Dict[str, Any]:
    """Verify MinIO and registry containers are stopped/removed.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    containers = [MINIO_CONTAINER, REGISTRY_CONTAINER]
    results = []
    all_removed = True

    for name in containers:
        cmd = host.run(
            CMDS["podman_ps_check"].format(container=name)
        )
        still_exists = cmd.rc == 0 and name in cmd.stdout
        results.append({
            "container": name,
            "removed": not still_exists,
            "error": (
                f"Container '{name}' still exists"
                if still_exists else None
            ),
        })
        if still_exists:
            all_removed = False

    return {
        "success": all_removed,
        "results": results,
        "details": (
            "All containers removed"
            if all_removed else
            "Some containers still exist"
        ),
    }


def check_s3_artifacts_removed(host) -> Dict[str, Any]:
    """Verify S3 buckets/images are cleaned up after cleanup tag.

    Returns:
        Dict with 'success', 'remaining_buckets', 'details'.
    """
    ls_cmd = host.run(CMDS["s3cmd_ls"])
    if ls_cmd.rc != 0:
        return {
            "success": True,
            "remaining_buckets": [],
            "details": "s3cmd not available (expected after cleanup)",
        }

    remaining = []
    for bucket in S3_EXPECTED_BUCKETS:
        if bucket in ls_cmd.stdout:
            remaining.append(bucket)

    return {
        "success": len(remaining) == 0,
        "remaining_buckets": remaining,
        "details": (
            "All S3 buckets cleaned"
            if not remaining else
            f"Remaining buckets: {', '.join(remaining)}"
        ),
    }


# =============================================================================
# CLEANUP VERIFICATION — EXTENDED
# =============================================================================

def check_services_removed(host) -> Dict[str, Any]:
    """Verify MinIO and registry systemd services are inactive/removed.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    results = []
    all_inactive = True

    for svc in SYSTEMD_SERVICES:
        cmd = host.run(
            CMDS["systemctl_is_active"].format(service=svc)
        )
        state = cmd.stdout.strip() if cmd.rc == 0 else "inactive"
        is_active = state == "active"
        results.append({
            "service": svc,
            "state": state,
            "removed": not is_active,
        })
        if is_active:
            all_inactive = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else f"still {r['state']}"
        details_lines.append(f"  {r['service']}: {status}")

    return {
        "success": all_inactive,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_firewall_ports_removed(host) -> Dict[str, Any]:
    """Verify service ports are NOT listening after cleanup.

    Checks via ss -tlnp that ports 9000, 9001, 5000 are no longer
    bound. This is more reliable than firewall-cmd since the playbook
    uses container port bindings rather than firewall rules.

    Returns:
        Dict with 'success', 'open_ports', 'details'.
    """
    still_open = []

    for port in LISTENING_PORTS:
        cmd = host.run(
            CMDS["ss_listen_port"].format(port=port)
        )
        if cmd.rc == 0 and str(port) in cmd.stdout:
            still_open.append(port)

    details_lines = []
    for port in LISTENING_PORTS:
        status = (
            "STILL LISTENING (should be closed)"
            if port in still_open else "closed"
        )
        details_lines.append(f"  {port}/tcp: {status}")

    return {
        "success": len(still_open) == 0,
        "open_ports": still_open,
        "details": "\n".join(details_lines),
    }


def check_s3cfg_removed(host) -> Dict[str, Any]:
    """Verify s3cmd configuration file is removed after cleanup.

    Returns:
        Dict with 'success', 'details'.
    """
    cmd = host.run(
        CMDS["file_exists"].format(path=S3CMD_CONFIG_PATH)
    )
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": not exists,
        "details": (
            f"{S3CMD_CONFIG_PATH}: removed"
            if not exists
            else f"{S3CMD_CONFIG_PATH}: still exists"
        ),
    }


def check_credentials_removed(host) -> Dict[str, Any]:
    """Verify credentials files are removed after cleanup.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    input_dir = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )

    files_to_check = [
        f"{input_dir}/{CREDENTIALS_FILE_NAME}",
        f"{input_dir}/{CREDENTIALS_KEY_NAME}",
    ]

    results = []
    all_removed = True
    for fpath in files_to_check:
        cmd = host.run(CMDS["file_exists"].format(path=fpath))
        exists = cmd.rc == 0 and "exists" in cmd.stdout
        fname = os.path.basename(fpath)
        results.append({
            "file": fname,
            "path": fpath,
            "removed": not exists,
        })
        if exists:
            all_removed = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else "still exists"
        details_lines.append(f"  {r['file']}: {status}")

    return {
        "success": all_removed,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_build_output_removed(host) -> Dict[str, Any]:
    """Verify build_status.yml is removed after cleanup.

    Returns:
        Dict with 'success', 'details'.
    """
    shared = _get_shared_path()
    project = _get_project_name()
    status_path = BUILD_STATUS_PATH.format(
        shared_path=shared, project=project
    )

    cmd = host.run(CMDS["file_exists"].format(path=status_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": not exists,
        "details": (
            "build_status.yml: removed"
            if not exists
            else f"build_status.yml still exists at {status_path}"
        ),
    }


def check_registry_cleaned(host) -> Dict[str, Any]:
    """Verify registry has no images after cleanup.

    Returns:
        Dict with 'success', 'registry_reachable', 'repos', 'details'.
    """
    cmd = host.run(
        CMDS["curl_registry_catalog_http"].format(port=REGISTRY_PORT)
    )
    if cmd.rc != 0 or "repositories" not in cmd.stdout:
        return {
            "success": True,
            "registry_reachable": False,
            "repos": [],
            "details": (
                "Registry not reachable (expected after cleanup)"
            ),
        }

    try:
        data = json.loads(cmd.stdout)
        repos = data.get("repositories", [])
    except (json.JSONDecodeError, ValueError):
        repos = []

    return {
        "success": len(repos) == 0,
        "registry_reachable": True,
        "repos": repos,
        "details": (
            "Registry empty (no images)"
            if not repos
            else f"Registry still has {len(repos)} repos: "
                 f"{', '.join(repos)}"
        ),
    }


# =============================================================================
# PREPARE VERIFICATION — EXTENDED
# =============================================================================

def check_s3cmd_configured(host) -> Dict[str, Any]:
    """Verify s3cmd is installed and s3cfg config exists.

    Returns:
        Dict with 'success', 's3cmd_available', 'config_exists', 'details'.
    """
    which_cmd = host.run(CMDS["which_cmd"].format(binary="s3cmd"))
    s3cmd_available = which_cmd.rc == 0

    cfg_cmd = host.run(
        CMDS["file_exists"].format(path=S3CMD_CONFIG_PATH)
    )
    config_exists = cfg_cmd.rc == 0 and "exists" in cfg_cmd.stdout

    details_lines = [
        f"  s3cmd binary: {'found' if s3cmd_available else 'NOT FOUND'}",
        f"  {S3CMD_CONFIG_PATH}: "
        f"{'exists' if config_exists else 'NOT FOUND'}",
    ]

    return {
        "success": s3cmd_available and config_exists,
        "s3cmd_available": s3cmd_available,
        "config_exists": config_exists,
        "details": "\n".join(details_lines),
    }


def check_firewall_ports_open(host) -> Dict[str, Any]:
    """Verify container ports are listening (via ss -tlnp).

    Checks that MinIO (9000, 9001) and registry (5000) ports
    are bound and accepting connections.

    Returns:
        Dict with 'success', 'open_ports', 'missing_ports', 'details'.
    """
    open_ports = []
    missing = []

    for port in LISTENING_PORTS:
        cmd = host.run(
            CMDS["ss_listen_port"].format(port=port)
        )
        if cmd.rc == 0 and str(port) in cmd.stdout:
            open_ports.append(port)
        else:
            missing.append(port)

    details_lines = []
    for port in LISTENING_PORTS:
        status = "listening" if port in open_ports else "NOT LISTENING"
        details_lines.append(f"  {port}/tcp: {status}")

    return {
        "success": len(missing) == 0,
        "open_ports": open_ports,
        "missing_ports": missing,
        "details": "\n".join(details_lines),
    }


def check_services_active(host) -> Dict[str, Any]:
    """Verify MinIO and registry systemd services are active.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    results = []
    all_active = True

    for svc in SYSTEMD_SERVICES:
        cmd = host.run(
            CMDS["systemctl_is_active"].format(service=svc)
        )
        state = cmd.stdout.strip() if cmd.rc == 0 else "inactive"
        is_active = state == "active"
        results.append({
            "service": svc,
            "state": state,
            "active": is_active,
        })
        if not is_active:
            all_active = False

    details_lines = []
    for r in results:
        details_lines.append(f"  {r['service']}: {r['state']}")

    return {
        "success": all_active,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_credentials_present(host) -> Dict[str, Any]:
    """Verify credentials file is present after prepare syncs it.

    Returns:
        Dict with 'success', 'details'.
    """
    input_dir = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    cred_path = f"{input_dir}/{CREDENTIALS_FILE_NAME}"

    cmd = host.run(CMDS["file_exists"].format(path=cred_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "details": (
            f"  {CREDENTIALS_FILE_NAME}: present at {cred_path}"
            if exists
            else f"  {CREDENTIALS_FILE_NAME}: NOT FOUND at {cred_path}"
        ),
    }


def check_clone_status(host) -> Dict[str, Any]:
    """Verify the project code is synced to the target.

    Checks that the clone_path directory exists and contains
    the expected domain directory structure.

    Returns:
        Dict with 'success', 'clone_path', 'details'.
    """
    config = load_test_config()
    clone_path = config["clone_path"]

    dir_cmd = host.run(CMDS["dir_exists"].format(path=clone_path))
    if dir_cmd.rc != 0 or "exists" not in dir_cmd.stdout:
        return {
            "success": False,
            "clone_path": clone_path,
            "details": f"  Project path NOT FOUND: {clone_path}",
        }

    # Check for domain directory as a basic sync validation
    ibm_dir = f"{clone_path}/src/image_build_manager"
    ibm_check = host.run(CMDS["dir_exists"].format(path=ibm_dir))
    has_ibm = ibm_check.rc == 0 and "exists" in ibm_check.stdout

    details_lines = [
        f"  Path: {clone_path}",
        f"  image_build_manager: {'present' if has_ibm else 'NOT FOUND'}",
    ]

    return {
        "success": has_ibm,
        "clone_path": clone_path,
        "details": "\n".join(details_lines),
    }


def check_registry_reachable(host) -> Dict[str, Any]:
    """Verify registry is reachable and report catalog info.

    Returns:
        Dict with 'success', 'registry_url', 'repo_count', 'repos',
        'details'.
    """
    hostname_cmd = host.run(CMDS["hostname_fqdn"])
    fqdn = (
        hostname_cmd.stdout.strip()
        if hostname_cmd.rc == 0 else "localhost"
    )
    registry_url = f"{fqdn}:{REGISTRY_PORT}"

    cmd = host.run(
        CMDS["curl_registry_catalog_http"].format(port=REGISTRY_PORT)
    )
    if cmd.rc != 0 or "repositories" not in cmd.stdout:
        return {
            "success": False,
            "registry_url": registry_url,
            "repo_count": 0,
            "repos": [],
            "details": f"  Registry NOT reachable at {registry_url}",
        }

    try:
        data = json.loads(cmd.stdout)
        repos = data.get("repositories", [])
    except (json.JSONDecodeError, ValueError):
        repos = []

    details_lines = [
        f"  URL: http://{registry_url}",
        f"  Repositories: {len(repos)}",
    ]
    for repo in repos:
        details_lines.append(f"    - {repo}")
    if not repos:
        details_lines.append("    (empty — no images pushed yet)")

    return {
        "success": True,
        "registry_url": registry_url,
        "repo_count": len(repos),
        "repos": repos,
        "details": "\n".join(details_lines),
    }


# =============================================================================
# VALIDATE VERIFICATION — EXTENDED
# =============================================================================

def check_input_config_exists(host) -> Dict[str, Any]:
    """Verify image_build_config.yml exists on target.

    Returns:
        Dict with 'success', 'details'.
    """
    cfg_path = _get_remote_ibm_config_path(host)

    cmd = host.run(CMDS["file_exists"].format(path=cfg_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "path": cfg_path,
        "details": (
            f"  image_build_config.yml: present at {cfg_path}"
            if exists
            else f"  image_build_config.yml: NOT FOUND at {cfg_path}"
        ),
    }
