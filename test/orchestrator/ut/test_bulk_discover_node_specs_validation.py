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

"""Unit tests for bulk_discover_node_specs input validation."""

import sys
from pathlib import Path

# Add the module path to sys.path
module_path = Path(__file__).parent.parent.parent.parent / "src" / "orchestrator" / "plugins" / "modules"
sys.path.insert(0, str(module_path))

# Import the validation functions from the module
from bulk_discover_node_specs import (
    _validate_int_value,
    _validate_hostname,
    _discover_single_node,
    VALIDATION_BOUNDS,
)


class TestValidateIntValue:
    """Unit tests for _validate_int_value function."""

    def test_valid_integer_within_bounds(self):
        """Test that valid integers within bounds are returned unchanged."""
        failures = []
        result = _validate_int_value(72, "CoresPerSocket", 1, 160, 72, "node01", failures)
        assert result == 72
        assert len(failures) == 0

    def test_valid_integer_at_min_bound(self):
        """Test that value at minimum bound is accepted."""
        failures = []
        result = _validate_int_value(1, "Sockets", 1, 16, 2, "node01", failures)
        assert result == 1
        assert len(failures) == 0

    def test_valid_integer_at_max_bound(self):
        """Test that value at maximum bound is accepted."""
        failures = []
        result = _validate_int_value(16, "Sockets", 1, 16, 2, "node01", failures)
        assert result == 16
        assert len(failures) == 0

    def test_negative_value_returns_default(self):
        """Test that negative values return default."""
        failures = []
        result = _validate_int_value(-1, "CoresPerSocket", 1, 160, 72, "node01", failures)
        assert result == 72
        assert len(failures) == 1

    def test_zero_value_for_positive_min_returns_default(self):
        """Test that zero returns default when min is 1."""
        failures = []
        result = _validate_int_value(0, "Sockets", 1, 16, 2, "node01", failures)
        assert result == 2
        assert len(failures) == 1

    def test_value_above_max_returns_default(self):
        """Test that values above max return default."""
        failures = []
        result = _validate_int_value(200, "CoresPerSocket", 1, 160, 72, "node01", failures)
        assert result == 72
        assert len(failures) == 1

    def test_string_integer_converts_successfully(self):
        """Test that string representation of integer converts successfully."""
        failures = []
        result = _validate_int_value("72", "CoresPerSocket", 1, 160, 72, "node01", failures)
        assert result == 72
        assert len(failures) == 0

    def test_float_converts_to_int_successfully(self):
        """Test that float converts to int successfully."""
        failures = []
        result = _validate_int_value(72.5, "CoresPerSocket", 1, 160, 72, "node01", failures)
        assert result == 72
        assert len(failures) == 0

    def test_invalid_string_returns_default(self):
        """Test that non-numeric string returns default."""
        failures = []
        result = _validate_int_value("abc", "CoresPerSocket", 1, 160, 72, "node01", failures)
        assert result == 72
        assert len(failures) == 1

    def test_bool_true_converts_to_int(self):
        """Test that bool True converts to int 1."""
        failures = []
        result = _validate_int_value(True, "Sockets", 1, 16, 2, "node01", failures)
        assert result == 1
        assert len(failures) == 0

    def test_bool_false_converts_to_int(self):
        """Test that bool False converts to int 0 (out of bounds)."""
        failures = []
        result = _validate_int_value(False, "Sockets", 1, 16, 2, "node01", failures)
        assert result == 2  # Default because 0 < min
        assert len(failures) == 1

    def test_none_returns_default(self):
        """Test that None returns default."""
        failures = []
        result = _validate_int_value(None, "CoresPerSocket", 1, 160, 72, "node01", failures)
        assert result == 72
        assert len(failures) == 1

    def test_very_large_value_returns_default(self):
        """Test that very large values return default."""
        failures = []
        result = _validate_int_value(9999999999, "RealMemory", 8192, 8000000000, 864000, "node01", failures)
        assert result == 864000
        assert len(failures) == 1

    def test_memory_at_8tb_max(self):
        """Test that 8TB (8000000000 MB) is accepted."""
        failures = []
        result = _validate_int_value(8000000000, "RealMemory", 8192, 8000000000, 864000, "node01", failures)
        assert result == 8000000000
        assert len(failures) == 0

    def test_memory_below_8gb_min_returns_default(self):
        """Test that values below 8GB return default."""
        failures = []
        result = _validate_int_value(4096, "RealMemory", 8192, 8000000000, 864000, "node01", failures)
        assert result == 864000
        assert len(failures) == 1

    def test_gpu_count_zero_accepted(self):
        """Test that GPU count of 0 is accepted."""
        failures = []
        result = _validate_int_value(0, "GPU count", 0, 16, 0, "node01", failures)
        assert result == 0
        assert len(failures) == 0

    def test_gpu_count_16_accepted(self):
        """Test that GPU count of 16 is accepted."""
        failures = []
        result = _validate_int_value(16, "GPU count", 0, 16, 0, "node01", failures)
        assert result == 16
        assert len(failures) == 0

    def test_gpu_count_above_16_returns_default(self):
        """Test that GPU count above 16 returns default."""
        failures = []
        result = _validate_int_value(20, "GPU count", 0, 16, 0, "node01", failures)
        assert result == 0
        assert len(failures) == 1

    def test_threads_per_core_1_accepted(self):
        """Test that threads per core of 1 is accepted."""
        failures = []
        result = _validate_int_value(1, "ThreadsPerCore", 1, 2, 1, "node01", failures)
        assert result == 1
        assert len(failures) == 0

    def test_threads_per_core_2_accepted(self):
        """Test that threads per core of 2 is accepted."""
        failures = []
        result = _validate_int_value(2, "ThreadsPerCore", 1, 2, 1, "node01", failures)
        assert result == 2
        assert len(failures) == 0

    def test_threads_per_core_3_returns_default(self):
        """Test that threads per core above 2 returns default."""
        failures = []
        result = _validate_int_value(3, "ThreadsPerCore", 1, 2, 1, "node01", failures)
        assert result == 1
        assert len(failures) == 1


