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

# pylint: disable=import-error,no-name-in-module
#!/usr/bin/python

"""Ansible module to collect RPM packages from default_packages.json, additional_packages.json,
and admin_debug_packages.json. Returns a flat list of package names for base image building."""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.build_image.common_functions import (
    load_json_file,
    is_additional_packages_enabled,
    is_admin_debug_enabled,
    extract_rpm_package_names,
    deduplicate_list
)


def collect_default_packages(json_path, module):
    """
    Collect RPM package names from default_packages.json.

    Args:
        json_path (str): Path to default_packages.json.
        module (AnsibleModule): The Ansible module instance.

    Returns:
        list: List of package names.
    """
    data = load_json_file(json_path, module)
    if not data:
        return []

    default_packages = data.get('default_packages', {})
    cluster_items = default_packages.get('cluster', [])
    return extract_rpm_package_names(cluster_items)


def collect_additional_global_packages(json_path, module):
    """
    Collect ONLY global RPM package names from additional_packages.json.
    Role-specific packages are handled by image_package_collector.py.

    Args:
        json_path (str): Path to additional_packages.json.
        module (AnsibleModule): The Ansible module instance.

    Returns:
        list: List of global package names.
    """
    data = load_json_file(json_path, module)
    if not data:
        return []

    # Only global RPMs from additional_packages.cluster[]
    additional_packages = data.get('additional_packages', {})
    global_cluster = additional_packages.get('cluster', [])
    return extract_rpm_package_names(global_cluster)


def collect_admin_debug_packages(json_path, module):
    """
    Collect RPM package names from admin_debug_packages.json.

    Args:
        json_path (str): Path to admin_debug_packages.json.
        module (AnsibleModule): The Ansible module instance.

    Returns:
        list: List of admin debug package names.
    """
    data = load_json_file(json_path, module)
    if not data:
        return []

    admin_debug_packages = data.get('admin_debug_packages', {})
    cluster_items = admin_debug_packages.get('cluster', [])
    return extract_rpm_package_names(cluster_items)


def run_module():
    """
    Run the Ansible module.

    Collects RPM packages from default_packages.json, additional_packages.json,
    and admin_debug_packages.json, returns a combined flat list of unique package names.
    """
    module_args = dict(
        default_json_path=dict(type="str", required=True),
        additional_json_path=dict(type="str", required=False, default=""),
        admin_debug_json_path=dict(type="str", required=False, default=""),
        software_config_path=dict(type="str", required=True),
    )

    result = dict(
        changed=False,
        base_image_packages=[],
        default_packages=[],
        additional_packages=[],
        admin_debug_packages=[]
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    default_json_path = module.params["default_json_path"]
    additional_json_path = module.params["additional_json_path"]
    admin_debug_json_path = module.params["admin_debug_json_path"]
    software_config_path = module.params["software_config_path"]

    # Load software_config.json
    software_config = load_json_file(software_config_path, module)

    # Collect from default_packages.json
    default_pkgs = collect_default_packages(default_json_path, module)
    result["default_packages"] = default_pkgs

    # Collect ONLY global packages from additional_packages.json if enabled
    # Role-specific packages are handled by image_package_collector.py
    additional_pkgs = []
    if additional_json_path and is_additional_packages_enabled(software_config):
        additional_pkgs = collect_additional_global_packages(additional_json_path, module)
    result["additional_packages"] = additional_pkgs

    # Collect admin debug packages if enabled
    admin_debug_pkgs = []
    if admin_debug_json_path and is_admin_debug_enabled(software_config):
        admin_debug_pkgs = collect_admin_debug_packages(admin_debug_json_path, module)
    result["admin_debug_packages"] = admin_debug_pkgs

    # Combine and deduplicate while preserving order
    combined = default_pkgs + additional_pkgs + admin_debug_pkgs
    result["base_image_packages"] = deduplicate_list(combined)
    module.exit_json(**result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
