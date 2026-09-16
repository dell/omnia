"""State shared by cleanup-pipeline trigger and verification tests."""

import pytest

from omnia_auto import load_test_config
from library.functions import get_image_groups_for_job, get_images_for_job


class CleanupPipelineState:  # pylint: disable=too-few-public-methods
    """Cleanup target and GitLab child-pipeline identifiers."""

    job_id = ""
    image_group_id = ""
    parent_pipeline_id = 0
    child_pipeline_id = 0
    summary_job_id = 0
    roles = []
    already_cleaned = False


@pytest.fixture(scope="session")
def cleanup_pipeline_state(host):
    """Resolve one cleanable image group for the configured BuildStream job."""
    state = CleanupPipelineState()
    state.job_id = str(load_test_config().get("job_id", "")).strip()
    if not state.job_id:
        pytest.fail(
            "cleanup_pipeline requires job_id in test_config.yml; "
            "run the build pipeline first or enter the job_id manually"
        )

    groups = get_image_groups_for_job(host, state.job_id)
    if not groups["success"]:
        pytest.fail(groups["error"])
    candidates = [
        group for group in groups["image_groups"]
        if group.get("status") != "CLEANED"
    ]
    if not candidates:
        candidates = [
            group for group in groups["image_groups"]
            if group.get("status") == "CLEANED"
        ]
        if not candidates:
            pytest.fail(
                f"No image group exists for job_id {state.job_id}"
            )
        state.already_cleaned = True
    state.image_group_id = candidates[0]["id"]

    images = get_images_for_job(host, state.job_id)
    if not images["success"]:
        pytest.fail(images["error"])
    state.roles = sorted({
        image["role"] for image in images["images"] if image.get("role")
    })
    if not state.roles:
        pytest.fail(
            f"No image roles exist for cleanup job_id {state.job_id}"
        )
    return state
