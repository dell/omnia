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
Telemetry-specific validation messages in English (US).
These messages are used to provide user-friendly error messages during
telemetry input configuration validation.
"""

# pylint: disable=invalid-name
# PowerScale telemetry validation messages
POWERSCALE_VICTORIA_REQUIRED_MSG = (
    "PowerScale telemetry requires VictoriaMetrics to be deployed. "
    "When telemetry_sources.powerscale.metrics_enabled is true in telemetry_config.yml, "
    "'victoria_metrics' must be included in collection_targets "
    "(e.g., 'victoria_metrics' or 'victoria_metrics,victoria_logs')."
)
POWERSCALE_VICTORIA_LOGS_REQUIRED_MSG = (
    "PowerScale logs collection requires VictoriaLogs to be deployed. "
    "When telemetry_sources.powerscale.logs_enabled is true in telemetry_config.yml, "
    "'victoria_logs' must be included in collection_targets "
    "(e.g., 'victoria_metrics,victoria_logs')."
)
POWERSCALE_CSI_DRIVER_MISSING_MSG = (
    "csi_driver_powerscale is not configured in software_config.json. "
    "PowerScale telemetry requires the CSI driver for PowerScale to be configured."
)
POWERSCALE_SERVICE_CLUSTER_MISSING_MSG = (
    "service cluster is not found in orchestrator_inventory. "
    "PowerScale telemetry requires a service cluster with at least one "
    "service_kube_control_plane node and one service_kube_node. "
    "Ensure orchestrator_inventory contains these groups with at least one host each."
)
POWERSCALE_CONFIGURATIONS_MISSING_MSG = (
    "powerscale_configurations section is required in telemetry_config.yml when "
    "telemetry_sources.powerscale.metrics_enabled is true. "
    "It must contain csm_observability_values_file_path."
)
POWERSCALE_OTEL_STORAGE_SIZE_INVALID_MSG = (
    "must be a non-empty string in format 'XGi' (e.g., '5Gi') in telemetry_config.yml"
)
POWERSCALE_CSM_VALUES_PATH_REQUIRED_MSG = (
    "csm_observability_values_file_path is required in telemetry_config.yml when "
    "telemetry_sources.powerscale.metrics_enabled is true. "
    "Please provide the path to the CSM Observability values.yaml file."
)
def powerscale_csm_values_not_found_msg(path):
    """Returns error message when CSM Observability values.yaml file is not found."""
    return (
        f"CSM Observability values.yaml file not found at '{path}'. "
        "Please verify the file path is correct in "
        "telemetry_config.yml (csm_observability_values_file_path)."
    )
POWERSCALE_CSM_VALUES_INVALID_YAML_MSG = (
    "CSM Observability values.yaml (path specified in "
    "telemetry_config.yml) must contain a valid YAML dictionary."
)
def powerscale_csm_values_parse_error_msg(error):
    """Returns error message when CSM Observability values.yaml fails to parse."""
    return f"Failed to parse CSM Observability values.yaml: {error}"
POWERSCALE_CSM_VALUES_MISSING_KARAVI_SECTION_MSG = (
    "CSM Observability values.yaml (path specified in "
    "telemetry_config.yml) is missing "
    "'karaviMetricsPowerscale' section."
)
POWERSCALE_CSM_METRICS_IMAGE_MISSING_MSG = (
    "CSM Metrics PowerScale image is required in CSM "
    "Observability values.yaml "
    "(path specified in telemetry_config.yml)."
)
POWERSCALE_OTEL_COLLECTOR_IMAGE_MISSING_MSG = (
    "OTEL Collector image is required in CSM Observability "
    "values.yaml (path specified in telemetry_config.yml)."
)
POWERSCALE_IMAGE_VERSION_MISMATCH_MSG = (
    "PowerScale image version mismatch detected in offline mode. "
    "Ensure these images match telemetry_packages.yml and are present in Pulp registry."
)
def powerscale_image_version_mismatch_msg(mismatched_images):
    """Returns error message when CSM values.yaml image version doesn't match telemetry_packages.yml."""
    return (
        f"{POWERSCALE_IMAGE_VERSION_MISMATCH_MSG} "
        f"{', '.join(mismatched_images)}"
    )
