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

"""Source-contract tests for the unified cadence GitLab pipeline."""

from pathlib import Path

import yaml


PIPELINE_PATH = (
    Path(__file__).resolve().parents[5]
    / "src"
    / "build_stream"
    / "roles"
    / "hosted_gitlab"
    / "files"
    / ".gitlab-ci-cadence.yml"
)


def _pipeline_text():
    """Return the cadence template source."""
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_cadence_pipeline_has_complete_ordered_lifecycle():
    """The unified cadence pipeline carries one run through validation."""
    pipeline = yaml.safe_load(_pipeline_text())
    assert pipeline["stages"] == [
        "initialization",
        "parse-catalog",
        "configure-local-repository",
        "build-images",
        "deploy",
        "restart",
        "validate",
        "summary",
    ]


def test_cadence_pipeline_uses_current_stage_api_contract():
    """Cadence calls the same BuildStream stage endpoints as normal CI."""
    source = _pipeline_text()
    for endpoint in (
        "/stages/parse-catalog",
        "/stages/create-local-repository",
        "/stages/build-image",
        "/stages/deploy",
        "/stages/restart",
        "/stages/validate",
    ):
        assert endpoint in source
    for stale_endpoint in (
        'jobs/${JOB_ID}/catalog',
        'jobs/${JOB_ID}/repository',
        'jobs/${JOB_ID}/build"',
        'jobs/${JOB_ID}/deploy"',
    ):
        assert stale_endpoint not in source


def test_cadence_pipeline_uses_current_status_contract():
    """Polling reads stage_name/stage_state and terminal uppercase states."""
    source = _pipeline_text()
    assert ".stage_name" in source
    assert ".stage_state" in source
    assert ".name ==" not in source
    assert ".status //" not in source
    assert "COMPLETED|SUCCEEDED" in source
    assert "FAILED|CANCELLED" in source


def test_cadence_pipeline_uploads_canonical_catalog_and_uses_dotenv():
    """Cadence input is uploaded once and IDs cross jobs via dotenv."""
    source = _pipeline_text()
    assert 'cp "${CI_PROJECT_DIR}/${CATALOG_FILE}" /tmp/catalog_rhel.json' in source
    assert 'files=@/tmp/catalog_rhel.json' in source
    assert "dotenv: job.env" in source
    assert "dotenv: parse_catalog.env" in source
    assert "- /tmp/cadence_job_id" not in source
    assert "- /tmp/cadence_image_group_id" not in source
