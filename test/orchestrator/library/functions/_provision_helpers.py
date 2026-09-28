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

"""Private desired-state and OpenCHAMI helpers for provision verification."""

import csv
import io
import json
import os
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

from omnia_auto import run_on_host

from ..vars.provision_vars import (
    DEFAULT_MAPPING_FILE,
    FUNCTIONAL_GROUP_CONFIG,
    OPENCHAMI_API_PATHS,
    ORCHESTRATOR_CONFIG,
    PROVISION_COMMANDS,
    REQUIRED_MAPPING_COLUMNS,
)
from ._prepare_helpers import read_yaml_mapping
from .project_func import (
    resolve_target_input_project_path,
    resolve_target_output_project_path,
)


def result(
    success: bool,
    summary: str,
    fields: list[tuple[str, object]],
    error: str = "",
) -> dict[str, Any]:
    """Return the stable structured result consumed by provision tests."""
    return {
        "success": success,
        "details": {"summary": summary, "fields": fields},
        "error": error,
        "skipped": False,
    }


def exception_result(summary: str, exc: Exception) -> dict[str, Any]:
    """Return one failed result for a boundary or transport exception."""
    return result(False, summary, [], str(exc))


def normalise_mac(value: object) -> str:
    """Return one lowercase colon-delimited MAC address."""
    compact = re.sub(r"[^0-9A-Fa-f]", "", str(value or ""))
    if len(compact) != 12:
        return str(value or "").strip().lower()
    return ":".join(compact[index : index + 2] for index in range(0, 12, 2)).lower()


def duplicates(values) -> list[str]:
    """Return sorted non-empty duplicate values."""
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _mapping_path(host, input_dir: str) -> str:
    config = read_yaml_mapping(host, os.path.join(input_dir, ORCHESTRATOR_CONFIG))
    configured = str(config.get("pxe_mapping_file_path") or "").strip()
    if configured:
        if not os.path.isabs(configured):
            raise ValueError("pxe_mapping_file_path must be absolute when overridden")
        return configured
    return os.path.join(input_dir, DEFAULT_MAPPING_FILE)


def _read_mapping(host, path: str) -> list[dict[str, str]]:
    """Read the user mapping without generating XNAMEs or temporary files."""
    source = host.file(path)
    if not source.is_file:
        raise ValueError(f"Required PXE mapping file is missing: {path}")
    lines = [
        line.strip()
        for line in source.content_string.splitlines()
        if line.strip() and not re.match(r"^\s*#", line)
    ]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    headers = tuple(reader.fieldnames or ())
    missing = [column for column in REQUIRED_MAPPING_COLUMNS if column not in headers]
    if missing:
        raise ValueError("PXE mapping is missing columns: " + ", ".join(missing))

    rows = []
    for row_index, source_row in enumerate(reader):
        row = {
            str(key).strip(): str(value or "").strip()
            for key, value in source_row.items()
            if key is not None
        }
        required = (
            "FUNCTIONAL_GROUP_NAME",
            "GROUP_NAME",
            "HOSTNAME",
            "ADMIN_MAC",
            "ADMIN_IP",
        )
        empty = [field for field in required if not row.get(field)]
        if empty:
            raise ValueError(
                f"PXE mapping row {row_index + 2} has empty fields: " + ", ".join(empty)
            )
        row["ADMIN_MAC"] = normalise_mac(row["ADMIN_MAC"])
        rows.append(row)
    if not rows:
        raise ValueError("PXE mapping contains no node rows")
    conflicts = []
    for label in ("ADMIN_MAC", "ADMIN_IP", "HOSTNAME"):
        duplicate_values = duplicates(row[label] for row in rows)
        if duplicate_values:
            conflicts.append(f"duplicate {label}: {', '.join(duplicate_values)}")
    if conflicts:
        raise ValueError("; ".join(conflicts))
    return rows


def _without_first_role(name: str) -> str:
    return name.replace("_first_", "_", 1)


