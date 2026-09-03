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

"""Unit tests for telemetry input-validation security boundaries."""
# The import path is extended before importing Ansible module_utils, and the
# tests intentionally exercise private validation helpers.
# pylint: disable=protected-access,wrong-import-position

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import ansible.module_utils
import jsonschema
import pytest
import yaml

import conftest as telemetry_conftest


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TELEMETRY_MODULE_UTILS = (
    _REPO_ROOT / "src" / "telemetry" / "plugins" / "module_utils"
)
_TELEMETRY_PACKAGE_SCHEMA = (
    _TELEMETRY_MODULE_UTILS
    / "input_validation"
    / "schema"
    / "telemetry_packages.json"
)
if str(_TELEMETRY_MODULE_UTILS) not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.append(str(_TELEMETRY_MODULE_UTILS))

from ansible.module_utils.input_validation.validators import (  # noqa: E402
    telemetry_validation,
)


@pytest.mark.parametrize(
    "raw_value,expected",
    [
        ("192.168.001.010", "192.168.1.10"),
        ("192.168.1", ""),
        ("192.168.1.1.2", ""),
        ("256.1.1.1", ""),
        ("-oProxyCommand=bad", ""),
        ("127.0.0.1;bad", ""),
        ("１２７.0.0.1", ""),
        (None, ""),
    ],
)
def test_ipv4_values_are_canonicalized(raw_value, expected):
    """Reconstruct valid IPv4 values and reject option-like input."""
    assert telemetry_validation._canonical_ipv4(raw_value) == expected


def test_ipv4_rejects_unbounded_numeric_component():
    """Reject oversized digit strings before integer conversion."""
    oversized_value = f"{'9' * 5000}.0.0.1"

    assert telemetry_validation._canonical_ipv4(oversized_value) == ""


@pytest.mark.parametrize(
    "mount_path,expected",
    [
        ("/opt/omnia/k8s mount", "/opt/omnia/k8s mount"),
        ("/opt/omnia/value;still-data", "/opt/omnia/value;still-data"),
        ("relative/path", ""),
        ("/opt/omnia/value\nother", ""),
        ("/opt/omnia/value\rother", ""),
        ("/opt/omnia/value\x00other", ""),
    ],
)
def test_mount_path_validation(mount_path, expected):
    """Allow absolute path characters but reject control-line injection."""
    assert telemetry_validation._validated_mount_path(mount_path) == expected


@pytest.mark.parametrize(
    "mount_path,is_valid",
    [
        ("/opt/omnia/k8s_mount", True),
        ("relative/path", False),
        ("/opt/omnia/value\n", False),
        ("/opt/omnia/value\r", False),
        ("/opt/omnia/value\x00", False),
    ],
)
def test_mount_path_schema_rejects_control_characters(mount_path, is_valid):
    """Keep the JSON schema aligned with the Python security boundary."""
    with open(_TELEMETRY_PACKAGE_SCHEMA, encoding="utf-8") as schema_stream:
        schema = yaml.safe_load(schema_stream)
    candidate = {
        "k8s_cluster_mount": mount_path,
        "slurm_cluster_mount": "/share_omnia",
    }

    errors = list(jsonschema.Draft7Validator(schema).iter_errors(candidate))

    assert (not errors) is is_valid


@pytest.mark.parametrize(
    "inventory_data",
    [
        None,
        [],
        {"all": []},
        {"all": {"children": []}},
        {"all": {"children": {"kube_vip_group": []}}},
        {
            "all": {
                "children": {
                    "kube_vip_group": {"hosts": ["192.0.2.10"]},
                },
            },
        },
    ],
)
def test_inventory_kube_vip_rejects_wrong_shapes(inventory_data):
    """Treat valid YAML of the wrong shape as missing inventory data."""
    kube_vip, children = telemetry_validation._inventory_kube_vip(
        inventory_data,
    )

    assert kube_vip == ""
    assert isinstance(children, dict)


