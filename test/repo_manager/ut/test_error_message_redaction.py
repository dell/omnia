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

"""Verify that user-facing errors do not echo exception-controlled text.

Telemetry and repo_manager both define ansible.module_utils.input_validation,
so run this file in its own pytest process.
"""

import builtins
import json
import logging
import subprocess
from contextlib import nullcontext

import pytest
import yaml

import source_loader  # noqa: F401  # pylint: disable=unused-import

# pylint: disable=wrong-import-position,import-error
from ansible.module_utils.input_validation.core import file_utils, validation_engine  # noqa: E402
from ansible.module_utils.repo_manager import parse_and_download  # noqa: E402
from plugins.modules import validate_input, vault_handler  # noqa: E402

SECRET = "S3cr3tValue"


class Failed(Exception):
    """Raised by FakeModule.fail_json."""


class FakeModule:
    """Minimal AnsibleModule stand-in."""

    def __init__(self, params=None):
        self.params = params or {}
        self.check_mode = False

    @staticmethod
    def fail_json(**kwargs):
        """Mimic AnsibleModule.fail_json."""
        raise Failed(kwargs.get("msg"))

    @staticmethod
    def exit_json(**kwargs):
        """Mimic AnsibleModule.exit_json."""
        raise SystemExit(kwargs)


