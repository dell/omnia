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

"""Negative input-validation tests for storage_config.yml mount entries.

Verifies that the mount entries in storage_config.yml satisfy the schema
contracts enforced by the mount_config role.  Each test validates one
mandatory-field or consistency rule and fails when the rule is violated.
"""

import pytest
from library.functions import (
    check_precheck_mount_invalid_mount_params,
    check_precheck_mount_missing_mount_point,
    check_precheck_mount_missing_source,
    check_precheck_mount_missing_targeting,
    check_precheck_mount_node_key_without_mount_point,
)

from fvt.result import verify_precheck

pytestmark = [pytest.mark.sanity, pytest.mark.negative, pytest.mark.mount_config]


@pytest.mark.order(30)
def test_mount_missing_mount_point(host):
    """TC-CI-NEG-001: Every mount entry must have a valid absolute mount_point."""
    verify_precheck(
        host,
        "precheck_mount_missing_mount_point",
        check_precheck_mount_missing_mount_point,
    )


@pytest.mark.order(31)
def test_mount_missing_targeting(host):
    """TC-CI-NEG-002: Every mount entry must have targeting (prefix or groups)."""
    verify_precheck(
        host,
        "precheck_mount_missing_targeting",
        check_precheck_mount_missing_targeting,
    )


@pytest.mark.order(32)
def test_mount_invalid_mount_params(host):
    """TC-CI-NEG-003: mount_params must reference an existing profile."""
    verify_precheck(
        host,
        "precheck_mount_invalid_mount_params",
        check_precheck_mount_invalid_mount_params,
    )


@pytest.mark.order(33)
def test_mount_missing_source(host):
    """TC-CI-NEG-004: Every mount entry must have a non-empty source."""
    verify_precheck(
        host,
        "precheck_mount_missing_source",
        check_precheck_mount_missing_source,
    )


@pytest.mark.order(34)
def test_mount_node_key_without_mount_point(host):
    """TC-CI-NEG-005: node_mount_point is mandatory when node_key is set."""
    verify_precheck(
        host,
        "precheck_mount_node_key_without_mount_point",
        check_precheck_mount_node_key_without_mount_point,
    )