def test_ssh_reachability_uses_canonical_argv(monkeypatch):
    """Use a fixed command, option terminator, timeout, and no shell."""
    captured = {}

    def _run(args, **kwargs):
        captured.update(args=args, kwargs=kwargs)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(telemetry_validation.subprocess, "run", _run)

    result = telemetry_validation._check_ssh_reachability("192.0.2.10")

    assert result.returncode == 0
    assert captured["args"][-3:] == ["--", "192.0.2.10", "true"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["check"] is False
    assert captured["kwargs"]["timeout"] == 15


def test_remote_mount_path_is_transported_only_as_stdin(monkeypatch):
    """Never place a user-controlled mount path in the SSH command."""
    captured = {}
    mount_path = "/opt/omnia/path; command-is-data 'with spaces'"

    def _run(args, **kwargs):
        captured.update(args=args, kwargs=kwargs)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(telemetry_validation.subprocess, "run", _run)

    result = telemetry_validation._check_remote_directory(
        "192.0.2.10", mount_path,
    )

    assert result.returncode == 0
    assert mount_path not in captured["args"]
    assert captured["args"][-3:-1] == ["--", "192.0.2.10"]
    assert captured["args"][-1] == telemetry_validation._REMOTE_DIRECTORY_CHECK
    assert captured["kwargs"]["input"] == f"{mount_path}\n"
    assert captured["kwargs"]["shell"] is False


def test_packages_rejects_inventory_command_injection(
    tmp_path, monkeypatch,
):
    """Reject an option-like inventory host before any SSH invocation."""
    inventory_path = tmp_path / "inventory.yml"
    inventory_path.write_text(
        yaml.safe_dump({
            "all": {
                "children": {
                    "kube_vip_group": {
                        "hosts": {"-oProxyCommand=bad": {}},
                    },
                },
            },
        }),
        encoding="utf-8",
    )
    config_path = tmp_path / "telemetry_config.yml"
    config_path.write_text(
        yaml.safe_dump({"cluster_inventory": str(inventory_path)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        telemetry_validation,
        "_check_ssh_reachability",
        lambda *_args: pytest.fail("invalid host reached SSH"),
    )

    errors = telemetry_validation.validate_telemetry_packages(
        str(tmp_path / "telemetry_packages.yml"),
        {
            "k8s_cluster_mount": "/opt/omnia/k8s_mount",
            "slurm_cluster_mount": "/share_omnia",
        },
        Mock(),
        Mock(),
        str(tmp_path),
        str(_TELEMETRY_MODULE_UTILS),
        "project_default",
    )

    assert any(error["error_key"] == "kube_vip" for error in errors)


def test_config_rejects_inventory_command_injection(tmp_path, monkeypatch):
    """Reject an unsafe inventory host at the primary config-validation path."""
    inventory_path = tmp_path / "inventory.yml"
    inventory_path.write_text(
        yaml.safe_dump({
            "all": {
                "children": {
                    "kube_vip_group": {
                        "hosts": {"-oProxyCommand=bad": {}},
                    },
                },
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        telemetry_validation,
        "_check_ssh_reachability",
        lambda *_args: pytest.fail("invalid host reached SSH"),
    )
    disabled_source = {
        "metrics_enabled": False,
        "logs_enabled": False,
        "collection_targets": [],
    }
    data = {
        "cluster_inventory": str(inventory_path),
        "telemetry_sources": {
            source_name: disabled_source.copy()
            for source_name in (
                "idrac", "ldms", "powerscale", "ufm", "vast", "ome",
            )
        },
        "telemetry_bridges": {
            "vector_ldms": {"metrics_enabled": False},
            "vector_ome": {
                "metrics_enabled": False,
                "logs_enabled": False,
            },
        },
        "telemetry_sinks": {
            "kafka": {"topic_partitions": {}},
            "victoria_metrics": {},
            "victoria_logs": {},
        },
        "ldms_configurations": {
            "sampler_plugins": [{"plugin_name": "meminfo"}],
        },
    }

    errors = telemetry_validation.validate_telemetry_config(
        str(tmp_path / "telemetry_config.yml"),
        data,
        Mock(),
        Mock(),
        str(tmp_path),
        str(_TELEMETRY_MODULE_UTILS),
        "project_default",
    )

    assert any(error["error_key"] == "kube_vip" for error in errors)


def test_packages_passes_safe_host_and_path_to_narrow_helpers(
    tmp_path, monkeypatch,
):
    """Canonicalize the host while preserving a metacharacter path as data."""
    inventory_path = tmp_path / "inventory.yml"
    inventory_path.write_text(
        yaml.safe_dump({
            "all": {
                "children": {
                    "kube_vip_group": {
                        "hosts": {
                            "vip": {"ansible_host": "192.168.001.010"},
                        },
                    },
                },
            },
        }),
        encoding="utf-8",
    )
    (tmp_path / "telemetry_config.yml").write_text(
        yaml.safe_dump({"cluster_inventory": str(inventory_path)}),
        encoding="utf-8",
    )
    observed = {}
    monkeypatch.setattr(
        telemetry_validation,
        "_check_ssh_reachability",
        lambda host: observed.setdefault(
            "reachability_host",
            SimpleNamespace(returncode=0, host=host),
        ),
    )

    def _directory(host, path):
        observed.update(directory_host=host, path=path)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(
        telemetry_validation, "_check_remote_directory", _directory,
    )
    mount_path = "/opt/omnia/value;still-data"

    errors = telemetry_validation.validate_telemetry_packages(
        str(tmp_path / "telemetry_packages.yml"),
        {
            "k8s_cluster_mount": mount_path,
            "slurm_cluster_mount": "/share_omnia",
        },
        Mock(),
        Mock(),
        str(tmp_path),
        str(_TELEMETRY_MODULE_UTILS),
        "project_default",
    )

    assert errors == []
    assert observed["reachability_host"].host == "192.168.1.10"
    assert observed["directory_host"] == "192.168.1.10"
    assert observed["path"] == mount_path


def test_packages_preserves_direct_kube_vip_fallback(
    tmp_path, monkeypatch,
):
    """Use a safely canonicalized direct kube_vip when inventory is absent."""
    (tmp_path / "telemetry_config.yml").write_text(
        yaml.safe_dump({"kube_vip": "192.168.001.010"}),
        encoding="utf-8",
    )
    observed = {}
    monkeypatch.setattr(
        telemetry_validation,
        "_check_ssh_reachability",
        lambda host: observed.setdefault(
            "reachability_host",
            SimpleNamespace(returncode=0, host=host),
        ),
    )

    def _directory(host, path):
        observed.update(directory_host=host, path=path)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(
        telemetry_validation, "_check_remote_directory", _directory,
    )

    errors = telemetry_validation.validate_telemetry_packages(
        str(tmp_path / "telemetry_packages.yml"),
        {
            "k8s_cluster_mount": "/opt/omnia/k8s_mount",
            "slurm_cluster_mount": "/share_omnia",
        },
        Mock(),
        Mock(),
        str(tmp_path),
        str(_TELEMETRY_MODULE_UTILS),
        "project_default",
    )

    assert errors == []
    assert observed["reachability_host"].host == "192.168.1.10"
    assert observed["directory_host"] == "192.168.1.10"
    assert observed["path"] == "/opt/omnia/k8s_mount"


def test_packages_rejects_direct_kube_vip_command_injection(
    tmp_path, monkeypatch,
):
    """Reject an option-like direct kube_vip before invoking SSH."""
    (tmp_path / "telemetry_config.yml").write_text(
        yaml.safe_dump({"kube_vip": "-oProxyCommand=bad"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        telemetry_validation,
        "_check_ssh_reachability",
        lambda *_args: pytest.fail("invalid host reached SSH"),
    )
    monkeypatch.setattr(
        telemetry_validation,
        "_check_remote_directory",
        lambda *_args: pytest.fail("invalid host reached directory check"),
    )

    errors = telemetry_validation.validate_telemetry_packages(
        str(tmp_path / "telemetry_packages.yml"),
        {
            "k8s_cluster_mount": "/opt/omnia/k8s_mount",
            "slurm_cluster_mount": "/share_omnia",
        },
        Mock(),
        Mock(),
        str(tmp_path),
        str(_TELEMETRY_MODULE_UTILS),
        "project_default",
    )

    assert any(error["error_key"] == "kube_vip" for error in errors)


def test_stdin_redirection_closes_source_handle(monkeypatch):
    """Close the /dev/null source after dup2 duplicates its descriptor."""
    open_fd = Mock(return_value=91)
    close_fd = Mock()
    monkeypatch.setattr(os, "open", open_fd)
    dup2 = Mock()
    monkeypatch.setattr(os, "dup2", dup2)
    monkeypatch.setattr(os, "close", close_fd)

    telemetry_conftest._redirect_stdin_to_devnull()

    open_fd.assert_called_once_with(os.devnull, os.O_RDONLY)
    dup2.assert_called_once_with(91, 0)
    close_fd.assert_called_once_with(91)


def test_stdin_redirection_reopens_closed_descriptor_zero():
    """Keep descriptor zero valid when it was closed before redirection."""
    command = [
        sys.executable,
        "-c",
        (
            "import os; import conftest; "
            "conftest._redirect_stdin_to_devnull(); os.fstat(0)"
        ),
    ]
    result = subprocess.run(
        command,
        cwd=str(_REPO_ROOT / "test" / "telemetry"),
        capture_output=True,
        text=True,
        check=False,
        preexec_fn=lambda: os.close(0),
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
