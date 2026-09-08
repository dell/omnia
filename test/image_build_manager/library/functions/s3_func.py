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
    _configured_functional_groups_result,
    _retry_run,
)
from .build_status_func import check_build_status_file
from ..vars.common_vars import (
    CMDS,
    IMAGE_BUILD_TYPE_SUFFIXES,
    S3_EXPECTED_BUCKETS,
    S3_BOOT_IMAGES_BUCKET,
)


_BUILD_STATUS_ARTIFACTS = (
    ("initrd", "initramfs"),
    ("kernel", "vmlinuz"),
    ("image", "rootfs"),
)

_THRILLHOUSE_FILENAMES = {
    "kernel": "vmlinuz",
    "initrd": "initramfs.img",
    "image": "rootfs.squashfs",
}


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
    available_buckets = {
        parts[-1].rstrip("/")
        for line in output.splitlines()
        if (parts := line.split()) and parts[-1].startswith("s3://")
    }
    found = []
    missing = []
    for bucket in S3_EXPECTED_BUCKETS:
        if bucket.rstrip("/") in available_buckets:
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


def _get_arch_build_status_entries(
    status_data: Dict[str, Any], arch: str
) -> Dict[str, Dict[str, Any]]:
    """Return validated build-status image entries for one architecture."""
    arch_blocks = status_data.get("functional_group_images", [])
    if not isinstance(arch_blocks, list):
        raise ValueError("functional_group_images must be a list")

    entries = {}
    for block_index, arch_block in enumerate(arch_blocks):
        if not isinstance(arch_block, dict):
            raise ValueError(
                "functional_group_images"
                f"[{block_index}] must be a mapping"
            )
        if arch not in arch_block:
            continue
        arch_entries = arch_block.get(arch, [])
        if not isinstance(arch_entries, list):
            raise ValueError(f"functional_group_images.{arch} must be a list")
        for entry_index, entry in enumerate(arch_entries):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"functional_group_images.{arch}[{entry_index}] "
                    "must be a mapping"
                )
            functional_group = entry.get("functional_group", "")
            if (
                not isinstance(functional_group, str)
                or not functional_group
                or functional_group != functional_group.strip()
            ):
                raise ValueError(
                    f"functional_group_images.{arch}[{entry_index}] "
                    "has an invalid functional_group"
                )
            if not functional_group.endswith(f"_{arch}"):
                raise ValueError(
                    f"Functional group '{functional_group}' is under {arch} "
                    f"but does not end with '_{arch}'"
                )
            if functional_group in entries:
                raise ValueError(
                    f"Duplicate {arch} build_status entry for "
                    f"functional group '{functional_group}'"
                )
            entries[functional_group] = entry
    return entries


def _get_status_bucket(status_data: Dict[str, Any]) -> str:
    """Return the bucket name declared by build_status.yml."""
    s3_config = status_data.get("s3_configurations", {})
    if not isinstance(s3_config, dict):
        s3_config = {}
    bucket = s3_config.get("bucket", S3_BOOT_IMAGES_BUCKET)
    if not isinstance(bucket, str) or not bucket.strip():
        bucket = S3_BOOT_IMAGES_BUCKET
    bucket = bucket.strip()
    if bucket.startswith("s3://"):
        bucket = bucket[len("s3://"):]
    return bucket.strip("/")


def _manifest_path_to_s3_uri(path: Any, bucket: str):
    """Validate an endpoint-relative manifest path and return its S3 URI."""
    if not isinstance(path, str) or not path.strip():
        return "", "path is missing from build_status.yml"

    value = path.strip()
    if value.startswith("s3://"):
        return "", "path must be endpoint-relative, not an s3:// URI"
    if value.startswith("/"):
        return "", "path must not start with '/'"
    if value.endswith("/"):
        return "", "path points to a directory, not an exact object"
    if not value.startswith(f"{bucket}/"):
        return "", f"path must start with '{bucket}/'"
    return f"s3://{value}", ""


def _load_build_status_manifest(host, arch: str):
    """Load exact artifact paths and producing engine for an architecture."""
    status = check_build_status_file(host)
    status_data = status.get("data")
    if not status.get("success") or not isinstance(status_data, dict):
        error = (
            status.get("error")
            or "build_status.yml is unavailable or invalid"
        )
        return {}, "", "", error
    status_bucket = _get_status_bucket(status_data)
    expected_bucket = S3_BOOT_IMAGES_BUCKET.removeprefix("s3://").strip("/")
    if status_bucket != expected_bucket:
        return {}, status_bucket, "", (
            f"build_status.yml bucket is '{status_bucket}', expected fixed "
            f"bucket '{expected_bucket}'"
        )

    try:
        entries = _get_arch_build_status_entries(status_data, arch)
    except ValueError as exc:
        return {}, status_bucket, "", f"Invalid build_status.yml: {exc}"
    return entries, status_bucket, status["image_build_type"], ""