def test_schema_yaml_error_does_not_return_file_content(tmp_path, monkeypatch):
    """A YAML error reaching schema() must not echo its text in returned errors."""
    schema_file = tmp_path / "s.json"
    schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    input_file = tmp_path / "in.yml"
    input_file.write_text("a: 1\n", encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise yaml.scanner.ScannerError(problem=f'password: "{SECRET}')
    monkeypatch.setattr(validation_engine.file_utils, "input_data", boom)
    errors = validation_engine.schema({
        "input_file_path": str(input_file), "schema_file_path": str(schema_file),
        "passwords_set": set(), "omnia_base_dir": str(tmp_path) + "/",
        "project_name": "proj", "logger": logging.getLogger("t"),
        "module": FakeModule(),
    })
    assert errors == [f"Unable to read or parse {input_file}: ScannerError"]


def _run_vault_write(tmp_path, monkeypatch, error):
    credential_file = tmp_path / "creds.yml"
    credential_file.write_text("x: y\n", encoding="utf-8")
    vault_key = tmp_path / ".key"
    vault_key.write_text("k", encoding="utf-8")
    params = {"file_path": str(credential_file), "vault_key": str(vault_key),
              "mode": "write", "data": {"x": "z"}}
    monkeypatch.setattr(vault_handler, "AnsibleModule", lambda **_: FakeModule(params))

    def boom(*_args, **_kwargs):
        raise error
    monkeypatch.setattr(vault_handler, "load_vault_yaml", boom)
    with pytest.raises(Failed) as failure:
        vault_handler.main()
    return str(failure.value)


@pytest.mark.parametrize("error, expected", [
    (yaml.scanner.ScannerError(problem=f"bad {SECRET}"), "ScannerError"),
    (subprocess.CalledProcessError(1, ["ansible-vault", SECRET]), "CalledProcessError"),
    (PermissionError(f"denied {SECRET}"), "PermissionError"),
    (UnicodeDecodeError("utf-8", SECRET.encode(), 0, 1, "bad"), "UnicodeDecodeError"),
])
def test_vault_write_read_failure_reports_type_only(tmp_path, monkeypatch, error, expected):
    """Known read failures keep fail_json and report only the exception type."""
    message = _run_vault_write(tmp_path, monkeypatch, error)
    assert message == f"Failed to read existing credential file: {expected}"
    assert SECRET not in message


def test_vault_write_unexpected_failure_still_fails_cleanly(tmp_path, monkeypatch):
    """Any other exception still ends in fail_json without its text."""
    message = _run_vault_write(tmp_path, monkeypatch, RuntimeError(SECRET))
    assert message == "Failed to read existing credential file: unexpected error"


def test_csv_own_messages_are_unchanged(tmp_path):
    """Messages raised by the validator itself keep their existing text."""
    csv_file = tmp_path / "map.csv"
    csv_file.write_text("", encoding="utf-8")
    with pytest.raises(ValueError) as failure:
        validate_input.validate_csv_structure(str(csv_file))
    assert str(failure.value) == (
        f"CSV validation error: CSV ERROR: Empty file - {csv_file}"
    )


def test_csv_decode_error_reports_type_only(tmp_path):
    """Data-derived decode errors are reported by type, still as ValueError."""
    csv_file = tmp_path / "map.csv"
    csv_file.write_bytes(b"a,b\n\xff\xfe,x\n")
    with pytest.raises(ValueError) as failure:
        validate_input.validate_csv_structure(str(csv_file))
    assert str(failure.value) == "CSV validation error: UnicodeDecodeError"


@pytest.mark.parametrize("error, expected", [
    (PermissionError(f"denied {SECRET}"), "CSV validation error: PermissionError"),
    (RuntimeError(SECRET), "CSV validation error: unexpected error"),
])
def test_csv_read_failures_do_not_echo_exception_text(tmp_path, monkeypatch, error, expected):
    """Read failures and unexpected errors still raise ValueError, without text."""
    csv_file = tmp_path / "map.csv"
    csv_file.write_text("a,b\n", encoding="utf-8")
    real_open = builtins.open

    def failing_open(path, *args, **kwargs):
        if str(path) == str(csv_file):
            raise error
        return real_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", failing_open)
    with pytest.raises(ValueError) as failure:
        validate_input.validate_csv_structure(str(csv_file))
    assert str(failure.value) == expected
    assert SECRET not in str(failure.value)


def test_input_data_unexpected_error_logs_type_only(tmp_path, monkeypatch, caplog):
    """Unexpected JSON-read failures still return None without logging text."""
    json_file = tmp_path / "input.json"
    json_file.write_text("{}", encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(file_utils.json, "load", boom)
    logger = logging.getLogger("t")
    with caplog.at_level(logging.ERROR, logger="t"):
        result, extension = file_utils.input_data(
            str(json_file), str(tmp_path) + "/", "proj", logger, FakeModule()
        )
    assert result is None
    assert extension == ".json"
    assert any(
        record.message == f"Unexpected error reading {json_file}: RuntimeError"
        for record in caplog.records
    )
    assert SECRET not in caplog.text


def test_write_status_to_file_keeps_running_when_mirror_index_update_fails(
        tmp_path, monkeypatch, caplog):
    """Mirror-index update failures stay warnings and do not fail status writes."""
    status_file = tmp_path / "rhel" / "10.0" / "x86_64" / "software" / "status.csv"
    mirror_index = tmp_path / "rhel" / "10.0" / "mirror_status" / "pulp_mirror_index.json"
    mirror_index.parent.mkdir(parents=True)
    mirror_index.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        parse_and_download,
        "load_mirror_index",
        lambda *_args, **_kwargs: {"MirrorIndex": {"packages": {}}},
    )
    monkeypatch.setattr(
        parse_and_download,
        "find_mirror_entry",
        lambda *_args, **_kwargs: (
            "identity",
            {
                "package_name": "pkg",
                "type": "rpm",
                "version": "",
                "arch": "x86_64",
                "source": "",
                "catalogs": [],
                "repo_name": "repo",
            },
        ),
    )
    monkeypatch.setattr(parse_and_download, "update_mirror_index_entry", lambda *_args, **_kwargs: None)

    def fail_save(*_args, **_kwargs):
        raise OSError(SECRET)

    monkeypatch.setattr(parse_and_download, "save_mirror_index", fail_save)
    logger = logging.getLogger("t")
    with caplog.at_level(logging.WARNING, logger="t"):
        parse_and_download.write_status_to_file(
            str(status_file), "pkg", "rpm", "Success", logger, nullcontext(), "repo"
        )
    assert status_file.exists()
    assert any(
        record.message == "Failed to update mirror index for package 'pkg': OSError"
        for record in caplog.records
    )
    assert SECRET not in caplog.text
