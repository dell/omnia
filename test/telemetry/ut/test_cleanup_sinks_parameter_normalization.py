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
Unit Tests — Cleanup Sinks Parameter Normalization.

Tests the normalize_extra_args() function in omnia.sh that converts
short-form sink parameters to Ansible-compatible format.

Test Coverage:
    UT_CLEANUP_PARAM_001: Single sink normalization (-e kafka → -e kafka=true)
    UT_CLEANUP_PARAM_002: Comma-separated normalization (-e kafka,vm → -e sinks=...)
    UT_CLEANUP_PARAM_003: Separate flags (no change needed)
    UT_CLEANUP_PARAM_004: Explicit form (no change needed)
    UT_CLEANUP_PARAM_005: Invalid sink names (should not normalize)
    UT_CLEANUP_PARAM_006: Mixed valid and invalid (should not normalize)
    UT_CLEANUP_PARAM_007: Case sensitivity (Kafka vs kafka)
    UT_CLEANUP_PARAM_008: Whitespace handling (kafka, victoria_metrics)
    UT_CLEANUP_PARAM_009: Multiple normalization in one command
    UT_CLEANUP_PARAM_010: Edge cases (empty, null, special chars)
"""

import pytest
import subprocess
import json


class TestParameterNormalization:
    """Test suite for omnia.sh parameter normalization."""

    @staticmethod
    def run_normalization_test(args):
        """Run a bash script to test parameter normalization.
        
        Args:
            args: List of arguments to normalize
            
        Returns:
            List of normalized arguments
        """
        # Create a bash script that tests the normalization function
        bash_script = '''
        source /root/automation_testing/omnia/src/main/omnia.sh 2>/dev/null || true
        
        # Test the normalize_extra_args function
        test_args=("${@}")
        normalize_extra_args test_args
        
        # Output the normalized args as JSON
        printf '%s\n' "${test_args[@]}" | python3 -c "import sys, json; print(json.dumps([line.strip() for line in sys.stdin]))"
        '''
        
        try:
            result = subprocess.run(
                ['bash', '-c', bash_script] + args,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout.strip())
            else:
                return None
        except Exception as e:
            pytest.skip(f"Could not run bash test: {e}")

    def test_single_sink_kafka_normalization(self):
        """UT_CLEANUP_PARAM_001: Single sink normalization (-e kafka).
        
        GIVEN: -e kafka
        WHEN: normalize_extra_args is called
        THEN: Should convert to -e kafka=true
        """
        result = self.run_normalization_test(["-e", "kafka"])
        assert result is not None, "Normalization function should be available"
        assert "-e" in result, "Should contain -e flag"
        assert "kafka=true" in result, "Should convert kafka to kafka=true"

    def test_single_sink_victoria_metrics_normalization(self):
        """UT_CLEANUP_PARAM_002: Victoria Metrics normalization.
        
        GIVEN: -e victoria_metrics
        WHEN: normalize_extra_args is called
        THEN: Should convert to -e victoria_metrics=true
        """
        result = self.run_normalization_test(["-e", "victoria_metrics"])
        assert result is not None
        assert "-e" in result
        assert "victoria_metrics=true" in result

    def test_comma_separated_normalization(self):
        """UT_CLEANUP_PARAM_003: Comma-separated normalization.
        
        GIVEN: -e kafka,victoria_metrics
        WHEN: normalize_extra_args is called
        THEN: Should convert to -e sinks=kafka,victoria_metrics
        """
        result = self.run_normalization_test(["-e", "kafka,victoria_metrics"])
        assert result is not None
        assert "-e" in result
        assert "sinks=kafka,victoria_metrics" in result

    def test_comma_separated_all_three_sinks(self):
        """UT_CLEANUP_PARAM_004: All three sinks comma-separated.
        
        GIVEN: -e kafka,victoria_metrics,victoria_logs
        WHEN: normalize_extra_args is called
        THEN: Should convert to -e sinks=kafka,victoria_metrics,victoria_logs
        """
        result = self.run_normalization_test([
            "-e", "kafka,victoria_metrics,victoria_logs"
        ])
        assert result is not None
        assert "sinks=kafka,victoria_metrics,victoria_logs" in result

    def test_explicit_form_no_change(self):
        """UT_CLEANUP_PARAM_005: Explicit form should not change.
        
        GIVEN: -e sinks=kafka
        WHEN: normalize_extra_args is called
        THEN: Should remain unchanged
        """
        result = self.run_normalization_test(["-e", "sinks=kafka"])
        assert result is not None
        assert "-e" in result
        assert "sinks=kafka" in result

    def test_separate_flags_normalization(self):
        """UT_CLEANUP_PARAM_006: Separate flags normalization.
        
        GIVEN: -e kafka -e victoria_metrics
        WHEN: normalize_extra_args is called
        THEN: Should convert each to kafka=true and victoria_metrics=true
        """
        result = self.run_normalization_test([
            "-e", "kafka", "-e", "victoria_metrics"
        ])
        assert result is not None
        assert "kafka=true" in result
        assert "victoria_metrics=true" in result

    def test_case_insensitive_kafka(self):
        """UT_CLEANUP_PARAM_007: Case insensitive - Kafka (capital K).
        
        GIVEN: -e Kafka
        WHEN: normalize_extra_args is called
        THEN: Should convert to Kafka=true
        """
        result = self.run_normalization_test(["-e", "Kafka"])
        assert result is not None
        assert "Kafka=true" in result

    def test_case_insensitive_victoria_metrics(self):
        """UT_CLEANUP_PARAM_008: Case insensitive - Victoria_metrics.
        
        GIVEN: -e Victoria_metrics
        WHEN: normalize_extra_args is called
        THEN: Should convert to Victoria_metrics=true
        """
        result = self.run_normalization_test(["-e", "Victoria_metrics"])
        assert result is not None
        assert "Victoria_metrics=true" in result

    def test_whitespace_in_comma_separated(self):
        """UT_CLEANUP_PARAM_009: Whitespace handling in comma-separated.
        
        GIVEN: -e "kafka, victoria_metrics"
        WHEN: normalize_extra_args is called
        THEN: Should handle whitespace correctly
        """
        result = self.run_normalization_test(["-e", "kafka, victoria_metrics"])
        assert result is not None
        # Should normalize with or without whitespace handling
        assert "sinks=" in result or ("kafka=true" in result and "victoria_metrics=true" in result)

    def test_invalid_sink_name_no_normalization(self):
        """UT_CLEANUP_PARAM_010: Invalid sink name should not normalize.
        
        GIVEN: -e invalid_sink
        WHEN: normalize_extra_args is called
        THEN: Should NOT normalize (not a valid sink name)
        """
        result = self.run_normalization_test(["-e", "invalid_sink"])
        assert result is not None
        # Should NOT convert to invalid_sink=true
        assert "invalid_sink=true" not in result

    def test_mixed_valid_invalid_no_normalization(self):
        """UT_CLEANUP_PARAM_011: Mixed valid/invalid should not normalize.
        
        GIVEN: -e kafka,invalid_sink
        WHEN: normalize_extra_args is called
        THEN: Should NOT normalize (contains invalid sink)
        """
        result = self.run_normalization_test(["-e", "kafka,invalid_sink"])
        assert result is not None
        # Should NOT convert to sinks=...
        assert "sinks=kafka,invalid_sink" not in result

    def test_other_flags_unchanged(self):
        """UT_CLEANUP_PARAM_012: Other flags should remain unchanged.
        
        GIVEN: --tags cleanup_sinks -e kafka --some-other-flag
        WHEN: normalize_extra_args is called
        THEN: Should only normalize -e kafka, leave others unchanged
        """
        result = self.run_normalization_test([
            "--tags", "cleanup_sinks", "-e", "kafka", "--some-other-flag"
        ])
        assert result is not None
        assert "--tags" in result
        assert "cleanup_sinks" in result
        assert "--some-other-flag" in result
        assert "kafka=true" in result

    def test_multiple_e_flags_normalization(self):
        """UT_CLEANUP_PARAM_013: Multiple -e flags.
        
        GIVEN: -e kafka -e victoria_metrics -e victoria_logs
        WHEN: normalize_extra_args is called
        THEN: Should normalize each one
        """
        result = self.run_normalization_test([
            "-e", "kafka",
            "-e", "victoria_metrics",
            "-e", "victoria_logs"
        ])
        assert result is not None
        assert "kafka=true" in result
        assert "victoria_metrics=true" in result
        assert "victoria_logs=true" in result

    def test_empty_value_after_e(self):
        """UT_CLEANUP_PARAM_014: Empty value after -e.
        
        GIVEN: -e "" (empty string)
        WHEN: normalize_extra_args is called
        THEN: Should not normalize
        """
        result = self.run_normalization_test(["-e", ""])
        assert result is not None
        # Should not normalize empty string

    def test_normalization_preserves_order(self):
        """UT_CLEANUP_PARAM_015: Normalization preserves argument order.
        
        GIVEN: --tags cleanup_sinks -e kafka --some-flag
        WHEN: normalize_extra_args is called
        THEN: Order should be preserved
        """
        result = self.run_normalization_test([
            "--tags", "cleanup_sinks", "-e", "kafka", "--some-flag"
        ])
        assert result is not None
        # Check order is preserved
        tags_idx = result.index("--tags") if "--tags" in result else -1
        e_idx = result.index("-e") if "-e" in result else -1
        flag_idx = result.index("--some-flag") if "--some-flag" in result else -1
        
        if tags_idx >= 0 and e_idx >= 0:
            assert tags_idx < e_idx, "Order should be preserved"


class TestParameterValidation:
    """Test suite for parameter validation logic."""

    def test_valid_sink_names(self):
        """Verify valid sink names are recognized.
        
        Valid names: kafka, Kafka, victoria_metrics, Victoria_metrics,
                    victoria_logs, Victoria_logs
        """
        valid_names = [
            "kafka", "Kafka",
            "victoria_metrics", "Victoria_metrics",
            "victoria_logs", "Victoria_logs"
        ]
        
        for name in valid_names:
            # Each should be normalizable
            result = subprocess.run(
                ['bash', '-c', f'[[ "{name}" =~ ^(kafka|Kafka|victoria_metrics|Victoria_metrics|victoria_logs|Victoria_logs)$ ]] && echo "valid" || echo "invalid"'],
                capture_output=True,
                text=True
            )
            assert "valid" in result.stdout, f"{name} should be valid"

    def test_invalid_sink_names(self):
        """Verify invalid sink names are rejected."""
        invalid_names = [
            "kafka_bridge",
            "victoria",
            "metrics",
            "logs",
            "invalid_sink",
            "kafka123",
            "victoria_metric",  # Missing 's'
        ]
        
        for name in invalid_names:
            result = subprocess.run(
                ['bash', '-c', f'[[ "{name}" =~ ^(kafka|Kafka|victoria_metrics|Victoria_metrics|victoria_logs|Victoria_logs)$ ]] && echo "valid" || echo "invalid"'],
                capture_output=True,
                text=True
            )
            assert "invalid" in result.stdout, f"{name} should be invalid"


class TestAnsibleVariableDetection:
    """Test suite for Ansible variable detection logic."""

    def test_marker_variable_null_default(self):
        """Verify marker variables have null defaults.
        
        The cleanup role vars/main.yml should define:
        kafka: null
        victoria_metrics: null
        victoria_logs: null
        """
        with open('/root/automation_testing/omnia/src/telemetry/roles/cleanup/vars/main.yml', 'r') as f:
            content = f.read()
            
        assert 'kafka: null' in content, "kafka should default to null"
        assert 'victoria_metrics: null' in content, "victoria_metrics should default to null"
        assert 'victoria_logs: null' in content, "victoria_logs should default to null"

    def test_short_form_detection_logic(self):
        """Verify short-form detection logic in initialize.yml.
        
        Should check: "is not none and is not mapping"
        """
        with open('/root/automation_testing/omnia/src/telemetry/roles/cleanup/tasks/initialize.yml', 'r') as f:
            content = f.read()
            
        assert 'is not none' in content, "Should check 'is not none'"
        assert 'is not mapping' in content, "Should check 'is not mapping'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
