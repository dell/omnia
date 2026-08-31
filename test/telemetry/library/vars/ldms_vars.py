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
LDMS Telemetry — Variables and Constants.

Component names, service names, and configuration paths for LDMS telemetry.
"""

# =============================================================================
# LDMS K8S COMPONENT NAMES
# =============================================================================

# LDMS aggregator StatefulSet name
LDMS_AGG_STS_NAME = "nersc-ldms-aggr"

# LDMS store StatefulSet name prefix
LDMS_STORE_NAME = "nersc-ldms-store"

# Vector-LDMS bridge deployment name
VECTOR_LDMS_APP_NAME = "vector-ldms-bridge"

# LDMS Kafka topic name
LDMS_KAFKA_TOPIC = "ldms"

# =============================================================================
# LDMS FUNCTIONAL GROUPS
# =============================================================================

# Functional groups in orchestrator inventory that run LDMS samplers
# These are the exact group names with architecture suffixes
LDMS_FUNCTIONAL_GROUPS = [
    "slurm_control_node_x86_64",
    "slurm_node_x86_64",
    "slurm_node_aarch64",
    "login_node_x86_64",
    "login_node_aarch64",
    "login_compiler_node_x86_64",
    "login_compiler_node_aarch64",
]

# =============================================================================
# LDMS SAMPLER SERVICE AND PATHS (on Slurm nodes)
# =============================================================================

# Systemd service name for LDMS sampler
LDMS_SAMPLER_SERVICE = "ldmsd.service"

# LDMS sampler configuration file path
LDMS_SAMPLER_CONF_PATH = "/opt/ovis-ldms/etc/ldms/sampler.conf"

# LDMS sampler environment file path
LDMS_SAMPLER_ENV_PATH = "/opt/ovis-ldms/etc/ldms/ldmsd.sampler.env"

# LDMS binary path for package check
LDMS_BINARY_PATH = "/opt/ovis-ldms/sbin/ldmsd"

# LDMS package name
LDMS_PACKAGE_NAME = "ovis-ldms"

# =============================================================================
# LDMS LOG MESSAGES
# =============================================================================

LDMS_LOG_MSGS = {
    "aggr_checking": "Verifying LDMS aggregator StatefulSet '{sts_name}'",
    "aggr_running": "LDMS aggregator: {count}/{expected} pods running",
    "aggr_not_running": "LDMS aggregator: {count}/{expected} pods running",
    "store_checking": "Verifying LDMS store pods '{store_name}'",
    "store_running": "LDMS store: {count}/{expected} pods running",
    "store_not_running": "LDMS store: only {count}/{expected} pods running",
    "vector_checking": "Verifying Vector-LDMS bridge deployment",
    "vector_running": "Vector-LDMS bridge: {count}/{expected} pods ready",
    "sampler_service_checking": "Verifying LDMS sampler service on Slurm nodes",
    "sampler_service_running": "LDMS sampler service active on all {count} nodes",
    "sampler_service_not_running": "LDMS sampler service not running on {count} nodes",
    "sampler_plugins_checking": "Verifying LDMS sampler plugins configuration",
    "sampler_plugins_match": "LDMS plugins configured correctly on all nodes",
    "sampler_plugins_mismatch": "LDMS plugin mismatch on {count} nodes",
    "package_checking": "Verifying LDMS package installed on Slurm nodes",
    "package_installed": "LDMS package installed on all {count} nodes",
    "package_not_installed": "LDMS package not installed on {count} nodes",
    "kafka_data_verifying": "Verifying latest LDMS data in Kafka topic",
    "kafka_data_success": "LDMS latest data verified for all {count} hosts",
    "kafka_earliest_verifying": "Verifying earliest LDMS data in Kafka topic",
    "kafka_earliest_success": "LDMS earliest data found for {count} hosts",
}

# =============================================================================
# LDMS ASSERT MESSAGES
# =============================================================================

LDMS_ASSERT_MSGS = {
    "aggr_not_running": "LDMS aggregator not running: {count}/{expected} pods",
    "store_not_running": "LDMS store not running: {count}/{expected} pods",
    "vector_not_running": "Vector-LDMS bridge not ready: {count}/{expected} pods",
    "sampler_service_failed": "LDMS service failed on: {nodes}",
    "sampler_plugins_mismatch": "LDMS plugin mismatch on: {nodes}",
    "package_not_installed": "LDMS package not installed on: {nodes}",
    "kafka_data_missing": "LDMS data missing from: {hosts}",
    "kafka_earliest_missing": "No LDMS earliest data found in Kafka topic",
}

# =============================================================================
# LDMS SKIP MESSAGES
# =============================================================================

LDMS_SKIP_MSGS = {
    "ldms_not_enabled": "LDMS not enabled in telemetry_config.yml",
    "no_slurm_nodes": "No Slurm nodes found in cluster_inventory",
    "no_inventory": "cluster_inventory path not configured",
}

# =============================================================================
# LDMS COMMAND TEMPLATES
# =============================================================================

LDMS_CMD_TEMPLATES = {
    # Service check commands (run on Slurm nodes via SSH)
    "check_service_active": "systemctl is-active {service}",
    "check_service_status": "systemctl status {service} --no-pager",

    # Package/binary check commands
    "check_ldms_binary": "test -f {binary_path} && echo 'installed' || echo 'not_installed'",
    "get_ldms_version": "{binary_path} -V 2>&1 | head -1",

    # Config file commands
    "read_sampler_conf": "cat {conf_path}",
    "read_sampler_env": "cat {env_path}",

    # Kafka bridge commands (via kubectl on kube_vip)
    "get_bridge_lb_ip": (
        "kubectl get svc {service} -n {namespace} "
        "-o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'"
    ),
    "get_bridge_lb_port": (
        "kubectl get svc {service} -n {namespace} "
        "-o jsonpath='{{.spec.ports[0].port}}'"
    ),

    # Kafka REST API commands (via curl)
    "rest_create_consumer": (
        "curl -s -X POST http://{bridge_ip}:{port}/consumers/{consumer_group} "
        "-H 'Content-Type: application/vnd.kafka.v2+json' "
        "-d '{{\"name\": \"{consumer_name}\", \"format\": \"json\", "
        "\"auto.offset.reset\": \"{offset}\"}}'"
    ),
    "rest_subscribe_topic": (
        "curl -s -X POST http://{bridge_ip}:{port}/consumers/{consumer_group}"
        "/instances/{consumer_name}/subscription "
        "-H 'Content-Type: application/vnd.kafka.v2+json' "
        "-d '{{\"topics\": [\"{topic}\"]}}'"
    ),
    "rest_consume_records": (
        "curl -s -X GET http://{bridge_ip}:{port}/consumers/{consumer_group}"
        "/instances/{consumer_name}/records "
        "-H 'Accept: application/vnd.kafka.json.v2+json'"
    ),
    "rest_delete_consumer": (
        "curl -s -X DELETE http://{bridge_ip}:{port}/consumers/{consumer_group}"
        "/instances/{consumer_name}"
    ),
}
