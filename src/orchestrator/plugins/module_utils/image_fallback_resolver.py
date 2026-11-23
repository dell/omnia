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
Image Build Manager Fallback Contract Resolver for Orchestrator.

Resolves kernel, initrd, and rootfs (image) fallback metadata from Image Build
Manager's build_status.yml output for functional groups that lack an explicit
image_override in their configuration (ER-ORCH-009 / FR-3.1 / AC-004 / AC-008).
"""

from typing import Any, Dict, List, Tuple


def extract_architecture_entries(
    build_status_data: Dict[str, Any], arch: str
) -> List[Dict[str, Any]]:
    """Extract image entries matching the target architecture from build status.

    Supports both nested architecture blocks ([{x86_64: [...]}, {aarch64: [...]}])
    and flat functional_group list structures.

    Args:
        build_status_data: Parsed build_status.yml content.
        arch: Target architecture (e.g. 'x86_64', 'aarch64').

    Returns:
        List of image dictionary entries for the given architecture.
    """
    entries = []
    fg_images = build_status_data.get("functional_group_images", [])
    if not isinstance(fg_images, list):
        return entries

    for item in fg_images:
        if not isinstance(item, dict):
            continue
        if arch in item and isinstance(item[arch], list):
            entries.extend(
                e for e in item[arch] if isinstance(e, dict)
            )
        elif "functional_group" in item:
            # Flat format: check explicit architecture or suffix
            item_arch = item.get("architecture")
            fg_name = item.get("functional_group", "")
            if item_arch == arch or fg_name.endswith(f"_{arch}"):
                entries.append(item)

    return entries


def resolve_boot_image_fallback(
    build_status_data: Dict[str, Any],
    functional_group_name: str,
    arch: str,
) -> Tuple[bool, Dict[str, str], str]:
    """Resolve and validate boot image fallback artifacts for a functional group.

    Enforces FR-3.1 fallback contract rules:
    - Overall status must be 'success'
    - S3 configurations must contain a non-empty endpoint_url
    - Entry must be associated with the requested architecture
    - Entry must match the exact functional group identity
    - Artifact triple (kernel, initrd, image/rootfs) must be complete and non-empty
    - Metadata must not be ambiguous (conflicting duplicate artifact entries)

    Args:
        build_status_data: Parsed build_status.yml dictionary.
        functional_group_name: Target functional group identity.
        arch: Target architecture ('x86_64' or 'aarch64').

    Returns:
        Tuple of (is_usable, artifact_dict, rejection_reason).
        When usable, artifact_dict contains 'kernel', 'initrd', 'rootfs', and 'endpoint'.
    """
    if not build_status_data:
        return False, {}, "build_status data is empty or missing"

    overall_status = build_status_data.get("overall_status", "")
    if overall_status != "success":
        return (
            False,
            {},
            f"build_status.yml reports overall_status='{overall_status}'; expected 'success'",
        )

    s3_config = build_status_data.get("s3_configurations", {})
    if not isinstance(s3_config, dict):
        return False, {}, "Missing or invalid s3_configurations in build_status.yml"

    endpoint = s3_config.get("endpoint_url", "").strip()
    if not endpoint:
        return (
            False,
            {},
            "Missing or empty s3_configurations.endpoint_url in build_status.yml",
        )

    arch_entries = extract_architecture_entries(build_status_data, arch)
    if not arch_entries:
        return (
            False,
            {},
            f"No image entries found for architecture '{arch}' in build_status.yml",
        )

    matching = [
        e for e in arch_entries if e.get("functional_group") == functional_group_name
    ]
    if not matching:
        return (
            False,
            {},
            f"No image entry found for '{functional_group_name}' under architecture '{arch}'",
        )

    if len(matching) > 1:
        distinct = {
            (e.get("kernel"), e.get("initrd"), e.get("image")) for e in matching
        }
        if len(distinct) > 1:
            return (
                False,
                {},
                f"Ambiguous fallback metadata: multiple conflicting artifact entries "
                f"for '{functional_group_name}' under '{arch}'",
            )

    entry = matching[0]
    kernel = str(entry.get("kernel") or "").strip()
    initrd = str(entry.get("initrd") or "").strip()
    image = str(entry.get("image") or "").strip()

    if not kernel:
        return (
            False,
            {},
            f"Incomplete fallback contract for '{functional_group_name}': "
            "missing or empty 'kernel'",
        )
    if not initrd:
        return (
            False,
            {},
            f"Incomplete fallback contract for '{functional_group_name}': "
            "missing or empty 'initrd'",
        )
    if not image:
        return (
            False,
            {},
            f"Incomplete fallback contract for '{functional_group_name}': "
            "missing or empty 'image' (rootfs)",
        )

    artifacts = {
        "kernel": kernel,
        "initrd": initrd,
        "rootfs": image,
        "endpoint": endpoint,
        "bucket": s3_config.get("bucket", "boot-images"),
    }
    return True, artifacts, ""