def _artifact_identity_error(
    field, s3_uri, status_bucket, functional_group
):
    """Validate artifact type and exact functional-group scope."""
    group_prefix = f"s3://{status_bucket}/{functional_group}/"
    efi_prefix = (
        f"s3://{status_bucket}/efi-images/{functional_group}/"
    )

    if field == "image":
        if not s3_uri.startswith(group_prefix):
            return f"rootfs path must be under '{group_prefix}'"
    elif not s3_uri.startswith((group_prefix, efi_prefix)):
        return (
            f"{field} path must be under '{group_prefix}' or "
            f"'{efi_prefix}'"
        )

    filename = s3_uri.rsplit("/", 1)[-1]
    if field == "kernel" and not filename.startswith("vmlinuz"):
        return "kernel filename must start with 'vmlinuz'"
    if field == "initrd" and not filename.startswith("initramfs"):
        return "initrd filename must start with 'initramfs'"
    if field == "image" and not (
        filename.startswith("rhel") or filename == "rootfs.squashfs"
    ):
        return "rootfs filename must be 'rootfs.squashfs' or start with 'rhel'"
    return ""


def _artifact_engine_error(
    s3_uri, status_bucket, functional_group, expected_suffix
):
    """Verify the image directory belongs to the recorded build engine."""
    if not expected_suffix:
        return ""

    prefixes = (
        f"s3://{status_bucket}/{functional_group}/",
        f"s3://{status_bucket}/efi-images/{functional_group}/",
    )
    relative_path = ""
    for prefix in prefixes:
        if s3_uri.startswith(prefix):
            relative_path = s3_uri[len(prefix):]
            break
    image_directory = relative_path.split("/", 1)[0]
    if not image_directory.endswith(expected_suffix):
        return (
            f"image directory '{image_directory or '<missing>'}' must end "
            f"with recorded builder suffix '{expected_suffix}'"
        )
    return ""


def _artifact_layout_result(
    field, s3_uri, status_bucket, functional_group, expected_suffix,
):
    """Validate the engine layout and return its artifact cohort."""
    group_prefix = f"s3://{status_bucket}/{functional_group}/"
    efi_prefix = (
        f"s3://{status_bucket}/efi-images/{functional_group}/"
    )

    if expected_suffix == IMAGE_BUILD_TYPE_SUFFIXES["image-builder"]:
        expected_prefix = (
            efi_prefix if field in ("kernel", "initrd") else group_prefix
        )
        if not s3_uri.startswith(expected_prefix):
            location = (
                "efi-images"
                if field in ("kernel", "initrd")
                else "functional-group"
            )
            return "", (
                f"image-builder {field} must use the {location} path "
                f"'{expected_prefix}'"
            )

        relative = s3_uri[len(expected_prefix):]
        parts = relative.split("/")
        if len(parts) != 2 or not all(parts):
            return "", (
                f"image-builder {field} path must contain exactly an "
                "image directory and filename"
            )
        image_directory, filename = parts
        if not image_directory.endswith(expected_suffix):
            return "", (
                f"image directory '{image_directory}' must end with "
                f"recorded builder suffix '{expected_suffix}'"
            )
        if field == "image" and not filename.startswith("rhel"):
            return "", (
                "image-builder rootfs filename must start with 'rhel'"
            )
        return image_directory, ""

    if expected_suffix == IMAGE_BUILD_TYPE_SUFFIXES["image-thrillhouse"]:
        if not s3_uri.startswith(group_prefix):
            return "", (
                f"image-thrillhouse {field} must use the "
                f"functional-group path '{group_prefix}'"
            )

        relative = s3_uri[len(group_prefix):]
        parts = relative.split("/")
        if len(parts) != 3 or not all(parts):
            return "", (
                f"image-thrillhouse {field} path must contain exactly an "
                "image directory, release, and filename"
            )
        image_directory, release, filename = parts
        if not image_directory.endswith(expected_suffix):
            return "", (
                f"image directory '{image_directory}' must end with "
                f"recorded builder suffix '{expected_suffix}'"
            )
        expected_filename = _THRILLHOUSE_FILENAMES[field]
        if filename != expected_filename:
            return "", (
                f"image-thrillhouse {field} filename must be "
                f"'{expected_filename}'"
            )
        return f"{image_directory}/{release}", ""

    return "", _artifact_engine_error(
        s3_uri, status_bucket, functional_group, expected_suffix,
    )


