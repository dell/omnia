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

"""Telemetry test module — functions sub-package."""

from omnia_auto import (
    load_test_config,
    load_test_credentials,
    get_testinfra_host,
    run_on_host,
    run_playbook,
    log,
)

from library.functions.telemetry_func import (
    get_telemetry_input_path,
    verify_input_file_exists,
    verify_all_input_files_exist,
    load_telemetry_config_from_target,
    get_kube_vip_from_config,
    is_source_enabled,
    is_sink_enabled,
)
from library.functions.k8s_func import (
    verify_kubectl_available,
    verify_control_plane_ready,
    verify_worker_nodes_ready,
    verify_pods_healthy,
    verify_kube_vip_reachable,
    get_pods_by_prefix,
    get_pod_count,
    verify_secret_exists,
)
from library.functions.host_func import (
    sync_project_to_remote,
    sync_telemetry_input,
    get_dataset_input_dir,
)
from library.functions.validation_func import (
    validate_all,
    ConfigValidationError,
)
from library.functions.sink_func import (
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
    verify_kafka_persistence,
)
from library.functions.source_func import (
    verify_idrac_sts_ready,
    verify_idrac_containers,
    verify_idrac_kafka_topic,
    verify_idrac_victoriapump,
    verify_idrac_service,
    verify_ldms_aggregator,
    verify_ldms_store,
    verify_vector_ldms,
    verify_ldms_kafka_topic,
    verify_ldms_sampler_config,
    verify_vector_ome,
    verify_ome_kafka_user,
    verify_ome_sink_prerequisites,
)
from library.functions.cleanup_func import (
    verify_idrac_cleaned,
    verify_ldms_cleaned,
    verify_ome_cleaned,
    verify_dcgm_cleaned,
    verify_ufm_cleaned,
    verify_vast_cleaned,
    verify_sfm_cleaned,
    verify_kafka_cleaned,
    verify_victoria_metrics_cleaned,
    verify_victoria_logs_cleaned,
    verify_no_pods_remaining,
    verify_no_pvcs_remaining,
)

__all__ = [
    # omnia_auto re-exports
    "load_test_config",
    "load_test_credentials",
    "get_testinfra_host",
    "run_on_host",
    "run_playbook",
    "log",
    # telemetry domain functions
    "get_telemetry_input_path",
    "verify_input_file_exists",
    "verify_all_input_files_exist",
    "load_telemetry_config_from_target",
    "get_kube_vip_from_config",
    "is_source_enabled",
    "is_sink_enabled",
    # k8s verification
    "verify_kubectl_available",
    "verify_control_plane_ready",
    "verify_worker_nodes_ready",
    "verify_pods_healthy",
    "verify_kube_vip_reachable",
    "get_pods_by_prefix",
    "get_pod_count",
    "verify_secret_exists",
    # host/sync
    "sync_project_to_remote",
    "sync_telemetry_input",
    "get_dataset_input_dir",
    # validation
    "validate_all",
    "ConfigValidationError",
    # sinks
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
    "verify_kafka_persistence",
    # sources
    "verify_idrac_sts_ready",
    "verify_idrac_containers",
    "verify_idrac_kafka_topic",
    "verify_idrac_victoriapump",
    "verify_idrac_service",
    "verify_ldms_aggregator",
    "verify_ldms_store",
    "verify_vector_ldms",
    "verify_ldms_kafka_topic",
    "verify_ldms_sampler_config",
    "verify_vector_ome",
    "verify_ome_kafka_user",
    "verify_ome_sink_prerequisites",
    # cleanup verification
    "verify_idrac_cleaned",
    "verify_ldms_cleaned",
    "verify_ome_cleaned",
    "verify_dcgm_cleaned",
    "verify_ufm_cleaned",
    "verify_vast_cleaned",
    "verify_sfm_cleaned",
    "verify_kafka_cleaned",
    "verify_victoria_metrics_cleaned",
    "verify_victoria_logs_cleaned",
    "verify_no_pods_remaining",
    "verify_no_pvcs_remaining",
]
