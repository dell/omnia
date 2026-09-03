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

"""Regression tests for omnia-auto Checkmarx remediations."""
# Unit tests intentionally exercise private security-boundary helpers.
# pylint: disable=protected-access,too-few-public-methods

import json
import os
import secrets
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

_PLUGIN_ROOT = Path(__file__).resolve().parent
_DISTRIBUTED_WHEEL = (
    _PLUGIN_ROOT / "dist" / "omnia_auto-1.0.0-py3-none-any.whl"
)
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

import pytest
import yaml

from omnia_auto.functions import credential_func
from omnia_auto.functions import host_func
from omnia_auto.functions import process_security
from omnia_auto.functions import runner_func
from omnia_auto.functions import sync_func
from omnia_auto.functions import validation_runner


def test_behavior_tests_import_local_plugin_source():
    """Fail clearly if an installed stale package shadows local changes."""
    expected_root = (_PLUGIN_ROOT / "omnia_auto").resolve()
    for module in (
        credential_func,
        host_func,
        process_security,
        runner_func,
        sync_func,
        validation_runner,
    ):
        assert Path(module.__file__).resolve().is_relative_to(expected_root)


def _runner(tmp_path):
    """Create a runner with trusted tags, suites, and markers."""
    (tmp_path / "fvt" / "deploy" / "sources").mkdir(parents=True)
    (tmp_path / "nft").mkdir()
    (tmp_path / "ut").mkdir()
    return validation_runner.ValidationRunner(
        "telemetry",
        script_dir=str(tmp_path),
        domain_config={
            "tags": ["deploy"],
            "markers": ["sanity", "source"],
            "suites": {"deploy": ["sources"]},
        },
    )


def _use_private_ansible_temp(tmp_path, monkeypatch):
    """Keep Ansible's local scratch data inside an isolated private path."""
    ansible_temp = tmp_path / "ansible-local"
    ansible_temp.mkdir(mode=0o700)
    monkeypatch.setenv("ANSIBLE_LOCAL_TEMP", str(ansible_temp))


@pytest.mark.parametrize(
    "module_name",
    [
        "credential_func.py",
        "host_func.py",
        "process_security.py",
        "runner_func.py",
        "sync_func.py",
        "validation_runner.py",
    ],
)
def test_distributed_wheel_contains_remediated_source(module_name):
    """Keep the tracked consumer wheel synchronized with package source."""
    source_path = _PLUGIN_ROOT / "omnia_auto" / "functions" / module_name
    archive_path = f"omnia_auto/functions/{module_name}"

    with ZipFile(_DISTRIBUTED_WHEEL) as wheel_archive:
        packaged_source = wheel_archive.read(archive_path).decode("utf-8")

    assert packaged_source == source_path.read_text(encoding="utf-8")


def test_prompt_fields_hides_secret_input(monkeypatch):
    """Read fields marked as secrets without terminal echo."""
    prompts = []

    def _hidden_prompt(prompt):
        prompts.append(prompt)
        return "entered-value"

    monkeypatch.setattr(credential_func.getpass, "getpass", _hidden_prompt)
    monkeypatch.setattr(
        credential_func,
        "_read_visible_input",
        lambda *_args, **_kwargs: pytest.fail("visible input was used"),
    )

    result = credential_func.prompt_fields_interactive([
        {
            "field": "account_name",
            "label": "Account name",
            "secret": True,
        },
    ])

    assert result == {"account_name": "entered-value"}
    assert prompts == ["  Account name: "]


def test_prompt_fields_preserves_visible_nonsecret_input(monkeypatch):
    """Keep the intended visible prompt for non-secret identifiers."""
    prompts = []
    monkeypatch.setattr(
        credential_func.getpass,
        "getpass",
        lambda *_args, **_kwargs: pytest.fail("hidden prompt was used"),
    )
    monkeypatch.setattr(
        credential_func,
        "_read_visible_input",
        lambda prompt: prompts.append(prompt) or "account-name",
    )

    result = credential_func.prompt_fields_interactive([
        {
            "field": "account_name",
            "label": "Account name",
            "secret": False,
        },
    ])

    assert result == {"account_name": "account-name"}
    assert prompts == ["  Account name: "]


@pytest.mark.parametrize(
    "field_name",
    ["credential_id", "token_endpoint", "secret_name", "access_key_id"],
)
def test_prompt_fields_honors_explicit_visible_input_for_identifiers(
    monkeypatch, field_name,
):
    """Preserve explicit visible prompts regardless of identifier spelling."""
    prompts = []
    monkeypatch.setattr(
        credential_func.getpass,
        "getpass",
        lambda *_args, **_kwargs: pytest.fail("hidden prompt was used"),
    )
    monkeypatch.setattr(
        credential_func,
        "_read_visible_input",
        lambda prompt: prompts.append(prompt) or "identifier-value",
    )

    result = credential_func.prompt_fields_interactive([
        {
            "field": field_name,
            "label": "Visible identifier",
            "secret": False,
        },
    ])

    assert result == {field_name: "identifier-value"}
    assert prompts == ["  Visible identifier: "]