def _artifact_records(
    status_entry, status_bucket, functional_group, expected_suffix,
):
    """Build validated manifest records and enforce one artifact cohort."""
    records = []
    for field, display in _BUILD_STATUS_ARTIFACTS:
        manifest_path = status_entry.get(field, "")
        expected_uri, path_error = _manifest_path_to_s3_uri(
            manifest_path, status_bucket,
        )
        if not path_error:
            path_error = _artifact_identity_error(
                field, expected_uri, status_bucket, functional_group,
            )

        cohort = ""
        if not path_error:
            cohort, path_error = _artifact_layout_result(
                field, expected_uri, status_bucket, functional_group,
                expected_suffix,
            )
        records.append({
            "field": field,
            "display": display,
            "manifest_path": manifest_path,
            "expected_uri": expected_uri,
            "cohort": cohort,
            "error": path_error,
        })

    valid_records = [record for record in records if not record["error"]]
    rootfs_record = next(
        (
            record for record in valid_records
            if record["field"] == "image"
        ),
        None,
    )
    cohort_anchor = (
        rootfs_record["cohort"]
        if rootfs_record else (
            valid_records[0]["cohort"] if valid_records else ""
        )
    )
    anchor_field = "rootfs" if rootfs_record else (
        valid_records[0]["display"] if valid_records else "artifact"
    )
    for record in valid_records:
        if record["cohort"] != cohort_anchor:
            record["error"] = (
                f"artifact cohort '{record['cohort']}' does not match "
                f"{anchor_field} cohort '{cohort_anchor}'"
            )
    return records


def _check_group_artifacts(
    functional_group, status_entry, s3_files, status_bucket,
    expected_suffix="",
):
    """Compare one functional group's manifest paths with S3 objects."""
    found_images = []
    missing_images = []
    missing_artifacts = []
    records = _artifact_records(
        status_entry, status_bucket, functional_group, expected_suffix,
    )
    seen_uris = set()
    for record in records:
        expected_uri = record["expected_uri"]
        path_error = record["error"]
        if expected_uri:
            if expected_uri in seen_uris:
                path_error = "path duplicates another artifact field"
            else:
                seen_uris.add(expected_uri)
        object_info = s3_files.get(expected_uri)
        object_size = (
            object_info.get("size", 0)
            if isinstance(object_info, dict) else 0
        )
        if (
            not path_error
            and object_info is not None
            and (not isinstance(object_size, (int, float)) or object_size <= 0)
        ):
            path_error = "exact object is empty (size must be greater than zero)"

        if not path_error and object_info is not None:
            found_images.append({
                "type": record["display"],
                "path": expected_uri,
                "size": _format_size(object_size),
            })
        else:
            missing_images.append(record["display"])
            missing_artifacts.append({
                "type": record["display"],
                "path": record["manifest_path"],
                "reason": path_error or "exact object not found in S3",
            })
    return found_images, missing_images, missing_artifacts


def _format_missing_artifacts(failed_results):
    """Format missing exact-object diagnostics by functional group."""
    error_parts = []
    for group_result in failed_results:
        functional_group = group_result["functional_group"]
        for artifact in group_result["missing_artifacts"]:
            manifest_path = artifact["path"] or "<not set>"
            error_parts.append(
                f"{functional_group}: {artifact['type']} "
                f"({manifest_path}) - {artifact['reason']}"
            )
    return "\n".join(error_parts)


def _check_manifest_groups(
    groups, status_entries, s3_files, status_bucket, expected_suffix=""
):
    """Build verification results for every configured functional group."""
    results = []
    for functional_group in groups:
        status_entry = status_entries.get(functional_group, {})
        found, missing, missing_artifacts = _check_group_artifacts(
            functional_group, status_entry, s3_files, status_bucket,
            expected_suffix,
        )
        results.append({
            "functional_group": functional_group,
            "success": len(missing) == 0,
            "found_images": found,
            "missing_images": missing,
            "missing_artifacts": missing_artifacts,
        })
    return results


