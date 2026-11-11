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

"""ER-ORCH-005 IPoIB IPv6 validation and rendering performance contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_ipoib_allocation_validation_latency,
    check_ipoib_artifact_generation_throughput,
)
from library.vars import TEST_CASES as TC

from nft.result import verify_nft


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.ipoib
@pytest.mark.order(60101)
def test_ipoib_allocation_validation_latency(host):
    """TC-NFT-001: allocation preflight p95 < 100 ms/record at 500 records."""
    tc = TC["ipoib_allocation_validation_latency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_ipoib_allocation_validation_latency)


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.ipoib
@pytest.mark.order(60102)
def test_ipoib_artifact_generation_throughput(host):
    """TC-NFT-002: artifact rendering p95 < 30 s/node at 500 nodes, hash-stable."""
    tc = TC["ipoib_artifact_generation_throughput"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_ipoib_artifact_generation_throughput)
