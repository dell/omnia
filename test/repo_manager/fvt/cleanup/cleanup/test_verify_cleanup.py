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
Repo Manager Cleanup — Comprehensive Verification.

Validates that --tags cleanup removed all Pulp artifacts:
  Pulp container removed
  Managed Pulp CLI preserved
  Pulp directories removed
"""

import pytest

from library.functions import (
    TestLogger,
    check_pulp_container_removed,
    check_pulp_cli_preserved,
    check_pulp_directories_removed,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)

pytestmark = pytest.mark.destructive


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(101)
def test_pulp_container_removed(host):
    """Verify Pulp container removed after cleanup."""
    tc = TC["pulp_container_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_container_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_container_removed"], result["details"])
    else:
        tl.failed(LOG["pulp_container_still_exists"], result["details"])

    assert result["success"], ASSERT["pulp_container_still_exists"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(102)
def test_pulp_cli_preserved(host):
    """Verify the managed Pulp CLI remains executable."""
    tc = TC["pulp_cli_preserved"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_cli_preserved(host)

    if result["success"]:
        tl.passed(LOG["pulp_cli_preserved"], result["details"])
    else:
        tl.failed(LOG["pulp_cli_missing"], result["details"])

    assert result["success"], ASSERT["pulp_cli_missing"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(103)
def test_pulp_directories_removed(host):
    """Verify Pulp directories removed after cleanup."""
    tc = TC["pulp_directories_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_directories_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_dirs_removed"], result["details"])
    else:
        tl.failed(LOG["pulp_dirs_still_exist"], result["details"])

    assert result["success"], ASSERT["pulp_dirs_still_exist"]
