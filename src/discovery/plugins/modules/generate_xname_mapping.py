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

"""Ansible module to generate XNAME mapping file from OME device location data.

Generates a separate CSV mapping SERVICE_TAG to XNAME based on physical
location data (aisle/rack/rackslot) from OME.  If ALL devices have valid
location data the XNAMEs are derived from the physical topology; otherwise
the file is NOT generated and the orchestrator falls back to its existing
sequential allocation via SMDIdentityResolver.
"""

import csv
import os
import re

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r'''
---
module: generate_xname_mapping
short_description: Generate XNAME mapping file from OME device location data
description:
    - This module generates a separate XNAME mapping CSV file from discovered
      server inventory data collected from OME.
    - If ALL devices have valid physical location data (aisle, rack, rackslot)
      configured in OME, XNAMEs are derived from that location.
    - If ANY device is missing location data, the file is NOT generated.
      The orchestrator will fall back to sequential XNAME allocation via
      SMDIdentityResolver.
options:
    servers:
        description: List of server dictionaries with inventory details including location fields
        required: true
        type: list
    output_file:
        description: Path to the output XNAME mapping CSV file
        required: true
        type: str
author:
    - Dell Inc.
'''

EXAMPLES = r'''
- name: Generate XNAME mapping file from OME location data
  generate_xname_mapping:
    servers: "{{ discovered_servers }}"
    output_file: "/path/to/xname_mapping_file.csv"
  register: xname_mapping_result

- name: Report XNAME mapping result
  ansible.builtin.debug:
    msg: "XNAME mode: {{ xname_mapping_result.xname_mode }}"
'''

RETURN = r'''
file_path:
    description: Path to the generated XNAME mapping file (empty if not generated)
    type: str
    returned: always
server_count:
    description: Number of servers written to the mapping file
    type: int
    returned: always
xname_file_generated:
    description: Whether the XNAME mapping file was generated
    type: bool
    returned: always
xname_mode:
    description: Mode used for XNAME generation (location or skipped)
    type: str
    returned: always
skip_reason:
    description: Reason the file was not generated (empty if generated)
    type: str
    returned: always
'''

# XNAME format validation — same pattern as identity.py in orchestrator
XNAME_RE = re.compile(r"^x1000c[0-9]+s[0-9]+b[0-9]+n0$")

# Pattern to extract leading or trailing digits from a string
_NUMBER_RE = re.compile(r"\d+")


def _sanitize_csv_value(value):
    """Prefix CSV values that could trigger formula injection in Excel."""
    if not value:
        return value
    if value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


def extract_number(identifier):
    """Extract the first numeric substring from an identifier.

    Examples:
        "Aisle3"  -> 3
        "Rack6"   -> 6
        "Rack12"  -> 12
        "3"       -> 3
        ""        -> None
        "NoDigit" -> None

    Returns:
        int or None
    """
    if not identifier:
        return None
    match = _NUMBER_RE.search(str(identifier))
    if match:
        return int(match.group())
    return None


def check_all_have_location(servers):
    """Check if ALL servers have valid location data.

    Valid means: aisle has a number, rack has a number, rackslot is a
    positive integer.

    Returns:
        (bool, str): (all_valid, reason_if_not)
    """
    for server in servers:
        svc_tag = server.get("service_tag", "unknown")
        aisle = server.get("aisle", "")
        rack = server.get("rack", "")
        rackslot = server.get("rackslot", "")

        aisle_num = extract_number(aisle)
        rack_num = extract_number(rack)

        try:
            rackslot_num = int(rackslot) if rackslot else 0
        except (ValueError, TypeError):
            rackslot_num = 0

        if aisle_num is None:
            return False, (
                f"Device {svc_tag}: missing or invalid aisle (row) value "
                f"'{aisle}' in OME location data"
            )
        if rack_num is None:
            return False, (
                f"Device {svc_tag}: missing or invalid rack value "
                f"'{rack}' in OME location data"
            )
        if rackslot_num <= 0:
            return False, (
                f"Device {svc_tag}: missing or invalid rackslot (slot) value "
                f"'{rackslot}' in OME location data"
            )

    return True, ""


