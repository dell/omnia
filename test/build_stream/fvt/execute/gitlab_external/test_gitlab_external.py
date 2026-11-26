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
Execute GitLab External — customer-managed GitLab (gitlab_mode: external).

What build_stream.yml --tags execute leaves on an external GitLab (ER-BSM-003):
credentials, CA bundle, GitLab version, token and group role, the Omnia project,
the operator-provided runner, the omnia-ci access token, the trigger, the CI/CD
variables and the setup journal. Every check only reads state over the GitLab
REST API with verified TLS. The suite is skipped when the input file selects
gitlab_mode: hosted.
"""

import pytest

from library.functions import (
    TestLogger,
    check_external_ca_bundle,
    check_external_ci_token,
    check_external_credentials,
    check_external_gitlab_api,
    check_external_journal,
    check_external_project,
    check_external_runner,
    check_external_trigger_and_variables,
    load_test_config,
    report_check,
)
from library.functions.probe_func import failure_summary
from library.vars import TEST_CASES as TC

pytestmark = pytest.mark.external_only


def _verify(case_key, result):
    """Report one external GitLab check and assert it passed."""
    tc = TC[case_key]
    tl = TestLogger(tc["title"], tc["id"])
    report_check(tl, result)
    assert result["success"], f"{tc['title']} failed: {failure_summary(result)}"


@pytest.mark.sanity
@pytest.mark.order(41201)
def test_external_credentials(host):
    """Verify gitlab_api_token is stored and gitlab_project_id is persisted."""
    _verify("external_credentials", check_external_credentials(host))


@pytest.mark.sanity
@pytest.mark.order(41202)
def test_external_ca_bundle(host):
    """Verify gitlab_ca_cert_path is a root-owned PEM certificate bundle."""
    _verify("external_ca_bundle", check_external_ca_bundle(host))


@pytest.mark.sanity
@pytest.mark.order(41203)
def test_external_gitlab_api(host):
    """Verify GitLab 17-19, token scopes and expiry and the group role over verified TLS."""
    days = (load_test_config().get("gitlab") or {}).get("token_min_days_remaining", 30)
    _verify("external_gitlab_api", check_external_gitlab_api(host, days))


@pytest.mark.sanity
@pytest.mark.order(41204)
def test_external_project(host):
    """Verify the Omnia project, its ownership marker, visibility and protected branch."""
    _verify("external_project", check_external_project(host))


@pytest.mark.sanity
@pytest.mark.order(41205)
def test_external_runner(host):
    """Verify an online operator-provided runner and its user_provided journal entry."""
    _verify("external_runner", check_external_runner(host))


@pytest.mark.sanity
@pytest.mark.order(41206)
def test_external_ci_token(host):
    """Verify the omnia-ci project access token."""
    _verify("external_ci_token", check_external_ci_token(host))


@pytest.mark.sanity
@pytest.mark.order(41207)
def test_external_trigger_variables(host):
    """Verify the pipeline trigger, its token file and the CI/CD variables."""
    _verify("external_trigger_variables", check_external_trigger_and_variables(host))


@pytest.mark.sanity
@pytest.mark.order(41208)
def test_external_journal(host):
    """Verify the setup journal is private, complete and free of secrets."""
    _verify("external_journal", check_external_journal(host))