def test_secret_prompt_does_not_display_existing_value(monkeypatch):
    """Show only a set indicator for an existing secret value."""
    prompts = []
    monkeypatch.setattr(
        credential_func.getpass,
        "getpass",
        lambda prompt: prompts.append(prompt) or "",
    )

    result = credential_func.prompt_fields_interactive(
        [{"field": "api_token", "label": "API token"}],
        {"api_token": "existing-sensitive-value"},
    )

    assert result == {"api_token": "existing-sensitive-value"}
    assert prompts == ["  API token [set]: "]


@pytest.mark.parametrize("field_spec", [["invalid"]])
def test_prompt_fields_rejects_malformed_specification(field_spec):
    """Reject malformed JSON structures before prompting."""
    with pytest.raises(ValueError):
        credential_func.prompt_fields_interactive(field_spec)


def test_sensitive_file_permissions_are_restricted(tmp_path):
    """Restrict a pre-existing credential file before it is read."""
    credential_path = tmp_path / "credentials.yml"
    credential_path.write_text("account: value\n", encoding="utf-8")
    credential_path.chmod(0o644)

    host_func._protect_sensitive_file(str(credential_path))

    assert stat.S_IMODE(credential_path.stat().st_mode) == 0o600


def test_sensitive_file_symlink_is_rejected(tmp_path):
    """Do not follow a symbolic link supplied as a credential file."""
    target = tmp_path / "target.yml"
    target.write_text("account: value\n", encoding="utf-8")
    link = tmp_path / "credentials.yml"
    link.symlink_to(target)

    with pytest.raises(ValueError, match="symbolic link"):
        host_func._protect_sensitive_file(str(link))


@pytest.mark.parametrize(
    "protector",
    [credential_func._protect_sensitive_file, host_func._protect_sensitive_file],
)
def test_sensitive_directory_is_rejected_without_chmod(tmp_path, protector):
    """Do not chmod a directory supplied where a sensitive file is expected."""
    directory = tmp_path / "not-a-credential-file"
    directory.mkdir(mode=0o750)
    original_mode = stat.S_IMODE(directory.stat().st_mode)

    with pytest.raises(ValueError, match="regular file"):
        protector(str(directory))

    assert stat.S_IMODE(directory.stat().st_mode) == original_mode


@pytest.mark.parametrize(
    "protector",
    [credential_func._protect_sensitive_file, host_func._protect_sensitive_file],
)
def test_sensitive_fifo_is_rejected_without_blocking(tmp_path, protector):
    """Reject a FIFO opened in nonblocking mode instead of waiting for a writer."""
    fifo_path = tmp_path / "not-a-credential-file"
    os.mkfifo(fifo_path, mode=0o640)
    original_mode = stat.S_IMODE(fifo_path.stat().st_mode)

    with pytest.raises(ValueError, match="regular file"):
        protector(str(fifo_path))

    assert stat.S_IMODE(fifo_path.stat().st_mode) == original_mode


def test_sensitive_descriptor_closes_after_validation_failure(
    tmp_path, monkeypatch,
):
    """Close the descriptor when the opened object fails validation."""
    invalid_path = tmp_path / "directory"
    invalid_path.mkdir()
    opened_fds = []
    real_open = os.open

    def _tracking_open(*args, **kwargs):
        file_fd = real_open(*args, **kwargs)
        opened_fds.append(file_fd)
        return file_fd

    monkeypatch.setattr(process_security.os, "open", _tracking_open)

    with pytest.raises(ValueError, match="regular file"):
        with process_security.sensitive_file_descriptor(str(invalid_path)):
            pytest.fail("invalid descriptor was yielded")

    assert len(opened_fds) == 1
    with pytest.raises(OSError):
        os.fstat(opened_fds[0])


def test_sensitive_descriptor_closes_after_context_failure(tmp_path):
    """Close the descriptor even when its context body raises."""
    sensitive_path = tmp_path / "credentials.yml"
    sensitive_path.write_text("account: value\n", encoding="utf-8")
    yielded_fd = -1

    with pytest.raises(RuntimeError, match="body failed"):
        with process_security.sensitive_file_descriptor(
            str(sensitive_path),
        ) as file_fd:
            yielded_fd = file_fd
            raise RuntimeError("body failed")

    with pytest.raises(OSError):
        os.fstat(yielded_fd)


@pytest.mark.parametrize("fail_during_write", [False, True])
def test_exclusive_sensitive_writer_has_one_closed_descriptor(
    tmp_path, fail_during_write,
):
    """Close the exclusive writer after successful and failed writes."""
    output_path = tmp_path / "private.txt"
    writer_fd = -1

    def _write():
        nonlocal writer_fd
        with process_security.exclusive_sensitive_text(
            str(output_path),
        ) as output_stream:
            writer_fd = output_stream.fileno()
            output_stream.write("protected data")
            if fail_during_write:
                raise RuntimeError("write failed")

    if fail_during_write:
        with pytest.raises(RuntimeError, match="write failed"):
            _write()
    else:
        _write()

    with pytest.raises(OSError):
        os.fstat(writer_fd)
    assert stat.S_IMODE(output_path.stat().st_mode) == 0o600


