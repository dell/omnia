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

"""File-permission and ownership security helpers.

These helpers back the IMGBM_NFT_SECURITY_* cases that guard the 0600
root:root posture of credential-bearing files (MinIO quadlet, /root/.s3cfg)
against accidental regression to world-readable modes.
"""

from typing import Dict, Any


def check_file_permissions(
    host,
    path: str,
    expected_mode: str = "0600",
    expected_owner: str = "root",
    expected_group: str = "root",
) -> Dict[str, Any]:
    """Verify file mode and ownership match the expected security posture.

    Args:
        host: testinfra host object.
        path: Absolute path to inspect.
        expected_mode: Expected octal mode string, e.g. ``"0600"``.
        expected_owner: Expected owning user.
        expected_group: Expected owning group.

    Returns:
        Dict with keys ``success``, ``path``, ``mode``, ``owner``,
        ``group``, ``details``.
    """
    cmd = host.run(
        "stat -c '%a %U %G' {path} 2>/dev/null".format(path=path)
    )
    if cmd.rc != 0 or not cmd.stdout.strip():
        return {
            "success": False,
            "path": path,
            "mode": None,
            "owner": None,
            "group": None,
            "details": (
                f"File not found or unreadable: {path} "
                f"(rc={cmd.rc}, stderr={cmd.stderr.strip()})"
            ),
        }

    parts = cmd.stdout.strip().split()
    if len(parts) != 3:
        return {
            "success": False,
            "path": path,
            "mode": None,
            "owner": None,
            "group": None,
            "details": f"Unexpected stat output for {path}: {cmd.stdout!r}",
        }

    actual_mode, actual_owner, actual_group = parts
    # Normalise expected mode: '0600' or '600' both accepted.
    expected_normalised = expected_mode.lstrip("0") or "0"
    actual_normalised = actual_mode.lstrip("0") or "0"
    mode_ok = actual_normalised == expected_normalised
    owner_ok = actual_owner == expected_owner
    group_ok = actual_group == expected_group
    success = mode_ok and owner_ok and group_ok

    return {
        "success": success,
        "path": path,
        "mode": actual_mode,
        "owner": actual_owner,
        "group": actual_group,
        "details": (
            f"{path}: mode={actual_mode} owner={actual_owner}:{actual_group} "
            f"(expected {expected_mode} {expected_owner}:{expected_group})"
        ),
    }
