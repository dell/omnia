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

"""Image content verification (squashfs mount + RPM package check)."""

import json
import os
import uuid
from typing import Dict, Any, List

import yaml

from omnia_auto import read_remote_env

from ._config_helpers import (
    _configured_functional_groups_result,
    _load_remote_ibm_config,
)
from .s3_func import (
    _artifact_identity_error,
    _artifact_layout_result,
    _load_build_status_manifest,
    _manifest_path_to_s3_uri,
    check_s3_buckets,
)
from ..vars.common_vars import (
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    ENV_CATALOG_FILE_PATH,
    CMDS,
    DOMAIN_NAME,
    PACKAGE_GROUPS_FILENAME,
    IMAGE_VERIFY_TEMP_MOUNT,
    IMAGE_BUILD_TYPE_SUFFIXES,
    SQUASHFS_PACKAGE,
    S3_BOOT_IMAGES_BUCKET,
)


# =============================================================================
# IMAGE PACKAGE VERIFICATION (squashfs mount + RPM check)
# =============================================================================

def _new_image_verification_paths():
    """Return collision-safe target paths for one verification invocation."""
    temp_root = f"{IMAGE_VERIFY_TEMP_MOUNT}_{uuid.uuid4().hex}"
    return (
        temp_root,
        os.path.join(temp_root, "rootfs.squashfs"),
        os.path.join(temp_root, "rootfs"),
    )


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


def _get_packages_from_catalog(
    host, functional_group: str, arch: str
) -> List[str]:
    """Resolve expected packages from the catalog JSON on target.

    Follows the catalog resolution chain:
        functionallayer[name].components[]
        -> non-driver groups[comp].components[]
        -> architecture-matching packages[key].name

    Returns:
        List of RPM package names, or empty list if unavailable.
    """
    catalog_path = read_remote_env(host, ENV_CATALOG_FILE_PATH)
    if not catalog_path:
        return []

    cmd = host.run(CMDS["cat_file"].format(path=catalog_path))
    if cmd.rc != 0 or not cmd.stdout.strip():
        return []

    try:
        raw = json.loads(cmd.stdout)
    except (json.JSONDecodeError, ValueError):
        return []

    catalog = raw.get("catalog", raw)
    layers = catalog.get("functionallayer", [])
    groups = catalog.get("groups", {})
    packages = catalog.get("packages", {})

    # Find the matching functional layer
    target_layer = None
    for layer in layers:
        if layer.get("name") == functional_group:
            target_layer = layer
            break
    if not target_layer:
        return []

    # Resolve RPM packages through groups
    pkg_names: list[str] = []
    for comp_name in target_layer.get("components", []):
        # Keep validation aligned with parse_catalog: hardware driver groups
        # are installed after boot and are not baked into the OS image.
        if "driver_group" in comp_name:
            continue
        group = groups.get(comp_name, {})
        for pkg_key in group.get("components", []):
            pkg_data = packages.get(pkg_key, {})
            if pkg_data.get("packagetype", "") != "rpm":
                continue
            arch_match = any(
                source.get("architecture") == arch
                for source in pkg_data.get("sources", [])
            )
            if not arch_match:
                continue
            rpm_name = pkg_data.get("name", "")
            if rpm_name:
                pkg_names.append(rpm_name)

    return list(dict.fromkeys(pkg_names))


def _map_catalog_name_to_config_name(
    functional_group: str, os_type: str, os_version: str
) -> str:
    """Map catalog-mode group name to config-mode group name.

    Catalog names: ``{role}_{os}_{ver}_{arch}``
        (e.g. slurm_node_rhel_10_0_x86_64)
    Config names:  ``{role}_{arch}``
        (e.g. slurm_node_x86_64)

    Strips ``_{os}_{ver}`` from the name when present.
    """
    os_ver_underscored = os_version.replace(".", "_")
    os_suffix = f"_{os_type}_{os_ver_underscored}"
    if os_suffix in functional_group:
        return functional_group.replace(os_suffix, "")
    return functional_group


