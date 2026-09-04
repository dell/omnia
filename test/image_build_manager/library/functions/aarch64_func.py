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

"""AArch64 build-node verification functions."""

import os
import shlex
from typing import Any, Dict

from omnia_auto import read_remote_env, run_on_host, run_ssh_command

from ._config_helpers import _load_remote_ibm_config
from ..vars.aarch64_vars import (
    AARCH64_CMDS,
    AARCH64_EXPECTED_ARCHITECTURE,
    AARCH64_SSH_USER,
    AARCH64_WORK_SUBDIRS,
)
from ..vars.common_vars import (
    CMDS,
    ENV_OMNIA_DATA_PATH,
)


def _aarch64_host_result(host) -> Dict[str, Any]:
    """Return the configured AArch64 host or an optional-feature skip."""
    config = _load_remote_ibm_config(host)
    arm_host = config.get("aarch64_inventory_host_ip", "")
    if isinstance(arm_host, str) and arm_host.strip():
        return {
            "success": True,
            "skipped": False,
            "host": arm_host.strip(),
            "error": None,
        }
    return {
        "success": True,
        "skipped": True,
        "host": "",
        "details": "aarch64_inventory_host_ip is not configured",
        "error": None,
    }


def _run_aarch64(host, arm_host, command_name, **command_values):
    """Run one centrally defined probe on the configured AArch64 node."""
    remote_command = AARCH64_CMDS[command_name]
    if command_values:
        remote_command = remote_command.format(**command_values)
    return run_ssh_command(
        host,
        target=arm_host,
        user=AARCH64_SSH_USER,
        command=remote_command,
    )


def check_aarch64_ssh_connectivity(host) -> Dict[str, Any]:
    """Verify passwordless SSH and report its source and destination."""
    target = _aarch64_host_result(host)
    if target["skipped"]:
        return target

    arm_host = target["host"]
    source_result = run_on_host(host, CMDS["hostname_fqdn"])
    source_host = (
        source_result.stdout.strip()
        if source_result.rc == 0 and source_result.stdout.strip()
        else "execution OIM"
    )
    result = _run_aarch64(host, arm_host, "aarch64_ssh_test")
    success = result.rc == 0 and result.stdout.strip() == "OK"
    return {
        "success": success,
        "skipped": False,
        "host": arm_host,
        "source": source_host,
        "destination": f"{AARCH64_SSH_USER}@{arm_host}",
        "authentication": "Passwordless SSH (BatchMode)",
        "details": "SSH connection completed" if success else "",
        "error": None if success else (
            f"SSH failed with rc={result.rc}: {result.stderr.strip()}"
        ),
    }


def check_aarch64_architecture(host) -> Dict[str, Any]:
    """Verify AArch64 architecture and collect kernel name and release."""
    target = _aarch64_host_result(host)
    if target["skipped"]:
        return target

    arm_host = target["host"]
    result = _run_aarch64(host, arm_host, "aarch64_uname")
    values = result.stdout.strip().splitlines()
    architecture = values[0].strip() if values else "unknown"
    kernel_name = values[1].strip() if len(values) > 1 else "unknown"
    kernel_release = values[2].strip() if len(values) > 2 else "unknown"
    success = (
        result.rc == 0
        and architecture == AARCH64_EXPECTED_ARCHITECTURE
    )
    return {
        "success": success,
        "skipped": False,
        "host": arm_host,
        "architecture": architecture,
        "kernel": f"{kernel_name} {kernel_release}",
        "details": "AArch64 architecture verified" if success else "",
        "error": None if success else (
            "Node reports "
            f"'{architecture}', expected '{AARCH64_EXPECTED_ARCHITECTURE}'"
        ),
    }


def check_aarch64_work_dirs(host) -> Dict[str, Any]:
    """Verify and return every required AArch64 work directory."""
    target = _aarch64_host_result(host)
    if target["skipped"]:
        return target

    arm_host = target["host"]
    try:
        data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
    except ValueError as exc:
        return {
            "success": False,
            "skipped": False,
            "host": arm_host,
            "directories": [],
            "missing": [],
            "details": "",
            "error": str(exc),
        }

    work_root = os.path.join(data_path, "image_build_manager")
    directories = [
        work_root if not subdir else os.path.join(work_root, subdir)
        for subdir in AARCH64_WORK_SUBDIRS
    ]
    missing = []
    for directory in directories:
        result = _run_aarch64(
            host,
            arm_host,
            "aarch64_test_dir",
            path=shlex.quote(directory),
        )
        if result.rc != 0 or result.stdout.strip() != "exists":
            missing.append(directory)

    return {
        "success": not missing,
        "skipped": False,
        "host": arm_host,
        "directories": directories,
        "missing": missing,
        "details": (
            f"{len(directories) - len(missing)}/"
            f"{len(directories)} present"
        ),
        "error": None if not missing else (
            "Missing directories: " + ", ".join(missing)
        ),
    }


def check_aarch64_builder_image(host) -> Dict[str, Any]:
    """Verify Podman and an AArch64 builder image on the build node."""
    target = _aarch64_host_result(host)
    if target["skipped"]:
        return target

    arm_host = target["host"]
    podman = _run_aarch64(host, arm_host, "aarch64_podman_version")
    images = _run_aarch64(host, arm_host, "aarch64_builder_images")
    podman_version = podman.stdout.strip()
    image_names = [
        line.strip() for line in images.stdout.splitlines() if line.strip()
    ]
    success = podman.rc == 0 and bool(podman_version) and bool(image_names)
    errors = []
    if podman.rc != 0 or not podman_version:
        errors.append("Podman is not installed or not functional")
    if images.rc != 0 or not image_names:
        errors.append("No AArch64 builder image was found")
    return {
        "success": success,
        "skipped": False,
        "host": arm_host,
        "podman_version": podman_version or "unavailable",
        "images": image_names,
        "details": "Podman and builder image verified" if success else "",
        "error": None if success else "; ".join(errors),
    }


def check_aarch64_regctl_installed(host) -> Dict[str, Any]:
    """Verify regctl and return its version and source revision."""
    target = _aarch64_host_result(host)
    if target["skipped"]:
        return target

    arm_host = target["host"]
    result = _run_aarch64(host, arm_host, "aarch64_regctl_version")
    version_fields = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition(":")
        if separator and value.strip():
            version_fields[key.strip()] = value.strip()
    version = version_fields.get("VCSTag", "unknown")
    revision = version_fields.get("VCSRef", "unknown")
    success = result.rc == 0 and bool(result.stdout.strip())
    return {
        "success": success,
        "skipped": False,
        "host": arm_host,
        "version": version,
        "revision": revision,
        "details": "regctl is installed and functional" if success else "",
        "error": None if success else (
            f"regctl version failed with rc={result.rc}: "
            f"{result.stderr.strip()}"
        ),
    }
