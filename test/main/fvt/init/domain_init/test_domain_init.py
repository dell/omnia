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
Omnia Main Init — Domain Init Verification.

TC_IN_002: Verify domain log directories created
TC_IN_003: Verify domain input files staged for image_build_manager
TC_IN_004: Verify domain input files staged for repo_manager
TC_IN_005: Verify domain input files staged for orchestrator
TC_IN_006: Verify domain input files staged for discovery
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import (
    check_domain_log_dirs,
    check_domain_input_staged,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.common_vars import DOMAINS_WITH_INIT


@pytest.mark.sanity
@pytest.mark.order(1)
def test_domain_log_dirs(host):
    """TC_IN_002: Verify domain log directories created."""
    tl = TestLogger(
        TEST_NAMES["domain_log_dirs"], "TC_IN_002"
    )
    result = check_domain_log_dirs(host)

    if result["success"]:
        tl.passed(LOG["log_dirs_ok"].format(
            count=result["details"].split()[0]
        ))
    else:
        missing = result.get("missing", [])
        tl.failed(LOG["log_dirs_missing"].format(
            count=len(missing)
        ))

    assert result["success"], ASSERT["log_dirs_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {d}" for d in result.get("missing", [])
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_domain_input_staged_image_build_manager(host):
    """TC_IN_003: Verify domain input files staged for image_build_manager."""
    domain = "image_build_manager"
    tl = TestLogger(
        TEST_NAMES["domain_input_staged"], "TC_IN_003"
    )
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )
    project = config.get(
        "project_name", "project_default"
    )

    result = check_domain_input_staged(host, domain)

    if result["success"]:
        tl.passed(LOG["input_staged_ok"].format(
            domain=domain,
            count=result["details"].split()[0],
        ))
    else:
        tl.failed(LOG["input_not_staged"].format(
            domain=domain
        ))

    expected_path = (
        f"{data_path}/{domain}/input/{project}"
    )
    assert result["success"], ASSERT["input_not_staged"].format(
        domain=domain,
        path=expected_path,
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_domain_input_staged_repo_manager(host):
    """TC_IN_004: Verify domain input files staged for repo_manager."""
    domain = "repo_manager"
    tl = TestLogger(
        TEST_NAMES["domain_input_staged"], "TC_IN_004"
    )
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )
    project = config.get(
        "project_name", "project_default"
    )

    result = check_domain_input_staged(host, domain)

    if result["success"]:
        tl.passed(LOG["input_staged_ok"].format(
            domain=domain,
            count=result["details"].split()[0],
        ))
    else:
        tl.failed(LOG["input_not_staged"].format(
            domain=domain
        ))

    expected_path = (
        f"{data_path}/{domain}/input/{project}"
    )
    assert result["success"], ASSERT["input_not_staged"].format(
        domain=domain,
        path=expected_path,
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_domain_input_staged_orchestrator(host):
    """TC_IN_005: Verify domain input files staged for orchestrator."""
    domain = "orchestrator"
    tl = TestLogger(
        TEST_NAMES["domain_input_staged_orchestrator"], "TC_IN_005"
    )
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )
    project = config.get(
        "project_name", "project_default"
    )

    result = check_domain_input_staged(host, domain)

    if result["success"]:
        tl.passed(LOG["input_staged_ok"].format(
            domain=domain,
            count=result["details"].split()[0],
        ))
    else:
        tl.failed(LOG["input_not_staged"].format(
            domain=domain
        ))

    expected_path = (
        f"{data_path}/{domain}/input/{project}"
    )
    assert result["success"], ASSERT["input_not_staged"].format(
        domain=domain,
        path=expected_path,
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_domain_input_staged_discovery(host):
    """TC_IN_006: Verify domain input files staged for discovery."""
    domain = "discovery"
    tl = TestLogger(
        TEST_NAMES["domain_input_staged_discovery"], "TC_IN_006"
    )
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )
    project = config.get(
        "project_name", "project_default"
    )

    result = check_domain_input_staged(host, domain)

    if result["success"]:
        tl.passed(LOG["input_staged_ok"].format(
            domain=domain,
            count=result["details"].split()[0],
        ))
    else:
        tl.failed(LOG["input_not_staged"].format(
            domain=domain
        ))

    expected_path = (
        f"{data_path}/{domain}/input/{project}"
    )
    assert result["success"], ASSERT["input_not_staged"].format(
        domain=domain,
        path=expected_path,
    )
