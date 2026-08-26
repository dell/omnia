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
Telemetry Cleanup — Verification Tests.

Test cases:
    TC_CL_002: Verify telemetry pods removed after cleanup
    TC_CL_003: Verify Kafka topics removed after cleanup
"""

import pytest

from library.functions import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import TELEMETRY_NAMESPACE
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.telemetry_func import run_on_kube_vip
from library.vars.common_vars import CMDS


@pytest.mark.sanity
@pytest.mark.order(1)
def test_cleanup_pods_removed(host):
    """TC_CL_002: Verify telemetry pods removed after cleanup."""
    tc = TC["cleanup_pods_removed"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking for remaining pods in telemetry namespace")
    cmd = CMDS["kubectl_get_pods"].format(namespace=TELEMETRY_NAMESPACE)
    result = run_on_kube_vip(host, cmd)

    pod_count = 0
    if result.rc == 0 and result.stdout.strip():
        lines = [
            ln for ln in result.stdout.strip().split("\n") if ln.strip()
        ]
        pod_count = len(lines)

    if pod_count == 0:
        tl.passed(
            LOG_MSGS["cleanup_pods_ok"],
            "No pods remaining",
        )
    else:
        tl.failed(
            LOG_MSGS["cleanup_pods_remaining"].format(count=pod_count),
            result.stdout.strip(),
        )

    assert pod_count == 0, ASSERT_MSGS["cleanup_pods_remaining"].format(
        count=pod_count,
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_cleanup_topics_removed(host):
    """TC_CL_003: Verify Kafka topics removed after cleanup."""
    tc = TC["cleanup_topics_removed"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking for remaining Kafka topics")
    cmd = CMDS["kafka_get_topics_cr"].format(namespace=TELEMETRY_NAMESPACE)
    result = run_on_kube_vip(host, cmd)

    topic_count = 0
    if result.rc == 0 and result.stdout.strip():
        lines = [
            ln for ln in result.stdout.strip().split("\n") if ln.strip()
        ]
        topic_count = len(lines)

    if topic_count == 0:
        tl.passed(
            LOG_MSGS["cleanup_topics_ok"],
            "No topics remaining",
        )
    else:
        tl.failed(
            LOG_MSGS["cleanup_topics_remaining"].format(count=topic_count),
            result.stdout.strip(),
        )

    assert topic_count == 0, (
        f"{topic_count} Kafka topic(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get kafkatopic -n telemetry\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup\n"
    )
