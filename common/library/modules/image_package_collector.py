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

import os
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.build_image.config import ROLE_SPECIFIC_KEYS
from ansible.module_utils.build_image.common_functions import (
    load_json_file,
    load_yaml_file,
    is_additional_packages_enabled,
    get_allowed_additional_subgroups,
    deduplicate_list
)

def get_additional_packages_for_role(additional_json_path, role_name, module):
    """
    Get RPM packages for a specific role from additional_packages.json.

    Args:
        additional_json_path (str): Path to additional_packages.json.
        role_name (str): Role name (e.g., 'slurm_control_node').
        module: Ansible module instance.

    Returns:
        list: List of RPM package names for the role.
    """
    if not additional_json_path or role_name not in ROLE_SPECIFIC_KEYS:
        return []

    data = load_json_file(additional_json_path, module)
    if not data or role_name not in data:
        return []

    role_data = data.get(role_name, {})
    cluster_items = role_data.get('cluster', [])

    packages = []
    for item in cluster_items:
        if item.get('type') == 'rpm' and item.get('package'):
            packages.append(item['package'])

    return packages

def normalize_functional_groups(raw_fgs, module):
    """Normalize functional_groups input into a list of strings."""
    if raw_fgs is None:
        return []

    # Accept YAML/JSON string from extra-vars
    if isinstance(raw_fgs, str):
        try:
            raw_fgs = yaml.safe_load(raw_fgs)
        except Exception as exc:  # pragma: no cover - defensive
            module.fail_json(msg=f"Unable to parse functional_groups: {exc}")

    # If provided as dict with key functional_groups
    if isinstance(raw_fgs, dict):
        raw_fgs = raw_fgs.get("functional_groups", [])

    if not isinstance(raw_fgs, list):
        module.fail_json(msg="functional_groups must be a list of strings")

    fgs = []
    for fg in raw_fgs:
        if isinstance(fg, str):
            fgs.append(fg)
        elif isinstance(fg, dict) and "name" in fg:
            fgs.append(fg["name"])
        else:
            module.fail_json(msg="functional_groups items must be strings or dicts with 'name'")
    return fgs


