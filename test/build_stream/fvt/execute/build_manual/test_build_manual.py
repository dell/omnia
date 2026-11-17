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
Execute — Build Pipeline, Manual Trigger (one test case per step).

Trigger: commit the installation.catalog catalog as catalog_rhel.json with
the next unused version and [skip ci] (verified to start no pipeline), then
trigger PIPELINE_TYPE=build through the GitLab API, as a user running the
pipeline by hand. Verify-only mode (pipeline.build_job_id set)
commits and triggers nothing.

Every later step is the same function as the automatic build suite: one test
case per stage, Repo Manager status, Image Build Manager artifacts, the
pipeline result and the OAuth client. A failed build skips the deploy
suites of the same run.
Markers: pipeline, build_pipeline, manual_execution (no sanity).
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
@pytest.mark.manual_execution
@pytest.mark.order(40501)
def test_build_manual_trigger_pipeline(host):
    """Commit the selected catalog and verify the build pipeline and job started."""
    run_step(TC["build_manual_trigger_pipeline"], "Build trigger", start_build_pipeline,
             host, "build_manual")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40502)
def test_build_manual_upload_stage(host):
    """Verify the upload stage and that the committed catalog reached the host."""
    run_step(TC["build_manual_upload_stage"], "Build upload stage", run_stage_step,
             host, "build_manual", "upload")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40503)
def test_build_manual_parse_catalog_stage(host):
    """Verify the parse-catalog stage."""
    run_step(TC["build_manual_parse_catalog_stage"], "Build parse-catalog stage", run_stage_step,
             host, "build_manual", "parse-catalog")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40504)
def test_build_manual_create_local_repository_stage(host):
    """Verify the create-local-repository stage."""
    run_step(TC["build_manual_create_local_repository_stage"],
             "Build create-local-repository stage",
             run_stage_step, host, "build_manual", "create-local-repository")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40505)
def test_build_manual_build_image_stage(host):
    """Verify the build-image stage."""
    run_step(TC["build_manual_build_image_stage"], "Build build-image stage", run_stage_step,
             host, "build_manual", "build-image")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40506)
def test_build_manual_repo_manager_status(host):
    """Verify repo_status.yml reports overall_status success."""
    run_step(TC["build_manual_repo_manager_status"], "Repo Manager status",
             verify_repo_manager_status, host, "build_manual")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40507)
def test_build_manual_image_build_manager_artifacts(host):
    """Verify every role's registry image and S3 boot files."""
    run_step(TC["build_manual_image_build_manager_artifacts"], "Image Build Manager artifacts",
             verify_image_build_artifacts, host, "build_manual")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40508)
def test_build_manual_pipeline_records(host):
    """Verify the GitLab pipeline result and the job, image group and images rows."""
    run_step(TC["build_manual_pipeline_records"], "Build pipeline result", verify_build_result,
             host, "build_manual")


@pytest.mark.pipeline
@pytest.mark.build_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40509)
def test_build_manual_oauth_client_registered(host):
    """Verify the OAuth client is in GitLab CI/CD and created the build job."""
    run_step(TC["build_manual_oauth_client_registered"], "OAuth client", verify_oauth_client,
             host, "build_manual")
