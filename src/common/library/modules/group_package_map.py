# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

#!/usr/bin/python

"""Ansible module for omnia for group package mapping"""

import os
import json
import yaml
from ansible.module_utils.basic import AnsibleModule

RPM_LIST_BASE = "rpm"
REBOOT_KEY = "reboot_required"

# Read JSON file


def read_json_file(file_path, module):
    """
    Reads a JSON file and returns its data.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The loaded JSON data.
    """
    if not os.path.exists(file_path):
        module.exit_json(failed=True, msg=f"File not found: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        module.exit_json(failed=True, msg=f"Error loading JSON {file_path}: {exc}")
    return data

# Read YAML file


def read_functional_groups_config(file_path, module):
    """
    Reads a YAML file containing roles configuration and
     returns the roles configuration and all groups.

    Args:
        file_path (str): The path to the YAML file.

    Returns:
        tuple: A tuple containing a dictionary of roles configuration and a list of all groups.
    """
    if not os.path.exists(file_path):
        module.exit_json(failed=True, msg=f"File not found: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        module.exit_json(failed=True, msg=f"Error loading YAML {file_path}: {exc}")
    role_cfg = {item['name']: item['groups'] for item in data.get('Roles', [])}
    all_groups = list(data.get('Groups', {}).keys())
    return role_cfg, all_groups


def careful_merge(split_dict, split_key, value):
    """
    Carefully merges a dictionary with a given key and value.

    Args:
        split_dict (dict): The dictionary to merge into.
        split_key (str): The key to merge into the dictionary.
        value (dict): The dictionary to merge.

    Returns:
        None
    """
    val_d = split_dict.get(split_key, {})
    for key, val in value.items():
        if key == REBOOT_KEY:
            val_d[key] = val_d.get(key, False) or val
            continue
        got_existing_list = val_d.get(key, []) + val
        # Order matters?
        val_d[key] = list(set(got_existing_list))  # remove duplicates
    split_dict[split_key] = val_d


def split_comma_keys(input_dict):
    """
    Splits a dictionary's keys by commas and merges the values into a new dictionary.

    Args:
        input_dict (dict): The input dictionary with comma-separated keys.

    Returns:
        dict: A new dictionary with split keys and merged values.
    """
    split_dict = {}
    for key, value in input_dict.items():
        split_keys = [k.strip() for k in key.split(',')]
        for split_key in split_keys:
            careful_merge(split_dict, split_key, value)
    return split_dict


def get_type_dict(clust_list):
    """
    Returns a dictionary of package types and their corresponding package lists.

    Args:
        clust_list (list): A list of dictionaries containing package information.

    Returns:
        dict: A dictionary of package types and their corresponding package lists.
    """
    type_dict = {}
    for pkg_dict in clust_list:
        pkgtype = pkg_dict.get('type')
        if pkgtype == 'rpm_list':
            # Add package_list to RPM_LIST_BASE
            type_dict[RPM_LIST_BASE] = type_dict.get(
               RPM_LIST_BASE, []) + pkg_dict.get('package_list')

        elif pkgtype == 'image' and pkg_dict.get('tag') is not None:
            # Add package:tag to type_dict
            type_dict[pkgtype] = type_dict.get(
                pkgtype, []) + [pkg_dict.get('package') + ":" + pkg_dict.get('tag')]

        elif pkgtype == 'image' and pkg_dict.get('digest') is not None:
            # Add package@sha256:digest to type_dict
            type_dict[pkgtype] = type_dict.get(
                pkgtype, []) + [pkg_dict.get('package') + '@sha256:' + pkg_dict.get('digest')]

        elif pkgtype == 'rpm':  # rpm
                # Add package to rpm key
            type_dict[pkgtype] = type_dict.get(
                pkgtype, []) + [pkg_dict.get('package')]
            # Also track repo_name mapping for RPMs
            if 'repo_mapping' not in type_dict:
                type_dict['repo_mapping'] = {}
            type_dict['repo_mapping'][pkg_dict.get('package')] = pkg_dict.get('repo_name', '')

        # Update reboot required values
        reboot_val = pkg_dict.get(REBOOT_KEY, False)
        type_dict[REBOOT_KEY] = type_dict.get(REBOOT_KEY, False) or reboot_val

    return type_dict


def modify_addl_software(addl_dict):
    """
    Modifies the additional software dictionary by generating
      a type dictionary for each cluster list.

    Args:
        addl_dict (dict): A dictionary of additional software.

    Returns:
        dict: A dictionary of package types and their corresponding package lists.
    """
    new_dict = {}
    for key, value in addl_dict.items():
        clust_list = value.get('cluster', [])
        type_dict = get_type_dict(clust_list)
        new_dict[key] = type_dict
    return new_dict


def main():
    """
    The main function is the entry point for the Ansible module.
     It processes the input parameters and returns the group package map.

    Args:
        software_bundle (path): The path to the software bundle.
        roles_config (path): The path to the roles configuration file.
        software_config (path): The path to the software configuration file.
        input_path (path): The path to the input path.
        software_bundle_key (str): The key for the software bundle.
        Defaults to 'additional_software'.

    Returns:
        dict: A dictionary containing the group package map.
    """
    module = AnsibleModule(
        argument_spec={
            'software_bundle': {'type': 'path'},
            'roles_config': {'type': 'path'},
            'software_config': {'type': 'path'},
            'input_path': {'type': 'path'},
            'software_bundle_key': {'type': 'str', 'default': 'additional_software'}
        },
        mutually_exclusive=[
            ('input_path', 'software_config'),
            ('input_path', 'roles_config'),
            ('input_path', 'software_bundle')
        ],
        required_one_of=[
            ('input_path', 'software_config', 'roles_config', 'software_bundle')
        ],
        required_together=[
            ('software_config', 'roles_config', 'software_bundle')
        ],
        supports_check_mode=True
    )

    inp_path = module.params.get('input_path')
    addl_key = module.params['software_bundle_key']
    if inp_path:
        inp_path = inp_path.rstrip('/')
        if not os.path.isdir(inp_path):
            module.exit_json(failed=True, msg=f"{inp_path} is not a directory")
        sw_cfg_path = inp_path + '/software_config.json'
        sw_cfg_data = read_json_file(sw_cfg_path, module)
        addl_soft = f"{inp_path}/config/{sw_cfg_data['cluster_os_type']}/{sw_cfg_data['cluster_os_version']}/{addl_key}.json"
        roles_config = f"{inp_path}/roles_config.yml"
    else:
        addl_soft = module.params.get('software_bundle')
        roles_config = module.params.get('roles_config')
        sw_cfg_data = read_json_file(module.params.get('software_config'), module)

    sw_list = [sw_dict.get('name') for sw_dict in sw_cfg_data.get('softwares')]
    if addl_key not in sw_list:
        module.exit_json(
            msg=f"{addl_key} not found in {sw_list}",
            grp_pkg_map={})
    req_addl_soft_list = [
        sub_group.get('name') for sub_group in sw_cfg_data.get(
            addl_key, [])]
    req_addl_soft_list.append(addl_key)  # add the additional_software key

    addl_soft_json_data = read_json_file(addl_soft, module)
    req_addl_soft = {sub_group: addl_soft_json_data.get(
        sub_group) for sub_group in req_addl_soft_list}

    roles_dict, all_groups = read_roles_config(roles_config, module)
    temp_addl_pkgs = req_addl_soft.pop(addl_key, {})
    key = ','.join(all_groups)
    req_addl_soft.setdefault(key, {'cluster': []})['cluster'].extend(temp_addl_pkgs['cluster'])
    addl_software_dict = modify_addl_software(req_addl_soft)
    split_comma_dict = split_comma_keys(addl_software_dict)

    # intersection of split_comma_dict and roles_yaml_data
    common_roles = split_comma_dict.keys() & roles_dict.keys()

    for role in common_roles:
        bundle = split_comma_dict.pop(role)
        group_list = roles_dict.get(role)
        for grp in group_list:
            careful_merge(split_comma_dict, grp, bundle)

    changed = True
    module.exit_json(
        changed=changed,
        grp_pkg_map=split_comma_dict,
        msg="Successfully fetched and mapped groups and packages")


if __name__ == "__main__":
    main()
