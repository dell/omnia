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

"""Kafka local-disk post-boot verification tests.

Covers ER-ORCH-011:
  - TC-FVT-030: Kafka node label follows disk status and disable-marker state
  - TC-FVT-032: Per-node status file exists and reports a valid result field
"""

import pytest
from library.functions import (
    TestLogger,
    check_kubernetes_kafka_disk_status,
    check_kubernetes_kafka_node_label,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.local_storage
@pytest.mark.order(10601)
def test_kafka_node_label_follows_disk_status(host):
    """TC-FVT-030: Kafka label is present on worker nodes whose disk status is ok."""
    tc = TC["kafka_node_label"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_kafka_node_label)


@pytest.mark.local_storage
@pytest.mark.order(10602)
def test_kafka_disk_status_file(host):
    """TC-FVT-032: Per-node status file exists and has a valid result field."""
    tc = TC["kafka_disk_status_file"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_kafka_disk_status)
