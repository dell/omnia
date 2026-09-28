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
from library.functions import check_lifecycle_performance

from nft.result import verify_nft

pytestmark = [pytest.mark.nft, pytest.mark.performance]


@pytest.mark.order(10)
def test_precheck_performance(host):
    """Require precheck to complete within its configured threshold."""
    verify_nft(host, "precheck_performance", check_lifecycle_performance, "precheck")


@pytest.mark.destructive
@pytest.mark.order(20)
def test_prepare_performance(host):
    """Require prepare to complete within its configured threshold."""
    verify_nft(host, "prepare_performance", check_lifecycle_performance, "prepare")


@pytest.mark.destructive
@pytest.mark.order(40)
def test_provision_performance(host):
    """Require provision to complete within its configured threshold."""
    verify_nft(host, "provision_performance", check_lifecycle_performance, "provision")


@pytest.mark.destructive
@pytest.mark.order(90)
def test_cleanup_performance(host):
    """Require full cleanup to complete within its configured threshold."""
    verify_nft(host, "cleanup_performance", check_lifecycle_performance, "cleanup")
