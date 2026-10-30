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

"""
Telemetry -- Non-Functional iDRAC BMC Inventory Lifecycle Test.

Verifies that node deletion and node addition in bmc_group_data.csv are
reflected in the per-pod MySQL ``services`` table of the iDRAC StatefulSet.

The BMC under test comes from ``idrac_nft_bmc_ip`` in test_config.yml.

Flow (single test so the CSV is always restored in ``finally``):
  1. Baseline: MySQL must already match bmc_group_data.csv (V013 rules) and
     the configured BMC must be in the CSV and registered in MySQL.
  2. Delete node: remove the BMC row, redeploy, and require that the BMC is
     gone from every pod while all other rows are unchanged, the pod count is
     unchanged, and the report lists it under "Removed IPs List".
  3. Add node: restore the original CSV, redeploy, and require that the BMC
     is back in its assigned pod, listed as activated, and MySQL again
     matches the CSV exactly.

The BMC must not change the StatefulSet layout (MGMT BMC, or a parent that
keeps at least one other BMC). Deletion must only remove the MySQL row; it
must not change the iDRAC's own telemetry configuration.

If ``idrac_nft_bmc_ip`` is empty or unusable the test is skipped with a
warning that names the reason.

Test case:
    TEL_NFT_026: iDRAC BMC inventory delete/re-add reflected in MySQL (order 123)
"""

import warnings
from uuid import uuid4

import pytest

from omnia_auto import TestLogger, run_on_host, run_playbook

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    IDRAC_NFT_BMC_IP_KEY,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
)
from library.functions.telemetry_func import is_source_enabled
from library.functions.idrac_func import (
    check_bmc_lifecycle_candidate,
    get_bmc_group_data_path,
    get_idrac_lifecycle_state,
    get_idrac_pod_inventory,
    get_idrac_report_ips,
    get_mysql_ips_by_pod,
    get_nft_bmc_ip,
    remove_bmc_from_group_data,
    verify_mysql_data_in_pods,
    wait_for_idrac_replicas,
)

INVENTORY_DEPLOY_TIMEOUT = 1800
REPLICA_READY_TIMEOUT = 600


def _deploy(step):
    """Run the telemetry deploy and fail with the output tail on error."""
    run = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="execute",
        timeout=INVENTORY_DEPLOY_TIMEOUT,
    )
    assert run["rc"] == 0, (
        f"Telemetry deploy after {step} failed (rc={run['rc']}): "
        f"{run.get('output', '')[-2000:]}"
    )


def _mysql_ips(host):
    """Return ``{pod: [ips]}`` after asserting every MySQL query succeeded."""
    by_pod = get_mysql_ips_by_pod(host)
    failed = {pod: q["error"] for pod, q in by_pod.items() if not q["success"]}
    assert not failed, f"MySQL query failed in iDRAC pod(s): {failed}"
    return {pod: sorted(q["mysql_ips"]) for pod, q in by_pod.items()}


def _skip_with_warning(tl, reason):
    """Skip TEL_NFT_026, logging the reason and raising a pytest warning."""
    message = f"TEL_NFT_026 skipped: {reason}"
    tl.skipped(message)
    warnings.warn(message, UserWarning, stacklevel=2)
    pytest.skip(message)


def _assert_parity(host, phase):
    """Assert MySQL matches bmc_group_data.csv exactly (V013 rules)."""
    parity = verify_mysql_data_in_pods(host)
    assert parity["success"], (
        f"MySQL does not match bmc_group_data.csv {phase}: "
        + "; ".join(parity.get("errors", []))
    )


