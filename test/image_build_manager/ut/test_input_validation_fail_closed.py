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
    """Without a vault key the credentials file is never counted as valid."""
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "other_key").write_text("k2", encoding="utf-8")
    _encrypt(project / CREDENTIALS, 's3_secret_key: "abcdefgh1"\n', tmp_path / "other_key")
    result, _ = _validate(project, tmp_path / "logs")
    assert _names(result["unvalidated_files"]) == [CREDENTIALS]
    assert CREDENTIALS not in _names(result["valid_files"])
