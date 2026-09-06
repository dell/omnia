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
"""Validate repository certificate configuration and filesystem state."""

# pylint: disable=import-error,no-name-in-module
import os
from ansible.module_utils.repo_manager.common_functions import load_yaml_file
from ansible.module_utils.repo_manager.config import (
    get_repos_section,
    iterate_all_repos
)




def validate_repo_certificates(repo_list, certs_path):
    """
    Validates the repository certificates based on the provided repository list and certificate path.

    Parameters:
        repo_list (list): A list of dictionaries containing repository information.
        certs_path (str): The path to the repository certificates.

    Returns:
        list: A list of strings describing certificate issues for each repository.
    """

    cert_issues = []

    if not repo_list:
        return cert_issues

    for repo in repo_list:
        repo_name = repo.get("name", "unnamed_repo")

        # Skip certificate validation for repos with empty SSL cert fields
        cert_keys = ["sslcacert", "sslclientkey", "sslclientcert"]
        cert_values = {key: repo.get(key) for key in cert_keys}

        # Skip if all cert values are None or empty strings (no cert scenario)
        if all(value is None or value == "" for value in cert_values.values()):
            continue

        # Skip if URL is empty (RHEL subscription repos)
        if repo.get("url", "") == "":
            continue

        repo_cert_path = os.path.join(certs_path, repo_name)

        if not os.path.isdir(repo_cert_path):
            cert_issues.append(f"{repo_name} (certificate path not found)")
            continue

        all_files = os.listdir(repo_cert_path)
        pem_files = [f for f in all_files if f.endswith(".pem")]
        key_files = [f for f in all_files if f.endswith(".key")]
        crt_files = [f for f in all_files if f.endswith(".crt")]

        issues = []

        if len(pem_files) != 3:
            issues.append(f"{len(pem_files)} .pem files found: {pem_files}")
        if len(key_files) > 1:
            issues.append(f"{len(key_files)} .key files found: {key_files}")
        if len(crt_files) > 1:
            issues.append(f"{len(crt_files)} .crt files found: {crt_files}")

        if issues:
            cert_issues.append(f"{repo_name} ({'; '.join(issues)})")

    return cert_issues


def validate_certificates(local_repo_config_path, certs_path,
                          cluster_os_version, architectures):
    """
    Validates the repository certificates based on the provided repository list and certificate path.

    Parameters:
        local_repo_config_path (str): The path to the local repository configuration file.
        certs_path (str): The path to the repository certificates.
        cluster_os_version (str): OS version selected from the catalog.

    Returns:
        dict: A dictionary containing the validation status and a list of issues if any.
    """

    config_file = load_yaml_file(local_repo_config_path)

    # Collect all repos with certificates from new structure
    all_repos = []
    for arch in architectures:
        repos_section = get_repos_section(config_file, cluster_os_version, arch)
        for repo_name, repo_config in iterate_all_repos(repos_section):
            if repo_config and isinstance(repo_config, dict):
                entry = {"name": repo_name, **repo_config}
                all_repos.append(entry)

    issues = validate_repo_certificates(all_repos, certs_path)

    if issues:
        return {"status": "error", "missing": issues}

    return {"status": "ok"}
