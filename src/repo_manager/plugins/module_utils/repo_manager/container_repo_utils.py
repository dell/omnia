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
# pylint: disable=import-error,no-name-in-module,line-too-long,broad-exception-caught
# pylint: disable=no-else-return,too-many-locals,too-many-nested-blocks
# pylint: disable=too-many-return-statements,too-many-branches,too-many-statements

"""
Container repository utilities for Pulp operations.

This module provides functions for creating, syncing, and managing
container repositories and distributions in Pulp.
"""

import multiprocessing
from ansible.module_utils.repo_manager.container_platform import (
    verify_container_reference,
)
from ansible.module_utils.repo_manager.parse_and_download import execute_command
from ansible.module_utils.repo_manager.pulp_object_state import query_pulp_object
from ansible.module_utils.repo_manager.pulp_commands import pulp_container_commands
from ansible.module_utils.repo_manager.security_utils import (
    validate_container_digest,
    validate_container_reference,
    validate_container_tag,
    validate_repository_id,
)
remote_creation_lock = multiprocessing.Lock()
repository_creation_lock = multiprocessing.Lock()

# Per-distribution locks for container operations
_container_distribution_locks = {}
_container_dist_locks_lock = multiprocessing.Lock()

def get_container_distribution_lock(dist_name):
    """
    Get or create lock for specific container distribution.

    This allows different container distributions to be processed in parallel
    while preventing race conditions for the same distribution.

    Args:
        dist_name (str): The distribution name to get a lock for.

    Returns:
        Lock: The lock for this specific distribution.
    """
    with _container_dist_locks_lock:
        if dist_name not in _container_distribution_locks:
            _container_distribution_locks[dist_name] = multiprocessing.Lock()
        return _container_distribution_locks[dist_name]


def create_container_repository(repo_name, logger):
    """
    Creates a container repository.
    Args:
        repo_name (str): The name of the repository.
    Returns:
        bool: True if the repository was created successfully or already exists,
              False if there was an error.
    """
    try:
        repo_name = validate_repository_id(repo_name)
        present, _details = query_pulp_object(
            pulp_container_commands["show_repository"] % repo_name,
            logger,
            execute_command,
        )
        if present is None:
            logger.error("Unable to determine container repository state")
            return False
        if present is False:
            command = pulp_container_commands["create_repository"] % repo_name
            result = execute_command(command, logger)
            logger.info(f"Repository created successfully: {repo_name}")
            return result
        logger.info(f"Repository {repo_name} already exists.")
        return True
    except Exception:
        logger.error("Failed to create the container repository")
        return False


def extract_existing_tags(remote_name, logger):
    """
    Extracts existing include_tags from a container remote.
    Args:
        remote_name (str): The name of the remote.
    Returns:
        list: A list of existing tags, or an empty list if an error occurs.
    """
    try:
        remote_name = validate_repository_id(remote_name)
        command = pulp_container_commands["list_remote_tags"] % remote_name
        present, remotes = query_pulp_object(command, logger, execute_command)
        if present is not True:
            logger.error("Failed to fetch remote tags.")
            raise ValueError("Container remote tag state is unknown")
        if not isinstance(remotes, list) or len(remotes) == 0:
            logger.error("Unexpected data format for remote tags.")
            raise ValueError("Container remote tag response is invalid")

        # pulp-cli exposes ContainerRemote.include_tags as ``includes``.
        # Keep the old key as a compatibility alias for older responses.
        return remotes[0].get("includes", remotes[0].get("include_tags", []))

    except ValueError:
        raise
    except Exception as error:
        logger.error("Failed to extract container remote tags")
        raise ValueError("Container remote tag state is unknown") from error


