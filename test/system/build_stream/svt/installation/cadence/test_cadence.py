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
Installation — Cadence Pipeline.

Trigger mode (pipeline.cadence_job_id empty):
  playbook-watcher active, cadence.enabled true, trigger script present
  upload the installation.catalog catalog to GitLab cadence_catalog_rhel.json
  with [skip ci] (no pipeline), one minor below the next unused version
  run trigger_cadence.sh (SIGUSR1; the command is printed) instead of
  waiting for the interval; every cadence journal record is printed
  follow the playbook-watcher journal: cycle start, GitLab catalog fetch,
  repo sync submitted/succeeded (or failed), catalog bump, GitLab commit
  verify cadence_catalog_rhel.json was committed with the bumped version
  verify the commit started cadence_pipeline and created a BuildStream job
Verify-only mode (pipeline.cadence_job_id set): nothing is triggered.

Both modes then verify, stage by stage:
  upload -> parse-catalog -> create-local-repository -> build-image
  -> deploy -> restart -> validate
  GitLab pipeline finished as success; image group PASSED; API job view
"""

import pytest

from library.functions import (
    TestLogger,
    failure_fields,
    failure_summary,
    installation_settings,
    is_cadence_enabled,
    load_test_config,
    run_cadence_pipeline,
    skip_test,
)
from library.functions.api_func import load_bsm_context
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

_PIPELINE = "cadence"


@pytest.mark.svt
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(2501)
def test_cadence_pipeline_trigger_and_verify(host):
    """Cadence trigger syncs repos, commits the catalog and runs the pipeline."""
    tc = TC["cadence_pipeline_trigger_and_verify"]
    tl = TestLogger(tc["title"], tc["id"])
    settings = installation_settings(load_test_config())
    block = settings[_PIPELINE]

    # Independent of the build pipeline test: the cadence cycle syncs the
    # selected catalog and runs its own build + deploy. Skip only when
    # cadence is disabled in build_stream_config.yml.
    if not block["job_id"]:
        context = load_bsm_context(host)
        if context["success"] and not is_cadence_enabled(host, context):
            pytest.skip(skip_test(tl, LOG["cadence_disabled_skip"].format(
                disable_id=TC["cadence_disable_takes_effect_live"]["id"],
                reenable_id=TC["cadence_reenable_resumes_cycle"]["id"])))

    if block["job_id"]:
        tl.check(LOG["pipeline_mode_verify"].format(job_id=block["job_id"], pipeline=_PIPELINE))
    else:
        tl.check(LOG["pipeline_mode_trigger"].format(pipeline=_PIPELINE))

    result = run_cadence_pipeline(host, settings, tl.info)

    if result["success"]:
        tl.passed_fields(LOG["pipeline_ok"].format(pipeline=_PIPELINE), result["fields"])
    else:
        tl.failed_fields(
            LOG["pipeline_failed"].format(pipeline=_PIPELINE, count=len(result["failures"])),
            [*result["fields"], *failure_fields(result["failures"])],
        )
    assert result["success"], ASSERT["cadence_failed"].format(failures=failure_summary(result))
