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
Telemetry — Module-Specific Variables

Constants, component names, and shell command templates for telemetry FVT.
Paths are resolved from environment variables on the target host at runtime.
"""

import os
import re

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Module root: test/telemetry/ directory (where conftest.py lives)
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))

# Parent of module root: test/
TEST_ROOT = os.path.dirname(MODULE_ROOT)

# Omnia monorepo root: omnia/
MONOREPO_ROOT = os.path.dirname(TEST_ROOT)

# src/ paths - used when dataset is empty (default: use src/ directly)
SRC_INPUT_DIR = os.path.join(
    MONOREPO_ROOT, "src", "telemetry", "input",
)

# =============================================================================
# DOMAIN IDENTITY
# =============================================================================

DOMAIN_NAME = "telemetry"

# Environment variable names on the target host
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"

# =============================================================================
# INPUT FILE NAMES
# =============================================================================

TELEMETRY_CONFIG_FILE = "telemetry_config.yml"
TELEMETRY_PACKAGES_FILE = "telemetry_packages.yml"

# =============================================================================
# PLAYBOOK CONFIGURATION
# =============================================================================

PLAYBOOK_ENTRY_POINT = "playbooks/telemetry.yml"
PLAYBOOK_WORKDIR = "src/telemetry"

# Valid playbook tags
PLAYBOOK_TAGS = [
    "precheck",
    "validate",
    "deploy",
    "cleanup",
    "upgrade",
    "rollback",
    "external_kafka",
    "external_victoria",
]

# =============================================================================
# K8S CONSTANTS
# =============================================================================

TELEMETRY_NAMESPACE = "telemetry"

# =============================================================================
# SINK COMPONENT NAMES
# =============================================================================

# VictoriaMetrics cluster pod prefixes
VM_POD_PREFIXES = {
    "vmstorage": "vmstorage",
    "vminsert": "vminsert",
    "vmselect": "vmselect",
}

# VictoriaMetrics agent
VMAGENT_POD_PREFIX = "vmagent"

# VictoriaLogs cluster pod prefixes
VL_POD_PREFIXES = {
    "vlstorage": "vlstorage",
    "vlinsert": "vlinsert",
    "vlselect": "vlselect",
}

# VictoriaLogs agent
VLAGENT_POD_PREFIX = "vlagent"

# Kafka pod prefixes (Strimzi naming)
KAFKA_POD_PREFIXES = {
    "broker": "kafka-broker",
    "controller": "kafka-controller",
}

KAFKA_BRIDGE_PREFIX = "bridge-bridge"
KAFKA_CR_NAME = "kafka"
KAFKA_EXTERNAL_BOOTSTRAP_SVC = "kafka-kafka-external-bootstrap"

# =============================================================================
# SOURCE COMPONENT NAMES
# =============================================================================

# iDRAC (from deploy_idrac_telemetry/vars/main.yml)
IDRAC_POD_PREFIX = "idrac-telemetry"
IDRAC_STS_NAME = "idrac-telemetry"
IDRAC_SERVICE_NAME = "idrac-telemetry-service"
IDRAC_CONTAINERS = [
    "idrac-telemetry-receiver",
    "kafka-pump",
    "victoria-pump",
    "mysqldb",
    "activemq",
]
IDRAC_KAFKA_TOPIC = "idrac"

# LDMS - see ldms_vars.py for all LDMS-specific constants
# Kept here for backward compatibility
from .ldms_vars import (  # noqa: F401, E402
    LDMS_AGG_STS_NAME,
    LDMS_STORE_NAME,
    LDMS_KAFKA_TOPIC,
    LDMS_FUNCTIONAL_GROUPS,
    LDMS_SAMPLER_SERVICE,
    LDMS_SAMPLER_CONF_PATH,
)

# LDMS Kafka verification behavior
LDMS_KAFKA_LATEST_TIMEOUT_SECONDS = 90
LDMS_KAFKA_EARLIEST_TIMEOUT_SECONDS = 60
LDMS_KAFKA_CLOCK_SKEW_SECONDS = 10
LDMS_KAFKA_LATEST_POLL_INTERVAL_SECONDS = 2
LDMS_KAFKA_EARLIEST_POLL_INTERVAL_SECONDS = 0.3
LDMS_KAFKA_OFFSET_LATEST = "latest"
LDMS_KAFKA_OFFSET_EARLIEST = "earliest"
LDMS_KAFKA_CONSUMER_GROUP_TEMPLATE = "ldms-{offset}-{suffix}"
LDMS_KAFKA_CONSUMER_NAME_TEMPLATE = "{consumer_group}-consumer"

# PowerScale (from deploy_powerscale/vars/main.yml)
POWERSCALE_DEPLOY_NAME = "karavi-metrics-powerscale"
POWERSCALE_OTEL_DEPLOY_NAME = "otel-collector"
POWERSCALE_CSI_EXPORTER_DEPLOY_NAME = "csi-volume-exporter"
POWERSCALE_CSI_DRIVER_DEPLOY_NAME = "isilon-controller"
POWERSCALE_SECRET_NAME = "isilon-creds"
# Karavi Observability metrics (from CSM Metrics PowerScale + OTEL Collector)
POWERSCALE_KARAVI_METRICS = [
    "karavi_topology_metrics",
    "powerscale_cluster_cpu_use_rate",
    "powerscale_cluster_disk_read_operation_rate",
    "powerscale_cluster_disk_write_operation_rate",
    "powerscale_cluster_disk_throughput_read_rate_megabytes_per_second",
    "powerscale_cluster_disk_throughput_write_rate_megabytes_per_second",
    "powerscale_cluster_total_capacity_terabytes",
    "powerscale_cluster_remaining_capacity_terabytes",
    "powerscale_cluster_used_capacity_percentage",
]

# CSI Volume Exporter metrics (from health monitor)
POWERSCALE_CSI_EXPORTER_METRICS = [
    "powerscale_volume_status",
    "powerscale_volume_count",
    "powerscale_volume_capacity_bytes",
    "powerscale_volume_info",
    "powerscale_volume_age_seconds",
    "powerscale_pvc_status_phase",
    "powerscale_pvc_requested_bytes",
    "powerscale_pvc_count",
    "powerscale_volume_health_abnormal",
    "powerscale_volume_abnormal_events_total",
    "powerscale_node_failure_events_total",
    "powerscale_node_ready",
    "powerscale_storageclass_info",
    "powerscale_total_capacity_bytes",
]

# Combined expected metrics (for backward compatibility)
POWERSCALE_EXPECTED_METRICS = POWERSCALE_KARAVI_METRICS

# PowerScale syslog port (OneFS default)
POWERSCALE_SYSLOG_PORT = 514

# Telemetry config key paths (dot notation for read_yaml_key)
CFG_KEY_PS_METRICS_ENABLED = "telemetry_sources.powerscale.metrics_enabled"
CFG_KEY_PS_LOGS_ENABLED = "telemetry_sources.powerscale.logs_enabled"

# K8s service names (for dynamic IP/port resolution)
SVC_VMSELECT = "vmselect-victoria-cluster"
SVC_VLSELECT = "vlselect-victoria-logs-cluster"
SVC_VLAGENT = "vlagent-vlagent"

# Default port names inside K8s service specs
SVC_PORT_NAME_HTTP = "http"

# Vector bridges
VECTOR_LDMS_APP_NAME = "vector-ldms"
VECTOR_OME_APP_NAME = "vector-ome"

# VAST (from deploy_vast/vars/main.yml)
VAST_SVC_NAME = "vast-external"
VAST_VMSCRAPE_NAME = "vast-storage-metrics"
# K8s Secret object name, not a credential value
VAST_SECRET_NAME = "vast-telemetry-credentials"  # noqa: S105
# Expected VAST metrics based on documentation and screenshot
# The screenshot shows: vast_cluster_metrics_EStoreMigrateMetrics_physical_size_count
VAST_EXPECTED_METRICS = [
    "vast_read_throughput",
    "vast_write_throughput",
    "vast_read_iops",
    "vast_write_iops",
    "vast_capacity_total_bytes",
    "vast_capacity_used_bytes",
    "vast_capacity_avail_bytes",
    "vast_cluster_metrics_EStoreMigrateMetrics_physical_size_count",
]

# Telemetry config key paths for VAST
CFG_KEY_VAST_METRICS_ENABLED = "telemetry_sources.vast.metrics_enabled"
CFG_KEY_VAST_LOGS_ENABLED = "telemetry_sources.vast.logs_enabled"
CFG_KEY_VAST_ENDPOINT = "vast_configuration.vast_endpoint"
CFG_KEY_VAST_PORT = "vast_configuration.vast_metrics_port"

# Telemetry sources list
TELEMETRY_SOURCES = [
    "idrac", "ldms", "powerscale", "ufm",
    "vast", "ome", "sfm",
]

# Telemetry sinks list
TELEMETRY_SINKS = [
    "victoria_metrics",
    "victoria_logs",
    "kafka",
]

# =============================================================================
# CONFIG VALIDATION CONSTANTS
# =============================================================================

IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
)

REQUIRED_CONFIG_FIELDS = [
    "clone_path",
    "report_path",
    "report_name",
]

REQUIRED_SRC_FILES = [
    "telemetry_config.yml",
    "telemetry_packages.yml",
]

# =============================================================================
# CENTRALIZED SHELL COMMANDS
# =============================================================================
# All shell commands used by verification functions.
# Use .format() with named placeholders to fill in runtime values.

CMDS = {
    # --- K8s / kubectl ---
    "kubectl_get_pods_wide": (
        "kubectl get pods -n {namespace} -o wide"
    ),
    "kubectl_get_pods_json_all": (
        "kubectl get pods -n {namespace} -o json 2>/dev/null"
    ),
    "kubectl_get_pods": (
        "kubectl get pods -n {namespace}"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name,STATUS:.status.phase'"
    ),
    "kubectl_get_pods_by_prefix": (
        "kubectl get pods -n {namespace}"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name,STATUS:.status.phase'"
        " | grep '^{prefix}'"
    ),
    "kubectl_get_pods_json_by_label": (
        "kubectl get pods -n {namespace}"
        " -l {label_selector}"
        " -o json 2>/dev/null"
    ),
    "kubectl_get_deploy_selector": (
        "kubectl get deploy {name} -n {namespace}"
        " -o jsonpath='{{.spec.selector.matchLabels}}'"
        " 2>/dev/null"
    ),
    "kubectl_get_pods_json_by_selector": (
        "kubectl get pods -n {namespace}"
        " -l '{label_selector}'"
        " -o json 2>/dev/null"
    ),
    "kubectl_get_pod_count": (
        "kubectl get pods -n {namespace}"
        " --no-headers"
        " | grep '^{prefix}' | wc -l"
    ),
    "kubectl_get_svc": (
        "kubectl get svc -n {namespace}"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name'"
    ),
    "kubectl_get_nodes_ready": (
        "kubectl get nodes --no-headers"
        " -o custom-columns='NAME:.metadata.name,"
        "READY:.status.conditions[-1].status'"
    ),

    # --- StatefulSet ---
    "kubectl_get_sts_ready": (
        "kubectl get statefulset {name} -n {namespace}"
        " -o jsonpath='{{.status.readyReplicas}}' 2>/dev/null"
    ),

    # --- Deployment ---
    "kubectl_get_deploy_ready": (
        "kubectl get deployment {name} -n {namespace}"
        " -o jsonpath='{{.status.readyReplicas}}' 2>/dev/null"
    ),

    # --- Pod containers ---
    "kubectl_get_pod_containers": (
        "kubectl get pod {pod_name} -n {namespace}"
        " -o jsonpath='{{range .status.containerStatuses[*]}}"
        "{{.name}}={{.ready}}{{\"\\n\"}}{{end}}'"
        " 2>/dev/null"
    ),

    # --- Pod by label ---
    "kubectl_get_pod_by_label": (
        "kubectl get pods -n {namespace}"
        " -l app={label}"
        " -o jsonpath='{{.items[0].metadata.name}}'"
        " 2>/dev/null"
    ),

    # --- Kafka ---
    "kafka_wait_ready": (
        "kubectl wait kafka/{kafka_cr} -n {namespace}"
        " --for=condition=Ready --timeout=10s 2>/dev/null"
        " && echo ready || echo not_ready"
    ),
    "kafka_get_topics_cr": (
        "kubectl get kafkatopic -n {namespace}"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name' 2>/dev/null"
    ),
    "kafka_topic_ready": (
        "kubectl get kafkatopic {topic} -n {namespace}"
        " -o jsonpath='{{.status.conditions[?(@.type==\"Ready\")].status}}'"
        " 2>/dev/null"
    ),

    # --- KafkaUser ---
    "kubectl_get_kafkauser": (
        "kubectl get kafkauser {name} -n {namespace}"
        " --no-headers 2>/dev/null && echo exists || echo missing"
    ),

    # --- VictoriaPump ---
    "victoriapump_container_running": (
        "kubectl get pod {pod_name} -n {namespace}"
        " -o jsonpath='{{.status.containerStatuses[?(@.name==\"victoria-pump\")].ready}}'"
        " 2>/dev/null"
    ),

    # --- Files ---
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",

    # --- Ansible / Playbook ---
    "ansible_playbook": (
        "cd {workdir} && ansible-playbook {playbook}"
        " --tags {tag} -v 2>&1"
    ),

    # --- LDMS specific ---
    "ldms_sampler_conf_exists": (
        "test -f {share_path}/samplers/sampler.conf"
        " && echo exists || echo missing"
    ),

    # --- Resolve kube_vip from orchestrator inventory ---
    "read_kube_vip_ip": (
        "python3 -c \""
        "import yaml;"
        "inv=yaml.safe_load(open('{inventory_path}'));"
        "print(inv['all']['children']['kube_vip_group']"
        "['hosts']['kube-vip']['ansible_host'])"
        "\" 2>/dev/null"
    ),

    # --- Resolve telemetry config field ---
    "read_telemetry_config_field": (
        "python3 -c \""
        "import yaml;"
        "cfg=yaml.safe_load(open('{config_path}'));"
        "print(cfg.get('{field}', ''))"
        "\" 2>/dev/null"
    ),

    # --- PowerScale / isilon-creds secret ---
    "kubectl_get_secret": (
        "kubectl get secret {name} -n {namespace}"
        " -o json 2>/dev/null"
    ),
    "kubectl_get_secret_data": (
        "kubectl get secret {name} -n {namespace}"
        " -o jsonpath='{{.data.{key}}}' 2>/dev/null"
    ),

    # --- VictoriaMetrics queries ---
    "vm_query_metric_names": (
        "curl -sk 'https://{vmselect_ip}:{vmselect_port}"
        "/select/0/prometheus/api/v1/label/__name__/values'"
    ),
    "vm_query_instant": (
        "curl -sk 'https://{vmselect_ip}:{vmselect_port}"
        "/select/0/prometheus/api/v1/query?query={query}'"
    ),
    # --- iDRAC VictoriaMetrics data ---
    "vm_query_idrac_service_tag": (
        "curl -s --max-time 15"
        " 'http://{vmselect_ip}:{vmselect_port}"
        "/select/0/prometheus/api/v1/query?query={encoded_query}'"
    ),

    # --- VictoriaLogs queries ---
    "vl_query_logs": (
        "curl -sk 'https://{vlselect_ip}:{vlselect_port}"
        "/select/logsql/query?query={query}&limit={limit}&start=-{range}'"
    ),

    # --- Service external IP ---
    "kubectl_get_svc_lb_ip": (
        "kubectl get svc {name} -n {namespace}"
        " -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'"
        " 2>/dev/null"
    ),
    "kubectl_get_svc_json": (
        "kubectl get svc {name} -n {namespace}"
        " -o json 2>/dev/null"
    ),
    "kubectl_get_svc_port": (
        "kubectl get svc {name} -n {namespace}"
        " -o jsonpath='{{.spec.ports[?(@.name==\"{port_name}\")].port}}'"
        " 2>/dev/null"
    ),
    "kubectl_get_svc_first_port": (
        "kubectl get svc {name} -n {namespace}"
        " -o jsonpath='{{.spec.ports[0].port}}'"
        " 2>/dev/null"
    ),

    # --- OME REST API ---
    "ome_get_forwarder": (
        "curl -sk -u '{user}:{password}' --max-time 15"
        " 'https://{ome_ip}/api/DataForwardingService/"
        "Forwarders({forwarder_id})'"
    ),
    "ome_get_forwarder_status": (
        "curl -sk -u '{user}:{password}' --max-time 15"
        " 'https://{ome_ip}/api/DataForwardingService/"
        "Forwarders({forwarder_id})/ConnectivityStatus'"
    ),
    "ome_get_forwarders_list": (
        "curl -sk -u '{user}:{password}' --max-time 15"
        " 'https://{ome_ip}/api/DataForwardingService/Forwarders'"
    ),

    # --- OpenSSL ---
    "openssl_create_pfx": (
        "openssl pkcs12 -export"
        " -out {cert_dir}/user.pfx"
        " -inkey {cert_dir}/user.key"
        " -in {cert_dir}/user.crt"
        " -passout pass:{password} 2>&1"
    ),

    # --- OME REST API: upload certificates ---
    # Upload server certificate (CA cert) - X.509 format, base64 encoded
    "ome_upload_server_cert": (
        "curl -sk -u '{user}:{password}' --max-time 30"
        " -X POST"
        " -H 'Content-Type: application/json'"
        " -d '{{\"CertData\": \"{cert_data_b64}\","
        " \"CertFormat\": \"X_509\","
        " \"ClientType\": \"KAFKA\"}}'"
        " 'https://{ome_ip}/api/ApplicationService/"
        "Actions/ApplicationService.UploadServerCertificate'"
        " -w '\\nHTTP_CODE:%{{http_code}}'"
    ),
    # Upload client certificate (PFX) - PKCS12 format, base64 encoded
    "ome_upload_client_cert": (
        "curl -sk -u '{user}:{password}' --max-time 30"
        " -X POST"
        " -H 'Content-Type: application/json'"
        " -d '{{\"CertData\": \"{cert_data_b64}\","
        " \"CertFormat\": \"PKCS_12\","
        " \"ClientType\": \"KAFKA\","
        " \"Passphrase\": \"{pfx_secret}\"}}'"
        " 'https://{ome_ip}/api/ApplicationService/"
        "Actions/ApplicationService.UploadClientCertificate'"
        " -w '\\nHTTP_CODE:%{{http_code}}'"
    ),
    # View client certificate
    "ome_view_client_cert": (
        "curl -sk -u '{user}:{password}' --max-time 15"
        " -X POST"
        " -H 'Content-Type: application/json'"
        " -d '{{\"ClientType\": \"KAFKA\"}}'"
        " 'https://{ome_ip}/api/ApplicationService/"
        "Actions/ApplicationService.ViewClientCertificate'"
    ),
    # Test Kafka connection
    "ome_test_kafka_connection": (
        "curl -sk -u '{user}:{password}' --max-time 30"
        " -X POST"
        " -H 'Content-Type: application/json'"
        " -d '{{\"Id\": {forwarder_id},"
        " \"ForwarderConfigurations\": ["
        "{{\"ConfigurationName\": \"OMEIdentifier\", "
        "\"ConfigurationValue\": \"{ome_identifier}\"}},"
        "{{\"ConfigurationName\": \"ClientType\", \"ConfigurationValue\": \"KAFKA\"}},"
        "{{\"ConfigurationName\": \"BrokerList\", \"ConfigurationValue\": \"{broker_list}\"}},"
        "{{\"ConfigurationName\": \"AuthMode\", \"ConfigurationValue\": \"2\"}},"
        "{{\"ConfigurationName\": \"ServerCert\", \"ConfigurationValue\": \"true\"}},"
        "{{\"ConfigurationName\": \"ClientCert\", \"ConfigurationValue\": \"true\"}}"
        "]}}'"
        " 'https://{ome_ip}/api/DataForwardingService/"
        "Actions/DataForwardingService.TestConnection'"
        " -w '\\nHTTP_CODE:%{{http_code}}'"
    ),
    # Update forwarder settings
    "ome_update_forwarder_settings": (
        "curl -sk -u '{user}:{password}' --max-time 30"
        " -X POST"
        " -H 'Content-Type: application/json'"
        " -d '{{\"Id\": {forwarder_id},"
        " \"Enabled\": true,"
        " \"ForwarderConfigurations\": ["
        "{{\"ConfigurationName\": \"OMEIdentifier\", "
        "\"ConfigurationValue\": \"{ome_identifier}\"}},"
        "{{\"ConfigurationName\": \"ClientType\", \"ConfigurationValue\": \"KAFKA\"}},"
        "{{\"ConfigurationName\": \"BrokerList\", \"ConfigurationValue\": \"{broker_list}\"}},"
        "{{\"ConfigurationName\": \"AuthMode\", \"ConfigurationValue\": \"2\"}},"
        "{{\"ConfigurationName\": \"ServerCert\", \"ConfigurationValue\": \"true\"}},"
        "{{\"ConfigurationName\": \"ClientCert\", \"ConfigurationValue\": \"true\"}},"
        "{{\"ConfigurationName\": \"HeartBeat\", \"ConfigurationValue\": \"120\"}}"
        "]}}'"
        " 'https://{ome_ip}/api/DataForwardingService/"
        "Actions/DataForwardingService.ForwarderSettings'"
        " -w '\\nHTTP_CODE:%{{http_code}}'"
    ),
    # Get forwarder configuration
    "ome_get_forwarder_config": (
        "curl -sk -u '{user}:{password}' --max-time 15"
        " 'https://{ome_ip}/api/DataForwardingService/"
        "Forwarders({forwarder_id})/ForwarderConfigurations'"
    ),

    # --- PowerScale syslog config via SSH ---
    "powerscale_syslog_view": (
        "sshpass -p '{password}'"
        " ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no"
        " {user}@{host}"
        " 'isi audit settings global view'"
    ),
    "powerscale_syslog_configure": (
        "sshpass -p '{password}'"
        " ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no"
        " {user}@{host}"
        " '{isi_cmd}'"
    ),

    # --- Cleanup verification ---
    "kubectl_count_resources": (
        "kubectl get {resource} -n {namespace}"
        " --no-headers --ignore-not-found 2>/dev/null | wc -l"
    ),
    "kubectl_get_ns": (
        "kubectl get namespace {namespace}"
        " --no-headers --ignore-not-found 2>/dev/null"
    ),
}

