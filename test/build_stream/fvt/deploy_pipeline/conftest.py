"""Shared, fail-closed deploy-pipeline target state."""

import os
import pytest

from omnia_auto import load_test_config, log
from library.functions import (
    discover_deploy_pipeline,
    resolve_deploy_image_group,
)


class DeployPipelineState:  # pylint: disable=too-few-public-methods
    """Resolved deploy target and GitLab pipeline identifiers."""

    job_id: str = ""
    image_group_id: str = ""
    image_group_status: str = ""
    parent_pipeline_id: int = 0
    child_pipeline_id: int = 0
    summary_job_id: int = 0


@pytest.fixture(scope="session")
def deploy_pipeline_state(host):
    """Resolve the configured job without any latest-image fallback."""
    config = load_test_config()
    job_id = str(config.get("job_id", "")).strip()
    if not job_id:
        pytest.fail(
            "deploy_pipeline requires job_id in test_config.yml; "
            "run build_pipeline first or enter the job_id manually"
        )
    resolved = resolve_deploy_image_group(
        host,
        job_id,
        require_built=os.environ.get("OMNIA_COMMAND_TYPE", "") == "exec",
    )
    if not resolved["success"]:
        pytest.fail(resolved["error"])

    state = DeployPipelineState()
    state.job_id = job_id
    state.image_group_id = resolved["image_group_id"]
    state.image_group_status = resolved["status"]
    if os.environ.get("OMNIA_COMMAND_TYPE", "") == "verify":
        discovered = discover_deploy_pipeline(
            host, job_id, state.image_group_id,
        )
        if not discovered["success"]:
            pytest.fail(discovered["error"])
        state.parent_pipeline_id = discovered["parent_pipeline_id"]
        state.child_pipeline_id = discovered["child_pipeline_id"]
        state.summary_job_id = discovered["summary_job_id"]
    log(
        f"Deploy target: job_id={job_id}, image_group_id={state.image_group_id}, "
        f"status={state.image_group_status}",
        "INFO",
    )
    return state
