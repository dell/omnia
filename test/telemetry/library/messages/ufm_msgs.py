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

"""Centralized log, assertion, error, and detail messages for UFM tests."""

UFM_LOG_MSGS = {
    "disabled": "UFM source is not enabled in telemetry_config.yml",
    "service_check": "Verifying UFM external headless service",
    "service_exists": (
        "UFM external service '{service}' exists with endpoint "
        "{endpoint_ip}:{endpoint_port}"
    ),
    "service_missing": "UFM external service '{service}' not found",
    "vmscrape_check": "Checking UFM VMServiceScrape resource",
    "vmscrape_exists": "UFM VMServiceScrape '{name}' exists",
    "vmscrape_missing": "UFM VMServiceScrape '{name}' not found",
    "secret_check": "Checking UFM credentials secret",
    "secret_exists": "UFM credentials secret '{secret}' exists",
    "secret_missing": "UFM credentials secret '{secret}' not found",
    "metrics_check": "Querying VictoriaMetrics for UFM InfiniBand metrics",
    "metrics_found": (
        "All {count} UFM metrics have live samples in VictoriaMetrics"
    ),
    "metrics_missing": "UFM live metric verification is incomplete",
    "cleanup_complete": "No UFM resources remaining",
    "cleanup_incomplete": "UFM resources still present",
}


UFM_ASSERT_MSGS = {
    "service_missing": (
        "UFM external service '{service}' was not verified\n"
        "HOW TO FIX:\n"
        "  1. Run: kubectl get svc -n telemetry | grep ufm\n"
        "  2. Re-run telemetry deploy with UFM enabled"
    ),
    "vmscrape_missing": (
        "UFM VMServiceScrape '{name}' was not verified\n"
        "HOW TO FIX:\n"
        "  1. Run: kubectl get vmservicescrape -n telemetry | grep ufm\n"
        "  2. Re-run telemetry deploy with UFM enabled"
    ),
    "secret_missing": (
        "UFM credentials secret '{secret}' was not verified\n"
        "HOW TO FIX:\n"
        "  1. Run: kubectl get secret -n telemetry | grep ufm\n"
        "  2. Re-run telemetry deploy with UFM credentials"
    ),
    "metrics_missing": (
        "UFM metrics do not have live samples in VictoriaMetrics: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Check vmagent scrape targets for UFM.\n"
        "  2. Verify the UFM metrics endpoint is reachable.\n"
        "  3. Inspect the vmagent logs in the telemetry namespace."
    ),
    "cleanup_incomplete": (
        "UFM resources still present after cleanup\n"
        "HOW TO FIX:\n"
        "  1. Run: kubectl get svc,vmservicescrape,secret -n telemetry | grep ufm\n"
        "  2. Re-run cleanup with the cleanup_ufm tag"
    ),
}


UFM_ERROR_MSGS = {
    "service_not_found": "UFM external service was not found",
    "service_json_invalid": "UFM external service returned invalid JSON",
    "endpoints_json_invalid": "UFM external endpoints returned invalid JSON",
    "vmscrape_not_found": "UFM VMServiceScrape resource was not found",
    "vmscrape_json_invalid": "UFM VMServiceScrape returned invalid JSON",
    "secret_not_found": "UFM credentials secret was not found",
    "secret_json_invalid": "UFM credentials secret returned invalid JSON",
}


UFM_DETAIL_MSGS = {
    "service": (
        "Endpoint: {endpoint_ip}:{endpoint_port}\n"
        "Expected: {expected_endpoint}:{expected_port}"
    ),
    "vmscrape": (
        "Port: {port}\nPath: {path}\nScrape interval: {scrape_interval}"
    ),
    "secret": "Keys: {keys}",
    "failure": "{details}\nError: {error}",
    "metrics": (
        "Expected metrics: {expected_count}\n"
        "Found metrics: {found_count}/{expected_count}\n"
        "Missing metrics: {missing_metrics}\n\n"
        "UFM metric data:\n{metric_results}"
    ),
    "metric_found": (
        "  \u2713 {metric} ({sample_count} live samples)\n"
        "      - value: {value}\n"
        "      - timestamp: {timestamp_utc}"
    ),
    "metric_missing": "  \u2717 {metric}: {reason}",
    "metric_name_missing": "MISSING",
    "metric_sample_missing": "NO LIVE SAMPLE",
}
