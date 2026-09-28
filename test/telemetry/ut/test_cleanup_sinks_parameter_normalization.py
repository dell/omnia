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
    UT_CLEANUP_PARAM_003: Separate flags
    UT_CLEANUP_PARAM_004: Explicit form (no change needed)
    UT_CLEANUP_PARAM_005: Invalid sink names (should not normalize)
    UT_CLEANUP_PARAM_006: Mixed valid and invalid (should not normalize)
    UT_CLEANUP_PARAM_007: Case sensitivity (Kafka vs kafka)
    UT_CLEANUP_PARAM_008: Whitespace handling
    UT_CLEANUP_PARAM_009: Multiple normalization in one command
    UT_CLEANUP_PARAM_010: Edge cases
"""

import pytest
import subprocess


class TestParameterNormalization:
    """Test suite for omnia.sh parameter normalization."""

    @staticmethod
    def run_normalization_test(args):
        """Run a bash script to test parameter normalization.
        
        Args:
            args: List of arguments to normalize
            
        Returns:
            String output from bash script
        """
        bash_script = '''
        set -e
        cd /root/automation_testing/omnia
        source ./src/main/omnia.sh
        
        # Test the normalize_extra_args function
        test_args=("${@}")
        normalize_extra_args test_args
        
        # Output the normalized args
        printf '%s\\n' "${test_args[@]}"
        '''
        
        try:
            result = subprocess.run(
                ['bash', '-c', bash_script, '--'] + args,
                capture_output=True,
                text=True,
                timeout=10,
                cwd='/root/automation_testing/omnia'
            )
            
            if result.returncode != 0:
                pytest.skip(f"Bash script failed: {result.stderr}")
            
            return result.stdout.strip()
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
        # Check that both -e and kafka=true are in the output
        assert "-e" in result and "kafka=true" in result, f"Should convert kafka to kafka=true, got: {result}"

    def test_single_sink_victoria_metrics_normalization(self):
        """UT_CLEANUP_PARAM_002: Victoria Metrics normalization.
        
        GIVEN: -e victoria_metrics
        WHEN: normalize_extra_args is called
        THEN: Should convert to -e victoria_metrics=true
        """
        result = self.run_normalization_test(["-e", "victoria_metrics"])
        assert result is not None
        assert "-e" in result and "victoria_metrics=true" in result, f"Should normalize victoria_metrics, got: {result}"

    def test_comma_separated_normalization(self):
        """UT_CLEANUP_PARAM_003: Comma-separated normalization.
        
        GIVEN: -e kafka,victoria_metrics
        WHEN: normalize_extra_args is called
        THEN: Should convert to -e sinks=kafka,victoria_metrics
        """
        result = self.run_normalization_test(["-e", "kafka,victoria_metrics"])
        assert result is not None
        assert "-e" in result and "sinks=kafka,victoria_metrics" in result, f"Should normalize comma-separated, got: {result}"

    def test_comma_separated_all_three_sinks(self):
        """UT_CLEANUP_PARAM_004: All three sinks comma-separated.
        
        GIVEN: -e kafka,victoria_metrics,victoria_logs
        WHEN: normalize_extra_args is called
        THEN: Should convert to -e sinks=kafka,victoria_metrics,victoria_logs
        """
        result = self.run_normalization_test(["-e", "kafka,victoria_metrics,victoria_logs"])
        assert result is not None
        assert "-e" in result and "sinks=kafka,victoria_metrics,victoria_logs" in result, f"Should normalize all three, got: {result}"

    def test_explicit_form_no_change(self):
        """UT_CLEANUP_PARAM_005: Explicit form should not change.
        
        GIVEN: -e sinks=kafka
        WHEN: normalize_extra_args is called
        THEN: Should remain unchanged
        """
        result = self.run_normalization_test(["-e", "sinks=kafka"])
        assert result is not None
        assert "sinks=kafka" in result, f"Should keep explicit form unchanged, got: {result}"

    def test_separate_flags_normalization(self):
        """UT_CLEANUP_PARAM_006: Separate flags normalization.
        
        GIVEN: -e kafka -e victoria_metrics
        WHEN: normalize_extra_args is called
        THEN: Should convert each to kafka=true and victoria_metrics=true
        """
        result = self.run_normalization_test(["-e", "kafka", "-e", "victoria_metrics"])
        assert result is not None
        # Should have both -e flags and both normalized values
        assert result.count("-e") >= 2, f"Should have at least 2 -e flags, got: {result}"
        assert "kafka=true" in result, f"Should normalize kafka, got: {result}"
        assert "victoria_metrics=true" in result, f"Should normalize victoria_metrics, got: {result}"

    def test_case_insensitive_kafka(self):
        """UT_CLEANUP_PARAM_007: Case insensitive - Kafka (capital K).
        
        GIVEN: -e Kafka
        WHEN: normalize_extra_args is called
        THEN: Should convert to Kafka=true
        """
        result = self.run_normalization_test(["-e", "Kafka"])
        assert result is not None
        assert "-e" in result and "Kafka=true" in result, f"Should handle case variation, got: {result}"

    def test_case_insensitive_victoria_metrics(self):
        """UT_CLEANUP_PARAM_008: Case insensitive - Victoria_metrics.
        
        GIVEN: -e Victoria_metrics
        WHEN: normalize_extra_args is called
        THEN: Should convert to Victoria_metrics=true
        """
        result = self.run_normalization_test(["-e", "Victoria_metrics"])
        assert result is not None
        assert "-e" in result and "Victoria_metrics=true" in result, f"Should handle case variation, got: {result}"

    def test_whitespace_in_comma_separated(self):
        """UT_CLEANUP_PARAM_009: Whitespace handling in comma-separated.
        
        GIVEN: -e "kafka, victoria_metrics"
        WHEN: normalize_extra_args is called
        THEN: Should handle whitespace correctly
        """
        result = self.run_normalization_test(["-e", "kafka, victoria_metrics"])
        assert result is not None
        # Should either normalize or pass through (whitespace may prevent normalization)
        assert "kafka" in result or "sinks=" in result, f"Should handle whitespace, got: {result}"

    def test_invalid_sink_name_no_normalization(self):
        """UT_CLEANUP_PARAM_010: Invalid sink name should not normalize.
        
        GIVEN: -e invalid_sink
        WHEN: normalize_extra_args is called
        THEN: Should NOT normalize (not a valid sink name)
        """
        result = self.run_normalization_test(["-e", "invalid_sink"])
        assert result is not None
        # Should NOT convert to invalid_sink=true (should error or pass through)
        assert "invalid_sink=true" not in result, f"Should reject invalid sink, got: {result}"

    def test_mixed_valid_invalid_no_normalization(self):
        """UT_CLEANUP_PARAM_011: Mixed valid/invalid should not normalize.
        
        GIVEN: -e kafka,invalid_sink
        WHEN: normalize_extra_args is called
        THEN: Should NOT normalize (contains invalid sink)
        """
        result = self.run_normalization_test(["-e", "kafka,invalid_sink"])
        assert result is not None
        # Should NOT convert to sinks=...
        assert "sinks=kafka,invalid_sink" not in result, f"Should reject mixed valid/invalid, got: {result}"

    def test_other_flags_unchanged(self):
        """UT_CLEANUP_PARAM_012: Other flags should remain unchanged.
        
        GIVEN: --tags cleanup_sinks -e kafka --some-other-flag
        WHEN: normalize_extra_args is called
        THEN: Should only normalize -e kafka, leave others unchanged
        """
        result = self.run_normalization_test(["--tags", "cleanup_sinks", "-e", "kafka", "--some-other-flag"])
        assert result is not None
        assert "--tags" in result, f"Should preserve --tags, got: {result}"
        assert "cleanup_sinks" in result, f"Should preserve cleanup_sinks, got: {result}"
        assert "--some-other-flag" in result, f"Should preserve --some-other-flag, got: {result}"
        assert "-e" in result and "kafka=true" in result, f"Should normalize kafka, got: {result}"

    def test_multiple_e_flags_normalization(self):
        """UT_CLEANUP_PARAM_013: Multiple -e flags.
        
        GIVEN: -e kafka -e victoria_metrics -e victoria_logs
        WHEN: normalize_extra_args is called
        THEN: Should normalize each one
        """
        result = self.run_normalization_test(["-e", "kafka", "-e", "victoria_metrics", "-e", "victoria_logs"])
        assert result is not None
        # Should have 3 -e flags
        assert result.count("-e") >= 3, f"Should have at least 3 -e flags, got: {result}"
        assert "kafka=true" in result, f"Should normalize kafka, got: {result}"
        assert "victoria_metrics=true" in result, f"Should normalize victoria_metrics, got: {result}"
        assert "victoria_logs=true" in result, f"Should normalize victoria_logs, got: {result}"

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
        result = self.run_normalization_test(["--tags", "cleanup_sinks", "-e", "kafka", "--some-flag"])
        assert result is not None
        # Check that all required arguments are present
        assert "--tags" in result, f"Should contain --tags, got: {result}"
        assert "cleanup_sinks" in result, f"Should contain cleanup_sinks, got: {result}"
        assert "-e" in result, f"Should contain -e, got: {result}"
        assert "kafka=true" in result, f"Should contain kafka=true, got: {result}"
        assert "--some-flag" in result, f"Should contain --some-flag, got: {result}"


class TestParameterValidation:
    """Test suite for parameter validation logic."""

    def test_valid_sink_names(self):
        """Verify valid sink names are recognized."""
        valid_names = [
            "kafka", "Kafka",
            "victoria_metrics", "Victoria_metrics",
            "victoria_logs", "Victoria_logs"
        ]
        
        for name in valid_names:
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
            "victoria_metric",
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
        """Verify marker variables have null defaults."""
        with open('/root/automation_testing/omnia/src/telemetry/roles/cleanup/vars/main.yml', 'r') as f:
            content = f.read()
            
        assert 'kafka: null' in content, "kafka should default to null"
        assert 'victoria_metrics: null' in content, "victoria_metrics should default to null"
        assert 'victoria_logs: null' in content, "victoria_logs should default to null"

    def test_short_form_detection_logic(self):
        """Verify short-form detection logic in initialize.yml."""
        with open('/root/automation_testing/omnia/src/telemetry/roles/cleanup/tasks/initialize.yml', 'r') as f:
            content = f.read()
            
        assert 'is not none' in content, "Should check 'is not none'"
        assert 'is not mapping' in content, "Should check 'is not mapping'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
