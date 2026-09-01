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
Telemetry Deploy — SFM Prometheus Remote Write integration verification.

Validates the opt-in SFM workflow in dependency order:
  required Omnia VictoriaMetrics workloads and pods
  required Omnia VictoriaMetrics services and endpoints
  SFM Prometheus pod, hosts mapping, and vminsert reachability
  SFM certificate import, Remote Write readback, and forwarding health
  three attributed SFM metrics with earliest/latest Victoria timestamps
"""

import pytest

from library.functions import (
    TestLogger,
    configure_sfm_observability,
    configure_sfm_switch,
    verify_sfm_metrics_in_victoria,
    verify_sfm_omnia_pods,
    verify_sfm_omnia_services,
)
from library.messages import SFM_ASSERT_MSGS as ASSERT
from library.messages import SFM_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.sfm
@pytest.mark.order(110)
def test_sfm_omnia_pods(host):
    """Verify the three required Omnia workloads and their pods."""
    test_case = TC["sfm_omnia_pods"]
    test_log = TestLogger(test_case["title"], test_case["id"])
    test_log.check(LOG["omnia_pods_check"])
    result = verify_sfm_omnia_pods(host)
    if result.get("skipped", False):
        test_log.skipped(result["details"])
        pytest.skip(result["details"])
    if result["success"]:
        test_log.passed(LOG["omnia_pods_passed"], result["details"])
    else:
        test_log.failed(
            LOG["omnia_pods_failed"],
            result.get("details") or result["error"],
        )
    assert result["success"], ASSERT["omnia_pods_failed"].format(
        error=result["error"],
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.sfm
@pytest.mark.order(111)
def test_sfm_omnia_services(host):
    """Verify the three required Omnia services and ready endpoints."""
    test_case = TC["sfm_omnia_services"]
    test_log = TestLogger(test_case["title"], test_case["id"])
    test_log.check(LOG["omnia_services_check"])
    result = verify_sfm_omnia_services(host)
    if result.get("skipped", False):
        test_log.skipped(result["details"])
        pytest.skip(result["details"])
    if result["success"]:
        test_log.passed(LOG["omnia_services_passed"], result["details"])
    else:
        test_log.failed(
            LOG["omnia_services_failed"],
            result.get("details") or result["error"],
        )
    assert result["success"], ASSERT["omnia_services_failed"].format(
        error=result["error"],
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.sfm
@pytest.mark.order(112)
def test_sfm_switch_configuration(host):
    """Verify the complete SFM Prometheus switch-side configuration."""
    test_case = TC["sfm_switch_configuration"]
    test_log = TestLogger(test_case["title"], test_case["id"])
    test_log.check(LOG["switch_check"])
    result = configure_sfm_switch(host)
    if result.get("skipped", False):
        test_log.skipped(result["details"])
        pytest.skip(result["details"])
    if result["success"]:
        test_log.passed(LOG["switch_passed"], result["details"])
    else:
        test_log.failed(
            LOG["switch_failed"],
            result.get("details") or result["error"],
        )
    assert result["success"], ASSERT["switch_failed"].format(
        error=result["error"],
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.sfm
@pytest.mark.order(113)
def test_sfm_observability_configuration(host):
    """Configure and verify the complete SFM observability target."""
    test_case = TC["sfm_observability_configuration"]
    test_log = TestLogger(test_case["title"], test_case["id"])
    test_log.check(LOG["observability_check"])
    result = configure_sfm_observability(host)
    if result.get("skipped", False):
        test_log.skipped(result["details"])
        pytest.skip(result["details"])
    if result["success"]:
        test_log.passed(LOG["observability_passed"], result["details"])
    else:
        test_log.failed(
            LOG["observability_failed"],
            result.get("details") or result["error"],
        )
    assert result["success"], ASSERT["observability_failed"].format(
        error=result["error"],
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.sfm
@pytest.mark.order(114)
def test_sfm_metrics_in_victoria(host):
    """Verify three SFM metrics and their Victoria timestamp bounds."""
    test_case = TC["sfm_metrics_in_victoria"]
    test_log = TestLogger(test_case["title"], test_case["id"])
    test_log.check(LOG["metrics_check"])
    result = verify_sfm_metrics_in_victoria(host)
    if result.get("skipped", False):
        test_log.skipped(result["details"])
        pytest.skip(result["details"])
    if result["success"]:
        test_log.passed(
            LOG["metrics_passed"].format(
                count=result["found_metric_count"],
            ),
            result["details"],
        )
    else:
        test_log.failed(
            LOG["metrics_failed"],
            result.get("details") or result["error"],
        )
    assert result["success"], ASSERT["metrics_failed"].format(
        error=result["error"],
    )
