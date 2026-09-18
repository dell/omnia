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

"""Centralized log, assertion, error, and detail messages for SFM tests."""

SFM_LOG_MSGS: dict[str, str] = {
    "disabled": "SFM integration is disabled in test_config.yml",
    "omnia_pods_check": "Checking required Omnia VictoriaMetrics workloads and pods",
    "omnia_pods_passed": "Required Omnia VictoriaMetrics workloads and pods are ready",
    "omnia_pods_failed": "Omnia VictoriaMetrics workload or pod verification failed",
    "omnia_services_check": "Checking required Omnia VictoriaMetrics services",
    "omnia_services_passed": "Required Omnia VictoriaMetrics services are ready",
    "omnia_services_failed": "Omnia VictoriaMetrics service verification failed",
    "switch_check": "Checking the complete SFM switch-side Prometheus configuration",
    "switch_passed": "SFM switch-side Prometheus configuration is ready",
    "switch_failed": "SFM switch-side Prometheus configuration failed",
    "observability_check": "Configuring and checking SFM observability Remote Write",
    "observability_passed": "SFM observability Remote Write is configured and healthy",
    "observability_failed": "SFM observability Remote Write configuration failed",
    "metrics_check": "Verifying earliest and latest SFM data in VictoriaMetrics",
    "metrics_passed": (
        "SFM earliest and latest data verified for all {count} metrics"
    ),
    "metrics_failed": "SFM earliest/latest data is incomplete",
    "cleanup_complete": "No SFM pods remaining",
    "cleanup_incomplete": "SFM pods are still present",
}


SFM_ASSERT_MSGS: dict[str, str] = {
    "omnia_pods_failed": (
        "Required Omnia VictoriaMetrics workloads are not ready: {error}\n"
        "HOW TO FIX:\n"
        "  1. Verify VictoriaMetrics is deployed in the telemetry namespace.\n"
        "  2. Inspect vminsert, vmstorage, and vmselect workload events.\n"
        "  3. Run telemetry.yml with --tags external_victoria if export data is missing."
    ),
    "omnia_services_failed": (
        "Required Omnia VictoriaMetrics services are not ready: {error}\n"
        "HOW TO FIX:\n"
        "  1. Inspect vminsert, vmstorage, and vmselect services and endpoints.\n"
        "  2. Confirm the LoadBalancer services have external addresses.\n"
        "  3. Resolve unready VMCluster pods before retrying."
    ),
    "switch_failed": (
        "SFM switch-side Prometheus configuration is not ready: {error}\n"
        "HOW TO FIX:\n"
        "  1. Verify sfm_ssh_ip and all encrypted SFM SSH credentials.\n"
        "  2. Add the verified SFM SSH host key to the runner's known_hosts.\n"
        "  3. Check the SFM Prometheus pod, /etc/hosts mapping, and vminsert port."
    ),
    "observability_failed": (
        "SFM observability Remote Write configuration failed: {error}\n"
        "HOW TO FIX:\n"
        "  1. Verify sfm_api_ip and all encrypted SFM API credentials.\n"
        "  2. Confirm ca.crt is the current VictoriaMetrics server CA.\n"
        "  3. Inspect Observability > Settings > Prometheus Remote Write in SFM.\n"
        "  4. Inspect SFM Prometheus logs for TLS or queue errors."
    ),
    "metrics_failed": (
        "The expected SFM metrics were not verified in VictoriaMetrics: {error}\n"
        "HOW TO FIX:\n"
        "  1. Verify the SFM observability configuration test passes.\n"
        "  2. Confirm the managed switch is producing transceiver DOM metrics.\n"
        "  3. Query VictoriaMetrics for the three expected metric names."
    ),
    "cleanup_incomplete": (
        "SFM pods are still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. Run: kubectl get pods -n telemetry | grep sfm\n"
        "  2. Re-run cleanup with the cleanup_sfm tag"
    ),
}


