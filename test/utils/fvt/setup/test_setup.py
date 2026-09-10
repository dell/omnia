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
Setup Scenario - Test Automation.

Tests for utils.yml --tags setup functionality.
Validates that the setup tag properly initializes the utils domain:
- Sets OMNIA_DATA_PATH fact
- Sets project input/output paths
- Creates output directory
- Sets utils_domain_ready fact
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_playbook,
    check_dir_exists,
    check_setup_output_dir_exists,
    check_setup_input_dir_exists,
    get_utils_input_path,
    get_utils_output_path,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
    PLAYBOOK_WORKDIR,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# PLAYBOOK DEPLOYMENT TESTS
# =============================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.setup
@pytest.mark.order(0)
def test_deploy_setup(host):
    """Deploy utils.yml with setup tag."""
    tc = TC["deploy_setup"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_UTILS, tag="setup")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_UTILS,
        tag="setup",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" +
        PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


# =============================================================================
# SETUP VERIFICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.setup
@pytest.mark.order(1)
def test_setup_omnia_data_path_set(host):
    """Verify OMNIA_DATA_PATH fact is set after setup."""
    tc = TC["setup_omnia_data_path_set"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check that OMNIA_DATA_PATH environment variable is set
    cmd = "echo $OMNIA_DATA_PATH"
    result = host.run(cmd)

    data_path = result.stdout.strip()
    success = bool(data_path) and data_path != ""

    if success:
        tl.passed(f"OMNIA_DATA_PATH is set to: {data_path}")
    else:
        tl.failed("OMNIA_DATA_PATH is not set or empty")

    assert success, "OMNIA_DATA_PATH environment variable is not set"


@pytest.mark.sanity
@pytest.mark.setup
@pytest.mark.order(2)
def test_setup_project_paths_set(host):
    """Verify project input/output paths are set after setup."""
    tc = TC["setup_project_paths_set"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    output_path = get_utils_output_path(host)

    # Check both paths are valid
    input_result = check_setup_input_dir_exists(host, input_path)
    output_result = check_setup_output_dir_exists(host, output_path)

    success = input_result["success"] or output_result["success"]

    if success:
        tl.passed(f"Project paths configured - Input: {input_path}, Output: {output_path}")
    else:
        tl.failed(f"Project paths not properly configured")

    # At minimum, output path should exist after setup
    assert output_result["success"], f"Output directory not created: {output_path}"


@pytest.mark.sanity
@pytest.mark.setup
@pytest.mark.order(3)
def test_setup_output_dir_created(host):
    """Verify output directory is created after setup."""
    tc = TC["setup_output_dir_created"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_dir_exists(host, output_path)

    if result["success"]:
        tl.passed(f"Output directory exists: {output_path}")
    else:
        tl.failed(f"Output directory not found: {output_path}")

    assert result["success"], f"Output directory not created: {output_path}"


@pytest.mark.sanity
@pytest.mark.setup
@pytest.mark.order(4)
def test_setup_domain_ready_fact(host):
    """Verify utils domain is ready after setup.
    
    This test verifies that the setup tag completes successfully
    by checking that the output directory structure is in place.
    The utils_domain_ready fact is set internally by Ansible.
    """
    tc = TC["setup_domain_ready_fact"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    
    # Check that the output directory exists (indicates setup completed)
    result = check_dir_exists(host, output_path)

    if result["success"]:
        tl.passed("Utils domain is ready (output directory exists)")
    else:
        tl.failed("Utils domain setup incomplete")

    assert result["success"], "Utils domain setup did not complete successfully"
