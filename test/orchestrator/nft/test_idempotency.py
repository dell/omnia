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

"""Orchestrator repeat-execution contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_cleanup_idempotency,
    check_precheck_idempotency,
    check_prepare_idempotency,
)
from library.vars import TEST_CASES as TC

from nft.result import verify_nft


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.destructive
@pytest.mark.order(60003)
def test_prepare_idempotency(host):
    """Require repeated prepare to preserve runtime identity and readiness."""
    tc = TC["prepare_idempotency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_prepare_idempotency)


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(60005)
def test_precheck_idempotency(host):
    """Require repeated precheck to remain read-only."""
    tc = TC["precheck_idempotency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_precheck_idempotency)


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.destructive
@pytest.mark.order(60011)
def test_cleanup_idempotency(host):
    """Require repeated full cleanup to remain successful and unchanged."""
    tc = TC["cleanup_idempotency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_cleanup_idempotency)
