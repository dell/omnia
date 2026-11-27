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
# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-CONFIG-001.5, CG-DESER-001.1
# ****
"""Unit tests for the oci_boot_ready_check module (TC-UT-010 companion, FR-1.5).

regctl and the AnsibleModule runtime are replaced by in-process fakes. Layer
archives are built in memory, so no registry, extraction or Ansible run is
required.
"""

# Pytest injects fixtures by reusing fixture function names as test arguments,
# and descriptive test names make per-test docstrings redundant.
# pylint: disable=missing-function-docstring,redefined-outer-name,too-few-public-methods
# pylint: disable=protected-access,unused-argument,duplicate-code
# protected-access: the tests drive the module helpers directly with fakes.
# unused-argument: fakes mirror the AnsibleModule and Popen signatures.
# duplicate-code: the loader mirrors test_oci_boot_ready.py by design.

import importlib.util
import io
import json
import subprocess
import tarfile
from pathlib import Path

import ansible.module_utils
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_UTILS_DIR = REPO_ROOT / "src/image_build_manager/plugins/module_utils"
MODULE_PATH = REPO_ROOT / "src/image_build_manager/plugins/modules/oci_boot_ready_check.py"
if str(MODULE_UTILS_DIR) not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.append(str(MODULE_UTILS_DIR))


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


CHECK = _load_module("oci_boot_ready_check_under_test", MODULE_PATH)
MANIFEST_SOURCE = "sha256:low"
MANIFEST_HIGH = "sha256:high"


class ModuleFailure(Exception):
    """Raised by the fake module where AnsibleModule would call fail_json."""


class FakeModule:
    """Minimal stand-in for AnsibleModule that records exit_json and raises on fail_json."""

    def __init__(self, **params):
        self.params = {
            "image_repo": "registry:5000/rhel-slurm",
            "image_ref": "registry:5000/rhel-slurm:10.0",
            "regctl_bin": "/usr/local/bin/regctl",
            "timeout_seconds": 300,
            **params,
        }
        self.result = None

    def fail_json(self, **kwargs):
        raise ModuleFailure(kwargs["msg"])

    def exit_json(self, **kwargs):
        self.result = kwargs


class FakeProcess:
    """Stand-in for the regctl blob reader Popen object."""

    def __init__(self, payload, returncode=0):
        self.stdout = io.BytesIO(payload)
        self.returncode = returncode
        self.killed = False

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.killed = True


class FakeClock:
    """Return 0 for the first reading and 1000 afterwards, so any deadline has passed."""

    def __init__(self):
        self.calls = 0

    def monotonic(self):
        self.calls += 1
        return 0 if self.calls == 1 else 1000


def _layer_tar(names):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name in names:
            archive.addfile(tarfile.TarInfo(name), io.BytesIO(b""))
    return buffer.getvalue()


def _manifest(*digests):
    return json.dumps({"layers": [{"digest": digest} for digest in digests]})


def _fake_run(stdout="", returncode=0, raises=None):
    def run(args, **_kwargs):
        if raises:
            raise raises
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")

    return run


def _fake_popen(payloads, returncode=0, processes=None):
    def popen(args, **_kwargs):
        process = FakeProcess(payloads[args[-1]], returncode)
        if processes is not None:
            processes.append(process)
        return process

    return popen


def test_layer_entries_are_listed_in_manifest_order(monkeypatch):
    payloads = {
        MANIFEST_SOURCE: _layer_tar(["boot/vmlinuz-6.12.0"]),
        MANIFEST_HIGH: _layer_tar(["boot/initramfs-6.12.0.img"]),
    }
    manifest = _manifest(MANIFEST_SOURCE, MANIFEST_HIGH)
    monkeypatch.setattr(CHECK.subprocess, "run", _fake_run(stdout=manifest))
    monkeypatch.setattr(CHECK.subprocess, "Popen", _fake_popen(payloads))

    layers = CHECK._layer_entries(FakeModule(), 300)

    assert layers == [["boot/vmlinuz-6.12.0"], ["boot/initramfs-6.12.0.img"]]


def test_manifest_without_layers_fails(monkeypatch):
    monkeypatch.setattr(CHECK.subprocess, "run", _fake_run(stdout='{"layers": []}'))

    with pytest.raises(ModuleFailure) as failure:
        CHECK._layer_entries(FakeModule(), 300)

    assert str(failure.value) == CHECK.NO_LAYERS_MSG


