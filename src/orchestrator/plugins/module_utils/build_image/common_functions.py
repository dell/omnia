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
Common utility functions for build_image modules.
Shared across additional_images_collector, base_image_package_collector,
and image_package_collector modules.
"""

import os
import json
import yaml


def load_json_file(path, module):
    """
    Load a JSON file safely.

    Args:
        path (str): Path to the JSON file.
        module (AnsibleModule): The Ansible module instance.

    Returns:
        dict or None: Parsed JSON content if successful, otherwise None.
    """
    if not os.path.isfile(path):
        module.log(f"File not found: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        module.log(f"Failed to read JSON file {path}: {e}")
        return None


def load_yaml_file(path, module):
    """
    Load a YAML file safely.

    Args:
        path (str): Path to the YAML file.
        module (AnsibleModule): The Ansible module instance, used for error reporting.

    Returns:
        dict: Parsed YAML content.

    Raises:
        Fails the module if the file cannot be read or parsed.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        module.fail_json(msg=f"Failed to read YAML file {path}: {e}")


def get_allowed_roles_from_catalog(catalog_data):
    """
    Get list of allowed roles from catalog functional layers.

    Extracts role names from the catalog's functionallayer entries,
    normalizing names (e.g. 'slurm_control_node_rhel_10_0_x86_64' →
    'slurm_control_node').

    Args:
        catalog_data (dict): Parsed catalog JSON content.

    Returns:
        list: List of allowed role names.
    """
    if not catalog_data:
        return []

    catalog = catalog_data.get('catalog', {})
    functionallayers = catalog.get('functionallayer', [])
    roles = set()

    for fl in functionallayers:
        name = fl.get('name', '')
        # Strip OS/arch suffix: slurm_control_node_rhel_10_0_x86_64 → slurm_control_node
        parts = name.split('_')
        # Find where OS identifier starts (rhel, rocky, ubuntu, etc.)
        os_markers = {'rhel', 'rocky', 'ubuntu', 'sles', 'centos'}
        role_parts = []
        for part in parts:
            if part.lower() in os_markers:
                break
            role_parts.append(part)
        if role_parts:
            roles.add('_'.join(role_parts))

    return list(roles)


def extract_rpm_package_names(cluster_items):
    """
    Extract RPM package names from a cluster list.

    Args:
        cluster_items (list): List of package items.

    Returns:
        list: List of package names (strings) where type is 'rpm'.
    """
    if not cluster_items or not isinstance(cluster_items, list):
        return []
    return [
        item.get('package') for item in cluster_items
        if item.get('type') == 'rpm' and item.get('package')
    ]


def deduplicate_list(items):
    """
    Deduplicate a list while preserving order.

    Args:
        items (list): List of items to deduplicate.

    Returns:
        list: Deduplicated list with original order preserved.
    """
    seen = set()
    unique_items = []
    for item in items:
        if item not in seen:
            unique_items.append(item)
            seen.add(item)
    return unique_items