def test_exclusive_sensitive_writer_closes_if_stream_creation_fails(
    tmp_path, monkeypatch,
):
    """Close the raw descriptor when its text wrapper cannot be created."""
    output_path = tmp_path / "private.txt"
    opened_fds = []
    real_os_open = os.open

    def _tracking_open(*args, **kwargs):
        file_fd = real_os_open(*args, **kwargs)
        opened_fds.append(file_fd)
        return file_fd

    monkeypatch.setattr(process_security.os, "open", _tracking_open)
    monkeypatch.setattr(
        "builtins.open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError("stream creation failed")
        ),
    )

    with pytest.raises(OSError, match="stream creation failed"):
        with process_security.exclusive_sensitive_text(str(output_path)):
            pytest.fail("failed stream was yielded")

    assert len(opened_fds) == 1
    with pytest.raises(OSError):
        os.fstat(opened_fds[0])


def test_inventory_directory_is_removed_after_sensitive_write_failure(
    tmp_path, monkeypatch,
):
    """Remove the private inventory directory after validation failure."""
    inventory_dir = tmp_path / "inventory"

    def _make_inventory_dir(**_kwargs):
        inventory_dir.mkdir()
        return str(inventory_dir)

    def _fail_sensitive_write(*_args, **_kwargs):
        raise ValueError("validation failed")

    monkeypatch.setattr(host_func.tempfile, "mkdtemp", _make_inventory_dir)
    monkeypatch.setattr(
        host_func,
        "exclusive_sensitive_text",
        _fail_sensitive_write,
    )

    with pytest.raises(ValueError, match="validation failed"):
        host_func._write_testinfra_inventory({"all": {"hosts": {}}})

    assert not inventory_dir.exists()


def test_atomic_credential_write_preserves_original_on_failure(tmp_path):
    """Do not publish transient plaintext when Vault encryption fails."""
    credential_path = tmp_path / "credentials.yml"
    credential_path.write_text(
        f"{credential_func.VAULT_HEADER};1.2;AES256\noriginal\n",
        encoding="utf-8",
    )
    key_path = tmp_path / "vault.key"
    key_path.write_text("vault-password", encoding="utf-8")
    original_content = credential_path.read_text(encoding="utf-8")

    def _vault_command(command, **_kwargs):
        if "decrypt" in command:
            return SimpleNamespace(stdout="account: original\n")
        raise subprocess.CalledProcessError(
            1, command, stderr="generation failed",
        )

    with patch.object(
        process_security.subprocess,
        "run",
        side_effect=_vault_command,
    ):
        result = credential_func.write_credential_fields(
            str(credential_path),
            str(key_path),
            {"account": "replacement"},
        )

    assert result["success"] is False
    assert credential_path.read_text(encoding="utf-8") == original_content
    assert not list(tmp_path.glob(".credentials.yml.*"))


def test_vault_key_is_created_and_retained_with_private_mode(tmp_path):
    """Apply mode 0600 before writing and tighten an existing key."""
    key_path = tmp_path / "vault.key"
    previous_umask = os.umask(0)
    try:
        created = credential_func.ensure_vault_key(str(key_path))
    finally:
        os.umask(previous_umask)

    assert created["created"] is True
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    original_value = key_path.read_text(encoding="utf-8")

    key_path.chmod(0o644)
    retained = credential_func.ensure_vault_key(str(key_path))

    assert retained["created"] is False
    assert key_path.read_text(encoding="utf-8") == original_value
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600


def test_vault_key_symlink_is_rejected(tmp_path):
    """Never follow a caller-supplied final-path key symlink."""
    target = tmp_path / "target.key"
    target.write_text("unchanged", encoding="utf-8")
    link = tmp_path / "vault.key"
    link.symlink_to(target)

    with pytest.raises(ValueError, match="symbolic link"):
        credential_func.ensure_vault_key(str(link))

    assert target.read_text(encoding="utf-8") == "unchanged"


def test_existing_vault_key_directory_is_not_modified(tmp_path):
    """Reject an existing directory without changing its permissions."""
    key_path = tmp_path / "vault.key"
    key_path.mkdir(mode=0o750)
    original_mode = stat.S_IMODE(key_path.stat().st_mode)

    with pytest.raises(ValueError, match="regular file"):
        credential_func.ensure_vault_key(str(key_path))

    assert stat.S_IMODE(key_path.stat().st_mode) == original_mode


def test_credentials_have_private_mode_before_yaml_write(tmp_path, monkeypatch):
    """Set mode 0600 before plaintext credential bytes are written."""
    observed = {}
    original_safe_dump = credential_func.yaml.safe_dump

    def _safe_dump(data, stream, **kwargs):
        observed["mode_during_write"] = stat.S_IMODE(
            os.fstat(stream.fileno()).st_mode,
        )
        return original_safe_dump(data, stream, **kwargs)

    monkeypatch.setattr(credential_func.yaml, "safe_dump", _safe_dump)

    def _encrypt(_plaintext_fd, _key_fd, encrypted_fd):
        os.ftruncate(encrypted_fd, 0)
        os.write(
            encrypted_fd,
            f"{credential_func.VAULT_HEADER}\nencrypted\n".encode("ascii"),
        )

    monkeypatch.setattr(credential_func, "_run_vault_encrypt", _encrypt)
    creds_path = tmp_path / "credentials.yml"
    key_path = tmp_path / "vault.key"

    result = credential_func.write_credential_fields(
        str(creds_path), str(key_path), {"account": "protected-value"},
    )

    assert result["success"] is True
    assert observed["mode_during_write"] == 0o600
    assert stat.S_IMODE(creds_path.stat().st_mode) == 0o600


