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

"""Shared state for the unified cadence-pipeline FVT suite."""

import os

import pytest

from omnia_auto import load_test_config, log
from library.functions import (
    discover_cadence_pipeline,
    get_cadence_catalog,
    resolve_deploy_image_group,
)


class CadencePipelineState:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """Identifiers and catalog metadata for one cadence pipeline."""

    job_id: str = ""
    image_group_id: str = ""
    parent_pipeline_id: int = 0
    child_pipeline_id: int = 0
    summary_job_id: int = 0
    pipeline_sha: str = ""
    catalog_identifier: str = ""
    catalog_version: str = ""


@pytest.fixture(scope="session")
def cadence_pipeline_state(host):
    """Resolve the exact cadence pipeline recorded in test_config.yml."""
    state = CadencePipelineState()
    if os.environ.get("OMNIA_COMMAND_TYPE", "") == "exec":
        return state

    config = load_test_config()
    state.job_id = str(config.get("job_id", "") or "").strip()
    if not state.job_id:
        pytest.fail(
            "cadence_pipeline requires job_id in test_config.yml; "
            "run cadence_pipeline exec/test first"
        )

    image_group = resolve_deploy_image_group(host, state.job_id)
    if not image_group["success"]:
        pytest.fail(image_group["error"])
    state.image_group_id = image_group["image_group_id"]

    discovered = discover_cadence_pipeline(
        host, state.job_id, state.image_group_id,
    )
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

    log(
        "Cadence target: "
        f"job_id={state.job_id}, "
        f"image_group_id={state.image_group_id}, "
        f"pipeline={state.child_pipeline_id}",
        "INFO",
    )
    return state
