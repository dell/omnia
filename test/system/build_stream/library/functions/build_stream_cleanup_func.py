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

"""Build Stream cleanup verification (``build_stream.yml --tags cleanup``).

- ``postgres_backup`` (default true): preserve (true) or delete (false) the
  Postgres data directory and volumes.
- ``cleanup_credentials`` (default true): remove the credential files; false
  runs the playbook with ``--skip-tags credentials`` and expects them kept.
"""

from typing import Any, Dict, List

from omnia_auto import read_remote_yaml

from .probe_func import (
    Probe,
    container_absent,
    data_path,
    domain_input_path,
    path_preserved,
    path_removed,
    port_closed,
    removed_or_preserved,
    run_cmd,
    summarize,
    unit_inactive,
)
from ..vars.common_vars import (
    BSM_CONFIG_FILE,
    BSM_CONFIG_KEYS,
    BSM_CONTAINER,
    BSM_CREDENTIAL_FILES,
    BSM_PLAYBOOK_WATCHER_SERVICE,
    BSM_PLAYBOOK_WATCHER_UNIT_FILE,
    BSM_POSTGRES_CONTAINER,
    BSM_POSTGRES_DATA_DIR,
    BSM_RUNTIME_DIRS,
)


def _postgres_data_dir(host: Any) -> str:
    """Return the Postgres data directory on the shared path."""
    return f"{data_path(host)}/{BSM_POSTGRES_DATA_DIR}"


def _credential_paths(host: Any) -> List[str]:
    """Return the BuildStream credential files in the project input directory."""
    input_dir = domain_input_path(host, "build_stream")
    return [f"{input_dir}/{name}" for name in BSM_CREDENTIAL_FILES]


def pre_cleanup(host: Any, effective_vars: Dict[str, Any]) -> Dict[str, Any]:
    """Collect paths to preserve and the API port before cleanup runs.

    Returns:
        Dict with keys: preserve (paths), facts (api_port or None).
    """
    preserve = [_postgres_data_dir(host)] if effective_vars["postgres_backup"] else []
    if not effective_vars["cleanup_credentials"]:
        preserve.extend(_credential_paths(host))
    try:
        config = read_remote_yaml(
            host, f"{domain_input_path(host, 'build_stream')}/{BSM_CONFIG_FILE}")
        port = config.get(BSM_CONFIG_KEYS["api_port"])
    except (RuntimeError, ValueError):
        port = None
    return {"preserve": preserve, "facts": {"api_port": port}}


def _postgres_volumes_removed(host: Any) -> Probe:
    """Check that no Postgres podman volume is left."""
    volumes = run_cmd(host, "podman_postgres_volumes").stdout.split()
    state = f"STILL EXIST: {', '.join(volumes)}" if volumes else "removed"
    return "Postgres volumes", state, not volumes


def verify_build_stream_cleanup(host: Any, effective_vars: Dict[str, Any],
                                baseline: Dict[str, bool],
                                facts: Dict[str, Any]) -> Dict[str, Any]:
    """Verify BSM API, Postgres, playbook-watcher, runtime and credential state."""
    keep_db = effective_vars["postgres_backup"]
    remove_credentials = effective_vars["cleanup_credentials"]
    shared = data_path(host)
    db_dir = _postgres_data_dir(host)

    probes = [
        container_absent(host, BSM_CONTAINER),
        container_absent(host, BSM_POSTGRES_CONTAINER),
        unit_inactive(host, BSM_PLAYBOOK_WATCHER_SERVICE),
        path_removed(host, BSM_PLAYBOOK_WATCHER_UNIT_FILE),
    ]
    if facts.get("api_port"):
        probes.append(port_closed(host, int(facts["api_port"])))
    if keep_db:
        probes.append(path_preserved(host, db_dir, baseline))
    else:
        probes.extend([path_removed(host, db_dir), _postgres_volumes_removed(host)])
    probes.extend(path_removed(host, f"{shared}/{rel}") for rel in BSM_RUNTIME_DIRS)
    probes.extend(removed_or_preserved(host, _credential_paths(host),
                                       remove_credentials, baseline))
    return summarize("build_stream", probes, [
        ("postgres_backup", str(keep_db).lower()),
        ("cleanup_credentials", str(remove_credentials).lower()),
        ("API port", facts.get("api_port") or "unknown (config unreadable)"),
    ])
