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

"""Regression tests for standalone GitLab cleanup mode guards."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

SRC = Path(__file__).resolve().parents[5] / "src" / "build_stream"
PLAYBOOKS = SRC / "playbooks" / "cleanup"
ANSIBLE = shutil.which("ansible-playbook")

pytestmark = pytest.mark.skipif(ANSIBLE is None, reason="ansible-playbook is not installed")


def run_playbook(tmp_path, playbook_name, mode):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "build_stream_config.yml").write_text(
        yaml.safe_dump({"gitlab_mode": mode}), encoding="utf-8",
    )
    extra = {
        "build_stream_setup_done": True,
        "input_project_dir": str(input_dir),
        "config_file_status": True,
    }
    env = dict(
        os.environ,
        ANSIBLE_ROLES_PATH=str(SRC / "roles"),
        ANSIBLE_NOCOLOR="1",
        ANSIBLE_HOME=str(tmp_path / ".ansible"),
        ANSIBLE_LOCALHOST_WARNING="False",
    )
    return subprocess.run(
        [ANSIBLE, str(PLAYBOOKS / playbook_name), "-i", "localhost,", "-e", json.dumps(extra)],
        capture_output=True,
        text=True,
        env=env,
        cwd=SRC,
        check=False,
        timeout=60,
    )


@pytest.mark.parametrize(("playbook_name", "mode"), [
    ("cleanup_external_gitlab.yml", "hosted"),
    ("cleanup_hosted_gitlab.yml", "external"),
])
def test_wrong_mode_stops_all_cleanup_plays(tmp_path, playbook_name, mode):
    result = run_playbook(tmp_path, playbook_name, mode)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "undefined" not in output.lower()
    assert "Initialise external cleanup state" not in output
    assert "Wait for the SSH connection to the GitLab host" not in output


@pytest.mark.parametrize("playbook_name", [
    "cleanup_external_gitlab.yml",
    "cleanup_hosted_gitlab.yml",
])
@pytest.mark.parametrize("mode", ["", "invalid"])
def test_missing_or_invalid_mode_fails_closed(tmp_path, playbook_name, mode):
    result = run_playbook(tmp_path, playbook_name, mode)
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "requires gitlab_mode to be explicitly set" in output
