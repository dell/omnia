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


def validate_telemetry_config(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the telemetry configuration from telemetry_config.yml.

    This function validates the new three-layer telemetry configuration structure:
    - telemetry_sources (idrac, ldms, dcgm, powerscale, ufm, vast)
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
    # L2: Validate kube_vip — IPv4 format + SSH reachability + cluster_mount path
    # =========================================================================
    kube_vip = data.get("kube_vip", "")
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

    dcgm_source = telemetry_sources.get("dcgm", {})

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

    # DCGM: should NOT have collection_targets
    if "collection_targets" in dcgm_source:
        errors.append(create_error_msg(
            "telemetry_sources.dcgm.collection_targets",
            dcgm_source.get("collection_targets"),
            "DCGM does not support collection_targets. DCGM metrics are collected via LDMS samplers and routed through LDMS flow."
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

    if powerscale_enabled:
        logger.info("PowerScale metrics enabled — performing standalone PowerScale validation")

        # powerscale_configurations section must exist
        if not powerscale_configs:
            errors.append(create_error_msg(
                "powerscale_configurations",
                "not defined",
                en_us_validation_msg.POWERSCALE_CONFIGURATIONS_MISSING_MSG
            ))
        else:
            # victoria_metrics must be in collection_targets
            if 'victoria_metrics' not in powerscale_collection_targets:
                errors.append(create_error_msg(
                    "telemetry_sources.powerscale.collection_targets",
                    powerscale_collection_targets,
                    en_us_validation_msg.POWERSCALE_VICTORIA_REQUIRED_MSG
                ))

            # otel_collector_storage_size must be set
            otel_storage = powerscale_configs.get("otel_collector_storage_size", "")
            if not otel_storage or not isinstance(otel_storage, str):
                errors.append(create_error_msg(
                    "powerscale_configurations.otel_collector_storage_size",
                    otel_storage,
                    en_us_validation_msg.POWERSCALE_OTEL_STORAGE_SIZE_INVALID_MSG
                ))

            # csm_observability_values_file_path must be set and exist
            csm_values_path = powerscale_configs.get("csm_observability_values_file_path", "")
            if not csm_values_path or (isinstance(csm_values_path, str) and csm_values_path.strip() == ""):
                errors.append(create_error_msg(
                    "powerscale_configurations.csm_observability_values_file_path",
                    csm_values_path,
                    en_us_validation_msg.POWERSCALE_CSM_VALUES_PATH_REQUIRED_MSG
                ))
            elif not os.path.exists(csm_values_path):
                errors.append(create_error_msg(
                    "powerscale_configurations.csm_observability_values_file_path",
                    csm_values_path,
                    en_us_validation_msg.powerscale_csm_values_not_found_msg(csm_values_path)
                ))
            else:
                try:
                    with open(csm_values_path, 'r', encoding='utf-8') as csm_f:
                        csm_values = yaml.safe_load(csm_f)
                    if not isinstance(csm_values, dict):
                        errors.append(create_error_msg(
                            "powerscale_configurations.csm_observability_values_file_path",
                            csm_values_path,
                            en_us_validation_msg.POWERSCALE_CSM_VALUES_INVALID_YAML_MSG
                        ))
                    else:
                        karavi_metrics = csm_values.get("karaviMetricsPowerscale", {})
                        if not karavi_metrics:
                            errors.append(create_error_msg(
                                "csm_observability_values_file_path",
                                csm_values_path,
                                en_us_validation_msg.POWERSCALE_CSM_VALUES_MISSING_KARAVI_SECTION_MSG
                            ))
                        else:
                            if not karavi_metrics.get("image"):
                                errors.append(create_error_msg(
                                    "karaviMetricsPowerscale.image",
                                    "not defined",
                                    en_us_validation_msg.POWERSCALE_CSM_METRICS_IMAGE_MISSING_MSG
                                ))
                            karavi_auth = karavi_metrics.get("authorization", {})
                            if karavi_auth.get("enabled", False):
                                proxy_host = karavi_auth.get("proxyHost", "")
                                if not proxy_host or (isinstance(proxy_host, str) and proxy_host.strip() == ""):
                                    errors.append(create_error_msg(
                                        "karaviMetricsPowerscale.authorization.proxyHost",
                                        proxy_host,
                                        en_us_validation_msg.POWERSCALE_AUTH_PROXY_HOST_MISSING_MSG
                                    ))
                        otel_config = csm_values.get("otelCollector", {})
                        if not otel_config or not otel_config.get("image"):
                            errors.append(create_error_msg(
                                "otelCollector.image",
                                "not defined",
                                en_us_validation_msg.POWERSCALE_OTEL_COLLECTOR_IMAGE_MISSING_MSG
                            ))
                        unsupported_metrics = {
                            "karaviMetricsPowerflex": ("PowerFlex", "karaviMetricsPowerflex"),
                            "karaviMetricsPowerstore": ("PowerStore", "karaviMetricsPowerstore"),
                            "karaviMetricsPowermax": ("PowerMax", "karaviMetricsPowermax"),
                        }
                        for section_key, (component_name, section_name) in unsupported_metrics.items():
                            section = csm_values.get(section_key, {})
                            if isinstance(section, dict) and section.get("enabled", False):
                                errors.append(create_error_msg(
                                    f"{section_name}.enabled",
                                    "true",
                                    en_us_validation_msg.powerscale_unsupported_metrics_enabled_msg(
                                        component_name, section_name, csm_values_path
                                    )
                                ))
                        logger.info("CSM Observability values.yaml validation passed")
                except (yaml.YAMLError, IOError) as e:
                    errors.append(create_error_msg(
                        "powerscale_configurations.csm_observability_values_file_path",
                        csm_values_path,
                        en_us_validation_msg.powerscale_csm_values_parse_error_msg(str(e))
                    ))

    if powerscale_logs_enabled:
        logger.info("PowerScale logs enabled — validating victoria_logs collection target")
        if 'victoria_logs' not in powerscale_collection_targets:
            errors.append(create_error_msg(
                "telemetry_sources.powerscale.collection_targets",
                powerscale_collection_targets,
                en_us_validation_msg.POWERSCALE_VICTORIA_LOGS_REQUIRED_MSG
            ))


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
    # Validate telemetry_registry (when host is configured)
    # =========================================================================
    registry = data.get("telemetry_registry", {})
    registry_host = registry.get("host", "") if isinstance(registry, dict) else ""
    if registry_host and isinstance(registry_host, str) and registry_host.strip():
        if ":" not in registry_host:
            errors.append(create_error_msg(
                "telemetry_registry.host",
                registry_host,
                en_us_validation_msg.REGISTRY_HOST_FORMAT_MSG
            ))
        else:
            logger.info(f"telemetry_registry.host format validation PASSED: {registry_host}")

        cert_path = registry.get("cert_path", "")
        if cert_path and isinstance(cert_path, str) and cert_path.strip():
            if not os.path.exists(cert_path):
                errors.append(create_error_msg(
                    "telemetry_registry.cert_path",
                    cert_path,
                    en_us_validation_msg.REGISTRY_CERT_NOT_FOUND_MSG
                ))

        key_path = registry.get("key_path", "")
        if key_path and isinstance(key_path, str) and key_path.strip():
            if not os.path.exists(key_path):
                errors.append(create_error_msg(
                    "telemetry_registry.key_path",
                    key_path,
                    en_us_validation_msg.REGISTRY_KEY_NOT_FOUND_MSG
                ))

    # =========================================================================
    # Validate telemetry_packages URL format (when URLs are provided)
    # =========================================================================
    packages = data.get("telemetry_packages", {})
    if isinstance(packages, dict):
        for pkg_name, pkg_url in packages.items():
            if pkg_url and isinstance(pkg_url, str) and pkg_url.strip():
                if not (pkg_url.startswith("http://") or pkg_url.startswith("https://")):
                    errors.append(create_error_msg(
                        f"telemetry_packages.{pkg_name}",
                        pkg_url,
                        en_us_validation_msg.PACKAGE_URL_INVALID_MSG
                    ))
                else:
                    logger.info(f"telemetry_packages.{pkg_name} URL validation PASSED")

    return errors
