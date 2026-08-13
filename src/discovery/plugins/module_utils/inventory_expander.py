#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

"""Shared sparse-to-complete inventory expansion utility.

This module is used by bmc_lease_handler.yml and the magellan_discovery Ansible role.
It expands a sparse admin_inventory.csv (SERVICE_TAG, GROUP_NAME,
FUNCTIONAL_GROUP_NAME, optional ROW, RACK, USLOT/SLOT, RANGE) into a complete
CSV containing BMC_IP values and, when location columns are supplied, USLOT
values.

Location is optional at the inventory level:
- If ROW and RACK columns are present, USLOT is assigned per (ROW, RACK)
  across the entire file and BMC_IP is assigned per GROUP_NAME.
- If ROW and RACK columns are absent, location expansion is skipped and only
  SERVICE_TAG, GROUP_NAME, FUNCTIONAL_GROUP_NAME, and BMC_IP are emitted.

USLOT assignment is independent of IP assignment:
- USLOT is assigned per (ROW, RACK) starting at 1.
- BMC_IP is assigned sequentially from the GROUP_NAME's RANGE.
"""

import argparse
import csv
import ipaddress
import os
import sys
from typing import Any, Dict, List, Tuple

REQUIRED_COLUMNS = [
    "SERVICE_TAG",
    "GROUP_NAME",
    "FUNCTIONAL_GROUP_NAME",
    "RANGE",
]

# CSM xname component limits. The expander validates these up-front so that
# invalid location data is caught before xnames are generated.
MAX_ROW = 8999
MAX_RACK = 2047
MAX_USLOT = 255


def _ip_to_int(ip_str: str) -> int:
    """Convert an IPv4 address string to a 32-bit integer."""
    return int(ipaddress.IPv4Address(ip_str))


def _int_to_ip(ip_int: int) -> str:
    """Convert a 32-bit integer to an IPv4 address string."""
    return str(ipaddress.IPv4Address(ip_int))


def _ip_is_reserved_host(ip_int: int, range_start: int, range_end: int) -> bool:
    """Return True when ip_int is the network or broadcast address of its RANGE.

    When the RANGE is exactly one CIDR-sized block (its size is a power of two
    and its start is aligned to that size), the first and last addresses are
    reserved and must not be assigned as a BMC_IP.  For non-CIDR ranges we do
    not make assumptions about the containing subnet.
    """
    range_size = range_end - range_start + 1
    if range_size > 0 and (range_size & (range_size - 1)) == 0 and (range_start % range_size) == 0:
        return ip_int == range_start or ip_int == range_end
    return False


def _count_usable_ipv4(start_int: int, end_int: int) -> int:
    """Count usable host addresses in [start_int, end_int]."""
    count = 0
    for ip_int in range(start_int, end_int + 1):
        if not _ip_is_reserved_host(ip_int, start_int, end_int):
            count += 1
    return count


def _usable_ipv4_generator(start_int: int, end_int: int):
    """Yield usable host IPv4 integers in [start_int, end_int]."""
    for ip_int in range(start_int, end_int + 1):
        if not _ip_is_reserved_host(ip_int, start_int, end_int):
            yield ip_int


def _is_valid_ipv4(ip_str: str) -> bool:
    """Return True if the string is a valid IPv4 address."""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def _is_non_negative_int(value: str) -> bool:
    """Return True if the value is a non-negative integer."""
    try:
        return int(value) >= 0
    except (ValueError, TypeError):
        return False


def _is_valid_range_value(value: str, max_value: int) -> bool:
    """Return True if the value is a non-negative integer not exceeding max_value."""
    try:
        return 0 <= int(value) <= max_value
    except (ValueError, TypeError):
        return False