def _unexpected_status_results(unexpected_groups):
    """Represent stale build-status entries as failed group results."""
    return [
        {
            "functional_group": functional_group,
            "success": False,
            "found_images": [],
            "missing_images": ["manifest entry"],
            "missing_artifacts": [{
                "type": "manifest entry",
                "path": functional_group,
                "reason": (
                    "unexpected stale functional group is not present in "
                    "the current configured input"
                ),
            }],
        }
        for functional_group in unexpected_groups
    ]


def check_s3_bucket_images(
    host, arch: str = "x86_64"
) -> Dict[str, Any]:
    """Verify exact build-status image objects exist in S3.

    Performs fast pre-check of S3 bucket existence before attempting
    expensive recursive listing. Config/catalog input defines the expected
    group set, while build_status.yml defines each exact object path. This
    supports image-builder's versioned filenames and image-thrillhouse's
    fixed filenames without fuzzy matching.

    Args:
        host: testinfra host object
        arch: Architecture filter (x86_64 or aarch64)

    Returns:
        Dict with 'success', 'results', 'details', 'error'.
        Returns success=False immediately if S3 bucket doesn't exist.
    """
    expected = _configured_functional_groups_result(host, arch=arch)
    if not expected["success"]:
        expected_error = expected.get("error") or (
            f"Unable to resolve configured {arch} functional groups"
        )
        return {
            "success": False,
            "skipped": False,
            "prerequisite_failed": True,
            "results": [],
            "details": expected_error,
            "error": expected_error,
        }

    if expected.get("skipped"):
        return {
            "success": True,
            "skipped": True,
            "results": [],
            "details": expected["details"],
            "error": None,
        }

    groups = expected["groups"]
    if not groups:
        no_groups_error = (
            f"No {arch} functional groups resolved from "
            f"{expected.get('source', 'configured')} input"
        )
        return {
            "success": False,
            "skipped": False,
            "prerequisite_failed": True,
            "results": [],
            "details": no_groups_error,
            "error": no_groups_error,
        }

    status_entries, status_bucket, manifest_build_type, status_error = (
        _load_build_status_manifest(host, arch)
    )
    if status_error:
        return {
            "success": False,
            "skipped": False,
            "prerequisite_failed": True,
            "results": [],
            "details": status_error,
            "error": status_error,
        }

    configured_build_type = expected["image_build_type"]
    expected_suffix = IMAGE_BUILD_TYPE_SUFFIXES[manifest_build_type]
    build_type_mismatch = configured_build_type != manifest_build_type
    missing_status_groups = [
        group for group in groups if group not in status_entries
    ]
    configured_groups = set(groups)
    unexpected_status_groups = [
        group for group in status_entries if group not in configured_groups
    ]
    if missing_status_groups or unexpected_status_groups:
        missing_results = _check_manifest_groups(
            missing_status_groups, status_entries, {}, status_bucket,
            expected_suffix,
        )
        mismatch_results = missing_results + _unexpected_status_results(
            unexpected_status_groups,
        )
        mismatch_details = []
        if missing_status_groups:
            mismatch_details.append(
                f"missing {len(missing_status_groups)} expected group(s)"
            )
        if unexpected_status_groups:
            mismatch_details.append(
                f"contains {len(unexpected_status_groups)} unexpected "
                "stale group(s)"
            )
        return {
            "success": False,
            "skipped": False,
            "prerequisite_failed": False,
            "results": mismatch_results,
            "details": (
                "build_status.yml " + " and ".join(mismatch_details)
                + f" for {arch}"
            ),
            "error": _format_missing_artifacts(mismatch_results),
            "image_build_type": manifest_build_type,
            "configured_image_build_type": configured_build_type,
            "image_build_type_mismatch": build_type_mismatch,
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

    results = _check_manifest_groups(
        groups, status_entries, s3_files, status_bucket,
        expected_suffix,
    )

    failed = [result for result in results if not result["success"]]
    total = len(groups)
    passed = total - len(failed)

    if not failed:
        return {
            "success": True,
            "skipped": False,
            "results": results,
            "details": (
                f"All 3 images found for all {total} "
                f"{arch} functional groups"
            ),
            "error": None,
            "image_build_type": manifest_build_type,
            "configured_image_build_type": configured_build_type,
            "image_build_type_mismatch": build_type_mismatch,
        }

    return {
        "success": False,
        "skipped": False,
        "results": results,
        "details": (
            f"{passed}/{total} functional groups "
            "have all images"
        ),
        "error": _format_missing_artifacts(failed),
        "image_build_type": manifest_build_type,
        "configured_image_build_type": configured_build_type,
        "image_build_type_mismatch": build_type_mismatch,
    }
