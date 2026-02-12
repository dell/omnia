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

import os
from collections import OrderedDict
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.input_validation.common_utils.slurm_conf_utils import (
    SlurmParserEnum,
    all_confs,
    parse_slurm_conf
)

DOCUMENTATION = r'''
---
module: slurm_conf
short_description: Parse, convert, and merge Slurm configuration files
version_added: "1.0.0"
description:
    - This module provides utilities for working with Slurm configuration files.
    - It can parse a Slurm conf file into a dictionary (parse).
    - It can convert a dictionary back to Slurm conf INI format (render).
    - It can merge multiple configuration sources (files and/or dicts) into one (merge).
options:
    op:
        description:
            - The operation to perform.
            - C(parse) - File to dict. Parse a Slurm conf file and return as dictionary.
            - C(render) - Dict to file. Convert a dictionary to Slurm conf INI lines.
            - C(merge) - Merge multiple configuration sources into one.
        required: true
        type: str
        choices: ['parse', 'render', 'merge']
    path:
        description:
            - Path to the Slurm configuration file.
            - Required when I(op=parse).
        type: str
    conf_map:
        description:
            - Dictionary of configuration key-value pairs.
            - Required when I(op=render).
        type: dict
        default: {}
    conf_sources:
        description:
            - List of configuration sources to merge.
            - Each source can be a file path (string) or a dictionary of config values.
            - Sources are merged in order, with later sources overriding earlier ones.
            - Required when I(op=merge).
        type: list
        elements: raw
        default: []
    conf_name:
        description:
            - The type of Slurm configuration file being processed.
            - Used for validation of configuration keys.
        type: str
        default: slurm
author:
    - Jagadeesh N V (@jagadeeshnv)
'''

EXAMPLES = r'''
# Parse a slurm.conf file into a dictionary
- name: Read slurm.conf
  slurm_conf:
    op: parse
    path: /etc/slurm/slurm.conf
    conf_name: slurm
  register: slurm_config

# Convert a dictionary to slurm.conf INI lines
- name: Generate slurm.conf lines
  slurm_conf:
    op: render
    conf_map:
      ClusterName: mycluster
      SlurmctldPort: 6817
      SlurmctldHost:
        - controller2
      NodeName:
        - NodeName: node[1-10]
          CPUs: 16
          RealMemory: 64000
  register: conf_lines

# Merge a base config file with custom overrides
- name: Merge configurations
  slurm_conf:
    op: merge
    conf_sources:
      - /etc/slurm/slurm.conf.base
      - SlurmctldTimeout: 120
        SlurmdTimeout: 300
      - NodeName:
          - NodeName: newnode1
            CPUs: 32
    conf_name: slurm
  register: merged_config

# Merge multiple config files
- name: Merge multiple files
  slurm_conf:
    op: merge
    conf_sources:
      - /etc/slurm/slurm.conf.defaults
      - /etc/slurm/slurm.conf.site
      - /etc/slurm/slurm.conf.local
    conf_name: slurm
  register: merged_config
'''

RETURN = r'''
conf_dict:
    description: Merged configuration as a dictionary (when op=merge or op=parse).
    type: dict
    returned: when op=merge or op=parse
    sample: {"ClusterName": "mycluster", "SlurmctldTimeout": 120}
ini_lines:
    description: Merged configuration as INI-format lines (when op=merge or op=render).
    type: list
    returned: when op=merge or op=render
    sample: ["ClusterName=mycluster", "SlurmctldTimeout=120"]
'''

# TODO:
#   - Module is not case sensitive for conf keys
#   - Support for validation of S_P_<data> types
#   - Validation for choices for each type
#   - Choices types for each type
#   - Merge of sub options
#   - Hostlist expressions, split and merge computations


def read_dict2ini(conf_dict):
    """Convert a configuration dictionary to INI-style lines for slurm.conf."""
    data = []
    for k, v in conf_dict.items():
        if isinstance(v, list):
            for dct_item in v:
                if isinstance(dct_item, dict):
                    od = OrderedDict(dct_item)
                    od.move_to_end(k, last=False)  # Move k to the beginning
                    data.append(
                        " ".join(f"{key}={value}" for key, value in od.items()))
                else:
                    data.append(f"{k}={dct_item}")
        else:
            data.append(f"{k}={v}")
    return data