def test_regctl_manifest_failure_reports_return_code(monkeypatch):
    monkeypatch.setattr(CHECK.subprocess, "run", _fake_run(returncode=1))

    with pytest.raises(ModuleFailure) as failure:
        CHECK._layer_entries(FakeModule(), 300)

    assert str(failure.value) == CHECK.REGCTL_FAILED_MSG.format(rc=1)


def test_manifest_timeout_is_reported(monkeypatch):
    timeout_error = subprocess.TimeoutExpired(cmd="regctl", timeout=300)
    monkeypatch.setattr(CHECK.subprocess, "run", _fake_run(raises=timeout_error))

    with pytest.raises(ModuleFailure) as failure:
        CHECK._layer_entries(FakeModule(), 300)

    assert str(failure.value) == CHECK.TIMEOUT_MSG.format(timeout=300)


def test_layer_read_failure_reports_return_code(monkeypatch):
    monkeypatch.setattr(CHECK.subprocess, "run", _fake_run(stdout=_manifest(MANIFEST_SOURCE)))
    monkeypatch.setattr(
        CHECK.subprocess,
        "Popen",
        _fake_popen({MANIFEST_SOURCE: _layer_tar(["boot/vmlinuz-6.12.0"])}, returncode=2),
    )

    with pytest.raises(ModuleFailure) as failure:
        CHECK._layer_entries(FakeModule(), 300)

    assert str(failure.value) == CHECK.REGCTL_FAILED_MSG.format(rc=2)


def test_layer_timeout_kills_the_blob_reader(monkeypatch):
    processes = []
    monkeypatch.setattr(CHECK.subprocess, "run", _fake_run(stdout=_manifest(MANIFEST_SOURCE)))
    monkeypatch.setattr(
        CHECK.subprocess,
        "Popen",
        _fake_popen({MANIFEST_SOURCE: _layer_tar(["boot/vmlinuz-6.12.0"])}, processes=processes),
    )
    monkeypatch.setattr(CHECK, "time", FakeClock())

    with pytest.raises(ModuleFailure) as failure:
        CHECK._layer_entries(FakeModule(), 300)

    assert str(failure.value) == CHECK.TIMEOUT_MSG.format(timeout=300)
    assert processes[0].killed is True


def test_main_reports_complete_boot_set(monkeypatch):
    created = []

    class _Module(FakeModule):
        def __init__(self, argument_spec, supports_check_mode):
            super().__init__()
            self.argument_spec = argument_spec
            self.supports_check_mode = supports_check_mode
            created.append(self)

    payloads = {MANIFEST_SOURCE: _layer_tar([
        "boot/vmlinuz-6.12.0",
        "boot/initramfs-6.12.0.img",
        "lib/modules/6.12.0/kernel/fs/ext4.ko.xz",
    ])}
    monkeypatch.setattr(CHECK, "AnsibleModule", _Module)
    monkeypatch.setattr(CHECK.subprocess, "run", _fake_run(stdout=_manifest(MANIFEST_SOURCE)))
    monkeypatch.setattr(CHECK.subprocess, "Popen", _fake_popen(payloads))

    CHECK.main()

    assert created[0].supports_check_mode is True
    assert created[0].result == {
        "changed": False,
        "complete_versions": ["6.12.0"],
        "layer_count": 1,
    }


def test_main_names_the_missing_path(monkeypatch):
    class _Module(FakeModule):
        def __init__(self, argument_spec, supports_check_mode):
            super().__init__()

    payloads = {MANIFEST_SOURCE: _layer_tar([
        "boot/vmlinuz-6.12.0",
        "lib/modules/6.12.0/kernel/fs/ext4.ko.xz",
    ])}
    monkeypatch.setattr(CHECK, "AnsibleModule", _Module)
    monkeypatch.setattr(CHECK.subprocess, "run", _fake_run(stdout=_manifest(MANIFEST_SOURCE)))
    monkeypatch.setattr(CHECK.subprocess, "Popen", _fake_popen(payloads))

    with pytest.raises(ModuleFailure) as failure:
        CHECK.main()

    assert str(failure.value) == CHECK.MISSING_PATH_MSG.format(path="boot/initramfs-6.12.0.img")
