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
Execute GitLab Project — project, CI/CD files and synced inputs.

Project settings, CI/CD variables, every .gitlab-ci*.yml file,
omnia.env and the domain input directories in the repository.
"""

import pytest

from library.functions import (
    TestLogger,
    check_domain_input_dirs,
    check_gitlab_default_branch,
    check_gitlab_pipeline_variables,
    check_gitlab_project_exists,
    check_gitlab_project_visibility,
    check_gitlab_repo_file_exists,
    check_omnia_env_in_repo,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    GITLAB_CI_BUILD_FILE,
    GITLAB_CI_CADENCE_FILE,
    GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
    GITLAB_CI_CLEANUP_FILE,
    GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
    GITLAB_CI_DEPLOY_FILE,
    GITLAB_CI_PIPELINE_FILE,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(40301)
def test_gitlab_project_exists(host):
    """Verify GitLab project exists."""
    tc = TC["gitlab_project_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_project_exists(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["project_missing"].format(name=result["project_name"])
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40302)
def test_gitlab_project_visibility(host):
    """Verify GitLab project visibility configured correctly."""
    tc = TC["gitlab_project_visibility"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_project_visibility(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["visibility_mismatch"].format(
            expected=result["expected"],
            actual=result.get("actual", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40303)
def test_gitlab_default_branch(host):
    """Verify GitLab project default branch configured correctly."""
    tc = TC["gitlab_default_branch"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_default_branch(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["branch_mismatch"].format(
            expected=result["expected"],
            actual=result.get("actual", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40304)
def test_gitlab_pipeline_variables(host):
    """Verify GitLab pipeline CI/CD variables configured."""
    tc = TC["gitlab_pipeline_variables"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_pipeline_variables(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["variables_missing"].format(
            missing=", ".join(result.get("missing", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40305)
def test_gitlab_pipeline_file_exists(host):
    """Verify .gitlab-ci.yml exists in GitLab project repo."""
    tc = TC["gitlab_pipeline_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_PIPELINE_FILE)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_PIPELINE_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40306)
def test_gitlab_ci_build_file_exists(host):
    """Verify .gitlab-ci-build.yml exists in GitLab repo (2.3)."""
    tc = TC["gitlab_ci_build_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_BUILD_FILE)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_BUILD_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40307)
def test_gitlab_ci_deploy_file_exists(host):
    """Verify .gitlab-ci-deploy.yml exists in GitLab repo (2.3)."""
    tc = TC["gitlab_ci_deploy_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_DEPLOY_FILE)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_DEPLOY_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40308)
def test_gitlab_ci_cleanup_file_exists(host):
    """Verify .gitlab-ci-cleanup.yml exists in GitLab repo (2.3)."""
    tc = TC["gitlab_ci_cleanup_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_CLEANUP_FILE)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_CLEANUP_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40309)
def test_gitlab_ci_cadence_file_exists(host):
    """Verify .gitlab-ci-cadence.yml exists in the GitLab repository."""
    tc = TC["gitlab_ci_cadence_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_CADENCE_FILE)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_CADENCE_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40310)
def test_gitlab_deploy_child_template_exists(host):
    """Verify deploy child template exists in GitLab repo (2.3)."""
    tc = TC["gitlab_deploy_child_template_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(
        host, GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
    )
    report_check(tl, result)
    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(
            file=GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40311)
def test_gitlab_cleanup_child_template_exists(host):
    """Verify cleanup child template exists in GitLab repo (2.3)."""
    tc = TC["gitlab_cleanup_child_template_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(
        host, GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
    )
    report_check(tl, result)
    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(
            file=GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40312)
def test_omnia_env_exists(host):
    """Verify omnia.env exists in GitLab repo with required vars (2.3)."""
    tc = TC["omnia_env_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_omnia_env_in_repo(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["omnia_env_missing"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(40313)
def test_domain_input_dirs_in_repo(host):
    """Verify domain input directories in GitLab repo (2.3)."""
    tc = TC["domain_input_dirs_in_repo"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_domain_input_dirs(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["domain_dirs_missing"].format(
            missing=", ".join(result.get("missing", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )
