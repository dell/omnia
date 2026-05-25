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
import csv
import json
import os

import yaml
from ansible.module_utils.input_validation.validation_flows import powerscale_telemetry_validation
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg
from ansible.module_utils.input_validation.common_utils.validation_utils import create_error_msg


def check_is_service_cluster_functional_groups_defined(
    errors, input_file_path, omnia_base_dir, project_name, logger, module
):
    """
    Checks if 'service_kube_node_x86_64' is configured in the mapping file.

    Args:
        errors (list): A list to store error messages.
        input_file_path (str): The path to the input file.
        omnia_base_dir (str): The base directory for Omnia.
        project_name (str): The name of the project.
        logger (object): A logger object for logging messages.
        module (object): A module object for logging messages.

    Returns:
        True if 'service_kube_node_x86_64' is defined and valid in mapping file, else False
    """
    # Get the directory containing the input file
    input_dir = os.path.dirname(input_file_path)
    provision_config_path = os.path.join(input_dir, "provision_config.yml")

    # Check if provision_config.yml exists
    if not os.path.exists(provision_config_path):
        errors.append(
            create_error_msg(
                "provision_config.yml",
                provision_config_path,
                en_us_validation_msg.PROVISION_CONFIG_NOT_FOUND
            )
        )
        return False

    try:
        # Load provision_config.yml to get pxe_mapping_file_path
        with open(provision_config_path, 'r', encoding='utf-8') as f:
            provision_config = yaml.safe_load(f)

        pxe_mapping_file_path = provision_config.get('pxe_mapping_file_path', '')

        if not pxe_mapping_file_path or not os.path.exists(pxe_mapping_file_path):
            errors.append(
                create_error_msg(
                    "pxe_mapping_file_path",
                    pxe_mapping_file_path,
                    en_us_validation_msg.PXE_MAPPING_FILE_NOT_FOUND
                )
            )
            return False

        # Read the mapping file and check for service_kube_node functional groups
        with open(pxe_mapping_file_path, 'r', encoding='utf-8') as fh:
            raw_lines = fh.readlines()

        # Remove blank lines
        non_comment_lines = [ln for ln in raw_lines if ln.strip()]

        if not non_comment_lines:
            errors.append(
                create_error_msg(
                    "pxe_mapping_file_path",
                    pxe_mapping_file_path,
                    en_us_validation_msg.PXE_MAPPING_FILE_EMPTY_SERVICE_CLUSTER_MSG
                )
            )
            return False

        # Use csv.DictReader to parse the mapping file
        reader = csv.DictReader(non_comment_lines)

        # Check if all required service cluster functional groups are present
        # Required: service_kube_node_, service_kube_control_plane_
        has_kube_node = False
        has_control_plane = False

        for row in reader:
            functional_group = row.get('FUNCTIONAL_GROUP_NAME', '').strip()
            if functional_group.startswith('service_kube_node_'):
                has_kube_node = True
                logger.info(f"Service cluster functional group found: {functional_group}")
            elif functional_group.startswith('service_kube_control_plane_'):
                has_control_plane = True
                logger.info(f"Service cluster functional group found: {functional_group}")

        # Both must be present for a complete service cluster
        service_cluster_found = has_kube_node and has_control_plane

        if not service_cluster_found:
            missing = []
            if not has_kube_node:
                missing.append('service_kube_node_*')
            if not has_control_plane:
                missing.append('service_kube_control_plane_*')
            logger.info(f"Service cluster incomplete. Missing functional groups: {', '.join(missing)}")

        return service_cluster_found

    except (yaml.YAMLError, IOError, csv.Error) as e:
        errors.append(
            create_error_msg(
                "pxe_mapping_file_path",
                pxe_mapping_file_path if 'pxe_mapping_file_path' in locals() else "unknown",
                f"Error reading mapping file: {str(e)}"
            )
        )
        return False


