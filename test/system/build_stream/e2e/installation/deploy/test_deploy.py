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
Installation — Deploy Pipeline Auto-Trigger.

Trigger mode (pipeline.deploy_job_id empty):
  pick the image group (built by the build test, else newest BUILT)
  swap two node rows of input/orchestrator/pxe_mapping_file.csv in GitLab
  verify the push pipeline starts deploy_pipeline
  play the image group's select_image job, then the manual deploy job
Verify-only mode (pipeline.deploy_job_id set to the deployed image group's
build job): nothing is committed.

Both modes then verify, stage by stage:
  deploy -> restart -> validate
  GitLab pipeline finished as success
  image group PASSED with an incremented deploy_count, plus API job view
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    installation_settings,
    load_test_config,
    run_deploy_pipeline,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

_PIPELINE = "deploy"


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.pipeline
@pytest.mark.sanity
@pytest.mark.order(2401)
def test_deploy_pipeline(host):
    """PXE mapping change triggers the deploy pipeline; verify stages and DB."""
    tc = TC["deploy_pipeline"]
    tl = TestLogger(tc["title"], tc["id"])
    settings = installation_settings(load_test_config())
    block = settings[_PIPELINE]
    if block["job_id"]:
        tl.check(LOG["pipeline_mode_verify"].format(job_id=block["job_id"], pipeline=_PIPELINE))
    else:
        tl.check(LOG["pipeline_mode_trigger"].format(pipeline=_PIPELINE))

    result = run_deploy_pipeline(host, settings, tl.info)

    if result["success"]:
        tl.passed_fields(LOG["pipeline_ok"].format(pipeline=_PIPELINE), result["fields"])
    else:
        tl.failed_fields(
            LOG["pipeline_failed"].format(pipeline=_PIPELINE, count=len(result["failures"])),
            [*result["fields"], *(("Failure", item) for item in result["failures"])],
        )
    assert result["success"], ASSERT["deploy_failed"].format(failures=failure_summary(result))
