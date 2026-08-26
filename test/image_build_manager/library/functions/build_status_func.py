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

"""Build status and functional group verification."""

from typing import Dict, Any, List

import yaml

from ._config_helpers import (
    _get_shared_path,
    _get_project_name,
    get_configured_functional_groups,
)
from ..vars.common_vars import CMDS, S3_BOOT_IMAGES_BUCKET


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
# BUILD STATUS ↔ S3 IMAGE PATH CROSS-REFERENCE
# =============================================================================

def check_build_status_s3_match(host) -> Dict[str, Any]:
    """Verify build_status.yml image paths exist in S3.

    Reads the ``image`` field from each functional group entry in
    build_status.yml and checks that the corresponding path exists
    in the S3 boot-images bucket listing.

    Returns:
        Dict with 'success', 'matched', 'unmatched', 'details'.
    """
    status = check_build_status_file(host)
    if not status.get("success") or "data" not in status:
        return {
            "success": False,
            "prerequisite_failed": True,
            "matched": [],
            "unmatched": [],
            "details": status.get(
                "error", "build_status.yml not available"
            ),
            "error": status.get(
                "error", "build_status.yml not available"
            ),
        }

    # Collect image paths from build_status.yml
    image_entries: List[Dict[str, str]] = []
    fg_images = status["data"].get(
        "functional_group_images", []
    )
    for arch_block in fg_images:
        if not isinstance(arch_block, dict):
            continue
        for arch_name, entries in arch_block.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                fg_name = entry.get("functional_group", "")
                image_path = entry.get("image", "")
                if fg_name and image_path:
                    image_entries.append({
                        "functional_group": fg_name,
                        "arch": arch_name,
                        "image_path": image_path,
                    })

    if not image_entries:
        return {
            "success": False,
            "prerequisite_failed": False,
            "matched": [],
            "unmatched": [],
            "details": (
                "No image entries in build_status.yml"
            ),
            "error": "No functional_group_images found",
        }

    # Get S3 listing
    s3_list = host.run(
        CMDS["s3cmd_ls_bucket"].format(
            bucket=S3_BOOT_IMAGES_BUCKET,
        )
    )
    s3_output = s3_list.stdout if s3_list.rc == 0 else ""

    matched = []
    unmatched = []

    for entry in image_entries:
        image_path = entry["image_path"]
        # build_status uses relative paths like
        # "boot-images/fg_name/rhel-fg_name_..."
        # S3 listing uses "s3://boot-images/fg_name/..."
        # Strip leading "boot-images/" for comparison
        search_path = image_path
        if search_path.startswith("boot-images/"):
            search_path = search_path[len("boot-images/"):]

        if search_path in s3_output:
            matched.append({
                "functional_group": entry[
                    "functional_group"
                ],
                "image_path": image_path,
                "status": "found",
            })
        else:
            unmatched.append({
                "functional_group": entry[
                    "functional_group"
                ],
                "image_path": image_path,
                "status": "not_found",
            })

    return {
        "success": len(unmatched) == 0,
        "prerequisite_failed": False,
        "matched": matched,
        "unmatched": unmatched,
        "total": len(image_entries),
        "details": (
            f"{len(matched)}/{len(image_entries)} "
            "image paths verified in S3"
        ),
        "error": None if not unmatched else (
            f"{len(unmatched)} image path(s) not found in S3"
        ),
    }
