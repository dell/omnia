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

"""Repo Manager cleanup verification (``repo_manager.yml --tags cleanup_pulp``).

- ``cleanup_logs`` (default true): remove or preserve the log directory.
- ``cleanup_credentials`` (default true): remove or preserve credentials.
"""

from typing import Any, Dict, List

from .probe_func import (
    container_absent,
    domain_data_path,
    domain_input_path,
    path_removed,
    removed_or_preserved,
    summarize,
)
from ..vars.common_vars import (
    RM_CREDENTIAL_FILES,
    RM_LOG_DIRS,
    RM_PULP_CONTAINER,
    RM_PULP_DIRS,
    RM_PULP_QUADLET,
)


def _log_paths(host: Any) -> List[str]:
    """Return the repo_manager log directories."""
    data_root = domain_data_path(host, "repo_manager")
    return [f"{data_root}/{rel}" for rel in RM_LOG_DIRS]


def _credential_paths(host: Any) -> List[str]:
    """Return the repo_manager credential files."""
    input_dir = domain_input_path(host, "repo_manager")
    return [f"{input_dir}/{name}" for name in RM_CREDENTIAL_FILES]


def pre_cleanup(host: Any, effective_vars: Dict[str, Any]) -> Dict[str, Any]:
    """Collect log/credential paths that must survive cleanup.

    Returns:
        Dict with keys: preserve (paths), facts (empty).
    """
    return {
        "preserve": [
            *([] if effective_vars["cleanup_logs"] else _log_paths(host)),
            *([] if effective_vars["cleanup_credentials"] else _credential_paths(host)),
        ],
        "facts": {},
    }


def verify_repo_manager_cleanup(host: Any, effective_vars: Dict[str, Any],
                                baseline: Dict[str, bool],
                                facts: Dict[str, Any]) -> Dict[str, Any]:
    """Verify the Pulp deployment, logs and credentials."""
    del facts
    remove_logs = effective_vars["cleanup_logs"]
    remove_credentials = effective_vars["cleanup_credentials"]
    data_root = domain_data_path(host, "repo_manager")

    probes = [container_absent(host, RM_PULP_CONTAINER), path_removed(host, RM_PULP_QUADLET)]
    probes.extend(path_removed(host, f"{data_root}/{rel}") for rel in RM_PULP_DIRS)
    probes.extend(removed_or_preserved(host, _log_paths(host), remove_logs, baseline))
    probes.extend(removed_or_preserved(host, _credential_paths(host),
                                       remove_credentials, baseline))
    return summarize("repo_manager", probes, [
        ("cleanup_logs", str(remove_logs).lower()),
        ("cleanup_credentials", str(remove_credentials).lower()),
    ])
