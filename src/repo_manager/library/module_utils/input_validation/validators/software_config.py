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
# pylint: disable=import-error,no-name-in-module,too-many-arguments,too-many-locals
# pylint: disable=too-many-branches,too-many-statements,too-many-positional-arguments
"""
Software configuration validator.

This module validates software_config.json for:
- OS version compatibility
- Software version validation
- Subgroup validation
- JSON file existence
"""
import json
from collections import Counter

from ansible.module_utils.input_validation.core.config import (
    files, expected_versions, os_version_ranges,
    ADDITIONAL_PACKAGES_SUPPORTED_SUBGROUPS
)
from ansible.module_utils.input_validation.core.utils import (
    create_error_msg, create_file_path, validate_softwaresubgroup_entries
)
from ansible.module_utils.input_validation.core.file_utils import load_json
from ansible.module_utils.input_validation.messages import software_messages as msg

from ansible.module_utils.local_repo.software_utils import (
    get_subgroup_dict, get_json_file_path
)


def validate(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the software configuration.

    Args:
        input_file_path (str): The path to the input file.
        data (dict): The data to be validated.
        logger: Logger instance.
        module: Ansible module instance.
        omnia_base_dir (str): The base directory of the Omnia configuration.
        module_utils_base (str): The base directory of the module utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors encountered during validation.
    """
    errors = []

    software_config_file_path = create_file_path(input_file_path, files["software_config"])
    with open(software_config_file_path, "r", encoding="utf-8") as f:
        software_config_json = json.load(f)

    # Validate versions
    results = _validate_versions(software_config_json)
    if results:
        errors.append(
            create_error_msg(
                software_config_file_path,
                "software version validation",
                f"Version mismatches found: {', '.join(results)}"
            )
        )

    # Validate OS version
    cluster_os_type = data["cluster_os_type"]
    cluster_os_version = data["cluster_os_version"]

    if cluster_os_type.lower() in os_version_ranges:
        version_range = os_version_ranges[cluster_os_type.lower()]
        if cluster_os_type.lower() in ["rhel", "rocky"]:
            if cluster_os_version not in version_range:
                errors.append(
                    create_error_msg(
                        "cluster_os_version",
                        cluster_os_version,
                        msg.os_version_fail_msg(cluster_os_type, ", ".join(version_range), None),
                    )
                )
        elif cluster_os_type.lower() == "ubuntu":
            if cluster_os_version not in version_range:
                errors.append(
                    create_error_msg(
                        "cluster_os_version",
                        cluster_os_version,
                        msg.os_version_fail_msg(cluster_os_type, version_range[0], version_range[1]),
                    )
                )

    # Validate subgroups and softwares
    subgroup_dict, _ = get_subgroup_dict(data, logger)
    validation_results = []
    failures = []
    fail_data = []

    # Ensure "default_packages" is present
    software_names = [pkg.get('name') for pkg in data.get('softwares', [])]
    if "default_packages" not in software_names:
        errors.append(
            create_error_msg(
                "Validation Error: ",
                "default_packages",
                "is mandatory in softwares_config.json but is missing."
            )
        )

    # Check for duplicate software names
    sw_duplicates = [sw_name for sw_name, count in Counter(software_names).items() if count > 1]
    if sw_duplicates:
        errors.append(
            create_error_msg(
                "Validation Error: ",
                "Duplicate software names found:",
                f"{', '.join(sw_duplicates)}"
            )
        )

    # Validate ldms dependencies
    if "ldms" in software_names and "service_k8s" not in software_names:
        errors.append(
            create_error_msg("Validation Error: ", "ldms", msg.LDMS_REQUIRES_SERVICE_K8S_MSG)
        )
    if "ldms" in software_names and not any(sw in software_names for sw in ["slurm_custom"]):
        errors.append(
            create_error_msg("Validation Error: ", "ldms", msg.LDMS_REQUIRES_SLURM_MSG)
        )

    # Check for required subgroups
    software_requiring_subgroups = ["additional_packages", "slurm_custom", "service_k8s"]
    for software_name in software_requiring_subgroups:
        if software_name in software_names:
            if software_name not in data or not data[software_name]:
                errors.append(
                    create_error_msg(
                        "Validation Error: ",
                        software_name,
                        f"is present in softwares but corresponding subgroup '{software_name}' "
                        f"is missing or empty in software_config.json. Please refer examples "
                        f"directory for the correct format."
                    )
                )

    supported_subgroups = ADDITIONAL_PACKAGES_SUPPORTED_SUBGROUPS
    additional_packages_warnings = False

    for software_pkg in data['softwares']:
        software = software_pkg['name']
        arch_list = software_pkg.get('arch')
        software_version = software_pkg.get('version')

        for arch in arch_list:
            json_path = get_json_file_path(
                software, cluster_os_type, cluster_os_version, input_file_path, arch,
                software_version=software_version
            )

            if not json_path:
                if software == "service_k8s" and software_version:
                    expected_file = f"{software}_v{software_version}.json"
                else:
                    expected_file = f"{software}.json"
                errors.append(
                    create_error_msg(
                        "Validation Error: ", software,
                        f"is present in software_config.json. JSON file not found: {expected_file}"
                    )
                )
            else:
                try:
                    subgroup_softwares = subgroup_dict.get(software, None)
                    json_data = load_json(json_path)

                    # Validate additional_packages subgroup keys
                    if software == "additional_packages":
                        if "additional_packages" not in json_data:
                            logger.warning(
                                f"{software}/{arch}: {json_path} - "
                                f"Required key 'additional_packages' is missing from the JSON file."
                            )
                            additional_packages_warnings = True

                        arch_supported = supported_subgroups.get(arch, [])
                        user_subgroups = [p.get('name') for p in data.get(software, [])]

                        for json_key in json_data:
                            if json_key == "additional_packages":
                                continue
                            if json_key not in arch_supported:
                                logger.warning(
                                    f"{software}/{arch}: {json_path} - "
                                    f"Subgroup '{json_key}' is not supported for architecture {arch}."
                                )
                                additional_packages_warnings = True
                            elif json_key not in user_subgroups:
                                logger.warning(
                                    f"{software}/{arch}: {json_path} - "
                                    f"Subgroup '{json_key}' is present in JSON but not listed "
                                    f"under additional_packages in software_config.json."
                                )
                                additional_packages_warnings = True

                    for subgroup_software in subgroup_softwares:
                        if software == "additional_packages":
                            if subgroup_software not in supported_subgroups.get(arch, []):
                                continue
                            elif subgroup_software not in json_data:
                                logger.warning(
                                    f"{software}/{arch}: {json_path} - "
                                    f"Software {subgroup_software} not found in {software}."
                                )
                                additional_packages_warnings = True
                                continue

                        _, fail_data = validate_softwaresubgroup_entries(
                            subgroup_software, json_path, json_data, validation_results, failures
                        )

                except (FileNotFoundError, json.JSONDecodeError) as e:
                    errors.append(
                        create_error_msg("Error opening or reading JSON file:", json_path, str(e))
                    )

    if fail_data:
        errors.append(
            create_error_msg(
                "Software config subgroup validation failed for",
                fail_data,
                "Please resolve the issues first before proceeding.",
            )
        )

    if additional_packages_warnings:
        logger.info(
            "[INFO] Additional packages validation completed with warnings. "
            "Please review the log file for additional_packages configuration details."
        )

    return errors


def _is_version_valid(actual_version, expected):
    """Check if the actual version matches the expected version."""
    if isinstance(expected, list):
        return actual_version in expected
    return actual_version == expected


def _validate_versions(data):
    """Validate software versions against expected versions."""
    mismatches = []

    # Validate top-level 'softwares'
    for sw in data.get("softwares", []):
        name = sw.get("name")
        version = sw.get("version")
        expected_version = expected_versions.get(name)

        if expected_version:
            if not version:
                mismatches.append(f"{name} is missing a version")
            elif not _is_version_valid(version, expected_version):
                mismatches.append(
                    f"{name} version mismatch: expected {expected_version}, got {version}"
                )

    # Validate subgroup software
    for parent_key, children in data.items():
        if parent_key == "softwares" or not isinstance(children, list):
            continue

        for sub_sw in children:
            name = sub_sw.get("name")
            version = sub_sw.get("version")
            expected_version = expected_versions.get(name)

            if expected_version and version:
                if not _is_version_valid(version, expected_version):
                    mismatches.append(
                        f"{name} version mismatch in {parent_key}: expected {expected_version}, got {version}"
                    )

    return mismatches
