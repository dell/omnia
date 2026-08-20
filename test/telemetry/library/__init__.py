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

"""Telemetry test module — public API."""

from library.functions import (
    # K8s verification
    verify_kubectl_available,
    verify_control_plane_ready,
    verify_worker_nodes_ready,
    verify_pods_healthy,
    verify_kube_vip_reachable,
    get_pods_by_prefix,
    get_pod_count,
    verify_secret_exists,
    # Input verification
    verify_input_file_exists,
    verify_all_input_files_exist,
    load_telemetry_config_from_target,
    get_kube_vip_from_config,
    is_source_enabled,
    is_sink_enabled,
    # Validation
    validate_all,
    ConfigValidationError,
    # Sink verification
    verify_vm_cluster_pods,
    verify_vmagent_pods,
    verify_vm_services,
    verify_vm_pvc_sizes,
    verify_vm_operator,
    verify_vl_cluster_pods,
    verify_vlagent_pods,
    verify_kafka_pods,
    verify_kafka_ready,
    verify_kafka_topics,
    verify_kafka_bridge,
    # Source verification
    verify_idrac_sts_ready,
    verify_idrac_containers,
    verify_idrac_kafka_topic,
    verify_idrac_victoriapump,
    verify_ldms_aggregator,
    verify_ldms_store,
    verify_vector_ldms,
    verify_ldms_kafka_topic,
    verify_ldms_sampler_config,
    verify_vector_ome,
    verify_ome_kafka_user,
)
from library.vars import TEST_CASES
from library.messages import TEST_LOG_MSGS, TEST_ASSERT_MSGS

__all__ = [
    # K8s verification
    "verify_kubectl_available",
    "verify_control_plane_ready",
    "verify_worker_nodes_ready",
    "verify_pods_healthy",
    "verify_kube_vip_reachable",
    "get_pods_by_prefix",
    "get_pod_count",
    "verify_secret_exists",
    # Input verification
    "verify_input_file_exists",
    "verify_all_input_files_exist",
    "load_telemetry_config_from_target",
    "get_kube_vip_from_config",
    "is_source_enabled",
    "is_sink_enabled",
    # Validation
    "validate_all",
    "ConfigValidationError",
    # Sink verification
    "verify_vm_cluster_pods",
    "verify_vmagent_pods",
    "verify_vm_services",
    "verify_vm_pvc_sizes",
    "verify_vm_operator",
    "verify_vl_cluster_pods",
    "verify_vlagent_pods",
    "verify_kafka_pods",
    "verify_kafka_ready",
    "verify_kafka_topics",
    "verify_kafka_bridge",
    # Source verification
    "verify_idrac_sts_ready",
    "verify_idrac_containers",
    "verify_idrac_kafka_topic",
    "verify_idrac_victoriapump",
    "verify_ldms_aggregator",
    "verify_ldms_store",
    "verify_vector_ldms",
    "verify_ldms_kafka_topic",
    "verify_ldms_sampler_config",
    "verify_vector_ome",
    "verify_ome_kafka_user",
    # Vars and messages
    "TEST_CASES",
    "TEST_LOG_MSGS",
    "TEST_ASSERT_MSGS",
]