ADDITIONAL_METRIC_ENDPOINTS_URL_EMPTY_MSG = (
    "Each additional_metric_remote_write_endpoint in "
    "telemetry_config.yml must have a non-empty 'url' field."
)
ADDITIONAL_METRIC_ENDPOINTS_URL_INVALID_MSG = (
    "URL in telemetry_config.yml must start with 'http://' or 'https://'."
)
ADDITIONAL_LOG_ENDPOINTS_URL_EMPTY_MSG = (
    "Each additional_log_write_endpoint in telemetry_config.yml must have a non-empty 'url' field."
)
ADDITIONAL_LOG_ENDPOINTS_URL_INVALID_MSG = (
    "URL in telemetry_config.yml must start with 'http://' or 'https://'."
)
POWERSCALE_IMAGE_VERSION_MISMATCH_MSG = (
    "PowerScale image version mismatch detected in offline mode. "
    "Ensure these images match telemetry_packages.yml and are present in Pulp registry."
)
def powerscale_image_version_mismatch_msg(mismatched_images):
    """Returns error message when CSM values.yaml image version doesn't match telemetry_packages.yml."""
    return (
        f"{POWERSCALE_IMAGE_VERSION_MISMATCH_MSG} "
        f"{', '.join(mismatched_images)}"
    )

# pylint: enable=invalid-name

def boolean_fail_msg(value):
    """Returns a formatted message indicating boolean_fail_msg."""
    return f"{value} must be set to either true or false."

def get_header():
    """Returns a formatted header string for execution logs."""
    return f"{'#' * 30} START EXECUTION {'#' * 30}"

def get_footer():
    """Returns a formatted footer string for execution logs."""
    return f"{'#' * 30} END EXECUTION {'#' * 30}"

# kube_vip validation messages (extracted from cluster_inventory)
KUBE_VIP_INVALID_IPV4_MSG = (
    "kube_vip extracted from cluster_inventory must be a valid IPv4 address "
    "with each octet in the range 0-255 (e.g., '10.0.0.1'). "
    "Check the kube_vip_group.hosts entry in your cluster_inventory file."
)
KUBE_VIP_SSH_UNREACHABLE_MSG = (
    "kube_vip (from cluster_inventory) is not reachable via SSH. "
    "Ensure the Kubernetes control plane VIP is online and SSH access is configured "
    "from this host before running telemetry operations."
)

# telemetry_packages.yml validation messages
CLUSTER_MOUNT_REQUIRED_MSG = (
    "cluster_mount is required in telemetry_packages.yml and must be a non-empty path. "
    "Provide the local NFS mount point on the Kubernetes cluster where telemetry packages "
    "will be staged (e.g., '/opt/omnia/k8s_mount')."
)
REGISTRY_HOST_FORMAT_MSG = (
    "telemetry_registry.host must be in format 'IP:port' or 'hostname:port' "
    "(e.g., '192.168.1.10:5000'). If no registry authentication is needed, leave host empty."
)
REGISTRY_CERT_NOT_FOUND_MSG = (
    "telemetry_registry.cert_path file not found. "
    "Ensure the certificate file exists at the specified path, or leave cert_path empty."
)
REGISTRY_KEY_NOT_FOUND_MSG = (
    "telemetry_registry.key_path file not found. "
    "Ensure the key file exists at the specified path, or leave key_path empty."
)
PACKAGE_URL_INVALID_MSG = (
    "Package URL in telemetry_packages.yml must start with 'http://' or 'https://'. "
    "Provide the full download URL from the Pulp repository or external source."
)
CLUSTER_MOUNT_PATH_NOT_FOUND_ON_KUBE_VIP_MSG = (
    "cluster_mount path does not exist on kube_vip host. "
    "Ensure the NFS mount point exists on the Kubernetes "
    "cluster before running telemetry deployment. "
    "Create the directory or verify the NFS mount is active."
)
CLUSTER_MOUNT_KUBE_VIP_NOT_FOUND_MSG = (
    "Cannot validate cluster_mount path existence: kube_vip "
    "could not be extracted from cluster_inventory. "
    "Ensure cluster_inventory in telemetry_config.yml points to a valid inventory file "
    "with kube_vip_group.hosts defined containing the Kubernetes control plane VIP."
)
CLUSTER_MOUNT_SSH_CHECK_FAILED_MSG = (
    "Failed to verify cluster_mount path on kube_vip via SSH. "
    "Ensure SSH access to kube_vip is configured and the host is reachable."
)

