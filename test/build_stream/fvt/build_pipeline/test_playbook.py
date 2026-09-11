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
Build Pipeline -- Playbook Execution (--test mode).

Pushes a catalog from ``src/main/samples/`` to GitLab, waits for the
pipeline to trigger and BSM job to be created, monitors GitLab CI/CD
stages in real-time (initialization, copy-input-files,
configure-local-repository, build-images, summary), and persists the
``job_id`` in ``test_config.yml`` so that ``--verify`` mode can read
it later.

This file is marked ``@pytest.mark.deploy`` so it is excluded when
running with ``--verify`` (which uses ``-m 'not deploy'``).
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    push_catalog_from_examples,
    trigger_build_pipeline_auto,
    get_latest_job,
    check_server_credentials,
    list_pipelines,
    poll_gitlab_ci_stages,
    poll_stage_until_complete,
    update_job_id_in_config,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import BUILD_PIPELINE_STAGES
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_build_pipeline(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    host, pipeline_state,
):
    """Push catalog, trigger pipeline, track CI stages, save job_id.

    Flow:
      1. Validate ``catalog_path`` in ``test_config.yml``
      2. Push catalog from ``src/main/samples/catalogs/`` to GitLab
      3. Wait for GitLab pipeline + BSM job
      4. Save ``job_id`` to ``test_config.yml``
      5. Track GitLab CI/CD stages in real-time
      6. Monitor BSM database stages
    """
    tc = TC["deploy_build_pipeline"]
    tl = TestLogger(tc["title"], tc["id"])
    config = load_test_config()
    configured_job_id = str(config.get("job_id", "") or "").strip()

    # ------------------------------------------------------------------
    # Step 1: Validate catalog_path is set
    # ------------------------------------------------------------------
    catalog_path = str(config.get("catalog_path", "") or "").strip()
    if not catalog_path:
        tl.failed(LOG["catalog_push_fail"].format(
            error="catalog_path is empty in test_config.yml",
        ))
        assert False, ASSERT["catalog_path_not_set"]

    tl.check(f"Catalog: {catalog_path}")

    credentials = check_server_credentials(host)
    if not credentials["success"]:
        error = credentials.get("error", "Incomplete BuildStream credentials")
        tl.failed(LOG["creds_configured_fail"].format(
            fields=", ".join(credentials.get("missing", [])),
        ))
        assert False, ASSERT["credentials_not_configured"].format(
            path=credentials.get("path", ""),
            missing=", ".join(credentials.get("missing", [])),
        ) + f"\nRoot cause: {error}"

    # ------------------------------------------------------------------
    # Step 2: Record current pipeline/job IDs, then push catalog
    # ------------------------------------------------------------------
    pre_push = list_pipelines(host, per_page=5)
    if not pre_push["success"]:
        error = pre_push.get("error", "Unable to read existing pipelines")
        tl.failed(LOG["catalog_trigger_fail"].format(error=error))
        assert False, ASSERT["pipeline_not_triggered"] + f"\nRoot cause: {error}"

    initial_pipeline_id = 0
    if pre_push.get("pipelines"):
        initial_pipeline_id = pre_push["pipelines"][0].get("id", 0)

    pre_job = get_latest_job(host)
    if (
        not pre_job.get("success")
        and pre_job.get("error") != "No jobs found in database"
    ):
        error = pre_job.get("error", "Unable to read existing BSM jobs")
        tl.failed(LOG["catalog_trigger_fail"].format(error=error))
        assert False, ASSERT["pipeline_not_triggered"] + f"\nRoot cause: {error}"

    initial_job_id = (
        pre_job.get("job_id", "") if pre_job.get("success") else ""
    )

    push_result = push_catalog_from_examples(
        host, catalog_path, log_callback=tl.check,
    )
    if not push_result["success"]:
        tl.failed(LOG["catalog_push_fail"].format(
            error=push_result["error"],
        ))
        assert False, (
            ASSERT["catalog_push_failed"]
            + f"\nRoot cause: {push_result['error']}"
        )

    tl.check(LOG["catalog_push_ok"].format(catalog=catalog_path))

    # ------------------------------------------------------------------
    # Step 3: Wait for pipeline triggered by the catalog push
    # ------------------------------------------------------------------
    result = trigger_build_pipeline_auto(
        host,
        initial_pipeline_id=initial_pipeline_id,
        initial_job_id=initial_job_id,
    )
    if not result["success"]:
        tl.failed(LOG["catalog_trigger_fail"].format(
            error=result["error"],
        ))
        assert False, (
            ASSERT["pipeline_not_triggered"]
            + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
        )

    pipeline_state.pipeline_id = result["pipeline_id"]
    pipeline_state.job_id = result.get("job_id", "")
    tl.check(LOG["catalog_trigger_ok"].format(
        pipeline_id=result["pipeline_id"],
    ))

    # ------------------------------------------------------------------
    # Step 4: Save job_id to test_config.yml
    # ------------------------------------------------------------------
    if not pipeline_state.job_id:
        tl.failed(LOG["job_not_created"])
        assert False, ASSERT["job_not_created"]

    if not update_job_id_in_config(pipeline_state.job_id):
        tl.failed(LOG["job_id_save_fail"])
        assert False, ASSERT["job_id_not_saved"]

    if configured_job_id and configured_job_id != pipeline_state.job_id:
        tl.check(LOG["job_id_overwritten"].format(
            old_job_id=configured_job_id[:8] + "...",
            new_job_id=pipeline_state.job_id[:8] + "...",
        ))
    else:
        tl.check(LOG["job_id_saved"].format(
            job_id=pipeline_state.job_id[:8] + "...",
        ))

    # ------------------------------------------------------------------
    # Step 5: Track GitLab CI/CD stages in real-time
    # ------------------------------------------------------------------
    ci_result = poll_gitlab_ci_stages(
        host,
        pipeline_id=pipeline_state.pipeline_id,
        log_callback=tl.check,
    )
    if ci_result["success"]:
        tl.check("All GitLab CI/CD stages completed successfully")
    elif ci_result.get("error"):
        tl.check(f"GitLab CI/CD: {ci_result['error']}")

    # ------------------------------------------------------------------
    # Step 6: Monitor BSM database stages
    # ------------------------------------------------------------------
    if pipeline_state.job_id:
        for stage_name in BUILD_PIPELINE_STAGES:
            stage_result = poll_stage_until_complete(
                host, pipeline_state.job_id, stage_name,
            )
            if stage_result["success"]:
                tl.check(LOG["stage_completed"].format(
                    stage=stage_name, elapsed=stage_result["elapsed"],
                ))
            elif "not found" in stage_result.get("error", "").lower():
                tl.check(LOG["stage_skipped"].format(stage=stage_name))
            else:
                tl.check(LOG["stage_failed"].format(
                    stage=stage_name, error=stage_result["error"],
                ))

    tl.passed(LOG["pipeline_triggered"].format(
        pipeline_id=pipeline_state.pipeline_id,
        status="complete",
    ))

    assert result["success"], (
        ASSERT["pipeline_not_triggered"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )
