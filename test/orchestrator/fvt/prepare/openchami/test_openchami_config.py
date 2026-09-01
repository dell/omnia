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
Orchestrator Prepare — OpenCHAMI Configuration File Verification Tests.

TC_PR_004: Verify OpenCHAMI configuration files exist after deployment
TC_PR_005: Verify tokensmith.json configuration file exists
TC_PR_006: Verify PostgreSQL initialization script exists
TC_PR_007: Verify RPM configuration files are not missing
"""

import pytest

from library.functions import (
    TestLogger,
    check_openchami_config_files,
    check_tokensmith_config,
    check_postgres_init_script,
    check_rpm_file_integrity,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(4)
def test_openchami_config_files_exist(host):
    """TC_PR_004: Verify OpenCHAMI configuration files exist after deployment."""
    tl = TestLogger(TEST_NAMES["openchami_config_files"], "TC_PR_004")
    result = check_openchami_config_files(host)

    if result["success"]:
        tl.passed(LOG["config_files_ok"], result["details"])
    else:
        tl.failed(
            LOG["config_files_missing"].format(
                files=result.get("missing_files", [])
            ),
            result["details"],
        )

    assert result["success"], ASSERT["config_files_missing"].format(
        files=result.get("missing_files", [])
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_tokensmith_config_exists(host):
    """TC_PR_005: Verify tokensmith.json configuration file exists."""
    tl = TestLogger(TEST_NAMES["tokensmith_config"], "TC_PR_005")
    result = check_tokensmith_config(host)

    if result["success"]:
        tl.passed(LOG["tokensmith_config_ok"], result["details"])
    else:
        tl.failed(LOG["tokensmith_config_missing"], result["details"])

    assert result["success"], ASSERT["tokensmith_config_missing"]


@pytest.mark.sanity
@pytest.mark.order(6)
def test_postgres_init_script_exists(host):
    """TC_PR_006: Verify PostgreSQL initialization script exists."""
    tl = TestLogger(TEST_NAMES["postgres_init_script"], "TC_PR_006")
    result = check_postgres_init_script(host)

    if result["success"]:
        tl.passed(LOG["postgres_init_script_ok"], result["details"])
    else:
        tl.failed(LOG["postgres_init_script_missing"], result["details"])

    assert result["success"], ASSERT["postgres_init_script_missing"]


@pytest.mark.functional
@pytest.mark.order(7)
def test_rpm_file_integrity(host):
    """TC_PR_007: Verify RPM configuration files are not missing."""
    tl = TestLogger(TEST_NAMES["rpm_file_integrity"], "TC_PR_007")
    result = check_rpm_file_integrity(host)

    if result["success"]:
        tl.passed(LOG["rpm_integrity_ok"], result["details"])
    else:
        tl.failed(
            LOG["rpm_integrity_failed"].format(
                files=result.get("missing_files", [])
            ),
            result["details"],
        )

    assert result["success"], ASSERT["rpm_integrity_failed"].format(
        files=result.get("missing_files", [])
    )
