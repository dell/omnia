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
"""Select PXE targets and maintain a project-scoped boot-result ledger."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: plan_pxe_targets
short_description: Select nodes that require PXE boot
version_added: "2.3.0"
description:
  - Selects new, changed, failed, pending, or unverified nodes for PXE boot.
  - Preserves successful nodes only when their complete PXE identity is unchanged.
  - Treats an explicit custom inventory as an exact operator-selected target set.
  - Produces a state ledger but performs no file or service mutations.
options:
  desired_nodes:
    description: Complete authoritative PXE mapping rows for the project.
    required: true
    type: list
    elements: dict
  requested_nodes:
    description: Rows requested for this run before automatic selection.
    required: true
    type: list
    elements: dict
  custom_selection:
    description: Whether requested_nodes came from an explicit inventory.
    required: true
    type: bool
  previous_state:
    description: Previous internal PXE state document.
    required: false
    type: raw
    default: {}
  previous_status:
    description: Previous public PXE status used to seed state on upgrade.
    required: false
    type: raw
    default: {}
  run_results:
    description:
      - Current per-node PXE results to merge into the state ledger.
      - When identity_signature is supplied, it must match the current row.
    required: false
    type: list
    elements: dict
    default: []
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Select PXE targets
  plan_pxe_targets:
    desired_nodes: "{{ canonical_pxe_rows }}"
    requested_nodes: "{{ requested_pxe_rows }}"
    custom_selection: false
    previous_state: "{{ previous_pxe_state }}"
    previous_status: "{{ previous_pxe_status }}"
  register: pxe_target_plan
"""

RETURN = r"""
errors:
  description: Conditions that make safe target selection impossible.
  type: list
  elements: str
  returned: always
target_nodes:
  description: Authoritative mapping rows selected for this PXE run.
  type: list
  elements: dict
  returned: always
skipped_nodes:
  description: Successful unchanged nodes omitted from this PXE run.
  type: list
  elements: dict
  returned: always
selection:
  description: Per-node selection decisions and reasons.
  type: list
  elements: dict
  returned: always
state:
  description: Updated internal PXE state document.
  type: dict
  returned: always
"""


IDENTITY_FIELDS = (
    "FUNCTIONAL_GROUP_NAME",
    "GROUP_NAME",
    "SERVICE_TAG",
    "PARENT_SERVICE_TAG",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
    "BMC_MAC",
    "BMC_IP",
    "IB_NIC_NAME",
    "IB_IP",
    "XNAME",
)
SUCCESS_STATUS = "success"
PRIMARY_CONTROL_PLANE_PREFIX = "service_kube_control_plane_first_"
CONTROL_PLANE_PREFIX = "service_kube_control_plane_"


def _text(value: Any) -> str:
    """Return a stable stripped string representation."""
    return str(value or "").strip()


def _mac(value: Any) -> str:
    """Return a normalized MAC address for identity comparison."""
    compact = _text(value).lower().replace("-", ":")
    if ":" not in compact and len(compact) == 12:
        compact = ":".join(
            compact[index:index + 2] for index in range(0, 12, 2)
        )
    return compact


def _identity(
    row: dict[str, Any],
    position: int | None = None,
) -> dict[str, str]:
    """Extract the complete PXE identity that determines boot eligibility."""
    identity = {field: _text(row.get(field)) for field in IDENTITY_FIELDS}
    identity["ADMIN_MAC"] = _mac(identity["ADMIN_MAC"])
    identity["BMC_MAC"] = _mac(identity["BMC_MAC"])
    if identity["FUNCTIONAL_GROUP_NAME"].startswith(
        PRIMARY_CONTROL_PLANE_PREFIX
    ):
        identity["FUNCTIONAL_GROUP_NAME"] = identity[
            "FUNCTIONAL_GROUP_NAME"
        ].replace(
            PRIMARY_CONTROL_PLANE_PREFIX,
            CONTROL_PLANE_PREFIX,
            1,
        )
    if not identity["XNAME"] and position is not None:
        identity["XNAME"] = (
            f"x1000c{position // 100}s{(position // 10) % 10}"
            f"b{position % 10}n0"
        )
    return identity


def _signature(identity: dict[str, str]) -> str:
    """Hash one normalized identity deterministically."""
    serialized = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _key(row: dict[str, Any]) -> str:
    """Use the BMC address as the project mapping's validated unique key."""
    return _text(row.get("BMC_IP"))


