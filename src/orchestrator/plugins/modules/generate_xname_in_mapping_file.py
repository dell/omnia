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

# pylint: disable=import-error,no-name-in-module,line-too-long
#!/usr/bin/python

import os
import pandas as pd
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: generate_xname_in_mapping_file
short_description: Generate xnames in a PXE mapping file
description:
  - Reads a PXE mapping CSV file and populates the XNAME column.
  - If an xnames mapping file (BMC_IP to XNAME) is supplied, it merges those
    physical-location xnames into the PXE mapping file.
  - If no xnames mapping file is supplied, fallback xnames are generated
    sequentially in a CSM/HMS-compatible format.
options:
  mapping_file_path:
    description: Path to the PXE mapping CSV file.
    required: true
    type: str
  xnames_mapping_file_path:
    description: >-
      Optional path to a BMC_IP-to-XNAME mapping CSV file. When omitted, the
      module looks for xnames_mapping_file.csv in the same directory as the
      PXE mapping file. If it is not found, fallback xname generation is used.
    required: false
    type: str
    default: null
'''

EXAMPLES = r'''
- name: Generate xnames in mapping file
  omnia.orchestrator.generate_xname_in_mapping_file:
    mapping_file_path: /opt/omnia/input/project_default/orchestrator/pxe_mapping_file.csv
    xnames_mapping_file_path: /opt/omnia/input/project_default/orchestrator/xnames_mapping_file.csv
'''

RETURN = r'''
msg:
  description: Status message indicating success or failure.
  type: str
  returned: always
'''

def generate_xname_in_mapping_file(mapping_file_path, module, xnames_mapping_file_path=None):
    """
    Generates xname in pxe mapping file:
    Parameters:
        mapping_file_path (str): The path to the pxe mapping file.
        module (AnsibleModule): The Ansible module instance for handling exit and failure.
        xnames_mapping_file_path (str, optional): Path to the xnames mapping file.
            When omitted, the file is resolved from the pxe mapping file directory.
    """
    try:
        csv_file = pd.read_csv(mapping_file_path)
        if len(csv_file) == 0:
            module.fail_json(msg="Please provide details in pxe mapping file.")

        # Strip whitespace from column values and names
        csv_file = csv_file.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)

        # Resolve the xnames mapping file path. If a path was supplied by the
        # caller, use it; otherwise fall back to the legacy behaviour of looking
        # next to the pxe mapping file.
        if xnames_mapping_file_path:
            xnames_file_path = xnames_mapping_file_path
        else:
            xnames_file_path = os.path.join(os.path.dirname(mapping_file_path), "xnames_mapping_file.csv")

        # Fallback xname generation if xname_mapping_file.csv is not present.
        if not os.path.exists(xnames_file_path):
            xname_values = []
            max_fallback = 9000 * 8 * 256  # 18,432,000 unique xnames
            if len(csv_file) > max_fallback:
                module.fail_json(
                    msg=f"Cannot generate fallback xnames for more than {max_fallback} entries."
                )

            for i in range(len(csv_file)):
                # Encode index into cabinet/chassis/slot while keeping b=0 and n=0
                # This satisfies:
                #   - hms-xname: cabinet 1-4 digits, chassis 0-7
                #   - csm:       cabinet <=100000, chassis/slot/bmc <256
                cabinet = 1000 + (i // (8 * 256))
                chassis = (i // 256) % 8
                slot = i % 256
                xname = f'x{cabinet}c{chassis}s{slot}b0n0'
                xname_values.append(xname)

            csv_file["XNAME"] = xname_values
            csv_file.to_csv(mapping_file_path, index=False)
            module.exit_json(changed=True, msg="Xnames are generated successfully in the pxe mapping file using fallback logic.")

        # Load xname_mapping_file.csv and trim whitespace so IP-based lookups are reliable.
        xnames_csv = pd.read_csv(xnames_file_path)
        xnames_csv = xnames_csv.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)

        # Validate the expected columns are present before attempting lookups.
        if "BMC_IP" not in xnames_csv.columns or "XNAME" not in xnames_csv.columns:
            module.fail_json(
                msg=f"xname_mapping_file.csv at {xnames_file_path} must contain BMC_IP and XNAME columns."
            )

        # Build a lookup table: each configured BMC IP maps to its physical-location xname.
        xname_map = dict(zip(xnames_csv["BMC_IP"], xnames_csv["XNAME"]))

        # Compare the sets of BMC IPs between the pxe mapping file and xname_mapping_file.csv.
        # Perfect one-to-one correspondence is required to avoid mismatched hardware metadata.
        pxe_bmc_ips = set(csv_file["BMC_IP"])
        xnames_bmc_ips = set(xname_map.keys())

        missing_in_xnames = pxe_bmc_ips - xnames_bmc_ips
        if missing_in_xnames:
            module.fail_json(
                msg="The following BMC_IPs from the pxe mapping file were not found in xname mapping file: "
                    f"{', '.join(sorted(missing_in_xnames))}"
            )

        extra_in_xnames = xnames_bmc_ips - pxe_bmc_ips
        if extra_in_xnames:
            module.fail_json(
                msg="The following BMC_IPs in xname mapping file were not found in the pxe mapping file: "
                    f"{', '.join(sorted(extra_in_xnames))}"
            )

        # Populate the XNAME column by looking up each mapping row's BMC_IP in xname_map.
        csv_file["XNAME"] = csv_file["BMC_IP"].map(xname_map)

        # Reject duplicate XNAMEs. If the same xname is assigned to multiple
        # BMCs, SMD will later refuse the second RedfishEndpoint/Component.
        dup_xnames = csv_file[csv_file["XNAME"].duplicated(keep=False)]["XNAME"].unique().tolist()
        if dup_xnames:
            module.fail_json(
                msg="Duplicate XNAME values found in the pxe mapping file: "
                    f"{', '.join(sorted(dup_xnames))}"
            )

        # Persist the enriched pxe mapping file back to disk.
        csv_file.to_csv(mapping_file_path, index=False)

        # If all checks pass
        module.exit_json(changed=True, msg="Xnames are generated successfully in the pxe mapping file.")

    except Exception as e:
        module.fail_json(msg=str(e))

def main():
    """
    Validate a pxe mapping file.

    Parameters:
        mapping_file_path (str): The path to the pxe mapping file.

    """
    module_args = {
        'mapping_file_path': {'type': 'path', 'required': True },
        'xnames_mapping_file_path': {'type': 'path', 'required': False, 'default': None}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)
    mapping_file_path = module.params.get('mapping_file_path')
    xnames_mapping_file_path = module.params.get('xnames_mapping_file_path')

    generate_xname_in_mapping_file(mapping_file_path, module, xnames_mapping_file_path)


if __name__ == "__main__":
    main()
