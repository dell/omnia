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
Telemetry — Variables

Common constants, paths, component names, and command templates.
"""

from .common_vars import (
    MODULE_ROOT,
    MONOREPO_ROOT,
    SRC_INPUT_DIR,
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    TELEMETRY_NAMESPACE,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    PLAYBOOK_TAGS,
    IDRAC_STS_NAME,
    IDRAC_SERVICE_NAME,
    IDRAC_CONTAINERS,
    IDRAC_KAFKA_TOPIC,
    LDMS_AGG_STS_NAME,
    LDMS_STORE_NAME,
    LDMS_KAFKA_TOPIC,
    VECTOR_LDMS_APP_NAME,
    VECTOR_OME_APP_NAME,
    OME_KAFKA_USER,
    KAFKA_CR_NAME,
    VM_POD_PREFIXES,
    VL_POD_PREFIXES,
    VMAGENT_POD_PREFIX,
    VLAGENT_POD_PREFIX,
    TELEMETRY_SOURCES,
    TELEMETRY_SINKS,
    IPV4_PATTERN,
    REQUIRED_CONFIG_FIELDS,
    REQUIRED_SRC_FILES,
    CMDS,
)

from .test_case_vars import TEST_CASES

__all__ = [
    "MODULE_ROOT",
    "MONOREPO_ROOT",
    "SRC_INPUT_DIR",
    "DOMAIN_NAME",
    "ENV_OMNIA_DATA_PATH",
    "ENV_OMNIA_PROJECT_NAME",
    "TELEMETRY_NAMESPACE",
    "PLAYBOOK_ENTRY_POINT",
    "PLAYBOOK_WORKDIR",
    "PLAYBOOK_TAGS",
    "IDRAC_STS_NAME",
    "IDRAC_SERVICE_NAME",
    "IDRAC_CONTAINERS",
    "IDRAC_KAFKA_TOPIC",
    "LDMS_AGG_STS_NAME",
    "LDMS_STORE_NAME",
    "LDMS_KAFKA_TOPIC",
    "VECTOR_LDMS_APP_NAME",
    "VECTOR_OME_APP_NAME",
    "OME_KAFKA_USER",
    "KAFKA_CR_NAME",
    "VM_POD_PREFIXES",
    "VL_POD_PREFIXES",
    "VMAGENT_POD_PREFIX",
    "VLAGENT_POD_PREFIX",
    "TELEMETRY_SOURCES",
    "TELEMETRY_SINKS",
    "IPV4_PATTERN",
    "REQUIRED_CONFIG_FIELDS",
    "REQUIRED_SRC_FILES",
    "CMDS",
    "TEST_CASES",
]
