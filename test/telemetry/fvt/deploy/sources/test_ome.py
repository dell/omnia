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
Telemetry Deploy — OME Source Verification Tests.

OME Architecture:
    OME itself is external (NOT deployed by Omnia).
    Omnia deploys the Vector-OME bridge that reads from OME's Kafka
    broker and writes to VictoriaMetrics/VictoriaLogs via
    vmagent-vector/vlagent-vector.

    OME connects to Kafka via mTLS (port 9094). The test suite can
    optionally run the external_kafka playbook to extract TLS certs,
    convert to PFX, and verify OME connectivity.

    Data pipeline:
        OME -> Kafka (mTLS) -> Vector-OME -> VictoriaMetrics/VictoriaLogs

Test cases (always run):
    TC_SR_070: Verify Vector-OME bridge deployment ready
    TC_SR_071: Verify OME KafkaUser CR exists

Test cases (only when configure_ome=true in test_config.yml):
    TC_SR_072: Verify external Kafka TLS certificates exist
    TC_SR_073: Verify user.pfx certificate created for OME mTLS
    TC_SR_074: Verify OME Kafka forwarder connectivity status
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    VECTOR_OME_APP_NAME,
    OME_KAFKA_CERT_FILES,
    TELEMETRY_NAMESPACE,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import verify_deploy_ready
from library.functions.telemetry_func import is_source_enabled
from library.functions.ome_func import (
    verify_external_kafka_certs,
    convert_certs_to_pfx,
    verify_ome_kafka_user_cr,
    verify_ome_kafka_connectivity,
    run_external_kafka_playbook,
    upload_ome_certs,
)


def _skip_if_ome_disabled(host):
    """Skip test if OME source is not enabled."""
    if not is_source_enabled(host, "ome"):
        pytest.skip("OME source not enabled in config")


def _skip_if_configure_ome_false():
    """Skip test if configure_ome is false in test_config."""
    test_cfg = load_test_config()
    if not test_cfg.get("configure_ome", False):
        pytest.skip("configure_ome=false in test_config.yml")


def _get_ome_credentials():
    """Read OME credentials from test_creds.yml.

    Returns:
        tuple: (ome_ip, ome_user, ome_password) or None values.
    """
    test_cfg = load_test_config()
    ome_ip = test_cfg.get("ome_ip", "")

    try:
        from library.functions import load_test_credentials
        creds = load_test_credentials()
        ome_user = creds.get("ome_user", "admin")
        ome_password = creds.get("ome_password", "")
    except Exception:
        ome_user = "admin"
        ome_password = ""

    return ome_ip, ome_user, ome_password


# =========================================================================
# TC_SR_070: Verify Vector-OME bridge deployment ready
#   Always runs when OME source is enabled
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(80)
def test_ome_vector_bridge(host):
    """Verify Vector-OME bridge deployment ready."""
    _skip_if_ome_disabled(host)
    tc = TC["ome_vector_bridge"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying Vector-OME bridge deployment")
    result = verify_deploy_ready(host, VECTOR_OME_APP_NAME)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="Vector-OME bridge",
                count=result["ready_replicas"],
                expected=result["expected"],
            ),
            f"\u2713 Ready: {result['ready_replicas']}"
            f"/{result['expected']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="Vector-OME bridge",
                running=result["ready_replicas"],
                expected=result["expected"],
            ),
            f"\u2717 Ready: {result['ready_replicas']}"
            f"/{result['expected']}",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Vector-OME bridge",
        expected=result["expected"],
        running=result["ready_replicas"],
    )


