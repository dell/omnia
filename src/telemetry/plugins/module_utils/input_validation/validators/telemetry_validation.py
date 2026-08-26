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
# pylint: disable=import-error,no-name-in-module,too-many-arguments,unused-argument
# pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-lines
# pylint: disable=too-many-positional-arguments,line-too-long
"""
This module contains functions for validating telemetry configuration.
"""
import os
import subprocess

import yaml
from ansible.module_utils.input_validation.messages import en_us_validation_msg
from ansible.module_utils.input_validation.core.validation_utils import create_error_msg
from ansible.module_utils.input_validation.validators import powerscale_telemetry_validation


def validate_telemetry_config(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the telemetry configuration from telemetry_config.yml.

    This function validates the new three-layer telemetry configuration structure:
    - telemetry_sources (idrac, ldms, powerscale, ufm, vast, ome)
    - telemetry_bridges (vector_ldms, vector_ome)
    - telemetry_sinks (victoria_metrics, victoria_logs, kafka)

    Args:
        input_file_path: Path to telemetry_config.yml
        data: Parsed YAML data from telemetry_config.yml
        logger: Logger instance
        module: Ansible module instance
        omnia_base_dir: Base directory of Omnia installation
        module_utils_base: Base directory of module_utils
        project_name: Name of the project

    Returns:
        List of error messages (empty if validation passes)
    """
    errors = []

    # =========================================================================
    # L2: Validate cluster_inventory — file existence under telemetry input dir
    # =========================================================================
    cluster_inventory = data.get("cluster_inventory", "")
    if cluster_inventory:
        # Determine the telemetry input directory
        # module_utils_base = /path/to/omnia/src/telemetry/plugins/module_utils
        # telemetry_root = /path/to/omnia/src/telemetry (2 levels up)
        # telemetry_input_dir = /path/to/omnia/src/telemetry/input
        telemetry_root = os.path.dirname(os.path.dirname(module_utils_base))
        telemetry_input_dir = os.path.join(telemetry_root, "input")

        # Normalize the cluster_inventory path
        cluster_inv_path = cluster_inventory.strip()

        # Check if path is absolute or relative
        if not os.path.isabs(cluster_inv_path):
            # If relative, prepend telemetry input dir
            cluster_inv_full_path = os.path.join(telemetry_input_dir, cluster_inv_path)
        else:
            cluster_inv_full_path = cluster_inv_path

        # Validate file exists
        if not os.path.exists(cluster_inv_full_path):
            # Extract just the filename for the example
            example_filename = os.path.basename(cluster_inv_path)
            errors.append(create_error_msg(
                "cluster_inventory",
                cluster_inventory,
                f". Cluster inventory file not found as: {cluster_inv_full_path}. "
                f"Ensure the file exists under omnia/src/telemetry/input/ directory. "
                f"Example paths: '/omnia/src/telemetry/input/{example_filename}'"
            ))
            logger.error(f"cluster_inventory file not found: {cluster_inv_full_path}")
        elif not os.path.isfile(cluster_inv_full_path):
            errors.append(create_error_msg(
                "cluster_inventory",
                cluster_inventory,
                f"cluster_inventory path exists but is not a file: {cluster_inv_full_path}. "
                f"Provide a valid YAML inventory file path."
            ))
            logger.error(f"cluster_inventory is not a file: {cluster_inv_full_path}")
        else:
            # File exists and is a valid file - validation passed
            # Note: cluster_inventory can be an absolute path anywhere on the system
            # (e.g., /opt/omnia/orchestrator/orchestrator.yml) - no directory restriction
            logger.info(f"cluster_inventory validated: {cluster_inv_full_path}")
    else:
        errors.append(create_error_msg(
            "cluster_inventory",
            "",
            "cluster_inventory is required. Provide the path to the Ansible inventory file "
            "(e.g., '/omnia/src/telemetry/input/orchestrator_inventory.yml' or 'orchestrator_inventory.yml')"
        ))
        logger.error("cluster_inventory is empty or not provided")

    # =========================================================================
    # L2: Validate kube_vip — extracted from cluster_inventory file
    # kube_vip is defined in cluster_inventory (kube_vip_group.hosts[0].ansible_host or hostname)
    # NOT in telemetry_config.yml directly
    # =========================================================================
    kube_vip = ""

    # Extract kube_vip from cluster_inventory
    if cluster_inventory:
        cluster_inv_path = cluster_inventory.strip()
        if not os.path.isabs(cluster_inv_path):
            telemetry_root = os.path.dirname(os.path.dirname(module_utils_base))
            telemetry_input_dir = os.path.join(telemetry_root, "input")
            cluster_inv_full_path = os.path.join(telemetry_input_dir, cluster_inv_path)
        else:
            cluster_inv_full_path = cluster_inv_path

        if os.path.exists(cluster_inv_full_path) and os.path.isfile(cluster_inv_full_path):
            try:
                with open(cluster_inv_full_path, "r", encoding="utf-8") as inv_file:
                    cluster_inv_data = yaml.safe_load(inv_file)
                # Extract kube_vip from cluster_inventory structure:
                # all.children.kube_vip_group.hosts.<hostname>.ansible_host or <hostname>
                if cluster_inv_data and "all" in cluster_inv_data:
                    children = cluster_inv_data.get("all", {}).get("children", {})
                    kube_vip_group = children.get("kube_vip_group", {})
                    hosts = kube_vip_group.get("hosts", {})
                    if hosts:
                        first_host_name = list(hosts.keys())[0]
                        first_host_data = hosts.get(first_host_name, {})
                        if isinstance(first_host_data, dict) and "ansible_host" in first_host_data:
                            kube_vip = first_host_data["ansible_host"]
                        else:
                            kube_vip = first_host_name
                        logger.info(f"Extracted kube_vip '{kube_vip}' from cluster_inventory")
            except (yaml.YAMLError, OSError, KeyError, TypeError) as e:
                logger.warning(f"Failed to extract kube_vip from cluster_inventory: {e}")

    kube_vip_valid = False
    if kube_vip and isinstance(kube_vip, str):
        octets = kube_vip.strip().split(".")
        if len(octets) == 4:
            kube_vip_valid = True
            for octet in octets:
                try:
                    val = int(octet)
                    if val < 0 or val > 255:
                        kube_vip_valid = False
                        break
                except ValueError:
                    kube_vip_valid = False
                    break
            if not kube_vip_valid:
                errors.append(create_error_msg(
                    "kube_vip",
                    kube_vip,
                    en_us_validation_msg.KUBE_VIP_INVALID_IPV4_MSG
                ))
        logger.info(f"kube_vip L2 validation checked: {kube_vip}")

        if kube_vip_valid:
            # Check SSH reachability of kube_vip
            try:
                ssh_reach_cmd = [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    "-o", "BatchMode=yes",
                    kube_vip,
                    "true"
                ]
                reach_result = subprocess.run(
                    ssh_reach_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=15
                )
                if reach_result.returncode != 0:
                    errors.append(create_error_msg(
                        "kube_vip",
                        kube_vip,
                        en_us_validation_msg.KUBE_VIP_SSH_UNREACHABLE_MSG
                    ))
                    logger.error(f"kube_vip '{kube_vip}' is not reachable via SSH")
                    kube_vip_valid = False
                else:
                    logger.info(f"kube_vip '{kube_vip}' is reachable via SSH")
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                errors.append(create_error_msg(
                    "kube_vip",
                    kube_vip,
                    en_us_validation_msg.KUBE_VIP_SSH_UNREACHABLE_MSG
                ))
                logger.warning(f"SSH reachability check for kube_vip failed: {e}")
                kube_vip_valid = False

        # kube_vip validation complete

    # =========================================================================
    # Extract parameters from new three-layer structure
    # =========================================================================
    telemetry_sources = data.get("telemetry_sources", {})
    telemetry_bridges = data.get("telemetry_bridges", {})
    telemetry_sinks = data.get("telemetry_sinks", {})
    ldms_configurations = data.get("ldms_configurations", {})

    # Source feature flags
    idrac_source = telemetry_sources.get("idrac", {})
    ldms_source = telemetry_sources.get("ldms", {})
    powerscale_source = telemetry_sources.get("powerscale", {})
    ufm_source = telemetry_sources.get("ufm", {})
    vast_source = telemetry_sources.get("vast", {})

    ome_source = telemetry_sources.get("ome", {})

    idrac_telemetry_support = idrac_source.get("metrics_enabled", False)
    idrac_collection_targets = idrac_source.get("collection_targets", [])

    # Bridge feature flags
    vector_ldms = telemetry_bridges.get("vector_ldms", {})
    vector_ome = telemetry_bridges.get("vector_ome", {})

    # Sink configurations
    kafka_sink = telemetry_sinks.get("kafka", {})
    topic_partitions = kafka_sink.get("topic_partitions", {})

    # =========================================================================
    # Validate collection_targets per source type
    # =========================================================================
    # iDRAC: supports kafka and victoria_metrics
    idrac_targets = set(idrac_collection_targets)
    allowed_idrac_targets = {"kafka", "victoria_metrics"}
    invalid_idrac_targets = idrac_targets - allowed_idrac_targets
    if invalid_idrac_targets:
        errors.append(create_error_msg(
            "telemetry_sources.idrac.collection_targets",
            list(invalid_idrac_targets),
            f"Invalid collection targets for iDRAC. Only 'kafka' and 'victoria_metrics' are supported. Found: {invalid_idrac_targets}"
        ))

    # LDMS: only supports kafka
    ldms_targets = set(ldms_source.get("collection_targets", []))
    if ldms_targets and ldms_targets != {"kafka"}:
        errors.append(create_error_msg(
            "telemetry_sources.ldms.collection_targets",
            list(ldms_targets),
            "LDMS only supports 'kafka' as collection target. Use Vector-LDMS bridge to route to victoria_metrics."
        ))

    # PowerScale: supports victoria_metrics and victoria_logs
    powerscale_targets = set(powerscale_source.get("collection_targets", []))
    allowed_powerscale_targets = {"victoria_metrics", "victoria_logs"}
    invalid_powerscale_targets = powerscale_targets - allowed_powerscale_targets
    if invalid_powerscale_targets:
        errors.append(create_error_msg(
            "telemetry_sources.powerscale.collection_targets",
            list(invalid_powerscale_targets),
            f"Invalid collection targets for PowerScale. Only 'victoria_metrics' and 'victoria_logs' are supported. Found: {invalid_powerscale_targets}"
        ))

    # UFM: supports victoria_metrics and victoria_logs
    ufm_targets = set(ufm_source.get("collection_targets", []))
    allowed_ufm_targets = {"victoria_metrics", "victoria_logs"}
    invalid_ufm_targets = ufm_targets - allowed_ufm_targets
    if invalid_ufm_targets:
        errors.append(create_error_msg(
            "telemetry_sources.ufm.collection_targets",
            list(invalid_ufm_targets),
            f"Invalid collection targets for UFM. Only 'victoria_metrics' and 'victoria_logs' are supported. Found: {invalid_ufm_targets}"
        ))

    # OME: only supports kafka (OME does NOT push directly to VictoriaMetrics)
    ome_targets = set(ome_source.get("collection_targets", []))
    if ome_targets and ome_targets != {"kafka"}:
        errors.append(create_error_msg(
            "telemetry_sources.ome.collection_targets",
            list(ome_targets),
            "OME only supports 'kafka' as collection target. OME publishes to Kafka; "
            "Vector-OME bridge routes to victoria_metrics/victoria_logs."
        ))


    # =========================================================================
    # Validate Kafka topic_partitions (now a dict: {idrac: N, ldms: N})
    # =========================================================================


    if topic_partitions and isinstance(topic_partitions, dict):
        allowed_topics = {"idrac", "ldms"}
        present_topics = set(topic_partitions.keys())

        # Validate topic names
        for topic_name in present_topics:
            if topic_name not in allowed_topics:
                errors.append(create_error_msg(
                    f"telemetry_sinks.kafka.topic_partitions.{topic_name}",
                    topic_name,
                    f"Invalid topic name '{topic_name}'. Only 'idrac' and 'ldms' are allowed as Kafka topic names."
                ))

        logger.info(f"Telemetry validation - Present topics: {present_topics}")

        # Validate required topics based on feature flags
        if idrac_telemetry_support and 'kafka' in idrac_collection_targets:
            if 'idrac' not in present_topics:
                errors.append(create_error_msg(
                    "telemetry_sinks.kafka.topic_partitions",
                    "missing 'idrac' topic",
                    "idrac topic is required when telemetry_sources.idrac.metrics_enabled is true and 'kafka' is in collection_targets"
                ))

        # If LDMS is enabled and kafka in collection_targets, ldms topic is required
        ldms_enabled = ldms_source.get("metrics_enabled", False)
        ldms_kafka_targets = set(ldms_source.get("collection_targets", []))
        if ldms_enabled and 'kafka' in ldms_kafka_targets and 'ldms' not in present_topics:
            errors.append(create_error_msg(
                "telemetry_sinks.kafka.topic_partitions",
                "missing 'ldms' topic",
                "ldms topic is required in topic_partitions when telemetry_sources.ldms.metrics_enabled "
                "is true and 'kafka' is in ldms collection_targets."
            ))
        elif ldms_enabled and 'kafka' in ldms_kafka_targets:
            logger.info(f"LDMS topic validation PASSED - 'ldms' found in present_topics: {present_topics}")

        # Validate partition values are positive integers
        for topic_name, partitions in topic_partitions.items():
            if not isinstance(partitions, int) or partitions < 1:
                errors.append(create_error_msg(
                    f"telemetry_sinks.kafka.topic_partitions.{topic_name}",
                    partitions,
                    f"Partition count for '{topic_name}' must be a positive integer (1-100)"
                ))

    # =========================================================================
    # Validate ldms_configurations.sampler_plugins
    # =========================================================================
    sampler_plugins = ldms_configurations.get("sampler_plugins")

    if sampler_plugins is None:
        errors.append(create_error_msg(
            "ldms_configurations.sampler_plugins",
            "null/None",
            "ldms_configurations.sampler_plugins is required and cannot be null. Please provide valid sampler configurations with plugin names."
        ))
    elif isinstance(sampler_plugins, list):
        if len(sampler_plugins) == 0:
            errors.append(create_error_msg(
                "ldms_configurations.sampler_plugins",
                "empty array []",
                "ldms_configurations.sampler_plugins cannot be an empty array. Please provide at least one valid sampler configuration with plugin names."
            ))
        else:
            for idx, sampler_config in enumerate(sampler_plugins):
                if not isinstance(sampler_config, dict):
                    continue

                plugin_name = sampler_config.get("plugin_name", "")
                if not plugin_name or (isinstance(plugin_name, str) and plugin_name.strip() == ""):
                    errors.append(create_error_msg(
                        f"ldms_configurations.sampler_plugins[{idx}].plugin_name",
                        f"'{plugin_name}'",
                        "plugin_name cannot be empty. Must be one of: meminfo, procstat2, vmstat, loadavg, slurm_sampler, procnetdev2"
                    ))

    # =========================================================================
    # Validate Vector bridge configurations
    # =========================================================================
    if vector_ome.get("metrics_enabled") or vector_ome.get("logs_enabled"):
        ome_identifier = vector_ome.get("ome_identifier", "")
        if not ome_identifier or (isinstance(ome_identifier, str) and ome_identifier.strip() == ""):
            errors.append(create_error_msg(
                "telemetry_bridges.vector_ome.ome_identifier",
                f"'{ome_identifier}'",
                "ome_identifier cannot be empty when Vector-OME is enabled."
            ))

    # =========================================================================
    # L2 Validation: Vector Bridge Prerequisites
    # =========================================================================
    # Vector-LDMS bridge can only be enabled when LDMS source is enabled
    vector_ldms_enabled = vector_ldms.get("metrics_enabled", False)
    vector_ome_metrics_enabled = vector_ome.get("metrics_enabled", False)
    vector_ome_logs_enabled = vector_ome.get("logs_enabled", False)
    ldms_source_enabled = ldms_source.get("metrics_enabled", False)

    # Validation 1: Vector-LDMS requires LDMS source to be enabled
    if vector_ldms_enabled and not ldms_source_enabled:
        errors.append(create_error_msg(
            "telemetry_bridges.vector_ldms.metrics_enabled",
            "true",
            en_us_validation_msg.VECTOR_LDMS_SOURCE_DISABLED_MSG
        ))
        logger.error(
            "Vector-LDMS bridge prerequisite validation FAILED: "
            f"vector_ldms.metrics_enabled={vector_ldms_enabled}, "
            f"ldms_source.metrics_enabled={ldms_source_enabled}"
        )
    elif vector_ldms_enabled and ldms_source_enabled:
        logger.info(
            "Vector-LDMS bridge prerequisite validation PASSED: "
            f"vector_ldms.metrics_enabled={vector_ldms_enabled}, "
            f"ldms_source.metrics_enabled={ldms_source_enabled}"
        )

    elif ldms_source_enabled and not vector_ldms_enabled:
        logger.info(
            "LDMS source is enabled without Vector-LDMS bridge: "
            f"ldms_source.metrics_enabled={ldms_source_enabled}, "
            f"vector_ldms.metrics_enabled={vector_ldms_enabled}. "
            "LDMS metrics will flow to Kafka only. "
            "To also route metrics to VictoriaMetrics, set telemetry_bridges.vector_ldms.metrics_enabled to true."
        )

    # # Validation 3: Verify Kafka collection target for LDMS
    # ldms_collection_targets = ldms_source.get("collection_targets", [])
    # if ldms_source_enabled and 'kafka' not in ldms_collection_targets:
    #     errors.append(create_error_msg(
    #         "telemetry_sources.ldms.collection_targets",
    #         str(ldms_collection_targets),
    #         "LDMS source requires 'kafka' in collection_targets. "
    #         "LDMS only supports Kafka-based collection."
    #     ))
    #     logger.error(
    #         f"LDMS collection_targets missing 'kafka': {ldms_collection_targets}"
    #     )

    # =========================================================================
    # OME source ↔ Vector-OME bridge independent validation
    # =========================================================================
    # Metrics and logs channels are validated independently:
    #   - vector_ome.metrics_enabled requires ome.metrics_enabled
    #   - vector_ome.logs_enabled requires ome.logs_enabled
    ome_metrics_enabled = ome_source.get("metrics_enabled", False)
    ome_logs_enabled = ome_source.get("logs_enabled", False)

    # Validation: Vector-OME metrics bridge requires OME metrics source
    if vector_ome_metrics_enabled and not ome_metrics_enabled:
        errors.append(create_error_msg(
            "telemetry_bridges.vector_ome.metrics_enabled",
            "true",
            "Vector-OME metrics bridge is enabled but telemetry_sources.ome.metrics_enabled is false. "
            "Either enable telemetry_sources.ome.metrics_enabled or disable "
            "telemetry_bridges.vector_ome.metrics_enabled."
        ))
        logger.error(
            "OME-VectorOME metrics dependency validation FAILED: "
            f"ome.metrics_enabled={ome_metrics_enabled}, "
            f"vector_ome.metrics_enabled={vector_ome_metrics_enabled}"
        )

    # Validation: Vector-OME logs bridge requires OME logs source
    if vector_ome_logs_enabled and not ome_logs_enabled:
        errors.append(create_error_msg(
            "telemetry_bridges.vector_ome.logs_enabled",
            "true",
            "Vector-OME logs bridge is enabled but telemetry_sources.ome.logs_enabled is false. "
            "Either enable telemetry_sources.ome.logs_enabled or disable "
            "telemetry_bridges.vector_ome.logs_enabled."
        ))
        logger.error(
            "OME-VectorOME logs dependency validation FAILED: "
            f"ome.logs_enabled={ome_logs_enabled}, "
            f"vector_ome.logs_enabled={vector_ome_logs_enabled}"
        )

    # Log Vector-OME bridge status
    if vector_ome_metrics_enabled or vector_ome_logs_enabled:
        logger.info(
            "Vector-OME bridge validation PASSED: "
            f"metrics_enabled={vector_ome_metrics_enabled}, "
            f"logs_enabled={vector_ome_logs_enabled}, "
            f"ome_source.metrics_enabled={ome_metrics_enabled}, "
            f"ome_source.logs_enabled={ome_logs_enabled}"
        )

    # =========================================================================
    # Validate additional_metric_remote_write_endpoints (victoria_metrics)
    # =========================================================================
    victoria_metrics_sink = telemetry_sinks.get("victoria_metrics", {})
    additional_metric_endpoints = victoria_metrics_sink.get(
        "additional_metric_remote_write_endpoints", []
    )
    if additional_metric_endpoints and isinstance(additional_metric_endpoints, list):
        if len(additional_metric_endpoints) > 5:
            logger.warning(
                f"More than 5 additional_metric_remote_write_endpoints "
                f"configured ({len(additional_metric_endpoints)}). "
                "This may impact performance."
            )
        for idx, endpoint in enumerate(additional_metric_endpoints):
            if not isinstance(endpoint, dict):
                continue
            url = endpoint.get("url", "")
            if not url or not isinstance(url, str):
                errors.append(create_error_msg(
                    f"telemetry_sinks.victoria_metrics.additional_metric_remote_write_endpoints[{idx}].url",
                    url,
                    en_us_validation_msg.ADDITIONAL_METRIC_ENDPOINTS_URL_EMPTY_MSG
                ))
            elif (not url.startswith("http://") and
                  not url.startswith("https://")):
                errors.append(create_error_msg(
                    f"telemetry_sinks.victoria_metrics.additional_metric_remote_write_endpoints[{idx}].url",
                    url,
                    en_us_validation_msg.ADDITIONAL_METRIC_ENDPOINTS_URL_INVALID_MSG
                ))

    # =========================================================================
    # Validate additional_log_write_endpoints (victoria_logs)
    # =========================================================================
    victoria_logs_sink = telemetry_sinks.get("victoria_logs", {})
    additional_log_endpoints = victoria_logs_sink.get(
        "additional_log_write_endpoints", []
    )
    if additional_log_endpoints and isinstance(additional_log_endpoints, list):
        if len(additional_log_endpoints) > 5:
            logger.warning(
                f"More than 5 additional_log_write_endpoints "
                f"configured ({len(additional_log_endpoints)}). "
                "This may impact performance."
            )
        for idx, endpoint in enumerate(additional_log_endpoints):
            if not isinstance(endpoint, dict):
                continue
            url = endpoint.get("url", "")
            if not url or not isinstance(url, str):
                errors.append(create_error_msg(
                    f"telemetry_sinks.victoria_logs.additional_log_write_endpoints[{idx}].url",
                    url,
                    en_us_validation_msg.ADDITIONAL_LOG_ENDPOINTS_URL_EMPTY_MSG
                ))
            elif (not url.startswith("http://") and
                  not url.startswith("https://")):
                errors.append(create_error_msg(
                    f"telemetry_sinks.victoria_logs.additional_log_write_endpoints[{idx}].url",
                    url,
                    en_us_validation_msg.ADDITIONAL_LOG_ENDPOINTS_URL_INVALID_MSG
                ))

    # =========================================================================
    # Validate PowerScale telemetry configuration (standalone design)
    # =========================================================================
    powerscale_enabled = powerscale_source.get("metrics_enabled", False)
    powerscale_logs_enabled = powerscale_source.get("logs_enabled", False)
    powerscale_configs = data.get("powerscale_configurations", {})
    powerscale_collection_targets = powerscale_source.get("collection_targets", [])

    # Build config_paths for PowerScale validation
    telemetry_root = os.path.dirname(os.path.dirname(module_utils_base))
    telemetry_input_dir = os.path.join(telemetry_root, "input")
    software_config_file_path = os.path.join(telemetry_input_dir, "software_config.json")
    telemetry_packages_file_path = os.path.join(telemetry_input_dir, "telemetry_packages.yml")
    is_service_cluster_defined = bool(kube_vip_valid)
    config_paths = {
        "service_k8s_json_path": os.path.join(telemetry_input_dir, "service_k8s.json"),
        "csi_driver_powerscale_json_path": os.path.join(telemetry_input_dir, "csi_driver_powerscale.json"),
    }

    if powerscale_enabled or powerscale_logs_enabled:
        # Use standalone PowerScale validation module
        powerscale_telemetry_validation.validate_powerscale_telemetry_config(
            data=data,
            powerscale_collection_targets=powerscale_collection_targets,
            software_config_file_path=software_config_file_path,
            is_service_cluster_defined=is_service_cluster_defined,
            config_paths=config_paths,
            logger=logger,
            errors=errors,
            telemetry_packages_file_path=telemetry_packages_file_path
        )


    # =========================================================================
    # Validate UFM telemetry configuration
    # =========================================================================
    ufm_metrics_enabled = ufm_source.get("metrics_enabled", False)
    ufm_logs_enabled = ufm_source.get("logs_enabled", False)
    ufm_detailed_config = data.get("ufm_configuration", {})

    if ufm_metrics_enabled or ufm_logs_enabled:
        # Check required UFM endpoint
        ufm_endpoint = ufm_detailed_config.get("ufm_endpoint", "")
        if not ufm_endpoint or (isinstance(ufm_endpoint, str) and ufm_endpoint.strip() == ""):
            errors.append(create_error_msg(
                "ufm_configuration.ufm_endpoint",
                ufm_endpoint,
                "ufm_endpoint is required when UFM telemetry is enabled. Provide the UFM appliance IP address or hostname."
            ))

        # Validate UFM metrics port if metrics enabled
        if ufm_metrics_enabled:
            ufm_metrics_port = ufm_detailed_config.get("ufm_metrics_port", 9001)
            if not isinstance(ufm_metrics_port, int) or ufm_metrics_port < 1 or ufm_metrics_port > 65535:
                errors.append(create_error_msg(
                    "ufm_configuration.ufm_metrics_port",
                    ufm_metrics_port,
                    "ufm_metrics_port must be an integer between 1 and 65535."
                ))

        # Validate TLS mode
        tls_mode = ufm_detailed_config.get("tls_mode", "self_signed")
        if tls_mode not in ["self_signed", "ca_signed"]:
            errors.append(create_error_msg(
                "ufm_configuration.tls_mode",
                tls_mode,
                "tls_mode must be 'self_signed' or 'ca_signed'."
            ))

        # Validate CA certificate path when tls_mode is ca_signed
        if tls_mode == "ca_signed":
            ca_cert_path = ufm_detailed_config.get("ufm_ca_cert_path", "")
            if not ca_cert_path or (isinstance(ca_cert_path, str) and ca_cert_path.strip() == ""):
                errors.append(create_error_msg(
                    "ufm_configuration.ufm_ca_cert_path",
                    ca_cert_path,
                    "ufm_ca_cert_path is required when tls_mode is 'ca_signed'. Provide path to CA certificate file."
                ))

        # Validate auth mode
        auth_mode = ufm_detailed_config.get("auth_mode", "basic")
        if auth_mode not in ["basic", "none"]:
            errors.append(create_error_msg(
                "ufm_configuration.auth_mode",
                auth_mode,
                "auth_mode must be 'basic' or 'none'."
            ))

    # =========================================================================
    # Validate VAST telemetry configuration
    # =========================================================================
    vast_metrics_enabled = vast_source.get("metrics_enabled", False)
    vast_logs_enabled = vast_source.get("logs_enabled", False)
    vast_detailed_config = data.get("vast_configuration", {})
    
    if vast_metrics_enabled or vast_logs_enabled:
        # Check required VAST endpoint
        vast_endpoint = vast_detailed_config.get("vast_endpoint", "")
        if not vast_endpoint or (isinstance(vast_endpoint, str) and vast_endpoint.strip() == ""):
            errors.append(create_error_msg(
                "vast_configuration.vast_endpoint",
                vast_endpoint,
                "vast_endpoint is required when VAST telemetry is enabled. Provide the VAST cluster IP address or hostname."
            ))
        
        # Validate VAST metrics port if metrics enabled
        if vast_metrics_enabled:
            vast_metrics_port = vast_detailed_config.get("vast_metrics_port", 443)
            if not isinstance(vast_metrics_port, int) or vast_metrics_port < 1 or vast_metrics_port > 65535:
                errors.append(create_error_msg(
                    "vast_configuration.vast_metrics_port",
                    vast_metrics_port,
                    "vast_metrics_port must be an integer between 1 and 65535."
                ))
        
        # Validate TLS mode
        tls_mode = vast_detailed_config.get("tls_mode", "self_signed")
        if tls_mode not in ["self_signed", "ca_signed"]:
            errors.append(create_error_msg(
                "vast_configuration.tls_mode",
                tls_mode,
                "tls_mode must be 'self_signed' or 'ca_signed'."
            ))
        
        # Validate CA certificate path when tls_mode is ca_signed
        if tls_mode == "ca_signed":
            ca_cert_path = vast_detailed_config.get("vast_ca_cert_path", "")
            if not ca_cert_path or (isinstance(ca_cert_path, str) and ca_cert_path.strip() == ""):
                errors.append(create_error_msg(
                    "vast_configuration.vast_ca_cert_path",
                    ca_cert_path,
                    "vast_ca_cert_path is required when tls_mode is 'ca_signed'. Provide path to CA certificate file."
                ))
        
        # Validate auth mode
        auth_mode = vast_detailed_config.get("auth_mode", "basic")
        if auth_mode not in ["basic", "none"]:
            errors.append(create_error_msg(
                "vast_configuration.auth_mode",
                auth_mode,
                "auth_mode must be 'basic' or 'none'."
            ))

    return errors


def validate_telemetry_storage_config(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the telemetry storage configuration from telemetry_storage_config.yml.

    This function performs L2 logic validation by checking if required storage sections
    exist based on what's enabled in telemetry_config.yml.

    Args:
        input_file_path: Path to telemetry_storage_config.yml
        data: Parsed YAML data from telemetry_storage_config.yml
        logger: Logger instance
        module: Ansible module instance
        omnia_base_dir: Base directory of Omnia installation
        module_utils_base: Base directory of module_utils
        project_name: Name of the project

    Returns:
        List of error messages (empty if validation passes)
    """
    errors = []

    # Load telemetry_config.yml to determine what storage sections are required
    input_dir = os.path.dirname(input_file_path)
    telemetry_config_path = os.path.join(input_dir, "telemetry_config.yml")

    if not os.path.exists(telemetry_config_path):
        logger.info("telemetry_config.yml not found, skipping cross-file validation")
        return errors

    try:
        with open(telemetry_config_path, 'r', encoding='utf-8') as f:
            telemetry_config = yaml.safe_load(f)
    except (yaml.YAMLError, IOError) as e:
        errors.append(create_error_msg(
            "telemetry_config.yml",
            "error reading file",
            f"Error reading telemetry_config.yml for cross-validation: {str(e)}"
        ))
        return errors

    if not telemetry_config:
        logger.info("telemetry_config.yml is empty, skipping cross-file validation")
        return errors

    # Extract sections from telemetry_config.yml
    telemetry_sources = telemetry_config.get("telemetry_sources", {})
    telemetry_bridges = telemetry_config.get("telemetry_bridges", {})
    powerscale_source = telemetry_sources.get("powerscale", {})

    # Determine which storage sections are required
    kafka_required = False
    victoria_metrics_required = False
    victoria_logs_required = False
    vector_required = False
    powerscale_metrics_required = False

    # Check collection targets for all sources
    for source_name, source_config in telemetry_sources.items():
        collection_targets = source_config.get("collection_targets", [])
        metrics_enabled = source_config.get("metrics_enabled", False)
        logs_enabled = source_config.get("logs_enabled", False)

        if metrics_enabled or logs_enabled:
            if "kafka" in collection_targets:
                kafka_required = True
                logger.info(f"Kafka required for {source_name} (metrics={metrics_enabled}, logs={logs_enabled})")

            if "victoria_metrics" in collection_targets:
                victoria_metrics_required = True
                logger.info(f"VictoriaMetrics required for {source_name} (metrics={metrics_enabled})")

            if "victoria_logs" in collection_targets:
                victoria_logs_required = True
                logger.info(f"VictoriaLogs required for {source_name} (logs={logs_enabled})")

    # Check Vector bridges
    vector_ldms_enabled = telemetry_bridges.get("vector_ldms", {}).get("metrics_enabled", False)
    vector_ome_metrics_enabled = telemetry_bridges.get("vector_ome", {}).get("metrics_enabled", False)
    vector_ome_logs_enabled = telemetry_bridges.get("vector_ome", {}).get("logs_enabled", False)
    if vector_ldms_enabled or vector_ome_metrics_enabled or vector_ome_logs_enabled:
        vector_required = True
        logger.info(f"Vector required (vector_ldms={vector_ldms_enabled}, vector_ome_metrics={vector_ome_metrics_enabled}, vector_ome_logs={vector_ome_logs_enabled})")

    # Check PowerScale metrics
    powerscale_metrics_enabled = powerscale_source.get("metrics_enabled", False)
    if powerscale_metrics_enabled:
        powerscale_metrics_required = True
        logger.info("PowerScale metrics required")

    # Validate required sections exist in telemetry_storage_config.yml (data parameter)
    storage_config = data

    if not storage_config:
        errors.append(create_error_msg(
            "telemetry_storage_config.yml",
            "empty or invalid",
            "telemetry_storage_config.yml is empty or invalid"
        ))
        return errors

    # Validate kafka_storage
    if kafka_required and not storage_config.get("kafka_storage"):
        errors.append(create_error_msg(
            "telemetry_storage_config.yml.kafka_storage",
            "not defined",
            en_us_validation_msg.KAFKA_STORAGE_REQUIRED_MSG
        ))
    elif kafka_required:
        logger.info("kafka_storage validation passed")

    # Validate victoria_cluster_storage
    if victoria_metrics_required and not storage_config.get("victoria_cluster_storage"):
        errors.append(create_error_msg(
            "telemetry_storage_config.yml.victoria_cluster_storage",
            "not defined",
            en_us_validation_msg.VICTORIA_METRICS_STORAGE_REQUIRED_MSG
        ))
    elif victoria_metrics_required:
        logger.info("victoria_cluster_storage validation passed")

    # Validate victoria_logs_cluster_storage
    if victoria_logs_required and not storage_config.get("victoria_logs_cluster_storage"):
        errors.append(create_error_msg(
            "telemetry_storage_config.yml.victoria_logs_cluster_storage",
            "not defined",
            en_us_validation_msg.VICTORIA_LOGS_STORAGE_REQUIRED_MSG
        ))
    elif victoria_logs_required:
        logger.info("victoria_logs_cluster_storage validation passed")

    # Validate vector_storage
    if vector_required and not storage_config.get("vector_storage"):
        errors.append(create_error_msg(
            "telemetry_storage_config.yml.vector_storage",
            "not defined",
            en_us_validation_msg.VECTOR_STORAGE_REQUIRED_MSG
        ))
    elif vector_required:
        logger.info("vector_storage validation passed")

    # Validate csm_metrics_powerscale_storage
    if powerscale_metrics_required and not storage_config.get("csm_metrics_powerscale_storage"):
        errors.append(create_error_msg(
            "telemetry_storage_config.yml.csm_metrics_powerscale_storage",
            "not defined",
            en_us_validation_msg.CSM_METRICS_POWERSCALE_STORAGE_REQUIRED_MSG
        ))
    elif powerscale_metrics_required:
        logger.info("csm_metrics_powerscale_storage validation passed")

    # csi_volume_exporter_storage is always required (always deployed)
    if not storage_config.get("csi_volume_exporter_storage"):
        errors.append(create_error_msg(
            "telemetry_storage_config.yml.csi_volume_exporter_storage",
            "not defined",
            en_us_validation_msg.CSI_VOLUME_EXPORTER_STORAGE_REQUIRED_MSG
        ))
    else:
        logger.info("csi_volume_exporter_storage validation passed")

    # Validate idrac_telemetry_storage when iDRAC metrics are enabled
    idrac_source = telemetry_sources.get("idrac", {})
    idrac_metrics_enabled = idrac_source.get("metrics_enabled", False)
    if idrac_metrics_enabled and not storage_config.get("idrac_telemetry_storage"):
        errors.append(create_error_msg(
            "telemetry_storage_config.yml.idrac_telemetry_storage",
            "not defined",
            en_us_validation_msg.IDRAC_TELEMETRY_STORAGE_REQUIRED_MSG
        ))
    elif idrac_metrics_enabled:
        logger.info("idrac_telemetry_storage validation passed")

    return errors


def validate_telemetry_packages(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the telemetry packages configuration from telemetry_packages.yml.

    Performs L2 logic validation:
    - cluster_mount is non-empty
    - cluster_mount path exists on kube_vip host (cross-file check with telemetry_config.yml)
    - telemetry_registry.host format is correct when provided
    - registry cert_path / key_path files exist when provided
    - all non-empty package URLs start with http:// or https://

    Args:
        input_file_path: Path to telemetry_packages.yml
        data: Parsed YAML data from telemetry_packages.yml
        logger: Logger instance
        module: Ansible module instance
        omnia_base_dir: Base directory of Omnia installation
        module_utils_base: Base directory of module_utils
        project_name: Name of the project

    Returns:
        List of error messages (empty if validation passes)
    """
    errors = []

    if not data:
        logger.info("telemetry_packages.yml is empty, skipping L2 validation")
        return errors

    # =========================================================================
    # Validate cluster_mount
    # =========================================================================
    cluster_mount = data.get("cluster_mount", "")
    if not cluster_mount or (isinstance(cluster_mount, str) and cluster_mount.strip() == ""):
        errors.append(create_error_msg(
            "cluster_mount",
            cluster_mount,
            en_us_validation_msg.CLUSTER_MOUNT_REQUIRED_MSG
        ))
    else:
        logger.info(f"cluster_mount validation PASSED: {cluster_mount}")
        
        # Cross-file validation: check if cluster_mount exists on kube_vip
        input_dir = os.path.dirname(input_file_path)
        telemetry_config_path = os.path.join(input_dir, "telemetry_config.yml")
        
        if os.path.exists(telemetry_config_path):
            try:
                with open(telemetry_config_path, 'r', encoding='utf-8') as f:
                    telemetry_config = yaml.safe_load(f)
                
                kube_vip = telemetry_config.get("kube_vip", "") if isinstance(telemetry_config, dict) else ""

                # If kube_vip not in telemetry_config, try to extract from cluster_inventory
                if (not kube_vip or not isinstance(kube_vip, str) or not kube_vip.strip()):
                    cluster_inventory = telemetry_config.get("cluster_inventory", "") if isinstance(telemetry_config, dict) else ""
                    if cluster_inventory and isinstance(cluster_inventory, str) and cluster_inventory.strip():
                        cluster_inv_path = cluster_inventory.strip()
                        if not os.path.isabs(cluster_inv_path):
                            cluster_inv_full_path = os.path.join(input_dir, cluster_inv_path)
                        else:
                            cluster_inv_full_path = cluster_inv_path

                        if os.path.exists(cluster_inv_full_path) and os.path.isfile(cluster_inv_full_path):
                            try:
                                with open(cluster_inv_full_path, "r", encoding="utf-8") as inv_file:
                                    cluster_inv_data = yaml.safe_load(inv_file)
                                # Extract kube_vip from cluster_inventory structure
                                if cluster_inv_data and "all" in cluster_inv_data:
                                    children = cluster_inv_data.get("all", {}).get("children", {})
                                    kube_vip_group = children.get("kube_vip_group", {})
                                    hosts = kube_vip_group.get("hosts", {})
                                    if hosts:
                                        first_host_name = list(hosts.keys())[0]
                                        first_host_data = hosts.get(first_host_name, {})
                                        if isinstance(first_host_data, dict) and "ansible_host" in first_host_data:
                                            kube_vip = first_host_data["ansible_host"]
                                        else:
                                            kube_vip = first_host_name
                                        logger.info(f"Extracted kube_vip '{kube_vip}' from cluster_inventory for cluster_mount validation")
                            except (yaml.YAMLError, OSError, KeyError, TypeError) as e:
                                logger.warning(f"Failed to extract kube_vip from cluster_inventory: {e}")

                if kube_vip and isinstance(kube_vip, str) and kube_vip.strip():
                    # First, verify kube_vip is reachable via SSH
                    logger.info(f"Pre-checking SSH reachability to kube_vip '{kube_vip}' before cluster_mount path validation")
                    
                    try:
                        ssh_reach_cmd = [
                            "ssh",
                            "-o", "StrictHostKeyChecking=no",
                            "-o", "UserKnownHostsFile=/dev/null",
                            "-o", "ConnectTimeout=10",
                            "-o", "BatchMode=yes",
                            kube_vip,
                            "true"
                        ]
                        reach_result = subprocess.run(
                            ssh_reach_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False,
                            timeout=15
                        )
                        
                        if reach_result.returncode != 0:
                            logger.warning(f"kube_vip '{kube_vip}' is not reachable via SSH, skipping cluster_mount path check")
                            logger.info("cluster_mount path validation skipped due to kube_vip SSH unreachability")
                        else:
                            logger.info(f"kube_vip '{kube_vip}' is reachable, proceeding with cluster_mount path check")
                            
                            # Now check if cluster_mount path exists
                            try:
                                ssh_cmd = [
                                    "ssh",
                                    "-o", "StrictHostKeyChecking=no",
                                    "-o", "UserKnownHostsFile=/dev/null",
                                    "-o", "ConnectTimeout=10",
                                    kube_vip,
                                    f"test -d {cluster_mount}"
                                ]
                                result = subprocess.run(
                                    ssh_cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    check=False,
                                    timeout=15
                                )
                                
                                if result.returncode != 0:
                                    errors.append(create_error_msg(
                                        "cluster_mount",
                                        cluster_mount,
                                        en_us_validation_msg.CLUSTER_MOUNT_PATH_NOT_FOUND_ON_KUBE_VIP_MSG
                                    ))
                                    logger.error(f"cluster_mount path '{cluster_mount}' does not exist on kube_vip '{kube_vip}'")
                                else:
                                    logger.info(f"cluster_mount path '{cluster_mount}' exists on kube_vip '{kube_vip}'")
                            
                            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                                logger.warning(f"SSH check for cluster_mount path failed: {e}")
                                errors.append(create_error_msg(
                                    "cluster_mount",
                                    cluster_mount,
                                    en_us_validation_msg.CLUSTER_MOUNT_SSH_CHECK_FAILED_MSG
                                ))
                    
                    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                        logger.warning(f"SSH reachability check for kube_vip failed: {e}")
                        logger.info("cluster_mount path validation skipped due to kube_vip SSH check failure")
                else:
                    logger.warning("kube_vip not found in telemetry_config.yml, skipping cluster_mount path check")
                    errors.append(create_error_msg(
                        "cluster_mount",
                        cluster_mount,
                        en_us_validation_msg.CLUSTER_MOUNT_KUBE_VIP_NOT_FOUND_MSG
                    ))
            
            except (yaml.YAMLError, IOError, OSError) as e:
                logger.warning(f"Failed to load telemetry_config.yml for kube_vip lookup: {e}")
        else:
            logger.warning(f"telemetry_config.yml not found at {telemetry_config_path}, skipping cluster_mount path check")

    # =========================================================================
    # Validate install_mode
    # =========================================================================
    install_mode = data.get("install_mode", "offline")
    if install_mode not in ("offline", "online"):
        errors.append(create_error_msg(
            "install_mode",
            install_mode,
            "install_mode must be 'offline' or 'online'."
        ))
    else:
        logger.info(f"install_mode validation PASSED: {install_mode}")

    # =========================================================================
    # Validate repo_url (required for offline mode)
    # =========================================================================
    repo_url = data.get("repo_url", "")
    if install_mode == "offline":
        if repo_url and isinstance(repo_url, str) and repo_url.strip():
            if not (repo_url.startswith("http://") or repo_url.startswith("https://")):
                errors.append(create_error_msg(
                    "repo_url",
                    repo_url,
                    en_us_validation_msg.PACKAGE_URL_INVALID_MSG
                ))
            else:
                logger.info(f"repo_url validation PASSED: {repo_url}")
        else:
            logger.warning("repo_url is empty in offline mode — package downloads may fail")

    # =========================================================================
    # Validate container_registry format (when provided)
    # =========================================================================
    container_registry = data.get("container_registry", "")
    if container_registry and isinstance(container_registry, str) and container_registry.strip():
        logger.info(f"container_registry validation PASSED: {container_registry}")

    # =========================================================================
    # Validate helm_charts online_url format
    # =========================================================================
    helm_charts = data.get("helm_charts", {})
    if isinstance(helm_charts, dict):
        for chart_name, chart_data in helm_charts.items():
            if isinstance(chart_data, dict):
                online_url = chart_data.get("online_url", "")
                if online_url and isinstance(online_url, str) and online_url.strip():
                    if not (online_url.startswith("http://") or online_url.startswith("https://")):
                        errors.append(create_error_msg(
                            f"helm_charts.{chart_name}.online_url",
                            online_url,
                            en_us_validation_msg.PACKAGE_URL_INVALID_MSG
                        ))
                    else:
                        logger.info(f"helm_charts.{chart_name}.online_url validation PASSED")

    return errors
