# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Fail-closed Pulp lifecycle helpers for File and Python content."""

import json
import os

from ansible.module_utils.repo_manager.pulp_commands import (
    pulp_file_commands,
    pulp_python_commands,
)
from ansible.module_utils.repo_manager.pulp_object_state import query_pulp_object
from ansible.module_utils.repo_manager.shared_artifact_state import (
    SharedArtifactStateError,
    file_sha256,
)


def ensure_pulp_object(
        show_command, create_command, object_label, logger, executor):
    """Ensure one object exists without treating an unknown read as absent."""
    present, details = query_pulp_object(show_command, logger, executor)
    if present is None:
        logger.error("Unable to determine %s state", object_label)
        return False, None
    if present is True:
        return True, details
    if not executor(create_command, logger):
        logger.error("Failed to create %s", object_label)
        return False, None
    verified, details = query_pulp_object(show_command, logger, executor)
    if verified is not True:
        logger.error("Unable to verify newly created %s", object_label)
        return False, None
    return True, details


def reconcile_pulp_distribution(
        show_command, create_command, update_command, object_label,
        logger, executor, repository_show_command=None):
    """Create/update a distribution and verify its repository binding."""
    expected_repository_href = None
    if repository_show_command is not None:
        repository_present, repository_details = query_pulp_object(
            repository_show_command, logger, executor
        )
        if repository_present is not True or not isinstance(
                repository_details, dict):
            logger.error("Unable to verify repository for %s", object_label)
            return False
        expected_repository_href = repository_details.get("pulp_href")
        if not isinstance(expected_repository_href, str) or not (
                expected_repository_href):
            logger.error("Repository for %s has no Pulp href", object_label)
            return False

    present, _details = query_pulp_object(show_command, logger, executor)
    if present is None:
        logger.error("Unable to determine %s state", object_label)
        return False
    command = update_command if present else create_command
    if not executor(command, logger):
        logger.error("Failed to reconcile %s", object_label)
        return False
    verified, details = query_pulp_object(show_command, logger, executor)
    if verified is not True:
        logger.error("Unable to verify %s after reconciliation", object_label)
        return False
    if expected_repository_href is not None and (
            not isinstance(details, dict)
            or details.get("repository") != expected_repository_href):
        logger.error(
            "%s does not reference its expected repository", object_label
        )
        return False
    return True


def _pulp_list_results(details):
    """Return a Pulp CLI list response, or ``None`` for invalid data."""
    if isinstance(details, list):
        return details
    if isinstance(details, dict) and isinstance(details.get("results"), list):
        return details["results"]
    return None


def _latest_repository_version(show_command, object_label, logger, executor):
    """Return a verified latest repository-version href, or ``None``."""
    present, details = query_pulp_object(show_command, logger, executor)
    if present is not True or not isinstance(details, dict):
        logger.error("Unable to verify %s state", object_label)
        return None
    version_href = details.get("latest_version_href")
    if not isinstance(version_href, str) or not version_href:
        logger.error("%s has no latest repository version", object_label)
        return None
    return version_href


def reconcile_file_content(
        repository_name, file_path, relative_path, logger, executor):
    """Associate exact File content by digest, uploading only when absent."""
    try:
        digest = file_sha256(file_path)
    except SharedArtifactStateError:
        logger.error("File content is not a regular verified artifact")
        return False

    query_command = pulp_file_commands["list_content_exact"] % (
        digest, relative_path,
    )
    readable, details = query_pulp_object(query_command, logger, executor)
    matches = _pulp_list_results(details)
    if readable is not True or matches is None:
        logger.error("Unable to determine exact File content state")
        return False

    if matches:
        logger.info("Reusing verified File content already stored by Pulp")
        content_identity = json.dumps(
            [{"sha256": digest, "relative_path": relative_path}],
            sort_keys=True,
            separators=(",", ":"),
        )
        command = pulp_file_commands["content_add"] % (
            repository_name, content_identity,
        )
    else:
        command = pulp_file_commands["content_upload"] % (
            repository_name, file_path, relative_path,
        )
    if not executor(command, logger):
        return False

    version_href = _latest_repository_version(
        pulp_file_commands["show_repository"] % repository_name,
        f"File repository {repository_name}",
        logger,
        executor,
    )
    if not version_href:
        return False
    verified, version_details = query_pulp_object(
        pulp_file_commands["list_repository_content_exact"] % (
            digest, relative_path, version_href,
        ),
        logger,
        executor,
    )
    version_matches = _pulp_list_results(version_details)
    return verified is True and bool(version_matches)


def reconcile_python_content(
        repository_name, file_path, logger, executor):
    """Associate exact Python content by digest, uploading only when absent."""
    try:
        digest = file_sha256(file_path)
    except SharedArtifactStateError:
        logger.error("Python content is not a regular verified artifact")
        return False

    readable, details = query_pulp_object(
        pulp_python_commands["list_content_sha256"] % digest,
        logger,
        executor,
    )
    matches = _pulp_list_results(details)
    if readable is not True or matches is None:
        logger.error("Unable to determine exact Python content state")
        return False

    artifact_name = os.path.basename(file_path)
    if matches:
        logger.info("Reusing verified Python content already stored by Pulp")
        content_identity = json.dumps(
            [{"sha256": digest}], sort_keys=True, separators=(",", ":")
        )
        command = pulp_python_commands["content_add"] % (
            repository_name, content_identity,
        )
    else:
        command = pulp_python_commands["content_upload"] % (
            repository_name, file_path, artifact_name,
        )
    if not executor(command, logger):
        return False

    version_href = _latest_repository_version(
        pulp_python_commands["show_repository"] % repository_name,
        f"Python repository {repository_name}",
        logger,
        executor,
    )
    if not version_href:
        return False
    verified, version_details = query_pulp_object(
        pulp_python_commands["list_repository_content_sha256"] % (
            digest, version_href,
        ),
        logger,
        executor,
    )
    version_matches = _pulp_list_results(version_details)
    return verified is True and bool(version_matches)
