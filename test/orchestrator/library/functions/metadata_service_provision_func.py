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

"""Metadata Service group and instance verification after provision."""

from collections import defaultdict
from typing import Any

from ._provision_helpers import (
    api_json,
    exception_result,
    group_header,
    load_context,
    metadata_name,
    node_field,
    observe_smd,
    resource_list,
    result,
)


def check_metadata_groups(host) -> dict[str, Any]:
    """Verify one valid cloud-init group per effective functional group."""
    try:
        context = load_context(host)
        groups = resource_list(api_json(host, "metadata_groups"))
        failures = []
        fields = [("Metadata Service groups", len(groups))]
        for name, rows in context["rows_by_fg"].items():
            group_header(fields, name)
            matches = [item for item in groups if metadata_name(item) == name]
            errors = []
            if len(matches) != 1:
                errors.append(f"metadata group count={len(matches)}")
            else:
                metadata = matches[0].get("metadata")
                spec = matches[0].get("spec")
                status = matches[0].get("status")
                if not isinstance(metadata, dict) or not metadata.get("uid"):
                    errors.append("metadata.uid missing")
                if (
                    not isinstance(spec, dict)
                    or not str(spec.get("template") or "").strip()
                ):
                    errors.append("cloud-init template missing")
                if isinstance(status, dict) and status.get("valid") is False:
                    errors.append("metadata template status is invalid")
            fields.extend(
                [
                    (
                        "  Record",
                        "✓ unique" if len(matches) == 1 else f"✗ count={len(matches)}",
                    ),
                    (
                        "  Cloud-init template",
                        "✓ valid" if not errors else "✗ invalid",
                    ),
                    ("  Target nodes", len(rows)),
                ]
            )
            failures.extend(f"{name}: {error}" for error in errors)
        return result(
            not failures,
            "Metadata groups checked per functional group",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result("Metadata groups could not be validated", exc)


def check_metadata_instances(host) -> dict[str, Any]:
    """Verify unique hostname metadata for every SMD-resolved node."""
    try:
        context = load_context(host)
        observed = observe_smd(host, context)
        instances = resource_list(api_json(host, "instance_infos"))
        by_xname: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in instances:
            spec = item.get("spec")
            if isinstance(spec, dict):
                by_xname[str(spec.get("instance_id") or "").strip()].append(item)
        failures = list(observed["errors"])
        fields = [("Instance-info records", len(instances))]
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
                    errors.append(f"instance-info count={len(matches)}")
                else:
                    spec = matches[0].get("spec") or {}
                    expected = {row["HOSTNAME"]}
                    if context["domain_name"]:
                        expected.add(f"{row['HOSTNAME']}.{context['domain_name']}")
                    actual = {
                        str(spec.get("hostname") or "").strip(),
                        str(spec.get("local_hostname") or "").strip(),
                    }
                    if "" in actual or not actual <= expected:
                        errors.append("hostname metadata does not match mapping")
                    metadata = matches[0].get("metadata")
                    if not isinstance(metadata, dict) or not metadata.get("uid"):
                        errors.append("metadata.uid missing")
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
                            f"{xname} | unique hostname metadata",
                        )
                    )
            fields.append(("  Valid instances", f"{valid}/{len(group['nodes'])}"))
            fields.extend(node_fields)
        return result(
            not failures,
            "Metadata instances checked per functional group",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result("Metadata instances could not be validated", exc)
