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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.common_functions import(
    get_arch_from_sw_config
)
from ansible.module_utils.local_repo.software_utils import(
    load_json,
    load_yaml
)
from ansible.module_utils.local_repo.config import (
     SOFTWARE_CONFIG_PATH_DEFAULT,
     ROLES_CONFIG_PATH_DEFAULT
)

def main():
    """
    This utility extracts the architecture list for a given software in software_config.json. 
    If the architecture is not defined in the software_config, it falls back to architecture 
    values defined under each group in roles_config.yml.

    Parameters:
        software_name (str): Name of the software.
        user_json_file (str): Path to software_config.json
        roles_config_path (str): Path to roles_config.yml

    Returns:
        arch (dict): Dictionary mapping software name to a list of architectures.
    """

    module_args = {
        "software_name": {"type": "str", "required": True},
        "user_json_file": {"type": "str", "required": False, "default": SOFTWARE_CONFIG_PATH_DEFAULT},
        "roles_config_path": {"type": "str", "required": False, "default": ROLES_CONFIG_PATH_DEFAULT},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    software_name = module.params['software_name']
    sw_config_path = module.params['user_json_file']
    roles_config_path = module.params['roles_config_path']

    try:
        sw_config_data = load_json(sw_config_path)
        roles_config_data = load_yaml(roles_config_path)
        result = get_arch_from_sw_config(software_name, sw_config_data, roles_config_data)
        module.exit_json(changed=False, arch=result)
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()