def test_vault_encrypt_restores_private_mode(tmp_path, monkeypatch):
    """Atomically install validated vault output with private permissions."""
    creds_path = tmp_path / "credentials.yml"
    creds_path.write_text("account: value\n", encoding="utf-8")
    key_path = tmp_path / "vault.key"
    key_path.write_text("key-value", encoding="utf-8")

    def _run(args, **kwargs):
        output_fd = kwargs["stdout"]
        os.ftruncate(output_fd, 0)
        os.write(
            output_fd,
            f"{credential_func.VAULT_HEADER}\nencrypted\n".encode("ascii"),
        )
        creds_path.chmod(0o644)
        assert str(creds_path) not in args
        assert str(key_path) not in args
        assert args[1:5] == ["encrypt", "-", "--output", "-"]
        assert isinstance(kwargs["stdin"], int)
        assert output_fd not in kwargs["pass_fds"]
        assert kwargs["close_fds"] is True
        assert kwargs["shell"] is False
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(process_security.subprocess, "run", _run)

    result = credential_func.vault_encrypt(
        str(creds_path), str(key_path),
    )

    assert result["success"] is True
    assert creds_path.read_text(encoding="utf-8").startswith(
        credential_func.VAULT_HEADER,
    )
    assert stat.S_IMODE(creds_path.stat().st_mode) == 0o600


def test_vault_encrypt_failure_restores_private_mode(tmp_path, monkeypatch):
    """Repair credentials permissions even when ansible-vault fails."""
    creds_path = tmp_path / "credentials.yml"
    creds_path.write_text("account: value\n", encoding="utf-8")
    key_path = tmp_path / "vault.key"
    key_path.write_text("key-value", encoding="utf-8")

    def _run(*_args, **_kwargs):
        creds_path.chmod(0o644)
        raise credential_func.subprocess.CalledProcessError(
            1, ["ansible-vault"], stderr="encryption failed",
        )

    monkeypatch.setattr(process_security.subprocess, "run", _run)

    result = credential_func.vault_encrypt(
        str(creds_path), str(key_path),
    )

    assert result["success"] is False
    assert stat.S_IMODE(creds_path.stat().st_mode) == 0o600


def test_host_vault_encrypt_failure_restores_private_mode(
    tmp_path, monkeypatch,
):
    """Keep the host loader's credentials private after vault failure."""
    creds_path = tmp_path / "credentials.yml"
    creds_path.write_text("account: value\n", encoding="utf-8")
    key_path = tmp_path / "vault.key"
    key_path.write_text("key-value", encoding="utf-8")

    def _run(*_args, **_kwargs):
        creds_path.chmod(0o644)
        raise host_func.subprocess.CalledProcessError(
            1, ["ansible-vault"], stderr="encryption failed",
        )

    monkeypatch.setattr(process_security.subprocess, "run", _run)

    with pytest.raises(ValueError, match="Failed to encrypt"):
        host_func._encrypt_vault_file(str(creds_path), str(key_path))

    assert stat.S_IMODE(creds_path.stat().st_mode) == 0o600


