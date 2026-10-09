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

"""Orchestrator clean-baseline and fresh-install lifecycle contracts.

Addresses OMN-DEF #850: proves that the complete fresh-install lifecycle
succeeds from a verified clean OIM state.  The baseline test runs cleanup
and asserts every cleanup postcondition, then the fresh-install test runs
precheck -> prepare -> provision in sequence and verifies all prepare and
provision postconditions are bound to that run.
"""

import pytest
from library.functions import (
    TestLogger,
    check_clean_baseline,
    check_lifecycle_fresh_install,
    check_lifecycle_provision_verify,
)
from library.vars import TEST_CASES as TC

from nft.result import verify_nft


@pytest.mark.nft
@pytest.mark.lifecycle
@pytest.mark.destructive
@pytest.mark.order(60012)
def test_clean_baseline(host):
    """Require a provably clean OIM state before the fresh-install lifecycle."""
    tc = TC["clean_baseline"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_clean_baseline)


@pytest.mark.nft
@pytest.mark.lifecycle
@pytest.mark.destructive
@pytest.mark.order(60013)
def test_lifecycle_fresh_install(host):
    """Require the complete fresh-install lifecycle to succeed from clean baseline."""
    tc = TC["lifecycle_fresh_install"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_lifecycle_fresh_install)


@pytest.mark.nft
@pytest.mark.lifecycle
@pytest.mark.order(60014)
def test_lifecycle_provision_verify(host):
    """Verify provision state and node connectivity after the fresh-install lifecycle."""
    tc = TC["lifecycle_provision_verify"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_nft(test_log, tc, host, check_lifecycle_provision_verify)
