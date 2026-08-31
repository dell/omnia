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

"""Orchestrator — Variables Package."""

from .common_vars import (
    MODULE_ROOT,
    MONOREPO_ROOT,
    SRC_ORCHESTRATOR_DIR,
    DOMAIN_NAME,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    PLAYBOOK_TAGS,
    CMDS,
)
from .slurm_vars import (
    SLURM_SERVICES,
    SLURM_DIRECTORIES,
    SLURM_CONFIG_FILES,
    SLURM_PROVISION_PLAYBOOK,
    SLURM_PROVISION_WORKDIR,
    TEST_CASES as SLURM_TEST_CASES,
)

__all__ = [
    "MODULE_ROOT",
    "MONOREPO_ROOT",
    "SRC_ORCHESTRATOR_DIR",
    "DOMAIN_NAME",
    "PLAYBOOK_ENTRY_POINT",
    "PLAYBOOK_WORKDIR",
    "PLAYBOOK_TAGS",
    "CMDS",
    "SLURM_SERVICES",
    "SLURM_DIRECTORIES",
    "SLURM_CONFIG_FILES",
    "SLURM_PROVISION_PLAYBOOK",
    "SLURM_PROVISION_WORKDIR",
    "SLURM_TEST_CASES",
]
