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

"""Prepare-base verification: what each base domain's prepare leaves running.

These are the BuildStream prerequisites ``./omnia.sh --prepare-base``
creates (repo_manager -> image_build_manager -> orchestrator). Each check
follows the producing domain's own deployment contract and lists every
container, unit, volume and port it checks (summarize marks each one).
"""

from typing import Any, Dict, List

from omnia_auto import read_remote_yaml

from .probe_func import (
    Probe,
    container_running,
    domain_data_path,
    file_present,
    port_open,
    project_name,
    summarize,
    unit_active,
    volume_present,
)
from ..vars.common_vars import (
    IBM_CONTAINERS,
    IBM_PORTS,
    IBM_SERVICES,
    ORCH_OPENCHAMI_CONTAINERS,
    ORCH_OPENCHAMI_TIMER,
    ORCH_OPENCHAMI_UNITS,
    ORCH_OPENCHAMI_VOLUMES,
    ORCH_OPENLDAP_CONTAINER,
    ORCH_OPENLDAP_FLAG,
    ORCH_OPENLDAP_QUADLET,
    ORCH_OPENLDAP_SERVICE,
    ORCH_STATE_FILE,
    RM_PULP_CONTAINER,
    RM_PULP_QUADLET,
    RM_PULP_SERVICE,
)


def verify_repo_manager_ready(host: Any) -> Dict[str, Any]:
    """Verify repo_manager prepare: Pulp quadlet, service and container.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    return summarize("repo_manager", [file_present(host, RM_PULP_QUADLET),
                                      unit_active(host, RM_PULP_SERVICE),
                                      container_running(host, RM_PULP_CONTAINER)])


def verify_image_build_manager_ready(host: Any) -> Dict[str, Any]:
    """Verify image_build_manager prepare: MinIO and the registry are serving.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes = [container_running(host, name) for name in IBM_CONTAINERS]
    probes.extend(unit_active(host, unit) for unit in IBM_SERVICES)
    probes.extend(port_open(host, port) for port in IBM_PORTS)
    return summarize("image_build_manager", probes)


def _openldap_probes(host: Any) -> List[Probe]:
    """OpenLDAP probes when orchestrator_state.yml enables it; else none."""
    try:
        path = (f"{domain_data_path(host, 'orchestrator')}/"
                f"{ORCH_STATE_FILE.format(project=project_name(host))}")
        state = read_remote_yaml(host, path) or {}
    except (RuntimeError, ValueError) as exc:
        return [("orchestrator_state.yml", f"UNREADABLE ({exc})", False)]
    enabled = bool(state.get(ORCH_OPENLDAP_FLAG))
    probes: List[Probe] = [(f"{ORCH_OPENLDAP_FLAG} ({path})", str(enabled).lower(), True)]
    if enabled:
        probes += [file_present(host, ORCH_OPENLDAP_QUADLET),
                   unit_active(host, ORCH_OPENLDAP_SERVICE),
                   container_running(host, ORCH_OPENLDAP_CONTAINER)]
    return probes


def verify_orchestrator_ready(host: Any) -> Dict[str, Any]:
    """Verify orchestrator prepare: every OpenCHAMI unit, container and volume.

    Units (including one-shot units, which stay active), the certificate
    renewal timer, the long-running containers (healthcheck honoured), the
    data volumes, and OpenLDAP when orchestrator_state.yml enables it.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes = [unit_active(host, unit) for unit in (*ORCH_OPENCHAMI_UNITS, ORCH_OPENCHAMI_TIMER)]
    probes.extend(container_running(host, name) for name in ORCH_OPENCHAMI_CONTAINERS)
    probes.extend(volume_present(host, name) for name in ORCH_OPENCHAMI_VOLUMES)
    probes.extend(_openldap_probes(host))
    return summarize("orchestrator", probes)
