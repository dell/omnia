# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Network postconditions produced by Orchestrator prepare."""

import pytest
from library.functions import TestLogger
from library.functions.network_prepare_func import (
    check_prepare_coredhcp_network,
    check_prepare_firewall_network,
)
from library.messages import (
    PREPARE_TEST_ASSERT_MSGS as ASSERT,
)
from library.messages import (
    PREPARE_TEST_LOG_MSGS as LOG,
)
from library.vars import TEST_CASES as TC

pytestmark = [pytest.mark.sanity]


def _assert_result(test_log, component, result):
    """Record a structured network result and enforce its postcondition."""
    if result["success"]:
        test_log.passed_fields(
            LOG["check_passed"].format(component=component),
            result["fields"],
        )
    else:
        test_log.failed_fields(
            LOG["check_failed"].format(component=component),
            [*result["fields"], ("Error", result["error"])],
        )
    assert result["success"], ASSERT["verification_failed"].format(
        component=component,
        error=result["error"],
    )


@pytest.mark.order(6)
def test_firewall_and_podman_network_policy(host):
    """Verify OpenCHAMI ports and trusted Podman interfaces."""
    tc = TC["firewall_network"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "Firewall and Podman network",
        check_prepare_firewall_network(host),
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.order(7)
def test_coredhcp_and_coredns_configuration(host):
    """Verify rendered DHCP/DNS configuration and additional routes."""
    tc = TC["coredhcp_network"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "CoreDHCP and CoreDNS",
        check_prepare_coredhcp_network(host),
    )
