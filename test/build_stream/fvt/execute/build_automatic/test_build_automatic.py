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
Execute — Build Pipeline, Automatic Trigger (one test case per step).

Trigger: commit the installation.catalog catalog as catalog_rhel.json with
the next unused version (version bump); the push auto-triggers
build_pipeline and creates a BuildStream job. Running or pending pipelines
are cancelled first when pipeline.allow_pipeline_cancel is true (else the
test fails and lists them). Verify-only mode (pipeline.build_job_id set)
commits nothing.

Then one test case per stage: upload (plus the host catalog check),
parse-catalog, create-local-repository, build-image. Each waits for its
stage, streams the stage playbook log live with debug_mode: true, and checks
the job_stages row and the API stage. Then the Repo Manager output
(repo_status.yml), the Image Build Manager output (regctl registry image and
S3 boot files per role) and the GitLab pipeline result with the jobs,
image_groups and images rows. Last, the OAuth client: BSM_CLIENT_ID and
BSM_CLIENT_SECRET are GitLab CI/CD variables and jobs.client_id of the job
is BSM_CLIENT_ID (the secret is never read). A failed step skips the steps
after it, and a failed build skips the deploy suites of the same run.
Markers: pipeline, build_pipeline, automatic_execution, sanity.
"""

import pytest

from library.functions import (
    run_stage_step,
    run_step,
    start_build_pipeline,
    verify_build_result,
    verify_image_build_artifacts,
    verify_oauth_client,
    verify_repo_manager_status,
)
from library.vars import TEST_CASES as TC


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40401)
def test_build_trigger_pipeline(host):
    """Commit the selected catalog and verify the build pipeline and job started."""
    run_step(TC["build_trigger_pipeline"], "Build trigger", start_build_pipeline, host, "build")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40402)
def test_build_upload_stage(host):
    """Verify the upload stage and that the committed catalog reached the host."""
    run_step(TC["build_upload_stage"], "Build upload stage", run_stage_step,
             host, "build", "upload")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40403)
def test_build_parse_catalog_stage(host):
    """Verify the parse-catalog stage."""
    run_step(TC["build_parse_catalog_stage"], "Build parse-catalog stage", run_stage_step,
             host, "build", "parse-catalog")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40404)
def test_build_create_local_repository_stage(host):
    """Verify the create-local-repository stage."""
    run_step(TC["build_create_local_repository_stage"], "Build create-local-repository stage",
             run_stage_step, host, "build", "create-local-repository")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40405)
def test_build_build_image_stage(host):
    """Verify the build-image stage."""
    run_step(TC["build_build_image_stage"], "Build build-image stage", run_stage_step,
             host, "build", "build-image")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40406)
def test_build_repo_manager_status(host):
    """Verify repo_status.yml reports overall_status success."""
    run_step(TC["build_repo_manager_status"], "Repo Manager status", verify_repo_manager_status,
             host, "build")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40407)
def test_build_image_build_manager_artifacts(host):
    """Verify every role's registry image and S3 boot files."""
    run_step(TC["build_image_build_manager_artifacts"], "Image Build Manager artifacts",
             verify_image_build_artifacts, host, "build")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40408)
def test_build_pipeline_records(host):
    """Verify the GitLab pipeline result and the job, image group and images rows."""
    run_step(TC["build_pipeline_records"], "Build pipeline result", verify_build_result,
             host, "build")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40409)
def test_build_oauth_client_registered(host):
    """Verify the OAuth client is in GitLab CI/CD and created the build job."""
    run_step(TC["build_oauth_client_registered"], "OAuth client",
             verify_oauth_client, host, "build")