def _get_packages_from_package_groups(
    host, functional_group: str
) -> List[str]:
    """Get packages from package_groups.yml in the input directory.

    Falls back to config-mode name mapping when the exact
    functional group name is not found (catalog mode uses
    ``{role}_{os}_{ver}_{arch}`` while config mode uses
    ``{role}_{arch}``).
    """
    data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    pkg_path = (
        f"{data_path}/{DOMAIN_NAME}/input/{project}/"
        f"{PACKAGE_GROUPS_FILENAME}"
    )

    cmd = host.run(CMDS["cat_file"].format(path=pkg_path))
    if cmd.rc != 0 or not cmd.stdout.strip():
        return []
    try:
        data = yaml.safe_load(cmd.stdout)
    except yaml.YAMLError:
        return []

    base = data.get("base_packages", [])
    fg_data = data.get("functional_groups", {})
    if not isinstance(fg_data, dict):
        return list(dict.fromkeys(base)) if base else []

    # Try exact name first
    group_info = fg_data.get(functional_group, {})
    if not group_info or not isinstance(group_info, dict):
        # Try config-mode name mapping
        os_type = data.get("os", "")
        os_version = data.get("os_version", "")
        if os_type and os_version:
            config_name = _map_catalog_name_to_config_name(
                functional_group, os_type, os_version,
            )
            group_info = fg_data.get(config_name, {})
            if not isinstance(group_info, dict):
                group_info = {}

    fg_pkgs = group_info.get("packages", [])
    return list(dict.fromkeys(base + fg_pkgs))


def _get_image_packages_from_config(
    host, functional_group: str, arch: str
) -> List[str]:
    """Get expected packages for a functional group.

    Reads ``functional_groups_source`` from image_build_config.yml
    to determine the resolution mode:

    **catalog** mode:
        Resolve packages from catalog JSON (``CATALOG_FILE_PATH``
        env var) via the ``functionallayer -> groups -> packages``
        chain.

    **config** mode:
        Read packages from ``package_groups.yml`` in the
        image_build_manager input directory.

    Returns:
        Deduplicated list of RPM package names.
    """
    ibm_cfg = _load_remote_ibm_config(host)
    fg_source = ibm_cfg.get(
        "functional_groups_source", "config",
    )

    if fg_source == "catalog":
        return _get_packages_from_catalog(
            host, functional_group, arch,
        )

    # config mode
    return _get_packages_from_package_groups(
        host, functional_group,
    )


def _get_manifest_rootfs_uri(
    status_entries: Dict[str, Dict[str, Any]],
    status_bucket: str,
    functional_group: str,
    expected_suffix: str = "",
):
    """Return the exact rootfs URI declared for a functional group."""
    status_entry = status_entries.get(functional_group)
    if not isinstance(status_entry, dict):
        return "", (
            "functional group is missing from build_status.yml "
            "for the requested architecture"
        )

    rootfs_uri, path_error = _manifest_path_to_s3_uri(
        status_entry.get("image"), status_bucket,
    )
    if not path_error:
        path_error = _artifact_identity_error(
            "image", rootfs_uri, status_bucket, functional_group,
        )
    if not path_error and expected_suffix:
        _cohort, path_error = _artifact_layout_result(
            "image", rootfs_uri, status_bucket, functional_group,
            expected_suffix,
        )
    return rootfs_uri, path_error


