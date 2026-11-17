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

"""
Build Stream — Prepare Base Functions.

Runs ``./omnia.sh --prepare-base`` (repo_manager -> image_build_manager ->
orchestrator, the BuildStream prerequisites) and verifies what each base
domain's prepare leaves running, using the shared probes in probe_func.
"""

import os
from typing import Any, Dict, List

from omnia_auto import read_remote_env, read_remote_yaml

from library.functions.host_func import resolve_target_source_root
from library.functions.probe_func import (
    Probe,
    container_running,
    domain_data_path,
    domain_input_path,
    env_var_set,
    file_present,
    port_open,
    summarize_probes,
    unit_active,
    volume_present,
)
from library.vars.common_vars import (
    ENV_OMNIA_PROJECT_NAME,
    ENV_OMNIA_VENV_PATH,
    IBM_CONTAINERS,
    IBM_PORTS,
    IBM_SERVICES,
    OMNIA_SH_FILE,
    OMNIA_SH_WORKDIR,
    ORCH_OPENCHAMI_CONTAINERS,
    ORCH_OPENCHAMI_TIMER,
    ORCH_OPENCHAMI_UNITS,
    ORCH_OPENCHAMI_VOLUMES,
    ORCH_OPENLDAP_CONTAINER,
    ORCH_OPENLDAP_FLAG,
    ORCH_OPENLDAP_QUADLET,
    ORCH_OPENLDAP_SERVICE,
    ORCH_STATE_FILE,
    PREPARE_BASE_CREDENTIAL_FILES,
    PREPARE_BASE_DOMAINS,
    PREPARE_BASE_REQUIRED_ENV_VARS,
    RM_PULP_CONTAINER,
    RM_PULP_QUADLET,
    RM_PULP_SERVICE,
    VENV_ACTIVATE_FILE,
)

# =============================================================================
# PRECHECK AND ENTRY POINT
# =============================================================================

def check_prepare_base_prerequisites(host: Any) -> Dict[str, Any]:
    """Check that ``./omnia.sh --prepare-base`` can run unattended.

    Read-only. Verifies the omnia.env variables, the shared venv, omnia.sh in
    the checkout, and the repo_manager, image_build_manager and orchestrator
    credential stores (file and vault key). omnia.sh validates the domain
    inputs itself.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes = [env_var_set(host, name) for name in PREPARE_BASE_REQUIRED_ENV_VARS]
    _, venv, venv_set = probes[PREPARE_BASE_REQUIRED_ENV_VARS.index(ENV_OMNIA_VENV_PATH)]
    if venv_set:
        probes.append(file_present(host, f"{venv.rstrip('/')}/{VENV_ACTIVATE_FILE}"))
    probes.append(file_present(
        host, os.path.join(resolve_target_source_root(), OMNIA_SH_WORKDIR, OMNIA_SH_FILE)))
    for domain in PREPARE_BASE_DOMAINS:
        try:
            input_dir = domain_input_path(host, domain)
        except ValueError as exc:
            probes.append((f"{domain} credentials", str(exc), False))
            continue
        probes.extend(file_present(host, f"{input_dir}/{name}")
                      for name in PREPARE_BASE_CREDENTIAL_FILES[domain])
    return summarize_probes("prepare_base_prerequisites", probes)


# =============================================================================
# READINESS VERIFICATION
# =============================================================================

def check_repo_manager_ready(host: Any) -> Dict[str, Any]:
    """Verify repo_manager prepare: Pulp quadlet, service and container.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    return summarize_probes("repo_manager", [
        file_present(host, RM_PULP_QUADLET),
        unit_active(host, RM_PULP_SERVICE),
        container_running(host, RM_PULP_CONTAINER),
    ])


def check_image_build_manager_ready(host: Any) -> Dict[str, Any]:
    """Verify image_build_manager prepare: MinIO and the registry are serving.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes = [container_running(host, name) for name in IBM_CONTAINERS]
    probes.extend(unit_active(host, unit) for unit in IBM_SERVICES)
    probes.extend(port_open(host, port) for port in IBM_PORTS)
    return summarize_probes("image_build_manager", probes)


def _openldap_probes(host: Any) -> List[Probe]:
    """OpenLDAP probes when orchestrator_state.yml enables it; else none."""
    try:
        root = domain_data_path(host, "orchestrator")
        project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
        path = f"{root}/{ORCH_STATE_FILE.format(project=project)}"
        state = read_remote_yaml(host, path) or {}
    except (OSError, RuntimeError, ValueError) as exc:
        return [("orchestrator_state.yml", f"UNREADABLE ({exc})", False)]
    enabled = bool(state.get(ORCH_OPENLDAP_FLAG))
    probes: List[Probe] = [(f"{ORCH_OPENLDAP_FLAG} ({path})", str(enabled).lower(), True)]
    if enabled:
        probes += [file_present(host, ORCH_OPENLDAP_QUADLET),
                   unit_active(host, ORCH_OPENLDAP_SERVICE),
                   container_running(host, ORCH_OPENLDAP_CONTAINER)]
    return probes


def check_orchestrator_ready(host: Any) -> Dict[str, Any]:
    """Verify orchestrator prepare: every OpenCHAMI unit, container and volume.

    Units (one-shot units stay active), the certificate renewal timer, the
    long-running containers (healthcheck honoured), the data volumes, and
    OpenLDAP when orchestrator_state.yml enables it.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes = [unit_active(host, unit)
              for unit in (*ORCH_OPENCHAMI_UNITS, ORCH_OPENCHAMI_TIMER)]
    probes.extend(container_running(host, name) for name in ORCH_OPENCHAMI_CONTAINERS)
    probes.extend(volume_present(host, name) for name in ORCH_OPENCHAMI_VOLUMES)
    probes.extend(_openldap_probes(host))
    return summarize_probes("orchestrator", probes)
