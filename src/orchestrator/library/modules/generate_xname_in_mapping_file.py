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

# pylint: disable=import-error,no-name-in-module,line-too-long
#!/usr/bin/python

import pandas as pd
from ansible.module_utils.basic import AnsibleModule

def generate_xname_in_mapping_file(mapping_file_path, module):
    """
    Generates xname in mapping file:
    Parameters:
        mapping_file_path (str): The path to the mapping file.
        module (AnsibleModule): The Ansible module instance for handling exit and failure.
    """
    try:
        csv_file = pd.read_csv(mapping_file_path)
        if len(csv_file) == 0:
            module.fail_json(msg="Please provide details in mapping file.")

        # Strip whitespace from column values and names
        csv_file = csv_file.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)
 
        # The resulting XNAME values will have the format 'x1000c0s<d><b><d>n0', where <b> is a letter and <d> is a digit
        xname_values = []

        for i in range(len(csv_file)):
            # `c` will be based on i // 100 (every 100 entries we increment `c`)
            c_index = i // 100
            # `s` will be based on i // 10 (every 10 entries we increment `s`)
            s_index = (i // 10) % 10
            # `digit` cycles from 0 to 9
            digit = i % 10
            # Build the 'xname' with updated logic for `c` and `s` indices
            xname = f'x1000c{c_index}s{s_index}b{digit}n0'
            xname_values.append(xname)

        csv_file['XNAME'] = xname_values

        # Update the mapping file with the new XNAME values
        csv_file.to_csv(mapping_file_path, index=False)

        # If all checks pass
        module.exit_json(changed=False, msg="Xnames are generated successfully in the mapping file.")

    except Exception as e:
        module.fail_json(msg=str(e))

def main():
    """
	Validate a mapping file.

	Parameters:
		mapping_file_path (str): The path to the mapping file.

	"""
    module_args = {
        'mapping_file_path': {'type': 'path', 'required': True }
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)
    mapping_file_path = module.params.get('mapping_file_path')

    generate_xname_in_mapping_file(mapping_file_path, module)


if __name__ == "__main__":
    main()
