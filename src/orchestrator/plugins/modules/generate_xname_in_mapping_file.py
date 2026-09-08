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

import csv
import os
import tempfile
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: generate_xname_in_mapping_file
short_description: Generate xnames in a PXE mapping file
description:
  - Reads a PXE mapping CSV file and generates unique xname identifiers for each node entry.
options:
  mapping_file_path:
    description: Path to the PXE mapping CSV file.
    required: true
    type: str
'''

EXAMPLES = r'''
- name: Generate xnames in mapping file
  generate_xname_in_mapping_file:
    mapping_file_path: >-
      {{ omnia_data_path }}/orchestrator/input/{{ project_name }}/pxe_mapping_file.csv
'''

RETURN = r'''
msg:
  description: Status message indicating success or failure.
  type: str
  returned: always
'''

def generate_xname_in_mapping_file(mapping_file_path, module):
    """
    Generates xname in mapping file:
    Parameters:
        mapping_file_path (str): The path to the mapping file.
        module (AnsibleModule): The Ansible module instance for handling exit and failure.
    """
    try:
        with open(mapping_file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                module.fail_json(msg="Please provide details in mapping file.")
            fieldnames = [h.strip() for h in reader.fieldnames]
            rows = []
            for row in reader:
                rows.append({k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()})

        if len(rows) == 0:
            module.fail_json(msg="Please provide details in mapping file.")

        # The resulting XNAME values will have the format 'x1000c0s<d>b<d>n0'
        out_fieldnames = [f for f in fieldnames if f != "XNAME"] + ["XNAME"]
        for i, row in enumerate(rows):
            # `c` will be based on i // 100 (every 100 entries we increment `c`)
            c_index = i // 100
            # `s` will be based on i // 10 (every 10 entries we increment `s`)
            s_index = (i // 10) % 10
            # `digit` cycles from 0 to 9
            digit = i % 10
            # Build the 'xname' with updated logic for `c` and `s` indices
            row["XNAME"] = f"x1000c{c_index}s{s_index}b{digit}n0"

        # Write atomically via temp file to avoid partial writes
        dir_name = os.path.dirname(mapping_file_path)
        with tempfile.NamedTemporaryFile(mode="w", dir=dir_name, suffix=".csv",
                                         delete=False, newline="", encoding="utf-8") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=out_fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            tmp_path = tmp.name
        os.replace(tmp_path, mapping_file_path)

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