def _to_int(value: Any, default: int) -> int:
    """Convert a value to int, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _carry_forward(rows: List[Dict[str, Any]], has_location: bool) -> None:
    """Fill blank GROUP_NAME, FUNCTIONAL_GROUP_NAME, ROW, RACK, and RANGE values.

    GROUP_NAME and FUNCTIONAL_GROUP_NAME are carried from the last non-empty
    value seen in the file. ROW and RACK are also carried globally when the
    input contains location columns. RANGE is carried per GROUP_NAME so that a
    group keeps its own range and does not inherit another group's range.
    """
    carry_columns = ["GROUP_NAME", "FUNCTIONAL_GROUP_NAME"]
    if has_location:
        carry_columns.extend(["ROW", "RACK"])
    last_values: Dict[str, str] = {col: "" for col in carry_columns}
    group_ranges: Dict[str, str] = {}

    for row in rows:
        for col in carry_columns:
            value = row.get(col, "").strip()
            if value:
                last_values[col] = value
            row[col] = last_values[col]

        group = row["GROUP_NAME"]
        range_val = row.get("RANGE", "").strip()
        if range_val:
            group_ranges[group] = range_val
            row["RANGE"] = range_val
        elif group in group_ranges:
            row["RANGE"] = group_ranges[group]


def parse_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Parse the sparse admin inventory CSV and return a list of row dicts."""
    if not os.path.exists(csv_path):
        raise ValueError(f"CSV file not found: {csv_path}")

    errors = []
    rows: List[Dict[str, Any]] = []

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header row")

        fieldnames = [name.strip() for name in reader.fieldnames]
        missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        if "SLOT" in fieldnames and "USLOT" in fieldnames:
            raise ValueError("CSV cannot contain both SLOT and USLOT columns")

        slot_source = ""
        if "USLOT" in fieldnames:
            slot_source = "USLOT"
        elif "SLOT" in fieldnames:
            slot_source = "SLOT"

        has_location = "ROW" in fieldnames and "RACK" in fieldnames
        if slot_source and not has_location:
            raise ValueError("SLOT/USLOT column requires ROW and RACK columns")

        raw_rows: List[Dict[str, Any]] = []
        for row_num, raw_row in enumerate(reader, start=2):
            row = {
                k.strip(): (v.strip() if v is not None else "")
                for k, v in raw_row.items()
            }
            if slot_source == "SLOT":
                row["USLOT"] = row.get("SLOT", "")
            row["_row_num"] = row_num
            row["_has_location"] = has_location
            raw_rows.append(row)

    _carry_forward(raw_rows, has_location)

    for row in raw_rows:
        row_num = row["_row_num"]
        row_errors = []
        row_valid = True

        for col in REQUIRED_COLUMNS:
            if not row.get(col):
                row_errors.append(f"Row {row_num}: missing required value for {col}")
                row_valid = False

        if has_location:
            row_val = row.get("ROW", "")
            rack_val = row.get("RACK", "")
            uslot_val = row.get("USLOT", "")
            if not row_val or not rack_val:
                row_errors.append(
                    f"Row {row_num}: ROW and RACK are required because location columns are present"
                )
                row_valid = False
            else:
                if not _is_valid_range_value(row_val, MAX_ROW):
                    row_errors.append(
                        f"Row {row_num}: ROW must be an integer between 0 and {MAX_ROW}, got {row_val}"
                    )
                    row_valid = False
                if not _is_valid_range_value(rack_val, MAX_RACK):
                    row_errors.append(
                        f"Row {row_num}: RACK must be an integer between 0 and {MAX_RACK}, got {rack_val}"
                    )
                    row_valid = False
            if uslot_val and row_valid:
                if not _is_valid_range_value(uslot_val, MAX_USLOT):
                    row_errors.append(
                        f"Row {row_num}: USLOT must be an integer between 0 and {MAX_USLOT}, got {uslot_val}"
                    )
                    row_valid = False

        range_val = row.get("RANGE", "")
        if range_val and "-" not in range_val:
            row_errors.append(f"Row {row_num}: RANGE must be in 'start-end' format")
            row_valid = False
        elif range_val:
            parts = range_val.split("-")
            if len(parts) != 2 or not _is_valid_ipv4(parts[0]) or not _is_valid_ipv4(parts[1]):
                row_errors.append(f"Row {row_num}: RANGE contains invalid IPv4 addresses")
                row_valid = False

        errors.extend(row_errors)

        if row.get("SERVICE_TAG") and row_valid:
            rows.append(row)

    if errors:
        raise ValueError("\n".join(errors))

    return rows


