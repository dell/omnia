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

"""Tests for telemetry input validation vault handling and error reporting.

Telemetry and repo_manager both define ansible.module_utils.input_validation,
so run this file in its own pytest process.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path

import pytest
import ansible.module_utils

MODULE_UTILS = (
    Path(__file__).resolve().parents[3] / "src" / "telemetry" / "plugins" / "module_utils"
)
if str(MODULE_UTILS) not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.insert(0, str(MODULE_UTILS))

# pylint: disable=wrong-import-position,import-error
from ansible.module_utils.input_validation.core import (  # noqa: E402
    data_fetch, data_validation, validation_utils,
)

pytestmark = pytest.mark.skipif(
    shutil.which("ansible-vault") is None, reason="ansible-vault not installed"
)

KEY_NAME = ".test_key"


class Failed(Exception):
    """Raised by FakeModule.fail_json."""


class FakeModule:
    """Minimal AnsibleModule stand-in."""

    @staticmethod
    def fail_json(**kwargs):
        """Mimic AnsibleModule.fail_json."""
        raise Failed(kwargs.get("msg"))


def _make_vault(tmp_path, content, key="secret"):
    project = tmp_path / "proj"
    project.mkdir()
    (project / KEY_NAME).write_text(key, encoding="utf-8")
    vault_file = project / "creds.yml"
    vault_file.write_text(content, encoding="utf-8")
    subprocess.run(
        ["ansible-vault", "encrypt", str(vault_file),
         "--vault-password-file", str(project / KEY_NAME)],
        check=True, capture_output=True,
    )
    return str(tmp_path) + "/", "proj", str(vault_file)


@pytest.fixture(autouse=True)
def _vault_key_name(monkeypatch):
    monkeypatch.setattr(validation_utils.config, "get_vault_password", lambda _f: KEY_NAME)


def _wrong_key(base, project):
    (Path(base) / project / KEY_NAME).write_text("wrong", encoding="utf-8")


def test_process_encrypted_file_reads_without_touching_file(tmp_path):
    """Vaulted data is parsed and the file on disk stays encrypted and unchanged."""
    base, project, vault_file = _make_vault(tmp_path, "password: abc\nname: x\n")
    before = Path(vault_file).read_bytes()
    data = validation_utils.process_encrypted_file(
        vault_file, base, project, logging.getLogger("t"), FakeModule()
    )
    assert data == {"password": "abc", "name": "x"}
    assert Path(vault_file).read_bytes() == before
    assert before.startswith(b"$ANSIBLE_VAULT")


def test_process_encrypted_file_wrong_key_fails_and_file_untouched(tmp_path):
    """A failed view reports an error and leaves the file encrypted."""
    base, project, vault_file = _make_vault(tmp_path, "a: 1\n")
    _wrong_key(base, project)
    before = Path(vault_file).read_bytes()
    with pytest.raises(Failed):
        validation_utils.process_encrypted_file(
            vault_file, base, project, logging.getLogger("t"), FakeModule()
        )
    assert Path(vault_file).read_bytes() == before


def test_process_encrypted_file_malformed_yaml_fails_and_file_untouched(tmp_path):
    """Malformed YAML inside the vault never leaves the file decrypted."""
    base, project, vault_file = _make_vault(tmp_path, "a: [unclosed\n  b: : :\n")
    before = Path(vault_file).read_bytes()
    with pytest.raises(Failed):
        validation_utils.process_encrypted_file(
            vault_file, base, project, logging.getLogger("t"), FakeModule()
        )
    assert Path(vault_file).read_bytes() == before
    assert before.startswith(b"$ANSIBLE_VAULT")


def test_yml_line_number_on_vaulted_file(tmp_path):
    """Line lookup works on a vaulted file without modifying it."""
    base, project, vault_file = _make_vault(tmp_path, "first: 1\nsecond: 2\n")
    before = Path(vault_file).read_bytes()
    assert data_fetch.yml_line_number(vault_file, "second", base, project) == (2, True)
    assert data_fetch.yml_line_number(vault_file, "missing", base, project) is None
    assert Path(vault_file).read_bytes() == before


def test_yml_line_number_vault_failure_raises_and_file_untouched(tmp_path):
    """A vault failure raises VaultError and leaves the file encrypted."""
    base, project, vault_file = _make_vault(tmp_path, "a: 1\n")
    _wrong_key(base, project)
    before = Path(vault_file).read_bytes()
    with pytest.raises(validation_utils.VaultError):
        data_fetch.yml_line_number(vault_file, "a", base, project)
    assert Path(vault_file).read_bytes() == before


def test_no_in_place_decrypt_helpers_remain():
    """The decrypt-in-place helpers are gone."""
    assert not hasattr(validation_utils, "decrypt_file")
    assert not hasattr(validation_utils, "encrypt_file")


def _schema_config(tmp_path, data):
    schema_file = tmp_path / "s.json"
    schema_file.write_text(json.dumps({
        "type": "object",
        "properties": {"a": {"type": "integer"}, "b": {"type": "integer"},
                       "c": {"type": "integer"}},
    }), encoding="utf-8")
    input_file = tmp_path / "in.yml"
    input_file.write_text(data, encoding="utf-8")
    return {
        "input_file_path": str(input_file), "schema_file_path": str(schema_file),
        "passwords_set": set(), "omnia_base_dir": str(tmp_path) + "/",
        "project_name": "proj", "logger": logging.getLogger("t"), "module": FakeModule(),
    }


def test_schema_reports_all_errors_when_line_lookup_fails(tmp_path, monkeypatch):
    """A failing line-number lookup must not drop the remaining errors."""
    def boom(*_args, **_kwargs):
        raise RuntimeError("lookup failed")
    monkeypatch.setattr(data_validation.get, "yml_line_number", boom)
    errors = data_validation.schema(_schema_config(tmp_path, "a: x\nb: y\nc: z\n"))
    for key in ("a", "b", "c"):
        assert any(f"Validation Error at {key}:" in e for e in errors)
    assert not any("unexpected error" in e for e in errors)


def test_logic_returns_empty_list_on_success(tmp_path, monkeypatch):
    """logic() returns an empty list, not False, when validation passes."""
    config = _schema_config(tmp_path, "a: 1\n")
    config["module_utils_base"] = str(MODULE_UTILS)
    monkeypatch.setattr(
        data_validation.logical_validation, "validate_input_logic", lambda *a, **k: []
    )
    assert data_validation.logic(config) == []


def test_logic_handles_error_dicts_missing_fields(tmp_path, monkeypatch):
    """Error dicts without the mandatory keys must not crash logic()."""
    config = _schema_config(tmp_path, "a: 1\n")
    config["module_utils_base"] = str(MODULE_UTILS)
    monkeypatch.setattr(
        data_validation.logical_validation, "validate_input_logic",
        lambda *a, **k: [{"error_key": "a"}, {"error_msg": "m"}, {}],
    )
    errors = data_validation.logic(config)
    assert isinstance(errors, list) and len(errors) == 3


def test_schema_oserror_is_reported_and_logged_with_traceback(tmp_path, monkeypatch, caplog):
    """An I/O failure gets a specific message and a logged stack trace."""
    config = _schema_config(tmp_path, "a: 1\n")

    def boom(*_args, **_kwargs):
        raise OSError("disk")
    monkeypatch.setattr(data_validation.get, "input_data", boom)
    with caplog.at_level(logging.ERROR, logger="t"):
        errors = data_validation.schema(config)
    assert any("Unable to read or parse" in e and config["input_file_path"] in e for e in errors)
    assert any(r.exc_info for r in caplog.records)


def test_schema_unexpected_error_names_file_and_logs_traceback(tmp_path, monkeypatch, caplog):
    """The fallback handler names the file and logs a stack trace."""
    config = _schema_config(tmp_path, "a: 1\n")

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(data_validation.get, "input_data", boom)
    with caplog.at_level(logging.ERROR, logger="t"):
        errors = data_validation.schema(config)
    assert any(config["input_file_path"] in e and "boom" in e for e in errors)
    assert any(r.exc_info for r in caplog.records)


def test_run_subprocess_timeout_returns_distinct_code(monkeypatch):
    """A timed-out command returns rc 124 and a clear message, not 127."""
    def timed_out(cmd, **_kwargs):
        raise subprocess.TimeoutExpired(cmd, 5)
    monkeypatch.setattr(validation_utils.subprocess, "run", timed_out)
    result = validation_utils.run_subprocess(["sleep", "10"], timeout=5)
    assert result.returncode == 124
    assert "timed out after 5s" in result.stderr


def test_run_subprocess_missing_command_returns_127():
    """A command that cannot be started still returns rc 127."""
    result = validation_utils.run_subprocess(["definitely-not-a-real-command-xyz"])
    assert result.returncode == 127
