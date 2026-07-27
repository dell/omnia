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
Software configuration validation messages.

This module contains validation messages specific to software_config.json
and related software package validation.
"""

# =============================================================================
# OS VERSION MESSAGES
# =============================================================================


def os_version_fail_msg(cluster_os_type, min_version, max_version):
    """Returns a formatted message indicating os_version_fail_msg."""
    if cluster_os_type == "ubuntu":
        return (
            f"For OS type '{cluster_os_type}', the version must be either "
            f"{min_version} or {max_version}."
        )
    return f"For OS type '{cluster_os_type}', the supported version is {min_version}."

# =============================================================================
# SOFTWARE MANDATORY MESSAGES
# =============================================================================


def software_mandatory_fail_msg(software_name):
    """Returns a formatted message indicating software_mandatory_fail_msg."""
    return (
        f"in software_config.json. Please add the corresponding field '{software_name}' "
        "to the JSON. Look at /examples/template_ubuntu_software_config.json for an example"
    )


def json_file_mandatory(file_path):
    """Returns a formatted message indicating json_file_mandatory."""
    return (
        f"is present in software_config.json. Please make sure that the corresponding "
        f"JSON file is present at location '{file_path}'"
    )

# =============================================================================
# LDMS MESSAGES
# =============================================================================


LDMS_REQUIRES_SERVICE_K8S_MSG = (
    "requires service_k8s to be present in the 'softwares' list in software_config.json."
)

LDMS_REQUIRES_SLURM_MSG = (
    "requires Slurm package 'slurm_custom' to be present in the 'softwares' list "
    "in software_config.json."
)

# =============================================================================
# KUBERNETES MESSAGES
# =============================================================================

MISSING_CLUSTER_NAME_MSG = "Cluster name is mandatory for all kubernetes roles."

CLUSTER_NAME_OVERLAP_MSG = (
    "The cluster name '{0}' cannot be shared between service and compute Kubernetes roles."
)

CLUSTER_NAME_INCONSISTENT_MSG = (
    "Inconsistent 'cluster_name' values found across Service or Compute Kubernetes roles. "
    "Each of the following role sets must use the same 'cluster_name': "
    "[service_kube_control_plane, service_kube_node, service_etcd] and "
    "[kube_control_plane, kube_node, etcd]."
)

CLUSTER_ROLE_MISSING_MSG = (
    "Cluster '{0}' is missing the following required Kubernetes roles: {1}."
)

K8S_CNI_FAIL_MSG = (
    "k8s_cni is empty or invalid. k8s_cni must be set to either calico or flannel."
)

K8S_SERVICE_ADDRESSES_FAIL_MSG = (
    "k8s_service_addresses are empty. Please provide k8s_service_addresses value."
)

K8S_POD_NETWORK_CIDR_FAIL_MSG = (
    "k8s_pod_network_cidr is empty. Please provide a k8s_pod_network_cidr value."
)

POD_EXTERNAL_IP_RANGE_FAIL_MSG = (
    "pod_external_ip_range value is either empty or invalid. Please provide one of "
    "the following acceptable formats: '10.11.0.100-10.11.0.150' (range between start "
    "and end IP addresses) or '10.11.0.0/16' (CIDR notation)."
)

# =============================================================================
# SLURM MESSAGES
# =============================================================================

SLURM_INSTALLATION_TYPE_FAIL_MSG = (
    "slurm_installation_type is empty or invalid. slurm_installation_type must either "
    "be set to nfs_share or configless."
)

RESTART_SLURM_SERVICES_FAIL_MSG = (
    "restart_slurm_services is empty or invalid. restart_slurm_services must be set "
    "to either true or false."
)

# =============================================================================
# CSI DRIVER MESSAGES
# =============================================================================

CSI_DRIVER_SECRET_FAIL_MSG = "CSI Powerscale driver secret file path should not be empty."
CSI_DRIVER_VALUES_FAIL_MSG = "CSI Powerscale driver values file path should not be empty."

# =============================================================================
# SERVICE NODE MESSAGES
# =============================================================================

SERVICE_NODE_ENTRY_MISSING_ROLES_CONFIG_MSG = (
    "The role service_node defined in roles_config.yml, but service_node entry missing "
    "in software_config.json. Please rerun local repo with service_node entry in "
    "software_config.json to deploy service nodes successfully"
)

SERVICE_K8S_ENTRY_MISSING_SOFTWARE_CONFIG_MSG = (
    "The role service_kube_control_plane is defined in roles_config.yml, but the "
    "service_k8s package entry is missing in software_config.json. To deploy Kubernetes "
    "in the service_k8s cluster, the package must be added to software_config.json."
)

SERVICE_NODE_ENTRY_INVALID_ROLES_CONFIG_MSG = (
    "The 'service_node' role defined in roles_config.yml is not currently supported "
    "and is reserved for future use. Please remove or update this role to avoid "
    "configuration errors."
)

# =============================================================================
# FUNCTIONAL GROUP MESSAGES
# =============================================================================

SERVICE_K8S_FUNCTIONAL_GROUP_WITHOUT_SOFTWARE_MSG = (
    "Service Kubernetes functional groups (service_kube_node_* or service_kube_control_plane_*) "
    "are defined in the PXE mapping file, but 'service_k8s' is not configured in "
    "software_config.json. Please add 'service_k8s' to the 'softwares' list in "
    "software_config.json to deploy the service cluster."
)

SLURM_FUNCTIONAL_GROUP_WITHOUT_SOFTWARE_MSG = (
    "Slurm functional groups (slurm_control_node_* or slurm_node_*) are defined in the "
    "PXE mapping file, but 'slurm_custom' is not configured in software_config.json. "
    "Please add 'slurm_custom' to the 'softwares' list in software_config.json to deploy "
    "the Slurm cluster."
)

EMPTY_OR_SYNTAX_ERROR_FUNCTIONAL_GROUPS_CONFIG_MSG = (
    "The functional_groups_config.yml file is empty or has syntax errors. "
    "It must contain a valid 'functional_groups' section with proper YAML formatting. "
    "Check the file content and rerun the playbook."
)

MISSING_GROUPS_SECTION_MSG = (
    "The functional_groups_config.yml file is empty or has syntax errors. "
    "It must contain a valid 'groups' section with proper YAML formatting. "
    "Check the file content and rerun the playbook."
)

MISSING_FUNCTIONAL_GROUPS_SECTION_MSG = (
    "The functional_groups_config.yml file must contain a valid 'functional_groups' section. "
    "It must be a non-empty list."
)

NON_EMPTY_CLUSTER_NAME_MSG = "Cluster name must not be empty for '{name}' functional group."

FUNCTIONAL_GROUPS_NOT_LIST_MSG = (
    "The 'functional_groups' key must be associated with a list of functional group definitions."
)

EACH_FUNCTIONAL_GROUP_NOT_DICT_MSG = (
    "Each functional group entry must be a dictionary with required fields."
)

MISSING_FIELD_FUNCTIONAL_GROUP_MSG = "Missing required field: {field}"

DUPLICATE_FUNCTIONAL_GROUP_NAME_MSG = "Duplicate functional group name found."

LOGIN_NODE_WITHOUT_SLURM_MSG = (
    "Login node defined for cluster '{cluster}' but no corresponding slurm_control_node exists. "
    "Please make sure cluster name is same for slurm cluster and login_node functional groups."
)

SLURM_NODE_PARENT_MISSING_MSG = (
    "Functional group '{name}' must have a non-empty 'parent' field."
)

SLURM_NODE_WITHOUT_CONTROL_MSG = (
    "Slurm node defined for cluster '{cluster}' but no corresponding slurm_control_node exists. "
    "Please make sure cluster name is same for slurm_control_node and slurm_node functional groups."
)

SLURM_KUBE_CLUSTER_OVERLAP_MSG = (
    "Cluster '{cluster}' is defined for both SLURM nodes and Kubernetes nodes. Overlap not allowed."
)
