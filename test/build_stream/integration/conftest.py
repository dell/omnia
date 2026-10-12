# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Fixtures for standalone BuildStream integration suites."""

import os

import pytest

from omnia_auto import load_test_config, log
from library.functions import (
    discover_cadence_pipeline,
    get_cadence_catalog,
    get_image_groups_for_job,
    get_images_for_job,
    resolve_deploy_image_group,
)


class IntegrationState:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """Identifiers produced by the build prerequisite and cadence pipeline."""

    build_job_id = ""
    build_pipeline_id = 0
    job_id = ""
    image_group_id = ""
    parent_pipeline_id = 0
    child_pipeline_id = 0
    summary_job_id = 0
    pipeline_sha = ""
    catalog_identifier = ""
    catalog_version = ""


@pytest.fixture(scope="session")
def integration_state(host):
    """Hold execution state or resolve the configured cadence job for verify."""
    state = IntegrationState()
    if os.environ.get("OMNIA_COMMAND_TYPE", "") == "exec":
        return state

    state.job_id = str(load_test_config().get("job_id", "") or "").strip()
    if not state.job_id:
        pytest.fail(
            "cadence verification requires job_id in integration/test_config.yml"
        )
    image_group = resolve_deploy_image_group(host, state.job_id)
    if not image_group["success"]:
        pytest.fail(image_group["error"])
    state.image_group_id = image_group["image_group_id"]

    discovered = discover_cadence_pipeline(host, state.job_id, state.image_group_id)
    if not discovered["success"]:
        pytest.fail(discovered["error"])
    state.parent_pipeline_id = discovered["parent_pipeline_id"]
    state.child_pipeline_id = discovered["child_pipeline_id"]
    state.summary_job_id = discovered["summary_job_id"]
    state.pipeline_sha = discovered["pipeline_sha"]

    catalog = get_cadence_catalog(host, ref=state.pipeline_sha)
    if not catalog["success"]:
        pytest.fail(catalog["error"])
    state.catalog_identifier = catalog["identifier"]
    state.catalog_version = catalog["version"]
    log(f"Integration cadence target: job_id={state.job_id}", "INFO")
    return state


class AutomaticCleanupState:  # pylint: disable=too-few-public-methods
    """Exact automatic-cleanup target selected by integration configuration."""

    job_id = ""
    image_group_id = ""
    roles = []


@pytest.fixture(scope="session")
def automatic_cleanup_state(host):
    """Resolve only the explicitly configured automatic-cleanup target."""
    config = load_test_config()
    state = AutomaticCleanupState()
    state.job_id = str(config.get("automatic_cleanup_job_id", "")).strip()
    if not state.job_id:
        pytest.fail("automatic_cleanup_job_id is required in integration/test_config.yml")
    if (
        os.environ.get("OMNIA_COMMAND_TYPE", "") == "exec"
        and not config.get("automatic_cleanup_allow_execution", False)
    ):
        pytest.fail("automatic_cleanup_allow_execution must be true for execution")

    groups = get_image_groups_for_job(host, state.job_id)
    if not groups["success"]:
        pytest.fail(groups["error"])
    if len(groups["image_groups"]) != 1:
        pytest.fail(
            f"Expected one ImageGroup for {state.job_id}, found "
            f"{len(groups['image_groups'])}"
        )
    state.image_group_id = groups["image_groups"][0]["id"]

    images = get_images_for_job(host, state.job_id)
    if not images["success"]:
        pytest.fail(images["error"])
    state.roles = sorted({
        image["role"] for image in images["images"] if image.get("role")
    })
    if not state.roles:
        pytest.fail(f"No image roles exist for cleanup Job {state.job_id}")
    return state
