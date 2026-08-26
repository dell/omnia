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
from ansible.module_utils.input_validation.messages import (
    en_us_validation_msg
)
from ansible.module_utils.input_validation.core.validation_utils import (
    create_error_msg
)
# pylint: enable=import-error,no-name-in-module


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
# pylint: disable=too-many-nested-blocks,too-many-branches,too-many-statements
def validate_powerscale_telemetry_config(
    data, powerscale_collection_targets,
    is_service_cluster_defined, config_paths, logger, errors,
    telemetry_packages_file_path=None
):
    """
    Validates PowerScale telemetry configuration in telemetry_config.yml.

    Args:
        data (dict): Telemetry configuration data.
        powerscale_collection_targets (list): PowerScale collection targets list
                                              e.g. ["victoria_metrics", "victoria_logs"].
        is_service_cluster_defined (bool): Whether service cluster is defined.
        config_paths (dict): Dictionary containing resolved config file paths.
        logger (object): Logger object.
        errors (list): List to store error messages.
        telemetry_packages_file_path (str, optional): Path to telemetry_packages.yml.
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

        # Check CSI driver PowerScale is available in telemetry_packages.yml
        csi_powerscale_found = False
        if telemetry_packages_file_path and os.path.exists(telemetry_packages_file_path):
            try:
                with open(telemetry_packages_file_path, 'r', encoding='utf-8') as f:
                    packages_data = yaml.safe_load(f)
                    # Check if PowerScale images are defined in telemetry_packages.yml
                    powerscale_images = packages_data.get("images", {}).get("powerscale", {})
                    csi_powerscale_found = bool(
                        powerscale_images.get("csm_metrics") or
                        powerscale_images.get("otel_collector")
                    )
            except (yaml.YAMLError, IOError) as e:
                logger.warning(
                    f"Could not load telemetry_packages.yml for PowerScale validation: {e}"
                )

        if not csi_powerscale_found:
            errors.append(create_error_msg(
                "telemetry_sources.powerscale.metrics_enabled",
                powerscale_metrics_enabled,
                "PowerScale telemetry requires CSI driver PowerScale images to be defined in "
                "telemetry_packages.yml under images.powerscale section. "
                "Ensure csm_metrics and otel_collector images are configured."
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
                    # Note: proxyHost validation removed - proxy mode is optional

                    # Compare images with telemetry_packages.yml in offline mode
                    install_mode = "online"
                    expected_images = {}
                    if telemetry_packages_file_path and os.path.exists(telemetry_packages_file_path):
                        try:
                            with open(telemetry_packages_file_path, 'r', encoding='utf-8') as pkg_f:
                                packages_data = yaml.safe_load(pkg_f)
                            install_mode = packages_data.get("install_mode", "online")
                            if install_mode == "offline":
                                # Get expected PowerScale images from telemetry_packages.yml
                                powerscale_images = packages_data.get("images", {}).get("powerscale", {})
                                expected_images = powerscale_images
                        except (yaml.YAMLError, IOError) as pkg_err:
                            logger.warning(
                                f"Could not load telemetry_packages.yml: {pkg_err}"
                            )

                    # Collect actual images from PowerScale-specific sections only
                    actual_images = {}
                    # Extract images from karaviMetricsPowerscale section
                    karavi_metrics = csm_values.get("karaviMetricsPowerscale", {})
                    if karavi_metrics and isinstance(karavi_metrics, dict):
                        # Main image
                        if karavi_metrics.get("image"):
                            actual_images["karaviMetricsPowerscale.image"] = karavi_metrics["image"]
                        # Authorization sidecar image
                        karavi_auth = karavi_metrics.get("authorization", {})
                        if karavi_auth and isinstance(karavi_auth, dict):
                            sidecar_proxy = karavi_auth.get("sidecarProxy", {})
                            if sidecar_proxy and isinstance(sidecar_proxy, dict):
                                if sidecar_proxy.get("image"):
                                    actual_images["karaviMetricsPowerscale.authorization.sidecarProxy.image"] = sidecar_proxy["image"]

                    # Extract images from otelCollector section
                    otel_config = csm_values.get("otelCollector", {})
                    if otel_config and isinstance(otel_config, dict):
                        if otel_config.get("image"):
                            actual_images["otelCollector.image"] = otel_config["image"]
                        # nginx proxy image
                        nginx_proxy = otel_config.get("nginxProxy", {})
                        if nginx_proxy and isinstance(nginx_proxy, dict):
                            if nginx_proxy.get("image"):
                                actual_images["otelCollector.nginxProxy.image"] = nginx_proxy["image"]

                    # Extract images from cert-manager section (used by PowerScale)
                    cert_manager = csm_values.get("cert-manager", {})
                    if cert_manager and isinstance(cert_manager, dict):
                        if cert_manager.get("image"):
                            actual_images["cert-manager.image"] = cert_manager["image"]
                        # cert-manager components
                        for component in ["controller", "cainjector", "webhook", "acmesolver"]:
                            component_key = f"{component}"
                            if component_key in cert_manager:
                                component_config = cert_manager[component_key]
                                if isinstance(component_config, dict) and component_config.get("image"):
                                    actual_images[f"cert-manager.{component_key}.image"] = component_config["image"]

                    # Compare images in offline mode
                    if install_mode == "offline" and expected_images:
                        mismatched_images = []
                        for img_key, actual_img in actual_images.items():
                            # Find matching expected image by registry/repo
                            # Compare the base image (without tag) to find the expected version
                            actual_base = actual_img.rsplit(":", 1)[0] if ":" in actual_img else actual_img
                            for expected_key, expected_img in expected_images.items():
                                if expected_img:
                                    expected_base = expected_img.rsplit(":", 1)[0] if ":" in expected_img else expected_img
                                    if actual_base == expected_base:
                                        if actual_img != expected_img:
                                            mismatched_images.append(
                                                f"{img_key}: expected '{expected_img}', "
                                                f"found '{actual_img}'"
                                            )
                                        break
                        if mismatched_images:
                            logger.warning(
                                "PowerScale image version mismatch detected in offline mode. "
                                f"Ensure these images match telemetry_packages.yml: "
                                f"{', '.join(mismatched_images)}"
                            )
                        else:
                            logger.info(
                                "PowerScale images match telemetry_packages.yml in offline mode"
                            )
                    elif install_mode == "online":
                        logger.info(
                            "Online mode: skipping image version comparison with telemetry_packages.yml"
                        )

                    # Validate unsupported metrics are not enabled
                    # Only PowerScale metrics should be enabled; PowerFlex, PowerStore, PowerMax
                    # require their own CSI drivers which are not part of this deployment
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
                            logger.error(
                                f"Unsupported metrics component {section_name} is enabled "
                                f"in CSM Observability values file"
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
