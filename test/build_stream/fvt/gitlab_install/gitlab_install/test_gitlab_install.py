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
Build Stream GitLab Install — Infrastructure Verification.

Validates that --tags gitlab_install created all required resources:
  GitLab packages installed on GitLab server
  GitLab server reachable from OIM
  gitlab-runner container running
  gitlab-runner quadlet file and services
  GitLab URL accessible, services, resources
  puma/sidekiq configuration
  GitLab project, visibility, default branch
  Pipeline files and CI/CD variables
  Domain-segregated CI files (2.3)
  omnia.env and domain input directories in repo
"""

import pytest

from library.functions import (
    TestLogger,
    check_gitlab_packages_installed,
    check_gitlab_server_reachable,
    check_gitlab_runner_container,
    check_gitlab_runner_quadlet,
    check_gitlab_runner_services,
    check_gitlab_url_accessible,
    check_gitlab_services_running,
    check_gitlab_resources,
    check_puma_workers,
    check_sidekiq_concurrency,
    check_gitlab_project_exists,
    check_gitlab_project_visibility,
    check_gitlab_default_branch,
    check_gitlab_repo_file_exists,
    check_gitlab_pipeline_variables,
    check_omnia_env_in_repo,
    check_domain_input_dirs,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    GITLAB_CI_PIPELINE_FILE,
    GITLAB_CI_BUILD_FILE,
    GITLAB_CI_DEPLOY_FILE,
    GITLAB_CI_CLEANUP_FILE,
    GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
    GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_gitlab_packages_installed(host):
    """Verify GitLab packages installed on GitLab server."""
    tc = TC["gitlab_packages_installed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_packages_installed(host)

    if result["success"]:
        tl.passed(LOG["packages_installed"].format(
            packages=", ".join(result["installed"]),
        ))
    else:
        tl.failed(LOG["packages_missing"].format(
            packages=", ".join(result["missing"]),
        ))

    assert result["success"], (
        ASSERT["packages_missing"].format(
            packages=", ".join(result["missing"]),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_gitlab_server_reachable(host):
    """Verify GitLab server reachable from OIM host."""
    tc = TC["gitlab_server_reachable"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_server_reachable(host)

    if result["success"]:
        tl.passed(LOG["server_reachable"].format(
            host=result["gitlab_host"],
        ))
    else:
        tl.failed(LOG["server_unreachable"].format(
            host=result.get("gitlab_host", "unknown"),
        ))

    assert result["success"], (
        ASSERT["server_unreachable"].format(
            host=result.get("gitlab_host", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_gitlab_runner_container(host):
    """Verify gitlab-runner container running on GitLab server."""
    tc = TC["gitlab_runner_container"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_container(host)

    if result["success"]:
        tl.passed(LOG["runner_container_ok"], result["details"])
    else:
        tl.failed(LOG["runner_container_missing"])

    assert result["success"], (
        ASSERT["runner_container_missing"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_gitlab_runner_quadlet_exists(host):
    """Verify gitlab-runner quadlet file exists on GitLab server."""
    tc = TC["gitlab_runner_quadlet_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_quadlet(host)

    if result["success"]:
        tl.passed(LOG["quadlet_exists"].format(path=result["path"]))
    else:
        tl.failed(LOG["quadlet_missing"].format(path=result["path"]))

    assert result["success"], (
        ASSERT["quadlet_missing"].format(path=result["path"])
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_gitlab_runner_services_status(host):
    """Verify GitLab runner services running on GitLab server."""
    tc = TC["gitlab_runner_services_status"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_services(host)

    if result["success"]:
        tl.passed(LOG["runner_services_ok"].format(
            count=result["passed"], total=result["total"],
        ))
    else:
        failed_names = [
            s["name"] for s in result["results"] if not s["is_active"]
        ]
        tl.failed(LOG["runner_services_failed"].format(
            failed=", ".join(failed_names),
        ))

    assert result["success"], (
        ASSERT["runner_services_failed"].format(
            failed=result.get("error", ""),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_gitlab_url_accessible(host):
    """Verify GitLab URL accessible from OIM server."""
    tc = TC["gitlab_url_accessible"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_url_accessible(host)

    if result["success"]:
        tl.passed(LOG["url_accessible"].format(
            url=result["url"], code=result["http_code"],
        ))
    else:
        tl.failed(LOG["url_not_accessible"].format(
            url=result.get("url", "unknown"),
        ))

    assert result["success"], (
        ASSERT["url_not_accessible"].format(
            url=result.get("url", "unknown"),
            code=result.get("http_code", 0),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(7)
def test_gitlab_services_running(host):
    """Verify all GitLab services running via gitlab-ctl status."""
    tc = TC["gitlab_services_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_services_running(host)

    if result["success"]:
        tl.passed(LOG["services_running"].format(
            count=len(result["running"]), total=result["total"],
        ))
    else:
        tl.failed(LOG["services_not_running"].format(
            services=", ".join(result["not_running"]),
        ))

    assert result["success"], (
        ASSERT["services_not_running"].format(
            services=", ".join(result.get("not_running", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(8)
def test_gitlab_resources(host):
    """Verify GitLab server meets minimum resource requirements."""
    tc = TC["gitlab_resources"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_resources(host)

    if result["success"]:
        tl.passed(LOG["resources_ok"], result["details"])
    else:
        failed = [
            k for k, v in result["checks"].items() if not v
        ]
        tl.failed(LOG["resources_insufficient"].format(
            failed=", ".join(failed),
        ))

    assert result["success"], (
        ASSERT["resources_insufficient"].format(
            failed=result.get("error", ""),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(9)
def test_puma_workers(host):
    """Verify puma workers configured correctly in gitlab.rb."""
    tc = TC["puma_workers"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_puma_workers(host)

    if result["success"]:
        tl.passed(LOG["puma_workers_ok"].format(
            actual=result["actual"], expected=result["expected"],
        ))
    else:
        tl.failed(LOG["puma_workers_mismatch"].format(
            actual=result["actual"], expected=result["expected"],
        ))

    assert result["success"], (
        ASSERT["puma_workers_mismatch"].format(
            expected=result["expected"], actual=result["actual"],
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(10)
def test_sidekiq_concurrency(host):
    """Verify sidekiq concurrency configured correctly in gitlab.rb."""
    tc = TC["sidekiq_concurrency"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_sidekiq_concurrency(host)

    if result["success"]:
        tl.passed(LOG["sidekiq_ok"].format(
            actual=result["actual"], expected=result["expected"],
        ))
    else:
        tl.failed(LOG["sidekiq_mismatch"].format(
            actual=result["actual"], expected=result["expected"],
        ))

    assert result["success"], (
        ASSERT["sidekiq_mismatch"].format(
            expected=result["expected"], actual=result["actual"],
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(11)
def test_gitlab_project_exists(host):
    """Verify GitLab project exists."""
    tc = TC["gitlab_project_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_project_exists(host)

    if result["success"]:
        tl.passed(LOG["project_exists"].format(
            name=result["project_name"],
            project_id=result["project_id"],
        ))
    else:
        tl.failed(LOG["project_missing"].format(
            name=result["project_name"],
        ))

    assert result["success"], (
        ASSERT["project_missing"].format(name=result["project_name"])
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(12)
def test_gitlab_project_visibility(host):
    """Verify GitLab project visibility configured correctly."""
    tc = TC["gitlab_project_visibility"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_project_visibility(host)

    if result["success"]:
        tl.passed(LOG["visibility_ok"].format(
            actual=result["actual"], expected=result["expected"],
        ))
    else:
        tl.failed(LOG["visibility_mismatch"].format(
            actual=result.get("actual", "unknown"),
            expected=result["expected"],
        ))

    assert result["success"], (
        ASSERT["visibility_mismatch"].format(
            expected=result["expected"],
            actual=result.get("actual", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(13)
def test_gitlab_default_branch(host):
    """Verify GitLab project default branch configured correctly."""
    tc = TC["gitlab_default_branch"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_default_branch(host)

    if result["success"]:
        tl.passed(LOG["branch_ok"].format(
            actual=result["actual"], expected=result["expected"],
        ))
    else:
        tl.failed(LOG["branch_mismatch"].format(
            actual=result.get("actual", "unknown"),
            expected=result["expected"],
        ))

    assert result["success"], (
        ASSERT["branch_mismatch"].format(
            expected=result["expected"],
            actual=result.get("actual", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(14)
def test_gitlab_pipeline_file_exists(host):
    """Verify .gitlab-ci.yml exists in GitLab project repo."""
    tc = TC["gitlab_pipeline_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_PIPELINE_FILE)

    if result["success"]:
        tl.passed(LOG["pipeline_file_ok"].format(
            file=GITLAB_CI_PIPELINE_FILE,
        ))
    else:
        tl.failed(LOG["pipeline_file_missing"].format(
            file=GITLAB_CI_PIPELINE_FILE,
        ))

    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_PIPELINE_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(15)
def test_gitlab_pipeline_variables(host):
    """Verify GitLab pipeline CI/CD variables configured."""
    tc = TC["gitlab_pipeline_variables"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_pipeline_variables(host)

    if result["success"]:
        tl.passed(LOG["variables_ok"].format(
            count=len(result["found"]), total=result["total"],
        ))
    else:
        tl.failed(LOG["variables_missing"].format(
            missing=", ".join(result["missing"]),
        ))

    assert result["success"], (
        ASSERT["variables_missing"].format(
            missing=", ".join(result.get("missing", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(16)
def test_gitlab_ci_build_file_exists(host):
    """Verify .gitlab-ci-build.yml exists in GitLab repo (2.3)."""
    tc = TC["gitlab_ci_build_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_BUILD_FILE)

    if result["success"]:
        tl.passed(LOG["ci_file_ok"].format(file=GITLAB_CI_BUILD_FILE))
    else:
        tl.failed(LOG["ci_file_missing"].format(
            file=GITLAB_CI_BUILD_FILE,
        ))

    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_BUILD_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(17)
def test_gitlab_ci_deploy_file_exists(host):
    """Verify .gitlab-ci-deploy.yml exists in GitLab repo (2.3)."""
    tc = TC["gitlab_ci_deploy_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_DEPLOY_FILE)

    if result["success"]:
        tl.passed(LOG["ci_file_ok"].format(file=GITLAB_CI_DEPLOY_FILE))
    else:
        tl.failed(LOG["ci_file_missing"].format(
            file=GITLAB_CI_DEPLOY_FILE,
        ))

    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_DEPLOY_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(18)
def test_gitlab_ci_cleanup_file_exists(host):
    """Verify .gitlab-ci-cleanup.yml exists in GitLab repo (2.3)."""
    tc = TC["gitlab_ci_cleanup_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(host, GITLAB_CI_CLEANUP_FILE)

    if result["success"]:
        tl.passed(LOG["ci_file_ok"].format(
            file=GITLAB_CI_CLEANUP_FILE,
        ))
    else:
        tl.failed(LOG["ci_file_missing"].format(
            file=GITLAB_CI_CLEANUP_FILE,
        ))

    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(file=GITLAB_CI_CLEANUP_FILE)
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(19)
def test_gitlab_deploy_child_template_exists(host):
    """Verify deploy child template exists in GitLab repo (2.3)."""
    tc = TC["gitlab_deploy_child_template_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(
        host, GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
    )

    if result["success"]:
        tl.passed(LOG["ci_file_ok"].format(
            file=GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
        ))
    else:
        tl.failed(LOG["ci_file_missing"].format(
            file=GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
        ))

    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(
            file=GITLAB_CI_DEPLOY_CHILD_TEMPLATE,
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(20)
def test_gitlab_cleanup_child_template_exists(host):
    """Verify cleanup child template exists in GitLab repo (2.3)."""
    tc = TC["gitlab_cleanup_child_template_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_repo_file_exists(
        host, GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
    )

    if result["success"]:
        tl.passed(LOG["ci_file_ok"].format(
            file=GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
        ))
    else:
        tl.failed(LOG["ci_file_missing"].format(
            file=GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
        ))

    assert result["success"], (
        ASSERT["pipeline_file_missing"].format(
            file=GITLAB_CI_CLEANUP_CHILD_TEMPLATE,
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(21)
def test_omnia_env_exists(host):
    """Verify omnia.env exists in GitLab repo with required vars (2.3)."""
    tc = TC["omnia_env_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_omnia_env_in_repo(host)

    if result["success"]:
        tl.passed(LOG["omnia_env_ok"])
    else:
        tl.failed(LOG["omnia_env_missing"])

    assert result["success"], (
        ASSERT["omnia_env_missing"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(22)
def test_domain_input_dirs_in_repo(host):
    """Verify domain input directories in GitLab repo (2.3)."""
    tc = TC["domain_input_dirs_in_repo"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_domain_input_dirs(host)

    if result["success"]:
        tl.passed(LOG["domain_dirs_ok"])
    else:
        tl.failed(LOG["domain_dirs_missing"].format(
            missing=", ".join(result.get("missing", [])),
        ))

    assert result["success"], (
        ASSERT["domain_dirs_missing"].format(
            missing=", ".join(result.get("missing", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )
