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

"""Independent OIM-to-node ping and SSH postconditions."""

import pytest
from library.functions import (
    TestLogger,
    check_node_hostname_ssh,
    check_node_ping,
    check_node_ssh,
)
from library.messages import PXEBOOT_TEST_ASSERT_MSGS as ASSERT
from library.messages import PXEBOOT_TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

pytestmark = [pytest.mark.sanity, pytest.mark.connectivity]


def _check(host, key, callback):
    tc = TC[key]
    test_log = TestLogger(tc["title"], tc["id"])
    result = callback(host)
    fields = result["details"]["fields"]
    if result["success"]:
        test_log.passed_fields(
            LOG["check_passed"].format(component=tc["component"]), fields
        )
    else:
        test_log.failed_fields(
            LOG["check_failed"].format(component=tc["component"]),
            [*fields, ("Error", result["error"])],
        )
    assert result["success"], ASSERT["verification_failed"].format(
        component=tc["component"], error=result["error"]
    )


@pytest.mark.order(201)
def test_node_ping(host):
    """Verify ping from the OIM to every mapped administrative IP."""
    _check(host, "node_ping", check_node_ping)


@pytest.mark.order(202)
def test_node_ssh(host):
    """Verify passwordless root SSH from the OIM to every mapped node."""
    _check(host, "node_ssh", check_node_ssh)


@pytest.mark.order(203)
def test_node_hostname_ssh(host):
    """Verify mapped hostnames resolve and support passwordless root SSH."""
    _check(host, "node_hostname_ssh", check_node_hostname_ssh)
