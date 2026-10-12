# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Local OpenLDAP postconditions produced by Orchestrator prepare.

External LDAP proxy cases run in the pxeboot slurm_ldap suite.
"""

import pytest
from library.functions import TestLogger
from library.functions.openldap_prepare_func import (
    check_prepare_openldap_artifacts,
    check_prepare_openldap_endpoint,
    check_prepare_openldap_runtime,
)
from library.messages import (
    PREPARE_TEST_ASSERT_MSGS as ASSERT,
)
from library.messages import (
    PREPARE_TEST_LOG_MSGS as LOG,
)
from library.vars import TEST_CASES as TC


def _assert_result(test_log, component, result):
    """Record one structured LDAP result and enforce its postcondition."""
    if result.get("skipped"):
        test_log.skipped_fields(
            LOG["check_skipped"].format(component=component),
            result["fields"],
        )
        pytest.skip(result["details"])
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


@pytest.mark.openldap
@pytest.mark.sanity
@pytest.mark.order(20301)
def test_openldap_runtime(host):
    """Verify the enabled service and container are healthy."""
    tc = TC["openldap_runtime"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "OpenLDAP runtime",
        check_prepare_openldap_runtime(host),
    )


@pytest.mark.openldap
@pytest.mark.sanity
@pytest.mark.order(20302)
def test_openldap_artifacts(host):
    """Verify configuration modes, syntax and TLS lifetime."""
    tc = TC["openldap_artifacts"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "OpenLDAP artifacts",
        check_prepare_openldap_artifacts(host),
    )


@pytest.mark.openldap
@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.order(20303)
def test_openldap_endpoint(host):
    """Verify the local LDAP endpoint and published listeners."""
    tc = TC["openldap_endpoint"]
    test_log = TestLogger(tc["title"], tc["id"])
    _assert_result(
        test_log,
        "OpenLDAP endpoint",
        check_prepare_openldap_endpoint(host),
    )
