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
Precheck Credentials — prerequisite credential stores and domain files.

The repo_manager and image_build_manager credential files must exist,
as build_stream.yml --tags precheck requires. Per domain (repo_manager,
image_build_manager, orchestrator) the credential store, its vault key and
every input file build_stream.yml --tags execute uploads to GitLab must
exist: the upload skips a missing file silently and the pipelines then fail.
"""

import pytest

from library.functions import (
    TestLogger,
    check_precheck_credentials,
    check_precheck_domain_files,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(20301)
def test_precheck_credentials(host):
    """Verify the prerequisite credential stores exist."""
    tc = TC["precheck_credentials"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_credentials(host)
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="prerequisite credentials", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(20302)
def test_precheck_repo_manager_files(host):
    """Verify the repo_manager credential store, vault key and GitLab input files."""
    tc = TC["precheck_repo_manager_files"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_domain_files(host, "repo_manager")
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="repo_manager files", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(20303)
def test_precheck_image_build_manager_files(host):
    """Verify the image_build_manager credential store, vault key and GitLab input files."""
    tc = TC["precheck_image_build_manager_files"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_domain_files(host, "image_build_manager")
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="image_build_manager files", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(20304)
def test_precheck_orchestrator_files(host):
    """Verify the orchestrator credential store, vault key and GitLab input files."""
    tc = TC["precheck_orchestrator_files"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_domain_files(host, "orchestrator")
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="orchestrator files", error=result["error"],
    )
