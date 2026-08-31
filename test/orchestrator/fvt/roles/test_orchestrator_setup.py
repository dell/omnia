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
Orchestrator Roles — orchestrator_setup Tests.

TC_RO_001: Test orchestrator_setup role structure
TC_RO_002: Test orchestrator_setup role tasks
TC_RO_003: Test orchestrator_setup role metadata
TC_RO_004: Test orchestrator_setup role syntax
"""

import pytest

from library.functions import (
    TestLogger,
    check_role_structure,
    check_role_tasks,
    check_role_metadata,
    validate_role_syntax,
)
from library.messages import (
    TEST_FRAMEWORK_NAMES,
    TEST_FRAMEWORK_LOG_MSGS as LOG,
    TEST_FRAMEWORK_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_role_structure():
    """TC_RO_001: Test orchestrator_setup role structure."""
    role_name = "orchestrator_setup"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["role_structure"].format(role_name=role_name),
        "TC_RO_001"
    )

    result = check_role_structure(role_name)

    if result["success"]:
        tl.passed(LOG["role_structure_ok"].format(role_name=role_name), result["details"])
    else:
        missing_dirs = result.get("missing_dirs", [])
        tl.failed(
            LOG["role_structure_failed"].format(role_name=role_name, missing_dirs=missing_dirs),
            result["error"]
        )

    assert result["success"], ASSERT["role_structure_failed"].format(
        role_name=role_name,
        missing_dirs=result.get("missing_dirs", [])
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_role_tasks():
    """TC_RO_002: Test orchestrator_setup role tasks."""
    role_name = "orchestrator_setup"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["role_tasks"].format(role_name=role_name),
        "TC_RO_002"
    )

    result = check_role_tasks(role_name)

    if result["success"]:
        task_files = result.get("task_files", [])
        tl.passed(
            LOG["role_tasks_ok"].format(role_name=role_name),
            f"Task files: {task_files}"
        )
    else:
        tl.failed(LOG["role_tasks_failed"].format(role_name=role_name), result["error"])

    assert result["success"], ASSERT["role_tasks_failed"].format(
        role_name=role_name,
        error=result.get("error", "Invalid tasks")
    )


@pytest.mark.functional
@pytest.mark.order(3)
def test_role_metadata():
    """TC_RO_003: Test orchestrator_setup role metadata."""
    role_name = "orchestrator_setup"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["role_metadata"].format(role_name=role_name),
        "TC_RO_003"
    )

    result = check_role_metadata(role_name)

    if result["success"]:
        metadata = result.get("metadata", {})
        tl.passed(
            LOG["role_metadata_ok"].format(role_name=role_name),
            f"Metadata: {metadata.get('description', 'N/A')}"
        )
    else:
        tl.failed(LOG["role_metadata_failed"].format(role_name=role_name), result["error"])

    assert result["success"], ASSERT["role_structure_failed"].format(
        role_name=role_name,
        error=result.get("error", "Invalid metadata")
    )


@pytest.mark.functional
@pytest.mark.order(4)
def test_role_syntax():
    """TC_RO_004: Test orchestrator_setup role syntax."""
    role_name = "orchestrator_setup"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["role_syntax"].format(role_name=role_name),
        "TC_RO_004"
    )

    result = validate_role_syntax(role_name)

    if result["success"]:
        tl.passed(LOG["role_syntax_ok"].format(role_name=role_name), result["details"])
    else:
        tl.failed(LOG["role_syntax_failed"].format(role_name=role_name), result["error"])

    assert result["success"], ASSERT["role_syntax_failed"].format(
        role_name=role_name,
        error=result.get("error", "Syntax validation failed")
    )
