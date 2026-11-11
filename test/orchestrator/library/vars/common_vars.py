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

"""Paths and contracts shared by the prepare runner and its sync helpers."""

import os
import re

MODULE_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
REPO_ROOT = os.path.dirname(MODULE_ROOT)
MONOREPO_ROOT = os.path.dirname(REPO_ROOT)

SRC_ORCHESTRATOR_DIR = os.path.join(MONOREPO_ROOT, "src", "orchestrator")
SRC_INPUT_DIR = os.path.join(SRC_ORCHESTRATOR_DIR, "input")
SRC_REPO_OUTPUT_DIR = os.path.join(
    SRC_ORCHESTRATOR_DIR,
    "samples",
    "repo_manager_output",
)
SRC_IMAGE_BUILD_OUTPUT_DIR = os.path.join(
    SRC_ORCHESTRATOR_DIR,
    "samples",
    "image_build_manager_output",
)
DATASETS_DIR = os.path.join(MODULE_ROOT, "datasets")
SCHEMA_DIR = os.path.join(
    SRC_ORCHESTRATOR_DIR,
    "plugins",
    "module_utils",
    "orchestrator_validation",
    "schema",
)

DATASET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
REQUIRED_DATASET_INPUT_FILES = [
    "orchestrator_config.yml",
    "network_spec.yml",
]
REQUIRED_REPO_OUTPUT_FILES = ["repo_status.yml"]
REQUIRED_IMAGE_BUILD_OUTPUT_FILES = ["build_status.yml"]

PLAYBOOK_ENTRY_POINT = "orchestrator.yml"
PLAYBOOK_WORKDIR = "src/orchestrator/playbooks"
