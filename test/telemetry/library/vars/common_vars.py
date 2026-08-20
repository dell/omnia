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

Common vars (ssh_opts, config names, timeouts) live in the
``omnia_auto`` package and are set via ``omnia_auto.configure()``
in conftest.py.

Only module-specific constants remain here.
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

# src/ paths — used when dataset is empty (default: use src/ directly)
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
TELEMETRY_STORAGE_CONFIG_FILE = "telemetry_storage_config.yml"
TELEMETRY_PACKAGES_FILE = "telemetry_packages.yml"

INPUT_FILES = [
    TELEMETRY_CONFIG_FILE,
    TELEMETRY_STORAGE_CONFIG_FILE,
    TELEMETRY_PACKAGES_FILE,
]

# =============================================================================
# PLAYBOOK CONFIGURATION
# =============================================================================

PLAYBOOK_ENTRY_POINT = "playbooks/telemetry.yml"
PLAYBOOK_WORKDIR = "src/telemetry"

# Valid playbook tags
PLAYBOOK_TAGS = [
    "precheck",
    "validate",
    "execute",
    "deploy",
    "cleanup",
    "upgrade",
    "rollback",
]

# Cleanup sub-tags (tag-wise cleanup)
CLEANUP_TAGS = [
    "cleanup_kafka",
    "cleanup_victoria_metrics",
    "cleanup_victoria_logs",
    "cleanup_idrac",
    "cleanup_ldms",
    "cleanup_ome",
    "cleanup_powerscale",
    "cleanup_dcgm",
    "cleanup_ufm",
    "cleanup_vast",
    "cleanup_sfm",
    "cleanup_skyway",
    "cleanup_powervault",
]

# =============================================================================
# K8S CONSTANTS
# =============================================================================

TELEMETRY_NAMESPACE = "telemetry"

# =============================================================================
# SINK COMPONENT NAMES (used for pod verification)
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

# Kafka pod prefixes (Strimzi naming: <cluster>-kafka-<n> for brokers)
# Kafka CR name in deploy_kafka is "kafka", so pods = "kafka-kafka-*"
KAFKA_POD_PREFIXES = {
    "broker": "kafka-kafka",
    "controller": "kafka-controller",
}

KAFKA_BRIDGE_PREFIX = "kafka-bridge"
KAFKA_CR_NAME = "kafka"

# TLS secret name
VICTORIA_TLS_SECRET = "victoria-tls"

# Victoria cluster service names (from deploy_victoria vars)
VM_SERVICES = {
    "vminsert": "vminsert-victoria-cluster",
    "vmselect": "vmselect-victoria-cluster",
    "vmstorage": "vmstorage-victoria-cluster",
}
VL_SERVICES = {
    "vlinsert": "vlinsert-victoria-logs-cluster",
    "vlselect": "vlselect-victoria-logs-cluster",
    "vlstorage": "vlstorage-victoria-logs-cluster",
}

# VM operator
VM_OPERATOR_DEPLOY = "victoria-metrics-operator"

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

# LDMS (from deploy_ldms/vars/main.yml)
LDMS_AGG_POD = "nersc-ldms-aggr"
LDMS_AGG_STS_NAME = "nersc-ldms-aggr"
LDMS_STORE_POD = "nersc-ldms-store"
LDMS_STORE_NAME = "nersc-ldms-store"
LDMS_KAFKA_TOPIC = "ldms"

# DCGM
DCGM_POD_PREFIX = "dcgm-exporter"

# Vector bridges (from deploy_ldms/vars and deploy_ome/vars)
VECTOR_LDMS_PREFIX = "vector-ldms"
VECTOR_LDMS_APP_NAME = "vector-ldms"
VECTOR_OME_PREFIX = "vector-ome"
VECTOR_OME_APP_NAME = "vector-ome"

# OME Kafka user
OME_KAFKA_USER = "vector-ome-user"

# Telemetry sources as listed in telemetry_config.yml
TELEMETRY_SOURCES = [
    "idrac",
    "ldms",
    "dcgm",
    "powerscale",
    "ufm",
    "vast",
    "ome",
    "sfm",
    "skyway",
    "powervault",
]

# =============================================================================
# TELEMETRY SINKS
# =============================================================================

TELEMETRY_SINKS = [
    "victoria_metrics",
    "victoria_logs",
    "kafka",
]

# =============================================================================
# SHARED PATH DEFAULTS (runtime on target host)
# =============================================================================

DEFAULT_OMNIA_DATA_PATH = "/opt/omnia"
DEFAULT_PROJECT_NAME = "project_default"

# =============================================================================
# CONFIG VALIDATION CONSTANTS
# =============================================================================

IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
)

REQUIRED_CONFIG_FIELDS = [
    "project_name",
    "clone_path",
    "report_path",
    "report_name",
]

REQUIRED_DATASET_FILES = [
    "input/telemetry_config.yml",
    "input/telemetry_storage_config.yml",
    "input/telemetry_packages.yml",
]

REQUIRED_SRC_FILES = [
    "telemetry_config.yml",
    "telemetry_storage_config.yml",
    "telemetry_packages.yml",
]

# =============================================================================
# CENTRALIZED SHELL COMMANDS
# =============================================================================
# All shell commands used by verification functions.
# Use .format() with named placeholders to fill in runtime values.

