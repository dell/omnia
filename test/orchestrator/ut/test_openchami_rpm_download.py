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

"""The OpenCHAMI RPM is fetched from its pinned direct download URL.

The release is pinned, so deploy_openchami must not call the GitHub REST API: anonymous
requests are limited to 60 per hour per IP address, and once the limit is used the
installation fails with HTTP 403 ("API rate limit exceeded").
"""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest
import yaml

pytestmark = pytest.mark.unit

_ROLE = (Path(__file__).resolve().parents[3] / "src" / "orchestrator" / "roles"
         / "deploy_openchami")
_VARS = _ROLE / "vars" / "main.yml"
_TASKS = _ROLE / "tasks" / "configs" / "ochami.yml"


_RPM_VARS = ("openchami_release_repo", "openchami_version", "openchami_rpm_name",
             "openchami_rpm_url")


def _render(values: dict, name: str) -> str:
    """Return the OpenCHAMI RPM variable ``name`` rendered with Jinja from the role vars.

    Only the variables of the RPM download are resolved; the other role variables need
    facts of a real run (hostvars, cluster_name, ...).
    """
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    resolved = {key: values[key] for key in _RPM_VARS}
    for _ in range(len(_RPM_VARS)):
        resolved = {key: env.from_string(value).render(**resolved).strip()
                    for key, value in resolved.items()}
    return resolved[name]


@pytest.fixture(name="role_vars")
def _role_vars():
    return yaml.safe_load(_VARS.read_text(encoding="utf-8"))


def test_rpm_url_is_the_direct_download_of_the_pinned_version(role_vars):
    """The RPM URL is built from the pinned version, with no API lookup."""
    version = role_vars["openchami_version"]
    assert _render(role_vars, "openchami_rpm_name") == f"openchami-{version}.rpm"
    assert _render(role_vars, "openchami_rpm_url") == (
        f"https://github.com/OpenCHAMI/release/releases/download/v{version}/"
        f"openchami-{version}.rpm")


def test_role_does_not_call_the_github_api():
    """Neither the vars nor the tasks of the role reference api.github.com."""
    for path in (_VARS, _TASKS):
        assert "api.github.com" not in path.read_text(encoding="utf-8"), (
            f"{path.name} calls the rate-limited GitHub REST API")


def test_download_task_uses_the_url_var_and_is_skipped_when_present():
    """The download task takes openchami_rpm_url and only runs when the RPM is missing."""
    tasks = yaml.safe_load(_TASKS.read_text(encoding="utf-8"))
    download = next(task for task in tasks
                    if task.get("name") == "Download the OpenCHAMI RPM from GitHub releases")
    assert download["ansible.builtin.get_url"]["url"] == "{{ openchami_rpm_url }}"
    assert download["when"] == "not _openchami_rpm_stat.stat.exists"
