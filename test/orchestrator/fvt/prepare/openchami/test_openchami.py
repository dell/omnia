# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""OpenCHAMI postconditions produced by Orchestrator prepare."""

import pytest
from library.functions import TestLogger
from library.functions.openchami_prepare_func import (
    check_prepare_openchami_apis,
    check_prepare_openchami_artifacts,
    check_prepare_openchami_containers,
    check_prepare_openchami_services,
    check_prepare_openchami_storage,
)
from library.functions.postgres_prepare_func import (
    check_prepare_postgresql_readiness,
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
    """Record one structured prepare result and enforce its postcondition."""
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


@pytest.mark.order(1)
def test_openchami_containers_running(host):
    """Verify all long-running OpenCHAMI containers."""
    tc = TC["openchami_containers"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "OpenCHAMI containers",
        check_prepare_openchami_containers(host),
    )


@pytest.mark.order(2)
def test_openchami_services_ready(host):
    """Verify OpenCHAMI units and successful SMD initialization."""
    tc = TC["openchami_services"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "OpenCHAMI services",
        check_prepare_openchami_services(host),
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.order(3)
def test_openchami_apis_ready(host):
    """Verify the authenticated SMD, Boot and Metadata APIs."""
    tc = TC["openchami_apis"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "OpenCHAMI APIs",
        check_prepare_openchami_apis(host),
    )


@pytest.mark.order(4)
def test_openchami_persistent_storage_and_tls(host):
    """Verify persistent data volumes and HAProxy certificates."""
    tc = TC["openchami_storage"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "OpenCHAMI storage and TLS",
        check_prepare_openchami_storage(host),
    )


@pytest.mark.order(5)
def test_openchami_packages_and_artifacts(host):
    """Verify installed packages and generated configuration files."""
    tc = TC["openchami_artifacts"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "OpenCHAMI artifacts",
        check_prepare_openchami_artifacts(host),
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.order(13)
def test_postgresql_readiness(host):
    """Verify PostgreSQL and its required SMD database contract."""
    tc = TC["postgresql_readiness"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "PostgreSQL readiness",
        check_prepare_postgresql_readiness(host),
    )