class TestValidateHostname:
    """Unit tests for _validate_hostname function."""

    def test_valid_hostname_simple(self):
        """Test that simple hostname is valid."""
        assert _validate_hostname("node01") is True

    def test_valid_hostname_with_dots(self):
        """Test that hostname with dots is valid."""
        assert _validate_hostname("node01.example.com") is True

    def test_valid_hostname_with_hyphens(self):
        """Test that hostname with hyphens is valid."""
        assert _validate_hostname("node-01") is True

    def test_valid_hostname_with_underscores(self):
        """Test that hostname with underscores is valid."""
        assert _validate_hostname("node_01") is True

    def test_valid_hostname_mixed(self):
        """Test that hostname with mixed valid characters is valid."""
        assert _validate_hostname("node-01.example.com") is True

    def test_empty_hostname_invalid(self):
        """Test that empty hostname is invalid."""
        assert _validate_hostname("") is False

    def test_none_hostname_invalid(self):
        """Test that None hostname is invalid."""
        assert _validate_hostname(None) is False

    def test_hostname_with_newline_invalid(self):
        """Test that hostname with newline is invalid."""
        assert _validate_hostname("node01\n") is False

    def test_hostname_with_carriage_return_invalid(self):
        """Test that hostname with carriage return is invalid."""
        assert _validate_hostname("node01\r") is False

    def test_hostname_with_equals_invalid(self):
        """Test that hostname with equals sign is invalid."""
        assert _validate_hostname("node01=test") is False

    def test_hostname_with_semicolon_invalid(self):
        """Test that hostname with semicolon is invalid."""
        assert _validate_hostname("node01;test") is False

    def test_hostname_with_ampersand_invalid(self):
        """Test that hostname with ampersand is invalid."""
        assert _validate_hostname("node01&test") is False

    def test_hostname_with_pipe_invalid(self):
        """Test that hostname with pipe is invalid."""
        assert _validate_hostname("node01|test") is False

    def test_hostname_with_dollar_invalid(self):
        """Test that hostname with dollar sign is invalid."""
        assert _validate_hostname("node01$test") is False

    def test_hostname_with_backtick_invalid(self):
        """Test that hostname with backtick is invalid."""
        assert _validate_hostname("node01`test") is False

    def test_hostname_with_parentheses_invalid(self):
        """Test that hostname with parentheses is invalid."""
        assert _validate_hostname("node01(test)") is False

    def test_hostname_with_angle_brackets_invalid(self):
        """Test that hostname with angle brackets is invalid."""
        assert _validate_hostname("node01<test>") is False

    def test_hostname_with_space_invalid(self):
        """Test that hostname with space is invalid."""
        assert _validate_hostname("node 01") is False

    def test_hostname_with_special_chars_invalid(self):
        """Test that hostname with special characters is invalid."""
        assert _validate_hostname("node01@#%^&*") is False


