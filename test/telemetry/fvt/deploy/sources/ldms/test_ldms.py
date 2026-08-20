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
Telemetry Deploy — LDMS Source Verification Tests.

Test cases:
    TC_SR_006: Verify LDMS aggregator StatefulSet ready
    TC_SR_007: Verify LDMS store daemon pod running
    TC_SR_008: Verify Vector-LDMS bridge deployment ready
    TC_SR_009: Verify LDMS Kafka topic exists
    TC_SR_010: Verify LDMS sampler config on NFS
"""

import pytest

from omnia_auto import TestLogger, load_test_config

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.source_func import (
    verify_ldms_aggregator,
    verify_ldms_store,
    verify_vector_ldms,
    verify_ldms_kafka_topic,
    verify_ldms_sampler_config,
)
from library.functions.telemetry_func import (
    is_source_enabled,
    load_telemetry_config_from_target,
)


def _skip_if_ldms_disabled(host):
    """Skip test if LDMS source is not enabled."""
    if not is_source_enabled(host, "ldms"):
        pytest.skip("LDMS source not enabled in config")


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(50)
def test_ldms_aggregator(host):
    """TC_SR_006: Verify LDMS aggregator StatefulSet ready.

    Checks that the nersc-ldms-aggr StatefulSet has >= 1 ready replica.
    """
    _skip_if_ldms_disabled(host)
    tc = TC["ldms_aggregator"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying LDMS aggregator StatefulSet")
    result = verify_ldms_aggregator(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="LDMS aggregator",
                count=result["ready_replicas"],
                expected=1,
            ),
            f"Ready replicas: {result['ready_replicas']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="LDMS aggregator",
                running=result["ready_replicas"],
                expected=1,
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="LDMS aggregator",
        running=result["ready_replicas"],
        expected=1,
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(51)
def test_ldms_store(host):
    """TC_SR_007: Verify LDMS store daemon pod running.

    Checks that the nersc-ldms-store pod phase is Running.
    """
    _skip_if_ldms_disabled(host)
    tc = TC["ldms_store"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying LDMS store daemon pod")
    result = verify_ldms_store(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="LDMS store",
                count=1,
                expected=1,
            ),
            f"Phase: {result['phase']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="LDMS store",
                running=0,
                expected=1,
            ),
            f"Phase: {result['phase']}",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="LDMS store",
        running=0,
        expected=1,
    )


@pytest.mark.source
@pytest.mark.order(52)
def test_vector_ldms(host):
    """TC_SR_008: Verify Vector-LDMS bridge deployment ready.

    Checks that the vector-ldms Deployment has ready replicas.
    Only runs when telemetry_bridges.vector_ldms.metrics_enabled is true.
    """
    _skip_if_ldms_disabled(host)

    # Check bridge flag
    config = load_telemetry_config_from_target(host)
    bridge_enabled = False
    if config:
        bridges = config.get("telemetry_bridges", {})
        vector_ldms = bridges.get("vector_ldms", {})
        bridge_enabled = vector_ldms.get("metrics_enabled", False)
    if not bridge_enabled:
        pytest.skip("Vector-LDMS bridge not enabled in config")

    tc = TC["vector_ldms"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying Vector-LDMS bridge deployment")
    result = verify_vector_ldms(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="Vector-LDMS",
                count=result["ready_replicas"],
                expected=result["ready_replicas"],
            ),
            f"Ready replicas: {result['ready_replicas']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="Vector-LDMS",
                running=result["ready_replicas"],
                expected="1+",
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Vector-LDMS",
        running=result["ready_replicas"],
        expected="1+",
    )


@pytest.mark.source
@pytest.mark.order(53)
def test_ldms_kafka_topic(host):
    """TC_SR_009: Verify Kafka topic 'ldms' exists.

    Checks that the Kafka topic for LDMS telemetry data exists.
    """
    _skip_if_ldms_disabled(host)
    tc = TC["ldms_kafka_topic"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kafka topic 'ldms'")
    result = verify_ldms_kafka_topic(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["topic_exists"].format(topic=result["topic_name"]),
            "",
        )
    else:
        tl.failed(
            LOG_MSGS["topic_missing"].format(topic=result["topic_name"]),
            "",
        )

    assert result["success"], ASSERT_MSGS["topic_missing"].format(
        topic=result["topic_name"],
    )


@pytest.mark.source
@pytest.mark.order(54)
def test_ldms_sampler_config(host):
    """TC_SR_010: Verify LDMS sampler config on NFS.

    Checks that the LDMS sampler configuration file exists on the
    NFS share path at <cluster_mount>/telemetry/ldms/samplers/sampler.conf.
    """
    _skip_if_ldms_disabled(host)
    tc = TC["ldms_sampler_config"]
    tl = TestLogger(tc["title"], tc["id"])

    # Get cluster_mount from config
    config = load_telemetry_config_from_target(host)
    cluster_mount = "/opt/omnia"
    if config:
        cluster_mount = config.get("cluster_mount", cluster_mount)
    share_path = f"{cluster_mount}/telemetry/ldms"

    tl.check(f"Checking sampler config at {share_path}")
    result = verify_ldms_sampler_config(host, share_path)

    if result["success"]:
        tl.passed(
            "LDMS sampler config exists",
            f"Path: {result['path']}",
        )
    else:
        tl.failed(
            "LDMS sampler config missing",
            f"Expected at: {result['path']}",
        )

    assert result["success"], (
        f"LDMS sampler config missing at {result['path']}"
    )
