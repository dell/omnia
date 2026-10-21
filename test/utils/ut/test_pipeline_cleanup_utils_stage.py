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
Regression tests for OMN-DEF #916.

The automation pipeline's ``cleanup_omnia``/``summary`` stages must always be
able to observe the ``cleanup_utils`` job: the stage must be declared in the
pipeline's ``stages:`` list, the job must exist, and the dependency chain must
guarantee ``cleanup_utils`` finishes before ``cleanup_omnia`` can run (either
directly via ``needs``, or transitively through an intermediate stage such as
``cleanup_telemetry`` that itself needs ``cleanup_utils``). A prior regression
dropped the stage, leaving ``cleanup_omnia`` unable to run utils cleanup and
``summary`` reporting ``cleanup_utils`` as UNKNOWN.
"""

# pylint: disable=missing-function-docstring,missing-class-docstring

import yaml
import pytest

PIPELINE_FILES = [
    ".gitlab-ci-cluster.yml",
]


def _load_pipeline(pipeline_dir, filename):
    path = pipeline_dir / filename
    assert path.exists(), f"pipeline file not found: {path}"
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _job_needs_job(pipeline, job_name, dependency_name, _seen=None):
    """Return True if job_name needs dependency_name, directly or transitively."""
    if _seen is None:
        _seen = set()
    if job_name in _seen:
        return False
    _seen.add(job_name)

    job = pipeline.get(job_name)
    if not isinstance(job, dict):
        return False

    needs = job.get("needs", [])
    direct_names = [
        need["job"] if isinstance(need, dict) else need for need in needs
    ]
    if dependency_name in direct_names:
        return True
    return any(
        _job_needs_job(pipeline, needed, dependency_name, _seen)
        for needed in direct_names
    )


@pytest.mark.parametrize("filename", PIPELINE_FILES)
class TestCleanupUtilsStageIsWired:

    def test_cleanup_utils_stage_is_declared(self, pipeline_dir, filename):
        pipeline = _load_pipeline(pipeline_dir, filename)
        assert "cleanup_utils" in pipeline["stages"]

    def test_cleanup_utils_job_exists(self, pipeline_dir, filename):
        pipeline = _load_pipeline(pipeline_dir, filename)
        assert "cleanup_utils" in pipeline
        assert pipeline["cleanup_utils"]["stage"] == "cleanup_utils"

    def test_cleanup_omnia_waits_for_cleanup_utils(self, pipeline_dir, filename):
        pipeline = _load_pipeline(pipeline_dir, filename)
        assert _job_needs_job(pipeline, "cleanup_omnia", "cleanup_utils"), (
            "cleanup_omnia must depend on cleanup_utils directly or "
            "transitively, or Omnia cleanup can race ahead of utils cleanup"
        )

    def test_summary_waits_for_cleanup_utils(self, pipeline_dir, filename):
        pipeline = _load_pipeline(pipeline_dir, filename)
        assert _job_needs_job(pipeline, "summary", "cleanup_utils"), (
            "summary must depend on cleanup_utils so its status is reported "
            "as PASSED/FAILED instead of UNKNOWN"
        )
