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
# pylint: disable=import-error,no-name-in-module,too-many-branches,too-many-statements

"""
This module util contains all custom software utilities used across custom modules
"""
from collections import defaultdict
import json
from ansible.module_utils.repo_manager.config import (
    SOFTWARES_KEY,
    RPM_LABEL_TEMPLATE,
    POLICY_CACHING_MAP,
    DEFAULT_POLICY,
    DEFAULT_CACHING_POLICY,
    REPO_NAME_FORMAT,
    REPO_NAME_PREFIX_FORMAT,
)


# ----------------------------
# Repo Naming Convention Helpers
# Single place to define how Pulp repo / remote / distribution names
# are built from (arch, os_type, os_version, name).
#
# Format:  <arch>_<os_type>_<os_version>_<name>
# Example: x86_64_rhel_10.0_baseos
# ----------------------------

def build_repo_name(arch, os_type, os_version, name):
    """Build a Pulp repository/remote/distribution name.

    Uses ``REPO_NAME_FORMAT`` from config.py.
    Default: ``<arch>_<os_type>_<os_version>_<name>``.
    """
    return REPO_NAME_FORMAT.format(arch=arch, os_type=os_type,
                                   os_version=os_version, name=name)


def build_repo_name_prefix(arch, os_type, os_version):
    """Return the prefix portion used to detect/construct full names.

    Uses ``REPO_NAME_PREFIX_FORMAT`` from config.py.
    Default: ``<arch>_<os_type>_<os_version>_``.
    """
    return REPO_NAME_PREFIX_FORMAT.format(arch=arch, os_type=os_type,
                                          os_version=os_version)


def normalize_repo_name(repo_name, arch, os_type, os_version):
    """
    Normalize repository name to standard format if not already in format.

    Args:
        repo_name (str): Repository name from config
        arch (str): Architecture (e.g., "x86_64")
        os_type (str): OS type (e.g., "rhel")
        os_version (str): OS version (e.g., "10.0")

    Returns:
        str: Normalized repository name in standard format
    """
    # Check if already in standard format
    expected_prefix = f"{arch}_{os_type}_{os_version}_"

    if repo_name.startswith(expected_prefix):
        # Already in standard format, return as-is
        return repo_name
    else:
        # Not in standard format, convert it
        return build_repo_name(arch, os_type, os_version, repo_name)


