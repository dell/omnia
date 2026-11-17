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
Execute — Deploy Pipeline, Automatic Trigger (one test case per step).

Trigger: pick the image group built by build_automatic in this run (else by
build_manual); every step is skipped when that build failed. A deploy-only
run deploys pipeline.deploy_image_group_id and fails when it is empty
("image name is not present") or not in build_stream_db ("requested image
not found"). Then cancel running pipelines when allowed, swap two rows of
input/orchestrator/pxe_mapping_file.csv in GitLab and verify the push
started deploy_pipeline. Then play the image group's select_image job and
verify its log names the image group and build job; the deploy stage (the
manual deploy job is played first), restart stage, restart node results and
validate stage, each streaming its playbook log with debug_mode: true and
checking job_stages and the API; last the pipeline result, summary job
(RESULT: PASSED), image group PASSED with an incremented deploy_count,
and the job maps to exactly one image group, the deployed one.
Verify-only mode (pipeline.deploy_job_id set) triggers nothing.
Markers: pipeline, deploy_pipeline, automatic_execution, sanity.
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
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40601)
def test_deploy_trigger_pxe_change(host):
    """Swap PXE mapping rows in GitLab and verify the deploy pipeline started."""
    run_step(TC["deploy_trigger_pxe_change"], "Deploy trigger", start_deploy_pipeline,
             host, "deploy")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40602)
def test_deploy_select_image(host):
    """Select the image group and verify the select_image job chose it."""
    run_step(TC["deploy_select_image"], "Image selection", select_deploy_image, host, "deploy")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40603)
def test_deploy_deploy_stage(host):
    """Play the deploy job and verify the deploy stage."""
    run_step(TC["deploy_deploy_stage"], "Deploy stage", run_deploy_stage, host, "deploy")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40604)
def test_deploy_restart_stage(host):
    """Verify the restart stage."""
    run_step(TC["deploy_restart_stage"], "Restart stage", run_stage_step,
             host, "deploy", "restart")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40605)
def test_deploy_restart_node_results(host):
    """Verify the restart node-results and failed-nodes artifacts."""
    run_step(TC["deploy_restart_node_results"], "Restart node results", verify_restart_node_results,
             host, "deploy")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40606)
def test_deploy_validate_stage(host):
    """Verify the validate stage."""
    run_step(TC["deploy_validate_stage"], "Validate stage", run_stage_step,
             host, "deploy", "validate")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40607)
def test_deploy_pipeline_records(host):
    """Verify the pipeline result, summary job, image group PASSED and deploy_count."""
    run_step(TC["deploy_pipeline_records"], "Deploy pipeline result", verify_deploy_result,
             host, "deploy")


@pytest.mark.pipeline
@pytest.mark.deploy_pipeline
@pytest.mark.automatic_execution
@pytest.mark.sanity
@pytest.mark.order(40608)
def test_deploy_job_image_group_mapping(host):
    """Verify the job maps to exactly one image group, the deployed one."""
    run_step(TC["deploy_job_image_group_mapping"], "Job to image group mapping",
             verify_job_image_group_mapping, host, "deploy")
