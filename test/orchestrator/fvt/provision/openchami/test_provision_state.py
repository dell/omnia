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

"""OpenCHAMI desired-state postconditions produced by provision."""

import pytest
from library.functions import (
    TestLogger,
    check_boot_configurations,
    check_boot_nodes,
    check_metadata_groups,
    check_metadata_instances,
    check_network_inventory,
    check_provision_reports,
    check_smd_groups,
    check_smd_identity,
)
from library.messages import PROVISION_TEST_ASSERT_MSGS as ASSERT
from library.messages import PROVISION_TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

pytestmark = [pytest.mark.sanity]


def _assert_result(test_log, component, result):
    """Record one structured provision result and enforce its postcondition."""
    fields = result["details"]["fields"]
    if result["success"]:
        test_log.passed_fields(
            LOG["check_passed"].format(component=component),
            fields,
        )
    else:
        test_log.failed_fields(
            LOG["check_failed"].format(component=component),
            [*fields, ("Error", result["error"])],
        )
    assert result["success"], ASSERT["verification_failed"].format(
        component=component,
        error=result["error"],
    )


def _run_check(host, registry_key, check):
    """Create the registered logger and run one provision check."""
    tc = TC[registry_key]
    _assert_result(TestLogger(tc["title"], tc["id"]), tc["component"], check(host))


@pytest.mark.order(101)
def test_provision_reports(host):
    """Verify the provision report and generated inventory contracts."""
    _run_check(host, "provision_reports", check_provision_reports)


@pytest.mark.order(102)
def test_smd_identity(host):
    """Verify XNAME, administrative MAC, and IP identity in SMD."""
    _run_check(host, "smd_identity", check_smd_identity)


@pytest.mark.order(103)
def test_smd_group_membership(host):
    """Verify expected groups and reject competing cloud-init groups."""
    _run_check(host, "smd_groups", check_smd_groups)


@pytest.mark.order(104)
def test_boot_service_configurations(host):
    """Verify BootConfigurations and their mapped administrative MACs."""
    _run_check(
        host,
        "boot_configurations",
        check_boot_configurations,
    )


@pytest.mark.order(105)
def test_boot_service_node_identity(host):
    """Verify synchronized XNAME-to-bootMac records."""
    _run_check(host, "boot_nodes", check_boot_nodes)


@pytest.mark.order(106)
def test_metadata_service_groups(host):
    """Verify one usable cloud-init template per functional group."""
    _run_check(host, "metadata_groups", check_metadata_groups)


@pytest.mark.order(107)
def test_metadata_service_instances(host):
    """Verify unique per-node hostname metadata."""
    _run_check(
        host,
        "metadata_instances",
        check_metadata_instances,
    )


@pytest.mark.order(108)
def test_coredhcp_and_coredns_inventory(host):
    """Verify the SMD identity records consumed by CoreDHCP/CoreDNS."""
    _run_check(host, "network_inventory", check_network_inventory)