def collect_packages_from_json(sw_data, fg_name=None,
                               slurm_defined=False,
                               service_k8s_defined=False):
    """
    Collect RPM package names from a JSON-like dictionary of software data.
    """
    packages = []

    if slurm_defined:
        fg_name = fg_name.replace("_aarch64", "").replace("_x86_64", "")

        if "slurm_custom" in sw_data and "cluster" in sw_data["slurm_custom"]:
            for entry in sw_data["slurm_custom"]["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

        if fg_name in sw_data and "cluster" in sw_data[fg_name]:
            for entry in sw_data[fg_name]["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

    elif service_k8s_defined:
        fg_name = fg_name.replace("_aarch64", "").replace("_x86_64", "")

        if "service_k8s" in sw_data and "cluster" in sw_data["service_k8s"]:
            for entry in sw_data["service_k8s"]["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

        if fg_name in sw_data and "cluster" in sw_data[fg_name]:
            for entry in sw_data[fg_name]["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

    else:
        for section_data in sw_data.values():
            if isinstance(section_data, dict) and "cluster" in section_data:
                for entry in section_data["cluster"]:
                    if entry.get("type") == "rpm" and "package" in entry:
                        packages.append(entry["package"])

        if "cluster" in sw_data and isinstance(sw_data["cluster"], list):
            for entry in sw_data["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

    return packages


def process_functional_group(fg_name, arch, os_version, input_project_dir,
                             software_map, allowed_softwares, module):
    """
    Process a single functional group and return its package list.
    """
    group_path = os.path.join(
        input_project_dir, "config", arch, "rhel", os_version
    )

    if not os.path.isdir(group_path):
        module.log(f"Directory not found: {group_path}")
        return []

    json_files = software_map.get(fg_name, [])
    packages = []

    for json_file in json_files:
        sw_name = json_file.replace(".json", "")
        if sw_name not in allowed_softwares:
            continue

        sw_path = os.path.join(group_path, json_file)
        if not os.path.isfile(sw_path):
            module.log(f"File not found: {sw_path}")
            continue

        sw_data = load_json_file(sw_path, module)
        if not sw_data:
            continue

        if json_file == "slurm_custom.json":
            packages.extend(
                collect_packages_from_json(
                    sw_data, fg_name=fg_name, slurm_defined=True
                )
            )
        elif json_file == "service_k8s.json":
            packages.extend(
                collect_packages_from_json(
                    sw_data, fg_name=fg_name, service_k8s_defined=True
                )
            )
        else:
            packages.extend(collect_packages_from_json(sw_data))

    # Deduplicate while preserving order
    return deduplicate_list(packages)


def run_module():
    """
    Entry point for the Ansible module.
    """

    module_args = dict(
        # allow raw to support YAML/JSON string or list
        functional_groups=dict(type="raw", required=True),
        software_config_file=dict(type="str", required=True),
        input_project_dir=dict(type="str", required=True),
        additional_json_path=dict(type="str", required=False, default=""),
    )

    result = dict(
        changed=False,
        compute_images_dict={}
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    functional_groups = normalize_functional_groups(
        module.params["functional_groups"], module
    )
    software_config_file = module.params["software_config_file"]
    input_project_dir = module.params["input_project_dir"]
    additional_json_path = module.params["additional_json_path"]

    software_config = load_json_file(software_config_file, module)
    if not software_config:
        module.fail_json(msg="Failed to load software_config.json")

    os_version = software_config.get("cluster_os_version")
    if not os_version:
        module.fail_json(msg="cluster_os_version not found in software_config.json")

    allowed_softwares = {
        sw["name"] for sw in software_config.get("softwares", [])
    }

    # Check if additional_packages is enabled and get allowed subgroups
    additional_enabled = is_additional_packages_enabled(software_config)
    allowed_additional_subgroups = get_allowed_additional_subgroups(software_config) if additional_enabled else []

    # pylint: disable=line-too-long
    # Functional group → json files mapping
    software_map = {
        "default_x86_64": ["openldap.json"],
        "service_kube_node_x86_64": ["service_k8s.json"],
        "service_kube_control_plane_first_x86_64": ["service_k8s.json"],
        "service_kube_control_plane_x86_64": ["service_k8s.json"],
        "slurm_control_node_x86_64": ["slurm_custom.json", "openldap.json", "ldms.json"],
        "slurm_node_x86_64": ["slurm_custom.json", "openldap.json", "ldms.json"],
        "login_node_x86_64": ["slurm_custom.json", "openldap.json", "ldms.json"],
        "login_compiler_node_x86_64": [
            "slurm_custom.json", "openldap.json",
            "ucx.json", "openmpi.json", "ldms.json"
        ],
        "slurm_node_aarch64": ["slurm_custom.json", "openldap.json", "ldms.json"],
        "login_node_aarch64": ["slurm_custom.json", "openldap.json", "ldms.json"],
        "login_compiler_node_aarch64": [
            "slurm_custom.json", "openldap.json", "ldms.json"
        ],
    }

    compute_images_dict = {}

    for fg_name in functional_groups:

        if fg_name.endswith("_x86_64"):
            arch = "x86_64"
        elif fg_name.endswith("_aarch64"):
            arch = "aarch64"
        else:
            arch = "x86_64"

        # Base role name without architecture suffix, used for role-specific
        # additional packages lookups
        base_name = fg_name.replace("_x86_64", "").replace("_aarch64", "")

        packages = process_functional_group(
            fg_name, arch, os_version, input_project_dir,
            software_map, allowed_softwares, module
        )

        # Add role-specific packages from additional_packages.json if enabled
        if additional_enabled and base_name in allowed_additional_subgroups:
            additional_role_pkgs = get_additional_packages_for_role(
                additional_json_path, base_name, module
            )
            packages.extend(additional_role_pkgs)
            packages = deduplicate_list(packages)

        compute_images_dict[fg_name] = {
            "functional_group": fg_name,
            "packages": packages
        }

    result["compute_images_dict"] = compute_images_dict
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
