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

"""Core variables for automation library."""

# =============================================================================
# OMNIA BASE PATHS (inside omnia_core container)
# =============================================================================

OIM_SHARED_PATH = "/opt/omnia"
OMNIA_DATA_PATH = f"{OIM_SHARED_PATH}/.data"
OMNIA_AUTH_PATH = f"{OIM_SHARED_PATH}/auth"
OMNIA_TELEMETRY_PATH = f"{OIM_SHARED_PATH}/telemetry"
OMNIA_LOG_PATH = f"{OIM_SHARED_PATH}/log"
OMNIA_PULP_PATH = f"{OIM_SHARED_PATH}/pulp"

# =============================================================================
# INPUT BASE PATH (inside omnia_core container)
# =============================================================================

INPUT_BASE_PATH = f"{OIM_SHARED_PATH}/input/project_default"

# =============================================================================
# INPUT FILE NAMES (inside omnia_core container at INPUT_BASE_PATH)
# Used by core/load_inputs.py get_input_value(host, filename, key)
# =============================================================================

SOFTWARE_CONFIG_FILE = "software_config.json"
BUILD_STREAM_CONFIG_FILE = "build_stream_config.yml"
GITLAB_CONFIG_FILE = "gitlab_config.yml"
NETWORK_SPEC_FILE = "network_spec.yml"
PROVISION_CONFIG_FILE = "provision_config.yml"
DISCOVERY_CONFIG_FILE = "discovery_config.yml"
TELEMETRY_CONFIG_FILE = "telemetry_config.yml"
TELEMETRY_STORAGE_CONFIG_FILE = "telemetry_storage_config.yml"
STORAGE_CONFIG_FILE = "storage_config.yml"
OMNIA_CONFIG_FILE = "omnia_config.yml"
OMNIA_CREDENTIALS_FILE = "omnia_config_credentials.yml"
HA_CONFIG_FILE = "high_availability_config.yml"
PXE_MAPPING_FILE = "pxe_mapping_file.csv"
BMC_PXE_MAPPING_FILE_PREFIX = "bmc_pxe_mapping_file_"

# =============================================================================
# FULL INPUT FILE PATHS (built from INPUT_BASE_PATH + file names)
# =============================================================================

SOFTWARE_CONFIG_PATH = f"{INPUT_BASE_PATH}/{SOFTWARE_CONFIG_FILE}"
TELEMETRY_CONFIG_PATH = f"{INPUT_BASE_PATH}/{TELEMETRY_CONFIG_FILE}"
TELEMETRY_STORAGE_CONFIG_PATH = f"{INPUT_BASE_PATH}/{TELEMETRY_STORAGE_CONFIG_FILE}"
OMNIA_CONFIG_PATH = f"{INPUT_BASE_PATH}/{OMNIA_CONFIG_FILE}"
NETWORK_SPEC_PATH = f"{INPUT_BASE_PATH}/{NETWORK_SPEC_FILE}"
PROVISION_CONFIG_PATH = f"{INPUT_BASE_PATH}/{PROVISION_CONFIG_FILE}"
STORAGE_CONFIG_PATH = f"{INPUT_BASE_PATH}/{STORAGE_CONFIG_FILE}"
HA_CONFIG_PATH = f"{INPUT_BASE_PATH}/{HA_CONFIG_FILE}"
PXE_MAPPING_FILE_PATH = f"{INPUT_BASE_PATH}/{PXE_MAPPING_FILE}"
DISCOVERY_CONFIG_PATH = f"{INPUT_BASE_PATH}/{DISCOVERY_CONFIG_FILE}"
OMNIA_CREDENTIALS_PATH = f"{INPUT_BASE_PATH}/{OMNIA_CREDENTIALS_FILE}"
OMNIA_CREDENTIALS_KEY_PATH = f"{INPUT_BASE_PATH}/.omnia_config_credentials_key"
GITLAB_CONFIG_PATH = f"{INPUT_BASE_PATH}/{GITLAB_CONFIG_FILE}"
BUILD_STREAM_OAUTH_CREDENTIALS_PATH = f"{INPUT_BASE_PATH}/build_stream_oauth_credentials.yml"
BUILD_STREAM_OAUTH_CREDENTIALS_KEY_PATH = f"{INPUT_BASE_PATH}/.build_stream_oauth_credentials_key"