@pytest.mark.skipif(
    shutil.which("ansible-vault") is None,
    reason="ansible-vault is required for the integration test",
)
def test_real_vault_round_trip_preserves_fields_and_private_files(
    tmp_path, monkeypatch,
):
    """Exercise real Vault encryption, merge, and decryption end to end."""
    credential_dir = tmp_path / "credentials ; remain data"
    credential_dir.mkdir(mode=0o700)
    _use_private_ansible_temp(tmp_path, monkeypatch)
    creds_path = credential_dir / "test credentials.yml"
    key_path = credential_dir / "test key"
    initial_fields = {
        "account_name": f"operator-{secrets.token_hex(4)}",
        "api_token": secrets.token_urlsafe(24),
    }
    replacement_token = secrets.token_urlsafe(24)

    first_write = credential_func.write_credential_fields(
        str(creds_path),
        str(key_path),
        initial_fields,
        header_comment="Generated test credentials",
    )
    assert first_write["success"] is True, first_write["error"]
    assert credential_func.is_vault_encrypted(str(creds_path)) is True
    assert stat.S_IMODE(creds_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600

    second_write = credential_func.write_credential_fields(
        str(creds_path),
        str(key_path),
        {"api_token": replacement_token, "endpoint": "host.example.test"},
    )
    assert second_write["success"] is True, second_write["error"]

    decrypted = credential_func.vault_decrypt_to_dict(
        str(creds_path), str(key_path),
    )
    assert decrypted["success"] is True, decrypted["error"]
    assert decrypted["data"] == {
        "account_name": initial_fields["account_name"],
        "api_token": replacement_token,
        "endpoint": "host.example.test",
    }
    assert not list(credential_dir.glob(".test credentials.yml.*.tmp"))


@pytest.mark.skipif(
    shutil.which("ansible-vault") is None,
    reason="ansible-vault is required for the integration test",
)
def test_host_loader_encrypts_plaintext_once_and_reloads_it(
    tmp_path, monkeypatch,
):
    """Retain host-loader behavior while securing its plaintext input."""
    credential_dir = tmp_path / "host credentials"
    credential_dir.mkdir(mode=0o700)
    creds_path = credential_dir / "credentials.yml"
    key_path = credential_dir / "credentials.key"
    expected = {
        "service_user": f"user-{secrets.token_hex(4)}",
        "service_password": secrets.token_urlsafe(24),
    }
    creds_path.write_text(yaml.safe_dump(expected), encoding="utf-8")
    monkeypatch.setattr(host_func, "get_module_root", lambda: str(tmp_path))
    _use_private_ansible_temp(tmp_path, monkeypatch)

    first_load = host_func.load_test_credentials(
        str(creds_path), str(key_path),
    )
    second_load = host_func.load_test_credentials(
        str(creds_path), str(key_path),
    )

    assert first_load == expected
    assert second_load == expected
    assert host_func._is_vault_encrypted(str(creds_path)) is True
    assert stat.S_IMODE(creds_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600


@pytest.mark.skipif(
    shutil.which("ansible-vault") is None,
    reason="ansible-vault is required for the integration test",
)
def test_credential_cli_round_trip_uses_local_plugin_source(tmp_path):
    """Verify the installed-facing CLI contract with real Vault operations."""
    credential_dir = tmp_path / "CLI credentials ; data"
    credential_dir.mkdir(mode=0o700)
    creds_path = credential_dir / "credentials.yml"
    key_path = credential_dir / "credentials.key"
    fields = {
        "account_name": f"account-{secrets.token_hex(4)}",
        "access_token": secrets.token_urlsafe(24),
    }
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = os.pathsep.join(
        [str(_PLUGIN_ROOT), child_env.get("PYTHONPATH", "")],
    ).rstrip(os.pathsep)
    ansible_temp = tmp_path / "ansible-local"
    ansible_temp.mkdir(mode=0o700)
    child_env["ANSIBLE_LOCAL_TEMP"] = str(ansible_temp)
    cli_prefix = [sys.executable, "-m", "omnia_auto"]

    def _run_cli(*arguments):
        return subprocess.run(
            [*cli_prefix, *arguments],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=child_env,
            shell=False,
        )

    ensure_result = _run_cli("ensure-key", "--key-path", str(key_path))
    assert ensure_result.returncode == 0, ensure_result.stderr
    assert ensure_result.stdout.strip() == "CREATED"

    write_result = _run_cli(
        "write-fields",
        "--creds-path",
        str(creds_path),
        "--key-path",
        str(key_path),
        "--fields",
        json.dumps(fields),
    )
    assert write_result.returncode == 0, write_result.stderr
    assert write_result.stdout.strip() == "OK"

    encrypted_result = _run_cli(
        "is-encrypted", "--creds-path", str(creds_path),
    )
    assert encrypted_result.returncode == 0, encrypted_result.stderr
    assert encrypted_result.stdout.strip() == "YES"

    field_result = _run_cli(
        "read-field",
        "--creds-path",
        str(creds_path),
        "--key-path",
        str(key_path),
        "--field",
        "access_token",
    )
    assert field_result.returncode == 0, field_result.stderr
    assert field_result.stdout.strip() == fields["access_token"]

    all_result = _run_cli(
        "read-all",
        "--creds-path",
        str(creds_path),
        "--key-path",
        str(key_path),
    )
    assert all_result.returncode == 0, all_result.stderr
    assert json.loads(all_result.stdout) == fields


def _sample_auth_value():
    """Return an adversarial value used only as opaque authentication data."""
    return "value with spaces 'quotes' ; $(must-not-run)"


def test_sshpass_pipe_is_private_and_closed():
    """Transport one password line through a short-lived descriptor."""
    auth_value = _sample_auth_value()
    with process_security.sshpass_pipe(auth_value) as auth_fd:
        assert auth_fd is not None
        assert auth_fd >= 3
        assert os.read(auth_fd, 8192).decode("utf-8") == f"{auth_value}\n"

    with pytest.raises(OSError):
        os.fstat(auth_fd)


@pytest.mark.parametrize("auth_value", ["line\nnext", "line\rnext", "nul\x00value"])
def test_sshpass_pipe_rejects_multiline_values(auth_value):
    """Reject values that cannot be represented as one sshpass line."""
    with pytest.raises(ValueError, match="single line"):
        with process_security.sshpass_pipe(auth_value):
            pytest.fail("invalid authentication value was accepted")


def test_sshpass_builders_never_place_authentication_in_argv():
    """Reference only an inherited descriptor in SSH, SCP, and rsync argv."""
    auth_value = _sample_auth_value()
    auth_fd = 37
    ssh_args = sync_func._build_ssh_cmd_list(
        "192.0.2.10", "root", auth_fd, "-o BatchMode=no", "true",
    )
    scp_args = sync_func._build_scp_cmd_list(
        "192.0.2.10",
        "root",
        auth_fd,
        "-o BatchMode=no",
        "/source",
        "/destination",
    )
    rsync_shell = sync_func._build_rsync_ssh_e(
        auth_fd, "-o BatchMode=no",
    )

    for command in (ssh_args, scp_args, rsync_shell):
        assert auth_value not in command
        assert "-p" not in command
    assert ssh_args[:4] == ["sshpass", "-d", "37", "ssh"]
    assert scp_args[:4] == ["sshpass", "-d", "37", "scp"]
    assert rsync_shell.startswith("sshpass -d 37 ssh ")

    assert sync_func._build_ssh_cmd_list(
        "192.0.2.10", "root", None, "-o BatchMode=yes", "true",
    )[0] == "ssh"
    assert sync_func._build_scp_cmd_list(
        "192.0.2.10",
        "root",
        None,
        "-o BatchMode=yes",
        "/source",
        "/destination",
    )[0] == "scp"


def test_remote_sync_passes_authentication_only_through_descriptors(
    tmp_path, monkeypatch,
):
    """Keep the SSH value out of every remote sync process argv and env."""
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    auth_value = _sample_auth_value()
    calls = []

    def _run(args, **kwargs):
        auth_fd, = kwargs["pass_fds"]
        calls.append((
            args,
            kwargs,
            os.read(auth_fd, 8192).decode("utf-8"),
        ))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sync_func.subprocess, "run", _run)
    monkeypatch.setenv("SSHPASS", "parent-value")

    result = sync_func.sync_files(
        "ssh",
        str(source),
        "/remote/source.txt",
        ip="192.0.2.10",
        auth_secret=auth_value,
    )

    assert result["success"] is True
    assert len(calls) == 2
    for args, kwargs, auth_payload in calls:
        assert auth_value not in repr(args)
        assert auth_payload == f"{auth_value}\n"
        assert "SSHPASS" not in kwargs["env"]
    assert os.environ["SSHPASS"] == "parent-value"


def test_remote_rsync_uses_a_fresh_password_descriptor(tmp_path, monkeypatch):
    """Forward a fresh descriptor through rsync's remote-shell command."""
    source = tmp_path / "source"
    source.mkdir()
    auth_value = _sample_auth_value()
    calls = []

    def _run(args, **kwargs):
        auth_fd, = kwargs["pass_fds"]
        calls.append((
            args,
            os.read(auth_fd, 8192).decode("utf-8"),
        ))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sync_func.subprocess, "run", _run)

    result = sync_func.sync_files(
        "ssh",
        str(source),
        "/remote/source",
        ip="192.0.2.10",
        auth_secret=auth_value,
    )

    assert result["success"] is True
    assert len(calls) == 2
    assert calls[1][0][0] == "rsync"
    assert "sshpass -d" in calls[1][0][3]
    assert all(payload == f"{auth_value}\n" for _args, payload in calls)


