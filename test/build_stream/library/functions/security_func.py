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
"""File-permission and ownership security helpers for BuildStream NFT.

Back the BSM_NFT_SECURITY_00[6-8] cases that guard the 0600 root:root
posture of credential-bearing quadlet files (omnia_postgres.container,
omnia_build_stream.container) against accidental regression to
world-readable modes.
"""

import shlex
from typing import Any, Dict, Optional


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
        Dict with ``success``, ``path``, ``mode``, ``owner``, ``group``,
        ``details``.
    """
    cmd = host.run(f"stat -c '%a %U %G' {shlex.quote(path)} 2>/dev/null")
    parts = cmd.stdout.strip().split() if cmd.rc == 0 else []
    if len(parts) != 3:
        details = (f"Unexpected stat output for {path}: {cmd.stdout!r}" if cmd.rc == 0
                   and cmd.stdout.strip() else
                   f"File not found or unreadable: {path} "
                   f"(rc={cmd.rc}, stderr={cmd.stderr.strip()})")
        return _permission_result(path, None, details)

    actual = dict(zip(("mode", "owner", "group"), parts))
    success = ((actual["mode"].lstrip("0") or "0") == (expected_mode.lstrip("0") or "0")
               and actual["owner"] == expected_owner and actual["group"] == expected_group)
    details = (f"{path}: mode={actual['mode']} owner={actual['owner']}:{actual['group']} "
               f"(expected {expected_mode} {expected_owner}:{expected_group})")
    return _permission_result(path, actual, details, success)


def _permission_result(path: str, actual: Optional[Dict[str, str]], details: str,
                       success: bool = False) -> Dict[str, Any]:
    """Return the check_file_permissions result dict."""
    actual = actual or {}
    return {
        "success": success,
        "path": path,
        "mode": actual.get("mode"),
        "owner": actual.get("owner"),
        "group": actual.get("group"),
        "details": details,
    }
