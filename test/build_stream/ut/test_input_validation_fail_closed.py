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

"""Negative tests: Build Stream validation must not treat vault files as valid.

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

BUILD_STREAM_ROOT = Path(__file__).resolve().parents[3] / "src" / "build_stream"
SCHEMA_DIR = BUILD_STREAM_ROOT / "plugins" / "module_utils" / "input_validation" / "schema"
CREDENTIALS = "build_stream_credentials.yml"
KEY = ".build_stream_credentials_key"
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
    """Run validate_build_stream_config and return its JSON result."""
    args = {
        "input_project_dir": str(project),
        "schema_dir": str(SCHEMA_DIR),
        "log_dir": str(log_dir),
    }
    proc = subprocess.run(
        ["ansible", "localhost", "-m", "validate_build_stream_config", "-a", json.dumps(args)],
        cwd=BUILD_STREAM_ROOT, env=dict(os.environ, ANSIBLE_LOG_PATH=os.devnull),
        capture_output=True, text=True, check=False, timeout=120,
    )
    match = RESULT_PATTERN.search(proc.stdout)
    assert match, f"No module result in output:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(match.group(2)), proc.stdout


def _names(paths):
    return [Path(path).name for path in paths]


@pytest.fixture(name="project")
def fixture_project(tmp_path):
    """Return an empty project directory."""
    project = tmp_path / "project"
    project.mkdir()
    return project


def test_encrypted_credentials_are_schema_validated(project, tmp_path):
    """Decrypted vault content is validated rather than assumed valid."""
    (project / KEY).write_text("k1", encoding="utf-8")
    _encrypt(project / CREDENTIALS,
             'gitlab_root_password: "dummy_secret"\ngitlab_ssh_password: ""\n',
             project / KEY)
    result, _ = _validate(project, tmp_path / "logs")
    assert CREDENTIALS in _names(result["invalid_files"])
    assert CREDENTIALS not in _names(result["valid_files"])
    assert any("gitlab_ssh_password" in error for error in result["errors"])


def test_encrypted_file_without_key_is_reported_unvalidated(project, tmp_path):
    """Without a vault key the file is listed as unvalidated, never valid."""
    (tmp_path / "other_key").write_text("k1", encoding="utf-8")
    _encrypt(project / CREDENTIALS, 'gitlab_root_password: "dummy_secret"\n',
             tmp_path / "other_key")
    result, _ = _validate(project, tmp_path / "logs")
    assert _names(result["unvalidated_files"]) == [CREDENTIALS]
    assert CREDENTIALS not in _names(result["valid_files"])


def test_encrypted_file_with_wrong_key_fails(project, tmp_path):
    """A vault key that cannot decrypt the file is a validation error."""
    (tmp_path / "real_key").write_text("k1", encoding="utf-8")
    _encrypt(project / CREDENTIALS, 'gitlab_root_password: "dummy_secret"\n',
             tmp_path / "real_key")
    (project / KEY).write_text("WRONG", encoding="utf-8")
    result, _ = _validate(project, tmp_path / "logs")
    assert CREDENTIALS in _names(result["invalid_files"])
    assert any("Unable to decrypt vault file" in error for error in result["errors"])


def test_decrypted_secret_values_are_masked(project, tmp_path):
    """Secret values from decrypted files never reach module output or logs."""
    (project / KEY).write_text("k1", encoding="utf-8")
    _encrypt(project / CREDENTIALS,
             'gitlab_root_password: "dummy_secret"\ngitlab_ssh_password: "x"\n'
             "postgres_user: 98765\n",
             project / KEY)
    result, stdout = _validate(project, tmp_path / "logs")
    assert any("postgres_user" in error for error in result["errors"])
    logs = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "logs").glob("*"))
    for secret in ("dummy_secret", "98765"):
        assert secret not in stdout
        assert secret not in logs
