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

"""Orchestrator cleanup verification (``orchestrator.yml --tags cleanup``).

- ``cleanup_credentials`` (default true): remove or preserve the credential
  file and vault key.
- ``dry_run`` (default false): when true nothing may be removed, so the
  services that existed before cleanup must still exist.
- ``skip_approval``, ``cleanup_slurm``, ``cleanup_k8s``: reported; the
  shared-data outcome depends on storage_config.yml and is covered by the
  orchestrator FVT cleanup suite.
"""

from typing import Any, Dict, List

from .probe_func import (
    container_absent,
    domain_input_path,
    path_exists,
    removed_or_preserved,
    summarize,
    unit_inactive,
)
from ..vars.common_vars import (
    CLEANUP_DOMAINS,
    ORCH_CREDENTIAL_FILES,
    ORCH_OPENCHAMI_CONTAINERS,
    ORCH_OPENCHAMI_INIT_CONTAINER,
    ORCH_OPENCHAMI_TIMER,
    ORCH_OPENCHAMI_UNITS,
    ORCH_OPENLDAP_CONTAINER,
    ORCH_OPENLDAP_SERVICE,
)

_CONTAINERS = (*ORCH_OPENCHAMI_CONTAINERS, ORCH_OPENCHAMI_INIT_CONTAINER,
               ORCH_OPENLDAP_CONTAINER)


def _credential_paths(host: Any) -> List[str]:
    """Return the orchestrator credential files."""
    input_dir = domain_input_path(host, "orchestrator")
    return [f"{input_dir}/{name}" for name in ORCH_CREDENTIAL_FILES]


def pre_cleanup(host: Any, effective_vars: Dict[str, Any]) -> Dict[str, Any]:
    """Collect the credential paths that must be preserved.

    Returns:
        Dict with keys: preserve (paths), facts (empty).
    """
    preserve = [] if effective_vars["cleanup_credentials"] else _credential_paths(host)
    return {"preserve": preserve, "facts": {}}


def verify_orchestrator_cleanup(host: Any, effective_vars: Dict[str, Any],
                                baseline: Dict[str, bool],
                                facts: Dict[str, Any]) -> Dict[str, Any]:
    """Verify OpenCHAMI, OpenLDAP and credential state."""
    del facts
    probes = [container_absent(host, name) for name in _CONTAINERS]
    probes.extend(unit_inactive(host, unit)
                  for unit in (*ORCH_OPENCHAMI_UNITS, ORCH_OPENCHAMI_TIMER,
                               ORCH_OPENLDAP_SERVICE))
    probes.extend(removed_or_preserved(host, _credential_paths(host),
                                       effective_vars["cleanup_credentials"], baseline))
    reported = CLEANUP_DOMAINS["cleanup_orchestrator"]["supported_vars"]
    fields = [(key, str(effective_vars[key]).lower()) for key in reported]
    fields.append(("Credential files present",
                   ", ".join(p for p in _credential_paths(host) if path_exists(host, p))
                   or "none"))
    return summarize("orchestrator", probes, fields)