# =============================================================================
# OMNIA DATA PATHS (inside omnia_core container under .data/)
# =============================================================================

SERVICE_CLUSTER_METADATA_PATH = f"{OMNIA_DATA_PATH}/service_cluster_metadata.yml"
OIM_METADATA_PATH = f"{OMNIA_DATA_PATH}/oim_metadata.yml"
FUNCTIONAL_GROUPS_CONFIG_PATH = f"{OMNIA_DATA_PATH}/functional_groups_config.yml"

# =============================================================================
# OMNIA AUTH PATHS (inside omnia_core container under auth/)
# =============================================================================

SLAPD_CONF_PATH = f"{OMNIA_AUTH_PATH}/slapd.conf"
LDAP_CERT_PATH = f"{OMNIA_AUTH_PATH}/tls_certs/ldapserver.crt"

# =============================================================================
# OMNIA TELEMETRY PATHS (inside omnia_core container under telemetry/)
# =============================================================================

BMC_GROUP_DATA_PATH = f"{OMNIA_TELEMETRY_PATH}/bmc_group_data.csv"
IDRAC_TELEMETRY_REPORT_PATH = f"{OMNIA_TELEMETRY_PATH}/idrac_telemetry_report.yml"

# =============================================================================
# OMNIA PULP PATHS (inside omnia_core container under pulp/)
# =============================================================================

PULP_CERT_PATH = f"{OMNIA_PULP_PATH}/settings/certs/pulp_webserver.crt"

# =============================================================================
# OMNIA LOG PATHS (inside omnia_core container under log/)
# =============================================================================

LOCAL_REPO_LOG_PATH = f"{OMNIA_LOG_PATH}/local_repo"

# =============================================================================
# CONTAINER NAMES
# =============================================================================

OMNIA_CORE_CONTAINER = "omnia_core"

# =============================================================================
# KUBERNETES FUNCTIONAL GROUPS (from PXE mapping file)
# =============================================================================

K8S_CONTROL_PLANE_FUNCTIONAL_GROUP = "service_kube_control_plane_x86_64"
K8S_WORKER_NODE_FUNCTIONAL_GROUP = "service_kube_node_x86_64"

# =============================================================================
# SLURM FUNCTIONAL GROUPS (from PXE mapping file)
# =============================================================================

SLURM_CONTROL_NODE_FUNCTIONAL_GROUP = "slurm_control_node_x86_64"
SLURM_NODE_FUNCTIONAL_GROUP = "slurm_node_x86_64"
SLURM_NODE_AARCH64_FUNCTIONAL_GROUP = "slurm_node_aarch64"
LOGIN_NODE_FUNCTIONAL_GROUP = "login_node_x86_64"
LOGIN_NODE_AARCH64_FUNCTIONAL_GROUP = "login_node_aarch64"
LOGIN_COMPILER_NODE_FUNCTIONAL_GROUP = "login_compiler_node_x86_64"
LOGIN_COMPILER_NODE_AARCH64_FUNCTIONAL_GROUP = "login_compiler_node_aarch64"

# =============================================================================
# MINIMAL OS FUNCTIONAL GROUPS (from PXE mapping file)
# =============================================================================

MINIMAL_OS_X86_64_FUNCTIONAL_GROUP = "os_x86_64"
MINIMAL_OS_AARCH64_FUNCTIONAL_GROUP = "os_aarch64"

# =============================================================================
# OMNIA SUPPORTED FUNCTIONAL GROUPS (all valid functional group names)
# =============================================================================

OMNIA_SUPPORTED_FUNCTIONAL_GROUPS = [
    K8S_CONTROL_PLANE_FUNCTIONAL_GROUP,
    K8S_WORKER_NODE_FUNCTIONAL_GROUP,
    SLURM_CONTROL_NODE_FUNCTIONAL_GROUP,
    SLURM_NODE_FUNCTIONAL_GROUP,
    SLURM_NODE_AARCH64_FUNCTIONAL_GROUP,
    LOGIN_NODE_FUNCTIONAL_GROUP,
    LOGIN_NODE_AARCH64_FUNCTIONAL_GROUP,
    LOGIN_COMPILER_NODE_FUNCTIONAL_GROUP,
    LOGIN_COMPILER_NODE_AARCH64_FUNCTIONAL_GROUP,
    MINIMAL_OS_X86_64_FUNCTIONAL_GROUP,
    MINIMAL_OS_AARCH64_FUNCTIONAL_GROUP,
]

