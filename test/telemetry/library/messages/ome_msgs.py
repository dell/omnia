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
OME Automation - Messages.

This module contains all user-facing messages for OME (OpenManage Enterprise) tests.
"""

from typing import Dict


# =============================================================================
# OME TEST NAMES
# =============================================================================

OME_TEST_NAMES: Dict[str, str] = {
    # Deployment tests
    "ome_vector_bridge": "Verify Vector-OME bridge deployment ready",
    "ome_kafka_user": "Verify OME KafkaUser CR exists",

    # Certificate tests
    "ome_external_kafka_certs": "Verify external Kafka TLS certificates exist",
    "ome_pfx_conversion": "Verify user.pfx certificate created for OME mTLS",
    "ome_upload_certs": "Verify TLS certificates uploaded to OME",

    # Connectivity tests
    "ome_kafka_connectivity": "Verify OME Kafka forwarder connectivity status",

    # Kafka topic/data tests
    "ome_kafka_topics": "Verify OME Kafka topics exist",
    "ome_telemetry_data": "Verify OME telemetry data in Kafka",
    "ome_inventory_data": "Verify OME inventory data in Kafka",
    "ome_alerts_data": "Verify OME alerts data in Kafka",
    "ome_health_data": "Verify OME health data in Kafka",
    "ome_auditlogs_data": "Verify OME audit logs data in Kafka",
}


# =============================================================================
# OME LOG MESSAGES
# =============================================================================

OME_LOG_MSGS: Dict[str, str] = {
    # Deployment
    "ome_bridge_running": "Vector-OME bridge: {count}/{expected} pods running",
    "ome_bridge_not_running": "Vector-OME bridge: only {running}/{expected} pods running",
    "ome_kafka_user_exists": "OME KafkaUser '{user}' exists",
    "ome_kafka_user_missing": "OME KafkaUser '{user}' not found",

    # Certificates
    "ome_certs_found": "All {count} TLS certificate files found in {dir}",
    "ome_certs_missing": "TLS certificate files missing: {missing}",
    "ome_pfx_created": "user.pfx certificate created at {path}",
    "ome_pfx_failed": "Failed to create user.pfx: {error}",
    "ome_certs_uploaded": "TLS certificates uploaded to OME at {ome_ip}",
    "ome_certs_upload_failed": "Failed to upload certs to OME: {error}",
    "ome_playbook_running": "Running external_kafka playbook ({reason})",

    # Certificate comparison (OME vs locally generated)
    "ome_cert_match": "Uploaded certificate matches local cert ({count} fields)",
    "ome_cert_mismatch": "Uploaded certificate differs from local cert in {count} field(s)",
    "ome_cert_compare_failed": "Unable to compare certificates: {error}",

    # Connectivity
    "ome_kafka_connected": "OME Kafka forwarder '{name}' status: Connected",
    "ome_kafka_disconnected": "OME Kafka forwarder status: {status}",
    "ome_kafka_checking": "Checking OME Kafka forwarder connectivity at {ome_ip}",
    "ome_kafka_configuring": "Configuring Kafka forwarder with broker {broker}",
    "ome_kafka_polling": "Waiting for connection... ({attempt}/{max_attempts})",

    # Kafka topics
    "ome_topics_found": "All {count} OME Kafka topics found",
    "ome_topics_missing": "OME Kafka topics missing: {missing}",
    "ome_topics_checking": "Checking OME Kafka topics via REST proxy",

    # Kafka data verification
    "ome_data_verifying": "Verifying OME data in Kafka topic '{topic}'",
    "ome_data_found": "OME data found in Kafka topic '{topic}': {count} record(s)",
    "ome_data_missing": "No OME data found in Kafka topic '{topic}'",
    "ome_data_sample": "Sample record from '{topic}':",

    # Cleanup
    "ome_cleaned": "No OME pods remaining",
    "ome_not_cleaned": "{count} OME pod(s) still present",
}


# =============================================================================
# OME ASSERTION MESSAGES
# =============================================================================

OME_ASSERT_MSGS: Dict[str, str] = {
    # Deployment
    "ome_bridge_not_running": (
        "Vector-OME bridge pods not running: {running}/{expected}\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry -l app=vector-ome\n"
        "  2. kubectl describe deploy vector-ome -n telemetry\n"
        "  3. Re-run: ansible-playbook telemetry.yml --tags deploy_ome\n"
    ),
    "ome_kafka_user_missing": (
        "OME KafkaUser CR '{user}' not found\n"
        "HOW TO FIX:\n"
        "  1. kubectl get kafkauser -n telemetry\n"
        "  2. Re-run: ansible-playbook telemetry.yml --tags deploy_ome\n"
    ),

    # Certificates
    "ome_certs_missing": (
        "TLS certificate files missing: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook telemetry.yml --tags external_kafka\n"
        "  2. Check output in /opt/omnia/telemetry/output/<project>/external_kafka/\n"
    ),
    "ome_pfx_failed": (
        "Failed to create user.pfx for OME mTLS\n"
        "HOW TO FIX:\n"
        "  1. Verify user.crt and user.key exist\n"
        "  2. Run manually: openssl pkcs12 -export -out user.pfx -inkey user.key -in user.crt\n"
    ),
    "ome_upload_failed": (
        "Certificate upload to OME failed: {error}\n"
        "HOW TO FIX:\n"
        "  1. Verify OME is reachable at {ome_ip}\n"
        "  2. Check OME credentials in test_creds.yml\n"
        "  3. Verify certificate files exist\n"
    ),

    "ome_cert_mismatch": (
        "Certificate uploaded to OME does not match the locally generated"
        " certificate. Differing field(s): {mismatches}\n"
        "HOW TO FIX:\n"
        "  1. Re-run: ansible-playbook telemetry.yml --tags external_kafka\n"
        "  2. Re-upload certs so OME uses the current Kafka client cert\n"
        "  3. Compare manually: openssl x509 -in user.crt -noout -subject -issuer\n"
    ),

    # Connectivity
    "ome_kafka_not_connected": (
        "OME Kafka forwarder is {status}\n"
        "HOW TO FIX:\n"
        "  1. Check OME Data Forwarding Service configuration\n"
        "  2. Upload Kafka CA certificate via OME UI\n"
        "  3. Verify Kafka bootstrap endpoint is reachable from OME\n"
    ),

    # Kafka topics
    "ome_topics_missing": (
        "OME Kafka topics missing: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Verify OME Kafka forwarder is connected\n"
        "  2. Check OME → Configuration → Data Forwarding Service\n"
        "  3. Verify OME is sending data to Kafka\n"
    ),

    # Kafka data
    "ome_data_missing": (
        "No OME data found in Kafka topic '{topic}'\n"
        "HOW TO FIX:\n"
        "  1. Verify OME Kafka forwarder status: Connected\n"
        "  2. Check OME Transfer Status shows recent activity\n"
        "  3. curl http://<bridge-ip>:8080/topics to list topics\n"
    ),

    # Cleanup
    "ome_not_cleaned": (
        "{count} OME pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry -l app=vector-ome\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup_ome\n"
    ),
}