# Telemetry storage configuration validation
KAFKA_STORAGE_REQUIRED_MSG = (
    "kafka_storage section is required in telemetry_storage_config.yml "
    "when kafka is in collection_targets for any telemetry source "
    "(idrac, ldms). Please configure kafka_storage with kafka and "
    "entity_operator.user_operator resource configurations."
)

VICTORIA_METRICS_STORAGE_REQUIRED_MSG = (
    "victoria_cluster_storage section is required in telemetry_storage_config.yml "
    "when victoria_metrics is in collection_targets for any telemetry source. "
    "Please configure victoria_cluster_storage with vmstorage, vminsert, vmselect, and vmagent."
)

VICTORIA_LOGS_STORAGE_REQUIRED_MSG = (
    "victoria_logs_cluster_storage section is required in "
    "telemetry_storage_config.yml "
    "when victoria_logs is in collection_targets for any "
    "telemetry source. Please configure "
    "victoria_logs_cluster_storage with vlstorage, "
    "vlinsert, vlselect, and vlagent."
)

VECTOR_STORAGE_REQUIRED_MSG = (
    "vector_storage section is required in telemetry_storage_config.yml "
    "when Vector bridges are enabled (vector_ldms or vector_ome). "
    "Please configure vector_storage with ldms, ome, vlagent_vector, and vmagent_vector."
)

CSI_VOLUME_EXPORTER_STORAGE_REQUIRED_MSG = (
    "csi_volume_exporter_storage section is required in telemetry_storage_config.yml "
    "when CSI volume metrics are enabled. Please configure resource requests and limits."
)

CSM_METRICS_POWERSCALE_STORAGE_REQUIRED_MSG = (
    "csm_metrics_powerscale_storage section is required in telemetry_storage_config.yml "
    "when PowerScale metrics are enabled. Please configure resource requests and limits."
)

IDRAC_TELEMETRY_STORAGE_REQUIRED_MSG = (
    "idrac_telemetry_storage section is required in "
    "telemetry_storage_config.yml "
    "when iDRAC metrics are enabled. Please configure "
    "resource requests and limits for mysqldb, activemq, "
    "receiver, kafka_pump, and victoria_pump containers."
)

TELEMETRY_STORAGE_CONFIG_FILE_NOT_FOUND_MSG = (
    "telemetry_storage_config.yml file not found. This file "
    "is required when telemetry collection is enabled. "
    "Please create the file with appropriate storage "
    "configurations."
)

def get_validation_initiated(input_file_path):
    """Returns a formatted message indicating validation has started for a file."""
    return f"{'#' * 10} Validation Initiated for {input_file_path} {'#' * 10}"

def get_schema_failed(input_file_path):
    """Returns a formatted message indicating schema validation failure for a file."""
    return f"{'#' * 10} Schema validation failed for {input_file_path} {'#' * 10}"

def get_schema_success(input_file_path):
    """Returns a formatted message indicating schema validation success for a file."""
    return f"{'#' * 10} Schema validation successful for {input_file_path} {'#' * 10}"

def get_logic_failed(input_file_path):
    """Returns a formatted message indicating logic validation failure for a file."""
    return f"{'#' * 10} Logic validation failed for {input_file_path} {'#' * 10}"

def get_logic_success(input_file_path):
    """Returns a formatted message indicating logic validation success for a file."""
    return f"{'#' * 10} Logic validation successful for {input_file_path} {'#' * 10}"

# ============================================================================
# Vector Bridge Validation Messages
# ============================================================================

# Vector-LDMS validation messages
VECTOR_LDMS_SOURCE_DISABLED_MSG = (
    "Vector-LDMS bridge cannot be enabled when "
    "telemetry_sources.ldms.metrics_enabled is 'false'. "
    "Vector-LDMS consumes LDMS metrics from Kafka topic "
    "'ldms'. To fix: Either set "
    "telemetry_sources.ldms.metrics_enabled=true to enable "
    "LDMS data collection, or set "
    "telemetry_bridges.vector_ldms.metrics_enabled=false "
    "to disable the Vector-LDMS bridge."
)

# CSM Observability - Unsupported metrics validation messages
def powerscale_unsupported_metrics_enabled_msg(component_name, section_name, values_file_path):
    """Returns error message when unsupported CSM metrics components are enabled."""
    return (
        f"{component_name} metrics collection not supported. "
        f"Set {section_name}.enabled to false in {values_file_path} and rerun the playbook."
    )