def verify_image_packages(
    host, arch: str = "x86_64"
) -> Dict[str, Any]:
    """Download exact build-status rootfs objects and verify RPM packages.

    Resolves each functional group's ``image`` field from build_status.yml,
    validates its bucket, group, and engine layout, then downloads that exact
    S3 object. Performs a fast bucket pre-check before image downloads.

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

    expected = _configured_functional_groups_result(host, arch=arch)
    if not expected["success"]:
        expected_error = expected.get("error") or (
            f"Unable to resolve configured {arch} functional groups"
        )
        return {
            "success": False,
            "prerequisite_failed": True,
            "results": [],
            "details": expected_error,
            "error": expected_error,
        }

    groups = expected["groups"]
    if not groups:
        return {
            "success": True,
            "prerequisite_failed": False,
            "results": [],
            "details": expected.get(
                "details", f"No {arch} functional groups configured",
            ),
        }

    status_entries, status_bucket, manifest_build_type, status_error = (
        _load_build_status_manifest(host, arch)
    )
    if status_error:
        return {
            "success": False,
            "prerequisite_failed": True,
            "results": [],
            "details": status_error,
            "error": status_error,
        }
    expected_suffix = IMAGE_BUILD_TYPE_SUFFIXES[manifest_build_type]

    temp_root, temp_image, temp_mount = _new_image_verification_paths()

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

    results = []
    all_passed = True
    cleanup_error = None

    try:
        # Every invocation gets its own target paths so concurrent validation
        # runs cannot unmount, truncate, or remove each other's working image.
        # Keep setup in this block so partial setup is also cleaned on errors.
        host.run(CMDS["mkdir_p"].format(path=temp_mount))

        for fg in groups:
            expected_pkgs = _get_image_packages_from_config(host, fg, arch)
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

            s3_path, path_error = _get_manifest_rootfs_uri(
                status_entries, status_bucket, fg, expected_suffix,
            )
            if path_error:
                results.append({
                    "functional_group": fg,
                    "success": False,
                    "error": (
                        "Invalid build_status.yml rootfs path: "
                        f"{path_error}"
                    ),
                    "image_path": s3_path or None,
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
                host.run(CMDS["rm_file"].format(path=temp_image))
                results.append({
                    "functional_group": fg,
                    "success": False,
                    "error": (
                        "Failed to download exact build_status.yml "
                        f"rootfs {s3_path} (rc={dl.rc})"
                    ),
                    "image_path": s3_path,
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
                host.run(CMDS["umount"].format(
                    flags="-l", path=temp_mount,
                ))
                host.run(CMDS["rm_dir"].format(path=temp_mount))
                host.run(CMDS["rm_file"].format(path=temp_image))
                results.append({
                    "functional_group": fg,
                    "success": False,
                    "error": f"Failed to mount image (rc={mt.rc})",
                    "image_path": s3_path,
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
            if rpm_cmd.rc != 0 or not rpm_cmd.stdout.strip():
                host.run(CMDS["umount"].format(
                    flags="-l", path=temp_mount,
                ))
                host.run(CMDS["rm_dir"].format(path=temp_mount))
                host.run(CMDS["rm_file"].format(path=temp_image))
                results.append({
                    "functional_group": fg,
                    "success": False,
                    "error": (
                        "Failed to query mounted image RPM database "
                        f"(rc={rpm_cmd.rc})"
                    ),
                    "image_path": s3_path,
                    "expected_count": len(expected_pkgs),
                    "found_count": 0,
                    "missing_count": len(expected_pkgs),
                    "package_details": [],
                })
                all_passed = False
                continue

            installed = rpm_cmd.stdout.strip().split('\n')

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

            # Per-group cleanup
            host.run(CMDS["umount"].format(
                flags="-l", path=temp_mount,
            ))
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

    finally:
        # Guaranteed cleanup — runs even if an exception occurs
        try:
            host.run(CMDS["umount"].format(
                flags="-l", path=temp_mount,
            ))
        finally:
            cleanup = host.run(
                CMDS["rm_dir"].format(path=temp_root)
            )
            if cleanup.rc != 0:
                cleanup_error = (
                    "Failed to remove temporary image verification "
                    f"workspace {temp_root} (rc={cleanup.rc})"
                )

    passed_count = sum(1 for r in results if r["success"])
    verification_success = all_passed and cleanup_error is None

    return {
        "success": verification_success,
        "prerequisite_failed": False,
        "results": results,
        "total_groups": len(groups),
        "passed_groups": passed_count,
        "failed_groups": len(groups) - passed_count,
        "details": (
            f"Verified packages in "
            f"{passed_count}/{len(groups)} images"
        ),
        "error": cleanup_error or (
            None if all_passed else (
                f"{len(groups) - passed_count} image(s) "
                "have missing packages"
            )
        ),
    }
