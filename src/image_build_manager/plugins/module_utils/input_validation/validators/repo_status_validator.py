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


def _version_keys(mapping):
    """Return normalized string keys for a version-keyed mapping."""
    if not isinstance(mapping, dict):
        return set()
    return {str(version) for version in mapping}


def _validate_contexts(repo_status_data):
    """Return context errors and the ordered selected OS versions."""
    errors = []
    contexts = repo_status_data.get("execution_contexts", [])
    context_ids = []
    context_versions = []
    cluster_os_type = repo_status_data.get("cluster_os_type")
    if isinstance(contexts, list):
        for context in contexts:
            if not isinstance(context, dict):
                continue
            context_id = context.get("context_id")
            version = context.get("os_version")
            if context_id is not None:
                context_ids.append(str(context_id))
            if version is not None:
                context_versions.append(str(version))
            if context.get("os_type") != cluster_os_type:
                errors.append(
                    "repo_status.yml: every execution context os_type must "
                    "match cluster_os_type."
                )
                break

    if len(context_ids) != len(set(context_ids)):
        errors.append(
            "repo_status.yml: execution_contexts contains duplicate context_id values."
        )
    if len(context_versions) != len(set(context_versions)):
        errors.append(
            "repo_status.yml: execution_contexts contains duplicate OS versions."
        )
    return errors, context_versions


def _validate_version_maps(context_versions, status_by_version, repositories):
    """Return errors for mismatched or incomplete version-keyed output."""
    errors = []
    selected_versions = set(context_versions)
    status_versions = _version_keys(status_by_version)
    repository_versions = _version_keys(repositories)
    if selected_versions != status_versions:
        errors.append(
            "repo_status.yml: overall_status_by_version keys must exactly match "
            "the execution_contexts OS versions."
        )
    if selected_versions != repository_versions:
        errors.append(
            "repo_status.yml: repositories keys must exactly match the "
            "execution_contexts OS versions."
        )

    if isinstance(status_by_version, dict):
        incomplete_versions = sorted(
            str(version)
            for version, status in status_by_version.items()
            if status != "success"
        )
        if incomplete_versions:
            errors.append(
                "repo_status.yml: overall_status_by_version must be 'success' "
                "for every version; incomplete versions: "
                + ", ".join(incomplete_versions)
                + "."
            )
    return errors


def _validate_architecture_maps(contexts, repositories):
    """Require each version to expose exactly its selected architectures."""
    errors = []
    if not isinstance(contexts, list) or not isinstance(repositories, dict):
        return errors
    for context in contexts:
        if not isinstance(context, dict):
            continue
        version = str(context.get("os_version", ""))
        expected = set(context.get("architectures", []))
        version_repositories = repositories.get(version, {})
        actual = (
            set(version_repositories)
            if isinstance(version_repositories, dict)
            else set()
        )
        if expected != actual:
            errors.append(
                "repo_status.yml: repositories."
                f"{version} architecture keys must match execution_contexts."
            )
    return errors


def _has_repository_url(repositories):
    """Return whether any architecture has a consumable RPM repository URL."""
    if isinstance(repositories, dict):
        for version_data in repositories.values():
            if not isinstance(version_data, dict):
                continue
            for arch_repositories in version_data.values():
                if not isinstance(arch_repositories, dict):
                    continue
                for repository in arch_repositories.values():
                    if not isinstance(repository, dict):
                        continue
                    url = repository.get("url")
                    if isinstance(url, str) and url.strip():
                        return True
    return False


def validate(repo_status_data, logger=None):
    """Validate cross-field consistency required by image build consumers."""
    errors = []

    if repo_status_data.get("overall_status") != "success":
        errors.append("repo_status.yml: overall_status must be 'success'.")

    context_errors, context_versions = _validate_contexts(repo_status_data)
    errors.extend(context_errors)
    status_by_version = repo_status_data.get("overall_status_by_version", {})
    repositories = repo_status_data.get("repositories", {})
    errors.extend(
        _validate_version_maps(
            context_versions, status_by_version, repositories
        )
    )
    errors.extend(
        _validate_architecture_maps(
            repo_status_data.get("execution_contexts", []), repositories
        )
    )

    if not _has_repository_url(repositories):
        errors.append(
            "repo_status.yml: repositories must contain at least one non-empty "
            "repository URL."
        )

    if logger:
        for error in errors:
            logger.error(error)
    return errors