class TestDiscoverSingleNodeUnreachable:
    """Unit tests for _discover_single_node when iDRAC is unreachable."""

    def test_unreachable_node_returns_defaults_and_error(self):
        """Test that unreachable iDRAC returns default node_params and an error."""
        defaults = {
            "real_memory": 864,
            "corespersocket": 72,
            "threadspercore": 1,
            "sockets": 2,
        }
        failures = []
        hostname, node_params, gpus, error = _discover_single_node(
            "testnode", "99.99.99.99", "user", "pass", 5, defaults, failures
        )
        assert hostname == "testnode"
        assert error is not None
        assert "unreachable" in error.lower()
        assert node_params["NodeName"] == "testnode"
        assert node_params["Sockets"] == 2
        assert node_params["CoresPerSocket"] == 72
        assert node_params["ThreadsPerCore"] == 1
        assert node_params["RealMemory"] == 864
        assert gpus == []

    def test_unreachable_node_params_not_empty(self):
        """Test that unreachable node still returns a usable node_params dict."""
        defaults = {
            "real_memory": 512000,
            "corespersocket": 32,
            "threadspercore": 2,
            "sockets": 4,
        }
        failures = []
        hostname, node_params, gpus, error = _discover_single_node(
            "badnode", "99.99.99.99", "user", "pass", 5, defaults, failures
        )
        assert error is not None
        assert isinstance(node_params, dict)
        assert len(node_params) >= 5
        assert node_params["Sockets"] == 4
        assert node_params["CoresPerSocket"] == 32
        assert node_params["ThreadsPerCore"] == 2
        assert node_params["RealMemory"] == 512000


class TestValidationBounds:
    """Unit tests for VALIDATION_BOUNDS constant."""

    def test_sockets_bounds(self):
        """Test that sockets bounds are correct."""
        assert VALIDATION_BOUNDS["sockets"]["min"] == 1
        assert VALIDATION_BOUNDS["sockets"]["max"] == 16

    def test_cores_per_socket_bounds(self):
        """Test that cores per socket bounds are correct."""
        assert VALIDATION_BOUNDS["cores_per_socket"]["min"] == 1
        assert VALIDATION_BOUNDS["cores_per_socket"]["max"] == 160

    def test_threads_per_core_bounds(self):
        """Test that threads per core bounds are correct."""
        assert VALIDATION_BOUNDS["threads_per_core"]["min"] == 1
        assert VALIDATION_BOUNDS["threads_per_core"]["max"] == 2

    def test_real_memory_mb_bounds(self):
        """Test that real memory bounds are correct."""
        assert VALIDATION_BOUNDS["real_memory_mb"]["min"] == 8192  # 8GB
        assert VALIDATION_BOUNDS["real_memory_mb"]["max"] == 8000000000  # 8TB in MB

    def test_gpu_count_bounds(self):
        """Test that GPU count bounds are correct."""
        assert VALIDATION_BOUNDS["gpu_count"]["min"] == 0
        assert VALIDATION_BOUNDS["gpu_count"]["max"] == 16


if __name__ == "__main__":
    # Simple test runner
    import traceback
    
    test_classes = [TestValidateIntValue, TestValidateHostname, TestDiscoverSingleNodeUnreachable, TestValidationBounds]
    failed = 0
    passed = 0
    
    for test_class in test_classes:
        instance = test_class()
        for attr in dir(instance):
            if attr.startswith("test_"):
                test_method = getattr(instance, attr)
                try:
                    test_method()
                    print(f"✓ {test_class.__name__}.{attr}")
                    passed += 1
                except AssertionError as e:
                    print(f"✗ {test_class.__name__}.{attr}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"✗ {test_class.__name__}.{attr}: {e}")
                    traceback.print_exc()
                    failed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
