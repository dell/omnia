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
Orchestrator Playbooks — orchestrator.yml Tests.

TC_PB_001: Test orchestrator.yml playbook exists
TC_PB_002: Test orchestrator.yml playbook syntax
TC_PB_003: Test orchestrator.yml playbook tags
TC_PB_004: Test orchestrator.yml playbook dependencies
"""

import pytest

from library.functions import (
    TestLogger,
    check_playbook_exists,
    check_playbook_syntax,
    get_playbook_tags,
    check_playbook_dependencies,
)
from library.messages import (
    TEST_FRAMEWORK_NAMES,
    TEST_FRAMEWORK_LOG_MSGS as LOG,
    TEST_FRAMEWORK_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_playbook_exists():
    """TC_PB_001: Test orchestrator.yml playbook exists."""
    playbook_name = "orchestrator.yml"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["playbook_exists"].format(playbook_name=playbook_name),
        "TC_PB_001"
    )

    result = check_playbook_exists(playbook_name)

    if result["success"]:
        tl.passed(LOG["playbook_exists_ok"].format(playbook_name=playbook_name), result["details"])
    else:
        tl.failed(LOG["playbook_exists_failed"].format(playbook_name=playbook_name), result["error"])

    assert result["success"], ASSERT["playbook_syntax_failed"].format(
        playbook_name=playbook_name,
        error=result.get("error", "Playbook not found")
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_playbook_syntax():
    """TC_PB_002: Test orchestrator.yml playbook syntax."""
    playbook_name = "orchestrator.yml"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["playbook_syntax"].format(playbook_name=playbook_name),
        "TC_PB_002"
    )

    result = check_playbook_syntax(playbook_name)

    if result["success"]:
        tl.passed(LOG["playbook_syntax_ok"].format(playbook_name=playbook_name), result["details"])
    else:
        tl.failed(LOG["playbook_syntax_failed"].format(playbook_name=playbook_name), result["error"])

    assert result["success"], ASSERT["playbook_syntax_failed"].format(
        playbook_name=playbook_name,
        error=result.get("error", "Syntax validation failed")
    )


@pytest.mark.functional
@pytest.mark.order(3)
def test_playbook_tags():
    """TC_PB_003: Test orchestrator.yml playbook tags."""
    playbook_name = "orchestrator.yml"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["playbook_tags"].format(playbook_name=playbook_name),
        "TC_PB_003"
    )

    result = get_playbook_tags(playbook_name)

    if result["success"]:
        tags = result.get("tags", [])
        tl.passed(
            LOG["playbook_tags_ok"].format(playbook_name=playbook_name, count=len(tags), tags=tags),
            f"Available tags: {tags}"
        )
    else:
        tl.failed(LOG["playbook_syntax_failed"].format(playbook_name=playbook_name), result["error"])

    assert result["success"], ASSERT["playbook_syntax_failed"].format(
        playbook_name=playbook_name,
        error=result.get("error", "Failed to extract tags")
    )


@pytest.mark.functional
@pytest.mark.order(4)
def test_playbook_dependencies():
    """TC_PB_004: Test orchestrator.yml playbook dependencies."""
    playbook_name = "orchestrator.yml"
    tl = TestLogger(
        TEST_FRAMEWORK_NAMES["playbook_dependencies"].format(playbook_name=playbook_name),
        "TC_PB_004"
    )

    result = check_playbook_dependencies(playbook_name)

    if result["success"]:
        deps = result.get("dependencies", [])
        tl.passed(
            LOG["playbook_deps_ok"].format(playbook_name=playbook_name),
            f"Dependencies: {len(deps)} found"
        )
    else:
        tl.failed(LOG["playbook_deps_failed"].format(playbook_name=playbook_name), result["error"])

    assert result["success"], ASSERT["playbook_syntax_failed"].format(
        playbook_name=playbook_name,
        error=result.get("error", "Dependency check failed")
    )
