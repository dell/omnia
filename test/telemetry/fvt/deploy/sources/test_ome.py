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

Always-run checks validate the Vector-OME bridge and KafkaUser. When
``configure_ome=true``, the suite also validates the exported mTLS artifacts,
PFX conversion and upload, OME connectivity, certificate identity, topic
creation, and data in each OME Kafka topic.
"""

from datetime import datetime

import pytest

from library.functions import (
    TestLogger,
    compare_ome_cert_with_local,
    configure_ome_kafka_and_wait,
    convert_certs_to_pfx,
    get_kafka_external_bootstrap,
    get_ome_kafka_forwarder_config,
    get_ome_pipeline_context,
    load_test_config,
    load_test_credentials,
    run_external_kafka_playbook,
    upload_ome_client_cert,
    upload_ome_server_cert,
    verify_deploy_ready,
    verify_external_kafka_certs,
    verify_external_kafka_connection_details,
    verify_ome_data_in_kafka,
    verify_ome_kafka_connectivity,
    verify_ome_kafka_topics,
    verify_ome_kafka_user_cr,
    verify_ome_logs_in_victoria,
    verify_ome_metrics_in_victoria,
    view_ome_client_cert,
)
from library.messages import (
    OME_ASSERT_MSGS,
    OME_LOG_MSGS,
)
from library.messages import (
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.messages import (
    TEST_LOG_MSGS as LOG_MSGS,
)
from library.vars import (
    OME_KAFKA_CERT_FILES,
    OME_KAFKA_CONNECTION_TIMEOUT_SECONDS,
    OME_KAFKA_DATA_TIMEOUT_SECONDS,
    OME_KAFKA_TOPIC_TIMEOUT_SECONDS,
    OME_MAX_ENTRIES_SHOWN,
    OME_MAX_FIELDS_SHOWN,
    OME_MAX_METRICS_SHOWN,
    OME_VICTORIA_POLL_TIMEOUT_SECONDS,
    TELEMETRY_NAMESPACE,
    VECTOR_OME_APP_NAME,
)
from library.vars import (
    TEST_CASES as TC,
)

# Module-level state for test dependencies
_ome_certs_uploaded = None  # None=not run, True=success, False=failed
_ome_certs_error = ""


def _skip_if_ome_source_disabled(host, channel=None):
    """Skip unless either source or one requested source channel is enabled."""
    context = get_ome_pipeline_context(host)
    if channel:
        enabled = context[f"source_{channel}_enabled"]
        message = OME_LOG_MSGS["ome_source_channel_disabled"].format(
            channel=channel,
        )
    else:
        enabled = context["source_enabled"]
        message = OME_LOG_MSGS["ome_source_disabled"]
    if not enabled:
        pytest.skip(message)
    return context


def _skip_if_ome_bridge_disabled(host, channel=None):
    """Skip unless either bridge or one requested bridge channel is enabled."""
    context = get_ome_pipeline_context(host)
    if channel:
        enabled = context[f"bridge_{channel}_enabled"]
        message = OME_LOG_MSGS["ome_bridge_channel_disabled"].format(
            channel=channel,
        )
    else:
        enabled = context["bridge_enabled"]
        message = OME_LOG_MSGS["ome_bridge_disabled"]
    if not enabled:
        pytest.skip(message)
    return context


def _skip_if_certs_not_uploaded():
    """Skip test if certificate upload failed."""
    if _ome_certs_uploaded is False:
        pytest.skip(f"Skipped: cert upload failed - {_ome_certs_error}")


def _skip_if_configure_ome_false():
    """Skip test if configure_ome is false in test_config."""
    test_cfg = load_test_config()
    if not test_cfg.get("configure_ome", False):
        pytest.skip("configure_ome=false in test_config.yml")


def _get_ome_credentials():
    """Read OME credentials from test_creds.yml.

    Returns:
        tuple: (ome_ip, ome_user, ome_secret) or empty values.
    """
    test_cfg = load_test_config()
    ome_ip = test_cfg.get("ome_ip", "")

    ome_user = "admin"
    ome_secret = ""
    try:
        creds = load_test_credentials()
        # Flat structure: ome_username, ome_password
        ome_user = creds.get("ome_username", "admin")
        ome_secret = creds.get("ome_password", "")
    except Exception:
        pass

    return ome_ip, ome_user, ome_secret


def _get_ome_config(host=None):
    """Read OME configuration from test_config.yml and test_creds.yml.

    Args:
        host: Testinfra host connection (for Kafka bootstrap auto-discovery).

    Returns:
        dict with keys: ome_ip, ome_identifier, pfx_secret.
    """
    test_cfg = load_test_config()

    # pfx_secret comes from test_creds.yml
    pfx_secret = ""
    try:
        creds = load_test_credentials()
        pfx_secret = creds.get("pfx_secret", "")
    except Exception:
        pass

    return {
        "ome_ip": test_cfg.get("ome_ip", ""),
        "ome_identifier": test_cfg.get("ome_identifier", "ome"),
        "pfx_secret": pfx_secret,
    }


# =========================================================================
# TC_SR_070: Verify Vector-OME bridge deployment ready
#   Runs when either Vector-OME bridge channel is enabled
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ome
@pytest.mark.order(80)
def test_ome_vector_bridge(host):
    """Verify Vector-OME bridge deployment ready."""
    _skip_if_ome_bridge_disabled(host)
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
#   Runs when either Vector-OME bridge channel is enabled
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.ome
@pytest.mark.order(81)
def test_ome_kafka_user(host):
    """Verify OME KafkaUser CR exists."""
    _skip_if_ome_bridge_disabled(host)
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
# TC_SR_072: Verify external Kafka connection artifacts
#   Only runs when configure_ome=true
#   Runs external_kafka playbook first, then checks certs and endpoints
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(82)
def test_ome_external_kafka_certs(host):
    """Verify external Kafka TLS certificates and exported endpoints.

    If artifacts are missing or invalid, or the force flag is true, runs the
    external_kafka playbook to export them from the Kubernetes cluster.
    """
    _skip_if_ome_source_disabled(host)
    _skip_if_configure_ome_false()
    tc = TC["ome_external_kafka_certs"]
    tl = TestLogger(tc["title"], tc["id"])

    test_cfg = load_test_config()
    force_playbook = test_cfg.get("force_external_kafka_playbook", False)

    # Check whether the complete export already exists and matches live K8s.
    tl.check(OME_LOG_MSGS["ome_kafka_artifacts_checking"])
    result = verify_external_kafka_certs(host)
    details_result = verify_external_kafka_connection_details(host)

    # Run the playbook if any artifact is invalid or the force flag is set.
    if not result["success"] or not details_result["success"] or force_playbook:
        if force_playbook:
            reason = "force_external_kafka_playbook=true"
        elif not result["success"]:
            reason = "certificates missing"
        else:
            reason = "connection endpoint export invalid"
        tl.check(OME_LOG_MSGS["ome_playbook_running"].format(reason=reason))
        pb_result = run_external_kafka_playbook()
        if not pb_result["success"]:
            tl.failed(
                OME_LOG_MSGS["ome_kafka_artifacts_invalid"].format(
                    error=pb_result["error"],
                ),
                f"Playbook error: {pb_result['error']}",
            )
            assert False, OME_ASSERT_MSGS[
                "ome_kafka_artifacts_invalid"
            ].format(
                error=pb_result["error"],
            )

        # Re-check all generated artifacts after the playbook.
        result = verify_external_kafka_certs(host)
        details_result = verify_external_kafka_connection_details(host)

    detail_lines = [
        f"  \u2713 {f}" if f in result["found"]
        else f"  \u2717 {f}: MISSING"
        for f in OME_KAFKA_CERT_FILES
    ]
    if details_result["success"]:
        detail_lines.extend([
            f"  \u2713 OME Kafka bootstrap: "
            f"{details_result['bootstrap_server']}",
            f"  \u2713 Validation HTTP Bridge: "
            f"{details_result['bridge_endpoint']}",
        ])
    else:
        detail_lines.extend(
            f"  \u2717 {mismatch}"
            for mismatch in details_result["mismatches"]
        )
    artifact_details = "\n".join(detail_lines)
    artifacts_valid = result["success"] and details_result["success"]

    if artifacts_valid:
        tl.passed(
            OME_LOG_MSGS["ome_kafka_artifacts_valid"].format(
                count=len(result["found"]),
            ),
            artifact_details,
        )
    else:
        tl.failed(
            OME_LOG_MSGS["ome_kafka_artifacts_invalid"].format(
                error=(
                    details_result["error"]
                    or ", ".join(result["missing"])
                ),
            ),
            artifact_details,
        )

    assert artifacts_valid, OME_ASSERT_MSGS[
        "ome_kafka_artifacts_invalid"
    ].format(
        error=details_result["error"] or ", ".join(result["missing"]),
    )


# =========================================================================
# TC_SR_073: Verify user.pfx certificate created for OME mTLS
#   Only runs when configure_ome=true, after certs are verified
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(83)
def test_ome_pfx_conversion(host):
    """Verify user.pfx certificate created for OME mTLS."""
    _skip_if_ome_source_disabled(host)
    _skip_if_configure_ome_false()
    tc = TC["ome_pfx_conversion"]
    tl = TestLogger(tc["title"], tc["id"])

    # Get pfx_secret from credentials
    ome_cfg = _get_ome_config()
    pfx_secret = ome_cfg.get("pfx_secret", "")

    tl.check("Converting user.crt + user.key to user.pfx")
    result = convert_certs_to_pfx(host, pfx_secret)

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
#   Uploads both server cert (CA) and client cert (PFX)
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(84)
def test_ome_upload_certs(host):
    """Verify TLS certificates uploaded to OME.

    Uploads:
    - ca.crt as server certificate (X.509 format)
    - user.pfx as client certificate (PKCS12 format)

    Uses OME REST API:
    - ApplicationService.UploadServerCertificate
    - ApplicationService.UploadClientCertificate

    Requires ome_ip and OME credentials.
    """
    global _ome_certs_uploaded, _ome_certs_error

    _skip_if_ome_source_disabled(host)
    _skip_if_configure_ome_false()
    tc = TC["ome_upload_certs"]
    tl = TestLogger(tc["title"], tc["id"])

    ome_ip, ome_user, ome_secret = _get_ome_credentials()
    ome_cfg = _get_ome_config()
    pfx_secret = ome_cfg.get("pfx_secret", "")

    if not ome_ip:
        _ome_certs_uploaded = False
        _ome_certs_error = "OME IP not configured"
        pytest.skip("OME IP not configured in test_config.yml")
    if not ome_secret:
        _ome_certs_uploaded = False
        _ome_certs_error = "OME credentials not configured"
        pytest.skip(
            "OME credentials not configured in test_creds.yml"
        )

    # Upload server certificate (CA)
    tl.check(f"Uploading server certificate (CA) to OME at {ome_ip}")
    server_result = upload_ome_server_cert(
        host, ome_ip, ome_user, ome_secret,
    )

    if not server_result["success"]:
        _ome_certs_uploaded = False
        _ome_certs_error = f"Server cert: {server_result['error']}"
        tl.failed(
            LOG_MSGS["ome_certs_upload_failed"].format(
                error=server_result["error"]
            ),
            f"\u2717 Server cert upload failed: {server_result['error']}",
        )
        assert False, (
            f"Server certificate upload to OME at {ome_ip} failed: "
            f"{server_result['error']}"
        )

    # Upload client certificate (PFX)
    tl.check(f"Uploading client certificate (PFX) to OME at {ome_ip}")
    client_result = upload_ome_client_cert(
        host, ome_ip, ome_user, ome_secret, pfx_secret,
    )

    if not client_result["success"]:
        _ome_certs_uploaded = False
        _ome_certs_error = f"Client cert: {client_result['error']}"
        tl.failed(
            LOG_MSGS["ome_certs_upload_failed"].format(
                error=client_result["error"]
            ),
            f"\u2717 Client cert upload failed: {client_result['error']}",
        )
        assert False, (
            f"Client certificate upload to OME at {ome_ip} failed: "
            f"{client_result['error']}"
        )

    # Verify client cert was uploaded
    tl.check("Verifying client certificate uploaded to OME")
    view_result = view_ome_client_cert(
        host, ome_ip, ome_user, ome_secret,
    )

    details = [
        f"\u2713 Server cert (CA) uploaded: HTTP {server_result['http_code']}",
        f"\u2713 Client cert (PFX) uploaded: HTTP {client_result['http_code']}",
    ]
    if view_result["success"]:
        details.append(
            f"\u2713 Client cert verified: {view_result.get('issued_to', 'N/A')}"
        )
        details.append(
            f"  Valid: {view_result.get('valid_from', '')} to "
            f"{view_result.get('valid_to', '')}"
        )

    # Mark certs as successfully uploaded
    _ome_certs_uploaded = True
    _ome_certs_error = ""

    tl.passed(
        LOG_MSGS["ome_certs_uploaded"].format(ome_ip=ome_ip),
        "\n".join(details),
    )

    assert server_result["success"] and client_result["success"], (
        f"Certificate upload to OME at {ome_ip} failed"
    )


# =========================================================================
# TC_SR_075: Verify OME Kafka forwarder connectivity status
#   Only runs when configure_ome=true and ome_ip is set
#   If not connected, attempts to configure and test the connection
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(85)
def test_ome_kafka_connectivity(host):
    """Verify OME Kafka forwarder connectivity status.

    Uses OME REST API to check the Kafka forwarder is connected.
    If not connected and kafka_bootstrap_server is configured,
    attempts to test and save the forwarder settings.

    Requires ome_ip and OME credentials in test config/creds.
    Skipped if certificate upload failed (TC_SR_054).
    """
    context = _skip_if_ome_source_disabled(host)
    _skip_if_configure_ome_false()
    _skip_if_certs_not_uploaded()
    tc = TC["ome_kafka_connectivity"]
    tl = TestLogger(tc["title"], tc["id"])

    ome_ip, ome_user, ome_secret = _get_ome_credentials()
    ome_identifier = context["identifier"]

    if not ome_ip:
        tl.skipped(
            "OME IP not configured in test_config.yml",
            "Set ome_ip in test_config.yml",
        )
        pytest.skip("OME IP not configured in test_config.yml")

    if not ome_secret:
        tl.skipped(
            "OME credentials not configured in test_creds.yml",
            "Run: bash setup_env.sh --set-creds",
        )
        pytest.skip(
            "OME credentials not configured in test_creds.yml"
        )

    # Check both live connectivity and the saved native Kafka endpoint.
    tl.check(OME_LOG_MSGS["ome_kafka_checking"].format(ome_ip=ome_ip))
    result = verify_ome_kafka_connectivity(
        host, ome_ip, ome_user, ome_secret,
    )

    kafka_bootstrap = ""
    configured_broker = ""
    configuration_required = False
    config_result = None
    test_result = None
    settings_result = None
    if result.get("status") != "AuthError":
        tl.check(OME_LOG_MSGS["ome_kafka_bootstrap_discovering"])
        kafka_bootstrap = get_kafka_external_bootstrap(host)
        if not kafka_bootstrap:
            tl.failed(
                OME_LOG_MSGS["ome_kafka_bootstrap_missing"],
                OME_ASSERT_MSGS["ome_kafka_not_connected"].format(
                    status="bootstrap endpoint unavailable",
                ),
            )
            result = dict(result)
            result.update({
                "success": False,
                "status": "BootstrapUnavailable",
                "error": OME_LOG_MSGS["ome_kafka_bootstrap_missing"],
            })
        else:
            tl.check(OME_LOG_MSGS["ome_kafka_config_reading"])
            config_result = get_ome_kafka_forwarder_config(
                host, ome_ip, ome_user, ome_secret,
            )
            configured_broker = config_result.get("broker_list", "")
            configuration_required = (
                not config_result["success"]
                or configured_broker != kafka_bootstrap
            )
            if configuration_required:
                tl.check(OME_LOG_MSGS["ome_kafka_reconciling"].format(
                    current=configured_broker or "unavailable",
                    expected=kafka_bootstrap,
                ))

    if (not result["success"] or configuration_required) and kafka_bootstrap:
        tl.check(OME_LOG_MSGS["ome_kafka_configuring"].format(
            broker=kafka_bootstrap,
        ))

        # Retry TestConnection/Save while certificates reload, and use the
        # authoritative ConnectivityStatus as the final result.
        tl.check(OME_LOG_MSGS["ome_kafka_waiting"].format(
            timeout=OME_KAFKA_CONNECTION_TIMEOUT_SECONDS,
        ))

        def _report_connectivity(attempt, max_attempts, status_result):
            tl.check(OME_LOG_MSGS["ome_kafka_polling"].format(
                attempt=attempt,
                max_attempts=max_attempts,
                status=status_result.get("status", "Unknown"),
            ))

        result = configure_ome_kafka_and_wait(
            host, ome_ip, ome_user, ome_secret, kafka_bootstrap,
            ome_identifier=ome_identifier,
            status_callback=_report_connectivity,
            force_configuration=configuration_required,
        )
        test_result = result.get("test_connection")
        settings_result = result.get("settings_update")

        # Connectivity is only valid when OME saved the requested native
        # bootstrap endpoint, not a stale HTTP Bridge or previous cluster IP.
        if result["success"]:
            config_result = get_ome_kafka_forwarder_config(
                host, ome_ip, ome_user, ome_secret,
            )
            configured_broker = config_result.get("broker_list", "")
            if (
                    not config_result["success"]
                    or configured_broker != kafka_bootstrap):
                result = dict(result)
                result.update({
                    "success": False,
                    "status": "ConfigMismatch",
                    "error": config_result.get("error") or (
                        f"OME saved broker '{configured_broker}', expected "
                        f"'{kafka_bootstrap}'"
                    ),
                })

    status_icon = "\u2713" if result["success"] else "\u2717"
    details_lines = [
        f"{status_icon} Kafka connectivity: "
        f"{result.get('status')}",
        f"OME endpoint: https://{ome_ip}",
        f"Forwarder: {result.get('forwarder_name', 'N/A')}",
        f"Enabled: {result.get('forwarder_enabled', 'N/A')}",
        f"Status: {result.get('status', 'Unknown')}",
    ]
    if kafka_bootstrap:
        details_lines.append(f"Desired Kafka broker: {kafka_bootstrap}")
    if config_result is not None:
        details_lines.append(
            f"Saved Kafka broker: {configured_broker or 'unavailable'}"
        )
    if test_result and not test_result["success"]:
        details_lines.append(
            f"TestConnection response: {test_result['error']}"
        )
    if settings_result and not settings_result["success"]:
        details_lines.append(
            f"Save response: {settings_result['error']}"
        )
    if "attempts" in result:
        details_lines.append(
            f"Connection checks: {result['attempts']} over "
            f"{result['elapsed_seconds']}s"
        )
        details_lines.append(
            f"TestConnection attempts: "
            f"{result['test_connection_attempts']}"
        )
        details_lines.append(
            f"Save attempts: {result['settings_update_attempts']}"
        )
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


# =========================================================================
# TC_SR_056: Verify uploaded certificate matches generated certificate
#   Compares the cert details from OME with the generated cert
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(86)
def test_ome_cert_verify(host):
    """Verify uploaded certificate matches generated certificate.

    Compares the certificate details returned by OME with the
    certificate that was generated by the external_kafka playbook.
    """
    _skip_if_ome_source_disabled(host)
    _skip_if_configure_ome_false()
    _skip_if_certs_not_uploaded()
    tc = TC["ome_cert_verify"]
    tl = TestLogger(tc["title"], tc["id"])

    ome_ip, ome_user, ome_secret = _get_ome_credentials()

    if not ome_ip or not ome_secret:
        pytest.skip("OME credentials not configured")

    tl.check("Comparing OME certificate with locally generated user.crt")
    result = compare_ome_cert_with_local(host, ome_ip, ome_user, ome_secret)

    if result.get("error") and not result.get("mismatches"):
        tl.failed(
            OME_LOG_MSGS["ome_cert_compare_failed"].format(
                error=result["error"],
            ),
            f"Error: {result['error']}",
        )
        assert False, OME_ASSERT_MSGS["ome_cert_mismatch"].format(
            mismatches=result["error"],
        )

    matches = result.get("matches", [])
    mismatches = result.get("mismatches", [])

    details = [f"Compared {len(matches) + len(mismatches)} certificate field(s)"]
    for m in matches:
        details.append(f"  ✓ {m['field']}: {m['value']}")
    for m in mismatches:
        details.append(
            f"  ✗ {m['field']}: local='{m['local']}' OME='{m['ome']}'"
        )

    if result["success"]:
        tl.passed(
            OME_LOG_MSGS["ome_cert_match"].format(count=len(matches)),
            "\n".join(details),
        )
    else:
        tl.failed(
            OME_LOG_MSGS["ome_cert_mismatch"].format(count=len(mismatches)),
            "\n".join(details),
        )

    assert result["success"], OME_ASSERT_MSGS["ome_cert_mismatch"].format(
        mismatches=", ".join(m["field"] for m in mismatches),
    )


# =========================================================================
# TC_SR_057: Verify enabled OME Kafka topics exist
#   Checks only topic families enabled by the OME source flags
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(87)
def test_ome_kafka_topics(host):
    """Verify OME Kafka topics exist.

    Checks only the metric and log topic families enabled for the OME source.
    """
    context = _skip_if_ome_source_disabled(host)
    _skip_if_configure_ome_false()
    _skip_if_certs_not_uploaded()
    tc = TC["ome_kafka_topics"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(OME_LOG_MSGS["ome_topics_checking"].format(
        timeout=OME_KAFKA_TOPIC_TIMEOUT_SECONDS,
    ))
    result = verify_ome_kafka_topics(
        host,
        expected_topics=context["expected_topics"],
        timeout_seconds=OME_KAFKA_TOPIC_TIMEOUT_SECONDS,
    )

    if result.get("error"):
        tl.failed(
            OME_LOG_MSGS["ome_topics_missing"].format(
                missing=", ".join(result.get("missing_topics", [])),
            ),
            f"Error: {result['error']}",
        )
        assert False, result["error"]

    found = result.get("found_topics", [])
    missing = result.get("missing_topics", [])
    expected = result.get("expected_topics", context["expected_topics"])

    details = [
        f"Kafka bridge IP  : {result.get('bridge_ip')}:{result.get('port')}",
        f"Topics found     : {len(found)}/{len(expected)}",
        f"Checks           : {result.get('attempts', 0)} over "
        f"{result.get('elapsed_seconds', 0)}s",
        "",
        "Topic verification:",
    ]
    for topic in expected:
        exists = topic in found
        mark = "\u2713" if exists else "\u2717"
        state = "exists" if exists else "MISSING"
        details.append(f"  {mark} '{topic}': {state}")

    if result["success"]:
        tl.passed(
            OME_LOG_MSGS["ome_topics_found"].format(count=len(found)),
            "\n".join(details),
        )
    else:
        tl.failed(
            OME_LOG_MSGS["ome_topics_missing"].format(missing=", ".join(missing)),
            "\n".join(details),
        )

    assert result["success"], OME_ASSERT_MSGS["ome_topics_missing"].format(
        missing=", ".join(missing),
    )


# =========================================================================
# TC_SR_058 - TC_SR_062: Verify OME data per Kafka topic
#   One test case per OME topic so a single stalled data stream is
#   reported independently of the others.
# =========================================================================

def _verify_topic_data(host, tc_key, topic, channel):
    """Run the OME Kafka data check for a single topic.

    Args:
        host: Testinfra host connection to the OIM.
        tc_key: Key into TEST_CASES for the topic under test.
        topic: Canonical Kafka topic name to consume from.
        channel: OME source channel required by the topic.
    """
    context = _skip_if_ome_source_disabled(host, channel)
    _skip_if_configure_ome_false()
    _skip_if_certs_not_uploaded()
    topic = f"{context['identifier']}.{topic.rsplit('.', maxsplit=1)[-1]}"
    tc = TC[tc_key]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(OME_LOG_MSGS["ome_data_verifying"].format(
        topic=topic,
        timeout=OME_KAFKA_DATA_TIMEOUT_SECONDS,
    ))
    result = verify_ome_data_in_kafka(
        host,
        topic=topic,
        timeout_seconds=OME_KAFKA_DATA_TIMEOUT_SECONDS,
    )

    details = _build_ome_summary_lines(result, topic)
    for summary in result.get("record_summaries", []):
        details.extend(_build_ome_record_lines(summary))

    if result["success"]:
        tl.passed(
            OME_LOG_MSGS["ome_data_found"].format(
                topic=topic, count=result["records_found"],
            ),
            "\n".join(details),
        )
    else:
        tl.failed(
            OME_LOG_MSGS["ome_data_missing"].format(topic=topic),
            "\n".join(details),
        )

    assert result["success"], OME_ASSERT_MSGS["ome_data_missing"].format(
        topic=topic,
    )


def _format_kafka_ts(kafka_ts):
    """Format a Kafka record timestamp to a human-readable string.

    The Kafka REST proxy reports milliseconds since the epoch, while OME
    metric timestamps are already formatted strings.

    Args:
        kafka_ts: Epoch timestamp in seconds or milliseconds.

    Returns:
        str: ``<raw> (<YYYY-MM-DD HH:MM:SS>)`` or the raw value.
    """
    try:
        epoch = float(kafka_ts)
    except (TypeError, ValueError):
        return str(kafka_ts)

    # Kafka reports milliseconds; anything past year ~5138 in seconds is ms
    if epoch > 1e11:
        epoch /= 1000
    try:
        human = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return str(kafka_ts)
    return f"{kafka_ts} ({human})"


def _build_ome_summary_lines(result, topic):
    """Build the summary header lines for an OME topic data test.

    Args:
        result: Return value of ``verify_ome_data_in_kafka``.
        topic: Kafka topic name under test.

    Returns:
        list: Header detail lines.
    """
    records = result.get("records_found", 0)
    lines = [
        f"Kafka bridge IP  : {result.get('bridge_ip', '')}:"
        f"{result.get('port', '')}",
        f"Topic            : {topic}",
        f"Records consumed : {records}",
        f"Entries sampled  : {result.get('total_entries', 0)}",
        f"Checks           : {result.get('attempts', 0)}",
        f"Wait elapsed     : {result.get('elapsed_seconds', 0)}s",
    ]
    if result.get("error"):
        lines.append(f"Error            : {result['error']}")
    lines.append("")
    lines.append(
        "Record details:" if records else "Record details: (no records)"
    )
    return lines


def _build_ome_record_lines(summary):
    """Build detail lines for a single consumed OME Kafka record.

    Args:
        summary: One entry from ``result['record_summaries']``.

    Returns:
        list: Indented detail lines describing the record.
    """
    entries = summary.get("entries", [])
    icon = "\u2713" if entries else "\u2717"
    lines = [
        f"  {icon} partition {summary.get('partition')} /"
        f" offset {summary.get('offset')}"
    ]
    lines.append(
        f"      Kafka Time  : {_format_kafka_ts(summary.get('timestamp'))}"
    )
    if summary.get("payload_key"):
        lines.append(f"      Payload     : {summary['payload_key']}")
    lines.append(f"      Entries     : {summary.get('entry_count', 0)}")

    for entry in entries[:OME_MAX_ENTRIES_SHOWN]:
        lines.extend(_build_ome_entry_lines(entry))

    remaining = len(entries) - OME_MAX_ENTRIES_SHOWN
    if remaining > 0:
        lines.append(f"        ... {remaining} more entry(s)")
    return lines


def _build_ome_entry_lines(entry):
    """Build detail lines for one device/alert/log entry in a record.

    Args:
        entry: One entry from ``summary['entries']``.

    Returns:
        list: Indented detail lines describing the entry.
    """
    metrics = entry.get("metrics", [])
    fields = entry.get("fields", {})
    label = entry.get("identifier") or "(no identifier)"

    if metrics:
        lines = [f"        \u2713 {label} ({len(metrics)} metrics)"]
        for m in metrics[:OME_MAX_METRICS_SHOWN]:
            component = f" [{m['component']}]" if m.get("component") else ""
            when = f" @ {m['timestamp']}" if m.get("timestamp") else ""
            lines.append(
                f"            - {m['name']}{component}: {m['value']}{when}"
            )
        remaining = len(metrics) - OME_MAX_METRICS_SHOWN
        if remaining > 0:
            lines.append(f"            ... {remaining} more metric(s)")
        return lines

    lines = [f"        \u2713 {label}"]
    for key, value in list(fields.items())[:OME_MAX_FIELDS_SHOWN]:
        lines.append(f"            - {key}: {value}")
    return lines


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(88)
def test_ome_telemetry_data(host):
    """Verify OME telemetry metrics reach the ome.telemetry Kafka topic."""
    _verify_topic_data(
        host, "ome_telemetry_data", "ome.telemetry", "metrics",
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(89)
def test_ome_inventory_data(host):
    """Verify OME inventory data reaches the ome.inventory Kafka topic."""
    _verify_topic_data(
        host, "ome_inventory_data", "ome.inventory", "metrics",
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(90)
def test_ome_alerts_data(host):
    """Verify OME alerts reach the ome.alerts Kafka topic."""
    _verify_topic_data(host, "ome_alerts_data", "ome.alerts", "logs")


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(91)
def test_ome_health_data(host):
    """Verify OME health data reaches the ome.health Kafka topic."""
    _verify_topic_data(host, "ome_health_data", "ome.health", "metrics")


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(92)
def test_ome_auditlogs_data(host):
    """Verify OME audit logs reach the ome.auditlogs Kafka topic."""
    _verify_topic_data(host, "ome_auditlogs_data", "ome.auditlogs", "logs")


# =========================================================================
# TC_SR_064 - TC_SR_066: Verify OME metrics per VictoriaMetrics topic
#   Metric names are generated from OME payloads, so each source topic is
#   validated independently and every discovered metric is reported.
# =========================================================================

def _verify_victoria_metric_topic(host, tc_key, topic):
    """Run the OME VictoriaMetrics check for one metric-bearing topic."""
    _skip_if_ome_source_disabled(host, "metrics")
    _skip_if_ome_bridge_disabled(host, "metrics")
    _skip_if_configure_ome_false()
    _skip_if_certs_not_uploaded()
    tc = TC[tc_key]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(
        OME_LOG_MSGS["ome_vm_data_verifying"].format(
            topic=topic,
            timeout=OME_VICTORIA_POLL_TIMEOUT_SECONDS,
        )
    )
    result = verify_ome_metrics_in_victoria(host, topic)

    if result.get("skipped", False):
        tl.skipped(result["details"])
        pytest.skip(result["details"])
    if result["success"]:
        tl.passed(
            OME_LOG_MSGS["ome_vm_data_found"].format(
                topic=topic,
                count=result["metric_count"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            OME_LOG_MSGS["ome_vm_data_missing"].format(topic=topic),
            result.get("details") or result["error"],
        )

    assert result["success"], OME_ASSERT_MSGS["ome_vm_data_missing"].format(
        topic=topic,
        error=result["error"],
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(93)
def test_ome_telemetry_metrics_in_victoria(host):
    """Verify ome.telemetry metrics and timestamps in VictoriaMetrics."""
    _verify_victoria_metric_topic(
        host, "ome_telemetry_metrics_in_vm", "ome.telemetry",
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(94)
def test_ome_inventory_metrics_in_victoria(host):
    """Verify ome.inventory metrics and timestamps in VictoriaMetrics."""
    _verify_victoria_metric_topic(
        host, "ome_inventory_metrics_in_vm", "ome.inventory",
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(95)
def test_ome_health_metrics_in_victoria(host):
    """Verify ome.health metrics and timestamps in VictoriaMetrics."""
    _verify_victoria_metric_topic(
        host, "ome_health_metrics_in_vm", "ome.health",
    )


# =========================================================================
# TC_SR_067 - TC_SR_068: Verify OME logs per VictoriaLogs topic
#   OME alerts and auditlogs are event-driven and validated independently.
# =========================================================================

def _verify_victoria_log_topic(host, tc_key, topic):
    """Run the OME VictoriaLogs check for one log-bearing topic."""
    _skip_if_ome_source_disabled(host, "logs")
    _skip_if_ome_bridge_disabled(host, "logs")
    _skip_if_configure_ome_false()
    _skip_if_certs_not_uploaded()
    tc = TC[tc_key]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(
        OME_LOG_MSGS["ome_vl_data_verifying"].format(
            topic=topic,
            timeout=OME_VICTORIA_POLL_TIMEOUT_SECONDS,
        )
    )
    result = verify_ome_logs_in_victoria(host, topic)

    if result.get("skipped", False):
        tl.skipped(result["details"])
        pytest.skip(result["details"])
    if result["success"]:
        tl.passed(
            OME_LOG_MSGS["ome_vl_data_found"].format(
                topic=topic,
                count=result["log_count"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            OME_LOG_MSGS["ome_vl_data_missing"].format(topic=topic),
            result.get("details") or result["error"],
        )

    assert result["success"], OME_ASSERT_MSGS["ome_vl_data_missing"].format(
        topic=topic,
        error=result["error"],
    )


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(96)
def test_ome_alerts_logs_in_victoria(host):
    """Verify ome.alerts entries and timestamps in VictoriaLogs."""
    _verify_victoria_log_topic(host, "ome_alerts_logs_in_vl", "ome.alerts")


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(97)
def test_ome_auditlogs_logs_in_victoria(host):
    """Verify ome.auditlogs entries and timestamps in VictoriaLogs."""
    _verify_victoria_log_topic(
        host, "ome_auditlogs_logs_in_vl", "ome.auditlogs",
    )
