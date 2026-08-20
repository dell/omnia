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
Telemetry — Host Sync Functions.

Functions for syncing project, input files, and datasets to the target.
Re-exports common omnia_auto host functions.
"""

import os

from omnia_auto import (
    load_test_config,
    clone_repo,
    sync_files,
    log,
)

from library.vars.common_vars import (
    DOMAIN_NAME,
    SRC_INPUT_DIR,
    DEFAULT_OMNIA_DATA_PATH,
    DEFAULT_PROJECT_NAME,
    MODULE_ROOT,
)


def sync_project_to_remote(host):
    """Clone/sync the omnia repo to the target server.

    Uses omnia_auto.clone_repo() to ensure the source is available.

    Args:
        host: testinfra host connection.
    """
    config = load_test_config()
    clone_path = config.get("clone_path", "")
    repo_url = config.get("repo_url", "")
    branch = config.get("branch", "main")

    if not clone_path:
        log("clone_path not set in test_config.yml, skipping repo sync", "WARN")
        return

    clone_repo(
        mode="ssh",
        host=host,
        repo_url=repo_url,
        dest_path=clone_path,
        branch=branch,
    )


def sync_telemetry_input(host, dataset_dir=None):
    """Sync telemetry input files to the target's runtime path.

    If dataset_dir is provided, syncs from the dataset. Otherwise
    syncs from src/telemetry/input/.

    Args:
        host: testinfra host connection.
        dataset_dir: Local path to dataset input/ directory (optional).
    """
    config = load_test_config()
    project = config.get("project_name", DEFAULT_PROJECT_NAME)
    omnia_data_path = config.get("omnia_data_path", DEFAULT_OMNIA_DATA_PATH)
    dest = f"{omnia_data_path}/{DOMAIN_NAME}/input/{project}/"

    if dataset_dir and os.path.isdir(dataset_dir):
        src = dataset_dir
        log(f"Syncing telemetry input from dataset: {src}", "INFO")
    else:
        src = SRC_INPUT_DIR
        log(f"Syncing telemetry input from src: {src}", "INFO")

    sync_files(
        mode="ssh",
        host=host,
        src=src + "/",
        dest=dest,
    )


def get_dataset_input_dir(dataset_name):
    """Resolve the local path to a dataset's input/ directory.

    Args:
        dataset_name: Name of the dataset (e.g. 'data_set_01').

    Returns:
        str: Absolute path to datasets/<name>/input/ or empty string.
    """
    dataset_dir = os.path.join(MODULE_ROOT, "datasets", dataset_name, "input")
    if os.path.isdir(dataset_dir):
        return dataset_dir
    return ""
