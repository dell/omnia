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

"""Boot Service configuration and node identity verification."""

import time
from collections import defaultdict
from typing import Any

from ..vars.provision_vars import (
    BOOT_SERVICE_SYNC_DELAY_SECONDS,
    BOOT_SERVICE_SYNC_RETRIES,
)
from ._provision_helpers import (
    api_json,
    exception_result,
    group_header,
    load_context,
    metadata_name,
    node_field,
    normalise_mac,
    observe_smd,
    resource_list,
    result,
)


def check_boot_configurations(host) -> dict[str, Any]:
    """Verify one complete BootConfiguration per effective functional group."""
    try:
        context = load_context(host)
        configurations = resource_list(api_json(host, "boot_configurations"))
        failures = []
        fields = [("Boot configurations", len(configurations))]
        for name, rows in context["rows_by_fg"].items():
            group_header(fields, name)
            matches = [item for item in configurations if metadata_name(item) == name]
            errors = []
            configured_macs = []
            if len(matches) != 1:
                errors.append(f"configuration count={len(matches)}")
            else:
                spec = matches[0].get("spec")
                if not isinstance(spec, dict):
                    errors.append("spec missing")
                else:
                    errors.extend(
                        f"{field} missing"
                        for field in ("kernel", "initrd", "params")
                        if not str(spec.get(field) or "").strip()
                    )
                    configured_macs = (
                        sorted(normalise_mac(value) for value in spec.get("macs", []))
                        if isinstance(spec.get("macs"), list)
                        else []
                    )
                    expected_macs = sorted(row["ADMIN_MAC"] for row in rows)
                    if configured_macs != expected_macs:
                        errors.append("boot MAC set does not match mapping")
            fields.extend(
                [
                    (
                        "  Record",
                        "✓ unique" if len(matches) == 1 else f"✗ count={len(matches)}",
                    ),
                    ("  Boot MACs", f"{len(configured_macs)}/{len(rows)}"),
                    (
                        "  Boot artifacts",
                        "✓ complete" if not errors else "✗ invalid",
                    ),
                ]
            )
            failures.extend(f"{name}: {error}" for error in errors)
        return result(
            not failures,
            "Boot configurations checked per functional group",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result("Boot configurations could not be validated", exc)


def _check_boot_node_records(nodes, observed):
    by_xname: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in nodes:
        spec = item.get("spec")
        if isinstance(spec, dict):
            by_xname[str(spec.get("xname") or "").strip()].append(item)
    failures = []
    fields = []
    for group in observed["groups"]:
        group_header(fields, group["name"])
        valid = 0
        node_fields = []
        for node in group["nodes"]:
            row = node["row"]
            xname = node["xname"]
            errors = []
            matches = by_xname.get(xname, []) if xname else []
            if len(matches) != 1:
                errors.append(f"Boot Service node count={len(matches)}")
            else:
                spec = matches[0].get("spec") or {}
                actual_mac = normalise_mac(spec.get("bootMac"))
                if actual_mac != row["ADMIN_MAC"]:
                    errors.append(f"bootMac={actual_mac or 'missing'}")
                if (
                    not isinstance(spec.get("groups"), list)
                    or group["name"] not in spec["groups"]
                ):
                    errors.append("functional group is missing")
            foreign = sorted(
                {
                    str((item.get("spec") or {}).get("xname") or "unknown")
                    for item in nodes
                    if normalise_mac((item.get("spec") or {}).get("bootMac"))
                    == row["ADMIN_MAC"]
                    and str((item.get("spec") or {}).get("xname") or "") != xname
                }
            )
            if foreign:
                errors.append("bootMac also owned by " + ",".join(foreign))
            if errors:
                failures.append(
                    f"{group['name']}/{row['HOSTNAME']}: " + "; ".join(errors)
                )
                node_fields.append(node_field(node, "✗", "; ".join(errors)))
            else:
                valid += 1
                node_fields.append(
                    node_field(node, "✓", f"{xname} | {row['ADMIN_MAC']}")
                )
        fields.append(("  Synchronized nodes", f"{valid}/{len(group['nodes'])}"))
        fields.extend(node_fields)
    return failures, fields


def check_boot_nodes(host) -> dict[str, Any]:
    """Verify synchronized Boot Service XNAME-to-bootMac identity."""
    try:
        context = load_context(host)
        observed = observe_smd(host, context)
        attempts = 0
        nodes = []
        fields = []
        failures = []
        while True:
            attempts += 1
            nodes = resource_list(api_json(host, "boot_nodes"))
            failures, fields = _check_boot_node_records(nodes, observed)
            failures = [*observed["errors"], *failures]
            if not failures or attempts >= BOOT_SERVICE_SYNC_RETRIES:
                break
            time.sleep(BOOT_SERVICE_SYNC_DELAY_SECONDS)
        fields = [
            ("Boot Service records", len(nodes)),
            ("Synchronization checks", attempts),
            *fields,
        ]
        return result(
            not failures,
            "Boot Service identities checked per functional group",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result("Boot Service nodes could not be validated", exc)
