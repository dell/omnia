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
Repo Manager Execute — Repository Presence Verification.

Validates that --tags execute produced repo_status.yml and
expected repositories are present:
  repo_status.yml exists
  overall_status is success
  slurm_custom repo present (if configured)
  epel repo present (if configured)
  x86_64 base repos present (if configured)
  file repos present (if configured)
"""

import pytest

from library.functions import (
    TestLogger,
    check_repo_status_exists,
    check_repo_status_success,
    check_repo_status_has_repo,
    check_repo_status_has_file_repo,
    check_repo_configured,
    get_repo_status_contexts,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_repo_status_exists(host):
    """Verify repo_status.yml generated."""
    tc = TC["repo_status_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repo_status_exists(host)

    if result["success"]:
        tl.passed(LOG["repo_status_exists"], result["details"])
    else:
        tl.failed(LOG["repo_status_missing"], result["details"])

    assert result["success"], ASSERT["repo_status_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_repo_status_success(host):
    """Verify overall_status is success."""
    tc = TC["repo_status_success"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repo_status_success(host)

    if result["success"]:
        tl.passed(LOG["repo_status_success"], result["details"])
    else:
        tl.failed(LOG["repo_status_failed"], result["details"])

    assert result["success"], ASSERT["repo_status_not_success"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_slurm_custom_repo_present(host):
    """Verify slurm_custom repo present (if configured)."""
    tc = TC["slurm_custom_repo_present"]
    tl = TestLogger(tc["title"], tc["id"])
    # Get execution contexts to determine OS version
    contexts_result = get_repo_status_contexts(host)
    if not contexts_result["success"]:
        tl.failed("Cannot read execution contexts", contexts_result["details"])
        pytest.fail("Cannot verify without execution contexts")

    # Check if slurm_custom is configured in any context
    configured = False
    for os_type, os_version, arch in contexts_result["contexts"]:
        config_result = check_repo_configured(host, "slurm_custom", arch, os_version)
        if config_result["success"]:
            configured = True
            break

    if not configured:
        tl.skipped_fields(
            "Optional repository not configured",
            {
                "Repository": "slurm_custom",
                "Configuration file": "repo_manager_config.yml",
            }
        )
        pytest.skip("slurm_custom not configured in repo_manager_config.yml")

    # Check if slurm_custom exists in repo_status.yml for all contexts
    all_passed = True
    for os_type, os_version, arch in contexts_result["contexts"]:
        result = check_repo_status_has_repo(host, "slurm_custom", arch, os_version)

        if result["success"]:
            tl.passed(LOG["repo_present"].format(repo="slurm_custom"), 
                     f"{os_version}/{arch}: {result['details']}")
        else:
            tl.failed(LOG["repo_missing"].format(repo="slurm_custom"), 
                     f"{os_version}/{arch}: {result['details']}")
            all_passed = False

    assert all_passed, ASSERT["repo_not_found"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(4)
def test_epel_repo_present(host):
    """Verify epel repo present (if configured)."""
    tc = TC["epel_repo_present"]
    tl = TestLogger(tc["title"], tc["id"])
    
    # Get execution contexts to determine OS version
    contexts_result = get_repo_status_contexts(host)
    if not contexts_result["success"]:
        tl.failed("Cannot read execution contexts", contexts_result["details"])
        pytest.fail("Cannot verify without execution contexts")

    # Check if epel is configured in any context
    configured = False
    for os_type, os_version, arch in contexts_result["contexts"]:
        config_result = check_repo_configured(host, "epel", arch, os_version)
        if config_result["success"]:
            configured = True
            break

    if not configured:
        tl.skipped_fields(
            "Optional repository not configured",
            {
                "Repository": "epel",
                "Configuration file": "repo_manager_config.yml",
            }
        )
        pytest.skip("epel not configured in repo_manager_config.yml")

    # Check if epel exists in repo_status.yml for all contexts
    all_passed = True
    for os_type, os_version, arch in contexts_result["contexts"]:
        result = check_repo_status_has_repo(host, "epel", arch, os_version)

        if result["success"]:
            tl.passed(LOG["repo_present"].format(repo="epel"), 
                     f"{os_version}/{arch}: {result['details']}")
        else:
            tl.failed(LOG["repo_missing"].format(repo="epel"), 
                     f"{os_version}/{arch}: {result['details']}")
            all_passed = False

    assert all_passed, ASSERT["repo_not_found"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(5)
def test_x86_64_repos_present(host):
    """Verify x86_64 baseos and appstream present (if configured)."""
    tc = TC["x86_64_repos_present"]
    tl = TestLogger(tc["title"], tc["id"])
    base_repos = ["baseos", "appstream", "codeready-builder"]
    
    # Get execution contexts to determine OS version
    contexts_result = get_repo_status_contexts(host)
    if not contexts_result["success"]:
        tl.failed("Cannot read execution contexts", contexts_result["details"])
        pytest.fail("Cannot verify without execution contexts")

    # Check which base repos are configured in any context
    configured_repos = []
    for os_type, os_version, arch in contexts_result["contexts"]:
        if arch != "x86_64":
            continue
        for repo in base_repos:
            config_result = check_repo_configured(host, repo, arch, os_version)
            if config_result["success"] and repo not in configured_repos:
                configured_repos.append(repo)

    if not configured_repos:
        tl.skipped_fields(
            "Optional repositories not configured",
            {
                "Repositories": "baseos, appstream, codeready-builder",
                "Architecture": "x86_64",
                "Configuration file": "repo_manager_config.yml",
            }
        )
        pytest.skip(
            "No base repos (baseos, appstream, codeready-builder) "
            "configured in repo_manager_config.yml"
        )

    # Check if configured repos exist in repo_status.yml for all x86_64 contexts
    all_passed = True
    for os_type, os_version, arch in contexts_result["contexts"]:
        if arch != "x86_64":
            continue
        for repo in configured_repos:
            result = check_repo_status_has_repo(host, repo, arch, os_version)
            if not result["success"]:
                tl.failed(LOG["repo_missing"].format(repo=repo), 
                         f"{os_version}/{arch}: {result['details']}")
                all_passed = False

    if all_passed:
        tl.passed(f"x86_64 base repos present: {', '.join(configured_repos)}", "")

    assert all_passed, "One or more x86_64 base repos not found in repo_status.yml"


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(6)
def test_file_repos_present(host):
    """Verify file repos (tarball) present (if configured)."""
    tc = TC["file_repos_present"]
    tl = TestLogger(tc["title"], tc["id"])
    
    # Get execution contexts to determine OS version
    contexts_result = get_repo_status_contexts(host)
    if not contexts_result["success"]:
        tl.failed("Cannot read execution contexts", contexts_result["details"])
        pytest.fail("Cannot verify without execution contexts")

    # Check if imb is configured in any context
    configured = False
    for os_type, os_version, arch in contexts_result["contexts"]:
        config_result = check_repo_configured(host, "imb", arch, os_version)
        if config_result["success"]:
            configured = True
            break

    if not configured:
        tl.skipped_fields(
            "Optional repository not configured",
            {
                "Repository": "imb (file repo)",
                "Configuration file": "repo_manager_config.yml",
            }
        )
        pytest.skip("imb file repo not configured in repo_manager_config.yml")

    # Check if imb exists in repo_status.yml for all contexts
    all_passed = True
    for os_type, os_version, arch in contexts_result["contexts"]:
        result = check_repo_status_has_file_repo(host, "imb", arch, os_version)

        if result["success"]:
            tl.passed(LOG["file_repo_present"].format(repo="imb"), 
                     f"{os_version}/{arch}: {result['details']}")
        else:
            tl.failed(LOG["file_repo_missing"].format(repo="imb"), 
                     f"{os_version}/{arch}: {result['details']}")
            all_passed = False

    assert all_passed, ASSERT["repo_not_found"]