CMDS = {
    # --- K8s / kubectl ---
    "kubectl_get_pods": (
        "kubectl get pods -n {namespace}"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name,STATUS:.status.phase'"
    ),
    "kubectl_get_pods_wide": (
        "kubectl get pods -n {namespace} -o wide"
    ),
    "kubectl_get_pods_by_prefix": (
        "kubectl get pods -n {namespace}"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name,STATUS:.status.phase'"
        " | grep '^{prefix}'"
    ),
    "kubectl_get_pod_count": (
        "kubectl get pods -n {namespace}"
        " --no-headers"
        " | grep '^{prefix}' | wc -l"
    ),
    "kubectl_get_pvc": (
        "kubectl get pvc -n {namespace}"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name,CAPACITY:.status.capacity.storage'"
    ),
    "kubectl_get_svc": (
        "kubectl get svc -n {namespace}"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name,TYPE:.spec.type,"
        "CLUSTER-IP:.spec.clusterIP,EXTERNAL-IP:.status.loadBalancer.ingress[0].ip,"
        "PORT:.spec.ports[0].port'"
    ),
    "kubectl_get_secret": (
        "kubectl get secret {secret_name} -n {namespace}"
        " --no-headers 2>/dev/null && echo exists || echo missing"
    ),
    "kubectl_get_nodes_ready": (
        "kubectl get nodes --no-headers"
        " -o custom-columns='NAME:.metadata.name,"
        "STATUS:.status.conditions[-1].type,"
        "READY:.status.conditions[-1].status,"
        "ROLE:.metadata.labels.node-role\\.kubernetes\\.io/control-plane'"
    ),
    "kubectl_get_control_plane": (
        "kubectl get nodes"
        " -l node-role.kubernetes.io/control-plane"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name,"
        "READY:.status.conditions[-1].status'"
    ),
    "kubectl_get_workers": (
        "kubectl get nodes"
        " -l '!node-role.kubernetes.io/control-plane'"
        " --no-headers"
        " -o custom-columns='NAME:.metadata.name,"
        "READY:.status.conditions[-1].status'"
    ),
    "kubectl_get_all_pods_status": (
        "kubectl get pods --all-namespaces"
        " --no-headers"
        " --field-selector metadata.namespace!={namespace}"
        " -o custom-columns='NAMESPACE:.metadata.namespace,"
        "NAME:.metadata.name,STATUS:.status.phase'"
    ),
    "kubectl_available": (
        "kubectl version --client --short 2>/dev/null || kubectl version --client 2>/dev/null"
    ),

    # --- Connectivity ---
    "ping": "ping -c 2 -W 3 {host} 2>/dev/null",
    "ssh_check": (
        "ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no"
        " -o BatchMode=yes {user}@{host} 'echo ok' 2>/dev/null"
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

    # --- VictoriaMetrics health ---
    "vm_health": (
        "curl -sk https://{host}:{port}/health 2>/dev/null"
    ),

    # --- Kafka ---
    "kafka_topics": (
        "kubectl exec -n {namespace} {broker_pod} --"
        " /opt/kafka/bin/kafka-topics.sh --list"
        " --bootstrap-server localhost:9092 2>/dev/null"
    ),
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

    # --- StatefulSet ---
    "kubectl_get_sts_ready": (
        "kubectl get statefulset {name} -n {namespace}"
        " -o jsonpath='{{.status.readyReplicas}}' 2>/dev/null"
    ),
    "kubectl_get_sts": (
        "kubectl get statefulset {name} -n {namespace}"
        " -o jsonpath='{{.status.readyReplicas}}/{{.spec.replicas}}' 2>/dev/null"
    ),

    # --- Deployment ---
    "kubectl_get_deploy_ready": (
        "kubectl get deployment {name} -n {namespace}"
        " -o jsonpath='{{.status.readyReplicas}}' 2>/dev/null"
    ),
    "kubectl_get_deploy": (
        "kubectl get deployment {name} -n {namespace}"
        " -o jsonpath='{{.status.readyReplicas}}/{{.spec.replicas}}' 2>/dev/null"
    ),

    # --- Pod containers ---
    "kubectl_get_pod_containers": (
        "kubectl get pod {pod_name} -n {namespace}"
        " -o jsonpath='{{range .status.containerStatuses[*]}}{{.name}}={{.ready}}{{\"\\n\"}}{{end}}'"
        " 2>/dev/null"
    ),

    # --- KafkaUser ---
    "kubectl_get_kafkauser": (
        "kubectl get kafkauser {name} -n {namespace}"
        " --no-headers 2>/dev/null && echo exists || echo missing"
    ),

    # --- iDRAC specific ---
    "kubectl_get_idrac_pod_name": (
        "kubectl get pods -n {namespace}"
        " -l app={label}"
        " -o jsonpath='{{.items[0].metadata.name}}'"
        " 2>/dev/null"
    ),
    "kubectl_get_idrac_container_status": (
        "kubectl get pod {pod_name} -n {namespace}"
        " -o jsonpath='{{range .status.containerStatuses[*]}}{{.name}}={{.ready}}{{\"\\n\"}}{{end}}'"
        " 2>/dev/null"
    ),

    # --- VictoriaMetrics health ---
    "victoriapump_metrics": (
        "kubectl exec -n {namespace} {pod_name} -c victoria-pump --"
        " wget -qO- http://localhost:2112/metrics 2>/dev/null"
    ),

    # --- LDMS specific ---
    "ldms_sampler_conf_exists": (
        "test -f {share_path}/samplers/sampler.conf && echo exists || echo missing"
    ),
}
