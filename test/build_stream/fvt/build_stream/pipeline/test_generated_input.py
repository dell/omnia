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
Build Stream — Generated Input Verification FVT Tests.

After a build pipeline completes the generate-input stage, this test:
1. Clones the Omnia repository (same branch as used by build_stream)
2. Compares generated config files (inside omnia_core container) against
   source configs from the cloned repo
3. Reports mismatches at package level (missing, extra, version drift)

Adapted from automation_v22/molecule/build_stream/test_generated_input.py.
"""

import pytest

from library.functions import (
    TestLogger,
    clone_omnia_repo,
    cleanup_omnia_clone,
    get_software_config,
    verify_generated_inputs,
    is_build_stream_enabled,
)
from library.vars.common_vars import DEFAULT_CLONE_PATH
from library.messages.build_stream_msgs import TEST_NAMES, TEST_LOG_MSGS, SKIP_MSGS


# =============================================================================
# MODULE-LEVEL STATE
# =============================================================================

_gen_input_state = {
    "clone_success": False,
    "clone_path": DEFAULT_CLONE_PATH,
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def gen_input_state():
    """Provide shared generated input state across tests in this module."""
    return _gen_input_state


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.build_stream
@pytest.mark.pipeline
@pytest.mark.generated_input
@pytest.mark.order(250)
class TestGeneratedInput:
    """Verify generated input config files match Omnia source."""

    def test_clone_omnia_repo(self, host, gen_input_state):
        """Clone the Omnia repository for source comparison."""
        log = TestLogger("Clone Omnia Repository")

        if not is_build_stream_enabled(host):
            log.skipped(SKIP_MSGS["build_stream_disabled"])
            pytest.skip(SKIP_MSGS["build_stream_disabled"])

        result = clone_omnia_repo(host, gen_input_state["clone_path"])

        assert result["success"], (
            TEST_LOG_MSGS["clone_fail"].format(error=result["error"])
        )

        gen_input_state["clone_success"] = True

        log.passed(TEST_LOG_MSGS["clone_ok"].format(branch=result["branch"]))

    def test_software_config_readable(self, host, gen_input_state):
        """Verify software_config.json is readable in omnia_core container."""
        log = TestLogger("Read software_config.json")

        if not gen_input_state["clone_success"]:
            log.skipped(SKIP_MSGS["clone_failed"])
            pytest.skip(SKIP_MSGS["clone_failed"])

        result = get_software_config(host)

        assert result["success"], (
            f"Failed to read software_config.json: {result['error']}"
        )

        assert result["os_type"], "cluster_os_type is empty in software_config.json"
        assert result["os_version"], "cluster_os_version is empty in software_config.json"
        assert len(result["softwares"]) > 0, "No softwares found in software_config.json"

        log.passed(
            f"software_config.json: os={result['os_type']}/{result['os_version']}, "
            f"{len(result['softwares'])} software(s)"
        )

    def test_verify_generated_inputs(self, host, gen_input_state):
        """Compare all generated input configs against Omnia source."""
        log = TestLogger(TEST_NAMES.get(
            "verify_generated_inputs", "Verify Generated Input Config Files"
        ))

        if not gen_input_state["clone_success"]:
            log.skipped(SKIP_MSGS["clone_failed"])
            pytest.skip(SKIP_MSGS["clone_failed"])

        result = verify_generated_inputs(
            host, clone_path=gen_input_state["clone_path"]
        )

        # Log the summary regardless of pass/fail
        if result["summary"]:
            for line in result["summary"].split("\n"):
                log.info(line)

        assert result["success"], (
            TEST_LOG_MSGS["generated_inputs_fail"]
            + f"\n{result.get('summary', '')}"
        )

        log.passed(TEST_LOG_MSGS["generated_inputs_ok"])

    def test_cleanup_clone(self, host, gen_input_state):
        """Clean up the cloned Omnia repository."""
        log = TestLogger("Cleanup Omnia Repository Clone")

        cleanup_omnia_clone(host, gen_input_state["clone_path"])

        log.passed(f"Clone removed: {gen_input_state['clone_path']}")
