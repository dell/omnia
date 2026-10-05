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
    check_cleanup_idempotency,
    check_precheck_idempotency,
    check_prepare_idempotency,
)

from nft.result import verify_nft

pytestmark = [pytest.mark.nft, pytest.mark.idempotency]


@pytest.mark.destructive
@pytest.mark.order(30)
def test_prepare_idempotency(host):
    """Require repeated prepare to preserve runtime identity and readiness."""
    verify_nft(host, "prepare_idempotency", check_prepare_idempotency)


@pytest.mark.order(50)
def test_precheck_idempotency(host):
    """Require repeated precheck to remain read-only."""
    verify_nft(host, "precheck_idempotency", check_precheck_idempotency)


@pytest.mark.destructive
@pytest.mark.order(91)
def test_cleanup_idempotency(host):
    """Require repeated full cleanup to remain successful and unchanged."""
    verify_nft(host, "cleanup_idempotency", check_cleanup_idempotency)
