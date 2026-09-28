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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied
# See the License for the specific language governing permissions and
# limitations under the License.

"""Strict state handling for explicitly triggered manual build pipelines."""

import json
import os
from pathlib import Path

import pytest

from omnia_auto import load_test_config, log


class ManualBuildPipelineState:  # pylint: disable=too-few-public-methods
    """Pipeline and job identifiers shared within one manual suite run."""

    pipeline_id: int = 0
    job_id: str = ""
    catalog_path: str = ""
    architectures: set[str] = set()


def _catalog_architectures(catalog_file: Path) -> set[str]:
    """Return architecture values declared anywhere in a catalog."""
    try:
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        pytest.fail(f"Unable to load configured catalog {catalog_file}: {exc}")

    architectures = set()

    def _walk(value):
        if isinstance(value, dict):
            architecture = value.get("architecture")
            if isinstance(architecture, str) and architecture.strip():
                architectures.add(architecture.strip())
            for child in value.values():
                _walk(child)
        elif isinstance(value, list):
            for child in value:
                _walk(child)

    _walk(catalog)
    return architectures


@pytest.fixture(scope="session")
def pipeline_state():
    """Require configured job identity for verify; never select latest job."""
    state = ManualBuildPipelineState()
    config = load_test_config()
    state.catalog_path = str(config.get("catalog_path", "")).strip()
    if not state.catalog_path:
        pytest.fail("Manual build requires catalog_path in test_config.yml")

    module_root = Path(__file__).resolve().parents[3]
    catalog_file = (
        module_root.parents[1]
        / "src" / "main" / "samples" / "catalogs" / state.catalog_path
    ).resolve()
    catalog_root = (
        module_root.parents[1] / "src" / "main" / "samples" / "catalogs"
    ).resolve()
    try:
        catalog_file.relative_to(catalog_root)
    except ValueError:
        pytest.fail("catalog_path resolves outside src/main/samples/catalogs")
    state.architectures = _catalog_architectures(catalog_file)

    if os.environ.get("OMNIA_COMMAND_TYPE", "") == "verify":
        state.job_id = str(config.get("job_id", "")).strip()
        if not state.job_id:
            pytest.fail(
                "Manual build verify requires job_id in test_config.yml; "
                "run manual build exec/test first or enter the job_id"
            )
        log(f"Manual build target job_id: {state.job_id}", "INFO")
    return state
