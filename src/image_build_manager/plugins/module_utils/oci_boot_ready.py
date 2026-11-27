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
# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-CONFIG-001.5, CG-DESER-001.1
# ****

"""Evaluate whether OCI layer entry listings describe a complete boot set.

Layer entry names arrive in manifest order, lowest layer first. The merged view
applies whiteouts (``.wh.<name>``) and opaque directories (``.wh..wh..opq``) in
memory. Absolute names and names containing ``..`` are ignored, and rescue or
debug kernels never count. No layer content is extracted.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

WHITEOUT_PREFIX = ".wh."
OPAQUE_MARKER = ".wh..wh..opq"
KERNEL_PREFIX = "boot/vmlinuz-"
INITRAMFS_TEMPLATE = "boot/initramfs-{version}.img"
MODULES_TEMPLATE = "lib/modules/{version}"
USR_MERGED_MODULES_TEMPLATE = "usr/lib/modules/{version}"
MISSING_KERNEL_PATH = "boot/vmlinuz-*"
NON_BOOT_KERNEL = re.compile(r"rescue|debug")


def _normalize(name: str) -> str | None:
    """Return the relative path of a layer entry, or None when it must be ignored.

    Args:
        name: Entry name as listed in the layer archive.

    Returns:
        The normalized relative path, or None for absolute or ``..`` names and
        for entries that resolve to the archive root.
    """
    if name.startswith("/") or ".." in name.split("/"):
        return None
    return "/".join(part for part in name.split("/") if part not in ("", ".")) or None


def _remove(present: set[str], prefixes: Iterable[tuple[str, bool]]) -> None:
    """Remove paths under each prefix, and the prefix itself when requested.

    Args:
        present: Merged set of relative paths, updated in place.
        prefixes: Pairs of (path, include_self) describing whiteout targets.
    """
    removals = list(prefixes)
    if not removals:
        return
    for path in list(present):
        for prefix, include_self in removals:
            if path.startswith(prefix + "/") or (include_self and path == prefix):
                present.discard(path)
                break


def _merge_layers(layers: Sequence[Iterable[str]]) -> set[str]:
    """Merge layer entry listings in order, applying whiteouts and opaque markers.

    Args:
        layers: Entry names per layer, lowest layer first.

    Returns:
        Relative paths present in the merged image view.
    """
    present: set[str] = set()
    for layer in layers:
        removals: list[tuple[str, bool]] = []
        additions: set[str] = set()
        for entry in layer:
            path = _normalize(entry)
            if path is None:
                continue
            directory, _, base = path.rpartition("/")
            if base == OPAQUE_MARKER:
                removals.append((directory, False))
            elif base.startswith(WHITEOUT_PREFIX):
                name = base[len(WHITEOUT_PREFIX):]
                removals.append((f"{directory}/{name}" if directory else name, True))
            else:
                additions.add(path)
        _remove(present, removals)
        present.update(additions)
    return present


def _has_path(present: set[str], path: str) -> bool:
    """Return True when a path or any entry beneath it exists in the merged view.

    Args:
        present: Merged set of relative paths.
        path: Relative path to look up.

    Returns:
        True when the path itself or a child of it is present.
    """
    return path in present or any(item.startswith(path + "/") for item in present)


def _has_modules(present: set[str], version: str) -> bool:
    """Return True when the kernel modules directory exists in either layout.

    RHEL 10 images are usr-merged, so ``/lib`` is a symlink to ``/usr/lib`` and
    layer listings carry the modules under ``usr/lib/modules``.

    Args:
        present: Merged set of relative paths.
        version: Kernel version of a candidate boot set.

    Returns:
        True when ``lib/modules/<version>`` or ``usr/lib/modules/<version>`` exists.
    """
    return any(
        _has_path(present, template.format(version=version))
        for template in (MODULES_TEMPLATE, USR_MERGED_MODULES_TEMPLATE)
    )


def _first_missing(present: set[str], version: str) -> str:
    """Return the first missing boot path for one kernel version.

    Args:
        present: Merged set of relative paths.
        version: Kernel version of a candidate boot set.

    Returns:
        The initramfs path when it is absent, otherwise the modules directory.
    """
    initramfs = INITRAMFS_TEMPLATE.format(version=version)
    return initramfs if initramfs not in present else MODULES_TEMPLATE.format(version=version)


def evaluate_boot_set(layers: Sequence[Iterable[str]]) -> dict[str, Any]:
    """Report the complete boot sets in an image, or the first missing path.

    A boot set for kernel version V needs ``boot/vmlinuz-V``,
    ``boot/initramfs-V.img`` and ``lib/modules/V`` in the merged view. Kernel
    names containing ``rescue`` or ``debug`` are not candidates.

    Args:
        layers: Entry names per layer, lowest layer first.

    Returns:
        Dict with ``complete_versions`` (sorted kernel versions with a complete
        boot set) and ``missing_path`` (empty when a set is complete, otherwise
        the first missing path of the first candidate kernel).
    """
    present = _merge_layers(layers)
    versions = sorted(
        path[len(KERNEL_PREFIX):]
        for path in present
        if path.startswith(KERNEL_PREFIX)
        and "/" not in path[len(KERNEL_PREFIX):]
        and not NON_BOOT_KERNEL.search(path[len(KERNEL_PREFIX):])
    )
    complete = [
        version
        for version in versions
        if INITRAMFS_TEMPLATE.format(version=version) in present
        and _has_modules(present, version)
    ]
    missing = ""
    if not complete:
        missing = _first_missing(present, versions[0]) if versions else MISSING_KERNEL_PATH
    return {"complete_versions": complete, "missing_path": missing}