# =========================================================================
# TC_SR_071: Verify OME KafkaUser CR exists
#   Always runs when OME source is enabled
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(81)
def test_ome_kafka_user(host):
    """Verify OME KafkaUser CR exists."""
    _skip_if_ome_disabled(host)
    tc = TC["ome_kafka_user"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking OME KafkaUser CR")
    result = verify_ome_kafka_user_cr(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["health_ok"].format(component="OME KafkaUser"),
            f"\u2713 KafkaUser '{result['name']}': exists",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(
                component="OME KafkaUser"
            ),
            f"\u2717 KafkaUser '{result['name']}': MISSING",
        )

    assert result["success"], ASSERT_MSGS["service_missing"].format(
        service=result["name"],
        namespace=TELEMETRY_NAMESPACE,
    )


# =========================================================================
# TC_SR_072: Verify external Kafka TLS certificates exist
#   Only runs when configure_ome=true
#   Runs external_kafka playbook first, then checks certs
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(82)
def test_ome_external_kafka_certs(host):
    """Verify external Kafka TLS certificates exist.

    If certs are not already present, runs the external_kafka
    playbook to extract them from the K8s cluster.
    """
    _skip_if_ome_disabled(host)
    _skip_if_configure_ome_false()
    tc = TC["ome_external_kafka_certs"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if certs already exist
    tl.check("Checking for existing TLS certificate files")
    result = verify_external_kafka_certs(host)

    if not result["success"]:
        # Certs missing — run the external_kafka playbook
        tl.check(
            "Certs missing — running external_kafka playbook"
        )
        pb_result = run_external_kafka_playbook(host)
        if not pb_result["success"]:
            tl.failed(
                LOG_MSGS["ome_certs_missing"].format(
                    missing=", ".join(result["missing"]),
                ),
                f"Playbook error: {pb_result['error']}",
            )
            assert False, ASSERT_MSGS["ome_certs_missing"].format(
                missing=", ".join(result["missing"]),
            )

        # Re-check after playbook
        result = verify_external_kafka_certs(host)

    cert_detail = "\n".join(
        f"  \u2713 {f}" if f in result["found"]
        else f"  \u2717 {f}: MISSING"
        for f in OME_KAFKA_CERT_FILES
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["ome_certs_found"].format(
                count=len(result["found"]),
                dir=result["cert_dir"],
            ),
            cert_detail,
        )
    else:
        tl.failed(
            LOG_MSGS["ome_certs_missing"].format(
                missing=", ".join(result["missing"]),
            ),
            cert_detail,
        )

    assert result["success"], ASSERT_MSGS["ome_certs_missing"].format(
        missing=", ".join(result["missing"]),
    )


# =========================================================================
# TC_SR_073: Verify user.pfx certificate created for OME mTLS
#   Only runs when configure_ome=true, after certs are verified
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(83)
def test_ome_pfx_conversion(host):
    """Verify user.pfx certificate created for OME mTLS."""
    _skip_if_ome_disabled(host)
    _skip_if_configure_ome_false()
    tc = TC["ome_pfx_conversion"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Converting user.crt + user.key to user.pfx")
    result = convert_certs_to_pfx(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["ome_pfx_created"].format(
                path=result["pfx_path"]
            ),
            f"\u2713 {result['pfx_path']}",
        )
    else:
        tl.failed(
            LOG_MSGS["ome_pfx_failed"].format(
                error=result["error"]
            ),
            f"\u2717 {result['pfx_path']}: {result['error']}",
        )

    assert result["success"], ASSERT_MSGS["ome_pfx_failed"]


# =========================================================================
# TC_SR_074: Verify TLS certificates uploaded to OME
#   Only runs when configure_ome=true and ome_ip is set
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(84)
def test_ome_upload_certs(host):
    """Verify TLS certificates uploaded to OME.

    Uploads ca.crt to OME via REST API
    (ApplicationService.UploadCertificate).
    Requires ome_ip and OME credentials.
    """
    _skip_if_ome_disabled(host)
    _skip_if_configure_ome_false()
    tc = TC["ome_upload_certs"]
    tl = TestLogger(tc["title"], tc["id"])

    ome_ip, ome_user, ome_password = _get_ome_credentials()

    if not ome_ip:
        pytest.skip("OME IP not configured in test_config.yml")
    if not ome_password:
        pytest.skip(
            "OME credentials not configured in test_creds.yml"
        )

    tl.check(f"Uploading TLS certificates to OME at {ome_ip}")
    result = upload_ome_certs(
        host, ome_ip, ome_user, ome_password,
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["ome_certs_uploaded"].format(ome_ip=ome_ip),
            f"\u2713 CA cert uploaded to https://{ome_ip}",
        )
    else:
        tl.failed(
            LOG_MSGS["ome_certs_upload_failed"].format(
                error=result["error"]
            ),
            f"\u2717 Error: {result['error']}",
        )

    assert result["success"], (
        f"Certificate upload to OME at {ome_ip} failed: "
        f"{result['error']}"
    )


# =========================================================================
# TC_SR_075: Verify OME Kafka forwarder connectivity status
#   Only runs when configure_ome=true and ome_ip is set
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(85)
def test_ome_kafka_connectivity(host):
    """Verify OME Kafka forwarder connectivity status.

    Uses OME REST API to check the Kafka forwarder is connected.
    Requires ome_ip and OME credentials in test config/creds.
    """
    _skip_if_ome_disabled(host)
    _skip_if_configure_ome_false()
    tc = TC["ome_kafka_connectivity"]
    tl = TestLogger(tc["title"], tc["id"])

    ome_ip, ome_user, ome_password = _get_ome_credentials()

    if not ome_ip:
        tl.skipped(
            "OME IP not configured in test_config.yml",
            "Set ome_ip in test_config.yml",
        )
        pytest.skip("OME IP not configured in test_config.yml")

    if not ome_password:
        tl.skipped(
            "OME credentials not configured in test_creds.yml",
            "Set ome_user/ome_password in test_creds.yml",
        )
        pytest.skip(
            "OME credentials not configured in test_creds.yml"
        )

    tl.check(
        f"Checking OME Kafka forwarder connectivity at {ome_ip}"
    )
    result = verify_ome_kafka_connectivity(
        host, ome_ip, ome_user, ome_password,
    )

    status_icon = "\u2713" if result["success"] else "\u2717"
    details_lines = [
        f"{status_icon} Kafka connectivity: "
        f"{result.get('status')}",
        f"OME endpoint: https://{ome_ip}",
        f"Forwarder: {result.get('forwarder_name', 'N/A')}",
        f"Enabled: {result.get('forwarder_enabled', 'N/A')}",
        f"Status: {result.get('status', 'Unknown')}",
    ]
    time_connected = result.get("time_last_connected", "")
    if time_connected:
        details_lines.append(f"Last connected: {time_connected}")
    if result.get("error"):
        details_lines.append(f"Error: {result['error']}")
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["ome_kafka_connected"].format(
                name=result.get("forwarder_name", ""),
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["ome_kafka_disconnected"].format(
                status=result.get("status", "Unknown"),
            ),
            details,
        )

    assert result["success"], (
        ASSERT_MSGS["ome_kafka_not_connected"].format(
            status=result.get("status", "Unknown"),
        )
    )
