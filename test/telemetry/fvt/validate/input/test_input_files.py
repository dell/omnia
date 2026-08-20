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
Telemetry Validate — Input File Verification Tests.

Test cases:
    TC_VL_002: Verify telemetry_config.yml exists on target
    TC_VL_003: Verify telemetry_storage_config.yml exists on target
    TC_VL_004: Verify telemetry_packages.yml exists on target
    TC_VL_005: Verify L1 JSON schema validation passes for all input files
    TC_VL_006: Verify L2 cross-field logic validation passes
"""

import pytest

from omnia_auto import TestLogger, run_playbook, run_on_host

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    TELEMETRY_CONFIG_FILE,
    TELEMETRY_STORAGE_CONFIG_FILE,
    TELEMETRY_PACKAGES_FILE,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.telemetry_func import (
    verify_input_file_exists,
    get_telemetry_input_path,
)


@pytest.mark.sanity
@pytest.mark.order(11)
def test_config_file_exists(host):
    """TC_VL_002: Verify telemetry_config.yml exists on target.

    Checks that the primary telemetry configuration file is present
    at the expected runtime path on the target host.
    """
    tc = TC["config_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking {TELEMETRY_CONFIG_FILE} on target")
    result = verify_input_file_exists(host, TELEMETRY_CONFIG_FILE)

    if result["success"]:
        tl.passed(
            LOG_MSGS["file_exists"].format(
                filename=TELEMETRY_CONFIG_FILE,
                path=result["path"],
            ),
            f"Path: {result['path']}",
        )
    else:
        tl.failed(
            LOG_MSGS["file_missing"].format(
                filename=TELEMETRY_CONFIG_FILE,
                path=result["path"],
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["file_missing"].format(
        filename=TELEMETRY_CONFIG_FILE,
        path=result["path"],
    )


@pytest.mark.sanity
@pytest.mark.order(12)
def test_storage_config_exists(host):
    """TC_VL_003: Verify telemetry_storage_config.yml exists on target.

    Checks that the storage configuration file is present at the
    expected runtime path on the target host.
    """
    tc = TC["storage_config_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking {TELEMETRY_STORAGE_CONFIG_FILE} on target")
    result = verify_input_file_exists(host, TELEMETRY_STORAGE_CONFIG_FILE)

    if result["success"]:
        tl.passed(
            LOG_MSGS["file_exists"].format(
                filename=TELEMETRY_STORAGE_CONFIG_FILE,
                path=result["path"],
            ),
            f"Path: {result['path']}",
        )
    else:
        tl.failed(
            LOG_MSGS["file_missing"].format(
                filename=TELEMETRY_STORAGE_CONFIG_FILE,
                path=result["path"],
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["file_missing"].format(
        filename=TELEMETRY_STORAGE_CONFIG_FILE,
        path=result["path"],
    )


@pytest.mark.sanity
@pytest.mark.order(13)
def test_packages_config_exists(host):
    """TC_VL_004: Verify telemetry_packages.yml exists on target.

    Checks that the packages configuration file is present at the
    expected runtime path on the target host.
    """
    tc = TC["packages_config_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking {TELEMETRY_PACKAGES_FILE} on target")
    result = verify_input_file_exists(host, TELEMETRY_PACKAGES_FILE)

    if result["success"]:
        tl.passed(
            LOG_MSGS["file_exists"].format(
                filename=TELEMETRY_PACKAGES_FILE,
                path=result["path"],
            ),
            f"Path: {result['path']}",
        )
    else:
        tl.failed(
            LOG_MSGS["file_missing"].format(
                filename=TELEMETRY_PACKAGES_FILE,
                path=result["path"],
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["file_missing"].format(
        filename=TELEMETRY_PACKAGES_FILE,
        path=result["path"],
    )


@pytest.mark.sanity
@pytest.mark.order(14)
def test_l1_schema_valid(host):
    """TC_VL_005: Verify L1 JSON schema validation passes for all input files.

    Runs the validate_input module with tag 'telemetry' to perform
    L1 schema validation against:
    - plugins/module_utils/input_validation/schema/telemetry_config.json
    - plugins/module_utils/input_validation/schema/telemetry_storage_config.json
    - plugins/module_utils/input_validation/schema/telemetry_packages.json

    The validation playbook (--tags validate) already runs both L1 and L2.
    This test specifically verifies L1 by running validation and checking
    the output for schema-level errors.
    """
    tc = TC["l1_schema_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running L1 schema validation")
    result = run_playbook(
        host=host,
        playbook=PLAYBOOK_ENTRY_POINT,
        workdir=PLAYBOOK_WORKDIR,
        tag="validate",
    )

    output = result.get("output", "")
    # Check for schema-specific errors
    schema_errors = []
    for line in output.split("\n"):
        lower = line.lower()
        if "schema" in lower and ("error" in lower or "fail" in lower):
            schema_errors.append(line.strip())

    if result["rc"] == 0 and not schema_errors:
        tl.passed(
            LOG_MSGS["l1_valid"],
            "All 3 input files pass JSON schema validation",
        )
    else:
        error_detail = "\n".join(schema_errors[:10]) if schema_errors else (
            f"Validation failed with rc={result['rc']}"
        )
        tl.failed(LOG_MSGS["l1_invalid"], error_detail)

    assert result["rc"] == 0, ASSERT_MSGS["l1_invalid"].format(
        errors="; ".join(schema_errors[:5]) or f"rc={result['rc']}",
    )


@pytest.mark.sanity
@pytest.mark.order(15)
def test_l2_logic_valid(host):
    """TC_VL_006: Verify L2 cross-field logic validation passes.

    L2 validation checks cross-field consistency:
    - kube_vip format and required presence
    - Source/sink enable consistency
    - Storage config presence when sinks are enabled
    - Package URLs when required

    This leverages the same validate playbook run. If TC_VL_005 passed,
    L2 is also validated since the validate playbook runs both levels.
    """
    tc = TC["l2_logic_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running L2 logic validation")
    result = run_playbook(
        host=host,
        playbook=PLAYBOOK_ENTRY_POINT,
        workdir=PLAYBOOK_WORKDIR,
        tag="validate",
    )

    output = result.get("output", "")
    logic_errors = []
    for line in output.split("\n"):
        lower = line.lower()
        if ("logic" in lower or "validation" in lower) and (
            "error" in lower or "fail" in lower
        ):
            logic_errors.append(line.strip())

    if result["rc"] == 0 and not logic_errors:
        tl.passed(
            LOG_MSGS["l2_valid"],
            "Cross-field logic validation passed for all input files",
        )
    else:
        error_detail = "\n".join(logic_errors[:10]) if logic_errors else (
            f"Validation failed with rc={result['rc']}"
        )
        tl.failed(LOG_MSGS["l2_invalid"], error_detail)

    assert result["rc"] == 0, ASSERT_MSGS["l2_invalid"].format(
        errors="; ".join(logic_errors[:5]) or f"rc={result['rc']}",
    )
