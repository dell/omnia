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

"""Build log collection (for failure diagnostics)."""

from typing import Dict, Any

from ._config_helpers import _get_shared_path, _get_project_name
from ..vars.common_vars import CMDS, BUILD_LOG_PATH


# =============================================================================
# LOG COLLECTION (on failure)
# =============================================================================

def collect_build_logs(host, max_lines: int = 100) -> Dict[str, Any]:
    """Collect recent build log output from the target host.

    Reads the last ``max_lines`` lines from the build log directory.
    Used to provide diagnostic context when playbook execution fails.

    Args:
        host: testinfra host object.
        max_lines: Maximum number of log lines to return.

    Returns:
        Dict with 'success', 'log_output', 'log_path'.
    """
    project = _get_project_name()
    log_dir = BUILD_LOG_PATH.format(
        shared_path=_get_shared_path(), project=project,
    )

    # Try to get the latest .log file via ls -t
    ls_cmd = host.run(
        f"ls -t {log_dir}*.log 2>/dev/null | head -1"
    )
    if ls_cmd.rc != 0 or not ls_cmd.stdout.strip():
        return {
            "success": False,
            "log_output": "",
            "log_path": log_dir,
            "error": f"No log files found in {log_dir}",
        }

    latest_log = ls_cmd.stdout.strip()
    tail_cmd = host.run(
        CMDS["cat_build_log"].format(
            lines=max_lines, log_path=latest_log,
        )
    )

    return {
        "success": tail_cmd.rc == 0,
        "log_output": tail_cmd.stdout if tail_cmd.rc == 0 else "",
        "log_path": latest_log,
        "error": None if tail_cmd.rc == 0 else "Failed to read log",
    }
