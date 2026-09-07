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
"""Semantic validation for the repo_status.yml input contract."""


def validate(repo_status_data, logger=None):
    """Require a successful contract with at least one usable x86_64 RPM URL."""
    errors = []

    if repo_status_data.get("overall_status") != "success":
        errors.append("repo_status.yml: overall_status must be 'success'.")

    x86_urls = []
    repositories = repo_status_data.get("repositories", {})
    if isinstance(repositories, dict):
        for version_data in repositories.values():
            if not isinstance(version_data, dict):
                continue
            arch_repositories = version_data.get("x86_64", {})
            if not isinstance(arch_repositories, dict):
                continue
            for repository in arch_repositories.values():
                if not isinstance(repository, dict):
                    continue
                url = repository.get("url")
                if isinstance(url, str) and url.strip():
                    x86_urls.append(url)

    if not x86_urls:
        errors.append(
            "repo_status.yml: repositories must contain at least one non-empty "
            "x86_64 repository URL."
        )

    if logger:
        for error in errors:
            logger.error(error)
    return errors
