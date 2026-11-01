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
Installation — GitLab Repository Verification.

Validates the GitLab catalog project build_stream.yml populated:
  project reachable with the stored token
  the 7 .gitlab-ci*.yml files and omnia.env at the repository root
  every domain input file present on the OIM synced to input/<domain>/
  with identical content (repo_manager, image_build_manager, orchestrator)
Runs before the pipelines, which change catalog_rhel.json and the PXE
mapping in GitLab.
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    verify_gitlab_repository,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


@pytest.mark.svt
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.sanity
@pytest.mark.order(2201)
def test_verify_gitlab_repository_sync(host):
    """Verify the GitLab project holds the CI files, omnia.env and synced inputs."""
    tc = TC["verify_gitlab_repository_sync"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_gitlab_repository(host)

    if result["success"]:
        tl.passed_fields(LOG["repository_ok"], result["fields"])
    else:
        tl.failed_fields(LOG["repository_failed"].format(count=len(result["failures"])),
                         result["fields"])
    assert result["success"], ASSERT["repository_failed"].format(
        failures=failure_summary(result))