def check_is_slurm_cluster_functional_groups_defined(
    errors, input_file_path, omnia_base_dir, project_name, logger, module
):
    """
    Checks if 'slurm_control_node_x86_64 and slurm_node' is configured in the mapping file.

    Args:
        errors (list): A list to store error messages.
        input_file_path (str): The path to the input file.
        omnia_base_dir (str): The base directory for Omnia.
        project_name (str): The name of the project.
        logger (object): A logger object for logging messages.
        module (object): A module object for logging messages.

    Returns:
        True if 'slurm_control_node_x86_64 and slurm_node' is defined in mapping file, else False
    """
    # Get the directory containing the input file
    input_dir = os.path.dirname(input_file_path)
    provision_config_path = os.path.join(input_dir, "provision_config.yml")

    # Check if provision_config.yml exists
    if not os.path.exists(provision_config_path):
        errors.append(
            create_error_msg(
                "provision_config.yml",
                provision_config_path,
                en_us_validation_msg.PROVISION_CONFIG_NOT_FOUND
            )
        )
        return False

    try:
        # Load provision_config.yml to get pxe_mapping_file_path
        with open(provision_config_path, 'r', encoding='utf-8') as f:
            provision_config = yaml.safe_load(f)

        pxe_mapping_file_path = provision_config.get('pxe_mapping_file_path', '')

        if not pxe_mapping_file_path or not os.path.exists(pxe_mapping_file_path):
            errors.append(
                create_error_msg(
                    "pxe_mapping_file_path",
                    pxe_mapping_file_path,
                    en_us_validation_msg.PXE_MAPPING_FILE_NOT_FOUND
                )
            )
            return False

        # Read the mapping file and check for slurm functional groups
        with open(pxe_mapping_file_path, 'r', encoding='utf-8') as fh:
            raw_lines = fh.readlines()

        # Remove blank lines
        non_comment_lines = [ln for ln in raw_lines if ln.strip()]

        if not non_comment_lines:
            errors.append(
                create_error_msg(
                    "pxe_mapping_file_path",
                    pxe_mapping_file_path,
                    en_us_validation_msg.PXE_MAPPING_FILE_EMPTY_SLURM_CLUSTER_MSG
                )
            )
            return False

        # Use csv.DictReader to parse the mapping file
        reader = csv.DictReader(non_comment_lines)

        # Check if all required slurm cluster functional groups are present
        # Required: slurm_control_node_, slurm_node
        has_slurm_control = False
        has_slurm_node = False

        for row in reader:
            functional_group = row.get('FUNCTIONAL_GROUP_NAME', '').strip()
            if functional_group.startswith('slurm_control_node_'):
                has_slurm_control = True
                logger.info(f"Slurm cluster functional group found: {functional_group}")
            elif functional_group.startswith('slurm_node_'):
                has_slurm_node = True
                logger.info(f"Slurm cluster functional group found: {functional_group}")

        # Both must be present for a complete slurm cluster
        slurm_cluster_found = has_slurm_control and has_slurm_node

        if not slurm_cluster_found:
            missing = []
            if not has_slurm_control:
                missing.append('slurm_control_node_')
            if not has_slurm_node:
                missing.append('slurm_node_')
            logger.info(f"Slurm cluster incomplete. Missing functional groups: {', '.join(missing)}")

        return slurm_cluster_found

    except (yaml.YAMLError, IOError, csv.Error) as e:
        errors.append(
            create_error_msg(
                "pxe_mapping_file_path",
                pxe_mapping_file_path if 'pxe_mapping_file_path' in locals() else "unknown",
                f"Error reading mapping file: {str(e)}"
            )
        )
        return False


