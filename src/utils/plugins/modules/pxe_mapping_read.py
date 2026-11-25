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

#!/usr/bin/python

"""Read a PXE mapping CSV while ignoring blank and commented-out rows."""

import csv
import os

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: pxe_mapping_read
short_description: Read a PXE mapping CSV, ignoring blank and '#' comment lines
description:
  - Drop-in replacement for C(read_csv) on PXE mapping files.
  - Lines whose first non-blank character is C(#) and blank lines are ignored,
    so a commented-out node is treated as if it were not in the file.
options:
  path:
    description: Path to the CSV file.
    required: true
    type: str
  key:
    description: Column used to build the C(dict) result. Duplicate keys fail.
    required: false
    type: str
'''

EXAMPLES = r'''
- name: Read PXE mapping keyed by admin MAC
  pxe_mapping_read:
    path: "{{ pxe_mapping_file_path }}"
    key: ADMIN_MAC
  register: pxe_mapping
'''

RETURN = r'''
list:
  description: Rows as dictionaries, in file order.
  type: list
  returned: always
dict:
  description: Rows keyed by the C(key) column (empty when no key is given).
  type: dict
  returned: always
'''


def read_mapping_rows(path):
    """Return (fieldnames, rows) for the CSV, skipping blank and comment lines."""
    with open(path, "r", encoding="utf-8-sig", newline="") as csv_file:
        lines = [
            line.strip()
            for line in csv_file
            if line.strip() and not line.lstrip().startswith("#")
        ]
    reader = csv.DictReader(lines)
    return reader.fieldnames or [], list(reader)


def main():
    """Entry point."""
    module = AnsibleModule(
        argument_spec={
            "path": {"type": "str", "required": True},
            "key": {"type": "str", "required": False},
        },
        supports_check_mode=True,
    )
    path = module.params["path"]
    key = module.params["key"]

    if not os.path.isfile(path):
        module.fail_json(msg=f"PXE mapping file not found: {path}")
    try:
        fieldnames, rows = read_mapping_rows(path)
    except (OSError, UnicodeDecodeError, csv.Error) as err:
        module.fail_json(msg=f"Unable to read PXE mapping file {path}: {err}")

    keyed = {}
    if key:
        if key not in fieldnames:
            module.fail_json(msg=f"Key column {key!r} not found in {path}")
        for row in rows:
            value = row[key]
            if value in keyed:
                module.fail_json(msg=f"Duplicate value {value!r} in key column {key!r}")
            keyed[value] = row

    module.exit_json(changed=False, list=rows, dict=keyed)


if __name__ == "__main__":
    main()