def load_json(file_path):
    """
    Load JSON data from a file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The loaded JSON data.

    Raises:
        FileNotFoundError: If the file is not found.
        ValueError: If the JSON parsing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Error: File '{file_path}' not found.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Error: Failed to parse JSON in file '{file_path}'.") from exc










def transform_package_dict(data, arch_val, logger):
    """
    Transforms a dictionary of packages and organizes them by architecture.

    Args:
        data (dict): Dictionary of packages where each key is a software name,
                     and each value is a list of package dicts.
        arch_val: Current architecture being parsed for the software
        logger (logging.Logger): Logger instance used for structured logging of process steps.

    Returns:
        dict: A dictionary where each key is an architecture (e.g., 'x86_64', 'aarch64'),
              and each value is a dictionary of software mapped to their transformed task list.
    """
    result = defaultdict(dict)

    for sw_name, items in data.items():
        transformed_items = []
        rpm_packages = []
        repo_mapping = {}
        rpm_type_mapping = {}

        for item in items:
            if item.get("type") in ("rpm", "rpm_repo"):
                rpm_packages.append(item["package"])
                rpm_type_mapping[item["package"]] = item["type"]
                # Preserve repo_name if available
                if "repo_name" in item:
                    repo_mapping[item["package"]] = item["repo_name"]
                    logger.debug(f"Added repo_mapping: {item['package']} -> {item['repo_name']}")
            elif item.get("type") == "rpm_list":
                rpm_packages.extend(item["package_list"])
                # Preserve repo_mapping if available
                if "repo_mapping" in item:
                    repo_mapping.update(item["repo_mapping"])
                    logger.debug(f"Merged repo_mapping from rpm_list: {item['repo_mapping']}")
                # Legacy rpm_list entries default to rpm.  A caller that already
                # carries original catalog types can pass them through explicitly.
                rpm_type_mapping.update(item.get("rpm_type_mapping", {}))
            else:
                transformed_items.append(item)

        if rpm_packages:
            rpm_task = {
                "package": RPM_LABEL_TEMPLATE.format(key=sw_name),
                "rpm_list": rpm_packages,
                "type": "rpm",
                "rpm_type_mapping": {
                    package_name: rpm_type_mapping.get(package_name, "rpm")
                    for package_name in rpm_packages
                },
            }
            # Add repo_mapping if we have any
            if repo_mapping:
                rpm_task["repo_mapping"] = repo_mapping
                logger.debug(f"Added repo_mapping to rpm_task for {sw_name}: {repo_mapping}")
            transformed_items.append(rpm_task)

        result[arch_val][sw_name] = transformed_items
        logger.info("Finished processing %s. Result: %s", sw_name, transformed_items)

    final_result = dict(result)
    logger.info("Transformation complete for arch '%s'. Final result keys: %s", arch_val, list(final_result.keys()))
    return final_result


def resolve_pulp_policy(policy_str, caching_val, logger=None):
    """
    Resolve user-facing policy and caching into Pulp download policy.
    Args:
        policy_str (str): User policy ('always', 'on_demand', 'partial').
        caching_val: Caching flag (bool, str 'true'/'false', or None).
        logger: Optional logger instance.
    Returns:
        str: Pulp download policy ('immediate', 'on_demand', 'streamed').
    """
    policy = str(policy_str).lower() if policy_str else DEFAULT_POLICY
    if isinstance(caching_val, str):
        caching = caching_val.lower() in ('true', '1', 'yes')
    elif isinstance(caching_val, bool):
        caching = caching_val
    else:
        caching = DEFAULT_CACHING_POLICY
    pulp_policy = POLICY_CACHING_MAP.get(
        (policy, caching), "on_demand"
    )
    if logger:
        logger.info(
            f"Resolved policy='{policy}', caching={caching}"
            f" -> pulp_policy='{pulp_policy}'"
        )
    return pulp_policy




def set_version_variables(user_data, software_names, cluster_os_version, logger):
    """
    Generates a dictionary of version variables from the user data.
    Args:
        user_data (dict): The user data containing the software information.
        software_names (list): The list of software names to extract versions for.
        cluster_os_version (str): The version of the cluster operating system.
        logger (logging.Logger): Logger instance used for structured logging of process steps.
    Returns:
        dict: A dictionary of version variables, where the keys are the software names
              and the values are the corresponding versions.
    """
    version_variables = {}

    # Extract versions from catalog-based structure
    for key in software_names:
        for item in user_data.get(key, []):
            name = item.get('name')
            if 'version' in item:
                version_variables[f"{name}_version"] = item['version']

    version_variables["cluster_os_version"] = cluster_os_version
    logger.info("Added cluster_os_version: %s", cluster_os_version)

    logger.info("Version variables generated: %s", version_variables)
    return version_variables


def get_subgroup_dict(user_data, logger):
    """
    Returns a tuple containing a dictionary mapping software names to subgroup lists,
    and a list of software names.
    """
    logger.info("Starting get_subgroup_dict()")
    subgroup_dict = {}
    software_names = []

    for sw in user_data.get(SOFTWARES_KEY, []):
        software_name = sw['name']
        software_names.append(software_name)
        subgroups = [sw['name']] + [item['name']
                                    for item in user_data.get(software_name, [])]
        subgroup_dict[software_name] = subgroups if isinstance(
            user_data.get(software_name), list) else [sw['name']]

    logger.info("Completed get_subgroup_dict(). Found %d software entries.", len(software_names))
    logger.info("Final subgroup_dict: %s", subgroup_dict)

    return subgroup_dict, software_names
























def remove_duplicates_from_trans(trans):
    """
    Remove duplicate software entries from the transform output.
    The function modifies the input `trans` dictionary in-place and also returns it.
    Args:
        trans (dict): Dictionary returned from `transform_package_dict()` containing
                      architecture → software groups → package lists.
    Returns:
        dict: Deduplicated `trans` dictionary with unique package entries preserved.
    """

    for groups in trans.values():
        for group, items in groups.items():
            unique = {}
            cleaned = []

            for item in items:
                type_ = item.get("type")

                if type_ == "image":
                    # Use digest if present, otherwise use tag
                    identifier = item.get("digest") or item.get("tag")
                    key = (item.get("package"), identifier)

                elif type_ == "pip_module":
                    key = item.get("package")

                elif type_ in ["tarball", "manifest"]:
                    key = item.get("url") or item.get("package")

                elif type_ == "git":
                    key = (item.get("url"), item.get("version"))

                elif type_ in ("rpm", "rpm_repo") and "rpm_list" in item:
                    item["rpm_list"] = list(dict.fromkeys(item["rpm_list"]))
                    key = item.get("package")

                else:
                    key = str(item)

                if key not in unique:
                    unique[key] = True
                    cleaned.append(item)

            groups[group] = cleaned

    return trans
