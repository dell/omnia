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

"""Negative tests: Orchestrator validation must not treat vault files as valid.

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

ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[3] / "src" / "orchestrator"
SCHEMA_DIR = (
    ORCHESTRATOR_ROOT / "plugins" / "module_utils" / "orchestrator_validation" / "schema"
)
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
    """Run validate_orchestrator_config and return (result, stdout)."""
    args = {
        "input_project_dir": str(project),
        "schema_dir": str(SCHEMA_DIR),
        "log_dir": str(log_dir),
    }
    proc = subprocess.run(
        ["ansible", "localhost", "-m", "validate_orchestrator_config", "-a", json.dumps(args)],
        cwd=ORCHESTRATOR_ROOT, env=dict(os.environ, ANSIBLE_LOG_PATH=os.devnull),
        capture_output=True, text=True, check=False, timeout=120,
    )
    match = RESULT_PATTERN.search(proc.stdout)
    assert match, f"No module result in output:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(match.group(2)), proc.stdout


def _names(paths):
    return [Path(path).name for path in paths]


def test_encrypted_input_without_key_is_unvalidated(tmp_path):
    """ORCH_UT_102: An undecryptable vault input is never reported valid and validation fails."""
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "other_key").write_text("k4", encoding="utf-8")
    _encrypt(project / "omnia_config.yml", "x: 1\n", tmp_path / "other_key")
    result, _ = _validate(project, tmp_path / "logs")
    assert _names(result["unvalidated_files"]) == ["omnia_config.yml"]
    assert "omnia_config.yml" not in _names(result["valid_files"])
    assert result["validation_failed"] is True


def test_encrypted_input_is_decrypted_and_validated(tmp_path):
    """ORCH_UT_103: A vault input with its key is schema-validated."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".security_config_key").write_text("k5", encoding="utf-8")
    _encrypt(project / "security_config.yml", 'x: "OrchSecretValue"\n',
             project / ".security_config_key")
    result, _ = _validate(project, tmp_path / "logs")
    assert "security_config.yml" in _names(result["invalid_files"])
    assert any(
        error.startswith("security_config.yml:") for error in result["errors"]
    )


def test_decrypted_secret_values_are_masked(tmp_path):
    """ORCH_UT_104: Decrypted values never reach module output or logs."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".security_config_key").write_text("k5", encoding="utf-8")
    _encrypt(project / "security_config.yml",
             'ldap_connection_type: "OrchSecretValue"\n',
             project / ".security_config_key")
    result, stdout = _validate(project, tmp_path / "logs")
    assert "security_config.yml" in _names(result["invalid_files"])
    logs = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "logs").glob("*"))
    assert "OrchSecretValue" not in stdout
    assert "OrchSecretValue" not in logs
