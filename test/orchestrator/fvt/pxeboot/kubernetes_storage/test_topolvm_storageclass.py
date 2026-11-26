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

"""TopoLVM and Kafka StorageClass post-boot verification tests.

Covers ER-ORCH-011 Story 4 (ER-ORCH-011-topolvm-kafka-storageclass):
  - TC-FVT-012: TopoLVM installed only when a Kafka disk is declared
    (FR-3.1, AC-001, AC-007)
  - TC-FVT-013: Kafka StorageClass properties; default StorageClass unchanged
    (FR-3.2, AC-001, AC-002)
  - Story phase test: a claim on the Kafka StorageClass binds on the dedicated disk

Orders sit in the kubernetes_storage block (41000) after the NFS and PowerScale
cases. The temporary-claim case needs the functional marker, like its siblings.
"""

import pytest
from library.functions import (
    TestLogger,
    check_default_storageclass_unchanged,
    check_kafka_storageclass_properties,
    check_topolvm_capacity_per_node,
    check_topolvm_installed_when_kafka_declared,
    check_topolvm_kafka_dynamic_provisioning,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.local_storage
@pytest.mark.topolvm
@pytest.mark.kubernetes
@pytest.mark.order(41006)
def test_topolvm_installed_when_kafka_declared(host):
    """TC-FVT-012: TopoLVM is present only when purpose: kafka is declared (AC-001, AC-007)."""
    tc = TC["topolvm_installed_when_kafka_declared"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_topolvm_installed_when_kafka_declared)


@pytest.mark.local_storage
@pytest.mark.topolvm
@pytest.mark.kubernetes
@pytest.mark.order(41007)
def test_topolvm_capacity_per_node(host):
    """TC-FVT-012: TopoLVM reports declared-VG capacity on every Kafka-labelled node (AC-001)."""
    tc = TC["topolvm_capacity_per_node"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_topolvm_capacity_per_node)


@pytest.mark.local_storage
@pytest.mark.topolvm
@pytest.mark.kubernetes
@pytest.mark.order(41008)
def test_kafka_storageclass_properties(host):
    """TC-FVT-013: Kafka StorageClass has all FR-3.2 properties (AC-001)."""
    tc = TC["kafka_storageclass_properties"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kafka_storageclass_properties)


@pytest.mark.local_storage
@pytest.mark.topolvm
@pytest.mark.kubernetes
@pytest.mark.order(41009)
def test_default_storageclass_unchanged(host):
    """TC-FVT-013: Default StorageClass is unchanged after TopoLVM install (FR-3.2, AC-002)."""
    tc = TC["default_storageclass_unchanged"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_default_storageclass_unchanged)


@pytest.mark.functional
@pytest.mark.local_storage
@pytest.mark.topolvm
@pytest.mark.kubernetes
@pytest.mark.order(41010)
def test_topolvm_kafka_dynamic_provisioning(host):
    """Story 4 phase test: a Kafka StorageClass claim binds, is used and is removed (AC-001)."""
    tc = TC["topolvm_kafka_dynamic_provisioning"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_topolvm_kafka_dynamic_provisioning)