def create_container_distribution(repo_name, package_content, logger):
    """
    Create or update a distribution for a repository.

    Args:
        repo_name (str): The name of the repository.
        package_content (str): The content of the package.
        logger (logging.Logger): The logger instance.
    Returns:
        bool: True if the distribution is created or updated successfully, False otherwise.
    Raises:
        Exception: If there is an error creating or updating the distribution.
    """
    try:
        repo_name = validate_repository_id(repo_name)
        package_content = validate_container_reference(package_content)
        # Get lock for this specific distribution
        dist_lock = get_container_distribution_lock(repo_name)

        with dist_lock:
            repository_present, repository_details = query_pulp_object(
                pulp_container_commands["show_repository"] % repo_name,
                logger,
                execute_command,
            )
            if repository_present is not True or not isinstance(
                    repository_details, dict):
                logger.error("Unable to verify container repository state")
                return False
            expected_repository = repository_details.get("pulp_href")
            if not isinstance(expected_repository, str) or not expected_repository:
                logger.error("Container repository has no Pulp href")
                return False

            present, _details = query_pulp_object(
                pulp_container_commands["show_distribution"] % repo_name,
                logger,
                execute_command,
            )
            if present is None:
                logger.error("Unable to determine container distribution state")
                return False
            if present is False:
                command = pulp_container_commands["distribution_create"] % (
                    repo_name, repo_name, package_content,
                )
            else:
                command = pulp_container_commands["distribution_update"] % (
                    repo_name, repo_name, package_content,
                )
            if not execute_command(command, logger):
                return False
            verified, details = query_pulp_object(
                pulp_container_commands["show_distribution"] % repo_name,
                logger,
                execute_command,
            )
            if verified is not True or not isinstance(details, dict):
                logger.error("Unable to verify container distribution state")
                return False
            if details.get("repository") != expected_repository:
                logger.error(
                    "Container distribution does not reference its repository"
                )
                return False
            return True
    except Exception:
        logger.error("Failed to create the container distribution")
        return False


def sync_container_repository(
        repo_name, remote_name, package_content, logger, tag=None,
        architecture=None):
    """
    Synchronizes and distribute container repository with a remote.
    Args:
        repo_name (str): The name of the repository.
        remote_name (str): The name of the remote.
        package_content (str): Upstream name.
        logger: Logger instance.
        tag (str, optional): The tag to validate in repository content.
    Returns:
        bool: True if the synchronization is successful, False otherwise.
    """
    try:
        repo_name = validate_repository_id(repo_name)
        remote_name = validate_repository_id(remote_name)
        package_content = validate_container_reference(package_content)
        if tag is not None:
            if str(tag).startswith("sha256:"):
                tag = validate_container_digest(tag)
            else:
                tag = validate_container_tag(tag)
        logger.info(f"Getting repository version before sync for {repo_name}")
        verify_command = (
            pulp_container_commands["show_repository"] % repo_name
        )
        verify_result_before = execute_command(verify_command, logger, type_json=True)

        version_before = None
        if (verify_result_before and isinstance(verify_result_before, dict) and
                "stdout" in verify_result_before):
            repo_data_before = verify_result_before["stdout"]
            if isinstance(repo_data_before, dict):
                version_before = repo_data_before.get("latest_version_href")
                logger.info(f"Repository version before sync: {version_before}")

        command = pulp_container_commands["sync_repository"] % (
            repo_name, remote_name,
        )
        result = execute_command(command, logger)
        if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
            logger.error(f"Sync command failed for repository {repo_name}")
            return False

        logger.info(f"Validating sync result for repository {repo_name}")
        repository_state, repo_data_after = query_pulp_object(
            verify_command, logger, execute_command
        )
        if repository_state is not True or not isinstance(repo_data_after, dict):
            logger.error("Unable to verify repository after container sync")
            return False
        version_after = repo_data_after.get("latest_version_href")
        logger.info(f"Repository version after sync: {version_after}")
        if (
                not isinstance(version_after, str)
                or version_after.endswith("/versions/0/")):
            logger.error(
                "Sync completed but no content was downloaded for %s",
                repo_name,
            )
            return False
        if tag is not None:
            reference_state = verify_container_reference(
                version_after, tag, architecture, logger, execute_command
            )
            if reference_state is not True:
                logger.error(
                    "Container reference is absent, incompatible, or unknown "
                    "after sync"
                )
                return False
        logger.info(
            "Sync validation successful: repository %s version changed "
            "from %s to %s",
            repo_name,
            version_before,
            version_after,
        )
        result = create_container_distribution(repo_name, package_content, logger)
        return result
    except Exception:
        logger.error("Failed to synchronize the container repository")
        return False
