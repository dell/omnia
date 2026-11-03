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
import re
import shutil
import subprocess

import pytest
import yaml

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


def test_supported_tags_cover_public_and_play_tags(src_dir):
    """utils_setup guards utils.yml and install_os.yml; their tags all pass."""
    vars_file = src_dir / "roles" / "utils_setup" / "vars" / "main.yml"
    supported = set(yaml.safe_load(vars_file.read_text(encoding="utf-8"))["supported_tags"])
    # Also collect additional_supported_tags from each playbook
    for name in ("utils.yml", "install_os.yml"):
        playbook = yaml.safe_load((src_dir / "playbooks" / name).read_text(encoding="utf-8"))
        for play in playbook:
            if isinstance(play, dict) and "roles" in play:
                for role in play["roles"]:
                    if isinstance(role, dict) and "role" in role and role["role"] == "utils_setup":
                        if "vars" in role and "additional_supported_tags" in role["vars"]:
                            supported.update(role["vars"]["additional_supported_tags"])
    omnia_sh = (src_dir.parent / "main" / "omnia.sh").read_text(encoding="utf-8")
    block = omnia_sh.split("Public tags by domain", 1)[1]
    expected = set(re.search(r"^\s+utils:\s+(.+)$", block, re.M).group(1).split())
    for name in ("utils.yml", "install_os.yml"):
        for play in yaml.safe_load((src_dir / "playbooks" / name).read_text(encoding="utf-8")):
            tags = play.get("tags") or []
            expected.update([tags] if isinstance(tags, str) else tags)
    referenced = set()
    pattern = re.compile(r"['\"]([a-z][a-z0-9_]+)['\"]\s+in\s+\(?\s*ansible_run_tags")
    for path in src_dir.rglob("*.yml"):
        referenced.update(pattern.findall(path.read_text(encoding="utf-8")))
    assert (expected | referenced) - {"always", "never", "all"} - supported == set()