def test_remote_clone_passes_authentication_only_through_descriptors(
    monkeypatch,
):
    """Keep the SSH value out of every remote clone process argv and env."""
    auth_value = _sample_auth_value()
    calls = []

    def _run(args, **kwargs):
        auth_fd, = kwargs["pass_fds"]
        calls.append((
            args,
            kwargs,
            os.read(auth_fd, 8192).decode("utf-8"),
        ))
        stdout = "NO\n" if len(calls) == 1 else ""
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(sync_func.subprocess, "run", _run)

    result = sync_func.clone_repo(
        "ssh",
        "https://example.invalid/repository.git",
        "/remote/repository",
        ip="192.0.2.10",
        auth_secret=auth_value,
    )

    assert result["success"] is True
    assert calls
    for args, kwargs, auth_payload in calls:
        assert auth_value not in repr(args)
        assert auth_payload == f"{auth_value}\n"
        assert "SSHPASS" not in kwargs["env"]


def test_remote_playbook_passes_authentication_only_through_descriptor(
    monkeypatch,
):
    """Wire remote playbook authentication through a private descriptor."""
    auth_value = _sample_auth_value()
    captured = {}
    config = {
        "clone_path": "/remote/omnia",
        "oim_server_ip": "192.0.2.10",
        "oim_ssh_user": "root",
        "oim_ssh_port": 22,
    }
    monkeypatch.setattr(runner_func, "load_test_config", lambda: config)
    monkeypatch.setattr(
        runner_func,
        "load_test_credentials",
        lambda: {"oim_password": auth_value},
    )
    monkeypatch.setattr(runner_func, "is_local_execution", lambda: False)
    monkeypatch.setattr(runner_func.shutil, "which", lambda _name: "/bin/tool")

    class _Logger:
        @staticmethod
        def check(_message):
            """Ignore formatted runner progress output."""
            return None

    monkeypatch.setattr(runner_func, "TestLogger", lambda _name: _Logger())

    def _stream(*args, **kwargs):
        auth_fd, = kwargs["pass_fds"]
        captured.update(
            args=args,
            kwargs=kwargs,
            auth_payload=os.read(auth_fd, 8192).decode("utf-8"),
        )
        return {"success": True}

    monkeypatch.setattr(runner_func, "_stream_cmd", _stream)

    result = runner_func.run_playbook(
        playbook="telemetry.yml", playbook_workdir="src",
    )

    assert result["success"] is True
    assert auth_value not in repr(captured["args"])
    assert "sshpass -d" in captured["args"][0]
    assert captured["auth_payload"] == f"{auth_value}\n"


