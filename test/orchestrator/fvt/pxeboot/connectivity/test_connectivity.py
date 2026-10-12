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
    check_node_architecture,
    check_node_hostname_ssh,
    check_node_os_version,
    check_node_ping,
    check_node_ssh,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.connectivity
@pytest.mark.order(40101)
def test_node_ping(host):
    """Verify ping from the OIM to every mapped administrative IP."""
    tc = TC["node_ping"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_node_ping)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.connectivity
@pytest.mark.order(40102)
def test_node_ssh(host):
    """Verify passwordless root SSH from the OIM to every mapped node."""
    tc = TC["node_ssh"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_node_ssh)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.connectivity
@pytest.mark.order(40103)
def test_node_hostname_ssh(host):
    """Verify mapped hostnames resolve and support passwordless root SSH."""
    tc = TC["node_hostname_ssh"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_node_hostname_ssh)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.connectivity
@pytest.mark.order(40104)
def test_node_architecture(host):
    """Verify each node's live architecture matches its functional group."""
    tc = TC["node_architecture"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_node_architecture)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.connectivity
@pytest.mark.order(40105)
def test_node_os_version(host):
    """Verify each node's live OS version matches its functional group."""
    tc = TC["node_os_version"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_node_os_version)
