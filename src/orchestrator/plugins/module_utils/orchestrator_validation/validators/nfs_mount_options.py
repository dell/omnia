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
"""Shared checks for NFS rsize/wsize mount options."""

from __future__ import annotations

from typing import Any

NFS_TRANSFER_SIZE_OPTIONS = ("rsize", "wsize")
NFS_MAX_TRANSFER_SIZE = 1048576


def transfer_size_issues(
    mount_options: Any, allow_max: bool
) -> list[tuple[str, str]]:
    """Return (option, value) for each invalid rsize/wsize in mount_options.

    A value must be a whole number greater than 0 and at most 1 MiB
    (allow_max) or below 1 MiB (not allow_max).
    """
    if not isinstance(mount_options, str):
        return []
    issues = []
    for option in mount_options.split(","):
        key, separator, value = option.strip().partition("=")
        if key not in NFS_TRANSFER_SIZE_OPTIONS:
            continue
        value = value.strip()
        valid = (
            separator
            and value.isascii()
            and value.isdecimal()
            and 0 < int(value) <= NFS_MAX_TRANSFER_SIZE
            and (allow_max or int(value) < NFS_MAX_TRANSFER_SIZE)
        )
        if not valid:
            issues.append((key, value))
    return issues


def missing_transfer_size_pair(mount_options: Any) -> str | None:
    """Return the missing option when only one of rsize/wsize is set."""
    if not isinstance(mount_options, str):
        return None
    keys = {
        option.strip().partition("=")[0] for option in mount_options.split(",")
    }
    present = [key for key in NFS_TRANSFER_SIZE_OPTIONS if key in keys]
    if len(present) == 1:
        return next(
            key for key in NFS_TRANSFER_SIZE_OPTIONS if key not in present
        )
    return None
