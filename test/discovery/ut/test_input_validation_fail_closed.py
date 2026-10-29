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

"""Negative tests: Discovery validation must fail closed.

Covers empty schemas, unanchored patterns and vault-encrypted inputs. The
module runs through the ansible CLI from the collection root so it resolves
exactly as in production.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

DISCOVERY_ROOT = Path(__file__).resolve().parents[3] / "src" / "discovery"
SCHEMA_DIR = (
    DISCOVERY_ROOT / "plugins" / "module_utils" / "discovery_validation" / "schema"
)
RESULT_PATTERN = re.compile(r"\|\s*(\w+)!?\s*=>\s*(\{.*\})\s*$", re.DOTALL)

pytestmark = pytest.mark.skipif(
    shutil.which("ansible") is None or shutil.which("ansible-vault") is None,
    reason="ansible CLI not installed",
)


def _validate(project, schema_dir, log_dir):
    """Run validate_discovery_config and return (result, stdout)."""
    args = {
        "input_project_dir": str(project),
        "schema_dir": str(schema_dir),
        "log_dir": str(log_dir),
    }
    proc = subprocess.run(
        ["ansible", "localhost", "-m", "validate_discovery_config", "-a", json.dumps(args)],
        cwd=DISCOVERY_ROOT, env=dict(os.environ, ANSIBLE_LOG_PATH=os.devnull),
        capture_output=True, text=True, check=False, timeout=120,
    )
    match = RESULT_PATTERN.search(proc.stdout)
    assert match, f"No module result in output:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(match.group(2)), proc.stdout


def _encrypt(path, content, key_file):
    """Write content to path and vault-encrypt it with key_file."""
    path.write_text(content, encoding="utf-8")
    subprocess.run(
        ["ansible-vault", "encrypt", str(path), "--vault-password-file", str(key_file)],
        check=True, capture_output=True,
    )


def _names(paths):
    return [Path(path).name for path in paths]


@pytest.fixture(name="dirs")
def fixture_dirs(tmp_path):
    """Return (project, schema, logs) directories."""
    project, schema = tmp_path / "project", tmp_path / "schema"
    project.mkdir()
    schema.mkdir()
    return project, schema, tmp_path / "logs"


def test_empty_schema_fails_closed(dirs):
    """An empty schema can never make an input file valid."""
    project, schema, logs = dirs
    (schema / "discovery_config.json").write_text("{}", encoding="utf-8")
    (schema / "network_spec.json").write_text('{"type": "object"}', encoding="utf-8")
    (project / "discovery_config.yml").write_text("a: 1\n", encoding="utf-8")
    (project / "network_spec.yml").write_text("a: 1\n", encoding="utf-8")
    result, _ = _validate(project, schema, logs)
    assert result["validation_failed"]
    assert "discovery_config.yml" in _names(result["invalid_files"])
    assert (
        "discovery_config.yml: Schema is empty; refusing to treat input as valid"
        in result["errors"]
    )


def test_unanchored_pattern_must_match_whole_value(dirs):
    """A pattern without anchors cannot be satisfied by a partial match."""
    project, schema, logs = dirs
    (schema / "discovery_config.json").write_text('{"type": "object"}', encoding="utf-8")
    (schema / "network_spec.json").write_text(json.dumps({
        "type": "object",
        "properties": {"ip": {"type": "string", "pattern": "[0-9]+"}},
    }), encoding="utf-8")
    (project / "discovery_config.yml").write_text("a: 1\n", encoding="utf-8")
    (project / "network_spec.yml").write_text('ip: "12abc"\n', encoding="utf-8")
    result, _ = _validate(project, schema, logs)
    assert "network_spec.yml" in _names(result["invalid_files"])
    assert "network_spec.yml: Property 'ip' has an invalid value" in result["errors"]


def test_encrypted_input_is_decrypted_and_validated(dirs):
    """A vault file with its key is validated and its values are masked."""
    project, _, logs = dirs
    (project / ".network_spec_key").write_text("k3", encoding="utf-8")
    _encrypt(project / "network_spec.yml", 'Networks: "TopSecretNet"\n',
             project / ".network_spec_key")
    result, stdout = _validate(project, SCHEMA_DIR, logs)
    assert "network_spec.yml" in _names(result["invalid_files"])
    assert "network_spec.yml: Property 'Networks' must be of type 'array'" in result["errors"]
    log_text = "".join(p.read_text(encoding="utf-8") for p in logs.glob("*"))
    assert "TopSecretNet" not in stdout
    assert "TopSecretNet" not in log_text


def test_encrypted_input_without_key_is_unvalidated(dirs, tmp_path):
    """Without a vault key the file is reported unvalidated and validation fails."""
    project, _, logs = dirs
    (tmp_path / "other_key").write_text("k3", encoding="utf-8")
    _encrypt(project / "network_spec.yml", "Networks: []\n", tmp_path / "other_key")
    result, _ = _validate(project, SCHEMA_DIR, logs)
    assert _names(result["unvalidated_files"]) == ["network_spec.yml"]
    assert "network_spec.yml" not in _names(result["valid_files"])
    assert result["validation_failed"] is True
