#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Parse repo_status.yml repositories and build architecture-specific repo lists."""

from urllib.parse import urlparse

import yaml

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: parse_repo_status
short_description: Parse repo_status.yml and build per-architecture repo lists
version_added: "3.0.0"
description:
  - Reads the C(repo_status.yml) file produced by repo_manager.
  - Extracts C(cluster_os_type) and derives C(cluster_os_version) from
    the first key in C(repositories).
  - Builds per-architecture repo lists from
    C(repositories.{version}.{arch}.{repo_name}.url).
  - Extracts C(repo_port) from the first non-empty repo URL.
options:
  repo_status_file:
    description: Absolute path to repo_status.yml.
    required: true
    type: str
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Parse repo_status.yml
  omnia.image_build.parse_repo_status:
    repo_status_file: /opt/omnia/repo_manager/output/project_default/repo_status.yml
  register: repo_result

- name: Display parsed results
  ansible.builtin.debug:
    msg: >-
      OS={{ repo_result.cluster_os_type }}
      version={{ repo_result.cluster_os_version }}
      port={{ repo_result.repo_port }}
      x86_64_repos={{ repo_result.repo_manager_repos_x86_64 | length }}
      aarch64_repos={{ repo_result.repo_manager_repos_aarch64 | length }}
'''

RETURN = r'''
cluster_os_type:
  description: OS type from repo_status.yml (e.g., rhel).
  returned: always
  type: str
cluster_os_version:
  description:
    - OS version derived from first key of repositories dict.
    - Example C(10.0), C(10.1).
  returned: always
  type: str
repo_port:
  description:
    - Port number extracted from first non-empty repo URL.
    - Defaults to 2225 if no URL contains a port.
  returned: always
  type: int
repo_manager_repos_x86_64:
  description:
    - List of repo dicts for x86_64 architecture.
    - Each dict has keys C(name), C(base_url), C(gpg).
  returned: always
  type: list
  elements: dict
repo_manager_repos_aarch64:
  description:
    - List of repo dicts for aarch64 architecture.
    - Each dict has keys C(name), C(base_url), C(gpg).
  returned: always
  type: list
  elements: dict
'''

DEFAULT_PORT = 2225
SUPPORTED_ARCHS = ("x86_64", "aarch64")


def _load_repo_status(file_path: str) -> dict:
    """Load and validate repo_status.yml.

    Args:
        file_path: Path to repo_status.yml.

    Returns:
        Parsed YAML dict.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If required keys are missing.
    """
    with open(file_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(
            f"repo_status.yml is not a valid YAML dict: {file_path}"
        )
    if "repositories" not in data or not data["repositories"]:
        raise ValueError(
            "repo_status.yml missing required 'repositories' section"
        )
    if "cluster_os_type" not in data:
        raise ValueError(
            "repo_status.yml missing required 'cluster_os_type' field"
        )
    return data


def _extract_port(url: str) -> int:
    """Extract port from a URL, return 0 if not present.

    Args:
        url: Repository URL string.

    Returns:
        Port number or 0.
    """
    try:
        parsed = urlparse(url)
        return parsed.port or 0
    except (ValueError, AttributeError):
        return 0


def _find_repo_port(version_repos: dict) -> int:
    """Find port from first non-empty repo URL across all architectures.

    Args:
        version_repos: Dict of {arch: {repo_name: {url: ...}}}.

    Returns:
        Port number or DEFAULT_PORT.
    """
    for arch in SUPPORTED_ARCHS:
        arch_repos = version_repos.get(arch, {})
        if not isinstance(arch_repos, dict):
            continue
        for repo_data in arch_repos.values():
            if (
                isinstance(repo_data, dict)
                and repo_data.get("url")
            ):
                port = _extract_port(repo_data["url"])
                if port > 0:
                    return port
    return DEFAULT_PORT


def _build_repo_list(arch_repos: dict) -> list:
    """Build repo list from architecture-specific repos.

    Args:
        arch_repos: Dict of {repo_name: {url: str, ...}}.

    Returns:
        List of dicts with name, base_url, gpg keys.
    """
    result: list = []
    if not isinstance(arch_repos, dict):
        return result

    for repo_name, repo_data in arch_repos.items():
        if (
            isinstance(repo_data, dict)
            and repo_data.get("url")
        ):
            result.append({
                "name": repo_name,
                "base_url": repo_data["url"],
                "gpg": "",
            })
    return result


def parse_repo_status(file_path: str) -> dict:
    """Main entry: parse repo_status.yml and build repo lists.

    Args:
        file_path: Path to repo_status.yml.

    Returns:
        Dict with cluster_os_type, cluster_os_version, repo_port,
        repo_manager_repos_x86_64, repo_manager_repos_aarch64.
    """
    data = _load_repo_status(file_path)

    repositories = data["repositories"]
    os_type = data.get("cluster_os_type", "rhel")

    versions = list(repositories.keys())
    os_version = versions[0] if versions else "10.0"

    version_repos = repositories.get(os_version, {})
    repo_port = _find_repo_port(version_repos)

    repos_x86 = _build_repo_list(
        version_repos.get("x86_64", {})
    )
    repos_aarch64 = _build_repo_list(
        version_repos.get("aarch64", {})
    )

    return {
        "cluster_os_type": os_type,
        "cluster_os_version": str(os_version),
        "repo_port": repo_port,
        "repo_manager_repos_x86_64": repos_x86,
        "repo_manager_repos_aarch64": repos_aarch64,
    }


def main():
    """Main module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            repo_status_file=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )

    try:
        result = parse_repo_status(
            file_path=module.params["repo_status_file"],
        )
        module.exit_json(changed=False, **result)
    except FileNotFoundError as exc:
        module.fail_json(
            msg=f"repo_status.yml not found: {exc}"
        )
    except ValueError as exc:
        module.fail_json(
            msg=f"repo_status.yml validation failed: {exc}"
        )
    except Exception as exc:  # pylint: disable=broad-except
        module.fail_json(
            msg=f"repo_status parsing failed: {exc}"
        )


if __name__ == "__main__":
    main()
