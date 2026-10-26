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
Installation — Build Pipeline Auto-Trigger.

Trigger mode (pipeline.build_job_id empty):
  bump the active catalog version to the next unused value
  commit catalog_rhel.json to GitLab
  verify the push pipeline starts build_pipeline and creates a BuildStream job
Verify-only mode (pipeline.build_job_id set): nothing is committed.

Both modes then verify, stage by stage:
  upload -> parse-catalog -> create-local-repository -> build-image
  GitLab pipeline finished as success
  jobs / job_stages / image_groups / images rows and the API job view
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    installation_settings,
    load_test_config,
    run_build_pipeline,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

_PIPELINE = "build"


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.pipeline
@pytest.mark.sanity
@pytest.mark.order(2301)
def test_build_pipeline(host):
    """Catalog version change triggers the build pipeline; verify stages and DB."""
    tc = TC["build_pipeline"]
    tl = TestLogger(tc["title"], tc["id"])
    settings = installation_settings(load_test_config())
    block = settings[_PIPELINE]
    if block["job_id"]:
        tl.check(LOG["pipeline_mode_verify"].format(job_id=block["job_id"], pipeline=_PIPELINE))
    else:
        tl.check(LOG["pipeline_mode_trigger"].format(pipeline=_PIPELINE))

    result = run_build_pipeline(host, settings, tl.info)

    if result["success"]:
        tl.passed_fields(LOG["pipeline_ok"].format(pipeline=_PIPELINE), result["fields"])
    else:
        tl.failed_fields(
            LOG["pipeline_failed"].format(pipeline=_PIPELINE, count=len(result["failures"])),
            [*result["fields"], *(("Failure", item) for item in result["failures"])],
        )
    assert result["success"], ASSERT["build_failed"].format(failures=failure_summary(result))
