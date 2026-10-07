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
    check_boot_image_architecture,
    check_boot_image_identity,
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


@pytest.mark.sanity
@pytest.mark.order(30101)
def test_provision_reports(host):
    """Verify the provision report and generated inventory contracts."""
    tc = TC["provision_reports"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_provision_reports(host))


@pytest.mark.sanity
@pytest.mark.order(30102)
def test_smd_identity(host):
    """Verify XNAME, administrative MAC, and IP identity in SMD."""
    tc = TC["smd_identity"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_smd_identity(host))


@pytest.mark.sanity
@pytest.mark.order(30103)
def test_smd_group_membership(host):
    """Verify expected groups and reject competing cloud-init groups."""
    tc = TC["smd_groups"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_smd_groups(host))


@pytest.mark.sanity
@pytest.mark.order(30104)
def test_boot_service_configurations(host):
    """Verify BootConfigurations and their mapped administrative MACs."""
    tc = TC["boot_configurations"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_boot_configurations(host))


@pytest.mark.sanity
@pytest.mark.order(30105)
def test_boot_service_node_identity(host):
    """Verify synchronized XNAME-to-bootMac records."""
    tc = TC["boot_nodes"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_boot_nodes(host))


@pytest.mark.sanity
@pytest.mark.order(30106)
def test_metadata_service_groups(host):
    """Verify one usable cloud-init template per functional group."""
    tc = TC["metadata_groups"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_metadata_groups(host))


@pytest.mark.sanity
@pytest.mark.order(30107)
def test_metadata_service_instances(host):
    """Verify unique per-node hostname metadata."""
    tc = TC["metadata_instances"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_metadata_instances(host))


@pytest.mark.sanity
@pytest.mark.order(30108)
def test_coredhcp_and_coredns_inventory(host):
    """Verify the SMD identity records consumed by CoreDHCP/CoreDNS."""
    tc = TC["network_inventory"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_network_inventory(host))


@pytest.mark.boot_image
@pytest.mark.order(30109)
def test_boot_image_identity(host):
    """Verify Boot Service kernel/initrd paths match build_status.yml."""
    tc = TC["boot_image_identity"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_boot_image_identity(host))


@pytest.mark.boot_image
@pytest.mark.order(30110)
def test_boot_image_architecture(host):
    """Verify build_status.yml architecture keys match functional group names."""
    tc = TC["boot_image_architecture"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(test_log, tc["component"], check_boot_image_architecture(host))