def _assign_functional_groups(
    host,
    path: str,
    rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    """Map user groups to effective groups, including internal first KCP."""
    config = read_yaml_mapping(host, path)
    definitions = config.get("functional_groups")
    if not isinstance(definitions, list) or not definitions:
        raise ValueError(f"functional_groups is empty or invalid in {path}")
    candidates: dict[str, list[str]] = defaultdict(list)
    for item in definitions:
        if not isinstance(item, dict):
            raise TypeError(f"Invalid functional-group entry in {path}")
        name = str(item.get("name") or "").strip()
        groups = item.get("group")
        if not name or not isinstance(groups, list) or not groups:
            raise ValueError(f"Malformed functional-group entry in {path}")
        for group in groups:
            group_name = str(group or "").strip()
            if group_name and name not in candidates[group_name]:
                candidates[group_name].append(name)
    unresolved = sorted({row["GROUP_NAME"] for row in rows} - set(candidates))
    if unresolved:
        raise ValueError(
            "Generated functional-group config does not resolve GROUP_NAME(s): "
            + ", ".join(unresolved)
        )

    by_user_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_user_group[row["GROUP_NAME"]].append(row)
    rows_by_fg: dict[str, list[dict[str, str]]] = defaultdict(list)
    for user_group, group_rows in by_user_group.items():
        names = candidates[user_group]
        if len(names) == 1:
            assignments = [names[0]] * len(group_rows)
        else:
            pairs = [
                (first, normal)
                for first in names
                if "_first_" in first
                for normal in names
                if "_first_" not in normal and _without_first_role(first) == normal
            ]
            if len(pairs) != 1:
                raise ValueError(
                    f"GROUP_NAME {user_group} has ambiguous generated roles: "
                    + ", ".join(names)
                )
            first, normal = pairs[0]
            assignments = [first, *([normal] * (len(group_rows) - 1))]
        for row, name in zip(group_rows, assignments, strict=True):
            row["EXPECTED_FUNCTIONAL_GROUP"] = name
            rows_by_fg[name].append(row)
    return dict(sorted(rows_by_fg.items()))


def load_context(host) -> dict[str, Any]:
    """Load desired state from persistent project inputs and outputs."""
    input_dir = resolve_target_input_project_path(host)
    output_dir = resolve_target_output_project_path(host)
    mapping_path = _mapping_path(host, input_dir)
    rows = _read_mapping(host, mapping_path)
    rows_by_fg = _assign_functional_groups(
        host,
        os.path.join(output_dir, FUNCTIONAL_GROUP_CONFIG),
        rows,
    )
    state = read_yaml_mapping(host, os.path.join(output_dir, "orchestrator_state.yml"))
    return {
        "output_dir": output_dir,
        "mapping_path": mapping_path,
        "rows": rows,
        "rows_by_fg": rows_by_fg,
        "domain_name": str(state.get("domain_name") or "").strip(),
        "dns_enabled": bool(state.get("dns_enabled", False)),
    }


def _openchami_base_url(host) -> str:
    config = read_yaml_mapping(host, "/etc/ochami/config.yaml")
    default_name = config.get("default-cluster")
    clusters = config.get("clusters")
    if not isinstance(clusters, list):
        raise TypeError("ochami config clusters must be a list")
    for entry in clusters:
        if not isinstance(entry, dict) or entry.get("name") != default_name:
            continue
        cluster = entry.get("cluster")
        uri = str(cluster.get("uri") if isinstance(cluster, dict) else "").rstrip("/")
        if re.fullmatch(r"https://[A-Za-z0-9.-]+:\d+", uri):
            return uri
    raise ValueError("ochami config has no valid default cluster URI")


def api_json(host, resource: str) -> Any:
    """Read one authenticated API resource using a fresh access token."""
    endpoint = _openchami_base_url(host) + OPENCHAMI_API_PATHS[resource]
    probe = run_on_host(host, PROVISION_COMMANDS["api_get"], endpoint)
    if probe.rc != 0:
        reasons = {
            9: "temporary response-file creation failed",
            10: "access-token generation failed",
            11: "API transport failed",
            12: "API returned a non-success response",
            13: "authentication failed after token refresh",
        }
        reason = reasons.get(probe.rc, f"request rc={probe.rc}")
        raise RuntimeError(f"OpenCHAMI {resource} query failed ({reason})")
    try:
        return json.loads(probe.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenCHAMI {resource} returned invalid JSON") from exc


def resource_list(payload: Any, key: str | None = None) -> list[dict[str, Any]]:
    """Normalize list and SMD wrapper responses without accepting bad shapes."""
    value = payload.get(key) if key and isinstance(payload, dict) else payload
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TypeError(f"OpenCHAMI {key or 'resource'} response is not a list")
    return value


def metadata_name(item: Mapping[str, Any]) -> str:
    """Return the resource name from an OpenCHAMI metadata object."""
    metadata = item.get("metadata")
    return str(metadata.get("name") if isinstance(metadata, dict) else "").strip()


def interface_ips(interface: Mapping[str, Any]) -> set[str]:
    """Return every non-empty IP address recorded on one SMD interface."""
    values = interface.get("IPAddresses")
    if not isinstance(values, list):
        return set()
    return {
        str(value.get("IPAddress") if isinstance(value, dict) else value).strip()
        for value in values
        if (value.get("IPAddress") if isinstance(value, dict) else value)
    }


def group_members(group: Mapping[str, Any]) -> set[str]:
    """Return normalized member identifiers from one SMD group."""
    members = group.get("members")
    if isinstance(members, dict):
        members = members.get("ids")
    if not isinstance(members, list):
        return set()
    return {str(member).strip() for member in members if member}


def _smd_groups(host) -> list[dict[str, Any]]:
    payload = api_json(host, "smd_groups")
    if isinstance(payload, dict) and "Groups" in payload:
        return resource_list(payload, "Groups")
    return resource_list(payload)


def observe_smd(host, context: dict[str, Any]) -> dict[str, Any]:
    """Resolve live XNAMEs from admin MAC/IP records; never fabricate them."""
    interfaces = resource_list(api_json(host, "ethernet"))
    groups = _smd_groups(host)
    components = resource_list(api_json(host, "components"), "Components")
    component_ids = [
        str(item.get("ID") or "").strip()
        for item in components
        if str(item.get("Type") or "").lower() == "node"
    ]
    groups_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        groups_by_label[str(group.get("label") or "").strip()].append(group)

    results = []
    all_errors = []
    for functional_group, rows in context["rows_by_fg"].items():
        records = groups_by_label.get(functional_group, [])
        members = group_members(records[0]) if len(records) == 1 else set()
        errors = []
        if len(records) != 1:
            errors.append(f"SMD group record count={len(records)}")
        nodes = []
        expected_xnames = set()
        for row in rows:
            mac_matches = [
                item
                for item in interfaces
                if normalise_mac(item.get("MACAddress")) == row["ADMIN_MAC"]
            ]
            ip_matches = [
                item for item in interfaces if row["ADMIN_IP"] in interface_ips(item)
            ]
            exact = [
                item for item in mac_matches if row["ADMIN_IP"] in interface_ips(item)
            ]
            node_errors = []
            xname = ""
            interface = exact[0] if len(exact) == 1 else None
            if len(exact) != 1:
                node_errors.append(f"admin interface count={len(exact)}")
            else:
                xname = str(interface.get("ComponentID") or "").strip()
                if not xname:
                    node_errors.append("ComponentID is missing")
                else:
                    expected_xnames.add(xname)
                    if component_ids.count(xname) != 1:
                        node_errors.append(
                            f"Node component count={component_ids.count(xname)}"
                        )
                if str(interface.get("Type") or "").lower() != "node":
                    node_errors.append("interface Type is not Node")
            if (
                len(mac_matches) != 1
                or len({str(item.get("ComponentID")) for item in mac_matches}) != 1
            ):
                node_errors.append("admin MAC is not uniquely owned")
            if (
                len(ip_matches) != 1
                or len({str(item.get("ComponentID")) for item in ip_matches}) != 1
            ):
                node_errors.append("admin IP is not uniquely owned")
            if xname and xname not in members:
                node_errors.append("XNAME is missing from the functional group")
            nodes.append(
                {
                    "row": row,
                    "xname": xname,
                    "interface": interface,
                    "errors": node_errors,
                }
            )
            errors.extend(f"{row['HOSTNAME']}: {error}" for error in node_errors)
        missing = sorted(expected_xnames - members)
        unexpected = sorted(members - expected_xnames)
        if missing:
            errors.append("missing members=" + ",".join(missing))
        if unexpected:
            errors.append("unexpected members=" + ",".join(unexpected))
        results.append(
            {
                "name": functional_group,
                "rows": rows,
                "nodes": nodes,
                "members": members,
                "errors": errors,
            }
        )
        all_errors.extend(f"{functional_group}: {error}" for error in errors)
    return {
        "groups": results,
        "interfaces": interfaces,
        "smd_groups": groups,
        "node_components": component_ids,
        "errors": all_errors,
    }


def group_header(fields: list[tuple[str, object]], name: str) -> None:
    """Append a consistent role-oriented functional-group heading."""
    fields.append(("Functional group", f"[{name}]"))


def node_field(
    node: dict[str, Any],
    status: str,
    detail: str,
) -> tuple[str, str]:
    """Return one safe, structured hostname result field."""
    return (f"  {node['row']['HOSTNAME']}", f"{status} {detail}")
