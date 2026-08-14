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

"""Container (MinIO / registry) runtime checks."""

from typing import Dict, Any

from ._config_helpers import _retry_run, _get_s3_provider
from ..vars.common_vars import CMDS, MINIO_CONTAINER


# =============================================================================
# CONTAINER CHECKS
# =============================================================================

def check_container_running(
    host, container_name: str
) -> Dict[str, Any]:
    """Check if a container is running on the target host.

    Args:
        host: testinfra host object
        container_name: Name of the container to check

    Returns:
        Dict with 'success', 'status', 'error'.
    """
    cmd = _retry_run(
        host,
        CMDS["podman_ps_running"].format(container=container_name),
    )

    if cmd.rc == 0 and container_name in cmd.stdout:
        status = cmd.stdout.strip()
        return {
            "success": True,
            "status": status,
            "error": None,
        }

    # Check if container exists but not running
    check_all = _retry_run(
        host,
        CMDS["podman_ps_all_status"].format(
            container=container_name,
        ),
    )
    if check_all.rc == 0 and container_name in check_all.stdout:
        status = check_all.stdout.strip()
        return {
            "success": False,
            "status": status,
            "error": f"Container exists but not running: {status}",
        }

    return {
        "success": False,
        "status": "not_found",
        "error": f"Container '{container_name}' not found",
    }


def check_s3_containers(host) -> Dict[str, Any]:
    """Check MinIO container is running (only for minio backend).

    Returns:
        Dict with 'success', 'backend', 'results', 'details'.
    """
    backend = _get_s3_provider(host)

    if backend == "powerscale":
        return {
            "success": True,
            "backend": "powerscale",
            "skipped": True,
            "results": [],
            "details": (
                "S3 backend is PowerScale — "
                "no local containers to check"
            ),
        }

    result = check_container_running(host, MINIO_CONTAINER)
    return {
        "success": result["success"],
        "backend": "minio",
        "skipped": False,
        "results": [
            {
                "container": MINIO_CONTAINER,
                "success": result["success"],
                "status": result["status"],
                "error": result["error"],
            }
        ],
        "details": (
            f"MinIO container: "
            f"{'running' if result['success'] else 'NOT running'}"
        ),
    }