# =============================================================================
# PXE MAPPING FILE COLUMNS (expected columns in discovery output)
# =============================================================================

PXE_MAPPING_REQUIRED_COLUMNS = [
    "FUNCTIONAL_GROUP_NAME",
    "GROUP_NAME",
    "SERVICE_TAG",
    "PARENT_SERVICE_TAG",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
    "BMC_MAC",
    "BMC_IP",
    "IB_NIC_NAME",
    "IB_IP",
]

# =============================================================================
# PLAYBOOK PATHS (inside omnia_core container)
#
# Single source of truth for all playbook paths used by test_deploy.py files.
# If Omnia renames or moves a playbook, update only here.
# =============================================================================

_PLAYBOOKS_BASE = "/omnia/src/playbooks"

PREPARE_OIM_PLAYBOOK = f"{_PLAYBOOKS_BASE}/prepare_oim/prepare_oim.yml"
PREPARE_OIM_WORKDIR = f"{_PLAYBOOKS_BASE}/prepare_oim"

PROVISION_PLAYBOOK = f"{_PLAYBOOKS_BASE}/provision/provision.yml"
PROVISION_WORKDIR = f"{_PLAYBOOKS_BASE}/provision"

SET_PXE_BOOT_PLAYBOOK = f"{_PLAYBOOKS_BASE}/utils/set_pxe_boot.yml"
SET_PXE_BOOT_WORKDIR = f"{_PLAYBOOKS_BASE}/utils"

LOCAL_REPO_PLAYBOOK = f"{_PLAYBOOKS_BASE}/local_repo/local_repo.yml"
LOCAL_REPO_WORKDIR = f"{_PLAYBOOKS_BASE}/local_repo"

TELEMETRY_PLAYBOOK = f"{_PLAYBOOKS_BASE}/telemetry/telemetry.yml"
TELEMETRY_WORKDIR = f"{_PLAYBOOKS_BASE}/telemetry"

DISCOVERY_PLAYBOOK = f"{_PLAYBOOKS_BASE}/discovery/discovery.yml"
DISCOVERY_WORKDIR = f"{_PLAYBOOKS_BASE}/discovery"

GITLAB_PLAYBOOK = f"{_PLAYBOOKS_BASE}/gitlab/gitlab.yml"
GITLAB_WORKDIR = f"{_PLAYBOOKS_BASE}/gitlab"

GITLAB_CLEANUP_PLAYBOOK = f"{_PLAYBOOKS_BASE}/gitlab/cleanup_gitlab.yml"
GITLAB_CLEANUP_WORKDIR = f"{_PLAYBOOKS_BASE}/gitlab"

OIM_CLEANUP_PLAYBOOK = f"{_PLAYBOOKS_BASE}/utils/oim_cleanup.yml"
OIM_CLEANUP_WORKDIR = f"{_PLAYBOOKS_BASE}/utils"

BUILD_IMAGE_X86_64_PLAYBOOK = f"{_PLAYBOOKS_BASE}/build_image_x86_64/build_image_x86_64.yml"
BUILD_IMAGE_X86_64_WORKDIR = f"{_PLAYBOOKS_BASE}/build_image_x86_64"

BUILD_IMAGE_AARCH64_PLAYBOOK = f"{_PLAYBOOKS_BASE}/build_image_aarch64/build_image_aarch64.yml"
BUILD_IMAGE_AARCH64_WORKDIR = f"{_PLAYBOOKS_BASE}/build_image_aarch64"

VALIDATE_CONFIG_PLAYBOOK = f"{_PLAYBOOKS_BASE}/input_validation/validate_config.yml"
VALIDATE_CONFIG_WORKDIR = f"{_PLAYBOOKS_BASE}/input_validation"
