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

"""Unit tests of the catalog_build GitLab pipeline: one job per catalog, plan check.

No GitLab call and no SSH: the plan and the OIM are mocked. setup_svt_project.py
needs ``requests`` (the shared GitLab client), so its tests are skipped without it.
"""

# pylint: disable=protected-access,import-error,wrong-import-position

import json
import os
import sys
from unittest import mock

import pytest
import yaml

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODULE_ROOT)
sys.path.insert(0, os.path.join(MODULE_ROOT, "pipeline"))

import svt_ci  # noqa: E402

ENTRIES = [
    {"stage": "catalog_01", "index": 1, "catalog": "rhel/10.2/slurm_x86_64_no_vast.json",
     "run": True, "reason": ""},
    {"stage": "catalog_02", "index": 2, "catalog": "rhel/10.2/slurm_aarch64.json",
     "run": False, "reason": "skipped: contains aarch64 (x); include_aarch64 is false"},
]
PLAN_VALUE = ("catalog_01=rhel/10.2/slurm_x86_64_no_vast.json,"
              "catalog_02=rhel/10.2/slurm_aarch64.json")


@pytest.fixture(name="svt_project")
def _svt_project():
    pytest.importorskip("requests")
    import setup_svt_project  # pylint: disable=import-outside-toplevel
    return setup_svt_project


def _config(theme, **hours):
    return {"svt": {"theme": theme, "timeouts_hours": {"default_hours": 6, **hours}},
            "clusters": {"oim1": {}}}


def _plan(continue_on_failure=True):
    return {"settings": {"continue_on_failure": continue_on_failure}, "entries": ENTRIES}


# ------------------------------------------------------------------ render
def test_catalog_theme_renders_one_job_per_catalog(svt_project):
    """Every catalog is a job, titled with its catalog, soft, with the catalog timeout."""
    with mock.patch.object(svt_project, "catalog_plan", return_value=_plan()):
        text, longest = svt_project.render_ci(_config("catalog_build", catalog_stage=3))
    data = yaml.safe_load(text)
    assert data["variables"]["SVT_JOB_ORDER"] == (
        "preflight,initialization,catalog_01,catalog_02,summary")
    assert data["variables"]["SVT_CATALOG_PLAN"] == PLAN_VALUE
    assert data["stages"] == ["preflight", "initialization", "catalog_01", "catalog_02",
                              "summary"]
    for stage in ("catalog_01", "catalog_02"):
        assert data[stage]["script"] == [f"python3 svt_ci.py stage {stage}"]
        assert data[stage]["allow_failure"] is True
        assert data[stage]["timeout"] == "180m"
    assert "# Catalog 1: rhel/10.2/slurm_x86_64_no_vast.json:" in text
    assert "# Catalog 2: rhel/10.2/slurm_aarch64.json: skipped" in text
    assert longest == 6 * 3600


def test_catalog_jobs_are_hard_without_continue_on_failure(svt_project):
    """continue_on_failure: false makes every catalog job a hard one."""
    with mock.patch.object(svt_project, "catalog_plan", return_value=_plan(False)):
        data = yaml.safe_load(svt_project.render_ci(_config("catalog_build"))[0])
    assert "allow_failure" not in data["catalog_01"]
    assert data["catalog_01"]["timeout"] == "360m"


def test_build_stream_render_is_unchanged(svt_project):
    """build_stream: its fixed stages, no catalog plan, no plan variable."""
    data = yaml.safe_load(svt_project.render_ci(_config("build_stream"))[0])
    assert data["variables"]["SVT_JOB_ORDER"] == (
        "preflight,initialization,prepare_build_stream,build_deploy,cadence,"
        "automatic_cleanup,summary")
    assert "SVT_CATALOG_PLAN" not in data["variables"]
    assert data["build_deploy"]["allow_failure"] is True
    assert "allow_failure" not in data["prepare_build_stream"]
    assert svt_project.catalog_plan("build_stream") == {}


def test_catalog_plan_is_resolved_from_the_checkout(svt_project):
    """The plan comes from the theme config and --list-catalogs, as --configure does."""
    from library.functions import catalog_func  # pylint: disable=import-outside-toplevel
    listed = {"1": "rhel/10.2/slurm_x86_64_no_vast.json"}
    with mock.patch.object(catalog_func, "bundled_catalogs", return_value=(listed, "")):
        plan = svt_project.catalog_plan("catalog_build")
    assert [entry["stage"] for entry in plan["entries"]] == ["catalog_01"]
    assert plan["settings"]["catalogs"] == "all"
    with mock.patch.object(catalog_func, "bundled_catalogs", return_value=({}, "no list")):
        with pytest.raises(SystemExit, match="catalog plan of catalog_build: no list"):
            svt_project.catalog_plan("catalog_build")


# ------------------------------------------------------------- plan check
def _check(expected, remote_result):
    with mock.patch.dict(os.environ, {"SVT_CATALOG_PLAN": expected,
                                      "SVT_OMNIA_INSTALL_PATH": "/root/omnia"}), \
            mock.patch.object(svt_ci, "remote", return_value=remote_result) as remote:
        svt_ci._check_catalog_plan()
    return remote


def test_plan_check_passes_when_the_oim_plan_matches():
    """The OIM plan of this run is the rendered jobs: the check passes."""
    remote = _check(PLAN_VALUE, (0, json.dumps({"entries": ENTRIES}).encode()))
    assert "/root/omnia/test/system_test/reports/catalog_build_plan.json" in \
        remote.call_args[0][0]


@pytest.mark.parametrize("remote_result", [
    (0, json.dumps({"entries": ENTRIES[:1]}).encode()),
    (0, b"not json"),
    (1, b""),
])
def test_plan_check_fails_when_the_oim_plan_differs(tmp_path, monkeypatch, remote_result):
    """Another, unreadable or missing OIM plan fails the job with the fix."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        _check(PLAN_VALUE, remote_result)


def test_plan_check_is_skipped_for_other_themes():
    """Without SVT_CATALOG_PLAN (build_stream) the OIM is not asked."""
    with mock.patch.dict(os.environ, {"SVT_CATALOG_PLAN": ""}), \
            mock.patch.object(svt_ci, "remote") as remote:
        svt_ci._check_catalog_plan()
    remote.assert_not_called()
