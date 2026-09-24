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

"""CoreDHCP and CoreDNS source-inventory verification after provision."""

from typing import Any

from ._provision_helpers import (
    exception_result,
    group_header,
    load_context,
    node_field,
    observe_smd,
    result,
)


def check_network_inventory(host) -> dict[str, Any]:
    """Verify the SMD records consumed dynamically by CoreDHCP and CoreDNS."""
    try:
        context = load_context(host)
        observed = observe_smd(host, context)
        failures = list(observed["errors"])
        fields = [
            ("CoreDNS enabled", context["dns_enabled"]),
            ("SMD source interfaces", len(observed["interfaces"])),
        ]
        for group in observed["groups"]:
            group_header(fields, group["name"])
            valid = 0
            node_fields = []
            for node in group["nodes"]:
                row = node["row"]
                interface = node["interface"]
                errors = []
                if not isinstance(interface, dict):
                    errors.append("no unique DHCP/DNS source interface")
                else:
                    description = str(interface.get("Description") or "").strip()
                    names = {row["HOSTNAME"]}
                    if context["domain_name"]:
                        names.add(f"{row['HOSTNAME']}.{context['domain_name']}")
                    valid_descriptions = names | {
                        f"Interface 0 for {name}" for name in names
                    }
                    if description not in valid_descriptions:
                        errors.append(
                            f"hostname description={description or 'missing'}"
                        )
                if errors:
                    failures.append(
                        f"{group['name']}/{row['HOSTNAME']}: " + "; ".join(errors)
                    )
                    node_fields.append(node_field(node, "✗", "; ".join(errors)))
                else:
                    valid += 1
                    node_fields.append(
                        node_field(
                            node,
                            "✓",
                            f"{row['ADMIN_IP']} | {row['ADMIN_MAC']}",
                        )
                    )
            fields.append(("  Valid network records", f"{valid}/{len(group['nodes'])}"))
            fields.extend(node_fields)
        return result(
            not failures,
            "CoreDHCP/CoreDNS inventory checked per functional group",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result("Network inventory could not be validated", exc)
