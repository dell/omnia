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

"""Unit tests for iDRAC MySQL <-> bmc_group_data.csv parity and BMC lifecycle."""

from pathlib import Path

import yaml

from library.functions import idrac_func
from library.functions.validation_func import _validate_ip
from library.vars.common_vars import IDRAC_NFT_BMC_IP_KEY


REPO_ROOT = Path(__file__).resolve().parents[3]
IDRAC_ROLE = REPO_ROOT / "src/telemetry/roles/deploy_idrac_telemetry"

POD0 = "idrac-telemetry-0"
POD1 = "idrac-telemetry-1"
POD2 = "idrac-telemetry-2"


def _mysql(**pods):
    return {
        pod.replace("_", "-"): {"success": True, "mysql_ips": ips, "error": ""}
        for pod, ips in pods.items()
    }


def test_empty_pod_with_reported_unsupported_bmc_warns():
    """A pod whose BMC is only 'reported unsupported' passes with a warning."""
    inventory = {POD0: ["100.10.1.120"], POD1: ["100.10.1.121"]}
    mysql = _mysql(idrac_telemetry_0=["100.10.1.120"], idrac_telemetry_1=[])

    result = idrac_func.evaluate_idrac_mysql_parity(
        inventory, mysql, reported_unsupported=["100.10.1.121"],
    )

    assert result["success"], result["errors"]
    pod1 = next(pr for pr in result["pod_results"] if pr["pod_name"] == POD1)
    assert pod1["missing_ips"] == ["100.10.1.121"]
    assert pod1["ok"] and pod1["expected_idle"]
    assert any("reported as not supported" in w for w in result["warnings"])


def test_missing_bmc_not_in_report_fails():
    """A CSV BMC absent from MySQL and not reported unsupported is an error."""
    inventory = {POD0: ["10.0.0.1"], POD1: ["10.0.0.2"]}
    mysql = _mysql(idrac_telemetry_0=["10.0.0.1"], idrac_telemetry_1=[])

    result = idrac_func.evaluate_idrac_mysql_parity(inventory, mysql)

    assert not result["success"]
    assert not result["warnings"]
    pod1 = next(pr for pr in result["pod_results"] if pr["pod_name"] == POD1)
    assert not pod1["ok"] and not pod1["expected_idle"]


def test_deleted_bmc_left_in_mysql_fails():
    """A BMC removed from the CSV but still in MySQL is a stale row."""
    inventory = {POD0: ["10.0.0.1"]}
    mysql = _mysql(idrac_telemetry_0=["10.0.0.1", "10.0.0.9"])

    result = idrac_func.evaluate_idrac_mysql_parity(inventory, mysql)

    assert not result["success"]
    assert result["pod_results"][0]["unexpected_ips"] == ["10.0.0.9"]


def test_bmc_registered_in_wrong_pod_fails():
    """Each BMC must be in the pod that owns its PARENT."""
    inventory = {POD0: ["10.0.0.1"], POD1: ["10.0.0.2"], POD2: ["10.0.0.3"]}
    mysql = _mysql(
        idrac_telemetry_0=["10.0.0.1"],
        idrac_telemetry_1=["10.0.0.3"],
        idrac_telemetry_2=["10.0.0.2"],
    )

    result = idrac_func.evaluate_idrac_mysql_parity(inventory, mysql)

    assert not result["success"]
    by_pod = {pr["pod_name"]: pr for pr in result["pod_results"]}
    assert by_pod[POD1]["missing_ips"] == ["10.0.0.2"]
    assert by_pod[POD1]["unexpected_ips"] == ["10.0.0.3"]


def test_nothing_registered_fails_even_when_all_reported_unsupported():
    """iDRAC telemetry with zero registered BMCs can never pass."""
    inventory = {POD0: ["10.0.0.1"]}
    mysql = _mysql(idrac_telemetry_0=[])

    result = idrac_func.evaluate_idrac_mysql_parity(inventory, mysql, ["10.0.0.1"])

    assert not result["success"]
    assert any("No BMC" in err for err in result["errors"])


