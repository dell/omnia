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

"""Stable test-case IDs for existing Telemetry unit tests."""


def _module_cases(file_name, cases):
    """Build explicit pytest-node-to-test-case-ID mappings for one module."""
    return {
        f"{file_name}::{function_name}": f"TEL_UT_{sequence:03d}"
        for sequence, function_name in cases.items()
    }


# Every sequence is explicit so formatting or reordering cannot renumber a
# published case. Add new cases with the next available sequence.
UT_TEST_CASE_IDS = {
    **_module_cases(
        "test_ome_func.py",
        {
            1: "test_ome_polling_timeouts",
            2: "test_ome_pipeline_context_selects_source_topics",
            3: "test_configure_ome_reconciles_connected_stale_broker",
            4: "test_configure_ome_retries_transient_test_connection",
            5: "test_configure_ome_accepts_spontaneous_reconnection",
            6: "test_configure_ome_stops_on_authentication_error",
            7: "test_configure_ome_stops_on_action_http_403",
            8: "test_configure_ome_stops_at_polling_timeout",
            9: "test_configure_ome_retries_transient_save_failure",
            10: "test_ome_forwarder_actions_require_documented_http_200",
            11: "test_ome_api_values_use_testinfra_quoted_arguments",
            12: "test_ome_pfx_secret_uses_testinfra_quoted_argument",
            13: "test_ome_connectivity_stops_on_empty_http_401",
            14: "test_ome_connectivity_recognizes_body_permission_error",
            15: "test_get_ome_forwarder_config_reads_saved_broker",
            16: "test_external_kafka_details_reject_http_bridge_as_bootstrap",
            17: "test_external_kafka_details_accept_distinct_native_and_rest_endpoints",
            18: "test_external_kafka_playbook_suppresses_live_output",
            19: "test_external_kafka_playbook_reports_only_failure_tail",
            20: "test_ome_topics_retry_until_all_topics_exist",
            21: "test_ome_topics_accepts_expected_subset",
            22: "test_ome_data_retries_for_delayed_records",
        },
    ),
    **_module_cases(
        "test_ome_victoria_func.py",
        {
            23: "test_collect_metric_results_uses_original_sample_timestamps",
            24: "test_collect_metric_results_keeps_metrics_with_identical_labels",
            25: "test_verify_metrics_normalizes_custom_ome_identifier",
            26: "test_verify_logs_skips_when_bridge_is_disabled",
            27: "test_parse_log_timestamp_accepts_iso_and_nanoseconds",
            28: "test_extract_log_fields_returns_readable_key_values",
        },
    ),
}

if len(set(UT_TEST_CASE_IDS.values())) != len(UT_TEST_CASE_IDS):
    raise ValueError("Telemetry UT test-case IDs must be unique")