def assign_uslots(rows: List[Dict[str, Any]]) -> None:
    """Assign USLOT values per (ROW, RACK).

    Empty USLOT values are filled with the next available USLOT starting at 1.
    Provided USLOT values are checked for duplicates within the same
    (ROW, RACK) pair across the entire file.
    """
    if not rows or not rows[0].get("_has_location"):
        return

    errors = []
    groups: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for row in rows:
        row_num = row["_row_num"]
        row_val = row.get("ROW", "").strip()
        rack_val = row.get("RACK", "").strip()
        if not row_val and not rack_val:
            row["USLOT"] = ""
            continue
        if not row_val or not rack_val:
            errors.append(
                f"Row {row_num}: ROW and RACK must both be provided for correct expansion"
            )
            continue
        try:
            row_int = int(row_val)
            rack_int = int(rack_val)
        except ValueError:
            errors.append(f"Row {row_num}: ROW and RACK must be non-negative integers")
            continue
        if not (0 <= row_int <= MAX_ROW):
            errors.append(f"Row {row_num}: ROW must be an integer between 0 and {MAX_ROW}, got {row_val}")
            continue
        if not (0 <= rack_int <= MAX_RACK):
            errors.append(f"Row {row_num}: RACK must be an integer between 0 and {MAX_RACK}, got {rack_val}")
            continue
        key = (row_int, rack_int)
        groups.setdefault(key, []).append(row)

    for key, group_rows in groups.items():
        # Pre-collect provided USLOT values so auto-assigned slots never
        # collide with a USLOT provided on a later row in the same (ROW, RACK).
        provided_slots: Dict[int, int] = {}
        for row in group_rows:
            s = row.get("USLOT", "").strip()
            if s:
                if not _is_valid_range_value(s, MAX_USLOT):
                    errors.append(
                        f"Row {row['_row_num']}: USLOT must be an integer between 0 and {MAX_USLOT}, got {s}"
                    )
                    continue
                slot = int(s)
                provided_slots[slot] = provided_slots.get(slot, 0) + 1

        assigned = set()
        next_slot = 1
        for row in group_rows:
            s = row.get("USLOT", "").strip()
            row_num = row["_row_num"]
            if s:
                uslot_int = int(s)
                if uslot_int in assigned:
                    errors.append(
                        f"Row {row_num}: duplicate USLOT {uslot_int} in (ROW, RACK) {key}"
                    )
                elif provided_slots.get(uslot_int, 0) == 0:
                    errors.append(
                        f"Row {row_num}: duplicate USLOT {uslot_int} in (ROW, RACK) {key}"
                    )
                else:
                    provided_slots[uslot_int] -= 1
                    assigned.add(uslot_int)
                    row["USLOT"] = str(uslot_int)
            else:
                while next_slot in assigned or provided_slots.get(next_slot, 0) > 0:
                    next_slot += 1
                if next_slot > MAX_USLOT:
                    errors.append(
                        f"Row {row_num}: cannot auto-assign USLOT for (ROW, RACK) {key}; "
                        f"no free slot between 0 and {MAX_USLOT}"
                    )
                    continue
                uslot_int = next_slot
                assigned.add(uslot_int)
                next_slot += 1
                row["USLOT"] = str(uslot_int)

    if errors:
        raise ValueError("\n".join(errors))


def check_subnet_lengths(rows: List[Dict[str, Any]]) -> List[str]:
    """Return a list of error messages for invalid group ranges.

    Checks that:
    - All rows in a GROUP_NAME share the same RANGE.
    - Each RANGE is in 'start-end' format with valid IPv4 addresses.
    - Each group has enough IPs for its entries.
    - No two groups' ranges overlap.
    """
    errors = []
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["GROUP_NAME"], []).append(row)

    group_ranges: List[Tuple[str, int, int]] = []
    for group_name, group_rows in groups.items():
        ranges = set(r["RANGE"] for r in group_rows if r.get("RANGE"))
        if len(ranges) > 1:
            errors.append(
                f"Group {group_name}: all rows in a group must share the same RANGE"
            )
            continue
        if not ranges:
            errors.append(f"Group {group_name}: RANGE is missing")
            continue

        range_val = list(ranges)[0]
        if "-" not in range_val:
            errors.append(f"Group {group_name}: RANGE must be in 'start-end' format")
            continue
        parts = range_val.split("-")
        if len(parts) != 2 or not _is_valid_ipv4(parts[0]) or not _is_valid_ipv4(parts[1]):
            errors.append(f"Group {group_name}: RANGE contains invalid IPv4 addresses")
            continue

        start_int = _ip_to_int(parts[0])
        end_int = _ip_to_int(parts[1])
        if start_int > end_int:
            errors.append(
                f"Group {group_name}: RANGE start {parts[0]} is greater than end {parts[1]}"
            )
            continue

        available = _count_usable_ipv4(start_int, end_int)
        if len(group_rows) > available:
            errors.append(
                f"Group {group_name}: {len(group_rows)} entries but RANGE {range_val} "
                f"only provides {available} usable host IPs"
            )
            continue

        group_ranges.append((group_name, start_int, end_int))

    for i in range(len(group_ranges)):
        for j in range(i + 1, len(group_ranges)):
            g1, s1, e1 = group_ranges[i]
            g2, s2, e2 = group_ranges[j]
            if s1 <= e2 and s2 <= e1:
                errors.append(
                    f"Group {g1} RANGE {_int_to_ip(s1)}-{_int_to_ip(e1)} overlaps with "
                    f"Group {g2} RANGE {_int_to_ip(s2)}-{_int_to_ip(e2)}"
                )

    return errors