def test_duplicates_query_failures_and_missing_pods_fail():
    """Duplicate rows, failed MySQL queries, and non-running pods are failures."""
    inventory = {POD0: ["10.0.0.1"], POD1: ["10.0.0.2"], POD2: ["10.0.0.3"]}
    mysql = {
        POD0: {"success": True, "mysql_ips": ["10.0.0.1", "10.0.0.1"], "error": ""},
        POD1: {"success": False, "mysql_ips": [], "error": "Access denied"},
    }

    result = idrac_func.evaluate_idrac_mysql_parity(inventory, mysql)

    by_pod = {pr["pod_name"]: pr for pr in result["pod_results"]}
    assert not result["success"]
    assert by_pod[POD0]["duplicate_ips"] == ["10.0.0.1"]
    assert not by_pod[POD1]["query_success"]
    assert by_pod[POD2]["error"] == "pod is not running"


def test_csv_parser_matches_deploy_parser():
    """Header, blank, comment and short rows are skipped like prepare_bmc_inventory.yml."""
    csv_text = (
        "BMC_IP,GROUP_NAME,PARENT\n"
        "10.0.0.1,grp0,\n"
        "\n"
        "  # 10.0.0.9,grp,SVC9\n"
        "10.0.0.5,grp\n"
        " 10.0.0.2 , grp1 , SVC1 \r\n"
    )

    entries = idrac_func.parse_bmc_group_data(csv_text)

    assert entries == [
        {"bmc_ip": "10.0.0.1", "group_name": "grp0", "parent": ""},
        {"bmc_ip": "10.0.0.2", "group_name": "grp1", "parent": "SVC1"},
    ]


def test_lifecycle_candidate_never_changes_pod_layout():
    """The configured BMC must be in the CSV, registered, and not a parent's last BMC."""
    check = idrac_func.check_bmc_lifecycle_candidate

    single_parent = {POD0: [], POD1: ["10.0.0.2"]}
    pod, reason = check(single_parent, {POD1: ["10.0.0.2"]}, "10.0.0.2")
    assert pod == POD1 and "pod layout" in reason

    multi_parent = {POD0: [], POD1: ["10.0.0.3", "10.0.0.2"]}
    assert check(multi_parent, {POD1: ["10.0.0.2", "10.0.0.3"]}, "10.0.0.2") == (POD1, "")

    mgmt = {POD0: ["10.0.0.1"], POD1: ["10.0.0.2"]}
    assert check(mgmt, {POD0: ["10.0.0.1"], POD1: ["10.0.0.2"]}, "10.0.0.1") == (POD0, "")

    pod, reason = check({POD0: ["10.0.0.1"]}, {POD0: []}, "10.0.0.1")
    assert pod == POD0 and "not registered in MySQL" in reason

    pod, reason = check({POD0: ["10.0.0.1"]}, {POD0: ["10.0.0.1"]}, "10.0.0.9")
    assert pod is None and "not present in bmc_group_data.csv" in reason


def test_node_deletion_only_removes_mysql_rows():
    """Deleting a node must not change the iDRAC's telemetry configuration."""
    tasks_text = (IDRAC_ROLE / "tasks/remove_deleted_nodes.yml").read_text(encoding="utf-8")
    tasks = yaml.safe_load(tasks_text)
    modules = set()
    for task in tasks:
        for sub in [task, *task.get("block", []), *task.get("rescue", [])]:
            modules.update(sub.keys())

    assert "disable_idrac_telemetry" not in modules
    assert "delete_idracips_from_mysqldb" in modules
    report = (IDRAC_ROLE / "templates/telemetry_report.j2").read_text(encoding="utf-8")
    assert "Redfish" not in report
    assert "Removed IPs List:" in report


def test_nft_bmc_ip_config():
    """idrac_nft_bmc_ip is optional; when set it must be an IPv4 address."""
    field = IDRAC_NFT_BMC_IP_KEY
    assert idrac_func.get_nft_bmc_ip({}) == ""
    assert idrac_func.get_nft_bmc_ip({field: None}) == ""
    assert idrac_func.get_nft_bmc_ip({field: " 10.0.0.1 "}) == "10.0.0.1"
    assert not _validate_ip("", field)
    assert not _validate_ip("10.0.0.1", field)
    assert _validate_ip("10.0.0.300x", field)
