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
Build Stream — Prepare Verification Functions.

What ``build_stream.yml --tags prepare`` deploys (roles ``postgres`` and
``deploy_bsm``): the omnia_postgres and omnia_build_stream containers with
their quadlets, the systemd services including playbook-watcher, and
``build_stream_status.yml``.
"""

from typing import Any, Dict, List

from omnia_auto import read_remote_yaml

from library.functions.probe_func import (
    Probe,
    container_running,
    domain_output_path,
    file_present,
    summarize_probes,
    unit_active,
)
from library.vars.common_vars import (
    BSM_CONTAINERS,
    BUILD_STREAM_STATUS_FILE,
    BUILD_STREAM_STATUS_KEYS,
    BUILD_STREAM_STATUS_PREPARED,
    DOMAIN_NAME,
    PREPARE_QUADLETS,
    PREPARE_SERVICES,
)


def check_prepare_containers(host: Any) -> Dict[str, Any]:
    """Verify the omnia_build_stream and omnia_postgres containers and quadlets.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    probes = [container_running(host, name) for name in BSM_CONTAINERS]
    probes.extend(file_present(host, path) for path in PREPARE_QUADLETS)
    return summarize_probes("containers", probes)


def check_prepare_services(host: Any) -> Dict[str, Any]:
    """Verify omnia_postgres, omnia_build_stream and playbook-watcher are active.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("services", [unit_active(host, unit) for unit in PREPARE_SERVICES])


def check_prepare_status_file(host: Any) -> Dict[str, Any]:
    """Verify build_stream_status.yml reports ``prepared`` with every endpoint key.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    try:
        path = f"{domain_output_path(host, DOMAIN_NAME)}/{BUILD_STREAM_STATUS_FILE}"
        status = read_remote_yaml(host, path) or {}
    except (OSError, RuntimeError, ValueError) as exc:
        return summarize_probes("status_file", [(BUILD_STREAM_STATUS_FILE, str(exc), False)])
    probes: List[Probe] = [(f"File {path}", "present", True)]
    for key in BUILD_STREAM_STATUS_KEYS:
        value = str(status.get(key, "") or "")
        if key == "overall_status":
            probes.append((key, value or "MISSING", value == BUILD_STREAM_STATUS_PREPARED))
        else:
            probes.append((key, value or "MISSING", bool(value)))
    return summarize_probes("status_file", probes)
