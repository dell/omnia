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
Execute — Cadence Pipeline (one test case per step).

Trigger (pipeline.cadence_job_id empty):
  first build a NEW image group inside this test case (the next unused catalog
  version; upload -> parse-catalog -> create-local-repository -> build-image,
  image group BUILT). It is separate from the build suites' image, which the
  deploy suites deploy and validate, and it is the image the automated cleanup
  deletes later. A failed build fails this test and skips the cadence steps.
  check that a build pipeline ran (BSM_CLIENT_ID/SECRET CI/CD variables and an
  image group exist; the build above satisfies it)
  playbook-watcher active, cadence.enabled true, trigger script present
  cancel running pipelines when allowed (else fail and list them)
  upload the installation.catalog catalog to GitLab cadence_catalog_rhel.json
  with [skip ci] (no pipeline), one minor below the next unused version
  run trigger_cadence.sh and follow the cycle in the playbook-watcher journal
  (repo sync log streamed with debug_mode): fetch, sync, bump, commit
  verify the bumped version agrees in the journal, GitLab and the host and
  the commit started cadence_pipeline and a BuildStream job
Verify-only mode (pipeline.cadence_job_id set): nothing is triggered.

Then one test case per stage: upload -> parse-catalog ->
create-local-repository -> build-image -> deploy -> restart -> validate,
and the GitLab pipeline result, image group PASSED and API job.
After the disable / re-enable tests, two artifact checks of the cadence job:
the registry image and S3 boot files of every role it built, and the restart
node-results and failed-nodes artifacts the API serves for it.
The cadence catalog is installation.cadence_catalog (empty = the build
catalog installation.catalog).
Markers: pipeline, cadence, sanity (the two artifact checks carry pipeline
and cadence only).
"""

import pytest

from library.functions import (
    run_stage_step,
    run_step,
    start_cadence_pipeline,
    verify_cadence_result,
    verify_image_build_artifacts,
    verify_restart_node_results,
)
from library.vars import TEST_CASES as TC


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40801)
def test_cadence_pipeline_trigger_cycle(host):
    """Require a prior build, trigger a cadence cycle and verify it started the pipeline."""
    run_step(TC["cadence_pipeline_trigger_cycle"], "Cadence trigger", start_cadence_pipeline, host)


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40802)
def test_cadence_pipeline_upload_stage(host):
    """Verify the cadence upload stage."""
    run_step(TC["cadence_pipeline_upload_stage"], "Cadence upload stage", run_stage_step,
             host, "cadence", "upload")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40803)
def test_cadence_pipeline_parse_catalog_stage(host):
    """Verify the cadence parse-catalog stage."""
    run_step(TC["cadence_pipeline_parse_catalog_stage"], "Cadence parse-catalog stage",
             run_stage_step, host, "cadence", "parse-catalog")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40804)
def test_cadence_pipeline_create_local_repository_stage(host):
    """Verify the cadence create-local-repository stage."""
    run_step(TC["cadence_pipeline_create_local_repository_stage"],
             "Cadence create-local-repository stage",
             run_stage_step, host, "cadence", "create-local-repository")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40805)
def test_cadence_pipeline_build_image_stage(host):
    """Verify the cadence build-image stage."""
    run_step(TC["cadence_pipeline_build_image_stage"], "Cadence build-image stage", run_stage_step,
             host, "cadence", "build-image")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40806)
def test_cadence_pipeline_deploy_stage(host):
    """Verify the cadence deploy stage."""
    run_step(TC["cadence_pipeline_deploy_stage"], "Cadence deploy stage", run_stage_step,
             host, "cadence", "deploy")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40807)
def test_cadence_pipeline_restart_stage(host):
    """Verify the cadence restart stage."""
    run_step(TC["cadence_pipeline_restart_stage"], "Cadence restart stage", run_stage_step,
             host, "cadence", "restart")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40808)
def test_cadence_pipeline_validate_stage(host):
    """Verify the cadence validate stage."""
    run_step(TC["cadence_pipeline_validate_stage"], "Cadence validate stage", run_stage_step,
             host, "cadence", "validate")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(40809)
def test_cadence_pipeline_records(host):
    """Verify the GitLab pipeline result, image group PASSED and API job."""
    run_step(TC["cadence_pipeline_records"], "Cadence pipeline result", verify_cadence_result,
             host)


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.order(40812)
def test_cadence_pipeline_artifacts(host):
    """Verify the registry image and S3 boot files of the cadence image."""
    run_step(TC["cadence_pipeline_artifacts"], "Cadence image artifacts",
             verify_image_build_artifacts, host, "cadence")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.order(40813)
def test_cadence_pipeline_restart_node_results(host):
    """Verify the restart node-results and failed-nodes artifacts of the cadence job."""
    run_step(TC["cadence_pipeline_restart_node_results"], "Cadence restart node results",
             verify_restart_node_results, host, "cadence")
