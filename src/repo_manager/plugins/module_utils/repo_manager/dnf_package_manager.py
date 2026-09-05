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

"""Build DNF commands for the active Repo Manager execution context."""

# The command builders intentionally accept explicit context fields. Keeping
# these values visible at each call site prevents cross-version cache reuse.
# pylint: disable=too-many-arguments,too-many-positional-arguments

from ansible.module_utils.repo_manager.package_manager_cache import (
    prepare_dnf_cache_options,
)


DNF_COMMANDS = {
    "x86_64": [
        "dnf", "download", "--refresh", "--resolve", "--alldeps",
        "--arch=x86_64", "--arch=noarch", "--disablerepo=*",
        "--enablerepo=x86_64_*",
    ],
    "aarch64": [
        "dnf", "download", "--refresh", "--forcearch", "aarch64",
        "--resolve", "--alldeps", "--exclude=*.x86_64",
        "--disablerepo=*", "--enablerepo=aarch64_*",
    ],
}

DNF_INFO_COMMANDS = {
    "x86_64": ["dnf", "info", "--refresh", "--quiet"],
    "aarch64": [
        "dnf", "info", "--refresh", "--quiet", "--forcearch=aarch64",
    ],
}


def validate_dnf_architecture(architecture):
    """Return a supported DNF architecture without an implicit fallback."""
    arch_key = str(architecture or "").lower()
    if arch_key not in DNF_COMMANDS or arch_key not in DNF_INFO_COMMANDS:
        raise ValueError(f"Unsupported RPM architecture: {architecture}")
    return arch_key


def build_dnf_download_command(repo_store_path, os_type, os_version,
                               architecture, destination, packages,
                               preferred_repo_option=None):
    """Return a context-isolated DNF download command."""
    arch_key = validate_dnf_architecture(architecture)
    command = [
        argument for argument in DNF_COMMANDS[arch_key]
        if not argument.startswith("--enablerepo=")
    ]
    command.append(
        f"--enablerepo={arch_key}_{os_type}_{os_version}_*"
    )
    command.extend(prepare_dnf_cache_options(
        repo_store_path, os_type, os_version, arch_key
    ))
    if preferred_repo_option:
        command.append(preferred_repo_option)
    command.append(f"--destdir={destination}")
    command.extend(packages)
    return command


def build_dnf_info_command(repo_store_path, os_type, os_version,
                           architecture, repository_name, package_name):
    """Return a context-isolated DNF package-information command."""
    arch_key = validate_dnf_architecture(architecture)
    command = list(DNF_INFO_COMMANDS[arch_key])
    command.extend(prepare_dnf_cache_options(
        repo_store_path, os_type, os_version, arch_key
    ))
    command.extend([f"--repo={repository_name}", package_name])
    return command
