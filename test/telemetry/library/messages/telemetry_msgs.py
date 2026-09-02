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
    "vast_cleaned": "No VAST resources remaining",
    "vast_not_cleaned": "VAST resources still present",

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

    # OME Kafka topics
    "ome_topics_found": "All {count} OME Kafka topics found",
    "ome_topics_missing": "OME Kafka topics missing: {missing}",
    "ome_kafka_data_found": "OME data found in Kafka topic '{topic}': {count} record(s)",
    "ome_kafka_data_missing": "No OME data found in Kafka topic '{topic}'",

    # Config skip
    "source_disabled": "{source} source not enabled in telemetry_config.yml",

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
    "deployment_verified": "PowerScale deployment verified: {details}",
    "deployment_failed": "PowerScale deployment verification failed: {details}",
    "feature_flags": "PowerScale feature flags: {flags}",
    "health_metrics": "PowerScale health metrics: {details}",
    "health_metrics_missing": "PowerScale health metrics not found: {details}",
    "tls_enforced": "PowerScale TLS enforcement: {details}",
    "label_compliance": "PowerScale pod label compliance: {details}",
    "label_compliance_failed": "PowerScale pod label compliance failed: {details}",
    "scrape_interval": "PowerScale scrape interval: {details}",
    "csi_auth_mode": "PowerScale CSI authorization mode: {details}",
    "csi_auth_failed": "PowerScale CSI authorization check failed: {details}",
    "deployment_mode": "PowerScale deployment mode: {details}",
    "csi_exporter_deployed": "CSI Volume Exporter deployment verified: {details}",
    "csi_exporter_failed": "CSI Volume Exporter deployment failed: {details}",
    "csi_exporter_endpoint": "CSI Volume Exporter metrics endpoint: {details}",
    "csi_exporter_endpoint_failed": (
        "CSI Volume Exporter metrics endpoint not accessible: {details}"
    ),
    "csi_exporter_metrics": "CSI Volume Exporter metrics: {details}",
    "csi_driver_deployed": (
        "CSI Driver for PowerScale (isilon-controller) deployment verified: {details}"
    ),
    "csi_driver_failed": (
        "CSI Driver for PowerScale (isilon-controller) deployment failed: {details}"
    ),
    "health_monitor_container": "external-health-monitor-controller container verified: {details}",
    "health_monitor_container_failed": (
        "external-health-monitor-controller container check failed: {details}"
    ),
    "csi_exporter_dependency": "CSI volume exporter dependency validation: {details}",
    "csi_exporter_dependency_failed": "CSI volume exporter dependency validation failed: {details}",
    "health_monitor_warning": "Health monitor warning message behavior: {details}",
    "csm_otel_flow": "CSM Metrics to OTEL Collector data flow: {details}",
    "csm_otel_flow_failed": "CSM Metrics to OTEL Collector data flow failed: {details}",
    "otel_vm_export": "OTEL Collector to VictoriaMetrics export: {details}",
    "otel_vm_export_failed": "OTEL Collector to VictoriaMetrics export failed: {details}",
    "otel_service_patch": "OTEL Collector service patch: {details}",
    "otel_service_patch_failed": "OTEL Collector service patch failed: {details}",
    "cert_manager_tls": "cert-manager TLS certificate generation: {details}",
    "cert_manager_tls_failed": "cert-manager TLS certificate generation failed: {details}",

    # VAST
    "vast_svc_exists": "VAST external service '{service}' exists with endpoint {endpoint}",
    "vast_svc_missing": "VAST external service '{service}' not found",
    "vast_vmscrape_exists": "VAST VMServiceScrape '{name}' exists",
    "vast_vmscrape_missing": "VAST VMServiceScrape '{name}' not found",
    "vast_secret_exists": "VAST credentials secret '{secret}' exists",
    "vast_secret_missing": "VAST credentials secret '{secret}' not found",
    "vast_metrics_found": (
        "{count} VAST metric(s) found in VictoriaMetrics"
    ),
    "vast_metrics_missing": "Missing VAST metrics in VictoriaMetrics: {missing}",
    "vast_logs_found": "{count} VAST log entries found in VictoriaLogs",
    "vast_logs_missing": "No VAST logs found in VictoriaLogs",

    # Online/Offline Mode
    "config_value_correct": "Configuration value correct: {key}={value}",
    "config_value_incorrect": (
        "Configuration value incorrect: {key} expected {expected}, got {actual}"
    ),
    "python_package_installed": "Python package installed: {package}",
    "git_repo_cloned": "Git repo cloned: {repo}",
    "git_repo_not_cloned": "Git repo not cloned: {repo}",
    "deployment_success": "Deployment successful: {component}",
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

    # OME Kafka topics
    "ome_topics_missing": (
        "OME Kafka topics missing: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Verify OME Kafka forwarder is connected\n"
        "  2. Check OME → Configuration → Data Forwarding Service\n"
        "  3. Verify OME is sending data to Kafka\n"
    ),
    "ome_kafka_data_missing": (
        "No OME data found in Kafka topic '{topic}'\n"
        "HOW TO FIX:\n"
        "  1. Verify OME Kafka forwarder status: Connected\n"
        "  2. Check OME Transfer Status shows recent activity\n"
        "  3. curl http://<bridge-ip>:8080/topics to list topics\n"
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
    "vast_not_cleaned": (
        "VAST resources still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. kubectl get svc,vmservicescrape,secret -n telemetry | grep vast\n"
        "  2. Re-run cleanup: ansible-playbook telemetry.yml --tags cleanup_vast\n"
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
    "deployment_failed": (
        "PowerScale deployment verification failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry | grep karavi\n"
        "  2. kubectl logs deployment/karavi-metrics-powerscale -n telemetry\n"
        "  3. kubectl logs deployment/otel-collector -n telemetry\n"
    ),
    "health_metrics_missing": (
        "PowerScale health metrics not found: {details}\n"
        "HOW TO FIX:\n"
        "  1. Check CSM Metrics PowerScale logs\n"
        "  2. Verify PowerScale API connectivity\n"
        "  3. Check vmagent scrape targets\n"
    ),
    "tls_not_enforced": (
        "PowerScale TLS not enforced: {details}\n"
        "HOW TO FIX:\n"
        "  1. Verify cert-manager is deployed\n"
        "  2. Check OTEL TLS secret exists\n"
        "  3. Review csm_observability Helm values\n"
    ),
    "label_compliance_failed": (
        "PowerScale pod label compliance failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. Check pod labels: kubectl get pods -n telemetry "
        "-o jsonpath='{{.items[*].metadata.labels}}'\n"
        "  2. Review Helm chart values for label configuration\n"
    ),
    "scrape_interval_invalid": (
        "PowerScale scrape interval invalid: {details}\n"
        "HOW TO FIX:\n"
        "  1. Update scrape_interval in telemetry_config.yml\n"
        "  2. Acceptable range: 15s-300s\n"
    ),
    "csi_auth_failed": (
        "PowerScale CSI authorization check failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. Review csm_observability Helm values\n"
        "  2. Check karavi authorization configuration\n"
    ),
    "csi_exporter_failed": (
        "CSI Volume Exporter deployment failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n telemetry | grep csi-volume-exporter\n"
        "  2. kubectl logs deployment/csi-volume-exporter -n telemetry\n"
        "  3. Check PowerScale CSI driver is installed\n"
    ),
    "csi_exporter_endpoint_failed": (
        "CSI Volume Exporter metrics endpoint not accessible: {details}\n"
        "HOW TO FIX:\n"
        "  1. kubectl get svc csi-volume-exporter -n telemetry\n"
        "  2. kubectl port-forward svc/csi-volume-exporter 9090:9090 -n telemetry\n"
        "  3. Check pod logs: kubectl logs deployment/csi-volume-exporter -n telemetry\n"
    ),
    "csi_exporter_metrics_missing": (
        "CSI Volume Exporter metrics not found in VictoriaMetrics: {details}\n"
        "HOW TO FIX:\n"
        "  1. Check vmagent scrape targets for CSI Volume Exporter\n"
        "  2. Verify metrics endpoint is accessible\n"
        "  3. Check vmagent logs: kubectl logs -n telemetry <vmagent-pod>\n"
    ),
    "csi_driver_failed": (
        "CSI Driver for PowerScale (isilon-controller) deployment failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n kube-system | grep isilon-controller\n"
        "  2. kubectl logs statefulset/isilon-controller -n kube-system\n"
        "  3. Check CSI driver installation: kubectl get csinodes -n kube-system\n"
    ),
    "health_monitor_container_failed": (
        "external-health-monitor-controller container check failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. kubectl get pods -n isilon | grep isilon-controller\n"
        "  2. kubectl describe pod <isilon-controller-pod> -n isilon\n"
        "  3. Check container status: kubectl get pod <isilon-controller-pod> -n isilon "
        "-o jsonpath='{.status.containerStatuses}'\n"
        "  4. Deploy CSI driver with health monitor enabled in CSI driver values.yml\n"
    ),
    "csi_exporter_dependency_failed": (
        "CSI volume exporter dependency validation failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. Verify external-health-monitor-controller container is running\n"
        "  2. Check deployment logs for warning messages\n"
        "  3. Ensure CSI driver is deployed with health monitor enabled\n"
        "  4. Re-run telemetry.yml after fixing CSI driver configuration\n"
    ),
    "csm_otel_flow_failed": (
        "CSM Metrics to OTEL Collector data flow failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. Check CSM Metrics PowerScale pod logs: kubectl logs "
        "deployment/karavi-metrics-powerscale -n telemetry\n"
        "  2. Verify CSM Metrics is exposing metrics on expected port\n"
        "  3. Check OTEL Collector pod logs: kubectl logs deployment/otel-collector -n telemetry\n"
        "  4. Verify OTEL Collector configuration includes CSM Metrics as receiver\n"
    ),
    "otel_vm_export_failed": (
        "OTEL Collector to VictoriaMetrics export failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. Check OTEL Collector export configuration\n"
        "  2. Verify VictoriaMetrics vmagent is running: kubectl get pods -n telemetry "
        "| grep vmagent\n"
        "  3. Check vmagent scrape targets include OTEL Collector\n"
        "  4. Verify network connectivity between OTEL Collector and VictoriaMetrics\n"
    ),
    "otel_service_patch_failed": (
        "OTEL Collector service patch failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. Check OTEL Collector service annotations: kubectl get svc otel-collector "
        "-n telemetry -o yaml\n"
        "  2. Verify prometheus.io/scrape annotation is set to 'true'\n"
        "  3. Verify prometheus.io/port annotation points to metrics port\n"
        "  4. Re-run deployment to apply service patch\n"
    ),
    "cert_manager_tls_failed": (
        "cert-manager TLS certificate generation failed: {details}\n"
        "HOW TO FIX:\n"
        "  1. Check cert-manager pods: kubectl get pods -n telemetry | grep cert-manager\n"
        "  2. Verify cert-manager is running properly\n"
        "  3. Check TLS secret: kubectl get secret otel-collector-tls -n telemetry\n"
        "  4. Review cert-manager logs for certificate issuance issues\n"
        "  5. Verify cert-manager ClusterIssuer is configured\n"
    ),

    # VAST
    "vast_svc_missing": (
        "VAST external service '{service}' not found\n"
        "HOW TO FIX:\n"
        "  1. kubectl get svc -n telemetry | grep vast\n"
        "  2. Re-run telemetry deploy with VAST enabled\n"
    ),
    "vast_vmscrape_missing": (
        "VAST VMServiceScrape '{name}' not found\n"
        "HOW TO FIX:\n"
        "  1. kubectl get vmservicescrape -n telemetry | grep vast\n"
        "  2. Re-run telemetry deploy with VAST enabled\n"
    ),
    "vast_secret_missing": (
        "VAST credentials secret '{secret}' not found\n"
        "HOW TO FIX:\n"
        "  1. kubectl get secret -n telemetry | grep vast\n"
        "  2. Re-run telemetry deploy with VAST credentials\n"
    ),
    "vast_metrics_missing": (
        "VAST metrics not found in VictoriaMetrics: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Check vmagent scrape targets for VAST\n"
        "  2. Verify VAST endpoint is reachable: "
        "curl -sk https://<vast-ip>:443/api/prometheusmetrics/all\n"
        "  3. Check vmagent logs: kubectl logs -n telemetry <vmagent-pod>\n"
    ),
    "vast_logs_missing": (
        "No VAST logs found in VictoriaLogs\n"
        "HOW TO FIX:\n"
        "  1. Check VAST syslog config in VAST UI: Settings > Notifications > Syslog Setup\n"
        "  2. Verify VLAgent is listening: kubectl get svc vlagent-vlagent -n telemetry\n"
        "  3. Check VLAgent logs: kubectl logs vlagent-vlagent-0 -n telemetry\n"
    ),

    # Online/Offline Mode
    "config_value_incorrect": (
        "Configuration value incorrect: {key} expected {expected}, got {actual}\n"
        "HOW TO FIX:\n"
        "  1. Edit /abc/omnia/telemetry/input/project_default/telemetry_packages.yml\n"
        "  2. Set {key} to {expected}\n"
        "  3. Re-run deployment\n"
    ),

    # LDMS Kafka Data
    "ldms_data_missing": (
        "LDMS data missing for hostnames: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Check LDMS sampler running on compute nodes: systemctl status ldmsd\n"
        "  2. Check LDMS aggregator logs: kubectl logs nersc-ldms-aggr-0 -n telemetry\n"
        "  3. Check LDMS store logs: kubectl logs nersc-ldms-store-0 -n telemetry\n"
        "  4. Verify Kafka ldms topic has data: curl http://<bridge>:8080/topics\n"
    ),
    "ldms_plugins_missing": (
        "LDMS plugins missing for host {hostname}: {plugins}\n"
        "HOW TO FIX:\n"
        "  1. Check sampler.conf on compute node for plugin configuration\n"
        "  2. Verify LDMS sampler is running: ldms_ls -h localhost -p 10001\n"
    ),
}


# --- LDMS Log Messages ---
LDMS_LOG_MSGS = {
    "ldms_data_found": "LDMS data verified for {count} instances from {hosts} hosts",
    "ldms_data_missing": "LDMS data missing for {count} instance(s)",
    "ldms_verifying": "Verifying LDMS data in Kafka topic '{topic}'",
    "ldms_earliest_found": "Earliest LDMS data found for {count} hosts",
    "ldms_earliest_missing": "Earliest LDMS data missing for hosts: {missing}",
}


# --- LDMS Assert Messages ---
LDMS_ASSERT_MSGS = {
    "ldms_data_missing": (
        "LDMS data missing for {count} expected instance(s)\n"
        "Missing: {missing}\n"
        "Found: {found}\n"
    ),
    "ldms_hostnames_missing": (
        "LDMS data missing from hostnames: {missing}\n"
        "Found hostnames: {found}\n"
    ),
}