def allocate_ips(rows: List[Dict[str, Any]]) -> None:
    """Assign BMC_IP values sequentially from each GROUP_NAME's RANGE.

    Rows within a group are ordered by ROW, RACK, USLOT when location columns are
    present; otherwise they are kept in input order for deterministic allocation.
    """
    errors = []
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["GROUP_NAME"], []).append(row)

    has_location = rows[0].get("_has_location", False) if rows else False

    for group_name, group_rows in groups.items():
        ranges = set(r["RANGE"] for r in group_rows)
        if len(ranges) > 1:
            errors.append(
                f"Group {group_name}: all rows in a group must share the same RANGE"
            )
            continue

        range_val = group_rows[0].get("RANGE", "")
        if "-" not in range_val:
            errors.append(f"Group {group_name}: RANGE must be in 'start-end' format")
            continue
        parts = range_val.split("-")
        if len(parts) != 2 or not _is_valid_ipv4(parts[0]) or not _is_valid_ipv4(parts[1]):
            errors.append(f"Group {group_name}: RANGE contains invalid IPv4 addresses")
            continue

        start_int = _ip_to_int(parts[0])
        end_int = _ip_to_int(parts[1])
        if start_int > end_int:
            errors.append(
                f"Group {group_name}: RANGE start {parts[0]} is greater than end {parts[1]}"
            )
            continue

        available = _count_usable_ipv4(start_int, end_int)
        if len(group_rows) > available:
            errors.append(
                f"Group {group_name}: not enough usable host IPs in RANGE {range_val}"
            )
            continue

        if has_location:
            sorted_rows = sorted(
                group_rows,
                key=lambda r: (
                    _to_int(r.get("ROW", ""), 2_147_483_647),
                    _to_int(r.get("RACK", ""), 2_147_483_647),
                    _to_int(r.get("USLOT", ""), 2_147_483_647),
                    r["_row_num"],
                ),
            )
        else:
            sorted_rows = sorted(group_rows, key=lambda r: r["_row_num"])

        ip_gen = _usable_ipv4_generator(start_int, end_int)
        for row in sorted_rows:
            row["BMC_IP"] = _int_to_ip(next(ip_gen))

    if errors:
        raise ValueError("\n".join(errors))


def build_complete(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return the complete inventory list in the original CSV order."""
    seen_service_tags: Dict[str, int] = {}
    errors = []
    complete: List[Dict[str, Any]] = []

    if not rows:
        raise ValueError("CSV file has no data rows")

    has_location = rows[0].get("_has_location", False)
    if has_location:
        output_columns = [
            "SERVICE_TAG",
            "GROUP_NAME",
            "FUNCTIONAL_GROUP_NAME",
            "ROW",
            "RACK",
            "USLOT",
            "BMC_IP",
        ]
    else:
        output_columns = [
            "SERVICE_TAG",
            "GROUP_NAME",
            "FUNCTIONAL_GROUP_NAME",
            "BMC_IP",
        ]

    for row in rows:
        service_tag = row["SERVICE_TAG"]
        row_num = row["_row_num"]
        if service_tag in seen_service_tags:
            errors.append(
                f"Row {row_num}: duplicate SERVICE_TAG '{service_tag}' "
                f"(first seen at row {seen_service_tags[service_tag]})"
            )
        else:
            seen_service_tags[service_tag] = row_num

        complete_row: Dict[str, Any] = {col: row.get(col, "") for col in output_columns}
        complete.append(complete_row)

    if errors:
        raise ValueError("\n".join(errors))

    if not complete:
        raise ValueError("CSV file has no data rows")

    return complete


def expand_inventory(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Expand already-parsed sparse rows into complete inventory rows."""
    assign_uslots(rows)
    errors = check_subnet_lengths(rows)
    if errors:
        raise ValueError("\n".join(errors))
    allocate_ips(rows)
    return build_complete(rows)


def load_sparse_inventory(csv_path: str) -> List[Dict[str, Any]]:
    """Parse the sparse admin inventory CSV and expand it to a complete list."""
    rows = parse_csv(csv_path)
    return expand_inventory(rows)


def save_complete_inventory_csv(path: str, complete: List[Dict[str, Any]]) -> None:
    """Write the complete inventory to a CSV file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not complete:
        raise ValueError("No complete rows to write")
    fieldnames = [k for k in complete[0].keys() if not k.startswith("_")]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(complete)


def main() -> int:
    """CLI entry point for the inventory expander."""
    parser = argparse.ArgumentParser(description="Expand sparse admin_inventory.csv to a complete inventory CSV")
    parser.add_argument("--input", required=True, help="Path to sparse admin_inventory.csv")
    parser.add_argument("--csv", required=False, help="Path to write the complete inventory CSV")
    parser.add_argument("--validate", action="store_true", help="Validate the sparse CSV without writing output")
    args = parser.parse_args()

    complete = load_sparse_inventory(args.input)

    if args.validate:
        print(f"Validation passed: {len(complete)} entries")
        return 0

    if not args.csv:
        print("ERROR: --csv is required unless --validate is used", file=sys.stderr)
        return 1

    save_complete_inventory_csv(args.csv, complete)
    print(f"Complete inventory written to {args.csv} ({len(complete)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