def get_config_file_paths(input_dir, data, software_config_file_path):
    """
    Dynamically resolves config file paths based on cluster OS type and version.

    Args:
        input_dir (str): Input directory path.
        data (dict): Configuration data (may contain cluster_os_type, cluster_os_version).
        software_config_file_path (str): Path to software_config.json.

    Returns:
        dict: Dictionary containing resolved file paths:
              - service_k8s_json_path: Path to service_k8s (versioned)
              - csi_driver_powerscale_json_path: Path to csi_driver_powerscale.json
    """
    # Try reading cluster_os_type/version from data first, then from software_config.json
    cluster_os_type = data.get("cluster_os_type", "rhel")
    cluster_os_version = data.get("cluster_os_version", "10.0")
    service_k8s_version = None

    if os.path.exists(software_config_file_path):
        try:
            with open(software_config_file_path, 'r', encoding='utf-8') as scf:
                sc_data = json.load(scf)
                cluster_os_type = sc_data.get("cluster_os_type", cluster_os_type)
                cluster_os_version = sc_data.get("cluster_os_version", cluster_os_version)
                # Extract service_k8s version from software_config.json
                for sw in sc_data.get("softwares", []):
                    if sw.get("name") == "service_k8s" and sw.get("version"):
                        service_k8s_version = sw["version"]
                        break
        except (json.JSONDecodeError, IOError):
            pass

    config_base_path = os.path.join(input_dir, "config", "x86_64", cluster_os_type, cluster_os_version)

    # Use versioned service_k8s file if version is available
    # Return None paths if service_k8s is not configured (e.g., slurm-only clusters)
    service_k8s_json_path = None
    if service_k8s_version:
        service_k8s_json = f"service_k8s_v{service_k8s_version}.json"
        service_k8s_json_path = os.path.join(config_base_path, service_k8s_json)

    csi_driver_powerscale_json_path = os.path.join(config_base_path, "csi_driver_powerscale.json")

    return {
        "service_k8s_json_path": service_k8s_json_path,
        "csi_driver_powerscale_json_path": csi_driver_powerscale_json_path
    }


