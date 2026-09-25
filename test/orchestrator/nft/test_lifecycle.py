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
    check_clean_baseline,
    check_lifecycle_fresh_install,
)

from nft.result import verify_nft

pytestmark = [pytest.mark.nft, pytest.mark.lifecycle]


@pytest.mark.destructive
@pytest.mark.order(100)
def test_clean_baseline(host):
    """Require a provably clean OIM state before the fresh-install lifecycle."""
    verify_nft(host, "clean_baseline", check_clean_baseline)


@pytest.mark.destructive
@pytest.mark.order(101)
def test_lifecycle_fresh_install(host):
    """Require the complete fresh-install lifecycle to succeed from clean baseline."""
    verify_nft(host, "lifecycle_fresh_install", check_lifecycle_fresh_install)
