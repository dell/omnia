#!/usr/bin/python
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

"""Ansible module to generate an xnames mapping CSV from location data."""

import csv
import os
import re
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: generate_xnames_mapping
short_description: Generate xnames mapping CSV from server location data
description:
    - This module generates an xnames mapping CSV file from server location
      data (Row, Rack, U-slot) and the BMC IP for each server.
    - The generated xname follows the format x{1000+row}c{rack%8}s{rack//8}b{uslot}n0.
      Each component is constrained to pass both CSM and hms-xname validation.
options:
    servers:
        description: List of server dictionaries with idrac_ip or BMC_IP, and row/rack/uslot (case-insensitive; rackslot may be used in place of uslot)
        required: true
        type: list
    output_file:
        description: Path to the output xnames mapping CSV file
        required: true
        type: str
author:
    - Dell Inc.
'''

EXAMPLES = r'''
- name: Generate xnames mapping file
  generate_xnames_mapping:
    servers: "{{ discovered_servers }}"
    output_file: "/opt/omnia/input/project_default/xnames_mapping_file.csv"
'''

RETURN = r'''
output_file:
    description: Path to the generated xnames mapping file
    type: str
    returned: always
xnames_count:
    description: Number of xnames written to the file
    type: int
    returned: always
'''


def _get_value(server, *keys):
    """Return the first matching value from a server dict, case-insensitive."""
    for key in keys:
        if key in server:
            return server[key]
        if key.lower() in server:
            return server[key.lower()]
        if key.upper() in server:
            return server[key.upper()]
    return None


def construct_xname(row, rack, uslot):
    """Construct an xname from physical location fields.

    The xname format is x{cabinet}c{chassis}s{slot}b{bmc}n{node}. We map these fields
    to our location fields as follows:
      - cabinet = 1000 + row
      - chassis = rack % 8
      - slot    = rack // 8
      - bmc     = uslot
      - node    = 0

    Example:
      row=1, rack=400, uslot=99
      cabinet = 1000 + 1  = 1001
      chassis = 400 % 8   = 0
      slot    = 400 // 8  = 50
      bmc     = 99
      xname   = x1001c0s50b99n0

      row=1, rack=1, uslot=1
      cabinet = 1000 + 1  = 1001
      chassis = 1 % 8     = 1
      slot    = 1 // 8    = 0
      bmc     = 1
      xname   = x1001c1s0b1n0


    To extract the original values:
      row   = cabinet - 1000
      rack  = chassis + (8 * slot)
      uslot = bmc

    Valid ranges:
      - row:   0 - 8999   (cabinet becomes 1000 - 9999, 3-4 digits)
      - rack:  0 - 2047   (chassis 0-7, slot 0-255)
      - uslot: 0 - 255     (bmc 0-255)
    """
    try:
        row = int(row)
        rack = int(rack)
        uslot = int(uslot)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"row, rack, and uslot must be integers, got row={row}, rack={rack}, uslot={uslot}"
        ) from exc

    if not 0 <= row <= 8999:
        raise ValueError(f"row must be an integer between 0 and 8999, got {row}")
    if not 0 <= rack <= 2047:
        raise ValueError(f"rack must be an integer between 0 and 2047, got {rack}")
    if not 0 <= uslot <= 255:
        raise ValueError(f"uslot must be an integer between 0 and 255, got {uslot}")

    cabinet = 1000 + row
    chassis = rack % 8
    slot = rack // 8
    return f"x{cabinet}c{chassis}s{slot}b{uslot}n0"


def normalize_bmc_ip(ip_str):
    """Return a stripped BMC IP string."""
    if not ip_str:
        return ""
    return str(ip_str).strip()


def normalize_location_value(value):
    """Return a stripped location string or None when empty."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def generate_xnames_mapping(servers, output_file):
    """Generate the xnames mapping CSV file."""
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    rows = []
    seen_bmc_ips = set()
    seen_xnames = set()

    for idx, server in enumerate(servers):
        bmc_ip = normalize_bmc_ip(_get_value(server, "idrac_ip", "BMC_IP"))
        if not bmc_ip:
            raise ValueError(f"Server at index {idx} is missing idrac_ip/BMC_IP")

        if bmc_ip in seen_bmc_ips:
            raise ValueError(f"Duplicate BMC_IP found: {bmc_ip}")
        seen_bmc_ips.add(bmc_ip)

        row_val = normalize_location_value(_get_value(server, "row", "ROW"))
        rack_val = normalize_location_value(_get_value(server, "rack", "RACK"))
        # OME may return RackSlot; treat it as uslot if USLOT is not present.
        uslot_val = normalize_location_value(_get_value(server, "uslot", "USLOT", "rackslot", "RACKSLOT"))

        if row_val is None or rack_val is None or uslot_val is None:
            raise ValueError(
                f"Server {bmc_ip} is missing location data (ROW/RACK/USLOT or RACKSLOT)"
            )

        xname = construct_xname(row_val, rack_val, uslot_val)

        if xname in seen_xnames:
            raise ValueError(f"Duplicate xname '{xname}' generated; check ROW/RACK/USLOT values")
        seen_xnames.add(xname)

        rows.append({"BMC_IP": bmc_ip, "XNAME": xname})

    rows.sort(key=lambda r: r["XNAME"])

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["BMC_IP", "XNAME"])
        writer.writeheader()
        writer.writerows(rows)

    return output_file, len(rows)


def main():
    module_args = {
        "servers": {"type": "list", "required": True},
        "output_file": {"type": "str", "required": True},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    servers = module.params["servers"]
    output_file = module.params["output_file"]

    if module.check_mode:
        module.exit_json(
            changed=True,
            output_file=output_file,
            xnames_count=len(servers),
            msg=f"Would generate {len(servers)} xnames in {output_file}",
        )

    try:
        output_file, xnames_count = generate_xnames_mapping(servers, output_file)
        module.exit_json(
            changed=True,
            output_file=output_file,
            xnames_count=xnames_count,
            msg=f"Generated {xnames_count} xnames in {output_file}",
        )
    except Exception as exc:  # pylint: disable=broad-except
        module.fail_json(msg=f"Failed to generate xnames mapping: {str(exc)}")


if __name__ == "__main__":
    main()
