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
Telemetry — Functions

Common utilities come from the omnia_auto package.
Module-specific functions live in separate files:
  - telemetry_func.py   — common (kube_vip, config, VM/VL queries, iDRAC VM data)
  - k8s_func.py         — K8s resource verification (all pods, deploys, sts)
  - powerscale_func.py  — PowerScale source verification
  - ufm_func.py         — UFM source verification
  - ome_func.py         — OME Kafka connectivity verification
  - sfm_func.py         — SFM Prometheus Remote Write integration
  - sfm_metrics_func.py — attributed SFM-to-VictoriaMetrics verification
  - validation_func.py  — config validation
"""

# --- Common (from omnia_auto package) ---
from omnia_auto import (
    Colors,
    Symbols,
    log,
    set_debug_mode,
    TestLogger,
    get_test_output,
    get_testinfra_host,
    load_test_config,
    load_test_credentials,
    get_module_root,
    run_on_host,
    is_local_execution,
    TestReport,
    get_current_report,
    set_current_report,
    run_playbook as _run_playbook,
)
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

# --- Telemetry common verification ---
from .telemetry_func import (
    resolve_kube_vip_ip,
    get_kube_vip_host,
    is_source_enabled,
    is_logs_enabled,
    is_sink_enabled,
    load_telemetry_config_from_target,
    check_target_connectivity,
    check_env_vars_present,
    run_on_kube_vip,
    query_vm_metric_names,
    query_vm_instant,
    get_vmselect_endpoint,
    get_vlselect_endpoint,
    verify_idrac_vm_data,
    get_idrac_service_tags,
)

# --- K8s resource verification ---
from .k8s_func import (
    verify_all_pods_running,
    verify_pods_by_prefix,
    verify_sts_ready,
    verify_deploy_ready,
    verify_deploy_pods_detail,
    verify_pod_containers,
    verify_kafka_ready,
    verify_kafka_topics,
    verify_kafka_topic_ready,
    verify_services_exist,
    verify_services_detail,
)

# --- iDRAC verification ---
from .idrac_func import (
    verify_idrac_pod_count,
    verify_mysql_data_in_pods,
    verify_receiver_collecting,
)

# --- OME verification ---
from .ome_func import (
    verify_ome_kafka_connectivity,
    get_ome_forwarders,
    run_external_kafka_playbook,
    verify_external_kafka_certs,
    convert_certs_to_pfx,
    verify_ome_kafka_user_cr,
    upload_ome_server_cert,
    upload_ome_client_cert,
    view_ome_client_cert,
    send_ome_kafka_test_connection,
    update_ome_forwarder_settings,
)

# --- SFM verification and configuration ---
from .sfm_func import (
    configure_sfm_observability,
    configure_sfm_switch,
    verify_sfm_omnia_pods,
    verify_sfm_omnia_services,
)
from .sfm_metrics_func import verify_sfm_metrics_in_victoria

# --- VAST verification ---
from .vast_func import (
    verify_vast_external_service,
    verify_vast_vmscrape,
    verify_vast_credentials_secret,
    verify_vast_metrics,
    verify_vast_logs,
    get_vast_endpoint_from_config,
)

# --- Validation ---
from .validation_func import (
    validate_test_config,
    validate_all,
    ConfigValidationError,
)


def run_playbook(tag=None, **kwargs):
    """Wrapper that injects module-specific playbook and workdir."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )


__all__ = [
    # omnia_auto common
    "Colors",
    "Symbols",
    "log",
    "set_debug_mode",
    "TestLogger",
    "get_test_output",
    "get_testinfra_host",
    "load_test_config",
    "load_test_credentials",
    "get_module_root",
    "run_on_host",
    "is_local_execution",
    "TestReport",
    "get_current_report",
    "set_current_report",
    "run_playbook",
    # telemetry common
    "resolve_kube_vip_ip",
    "get_kube_vip_host",
    "is_source_enabled",
    "is_logs_enabled",
    "is_sink_enabled",
    "load_telemetry_config_from_target",
    "check_target_connectivity",
    "check_env_vars_present",
    "run_on_kube_vip",
    "query_vm_metric_names",
    "query_vm_instant",
    "get_vmselect_endpoint",
    "get_vlselect_endpoint",
    "verify_idrac_vm_data",
    "get_idrac_service_tags",
    # k8s
    "verify_all_pods_running",
    "verify_pods_by_prefix",
    "verify_sts_ready",
    "verify_deploy_ready",
    "verify_deploy_pods_detail",
    "verify_pod_containers",
    "verify_kafka_ready",
    "verify_kafka_topics",
    "verify_kafka_topic_ready",
    "verify_services_exist",
    "verify_services_detail",
    # idrac
    "verify_idrac_pod_count",
    "verify_mysql_data_in_pods",
    "verify_receiver_collecting",
    # ome
    "verify_ome_kafka_connectivity",
    "get_ome_forwarders",
    "run_external_kafka_playbook",
    "verify_external_kafka_certs",
    "convert_certs_to_pfx",
    "verify_ome_kafka_user_cr",
    "upload_ome_server_cert",
    "upload_ome_client_cert",
    "view_ome_client_cert",
    "send_ome_kafka_test_connection",
    "update_ome_forwarder_settings",
    # sfm
    "configure_sfm_observability",
    "configure_sfm_switch",
    "verify_sfm_omnia_pods",
    "verify_sfm_omnia_services",
    "verify_sfm_metrics_in_victoria",
    # vast
    "verify_vast_external_service",
    "verify_vast_vmscrape",
    "verify_vast_credentials_secret",
    "verify_vast_metrics",
    "verify_vast_logs",
    "get_vast_endpoint_from_config",
    # validation
    "validate_test_config",
    "validate_all",
    "ConfigValidationError",
]
