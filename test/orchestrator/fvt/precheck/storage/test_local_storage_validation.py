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

"""Precheck validation tests for local_storage declaration contracts.

Covers ER-ORCH-011 TC-FVT-001 to TC-FVT-005 and TC-FVT-029.
"""

import pytest
from library.functions import (
    TestLogger,
    check_precheck_kafka_switch_validation,
    check_precheck_local_storage_declarations,
    check_precheck_local_storage_etcd_nfs_fallback,
    check_precheck_local_storage_semantic_rules,
    check_precheck_local_storage_targeting,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_precheck


@pytest.mark.negative
@pytest.mark.local_storage
@pytest.mark.order(10401)
def test_local_storage_declarations(host):
    """TC-FVT-001: Every local_storage entry must have required fields and valid enums."""
    tc = TC["precheck_local_storage_declarations"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_local_storage_declarations)


@pytest.mark.negative
@pytest.mark.local_storage
@pytest.mark.order(10402)
def test_local_storage_service_group_targeting(host):
    """TC-FVT-002: Every local_storage entry must target only service Kubernetes groups."""
    tc = TC["precheck_local_storage_targeting"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_local_storage_targeting)


@pytest.mark.negative
@pytest.mark.local_storage
@pytest.mark.order(10403)
def test_local_storage_semantic_rules(host):
    """TC-FVT-003: Semantic rules — Kafka on workers only; etcd must not use nofail."""
    tc = TC["precheck_local_storage_semantic_rules"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_local_storage_semantic_rules)


@pytest.mark.local_storage
@pytest.mark.order(10404)
def test_local_storage_etcd_nfs_fallback(host):
    """TC-FVT-004: etcd uses NFS when no etcd disk entry is declared."""
    tc = TC["precheck_local_storage_etcd_nfs_fallback"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_local_storage_etcd_nfs_fallback)


@pytest.mark.local_storage
@pytest.mark.order(10405)
def test_kafka_on_local_disk_switch_validation(host):
    """TC-FVT-005/TC-FVT-029: kafka_on_local_disk defaults to false and rejects non-Boolean."""
    tc = TC["precheck_kafka_switch_validation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_kafka_switch_validation)
