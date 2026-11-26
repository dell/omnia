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
Cleanup External GitLab — customer-managed GitLab (gitlab_mode: external).

What build_stream.yml --tags cleanup removes on an external GitLab (ER-BSM-003):
the Omnia-owned project named in build_stream_config.yml is deleted outright
(taking its CI templates, sample catalogs, input files, CI/CD variables, the
omnia-ci access token and the pipeline trigger with it); the local setup
journal, its lock and the trigger token file are removed from the OIM. What it
must NOT touch: the pre-existing group/namespace, and any GitLab CE packages,
runner, tokens or certificates (those exist only in hosted mode).

Every check only reads state over the GitLab REST API with verified TLS. The
suite is skipped when the input file selects gitlab_mode: hosted.
"""

import pytest

from library.functions import (
    TestLogger,
    check_external_ci_resources_removed,
    check_external_cleanup_local_state_removed,
    check_external_namespace_preserved,
    check_external_project_removed,
    report_check,
)
from library.functions.probe_func import failure_summary
from library.vars import TEST_CASES as TC

pytestmark = pytest.mark.external_only


def _verify(case_key, result):
    """Report one external GitLab cleanup check and assert it passed."""
    tc = TC[case_key]
    tl = TestLogger(tc["title"], tc["id"])
    report_check(tl, result)
    assert result["success"], f"{tc['title']} failed: {failure_summary(result)}"


@pytest.mark.sanity
@pytest.mark.order(90120)
def test_external_cleanup_project_removed(host):
    """Verify the Omnia project was deleted from the external GitLab."""
    _verify("external_cleanup_project_removed", check_external_project_removed(host))


@pytest.mark.sanity
@pytest.mark.order(90121)
def test_external_cleanup_namespace_preserved(host):
    """Verify the pre-existing group/namespace was NOT removed by the cleanup."""
    _verify("external_cleanup_namespace_preserved", check_external_namespace_preserved(host))


@pytest.mark.sanity
@pytest.mark.order(90122)
def test_external_cleanup_ci_resources_removed(host):
    """Verify the omnia-ci token, the Omnia trigger and the Omnia CI/CD variables are gone."""
    _verify("external_cleanup_ci_resources_removed", check_external_ci_resources_removed(host))


@pytest.mark.sanity
@pytest.mark.order(90123)
def test_external_cleanup_local_state_removed(host):
    """Verify the setup journal, its lock and the trigger token file are removed on the OIM."""
    _verify("external_cleanup_local_state_removed",
            check_external_cleanup_local_state_removed(host))