SFM_ERROR_MSGS: dict[str, str] = {
    "config_missing": "Required SFM test setting is empty: {field}",
    "config_invalid": "Invalid SFM test setting {field}: {value}",
    "credential_missing": "Required encrypted SFM credential is empty: {field}",
    "export_read_failed": "Unable to read Victoria export artifact: {path}",
    "export_yaml_invalid": "Victoria connection details YAML is invalid: {error}",
    "export_value_missing": "Victoria connection detail is missing: {field}",
    "export_url_mismatch": "Unexpected SFM Remote Write URL in Victoria export: {url}",
    "export_ip_invalid": "Invalid vminsert address in Victoria export: {value}",
    "certificate_invalid": "Victoria CA certificate is not a valid PEM certificate",
    "certificate_not_current": (
        "Victoria CA certificate is outside its validity window "
        "({not_before} to {not_after})"
    ),
    "playbook_failed": "external_victoria playbook failed: {error}",
    "omnia_export_failed": "Victoria export prerequisite failed: {error}",
    "k8s_resource_read_failed": "Unable to read Kubernetes resource: {resource}",
    "k8s_json_invalid": "Kubernetes resource {resource} returned invalid JSON: {error}",
    "k8s_shape_invalid": "Kubernetes resource has an invalid shape: {resource}",
    "omnia_workloads_unready": "Unready Omnia workloads: {components}",
    "omnia_services_unready": "Unready Omnia services: {components}",
    "ssh_connect_failed": "Unable to connect to the SFM SSH console: {error}",
    "ssh_jump_unavailable": "The OIM SSH jump transport is unavailable",
    "ssh_menu_failed": "Unable to enter the SFM Secure Shell: {error}",
    "ssh_shell_probe_failed": (
        "SFM Secure Shell validation did not return the expected marker"
    ),
    "ssh_command_failed": "SFM Secure Shell command failed: {error}",
    "ssh_command_timeout": "SFM Secure Shell command timed out",
    "ssh_rc_missing": "SFM Secure Shell command did not return an exit status",
    "pods_json_invalid": "SFM pod response is not valid JSON: {error}",
    "pods_shape_invalid": "SFM pod response has an invalid Kubernetes shape",
    "pod_missing": "No ready SFM Prometheus pod was found in {namespace}",
    "hosts_read_failed": "Unable to read /etc/hosts from {pod}: {error}",
    "hosts_write_failed": "Unable to update /etc/hosts in {pod}: {error}",
    "hosts_verify_failed": "The expected vminsert mapping is absent after update",
    "network_check_failed": (
        "SFM Prometheus pod {pod} cannot resolve or reach vminsert: {error}"
    ),
    "api_request_failed": "SFM API request failed for {path}: {error}",
    "api_http_failed": "SFM API returned HTTP {status} for {path}: {body}",
    "api_json_invalid": "SFM API returned invalid JSON for {path}: {error}",
    "api_token_missing": "SFM login response did not contain an access token",
    "api_rows_invalid": "SFM Remote Write list response has an invalid shape",
    "api_duplicate_target": "Multiple SFM Remote Write targets are named {target}",
    "api_target_auth_conflict": (
        "Refusing to modify SFM target {target} with authorization type "
        "{authorization}; its unreadable OAuth secret cannot be rolled back"
    ),
    "api_id_missing": "SFM API response did not contain {field}",
    "api_id_mismatch": "SFM API returned an unexpected {field}: {value}",
    "api_import_id_ambiguous": (
        "SFM created a certificate import without returning ImportId; inspect "
        "SFM for an orphan import named victoria before retrying"
    ),
    "api_readback_missing": "SFM Remote Write target was absent after configuration",
    "api_readback_mismatch": "SFM Remote Write readback differs: {fields}",
    "api_certificate_mismatch": "SFM server certificate filename is {filename}",
    "api_import_still_referenced": (
        "Certificate import {import_id} is still referenced after target rollback"
    ),
    "api_rollback_failed": "SFM configuration failed and rollback was incomplete: {error}",
    "api_rollback_readback_failed": (
        "SFM target rollback could not be verified by API readback"
    ),
    "api_query_failed": "SFM Prometheus range query returned a failed status",
    "api_query_shape_invalid": "SFM Prometheus range query has an invalid response shape",
    "health_prerequisite_failed": (
        "SFM pod network prerequisite failed before health verification: {error}"
    ),
    "health_query_failed": "SFM Remote Write health query failed: {error}",
    "remote_write_unhealthy": (
        "Remote Write did not become healthy after {attempts} attempts: {reason}"
    ),
    "vm_endpoint_missing": "VictoriaMetrics vmselect endpoint is unavailable",
    "vm_query_failed": "VictoriaMetrics range query failed: {query}",
    "vm_query_json_invalid": "VictoriaMetrics returned invalid JSON: {error}",
    "vm_query_shape_invalid": "VictoriaMetrics range query returned an invalid shape",
    "vm_expected_metrics_missing": "Missing SFM metrics in VictoriaMetrics: {metrics}",
    "vm_common_identity_missing": (
        "The three SFM metrics do not share one switch and interface series"
    ),
    "vm_metrics_stale": "Stale SFM metrics in VictoriaMetrics: {metrics}",
    "vm_metrics_unknown_failure": "SFM metric verification failed without a result",
}


