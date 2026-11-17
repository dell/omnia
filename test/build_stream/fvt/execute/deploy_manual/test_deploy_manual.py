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
Execute — Deploy Pipeline, Manual Trigger (one test case per step).

Trigger: pick the image group built by build_manual in this run (else by
build_automatic); every step is skipped when that build failed. A
deploy-only run deploys pipeline.deploy_image_group_id and fails when it is
empty ("image name is not present") or not in build_stream_db ("requested
image not found"). Then cancel running pipelines when allowed and trigger
PIPELINE_TYPE=deploy through the GitLab API (no PXE mapping change).
Every later step is the same function as the automatic deploy suite.
Verify-only mode (pipeline.deploy_job_id set) triggers nothing.
Markers: pipeline, deploy_pipeline, manual_execution (no sanity).
"""

import pytest

from library.functions import (
    run_deploy_stage,
    run_stage_step,
    run_step,
    select_deploy_image,
    start_deploy_pipeline,
    verify_deploy_result,
    verify_job_image_group_mapping,
    verify_restart_node_results,
)
from library.vars import TEST_CASES as TC


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40701)
def test_deploy_manual_trigger_pipeline(host):
    """Trigger PIPELINE_TYPE=deploy through the API and verify the deploy pipeline started."""
    run_step(TC["deploy_manual_trigger_pipeline"], "Deploy trigger", start_deploy_pipeline,
             host, "deploy_manual")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40702)
def test_deploy_manual_select_image(host):
    """Select the image group and verify the select_image job chose it."""
    run_step(TC["deploy_manual_select_image"], "Image selection", select_deploy_image,
             host, "deploy_manual")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40703)
def test_deploy_manual_deploy_stage(host):
    """Play the deploy job and verify the deploy stage."""
    run_step(TC["deploy_manual_deploy_stage"], "Deploy stage", run_deploy_stage,
             host, "deploy_manual")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40704)
def test_deploy_manual_restart_stage(host):
    """Verify the restart stage."""
    run_step(TC["deploy_manual_restart_stage"], "Restart stage", run_stage_step,
             host, "deploy_manual", "restart")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40705)
def test_deploy_manual_restart_node_results(host):
    """Verify the restart node-results and failed-nodes artifacts."""
    run_step(TC["deploy_manual_restart_node_results"], "Restart node results",
             verify_restart_node_results, host, "deploy_manual")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40706)
def test_deploy_manual_validate_stage(host):
    """Verify the validate stage."""
    run_step(TC["deploy_manual_validate_stage"], "Validate stage", run_stage_step,
             host, "deploy_manual", "validate")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40707)
def test_deploy_manual_pipeline_records(host):
    """Verify the pipeline result, summary job, image group PASSED and deploy_count."""
    run_step(TC["deploy_manual_pipeline_records"], "Deploy pipeline result", verify_deploy_result,
             host, "deploy_manual")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.manual_execution
@pytest.mark.order(40708)
def test_deploy_manual_job_image_group_mapping(host):
    """Verify the job maps to exactly one image group, the deployed one."""
    run_step(TC["deploy_manual_job_image_group_mapping"], "Job to image group mapping",
             verify_job_image_group_mapping, host, "deploy_manual")
