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
"""Kernel-parameter, image-override, and naming rules for functional groups."""

from __future__ import annotations

import re
from logging import Logger
from typing import Any

from ..messages import orchestrator_messages as msg

#: Platform-managed boot, network, console, data-source, and security kernel
#: parameters (ER-ORCH-009 FR-2.2). A functional group cannot set them: the
#: kernel honors the last occurrence, so an appended value would override the
#: platform value in the boot-service template.
PROTECTED_KERNEL_PARAMS = frozenset(
    {
        "root",
        "ip",
        "ip6",
        "rd.live.image",
        "rd.live.ram",
        "rd.neednet",
        "console",
        "ds",
        "selinux",
        "apparmor",
        "netroot",
        "bootdev",
        "initrd",
        "BOOT_IMAGE",
        "inst.repo",
        "inst.stage2",
    }
)

#: One kernel parameter: ``key`` or ``key=value`` with a conservative value
#: alphabet. Quotes, backslashes, and control characters would break the
#: double-quoted boot-service ``params`` scalar.
KERNEL_PARAM_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+(?:=[A-Za-z0-9_.,:;/@+%=\-]*)?$")
_UNSAFE_KERNEL_CHARS = re.compile(r"[\x00-\x08\x0a-\x1f\x7f\"'\\]")

#: Image-storage object key: relative, no scheme, no parent traversal.
IMAGE_ARTIFACT_PATTERN = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9._/-]{1,512}$")
IMAGE_OVERRIDE_KEYS = ("kernel", "initrd", "rootfs")

#: Architectures Omnia supports for flexible functional groups.
SUPPORTED_ARCHITECTURES = ("x86_64", "aarch64")

#: Supported OS name/version combinations. Anything else warns but does not
#: fail, per the ER clarification response.
SUPPORTED_OS_TOKENS = (("rhel", "10_0"), ("rhel", "10_2"))
_OS_TOKEN = re.compile(r"_([a-z]+)_(\d+_\d+)_(?:x86_64|aarch64)$")


def record_error(errors: list[str], logger: Logger | None, message: str) -> None:
    """Append an error and write it to the validation log when configured."""
    errors.append(message)
    if logger:
        logger.error(message)


def record_warning(
    logger: Logger | None, message: str, warnings: list[str] | None = None
) -> None:
    """Record a non-blocking warning and write it to the validation log."""
    if warnings is not None:
        warnings.append(message)
    if logger:
        logger.warning(message)


def group_architecture(group: str) -> str | None:
    """Return the architecture suffix of a functional-group name, if present."""
    for architecture in SUPPORTED_ARCHITECTURES:
        if group.endswith(f"_{architecture}"):
            return architecture
    return None


def validate_architecture_reference(
    group: str,
    value: str,
    reference_kind: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Reject an explicitly named architecture that conflicts with a group."""
    group_arch = group_architecture(group)
    referenced = [arch for arch in SUPPORTED_ARCHITECTURES if arch in value]
    if group_arch and referenced and group_arch not in referenced:
        record_error(
            errors,
            logger,
            msg.functional_group_reference_architecture_conflict_msg(
                group, group_arch, reference_kind, referenced[0]
            ),
        )


def validate_kernel_params(
    raw: Any, referenced_by: str, errors: list[str], logger: Logger | None
) -> None:
    """Validate one ``boot_kernel_params`` string."""
    if raw is None:
        return
    if not isinstance(raw, str):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg(
                f"{referenced_by}.boot_kernel_params", type(raw).__name__, "a string"
            ),
        )
        return
    if _UNSAFE_KERNEL_CHARS.search(raw):
        record_error(
            errors,
            logger,
            msg.functional_group_kernel_param_format_msg(referenced_by, raw.strip()),
        )
        return
    for token in raw.split():
        if not KERNEL_PARAM_PATTERN.match(token):
            record_error(
                errors,
                logger,
                msg.functional_group_kernel_param_format_msg(referenced_by, token),
            )
            continue
        key = token.split("=", 1)[0]
        if key in PROTECTED_KERNEL_PARAMS:
            record_error(
                errors,
                logger,
                msg.functional_group_protected_param_msg(referenced_by, key),
            )


def validate_image_override(
    group: str, scope: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Validate the all-or-none ``{kernel, initrd, rootfs}`` image override.

    Reachability is verified before mutation by the image precheck against
    the configured image-storage endpoint; here the tuple is checked for
    completeness, safe object keys, and architecture agreement.
    """
    override = scope.get("image_override")
    if override is None or override == {}:
        return
    referenced_by = f"groups.{group}.image_override"
    if not isinstance(override, dict):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg(
                referenced_by, type(override).__name__, "a mapping"
            ),
        )
        return
    missing = [key for key in IMAGE_OVERRIDE_KEYS if not override.get(key)]
    unknown = sorted(set(override) - set(IMAGE_OVERRIDE_KEYS))
    if missing or unknown:
        record_error(
            errors,
            logger,
            msg.functional_group_image_override_incomplete_msg(group, missing, unknown),
        )
        return
    for key in IMAGE_OVERRIDE_KEYS:
        value = override[key]
        if not isinstance(value, str) or not IMAGE_ARTIFACT_PATTERN.match(value):
            record_error(
                errors,
                logger,
                msg.functional_group_image_artifact_invalid_msg(group, key, str(value)),
            )
            continue
        validate_architecture_reference(
            group, value, f"image_override.{key}", errors, logger
        )


def warn_unsupported_os(
    group: str, logger: Logger | None, warnings: list[str] | None
) -> None:
    """Warn, without failing, on an unsupported OS name/version."""
    match = _OS_TOKEN.search(group.lower())
    if match and (match.group(1), match.group(2)) in SUPPORTED_OS_TOKENS:
        return
    detail = (
        f"OS '{match.group(1)}' version '{match.group(2).replace('_', '.')}'"
        if match
        else "no recognizable <os>_<version> token"
    )
    record_warning(logger, msg.functional_group_unsupported_os_msg(group, detail), warnings)
