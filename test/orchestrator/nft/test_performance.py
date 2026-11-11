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

"""Orchestrator lifecycle-duration contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_lifecycle_performance,
)
from library.vars import TEST_CASES as TC

from nft.result import verify_nft


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(60001)
def test_precheck_performance(host):
    """Require precheck to complete within its configured threshold."""
    tc = TC["precheck_performance"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_lifecycle_performance, "precheck")


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.destructive
@pytest.mark.order(60002)
def test_prepare_performance(host):
    """Require prepare to complete within its configured threshold."""
    tc = TC["prepare_performance"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_lifecycle_performance, "prepare")


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.destructive
@pytest.mark.order(60004)
def test_provision_performance(host):
    """Require provision to complete within its configured threshold."""
    tc = TC["provision_performance"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_lifecycle_performance, "provision")


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.destructive
@pytest.mark.order(60010)
def test_cleanup_performance(host):
    """Require full cleanup to complete within its configured threshold."""
    tc = TC["cleanup_performance"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_lifecycle_performance, "cleanup")