def test_remote_playbook_reports_password_pipe_failure(monkeypatch):
    """Return the normal failure result when descriptor creation fails."""
    config = {
        "clone_path": "/remote/omnia",
        "oim_server_ip": "192.0.2.10",
        "oim_ssh_user": "root",
        "oim_ssh_port": 22,
    }
    monkeypatch.setattr(runner_func, "load_test_config", lambda: config)
    monkeypatch.setattr(
        runner_func,
        "load_test_credentials",
        lambda: {"oim_password": "protected-value"},
    )
    monkeypatch.setattr(runner_func, "is_local_execution", lambda: False)
    monkeypatch.setattr(runner_func.shutil, "which", lambda _name: "/bin/tool")
    monkeypatch.setattr(
        runner_func,
        "TestLogger",
        lambda _name: SimpleNamespace(check=lambda _message: None),
    )

    def _pipe_failure(_auth_value):
        raise OSError("password pipe unavailable")

    monkeypatch.setattr(runner_func, "sshpass_pipe", _pipe_failure)

    result = runner_func.run_playbook(
        playbook="telemetry.yml", playbook_workdir="src",
    )

    assert result["success"] is False
    assert result["error"] == "password pipe unavailable"


def test_streaming_process_forwards_descriptor_and_scrubs_environment(
    monkeypatch,
):
    """Pass only the credential descriptor into the spawned bash process."""
    auth_value = _sample_auth_value()
    captured = {}

    class _Process:
        stdin = None
        stdout = []
        stderr = None
        pid = 12345

        @staticmethod
        def wait(*_args, **_kwargs):
            """Return a successful process exit status."""
            return 0

    def _popen(args, **kwargs):
        auth_fd, = kwargs["pass_fds"]
        captured.update(
            args=args,
            kwargs=kwargs,
            auth_payload=os.read(auth_fd, 8192).decode("utf-8"),
        )
        return _Process()

    class _Timer:
        def start(self):
            """Do not start a real watchdog thread."""
            return None

        def cancel(self):
            """Accept runner cleanup for the fake watchdog."""
            return None

    monkeypatch.setattr(runner_func.subprocess, "Popen", _popen)
    monkeypatch.setattr(
        runner_func.threading,
        "Timer",
        lambda *_args, **_kwargs: _Timer(),
    )
    monkeypatch.setenv("SSHPASS", "inherited-value")

    with process_security.sshpass_pipe(auth_value) as auth_fd:
        result = runner_func._stream_cmd(
            "true",
            "telemetry.yml",
            30,
            None,
            {},
            pass_fds=process_security.descriptor_tuple(auth_fd),
        )

    assert result["success"] is True
    assert captured["args"] == ["bash", "-c", "true"]
    assert captured["auth_payload"] == f"{auth_value}\n"
    assert "SSHPASS" not in captured["kwargs"]["env"]
    assert os.environ["SSHPASS"] == "inherited-value"


def test_testinfra_inventory_is_private_and_cleanable():
    """Store authentication data only in a 0700 directory and 0600 file."""
    inventory = {
        "all": {
            "hosts": {
                "target": {
                    "ansible_host": "192.0.2.10",
                    "protected_value": os.environ.get(
                        "OMNIA_TEST_PROTECTED_VALUE", "",
                    ),
                },
            },
        },
    }

    inventory_path = host_func._write_testinfra_inventory(inventory)
    inventory_dir = os.path.dirname(inventory_path)
    try:
        assert stat.S_IMODE(os.stat(inventory_dir).st_mode) == 0o700
        assert stat.S_IMODE(os.stat(inventory_path).st_mode) == 0o600
        with open(inventory_path, encoding="utf-8") as inventory_stream:
            assert yaml.safe_load(inventory_stream) == inventory
    finally:
        host_func._cleanup_testinfra_inventory_dirs()
    assert not os.path.exists(inventory_dir)


def test_config_values_use_real_suite_directories(tmp_path):
    """Accept real suite directories and reject traversal variants."""
    runner = _runner(tmp_path)

    assert runner._canonical_marker("source+sanity") == "source+sanity"
    assert runner._build_config_extra(
        {"marker": "sanity", "suite": "sources"}, "deploy"
    ) == ["--marker", "sanity", "--suite", "sources"]
    with pytest.raises(ValueError, match="suite"):
        runner._build_config_extra({"suite": "../outside"}, "deploy")


def test_stale_tag_metadata_does_not_hide_real_fvt(tmp_path, monkeypatch):
    """Use trusted directories as the scenario allowlist."""
    (tmp_path / "fvt" / "catalog").mkdir(parents=True)
    runner = validation_runner.ValidationRunner(
        "repo_manager",
        script_dir=str(tmp_path),
        domain_config={
            "tags": ["prepare", "execute"],
            "markers": ["sanity"],
            "suites": {},
        },
    )
    observed = {}

    def _run_fvt(tag, command, **options):
        observed.update(tag=tag, command=command, options=options)
        return 0

    monkeypatch.setattr(runner, "_run_fvt", _run_fvt)

    assert runner.main([runner.cat_fvt, "catalog", "verify"]) == 0
    assert observed["tag"] == "catalog"
    assert observed["command"] == "verify"


def test_stale_suite_metadata_does_not_hide_real_suite(tmp_path):
    """Use immediate suite directories instead of stale metadata."""
    (tmp_path / "fvt" / "build" / "aarch64").mkdir(parents=True)
    runner = validation_runner.ValidationRunner(
        "image_build_manager",
        script_dir=str(tmp_path),
        domain_config={
            "tags": ["build"],
            "markers": ["sanity"],
            "suites": {"build": ["s3", "registry"]},
        },
    )

    assert runner._build_config_extra(
        {"suite": "aarch64"}, "build",
    ) == ["--suite", "aarch64"]


