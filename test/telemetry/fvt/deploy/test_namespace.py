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
Telemetry Deploy — Namespace-Wide Verification Tests.

Tests that verify the overall health of the telemetry namespace,
running before any source/sink-specific tests.

Matches the omnia-containers-2.2 format:
  - Shows ``kubectl get pods -o wide`` output
  - Lists every pod with ✓/✗ status
  - Retries if pods are not yet ready

Test cases:
    TC_NS_001: Verify all telemetry pods running
"""

import time

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import verify_all_pods_running


@pytest.mark.sanity
@pytest.mark.order(1)
def test_all_telemetry_pods_running(host):
    """TC_NS_001: Verify all pods in telemetry namespace are running.

    Retries up to 3 times with 30-second intervals.
    All pods must be Running with all containers ready.
    """
    tc = TC["all_pods_running"]
    tl = TestLogger(tc["title"], tc["id"])

    max_retries = 3
    retry_interval = 30
    result = None

    for attempt in range(1, max_retries + 1):
        tl.check(
            f"Checking all pods in telemetry namespace "
            f"(attempt {attempt}/{max_retries})"
        )
        result = verify_all_pods_running(host)

        if result["success"]:
            # Build details: show full kubectl output + per-pod status
            details_lines = [
                f"All pods running on attempt {attempt}",
                "",
            ]
            if result["output"]:
                for line in result["output"].strip().split("\n"):
                    details_lines.append(f"  {line}")

            details = "\n".join(details_lines)
            tl.passed(
                LOG_MSGS["all_pods_running"].format(
                    total=result["total_pods"],
                ),
                details,
            )
            return  # Test passed

        # Not all pods running — show which ones are failing
        if attempt < max_retries:
            not_running_names = [
                f"{p['name']} ({p['ready']}, {p['status']})"
                for p in result["not_running_pods"]
            ]
            tl.check(
                f"Not running ({result['not_running_count']}/{result['total_pods']}): "
                f"{not_running_names} - retrying in {retry_interval}s"
            )
            time.sleep(retry_interval)

    # All retries exhausted
    details_lines = [f"Failed after {max_retries} retries", ""]
    if result["output"]:
        for line in result["output"].strip().split("\n"):
            details_lines.append(f"  {line}")

    details_lines.append("")
    details_lines.append("Pod status:")
    for p in result.get("running_pods", []):
        details_lines.append(
            f"  \u2713 {p['name']}: {p['status']} ({p['ready']})"
        )
    for p in result.get("not_running_pods", []):
        details_lines.append(
            f"  \u2717 {p['name']}: {p['status']} ({p['ready']}, "
            f"restarts={p['restarts']})"
        )

    details = "\n".join(details_lines)
    tl.failed(
        LOG_MSGS["some_pods_not_running"].format(
            not_running=result["not_running_count"],
            total=result["total_pods"],
        ),
        details,
    )
    assert False, ASSERT_MSGS["telemetry_pods_not_running"].format(
        not_running=result["not_running_count"],
        total=result["total_pods"],
    )