@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.source
@pytest.mark.order(123)
def test_idrac_bmc_delete_and_readd(host):  # pylint: disable=too-many-locals,too-many-statements
    """TEL_NFT_026: BMC delete/re-add in bmc_group_data.csv is reflected in MySQL."""
    tc = TC["nft_idrac_bmc_inventory"]
    tl = TestLogger(tc["title"], tc["id"])

    bmc_ip = get_nft_bmc_ip()
    if not bmc_ip:
        _skip_with_warning(
            tl,
            f"input not given - set {IDRAC_NFT_BMC_IP_KEY} in test_config.yml "
            "to a BMC IP from bmc_group_data.csv to run the iDRAC node "
            "delete/add test",
        )
    if not is_source_enabled(host, "idrac"):
        pytest.skip("iDRAC source not enabled in config")
    baseline_state = get_idrac_lifecycle_state(host)
    if not baseline_state["success"]:
        pytest.skip(f"iDRAC StatefulSet not available: {baseline_state['error']}")
    replicas = baseline_state["statefulset"]["replicas"]

    tl.check("Verifying baseline MySQL matches bmc_group_data.csv")
    baseline_parity = verify_mysql_data_in_pods(host)
    if not baseline_parity["success"]:
        pytest.skip(
            "Baseline MySQL does not match bmc_group_data.csv (see "
            "TEL_FVT_DEPLOY_V013): " + "; ".join(baseline_parity["errors"])
        )
    before = _mysql_ips(host)
    tl.check(f"Validating {IDRAC_NFT_BMC_IP_KEY}={bmc_ip}")
    pod_name, reason = check_bmc_lifecycle_candidate(
        get_idrac_pod_inventory(host), before, bmc_ip,
    )
    if reason:
        _skip_with_warning(tl, f"{IDRAC_NFT_BMC_IP_KEY} cannot be used: {reason}")

    csv_path = get_bmc_group_data_path(host)
    backup_path = f"{csv_path}.bmc-lifecycle-{uuid4().hex}.bak"
    backup = run_on_host(  # pylint: disable=too-many-function-args
        host, "cp --preserve=all -- %s %s", csv_path, backup_path,
    )
    assert backup.rc == 0, f"Unable to back up {csv_path}: {backup.stderr}"

    completed = False
    csv_restored = False
    try:
        tl.check(f"Delete node: removing BMC {bmc_ip} ({pod_name}) from bmc_group_data.csv")
        removal = remove_bmc_from_group_data(host, csv_path, bmc_ip)
        assert removal["success"], f"Unable to edit {csv_path}: {removal['error']}"
        _deploy("BMC deletion")

        ready = wait_for_idrac_replicas(host, replicas, timeout=REPLICA_READY_TIMEOUT)
        assert ready["success"], (
            f"Pod count changed after deleting {bmc_ip}: {ready['error']}"
        )
        after_delete = _mysql_ips(host)
        still_present = [pod for pod, ips in after_delete.items() if bmc_ip in ips]
        assert not still_present, (
            f"Deleted BMC {bmc_ip} is still in MySQL of {still_present}"
        )
        expected_after_delete = {
            pod: sorted(set(ips) - {bmc_ip}) for pod, ips in before.items()
        }
        assert after_delete == expected_after_delete, (
            "MySQL rows of other BMCs changed after deletion: "
            f"expected {expected_after_delete}, got {after_delete}"
        )
        assert bmc_ip in get_idrac_report_ips(host)["removed"], (
            f"{bmc_ip} not listed under 'Removed IPs List' in idrac_telemetry_report.yml"
        )
        _assert_parity(host, "after deletion")

        tl.check(f"Add node: re-adding BMC {bmc_ip} by restoring bmc_group_data.csv")
        restore = run_on_host(  # pylint: disable=too-many-function-args
            host, "cp --preserve=all -- %s %s", backup_path, csv_path,
        )
        assert restore.rc == 0, f"Unable to restore {csv_path}: {restore.stderr}"
        csv_restored = True
        _deploy("BMC re-addition")

        ready = wait_for_idrac_replicas(host, replicas, timeout=REPLICA_READY_TIMEOUT)
        assert ready["success"], ready["error"]
        after_add = _mysql_ips(host)
        assert bmc_ip in after_add.get(pod_name, []), (
            f"Re-added BMC {bmc_ip} is not in MySQL of {pod_name}: {after_add}"
        )
        assert after_add == before, (
            f"MySQL after re-add differs from baseline: expected {before}, got {after_add}"
        )
        assert bmc_ip in get_idrac_report_ips(host)["activated"], (
            f"{bmc_ip} not listed as activated in idrac_telemetry_report.yml"
        )
        _assert_parity(host, "after re-addition")
        completed = True
    finally:
        restore_rc = 0
        deploy_rc = 0
        if not csv_restored:
            restore_rc = run_on_host(  # pylint: disable=too-many-function-args
                host, "cp --preserve=all -- %s %s", backup_path, csv_path,
            ).rc
            if restore_rc == 0:
                deploy_rc = run_playbook(
                    playbook=PLAYBOOK_ENTRY_POINT,
                    playbook_workdir=PLAYBOOK_WORKDIR,
                    tag="execute",
                    timeout=INVENTORY_DEPLOY_TIMEOUT,
                )["rc"]
        # Keep the backup for manual recovery when the copy itself failed.
        if restore_rc == 0:
            run_on_host(host, "rm -f -- %s", backup_path)  # pylint: disable=too-many-function-args
        if restore_rc != 0 or deploy_rc != 0:
            pytest.fail(
                "Failed to restore bmc_group_data.csv/telemetry state: "
                f"copy_rc={restore_rc}, deploy_rc={deploy_rc}, backup={backup_path}"
            )

    assert completed, "iDRAC BMC inventory lifecycle did not complete"
    tl.passed(
        f"BMC {bmc_ip} deletion and re-addition reflected in MySQL of {pod_name}",
        f"CSV: {csv_path}\nBaseline MySQL: {before}\n"
        f"After delete: {after_delete}\nAfter re-add: {after_add}",
    )
