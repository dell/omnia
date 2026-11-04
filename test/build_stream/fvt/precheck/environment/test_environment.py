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
Precheck Environment — omnia.env and OIM identity.

Mirrors the environment part of build_stream.yml --tags precheck:
omnia.env variables, hostname/domain, admin IPv4 and the data path export.
"""

import pytest

from library.functions import (
    TestLogger,
    check_precheck_admin_ipv4,
    check_precheck_data_path_export,
    check_precheck_environment,
    check_precheck_oim_identity,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(20101)
def test_precheck_environment_variables(host):
    """Verify omnia.env sets every variable the precheck reads."""
    tc = TC["precheck_environment_variables"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_environment(host)
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="omnia.env variables", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(20102)
def test_precheck_oim_identity(host):
    """Verify the OIM short hostname and domain match omnia.env."""
    tc = TC["precheck_oim_identity"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_oim_identity(host)
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="OIM identity", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(20103)
def test_precheck_admin_ipv4(host):
    """Verify the administrative IPv4 is assigned on the OIM."""
    tc = TC["precheck_admin_ipv4"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_admin_ipv4(host)
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="admin IPv4", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(20104)
def test_precheck_data_path_export(host):
    """Verify no no_root_squash NFS export covers the Omnia data path."""
    tc = TC["precheck_data_path_export"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_data_path_export(host)
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="data path export", error=result["error"],
    )