def validate_telemetry_config(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the telemetry configuration from telemetry_config.yml.

    This function validates the new three-layer telemetry configuration structure:
    - telemetry_sources (idrac, ldms, dcgm, powerscale)
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

    # =========================================================================
    # Validate service cluster and slurm cluster
    # =========================================================================
    is_service_cluster_defined = check_is_service_cluster_functional_groups_defined(errors,
                                input_file_path,
                                omnia_base_dir,
                                project_name,
                                logger,
                                module)
    if idrac_telemetry_support and not is_service_cluster_defined:
        errors.append(create_error_msg(
            "telemetry_sources.idrac.metrics_enabled can be",
            idrac_telemetry_support,
            en_us_validation_msg.TELEMETRY_SERVICE_CLUSTER_ENTRY_MISSING_ROLES_CONFIG_MSG
            )
        )

    is_slurm_cluster_defined = check_is_slurm_cluster_functional_groups_defined(errors,
                                input_file_path,
                                omnia_base_dir,
                                project_name,
                                logger,
                                module)

    # =========================================================================
    # Bidirectional LDMS validation
    # =========================================================================
    ldms_enabled_in_telemetry = ldms_source.get("metrics_enabled", False)
    ldms_support_from_software_config = False
    input_dir = os.path.dirname(input_file_path)
    software_config_file_path = os.path.join(input_dir, "software_config.json")

    logger.info(f"Checking for LDMS software in: {software_config_file_path}")

    if os.path.exists(software_config_file_path):
        try:
            with open(software_config_file_path, 'r', encoding='utf-8') as f:
                software_config = json.load(f)
                softwares = software_config.get("softwares", [])
                ldms_support_from_software_config = any(
                    software.get("name") == "ldms" for software in softwares
                )
                logger.info(f"LDMS software detected in software_config.json: {ldms_support_from_software_config}")
                if ldms_support_from_software_config:
                    logger.info("LDMS software found - 'ldms' topic will be required in telemetry_sinks.kafka.topic_partitions")
        except (json.JSONDecodeError, IOError) as e:
            logger.warn(f"Could not load software_config.json: {e}")
    else:
        logger.info(f"software_config.json not found at: {software_config_file_path}")

    # Bidirectional validation: LDMS in telemetry_config requires LDMS in software_config and vice versa
    if ldms_enabled_in_telemetry and not ldms_support_from_software_config:
        errors.append(create_error_msg(
            "telemetry_sources.ldms.metrics_enabled",
            "true",
            "LDMS is enabled in telemetry_config.yml but LDMS software is not configured in software_config.json. "
            "Please add LDMS to software_config.json or disable LDMS in telemetry_config.yml."
        ))

    if ldms_support_from_software_config and not ldms_enabled_in_telemetry:
        errors.append(create_error_msg(
            "telemetry_sources.ldms.metrics_enabled",
            "false",
            "LDMS software is configured in software_config.json but telemetry_sources.ldms.metrics_enabled is false in telemetry_config.yml. "
            "Please enable LDMS in telemetry_config.yml or remove LDMS from software_config.json."
        ))

    if ldms_support_from_software_config and not (is_service_cluster_defined and is_slurm_cluster_defined):
        errors.append(create_error_msg(
            "LDMS entry in software_config.json set to ",
            ldms_support_from_software_config,
            en_us_validation_msg.TELEMETRY_SERVICE_CLUSTER_ENTRY_FOR_LDMS_MISSING_ROLES_CONFIG_MSG
            )
        )

    # =========================================================================
    # Validate Kafka topic_partitions (now a dict: {idrac: N, ldms: N})
    # =========================================================================
    if not kafka_sink:
        if ldms_support_from_software_config:
            errors.append(create_error_msg(
                "telemetry_sinks.kafka",
                "not defined",
                "LDMS software is configured in software_config.json, but telemetry_sinks.kafka section is missing in telemetry_config.yml. "
                "Please define telemetry_sinks.kafka with at least the 'ldms' topic in topic_partitions."
            ))

    if kafka_sink and not topic_partitions:
        if ldms_support_from_software_config:
            errors.append(create_error_msg(
                "telemetry_sinks.kafka.topic_partitions",
                "not defined",
                "LDMS software is configured in software_config.json, but telemetry_sinks.kafka.topic_partitions is not defined. "
                "Please define at least the 'ldms' topic in topic_partitions."
            ))

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

        # If LDMS software is configured, ldms topic is required
        if ldms_support_from_software_config and 'ldms' not in present_topics:
            logger.error(f"LDMS topic validation FAILED - 'ldms' topic is missing from present_topics: {present_topics}")
            errors.append(create_error_msg(
                "telemetry_sinks.kafka.topic_partitions",
                "missing 'ldms' topic",
                "ldms topic is required when LDMS software is configured in software_config.json"
            ))
        elif ldms_support_from_software_config:
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

    # Validation 2: If LDMS source is enabled, Vector-LDMS bridge must also be enabled
    # (LDMS only supports Kafka collection, requires Vector bridge to reach VictoriaMetrics)
    if ldms_source_enabled and not vector_ldms_enabled:
        errors.append(create_error_msg(
            "telemetry_sources.ldms.metrics_enabled",
            "true",
            "LDMS source is enabled but Vector-LDMS bridge is disabled. "
            "LDMS metrics can only reach VictoriaMetrics via the Vector-LDMS bridge. "
            "If you want to check LDMS Metrics on VicotriaMetircs then:"
            "Set telemetry_bridges.vector_ldms.metrics_enabled to true in telemetry_config.yml"
        ))
        logger.error(
            "LDMS source enabled without Vector-LDMS bridge: "
            f"ldms_source.metrics_enabled={ldms_source_enabled}, "
            f"vector_ldms.metrics_enabled={vector_ldms_enabled}"
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

    # Validation 3: Log Vector-OME bridge status
    if vector_ome_metrics_enabled or vector_ome_logs_enabled:
        logger.info(
            "Vector-OME bridge validation: "
            f"metrics_enabled={vector_ome_metrics_enabled}, "
            f"logs_enabled={vector_ome_logs_enabled}"
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
    # Validate PowerScale telemetry configuration
    # =========================================================================
    powerscale_enabled = powerscale_source.get("metrics_enabled", False)
    powerscale_logs_enabled = powerscale_source.get("logs_enabled", False)
    powerscale_configs = data.get("powerscale_configurations", {})

    # Build data dict with powerscale flags merged for validation
    powerscale_validation_data = dict(data)
    powerscale_validation_data["powerscale_configurations"] = {
        "powerscale_telemetry_support": powerscale_enabled,
        "powerscale_log_enabled": powerscale_logs_enabled,
        **powerscale_configs
    }

    powerscale_collection_targets = powerscale_source.get("collection_targets", [])

    config_paths = get_config_file_paths(input_dir, powerscale_validation_data, software_config_file_path)
    powerscale_telemetry_validation.validate_powerscale_telemetry_config(
        powerscale_validation_data, powerscale_collection_targets, software_config_file_path,
        is_service_cluster_defined, config_paths, logger, errors
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

    return errors
