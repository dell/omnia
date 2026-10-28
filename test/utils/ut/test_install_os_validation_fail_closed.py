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

"""Negative tests: validate_install_os_config must fail closed on bad tags.

The role runs through ansible-playbook from the utils collection root so the
role resolves exactly as in production. The input directory is intentionally
empty; selected modes therefore stop at the missing-config check.
"""

import os
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)

PLAYBOOK = """\
- hosts: localhost
  connection: local
  gather_facts: false
  tags: always
  vars:
    input_project_dir: {input_dir}
  roles:
    - validate_install_os_config
"""


def _run_role(src_dir, tmp_path, tags):
    """Run the validation role with the given --tags and return combined output."""
    playbook = tmp_path / "validate.yml"
    playbook.write_text(
        PLAYBOOK.format(input_dir=tmp_path / "input"), encoding="utf-8"
    )
    env = dict(os.environ, ANSIBLE_LOG_PATH=os.devnull, ANSIBLE_STDOUT_CALLBACK="default")
    proc = subprocess.run(
        ["ansible-playbook", str(playbook), "--tags", tags],
        cwd=src_dir, env=env, capture_output=True, text=True,
        check=False, timeout=120,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_unknown_tag_fails_before_validation_is_skipped(src_dir, tmp_path):
    """A tag that selects no install_os mode fails instead of passing."""
    returncode, output = _run_role(src_dir, tmp_path, "iucghewqiug")
    assert returncode != 0
    assert "No install_os validation mode matches" in output


def test_install_os_tag_selects_full_validation(src_dir, tmp_path):
    """The utils.yml install_os tag enables every mode and reaches file checks."""
    returncode, output = _run_role(src_dir, tmp_path, "install_os")
    assert returncode != 0
    assert "No install_os validation mode matches" not in output
    assert "install_os_config.yml not found" in output


@pytest.mark.parametrize("tag", ["build_iso", "deploy", "generate_ks"])
def test_single_mode_tag_passes_mode_gate(src_dir, tmp_path, tag):
    """Each documented mode tag is accepted by the mode gate."""
    returncode, output = _run_role(src_dir, tmp_path, tag)
    assert returncode != 0
    assert "No install_os validation mode matches" not in output
    assert "install_os_config.yml not found" in output
