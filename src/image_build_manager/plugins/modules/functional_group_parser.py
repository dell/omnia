#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import yaml

DOCUMENTATION = r'''
---
module: functional_group_parser
short_description: Parse and normalize functional group input
version_added: "3.0.0"
description:
  - Reads a YAML file containing functional group definitions.
  - Normalizes input that may be a list of strings, list of dicts with C(name) key,
    or a dict with C(functional_groups) key.
  - Returns a flat list of functional group name strings.
options:
  functional_groups_file:
    description: Path to the functional groups YAML file.
    required: true
    type: str
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Parse functional groups
  omnia.image_build.functional_group_parser:
    functional_groups_file: /opt/omnia/image_build_manager/input/project_default/functional_groups.yml
  register: fg_result

- name: Display functional groups
  ansible.builtin.debug:
    var: fg_result.functional_groups
'''

RETURN = r'''
functional_groups:
  description: Flat list of functional group name strings.
  returned: always
  type: list
  elements: str
'''


def normalize_functional_groups(data):
    """
    Accepts either a dict with key 'functional_groups', or a list of
    strings/dicts, and returns a flat list of functional group names.
    """
    if data is None:
        return []

    # If passed as a string (e.g., extra-var), parse it first
    if isinstance(data, str):
        try:
            data = yaml.safe_load(data)
        except Exception:
            return []

    if isinstance(data, dict):
        functional_groups = data.get("functional_groups", [])
    else:
        functional_groups = data

    if not isinstance(functional_groups, list):
        return []

    names = []
    for fg in functional_groups:
        if isinstance(fg, str):
            names.append(fg)
        elif isinstance(fg, dict) and "name" in fg:
            names.append(fg["name"])
    return names


def get_functional_groups(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return normalize_functional_groups(data)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            functional_groups_file=dict(type="str", required=True)
        ),
        supports_check_mode=True,
    )

    config_path = module.params["functional_groups_file"]

    try:
        fg_list = get_functional_groups(config_path)
        module.exit_json(changed=False, functional_groups=fg_list)
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
