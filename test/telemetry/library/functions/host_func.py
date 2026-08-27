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
Telemetry — Module-specific host utilities.

Reads module config and passes ALL params to omnia_auto's
``sync_files()``.  No logic in the package -- only in this consumer.

Monorepo changes vs multi-repo:
- Input path resolved from target env vars (OMNIA_DATA_PATH, OMNIA_PROJECT_NAME)
- sync_project_to_remote() copies local project code to target clone_path
- No separate config.yml sync (env vars replace it)
"""

import os
from typing import Dict, Any

from omnia_auto import (
    load_test_config,
    get_module_root,
    sync_files,
    connection_params,
    resolve_domain_input_path,
    ensure_remote_dir,
)

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    SRC_INPUT_DIR,
)

__all__ = [
    "sync_project_to_remote",
    "sync_telemetry_input",
]


def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the local omnia project tree to clone_path on target.

    Source: ``<repo_root>/`` (the omnia monorepo root)
    Dest:   ``<clone_path>/`` on the target server
    """
    config = load_test_config()
    conn = connection_params()

    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    return sync_files(
        mode=conn["mode"],
        src=repo_root,
        dest=config["clone_path"],
        ip=conn["ip"],
        user=conn["user"],
        auth_secret=conn["auth_secret"],
        ssh_opts=conn["ssh_opts"],
    )


def _resolve_input_dir(config):
    """Resolve local input directory from dataset or src/."""
    dataset = config.get("dataset", "")
    if dataset:
        return os.path.join(
            get_module_root(), "datasets", dataset, "input",
        )
    return SRC_INPUT_DIR


def sync_telemetry_input(host) -> Dict[str, Any]:
    """Push telemetry input files from local source to target.

    Reads ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` from the target
    server's environment to resolve the correct destination::

        <OMNIA_DATA_PATH>/telemetry/input/<OMNIA_PROJECT_NAME>/

    Source: src/telemetry/input/ (default) or
            datasets/<dataset>/input/ (when dataset is set).
    """
    config = load_test_config()
    conn = connection_params()

    local_input = _resolve_input_dir(config)
    remote_input = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    ensure_remote_dir(host, remote_input)

    return sync_files(
        mode=conn["mode"], src=local_input, dest=remote_input,
        ip=conn["ip"], user=conn["user"],
        auth_secret=conn["auth_secret"], ssh_opts=conn["ssh_opts"],
    )
