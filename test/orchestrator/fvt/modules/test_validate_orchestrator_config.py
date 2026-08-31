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
Orchestrator Modules — validate_orchestrator_config Tests.

TC_MO_001: Test validate_orchestrator_config module structure
TC_MO_002: Test validate_orchestrator_config module dependencies
TC_MO_003: Test validate_orchestrator_config module schema validation
"""

import os
import pytest

from library.functions import (
    TestLogger,
    validate_module_structure,
    validate_orchestrator_config_module,
    validate_module_schema,
    check_module_dependencies,
)
from library.vars.common_vars import SRC_ORCHESTRATOR_DIR
from library.messages import (
    TEST_FRAMEWORK_NAMES,
    TEST_FRAMEWORK_LOG_MSGS as LOG,
    TEST_FRAMEWORK_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_module_structure():
    """TC_MO_001: Test validate_orchestrator_config module structure."""
    module_name = "validate_orchestrator_config"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["module_validation"].format(module_name=module_name),
        "TC_MO_001"
    )

    test_data = {
        "input_project_dir": "/opt/omnia/orchestrator/input/project_default",
        "schema_dir": os.path.join(SRC_ORCHESTRATOR_DIR, "plugins", "module_utils", "orchestrator_validation", "schema")
    }

    result = validate_module_structure(module_name, test_data)

    if result["success"]:
        tl.passed(LOG["module_validation_ok"].format(module_name=module_name), result["details"])
    else:
        tl.failed(LOG["module_validation_failed"].format(module_name=module_name), result["error"])

    assert result["success"], ASSERT["module_validation_failed"].format(
        module_name=module_name,
        error=result.get("error", "Unknown error")
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_module_dependencies():
    """TC_MO_002: Test validate_orchestrator_config module dependencies."""
    module_name = "validate_orchestrator_config"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["module_dependencies"].format(module_name=module_name),
        "TC_MO_002"
    )

    result = check_module_dependencies(module_name)

    if result["success"]:
        tl.passed(LOG["module_deps_ok"].format(module_name=module_name), result["details"])
    else:
        missing_deps = result.get("missing_deps", [])
        tl.failed(
            LOG["module_deps_missing"].format(module_name=module_name, deps=missing_deps),
            result["error"]
        )

    assert result["success"], ASSERT["module_import_failed"].format(
        module_name=module_name,
        error=result.get("error", "Missing dependencies")
    )


@pytest.mark.functional
@pytest.mark.order(3)
def test_module_schema_validation():
    """TC_MO_003: Test validate_orchestrator_config module schema validation."""
    module_name = "validate_orchestrator_config"
    schema_file = "orchestrator_config.json"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["module_schema"].format(module_name=module_name),
        "TC_MO_003"
    )

    result = validate_module_schema(module_name, schema_file)

    if result["success"]:
        tl.passed(LOG["module_schema_ok"].format(module_name=module_name), result["details"])
    else:
        tl.failed(LOG["module_schema_failed"].format(module_name=module_name), result["error"])

    assert result["success"], ASSERT["module_validation_failed"].format(
        module_name=module_name,
        error=result.get("error", "Schema validation failed")
    )