def generate_location_xnames(servers):
    """Generate XNAMEs from physical location data.

    Formula: x1000c{rack_num}s{aisle_num}b{rackslot_num}n0

    Where:
        rack_num    = number extracted from OME Rack field (e.g. "Rack6" -> 6)
        aisle_num   = number extracted from OME Aisle field (e.g. "Aisle3" -> 3)
        rackslot_num = integer from OME Rackslot field (e.g. "1" -> 1)

    Returns:
        list of (service_tag, xname) tuples
    """
    results = []
    for server in servers:
        svc_tag = server.get("service_tag", "")
        rack_num = extract_number(server.get("rack", ""))
        aisle_num = extract_number(server.get("aisle", ""))
        rackslot_num = int(server.get("rackslot", "0"))

        xname = f"x1000c{rack_num}s{aisle_num}b{rackslot_num}n0"
        results.append((svc_tag, xname))

    return results


def main():
    """Main function for the Ansible module."""
    module_args = {
        "servers": {"type": "list", "required": True},
        "output_file": {"type": "str", "required": True},
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    servers = module.params["servers"]
    output_file = module.params["output_file"]

    headers = ["SERVICE_TAG", "XNAME"]

    # No servers — nothing to do
    if not servers:
        module.exit_json(
            changed=False,
            file_path="",
            server_count=0,
            xname_file_generated=False,
            xname_mode="skipped",
            skip_reason="No servers provided"
        )

    if module.check_mode:
        all_valid, _ = check_all_have_location(servers)
        module.exit_json(
            changed=all_valid,
            file_path=output_file if all_valid else "",
            server_count=len(servers) if all_valid else 0,
            xname_file_generated=all_valid,
            xname_mode="location" if all_valid else "skipped",
            skip_reason="" if all_valid else "check_mode"
        )

    # Strict all-or-nothing check
    all_valid, skip_reason = check_all_have_location(servers)

    if not all_valid:
        module.exit_json(
            changed=False,
            file_path="",
            server_count=0,
            xname_file_generated=False,
            xname_mode="skipped",
            skip_reason=skip_reason
        )

    try:
        # Generate location-based XNAMEs
        xname_pairs = generate_location_xnames(servers)

        # Validate XNAME format
        for svc_tag, xname in xname_pairs:
            if not XNAME_RE.fullmatch(xname):
                module.fail_json(
                    msg=(
                        f"Device {svc_tag}: generated XNAME '{xname}' does not "
                        "match expected format x1000c<N>s<N>b<N>n0. "
                        "Check OME location values for this device."
                    )
                )

        # Validate no duplicate XNAMEs
        xname_list = [xname for _, xname in xname_pairs]
        seen = {}
        for svc_tag, xname in xname_pairs:
            if xname in seen:
                module.fail_json(
                    msg=(
                        f"Duplicate XNAME '{xname}' generated for devices "
                        f"'{seen[xname]}' and '{svc_tag}'. "
                        "OME location data (Rack/Aisle/Rackslot) must produce "
                        "unique XNAMEs for each device. "
                        "Check and fix the physical location configuration in OME."
                    )
                )
            seen[xname] = svc_tag

        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755)

        # Write CSV file with secure permissions (0640)
        fd = os.open(output_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
        try:
            os.fchmod(fd, 0o640)
        except Exception:
            os.close(fd)
            raise
        with os.fdopen(fd, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            for svc_tag, xname in xname_pairs:
                writer.writerow({
                    "SERVICE_TAG": _sanitize_csv_value(svc_tag),
                    "XNAME": _sanitize_csv_value(xname),
                })

        module.exit_json(
            changed=True,
            file_path=output_file,
            server_count=len(xname_pairs),
            xname_file_generated=True,
            xname_mode="location",
            skip_reason="",
            msg=f"Successfully generated XNAME mapping file with {len(xname_pairs)} servers (location-based)"
        )

    except Exception as e:  # pylint: disable=broad-except
        module.fail_json(msg=f"Error generating XNAME mapping file: {str(e)}")


if __name__ == "__main__":
    main()
