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

import os
from typing import Dict, Any, List

import yaml

from omnia_auto import read_remote_env

from ._config_helpers import (
    _load_remote_ibm_config,
    get_configured_functional_groups,
)
from .s3_func import check_s3_buckets
from ..vars.common_vars import (
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    CMDS,
    FG_PACKAGES_FILENAME,
    IMAGE_VERIFY_TEMP_IMAGE,
    IMAGE_VERIFY_TEMP_MOUNT,
    SQUASHFS_PACKAGE,
    S3_BOOT_IMAGES_BUCKET,
)


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

    try:
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
        host.run(CMDS["umount"].format(
            flags="-l", path=temp_mount,
        ))
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