def slurm_conf_dict_merge(conf_dict_list, conf_name, replace):
    """Merge multiple Slurm configuration dictionaries into a single dictionary."""
    merged_dict = OrderedDict()
    current_conf = all_confs.get(conf_name, {})
    for conf_dict in conf_dict_list:
        for ky, vl in conf_dict.items():
            if current_conf.get(ky) == SlurmParserEnum.S_P_ARRAY:
                for item in vl:
                    if isinstance(item, dict):
                        existing_dict = merged_dict.get(ky, {})
                        inner_dict = existing_dict.get(item.get(ky), {})
                        # Get the sub-options for this array type (e.g., nodename_options, partition_options)
                        sub_options = all_confs.get(f"{conf_name}->{ky}", {})
                        # Merge item into inner_dict, handling CSV fields specially
                        for k, v in item.items():
                            if sub_options.get(k) == SlurmParserEnum.S_P_CSV and k in inner_dict and not replace:
                                # Merge CSV values
                                existing_values = [val.strip() for val in inner_dict[k].split(',') if val.strip()]
                                new_values = [val.strip() for val in v.split(',') if val.strip()]
                                inner_dict[k] = ",".join(list(dict.fromkeys(existing_values + new_values)))
                            else:
                                # Regular update for non-CSV fields
                                inner_dict[k] = v
                        existing_dict[item.get(ky)] = inner_dict
                        merged_dict[ky] = existing_dict
            elif current_conf.get(ky) == SlurmParserEnum.S_P_LIST:
                existing_list = merged_dict.get(ky, [])
                if isinstance(vl, list):
                    new_items = vl
                else:
                    new_items = [vl]
                merged_dict[ky] = list(dict.fromkeys(existing_list + new_items))
            elif current_conf.get(ky) == SlurmParserEnum.S_P_CSV and not replace:
                existing_values = [v.strip() for v in merged_dict.get(ky, "").split(',') if v.strip()]
                new_values = [v.strip() for v in vl.split(',') if v.strip()]
                merged_dict[ky] = ",".join(list(dict.fromkeys(existing_values + new_values)))
            else:
                merged_dict[ky] = vl
    # flatten the dict
    merged_dict = {
        k: list(v.values()) if isinstance(v, dict) else v
        for k, v in merged_dict.items()
    }
    return merged_dict


def run_module():
    """Entry point for the Ansible module handling slurm.conf operations."""
    module_args = {
        "path": {'type': 'str'},
        "op": {'type': 'str', 'required': True, 'choices': ['parse', 'render', 'merge']},
        "conf_map": {'type': 'dict', 'default': {}},
        "conf_sources": {'type': 'list', 'elements': 'raw', 'default': []},
        "conf_name": {'type': 'str', 'default': 'slurm'},
        "validate": {'type': 'bool', 'default': False},
        "replace": {'type': 'bool', 'default': False}
    }

    result = {"changed": False, "failed": False}

    # Create the AnsibleModule object
    module = AnsibleModule(argument_spec=module_args,
                           required_if=[
                               ('op', 'render', ('conf_map',)),
                               ('op', 'merge', ('conf_sources',))
                           ],
                           supports_check_mode=True)
    try:
        conf_name = module.params['conf_name']
        validate = module.params['validate']
        replace = module.params['replace']
        # Parse the slurm.conf file
        if module.params['op'] == 'parse':
            s_dict, dup_keys = parse_slurm_conf(module.params['path'], conf_name, validate)
            if dup_keys:
                module.fail_json(msg=f"Duplicate keys found in {module.params['path']}: {dup_keys}")
            result['conf_dict'] = s_dict
        elif module.params['op'] == 'render':
            s_list = read_dict2ini(module.params['conf_map'])
            result['ini_lines'] = s_list
        elif module.params['op'] == 'merge':
            conf_dict_list = []
            for conf_source in module.params['conf_sources']:
                if isinstance(conf_source, dict):
                    conf_dict_list.append(OrderedDict(conf_source))
                elif isinstance(conf_source, str):
                    if not os.path.exists(conf_source):
                        raise FileNotFoundError(f"File {conf_source} does not exist")
                    s_dict, dup_keys = parse_slurm_conf(conf_source, conf_name, validate)
                    if dup_keys:
                        module.fail_json(msg=f"Duplicate keys found in {conf_source}: {dup_keys}")
                    conf_dict_list.append(OrderedDict(s_dict))
                else:
                    raise TypeError(f"Invalid type for conf_source: {type(conf_source)}")
            merged_dict = slurm_conf_dict_merge(conf_dict_list, conf_name, replace)
            result['conf_dict'] = merged_dict
            result['ini_lines'] = read_dict2ini(merged_dict)
    except (FileNotFoundError, ValueError, TypeError, AttributeError) as e:
        result['failed'] = True
        result['msg'] = str(e)
        module.fail_json(msg=str(e))
    module.exit_json(**result)


if __name__ == '__main__':
    run_module()
