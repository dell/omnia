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

"""Negative tests: Image Build validation must not treat vault files as valid.

The module runs through the ansible CLI from the collection root so it and
its module_utils resolve exactly as in production.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

IMAGE_BUILD_ROOT = Path(__file__).resolve().parents[3] / "src" / "image_build_manager"
SCHEMA_DIR = IMAGE_BUILD_ROOT / "plugins" / "module_utils" / "input_validation" / "schema"
CREDENTIALS = "image_build_credentials.yml"
KEY = ".image_build_credentials_key"
RESULT_PATTERN = re.compile(r"\|\s*(\w+)!?\s*=>\s*(\{.*\})\s*$", re.DOTALL)

pytestmark = pytest.mark.skipif(
    shutil.which("ansible") is None or shutil.which("ansible-vault") is None,
    reason="ansible CLI not installed",
)


def _encrypt(path, content, key_file):
    """Write content to path and vault-encrypt it with key_file."""
    path.write_text(content, encoding="utf-8")
    subprocess.run(
        ["ansible-vault", "encrypt", str(path), "--vault-password-file", str(key_file)],
        check=True, capture_output=True,
    )


def _validate(project, log_dir):
    """Run validate_image_build_config and return (result, stdout)."""
    args = {
        "input_project_dir": str(project),
        "schema_dir": str(SCHEMA_DIR),
        "log_dir": str(log_dir),
    }
    proc = subprocess.run(
        ["ansible", "localhost", "-m", "validate_image_build_config", "-a", json.dumps(args)],
        cwd=IMAGE_BUILD_ROOT, env=dict(os.environ, ANSIBLE_LOG_PATH=os.devnull),
        capture_output=True, text=True, check=False, timeout=120,
    )
    match = RESULT_PATTERN.search(proc.stdout)
    assert match, f"No module result in output:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(match.group(2)), proc.stdout


def _names(paths):
    return [Path(path).name for path in paths]


def test_encrypted_credentials_are_validated_with_masked_errors(tmp_path):
    """Decrypted credentials are schema-validated and the secret is masked."""
    project = tmp_path / "project"
    project.mkdir()
    (project / KEY).write_text("k2", encoding="utf-8")
    _encrypt(project / CREDENTIALS, 's3_secret_key: "abc"\n', project / KEY)
    result, stdout = _validate(project, tmp_path / "logs")
    assert CREDENTIALS in _names(result["invalid_files"])
    assert CREDENTIALS not in _names(result["valid_files"])
    assert "image_build_credentials.yml.s3_secret_key: ******** is too short" in result["errors"]
    logs = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "logs").glob("*"))
    assert "'abc'" not in stdout
    assert "'abc'" not in logs


def test_encrypted_credentials_without_key_are_unvalidated(tmp_path):
    """Without a vault key the credentials file is never counted as valid and validation fails."""
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "other_key").write_text("k2", encoding="utf-8")
    _encrypt(project / CREDENTIALS, 's3_secret_key: "abcdefgh1"\n', tmp_path / "other_key")
    result, _ = _validate(project, tmp_path / "logs")
    assert _names(result["unvalidated_files"]) == [CREDENTIALS]
    assert CREDENTIALS not in _names(result["valid_files"])
    assert result["validation_failed"] is True



def test_uncollected_template_values_are_not_errors(tmp_path):
    """The credential template's empty values are placeholders, not errors."""
    project = tmp_path / "project"
    project.mkdir()
    (project / KEY).write_text("k2", encoding="utf-8")
    _encrypt(project / CREDENTIALS,
             's3_access_id: ""\ns3_secret_key: ""\naarch64_ssh_password: ""\n',
             project / KEY)
    result, _ = _validate(project, tmp_path / "logs")
    assert CREDENTIALS in _names(result["valid_files"])
    assert not any(CREDENTIALS in error for error in result["errors"])

def test_standalone_x86_64_build_accepts_its_play_tags():
    """build_image_x86_64.yml runs the tag guard standalone; its play tags pass."""
    vars_file = IMAGE_BUILD_ROOT / "roles" / "image_build_setup" / "vars" / "main.yml"
    supported = set(yaml.safe_load(vars_file.read_text(encoding="utf-8"))["supported_tags"])
    playbook = yaml.safe_load(
        (IMAGE_BUILD_ROOT / "playbooks" / "build" / "build_image_x86_64.yml").read_text(
            encoding="utf-8"
        )
    )
    play_tags, extra, roles = set(), set(), set()

    def _add(tags):
        play_tags.update([tags] if isinstance(tags, str) else (tags or []))

    for play in playbook:
        _add(play.get("tags"))
        for entry in play.get("roles", []):
            roles.add(entry["role"] if isinstance(entry, dict) else entry)
        for task in play.get("tasks", []):
            _add(task.get("tags"))
            role = task.get("ansible.builtin.include_role") or {}
            roles.add(role.get("name"))
            if role.get("name") == "image_build_setup":
                extra.update((task.get("vars") or {}).get("additional_supported_tags", []))
    for role in filter(None, roles):
        for tasks_file in (IMAGE_BUILD_ROOT / "roles" / role / "tasks").glob("*.yml"):
            for task in yaml.safe_load(tasks_file.read_text(encoding="utf-8")) or []:
                _add(task.get("tags"))
    assert play_tags - {"always", "never"} - supported - extra == set()


def test_standalone_aarch64_build_accepts_its_play_tags():
    """build_image_aarch64.yml runs the tag guard standalone; its play tags pass."""
    vars_file = IMAGE_BUILD_ROOT / "roles" / "image_build_setup" / "vars" / "main.yml"
    supported = set(yaml.safe_load(vars_file.read_text(encoding="utf-8"))["supported_tags"])
    playbook = yaml.safe_load(
        (IMAGE_BUILD_ROOT / "playbooks" / "build" / "build_image_aarch64.yml").read_text(
            encoding="utf-8"
        )
    )
    play_tags, extra, roles = set(), set(), set()

    def _add(tags):
        play_tags.update([tags] if isinstance(tags, str) else (tags or []))

    for play in playbook:
        _add(play.get("tags"))
        for entry in play.get("roles", []):
            roles.add(entry["role"] if isinstance(entry, dict) else entry)
        for task in play.get("tasks", []):
            _add(task.get("tags"))
            role = task.get("ansible.builtin.include_role") or {}
            roles.add(role.get("name"))
            if role.get("name") == "image_build_setup":
                extra.update((task.get("vars") or {}).get("additional_supported_tags", []))
    for role in filter(None, roles):
        for tasks_file in (IMAGE_BUILD_ROOT / "roles" / role / "tasks").glob("*.yml"):
            for task in yaml.safe_load(tasks_file.read_text(encoding="utf-8")) or []:
                _add(task.get("tags"))
    assert play_tags - {"always", "never"} - supported - extra == set()
