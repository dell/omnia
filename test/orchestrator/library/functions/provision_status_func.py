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

"""Persistent provision report and generated inventory verification."""

import os
from collections import Counter
from typing import Any

from ..vars.provision_vars import ORCHESTRATOR_INVENTORY, PROVISION_REPORT
from ._prepare_helpers import read_yaml_mapping
from ._provision_helpers import (
    exception_result,
    group_header,
    load_context,
    result,
)


def check_provision_reports(host) -> dict[str, Any]:
    """Verify the provision report and generated inventory."""
    try:
        context = load_context(host)
        inventory_path = os.path.join(context["output_dir"], ORCHESTRATOR_INVENTORY)
        report = read_yaml_mapping(
            host,
            os.path.join(context["output_dir"], PROVISION_REPORT),
        )
        inventory = read_yaml_mapping(host, inventory_path)
        inventory_all = inventory.get("all")
        if not isinstance(inventory_all, dict):
            raise TypeError("orchestrator_inventory.yml all must be a mapping")
        inventory_children = inventory_all.get("children")
        if not isinstance(inventory_children, dict):
            raise TypeError("orchestrator_inventory.yml all.children must be a mapping")

        desired = Counter(
            (
                row["EXPECTED_FUNCTIONAL_GROUP"],
                row["HOSTNAME"],
                row["ADMIN_IP"],
                row["BMC_IP"],
                row["SERVICE_TAG"],
                row["GROUP_NAME"],
            )
            for row in context["rows"]
        )
        inventory_records = []
        inventory_counts = Counter()
        for group_name in context["rows_by_fg"]:
            group = inventory_children.get(group_name)
            if not isinstance(group, dict):
                continue
            hosts = group.get("hosts")
            if not isinstance(hosts, dict):
                continue
            inventory_counts[group_name] = len(hosts)
            for hostname, host_vars in hosts.items():
                if not isinstance(host_vars, dict):
                    raise TypeError(
                        f"Inventory host {hostname} variables must be a mapping"
                    )
                inventory_records.append(
                    (
                        group_name,
                        str(hostname),
                        str(host_vars.get("ansible_host") or ""),
                        str(host_vars.get("bmc_ip") or ""),
                        str(host_vars.get("service_tag") or ""),
                        str(host_vars.get("group_name") or ""),
                    )
                )
        generated = Counter(inventory_records)

        checks = {
            "Provisioning report phase": report.get("phase") == "provisioning",
            "Provisioning report status": report.get("overall_status") == "success",
            "Expected node count": int(report.get("total_expected_nodes", -1))
            == len(context["rows"]),
            "Registered node count": int(report.get("total_registered_nodes", -1))
            == len(context["rows"]),
            "Success count": int(report.get("success_count", -1))
            == len(context["rows"]),
            "Failure count": int(report.get("failure_count", -1)) == 0,
            "Expected admin interfaces": int(
                report.get("expected_admin_interfaces", -1)
            )
            == len(context["rows"]),
            "Registered admin interfaces": int(
                report.get("registered_admin_interfaces", -1)
            )
            == len(context["rows"]),
            "Generated inventory identities": generated == desired,
            "Inventory source": str(report.get("inventory_source") or "")
            == context["mapping_path"],
        }
        failures = [label for label, passed in checks.items() if not passed]
        for label in (
            "missing_nodes",
            "fg_missing_boot_config",
            "fg_missing_metadata",
            "missing_admin_interfaces",
            "nodes_missing_hostnames",
        ):
            if report.get(label):
                failures.append(label)
        fields = [
            ("Mapping", context["mapping_path"]),
            ("Generated inventory", inventory_path),
            ("Desired nodes", len(context["rows"])),
            ("Inventory nodes", len(inventory_records)),
            (
                "Registered nodes",
                report.get("total_registered_nodes", "missing"),
            ),
            ("Provision status", report.get("overall_status", "missing")),
        ]
        for name, rows in context["rows_by_fg"].items():
            group_header(fields, name)
            fields.append(("  Desired nodes", len(rows)))
            fields.append(("  Inventory nodes", inventory_counts[name]))
        return result(
            not failures,
            "Provision report and generated inventory match the desired state",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result("Provision reports could not be validated", exc)