SFM_DETAIL_MSGS: dict[str, str] = {
    "disabled": "SFM integration is disabled in test_config.yml",
    "not_available": "-",
    "export_ready": (
        "  \u2713 Details: {details_path}\n  \u2713 CA: {ca_path}\n"
        "  \u2713 vminsert: {vminsert_ip}\n"
        "  \u2713 vmselect: {vmselect_ip}\n"
        "  \u2713 Remote Write: {remote_write_url}\n"
        "Playbook run: {playbook_ran}"
    ),
    "omnia_pods_ready": (
        "Namespace: {namespace}\nExternal Victoria playbook run: {playbook_ran}\n"
        "Workload status:\n{workloads}"
    ),
    "omnia_workload_line": (
        "  {status_icon} {component}: {kind}/{name} desired={desired_replicas}, "
        "ready={ready_replicas}, pods={ready_pods}/{pod_count}"
    ),
    "omnia_services_ready": "Namespace: {namespace}\nService status:\n{services}",
    "omnia_service_line": (
        "  {status_icon} {component}: service/{name} type={service_type}, "
        "ports={ports}, "
        "external={external}, endpoints={ready_endpoints} ready/"
        "{not_ready_endpoints} not-ready"
    ),
    "switch_ready": (
        "Namespace: {namespace}\n"
        "  \u2713 Prometheus pod: {pod}\n"
        "      - container: {container}\n"
        "      - ready pods: {ready_count}\n"
        "  \u2713 Mapping: {vminsert_ip} {hostname}\n"
        "      - action: {action}\n"
        "  \u2713 Network: {hostname}:{port} reachable"
    ),
    "observability_ready": (
        "  \u2713 Prometheus pod: {pod}\n"
        "  \u2713 Remote Write target: {target}\n"
        "      - id: {remote_write_id}\n"
        "      - action: {action}\n"
        "  \u2713 Server certificate: {certificate}\n"
        "      - import id: {import_id}\n"
        "      - CA SHA-256: {fingerprint}\n"
        "  \u2713 Remote Write health\n"
        "      - samples (5m): {samples_total:.2f}\n"
        "      - bytes (5m): {bytes_total:.2f}\n"
        "      - pending: {pending_samples:.2f}\n"
        "      - pending growth: {pending_growth:.2f}\n"
        "      - failed (5m): {failed_samples:.2f}\n"
        "      - retried (5m): {retried_samples:.2f}\n"
        "      - SFM query age: {sample_age:.1f}s{warning}"
    ),
    "certificate_identity_unavailable": (
        "\nCA identity note: SFM exposes only the filename; exact target "
        "configuration and end-to-end health were verified"
    ),
    "old_import_retained": "\nRollback certificate import retained: {import_id}",
    "rollback_import_retained": (
        "Target rollback was not proven; the new certificate import was "
        "retained to avoid breaking an active target: {error}"
    ),
    "rollback_cleanup_failed": (
        "Target rollback succeeded, but new import cleanup failed: {error}"
    ),
    "metrics_ready": (
        "VictoriaMetrics: {vmselect_ip}:{vmselect_port}\n"
        "Expected metrics: {expected_metrics}\n"
        "Found metrics: {found}/{expected}\n"
        "Missing metrics: {missing_metrics}\n"
        "Switch: {switch_id}\nInterface: {interface_name}\n"
        "Series labels: {series_labels}\n"
        "Window: {start_display} to {end_display} ({window_seconds}s)\n\n"
        "Earliest and latest data per metric:\n{metric_results}"
    ),
    "metric_result_line": (
        "    \u2713 {metric} ({series_count} live series)\n"
        "        Earliest: {earliest_display}\n"
        "            - value: {earliest_value}\n"
        "        Latest: {latest_display}\n"
        "            - value: {latest_value}\n"
        "            - age_seconds: {age:.1f}"
    ),
    "health_reason": (
        "samples={samples_total:.2f}, bytes={bytes_total:.2f}, "
        "pending={pending_samples:.2f}, pending_growth={pending_growth:.2f}, "
        "failed={failed_samples:.2f}, sample_age={sample_age:.1f}s"
    ),
}
