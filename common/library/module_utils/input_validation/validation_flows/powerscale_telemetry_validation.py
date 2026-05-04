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
PowerScale telemetry validation module.
Contains validation logic for PowerScale telemetry configuration in telemetry_config.yml.
"""

import ipaddress
import json
import os
import yaml
# pylint: disable=import-error,no-name-in-module
from ansible.module_utils.input_validation.common_utils import (
    en_us_validation_msg
)
from ansible.module_utils.input_validation.common_utils.validation_utils import (
    create_error_msg
)
# pylint: enable=import-error,no-name-in-module


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
# pylint: disable=too-many-nested-blocks,too-many-branches,too-many-statements
def validate_powerscale_telemetry_config(
    data, powerscale_collection_targets, software_config_file_path,
    is_service_cluster_defined, config_paths, logger, errors
):
    """
    Validates PowerScale telemetry configuration in telemetry_config.yml.

    Args:
        data (dict): Telemetry configuration data.
        powerscale_collection_targets (list): PowerScale collection targets list
                                              e.g. ["victoria_metrics", "victoria_logs"].
        software_config_file_path (str): Path to software_config.json.
        is_service_cluster_defined (bool): Whether service cluster is defined.
        config_paths (dict): Dictionary containing resolved config file paths.
        logger (object): Logger object.
        errors (list): List to store error messages.
    """
    # Validate PowerScale telemetry configuration
    telemetry_sources = data.get("telemetry_sources", {})
    powerscale_source = telemetry_sources.get("powerscale", {})
    powerscale_metrics_enabled = powerscale_source.get("metrics_enabled", False)
    powerscale_logs_enabled = powerscale_source.get("logs_enabled", False)
    powerscale_config = data.get("powerscale_configurations", {})

    if powerscale_metrics_enabled:
        logger.info("PowerScale telemetry support is enabled, performing PowerScale validation")

        # Check powerscale_configurations section exists
        if not powerscale_config:
            errors.append(create_error_msg(
                "powerscale_configurations",
                "not defined",
                en_us_validation_msg.POWERSCALE_CONFIGURATIONS_MISSING_MSG
            ))
            return  # Skip further validation if section is missing

        # PowerScale requires at least victoria_metrics in collection_targets
        # (writes metrics via shared vmagent to victoria_metrics)
        if 'victoria_metrics' not in powerscale_collection_targets:
            errors.append(create_error_msg(
                "telemetry_sources.powerscale.collection_targets",
                powerscale_collection_targets,
                en_us_validation_msg.POWERSCALE_VICTORIA_REQUIRED_MSG
            ))

        # Check CSI driver PowerScale is in software_config.json
        csi_powerscale_found = False
        if os.path.exists(software_config_file_path):
            try:
                with open(software_config_file_path, 'r', encoding='utf-8') as f:
                    software_config = json.load(f)
                    softwares = software_config.get("softwares", [])
                    csi_powerscale_found = any(
                        software.get("name") == "csi_driver_powerscale" for software in softwares
                    )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Could not load software_config.json for PowerScale validation: {e}"
                )

        if not csi_powerscale_found:
            errors.append(create_error_msg(
                "telemetry_sources.powerscale.metrics_enabled",
                powerscale_metrics_enabled,
                en_us_validation_msg.POWERSCALE_CSI_DRIVER_MISSING_MSG
            ))

        # Check service cluster is defined
        if not is_service_cluster_defined:
            errors.append(create_error_msg(
                "telemetry_sources.powerscale.metrics_enabled",
                powerscale_metrics_enabled,
                en_us_validation_msg.POWERSCALE_SERVICE_CLUSTER_MISSING_MSG
            ))

        # Validate otel_collector_storage_size
        # (from powerscale_configurations)
        otel_storage = powerscale_config.get(
            "otel_collector_storage_size", ""
        )
        if not otel_storage or not isinstance(otel_storage, str):
            errors.append(create_error_msg(
                "powerscale_configurations.otel_collector_storage_size",
                otel_storage,
                en_us_validation_msg.POWERSCALE_OTEL_STORAGE_SIZE_INVALID_MSG
            ))

        # Validate csm_observability_values_file_path
        csm_values_path = powerscale_config.get(
            "csm_observability_values_file_path", ""
        )
        if (not csm_values_path or not isinstance(csm_values_path, str) or
                csm_values_path.strip() == ""):
            errors.append(create_error_msg(
                "powerscale_configurations.csm_observability_values_file_path",
                csm_values_path,
                en_us_validation_msg.POWERSCALE_CSM_VALUES_PATH_REQUIRED_MSG
            ))
        elif not os.path.exists(csm_values_path):
            errors.append(create_error_msg(
                "powerscale_configurations.csm_observability_values_file_path",
                csm_values_path,
                en_us_validation_msg.powerscale_csm_values_not_found_msg(
                    csm_values_path
                )
            ))
        else:
            # Validate the CSM Observability values.yaml content
            try:
                with open(csm_values_path, 'r', encoding='utf-8') as f:
                    csm_values = yaml.safe_load(f)
                if not isinstance(csm_values, dict):
                    errors.append(create_error_msg(
                        "powerscale_configurations.csm_observability_values_file_path",
                        csm_values_path,
                        en_us_validation_msg.POWERSCALE_CSM_VALUES_INVALID_YAML_MSG
                    ))
                else:
                    # Validate required keys
                    karavi_metrics = csm_values.get("karaviMetricsPowerscale", {})
                    if not karavi_metrics:
                        errors.append(create_error_msg(
                            "csm_observability_values_file_path",
                            csm_values_path,
                            en_us_validation_msg.POWERSCALE_CSM_VALUES_MISSING_KARAVI_SECTION_MSG
                        ))
                    else:
                        # Validate image reference exists
                        if not karavi_metrics.get("image"):
                            errors.append(create_error_msg(
                                "karaviMetricsPowerscale.image",
                                "not defined",
                                en_us_validation_msg.POWERSCALE_CSM_METRICS_IMAGE_MISSING_MSG
                            ))

                    otel_config = csm_values.get("otelCollector", {})
                    if not otel_config or not otel_config.get("image"):
                        errors.append(create_error_msg(
                            "otelCollector.image",
                            "not defined",
                            en_us_validation_msg.POWERSCALE_OTEL_COLLECTOR_IMAGE_MISSING_MSG
                        ))

                    # Validate Karavi Authorization config in Helm values
                    karavi_auth = (
                        karavi_metrics.get("authorization", {}) if karavi_metrics else {}
                    )
                    if karavi_auth.get("enabled", False):
                        proxy_host = karavi_auth.get("proxyHost", "")
                        if (not proxy_host or not isinstance(proxy_host, str) or
                                proxy_host.strip() == ""):
                            errors.append(create_error_msg(
                                "karaviMetricsPowerscale.authorization.proxyHost",
                                proxy_host,
                                en_us_validation_msg.POWERSCALE_AUTH_PROXY_HOST_MISSING_MSG
                            ))

                    # Cross-validate image versions
                    # between values.yaml and service_k8s.json
                    service_k8s_json_path = config_paths.get(
                        "service_k8s_json_path", ""
                    )
                    csi_driver_powerscale_json_path = config_paths.get(
                        "csi_driver_powerscale_json_path", ""
                    )

                    if service_k8s_json_path and os.path.exists(service_k8s_json_path):
                        try:
                            with open(service_k8s_json_path, 'r', encoding='utf-8') as sk8s_f:
                                service_k8s_data = json.load(sk8s_f)

                            # Build lookup: package -> tag from service_k8s.json
                            sk8s_images = {}
                            for entry in service_k8s_data.get(
                                "service_k8s", {}
                            ).get("cluster", []):
                                if entry.get("type") == "image" and "tag" in entry:
                                    sk8s_images[entry["package"]] = entry["tag"]

                            # Images to cross-validate:
                            # (description, values.yaml image, service_k8s package key)
                            images_to_check = []

                            if karavi_metrics and karavi_metrics.get("image"):
                                images_to_check.append((
                                    "csm-metrics-powerscale",
                                    karavi_metrics["image"],
                                    "quay.io/dell/container-storage-modules/"
                                    "csm-metrics-powerscale"
                                ))
                            if otel_config and otel_config.get("image"):
                                images_to_check.append((
                                    "opentelemetry-collector",
                                    otel_config["image"],
                                    "ghcr.io/open-telemetry/"
                                    "opentelemetry-collector-releases/"
                                    "opentelemetry-collector"
                                ))
                            karavi_auth = (
                                karavi_metrics.get("authorization", {}) if karavi_metrics else {}
                            )
                            sidecar_proxy = karavi_auth.get("sidecarProxy", {})
                            if sidecar_proxy and sidecar_proxy.get("image"):
                                # csm-authorization-sidecar is in
                                # csi_driver_powerscale.json, not service_k8s.json
                                if (csi_driver_powerscale_json_path and
                                        os.path.exists(csi_driver_powerscale_json_path)):
                                    try:
                                        with open(csi_driver_powerscale_json_path, 'r',
                                                  encoding='utf-8') as csi_f:
                                            csi_ps_data = json.load(csi_f)
                                        for entry in csi_ps_data.get(
                                            "csi_driver_powerscale", {}
                                        ).get("cluster", []):
                                            if (entry.get("type") == "image" and
                                                    entry.get("package") ==
                                                    "quay.io/dell/container-storage-modules/"
                                                    "csm-authorization-sidecar"):
                                                sidecar_values_tag = (
                                                    sidecar_proxy["image"].split(":")[-1]
                                                    if ":" in sidecar_proxy["image"] else ""
                                                )
                                                if (sidecar_values_tag and
                                                        sidecar_values_tag != entry["tag"]):
                                                    errors.append(create_error_msg(
                                                        "powerscale image: "
                                                        "csm-authorization-sidecar",
                                                        sidecar_proxy["image"],
                                                        en_us_validation_msg.
                                                        powerscale_image_version_mismatch_msg(
                                                            "csm-authorization-sidecar",
                                                            sidecar_proxy["image"],
                                                            f"{entry['package']}:{entry['tag']}"
                                                        )
                                                    ))
                                                else:
                                                    logger.info(
                                                        f"Image version match for "
                                                        f"csm-authorization-sidecar: "
                                                        f"{sidecar_values_tag}"
                                                    )
                                                break
                                    except (json.JSONDecodeError, IOError) as csi_err:
                                        logger.warning(
                                            f"Could not read csi_driver_powerscale.json: {csi_err}"
                                        )

                            for img_name, values_image, sk8s_key in images_to_check:
                                if sk8s_key in sk8s_images:
                                    # Extract tag from values.yaml image
                                    # (format: registry/repo:tag)
                                    values_tag = (
                                        values_image.split(":")[-1]
                                        if ":" in values_image else ""
                                    )
                                    sk8s_tag = sk8s_images[sk8s_key]
                                    if values_tag and values_tag != sk8s_tag:
                                        sk8s_full = f"{sk8s_key}:{sk8s_tag}"
                                        errors.append(create_error_msg(
                                            f"powerscale image: {img_name}",
                                            values_image,
                                            en_us_validation_msg.
                                            powerscale_image_version_mismatch_msg(
                                                img_name, values_image, sk8s_full
                                            )
                                        ))
                                    else:
                                        logger.info(
                                            f"Image version match for {img_name}: {values_tag}"
                                        )
                                else:
                                    logger.warning(
                                        f"Image {sk8s_key} not found in service_k8s.json, "
                                        f"skipping version check"
                                    )

                        except (json.JSONDecodeError, IOError) as sk8s_err:
                            logger.warning(
                                f"Could not read service_k8s.json for "
                                f"image version validation: {sk8s_err}"
                            )
                    else:
                        logger.warning(
                            f"service_k8s.json not found at {service_k8s_json_path}, "
                            f"skipping image version validation"
                        )

                    logger.info("CSM Observability values.yaml validation passed")
            except (yaml.YAMLError, IOError) as e:
                errors.append(create_error_msg(
                    "powerscale_configurations.csm_observability_values_file_path",
                    csm_values_path,
                    en_us_validation_msg.powerscale_csm_values_parse_error_msg(
                        str(e)
                    )
                ))

    if powerscale_logs_enabled:
        logger.info("PowerScale logs collection is enabled, performing logs validation")

        # PowerScale logs require victoria_logs in collection_targets
        # (writes logs via VLAgent to VictoriaLogs)
        if 'victoria_logs' not in powerscale_collection_targets:
            errors.append(create_error_msg(
                "telemetry_sources.powerscale.collection_targets",
                powerscale_collection_targets,
                en_us_validation_msg.POWERSCALE_VICTORIA_LOGS_REQUIRED_MSG
            ))
        # Validate syslog_source_ips when logs_enabled (optional field)
        # If empty, rsyslog will accept from any source IP
        syslog_source_ips = powerscale_config.get(
            "syslog_source_ips", []
        )
        # Only validate IP format if provided (not required)
        if syslog_source_ips and len(syslog_source_ips) > 0:
            for idx, ip_str in enumerate(syslog_source_ips):
                try:
                    ipaddress.ip_address(str(ip_str).strip())
                except ValueError:
                    errors.append(create_error_msg(
                        f"powerscale_configurations.syslog_source_ips[{idx}]",
                        ip_str,
                        en_us_validation_msg.POWERSCALE_SYSLOG_SOURCE_IP_INVALID_MSG
                    ))

    # Validate additional_remote_write_endpoints
    # (applies to metrics deployment)
    additional_endpoints = powerscale_config.get(
        "additional_remote_write_endpoints", []
    )
    if additional_endpoints and isinstance(additional_endpoints, list):
        if len(additional_endpoints) > 5:
            logger.warning(
                f"More than 5 additional_remote_write_endpoints "
                f"configured ({len(additional_endpoints)}). "
                "This may impact performance."
            )
        for idx, endpoint in enumerate(additional_endpoints):
            if not isinstance(endpoint, dict):
                continue
            url = endpoint.get("url", "")
            if not url or not isinstance(url, str):
                errors.append(create_error_msg(
                    f"powerscale_configurations.additional_remote_write_endpoints[{idx}].url",
                    url,
                    en_us_validation_msg.POWERSCALE_ADDITIONAL_ENDPOINTS_URL_EMPTY_MSG
                ))
            elif (not url.startswith("http://") and
                  not url.startswith("https://")):
                errors.append(create_error_msg(
                    f"powerscale_configurations.additional_remote_write_endpoints[{idx}].url",
                    url,
                    en_us_validation_msg.POWERSCALE_ADDITIONAL_ENDPOINTS_URL_INVALID_MSG
                ))
