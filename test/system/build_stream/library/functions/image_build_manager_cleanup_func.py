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

"""Image Build Manager cleanup verification (``--tags cleanup``).

- ``cleanup_credentials`` (default true): remove the credential file and
  vault key; false runs the playbook with ``--skip-tags cleanup_credentials``
  and expects them kept.

MinIO, registry, build output, logs and data are always removed.
"""

from typing import Any, Dict, List

from .probe_func import (
    container_absent,
    domain_data_path,
    domain_input_path,
    path_removed,
    port_closed,
    project_name,
    removed_or_preserved,
    summarize,
    unit_inactive,
)
from ..vars.common_vars import (
    IBM_BUILD_STATUS,
    IBM_CONTAINERS,
    IBM_CREDENTIAL_FILES,
    IBM_PORTS,
    IBM_SERVICES,
)


def _credential_paths(host: Any) -> List[str]:
    """Return the image_build_manager credential files."""
    input_dir = domain_input_path(host, "image_build_manager")
    return [f"{input_dir}/{name}" for name in IBM_CREDENTIAL_FILES]


def pre_cleanup(host: Any, effective_vars: Dict[str, Any]) -> Dict[str, Any]:
    """Collect credential paths to preserve when cleanup_credentials is false.

    Returns:
        Dict with keys: preserve (paths), facts (empty).
    """
    keep = not effective_vars["cleanup_credentials"]
    return {"preserve": _credential_paths(host) if keep else [], "facts": {}}


def verify_image_build_manager_cleanup(host: Any, effective_vars: Dict[str, Any],
                                       baseline: Dict[str, bool],
                                       facts: Dict[str, Any]) -> Dict[str, Any]:
    """Verify MinIO, registry, build output and credential state."""
    del facts
    remove_credentials = effective_vars["cleanup_credentials"]
    data_root = domain_data_path(host, "image_build_manager")
    build_status = IBM_BUILD_STATUS.format(project=project_name(host))

    probes = [container_absent(host, name) for name in IBM_CONTAINERS]
    probes.extend(unit_inactive(host, unit) for unit in IBM_SERVICES)
    probes.extend(port_closed(host, port) for port in IBM_PORTS)
    probes.append(path_removed(host, f"{data_root}/{build_status}"))
    probes.extend(removed_or_preserved(host, _credential_paths(host),
                                       remove_credentials, baseline))
    return summarize("image_build_manager", probes,
                     [("cleanup_credentials", str(remove_credentials).lower())])
