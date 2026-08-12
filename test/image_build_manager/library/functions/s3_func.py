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

"""S3 bucket and image verification functions."""

from typing import Dict, Any

from ._config_helpers import (
    _retry_run,
    get_configured_functional_groups,
)
from ..vars.common_vars import (
    CMDS,
    S3_EXPECTED_BUCKETS,
    S3_BOOT_IMAGES_BUCKET,
    IMAGE_TYPES,
    IMAGE_TYPE_DISPLAY,
)


# =============================================================================
# S3 BUCKET VERIFICATION
# =============================================================================

def check_s3_buckets(host) -> Dict[str, Any]:
    """Verify required S3 buckets exist.

    Returns:
        Dict with 'success', 'found', 'missing', 'details'.
    """
    ls_cmd = _retry_run(host, CMDS["s3cmd_ls"])
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
    if s3_cmd.rc != 0:
        return {
            "success": False,
            "skipped": False,
            "results": [],
            "details": "",
            "error": (
                f"s3cmd ls -Hr {S3_BOOT_IMAGES_BUCKET} failed "
                f"(rc={s3_cmd.rc})"
            ),
        }

    s3_files = _parse_s3_listing(s3_cmd.stdout)

    results = []
    all_passed = True

    for fg in groups:
        group_files = {
            path: info for path, info in s3_files.items()
            if fg in path
        }

        found_images = []
        missing_images = []

        for img_type, suffixes in IMAGE_TYPES.items():
            found = False
            matched_path = None
            matched_size = 0

            for path, info in group_files.items():
                fname = info["filename"]
                for suffix in suffixes:
                    if fname.endswith(suffix) or suffix in fname:
                        found = True
                        matched_path = path
                        matched_size = info["size"]
                        break
                if found:
                    break

            display = IMAGE_TYPE_DISPLAY.get(img_type, img_type)
            if found:
                found_images.append({
                    "type": display,
                    "path": matched_path,
                    "size": _format_size(matched_size),
                })
            else:
                missing_images.append(display)

        group_result = {
            "functional_group": fg,
            "success": len(missing_images) == 0,
            "found_images": found_images,
            "missing_images": missing_images,
        }
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
