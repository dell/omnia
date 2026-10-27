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

"""SMD identity and functional-group verification after provision."""

from collections import defaultdict
from typing import Any

from ..vars.provision_vars import (
    ADDITIONAL_METADATA_PREFIX,
    COMMON_METADATA_GROUPS,
)
from ._provision_helpers import (
    api_json,
    exception_result,
    group_header,
    group_members,
    load_context,
    metadata_name,
    node_field,
    observe_smd,
    resource_list,
    result,
)


def check_smd_identity(host) -> dict[str, Any]:
    """Verify live SMD node and admin-interface identity by functional group."""
    try:
        context = load_context(host)
        observed = observe_smd(host, context)
        fields = [
            ("Desired nodes", len(context["rows"])),
            ("SMD node components", len(observed["node_components"])),
            ("SMD Ethernet interfaces", len(observed["interfaces"])),
        ]
        for group in observed["groups"]:
            group_header(fields, group["name"])
            valid = sum(not node["errors"] for node in group["nodes"])
            fields.append(("  Valid admin identities", f"{valid}/{len(group['rows'])}"))
            for node in group["nodes"]:
                if node["errors"]:
                    fields.append(node_field(node, "✗", "; ".join(node["errors"])))
                else:
                    row = node["row"]
                    fields.append(
                        node_field(
                            node,
                            "✓",
                            f"{node['xname']} | {row['ADMIN_IP']} | {row['ADMIN_MAC']}",
                        )
                    )
        return result(
            not observed["errors"],
            "SMD identities checked per functional group",
            fields,
            "; ".join(observed["errors"]),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result("SMD identity could not be validated", exc)


def check_smd_groups(host) -> dict[str, Any]:
    """Verify expected membership and reject competing cloud-init groups."""
    try:
        context = load_context(host)
        observed = observe_smd(host, context)
        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        cloud_groups = {metadata_name(item) for item in metadata_groups}
        memberships: dict[str, set[str]] = defaultdict(set)
        for item in observed["smd_groups"]:
            label = str(item.get("label") or "").strip()
            for xname in group_members(item):
                memberships[xname].add(label)
        failures = list(observed["errors"])
        fields = [
            ("SMD groups", len(observed["smd_groups"])),
            ("Cloud-init groups", len(cloud_groups)),
        ]
        allowed_auxiliary = {
            name
            for name in cloud_groups
            if name == ADDITIONAL_METADATA_PREFIX
            or name.startswith(f"{ADDITIONAL_METADATA_PREFIX}_")
        }
        for group in observed["groups"]:
            group_header(fields, group["name"])
            conflicts = []
            allowed = {
                group["name"],
                *COMMON_METADATA_GROUPS,
                *allowed_auxiliary,
            }
            for node in group["nodes"]:
                if not node["xname"]:
                    continue
                extra = sorted((memberships[node["xname"]] & cloud_groups) - allowed)
                if extra:
                    conflicts.append(f"{node['xname']}: {','.join(extra)}")
            failures.extend(
                f"{group['name']}: conflicting cloud-init groups={item}"
                for item in conflicts
            )
            fields.extend(
                [
                    ("  Expected members", len(group["rows"])),
                    ("  SMD members", len(group["members"])),
                    ("  Cloud-init conflicts", len(conflicts)),
                ]
            )
            fields.extend(("  Conflict", f"✗ {item}") for item in conflicts)
        return result(
            not failures,
            "SMD functional-group membership checked",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result("SMD groups could not be validated", exc)