@pytest.mark.parametrize("marker", ["regression", "nft", "future_marker"])
def test_safe_marker_is_not_blocked_by_stale_metadata(tmp_path, marker):
    """Allow future safe pytest markers without weakening the grammar."""
    runner = _runner(tmp_path)

    assert runner._build_config_extra(
        {"marker": marker}, "deploy",
    ) == ["--marker", marker]


@pytest.mark.parametrize(
    "marker", ["sanity;touch_pwned", "sanity,other+mixed", "-k"],
)
def test_marker_grammar_rejects_injection(marker):
    """Reject shell/option syntax and mixed marker operators."""
    with pytest.raises(ValueError, match="marker"):
        validation_runner._validate_marker_value(marker)


def test_batch_rejects_unknown_scenario_without_execution(
    tmp_path, monkeypatch,
):
    """Do not execute a scenario name loaded from untrusted YAML."""
    runner = _runner(tmp_path)
    runner.config_file = str(tmp_path / "test_run_config.yml")
    with open(runner.config_file, "w", encoding="utf-8") as config_stream:
        yaml.safe_dump({
            runner.cat_fvt: {
                "deploy;touch-pwned": {
                    "run": True,
                    "command": "test",
                },
            },
        }, config_stream)
    monkeypatch.setattr(
        runner,
        "_run_config_command",
        lambda *_args, **_kwargs: pytest.fail("untrusted scenario executed"),
    )

    assert runner._cmd_config() == 1


def test_batch_skips_disabled_stale_scenario(tmp_path, monkeypatch):
    """Keep a disabled, removed scenario as a harmless skipped entry."""
    runner = _runner(tmp_path)
    runner.config_file = str(tmp_path / "test_run_config.yml")
    with open(runner.config_file, "w", encoding="utf-8") as config_stream:
        yaml.safe_dump({
            runner.cat_fvt: {
                "removed_scenario": {"run": False},
            },
        }, config_stream)
    monkeypatch.setattr(
        runner,
        "_run_config_command",
        lambda *_args, **_kwargs: pytest.fail("disabled scenario executed"),
    )

    assert runner._cmd_config() == 0


def test_internal_batch_execution_restores_environment(tmp_path, monkeypatch):
    """Keep scenario overrides local to a single internal batch entry."""
    runner = _runner(tmp_path)
    observed = {}

    def _main(args):
        observed["args"] = args
        observed["override"] = os.environ.get("OMNIA_DATASET_OVERRIDE")
        os.environ["OMNIA_LEAK_TEST"] = "changed"
        return 0

    monkeypatch.setattr(runner, "main", _main)
    monkeypatch.delenv("OMNIA_DATASET_OVERRIDE", raising=False)
    monkeypatch.delenv("OMNIA_LEAK_TEST", raising=False)

    result = runner._run_config_command(
        [runner.cat_fvt, "deploy", "verify"],
        {"OMNIA_DATASET_OVERRIDE": "dataset_01"},
    )

    assert result == 0
    assert observed == {
        "args": [runner.cat_fvt, "deploy", "verify"],
        "override": "dataset_01",
    }
    assert "OMNIA_DATASET_OVERRIDE" not in os.environ
    assert "OMNIA_LEAK_TEST" not in os.environ


def test_pytest_invocation_uses_argv_without_a_shell(tmp_path, monkeypatch):
    """Keep paths and expressions as data instead of a bash command string."""
    runner = _runner(tmp_path)
    captured = {}

    def _run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(validation_runner.subprocess, "run", _run)
    monkeypatch.delenv("OMNIA_LOG_FILE", raising=False)
    spaced_path = tmp_path / "suite with spaces"

    assert runner._invoke_pytest(
        [str(spaced_path)], "-m 'not deploy'", "-v"
    ) == 0
    assert str(spaced_path) in captured["args"]
    assert captured["args"][:3] == [
        validation_runner.sys.executable, "-m", "pytest",
    ]
    assert captured["kwargs"]["shell"] is False
    assert "bash" not in captured["args"]


def test_pytest_log_path_is_not_interpreted_by_a_shell(tmp_path, monkeypatch):
    """Treat a metacharacter-containing log filename only as a file path."""
    runner = _runner(tmp_path)
    captured = {}

    class _Process:
        stdout = iter(["test output\n"])

        def __enter__(self):
            """Return the fake process context."""
            return self

        def __exit__(self, *_args):
            """Leave the fake process context."""
            return False

        @staticmethod
        def wait():
            """Return a successful process status."""
            return 0

    def _popen(args, **kwargs):
        """Capture a shell-free Popen call."""
        captured.update(args=args, kwargs=kwargs)
        return _Process()

    monkeypatch.setattr(validation_runner.subprocess, "Popen", _popen)
    log_path = tmp_path / "results;still-a-filename.log"
    monkeypatch.setenv("OMNIA_LOG_FILE", str(log_path))

    assert runner._invoke_pytest(str(tmp_path / "ut")) == 0
    assert captured["kwargs"]["shell"] is False
    assert "bash" not in captured["args"]
    assert log_path.read_text(encoding="utf-8") == "test output\n"