def _records(document: Any, field: str, source: str) -> tuple[list, str]:
    """Read an optional record list from a state/status document."""
    if document in (None, ""):
        return [], ""
    if not isinstance(document, dict):
        return [], f"{source} must be a mapping"
    records = document.get(field, [])
    if records is None:
        records = []
    if not isinstance(records, list):
        return [], f"{source}.{field} must be a list"
    if any(not isinstance(record, dict) for record in records):
        return [], f"{source}.{field} contains a non-object record"
    return records, ""


def _index_records(
    records: list[dict[str, Any]],
    source: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    """Index records by unique BMC address and report ambiguous state."""
    indexed: dict[str, dict[str, Any]] = {}
    for position, record in enumerate(records, start=1):
        key = _text(record.get("bmc_ip") or record.get("BMC_IP"))
        if not key:
            errors.append(f"{source} record {position} has no BMC IP")
            continue
        if key in indexed:
            errors.append(f"{source} contains duplicate BMC IP {key}")
            continue
        indexed[key] = record
    return indexed


def _legacy_matches(
    current_identity: dict[str, str],
    legacy: dict[str, Any],
) -> bool:
    """Require every legacy identity field and match it exactly."""
    legacy_fields = {
        "BMC_IP": "bmc_ip",
        "ADMIN_IP": "admin_ip",
        "HOSTNAME": "hostname",
        "SERVICE_TAG": "service_tag",
        "XNAME": "xname",
    }
    if any(field not in legacy for field in legacy_fields.values()):
        return False
    return all(
        current_identity[identity_field] == _text(legacy[legacy_field])
        for identity_field, legacy_field in legacy_fields.items()
    )


def _prior_status(
    identity: dict[str, str],
    state_record: dict[str, Any] | None,
    legacy_record: dict[str, Any] | None,
) -> tuple[str, str]:
    """Resolve prior status only when it belongs to the unchanged identity."""
    signature = _signature(identity)
    if state_record:
        if _text(state_record.get("signature")) == signature:
            return _text(state_record.get("status")).lower(), "state"
        return "", "changed"
    if legacy_record and _legacy_matches(identity, legacy_record):
        return _text(legacy_record.get("status")).lower(), "legacy_status"
    return "", "new"


def _state_record(
    identity: dict[str, str],
    status: str,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one deterministic state record without carrying stale fields."""
    record: dict[str, Any] = {
        "bmc_ip": identity["BMC_IP"],
        "admin_ip": identity["ADMIN_IP"],
        "xname": identity["XNAME"],
        "hostname": identity["HOSTNAME"],
        "service_tag": identity["SERVICE_TAG"],
        "signature": _signature(identity),
        "status": status or "pending",
        "identity": identity,
    }
    if result:
        record["failure_stage"] = _text(result.get("failure_stage"))
        record["verification_state"] = _text(
            result.get("verification_state")
        )
        record["detail"] = _text(result.get("detail"))
    return record


def plan_pxe_targets(
    desired_nodes: list[dict[str, Any]],
    requested_nodes: list[dict[str, Any]],
    custom_selection: bool,
    previous_state: Any,
    previous_status: Any,
    run_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a safe target plan and updated PXE state document."""
    errors: list[str] = []
    if previous_state and (
        not isinstance(previous_state, dict)
        or _text(previous_state.get("schema_version")) != "1.0"
        or "nodes" not in previous_state
    ):
        errors.append(
            "previous PXE state must use schema_version 1.0 and contain nodes"
        )
    state_records, state_error = _records(
        previous_state, "nodes", "previous PXE state"
    )
    if previous_state:
        # The public report is only an upgrade seed. Once the internal ledger
        # exists, it is the sole authority and stale public output is ignored.
        legacy_records = []
        legacy_error = ""
    else:
        legacy_records, legacy_error = _records(
            previous_status, "nodes", "previous PXE status"
        )
    if not previous_state and previous_status and (
        not isinstance(previous_status, dict)
        or _text(previous_status.get("schema_version")) != "1.0"
        or _text(previous_status.get("phase")) != "pxeboot"
    ):
        legacy_records = []
    errors.extend(error for error in (state_error, legacy_error) if error)

    desired_by_key: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(desired_nodes, start=1):
        key = _key(row)
        if not key:
            errors.append(f"Desired PXE row {position} has no BMC_IP")
            continue
        if key in desired_by_key:
            errors.append(f"Desired PXE mapping contains duplicate BMC_IP {key}")
            continue
        desired_by_key[key] = row

    requested_keys = []
    for position, row in enumerate(requested_nodes, start=1):
        key = _key(row)
        if not key:
            errors.append(f"Requested PXE row {position} has no BMC_IP")
            continue
        if key not in desired_by_key:
            errors.append(
                f"Requested PXE BMC_IP {key} is not in the authoritative mapping"
            )
            continue
        if key in requested_keys:
            errors.append(f"Requested PXE rows contain duplicate BMC_IP {key}")
            continue
        requested_keys.append(key)

    state_by_key = _index_records(state_records, "previous PXE state", errors)
    legacy_by_key = _index_records(
        legacy_records, "previous PXE status", errors
    )
    results_by_key = _index_records(run_results, "current PXE results", errors)
    desired_identity_by_key = {
        key: _identity(row, position)
        for position, (key, row) in enumerate(desired_by_key.items())
    }
    for key, result in results_by_key.items():
        if key not in desired_identity_by_key:
            errors.append(
                f"Current PXE result BMC_IP {key} is not in the desired mapping"
            )
            continue
        result_signature = _text(result.get("identity_signature"))
        if result_signature and result_signature != _signature(
            desired_identity_by_key[key]
        ):
            errors.append(
                f"Current PXE result identity does not match BMC_IP {key}"
            )
    if errors:
        return {
            "errors": errors,
            "target_nodes": [],
            "skipped_nodes": [],
            "selection": [],
            "state": {"schema_version": "1.0", "nodes": []},
        }

    target_keys: list[str] = []
    skipped_nodes = []
    selection = []
    next_state = []
    explicitly_requested = set(requested_keys)

    for key, row in desired_by_key.items():
        identity = desired_identity_by_key[key]
        prior_status, source = _prior_status(
            identity,
            state_by_key.get(key),
            legacy_by_key.get(key),
        )
        if custom_selection:
            selected = key in explicitly_requested
            reason = "explicit_inventory" if selected else "not_requested"
        else:
            selected = prior_status != SUCCESS_STATUS
            if not prior_status:
                reason = source
            elif prior_status == "failed":
                reason = "previous_failure"
            elif prior_status == "pending":
                reason = "previous_incomplete_run"
            elif prior_status == "pxe_initiated_unverified":
                reason = "previous_unverified"
            elif selected:
                reason = f"previous_{prior_status}"
            else:
                reason = "previous_success"

        result = results_by_key.get(key)
        if result:
            current_status = _text(result.get("status")).lower() or "failed"
        elif selected:
            current_status = "pending"
        else:
            current_status = prior_status or "not_requested"

        next_state.append(_state_record(identity, current_status, result))
        selection.append({
            "bmc_ip": key,
            "admin_ip": identity["ADMIN_IP"],
            "hostname": identity["HOSTNAME"],
            "selected": selected,
            "reason": reason,
            "previous_status": prior_status or "none",
        })
        if selected:
            target_keys.append(key)
        else:
            skipped_nodes.append(row)

    return {
        "errors": [],
        "target_nodes": [desired_by_key[key] for key in target_keys],
        "skipped_nodes": skipped_nodes,
        "selection": selection,
        "state": {
            "schema_version": "1.0",
            "nodes": next_state,
        },
    }


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "desired_nodes": {
                "type": "list",
                "elements": "dict",
                "required": True,
            },
            "requested_nodes": {
                "type": "list",
                "elements": "dict",
                "required": True,
            },
            "custom_selection": {"type": "bool", "required": True},
            "previous_state": {"type": "raw", "default": {}},
            "previous_status": {"type": "raw", "default": {}},
            "run_results": {
                "type": "list",
                "elements": "dict",
                "default": [],
            },
        },
        supports_check_mode=True,
    )
    result = plan_pxe_targets(
        module.params["desired_nodes"],
        module.params["requested_nodes"],
        module.params["custom_selection"],
        module.params["previous_state"],
        module.params["previous_status"],
        module.params["run_results"],
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
