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
Telemetry — Log and Assertion Messages.

Centralized message templates for consistent test output.
"""

# --- Log Messages ---
TEST_LOG_MSGS = {
    # Playbook
    "playbook_success": "Playbook completed in {duration}",
    "playbook_failed": "Playbook failed (rc={rc}, duration={duration})",

    # Pods
    "pods_running": "{component}: {count}/{expected} pods running",
    "pods_not_running": "{component}: only {running}/{expected} pods running",

    # Containers
    "containers_ready": "Pod {pod}: all {count} containers ready",
    "containers_not_ready": "Pod {pod}: containers not ready: {not_ready}",

    # Topics
    "topic_exists": "Kafka topic '{topic}' exists and is ready",
    "topic_missing": "Kafka topic '{topic}' not found or not ready",
    "topic_ready": "Kafka topic '{topic}' Ready condition: {status}",

    # Services
    "services_ok": "{component} service exists",
    "services_missing": "{component} service not found",

    # Health
    "health_ok": "{component} health check passed",
    "health_failed": "{component} health check failed",

    # Kafka cluster
    "kafka_ready": "Kafka cluster is Ready",
    "kafka_not_ready": "Kafka cluster is not Ready: {status}",

    # Env vars
    "env_vars_ok": "All required omnia.env variables present",
    "env_vars_missing": "{count} omnia.env variable(s) missing",

    # K8s nodes
    "nodes_ready": "All {count} K8s nodes are Ready",
    "nodes_not_ready": "{not_ready_count} node(s) not Ready",

    # Cleanup - General
    "cleanup_pods_ok": "All telemetry pods removed",
    "cleanup_pods_remaining": "{count} pod(s) still running after cleanup",
    "cleanup_topics_ok": "All Kafka topics removed",
    "cleanup_topics_remaining": "{count} topic(s) still present after cleanup",

    # Cleanup - Sources
    "idrac_cleaned": "No iDRAC pods remaining",
    "idrac_not_cleaned": "{count} iDRAC pod(s) still present",
    "ldms_cleaned": "No LDMS pods remaining",
    "ldms_not_cleaned": "{count} LDMS pod(s) still present",
    "ome_cleaned": "No OME pods remaining",
    "ome_not_cleaned": "{count} OME pod(s) still present",
    "dcgm_cleaned": "No DCGM pods remaining",
    "dcgm_not_cleaned": "{count} DCGM pod(s) still present",
    "ufm_cleaned": "No UFM resources remaining",
    "ufm_not_cleaned": "UFM resources still present",
    "vast_cleaned": "No VAST resources remaining",
    "vast_not_cleaned": "VAST resources still present",
    "sfm_cleaned": "No SFM pods remaining",
    "sfm_not_cleaned": "{count} SFM pod(s) still present",

    # Cleanup - Sinks
    "kafka_cleaned": "No Kafka pods remaining",
    "kafka_not_cleaned": "{count} Kafka pod(s) still present",
    "vm_cleaned": "No VictoriaMetrics pods remaining",
    "vm_not_cleaned": "{count} VictoriaMetrics pod(s) still present",
    "vl_cleaned": "No VictoriaLogs pods remaining",
    "vl_not_cleaned": "{count} VictoriaLogs pod(s) still present",

    # Cleanup - Final State
    "no_pods_remaining": "No pods remaining in telemetry namespace",
    "pods_remaining": "{count} pod(s) still present in telemetry namespace",
    "no_pvcs_remaining": "No PVCs remaining in telemetry namespace",
    "pvcs_remaining": "{count} PVC(s) still present in telemetry namespace",

    # Cleanup - Idempotency / Playbook
    "cleanup_failed": "Cleanup playbook failed",
    "deploy_failed": "Deploy playbook failed",
    "idempotent_passed": "Idempotency verified: second run exited 0 (duration={duration}s)",
    "idempotent_failed": "Idempotency failed: second run exited {rc}",

    # All pods running
    "all_pods_running": "All {total} pods running in telemetry namespace",
    "some_pods_not_running": "{not_running}/{total} pod(s) not in Running state",

    # iDRAC pod count
    "idrac_pod_count_match": "iDRAC pod count matches expected: {expected}",
    "idrac_pod_count_mismatch": "iDRAC pod count mismatch",

    # iDRAC MySQL data
    "idrac_mysql_verified": "MySQL data verified in all {count} iDRAC pods",
    "idrac_mysql_missing": "MySQL data missing in {count} iDRAC pod(s)",

    # iDRAC receiver
    "idrac_receiver_collecting": "All {count} iDRAC receivers collecting metrics",
    "idrac_receiver_not_collecting": "{count} iDRAC receiver(s) not collecting",

    # iDRAC VM data
    "idrac_vm_data_found": "iDRAC data found for all {count} service tag(s)",
    "idrac_vm_data_missing": "iDRAC data missing for {count} service tag(s)",

    # OME Kafka connectivity
    "ome_kafka_connected": "OME Kafka forwarder '{name}' status: Connected",
    "ome_kafka_disconnected": "OME Kafka forwarder status: {status}",

    # OME external Kafka certs
    "ome_certs_found": "All {count} TLS certificate files found in {dir}",
    "ome_certs_missing": "TLS certificate files missing: {missing}",
    "ome_pfx_created": "user.pfx certificate created at {path}",
    "ome_pfx_failed": "Failed to create user.pfx: {error}",
    "ome_certs_uploaded": "TLS certificates uploaded to OME at {ome_ip}",
    "ome_certs_upload_failed": "Failed to upload certs to OME: {error}",

    # Config skip
    "source_disabled": "{source} source not enabled in telemetry_config.yml",

    # UFM
    "ufm_svc_exists": "UFM external service '{service}' exists with endpoint {endpoint}",
    "ufm_svc_missing": "UFM external service '{service}' not found",
    "ufm_vmscrape_exists": "UFM VMServiceScrape '{name}' exists",
    "ufm_vmscrape_missing": "UFM VMServiceScrape '{name}' not found",
    "ufm_secret_exists": "UFM credentials secret '{secret}' exists",
    "ufm_secret_missing": "UFM credentials secret '{secret}' not found",
    "ufm_metrics_found": "{count} UFM metric(s) found in VictoriaMetrics",
    "ufm_metrics_missing": "Missing UFM metrics in VictoriaMetrics: {missing}",

    # PowerScale / VictoriaMetrics / VictoriaLogs
    "secret_valid": "Secret '{secret}' has correct endpoint: {endpoint}",
    "secret_invalid": "Secret '{secret}' has wrong endpoint: {actual} (expected {expected})",
    "metrics_found": "{count} metric(s) found in VictoriaMetrics: {metrics}",
    "metrics_missing": "Missing metrics in VictoriaMetrics: {missing}",
    "metric_value": "{metric}: {value}",
    "logs_found": "{count} log entries found in VictoriaLogs",
    "logs_missing": "No log entries found in VictoriaLogs for {source}",
    "syslog_configured": "PowerScale syslog forwarding configured to {target}",
    "syslog_not_configured": "PowerScale syslog not forwarding to {target}",
}

# --- Assertion Messages ---
TEST_ASSERT_MSGS = {
    # Playbook
    "playbook_failed": (
        "Playbook {playbook} --tags {tag} failed (rc={rc})\n"
        "HOW TO FIX:\n"
        "  1. Check logs on the OIM server\n"
        "  2. Run manually: cd src/telemetry && "
        "ansible-playbook playbooks/telemetry.yml --tags {tag} -v\n"
    ),

    # Pods
    "pods_not_running": (
        "{component}: expected {expected} ready, got {running}\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry\n"
        "  2. kubectl describe pod <pod-name> -n telemetry\n"
        "  3. kubectl logs <pod-name> -n telemetry\n"
    ),

    # Topics
    "topic_missing": (
        "Kafka topic '{topic}' not found or not ready\n"
        "HOW TO FIX:\n"
        "  1. kubectl get kafkatopic -n telemetry\n"
        "  2. kubectl describe kafkatopic {topic} -n telemetry\n"
    ),

    # Services
    "service_missing": (
        "Service '{service}' not found in namespace {namespace}\n"
        "HOW TO FIX:\n"
        "  1. kubectl get svc -n telemetry\n"
    ),

    # Containers
    "containers_not_ready": (
        "iDRAC containers not ready: {not_ready}\n"
        "HOW TO FIX:\n"
        "  1. kubectl describe pod {pod} -n telemetry\n"
        "  2. kubectl logs {pod} -c <container> -n telemetry\n"
    ),

    # Env vars
    "env_vars_missing": (
        "Required omnia.env variables missing: {error}\n"
        "HOW TO FIX:\n"
        "  1. Check /etc/omnia/omnia.env on the OIM server\n"
        "  2. Run: omnia.sh --setup-venv\n"
    ),

    # All pods running
    "telemetry_pods_not_running": (
        "{not_running}/{total} pod(s) not in Running/Ready state\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry -o wide\n"
        "  2. kubectl describe pod <failing-pod> -n telemetry\n"
        "  3. kubectl logs <failing-pod> -n telemetry\n"
    ),

    # iDRAC pod count
    "idrac_pod_count_mismatch": (
        "iDRAC pod count: expected {expected}, got {actual}\n"
        "HOW TO FIX:\n"
        "  1. Check bmc_group_data.csv for BMC entries\n"
        "  2. kubectl get pods -n telemetry | grep idrac\n"
        "  3. Re-run telemetry deploy\n"
    ),

    # iDRAC MySQL data
    "idrac_mysql_missing": (
        "MySQL data missing in {count} iDRAC pod(s)\n"
        "HOW TO FIX:\n"
        "  1. kubectl exec <pod> -n telemetry -c mysqldb -- "
        "mysql -e 'SELECT * FROM idrac_telemetry.services'\n"
        "  2. Check idrac-telemetry-receiver logs\n"
    ),

    # iDRAC receiver
    "idrac_receiver_not_collecting": (
        "{count} iDRAC receiver(s) not collecting metrics\n"
        "HOW TO FIX:\n"
        "  1. kubectl logs <pod> -n telemetry -c idrac-telemetry-receiver\n"
        "  2. Verify iDRAC BMC endpoints are reachable\n"
    ),

    # iDRAC VM data
    "idrac_vm_data_missing": (
        "iDRAC telemetry data missing for service tags: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Check iDRAC telemetry receiver logs\n"
        "  2. Check victoria-pump container logs\n"
        "  3. Check vmagent scrape targets\n"
    ),

    # OME Kafka connectivity
    "ome_kafka_not_connected": (
        "OME Kafka forwarder is {status}\n"
        "HOW TO FIX:\n"
        "  1. Check OME Data Forwarding Service configuration\n"
        "  2. Upload Kafka CA certificate via OME UI\n"
        "  3. Verify Kafka bootstrap endpoint is reachable from OME\n"
    ),

    # OME external Kafka certs
    "ome_certs_missing": (
        "TLS certificate files missing: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook telemetry.yml"
        " --tags external_kafka\n"
        "  2. Check output in /opt/omnia/telemetry/external_kafka/\n"
    ),
    "ome_pfx_failed": (
        "Failed to create user.pfx for OME mTLS\n"
        "HOW TO FIX:\n"
        "  1. Verify user.crt and user.key exist in"
        " /opt/omnia/telemetry/external_kafka/\n"
        "  2. Run manually: openssl pkcs12 -export"
        " -out user.pfx -inkey user.key -in user.crt\n"
    ),

    # Cleanup - General
    "cleanup_pods_remaining": (
        "{count} pod(s) still running after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup\n"
    ),

    # Cleanup - Sources
    "idrac_not_cleaned": (
        "{count} iDRAC pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry -l app=idrac-telemetry\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup_idrac\n"
    ),
    "ldms_not_cleaned": (
        "{count} LDMS pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry | grep ldms\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup_ldms\n"
    ),
    "ome_not_cleaned": (
        "{count} OME pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry -l app=vector-ome\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup_ome\n"
    ),
    "dcgm_not_cleaned": (
        "{count} DCGM pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry | grep dcgm\n"
        "  2. Re-run cleanup\n"
    ),
    "ufm_not_cleaned": (
        "UFM resources still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get svc,vmservicescrape,secret -n telemetry | grep ufm\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup_ufm\n"
    ),
    "vast_not_cleaned": (
        "VAST resources still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get svc,vmservicescrape,secret -n telemetry | grep vast\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup_vast\n"
    ),
    "sfm_not_cleaned": (
        "{count} SFM pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry | grep sfm\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup_sfm\n"
    ),

    # Cleanup - Sinks
    "kafka_not_cleaned": (
        "{count} Kafka pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry | grep kafka\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup\n"
    ),
    "vm_not_cleaned": (
        "{count} VictoriaMetrics pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry | grep vm\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup\n"
    ),
    "vl_not_cleaned": (
        "{count} VictoriaLogs pod(s) still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry | grep vl\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup\n"
    ),

    # Cleanup - Final State
    "pods_remaining": (
        "{count} pod(s) still present in telemetry namespace\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup\n"
    ),
    "pvcs_remaining": (
        "{count} PVC(s) still present in telemetry namespace\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pvc -n telemetry\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup\n"
    ),

    # Idempotency
    "idempotent_failed": (
        "Idempotency check failed: second run exited {rc}\n"
        "HOW TO FIX:\n"
        "  1. Check the playbook output for tasks that failed on second run\n"
        "  2. Ensure tasks use proper idempotency guards\n"
    ),

    # UFM
    "ufm_svc_missing": (
        "UFM external service '{service}' not found\n"
        "HOW TO FIX:\n"
        "  1. kubectl get svc -n telemetry | grep ufm\n"
        "  2. Re-run telemetry deploy with UFM enabled\n"
    ),
    "ufm_vmscrape_missing": (
        "UFM VMServiceScrape '{name}' not found\n"
        "HOW TO FIX:\n"
        "  1. kubectl get vmservicescrape -n telemetry | grep ufm\n"
        "  2. Re-run telemetry deploy with UFM enabled\n"
    ),
    "ufm_secret_missing": (
        "UFM credentials secret '{secret}' not found\n"
        "HOW TO FIX:\n"
        "  1. kubectl get secret -n telemetry | grep ufm\n"
        "  2. Re-run telemetry deploy with UFM credentials\n"
    ),
    "ufm_metrics_missing": (
        "UFM metrics not found in VictoriaMetrics: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Check vmagent scrape targets for UFM\n"
        "  2. Verify UFM endpoint is reachable: curl -sk https://<ufm-ip>:9001/metrics\n"
        "  3. Check vmagent logs: kubectl logs -n telemetry <vmagent-pod>\n"
    ),

    # PowerScale
    "secret_invalid": (
        "Secret '{secret}' endpoint mismatch: got '{actual}', expected '{expected}'\n"
        "HOW TO FIX:\n"
        "  1. Update isilon-creds secret with correct PowerScale endpoint\n"
        "  2. kubectl get secret isilon-creds -n telemetry"
        " -o jsonpath='{{.data.config}}' | base64 -d\n"
    ),
    "metrics_missing": (
        "PowerScale metrics not found in VictoriaMetrics: {missing}\n"
        "HOW TO FIX:\n"
        "  1. kubectl logs deployment/karavi-metrics-powerscale -n telemetry\n"
        "  2. Check OTEL collector: kubectl logs deployment/otel-collector -n telemetry\n"
        "  3. Check vmagent scrape targets\n"
    ),
    "logs_missing": (
        "No {source} logs found in VictoriaLogs\n"
        "HOW TO FIX:\n"
        "  1. Check PowerScale syslog config: isi audit settings global view\n"
        "  2. Verify VLAgent is listening: kubectl get svc vlagent-vlagent -n telemetry\n"
        "  3. Check VLAgent logs: kubectl logs vlagent-vlagent-0 -n telemetry\n"
    ),
    "syslog_not_configured": (
        "PowerScale syslog not forwarding to {target}\n"
        "HOW TO FIX:\n"
        "  1. SSH to PowerScale and run:\n"
        "     isi audit settings global modify --config-syslog-servers={target}:514\n"
        "     isi audit settings global modify --system-syslog-servers={target}:514\n"
        "     isi audit settings global modify --protocol-syslog-servers={target}:514\n"
    ),
}
