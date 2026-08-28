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

# pylint:
# disable=import-error,no-name-in-module,too-many-branches,too-many-positional-arguments,too-many-arguments,too-many-locals,too-many-statements,broad-exception-caught,broad-exception-raised
"""This module handles mirroring of container images in the local repository."""

import re
import json
from multiprocessing import Lock
from jinja2 import Template
from ansible.module_utils.repo_manager.process_parallel import docker_password_cipher
from ansible.module_utils.repo_manager.parse_and_download import (
    execute_command, write_status_to_file
)
from ansible.module_utils.repo_manager.user_image_utility import handle_user_image_registry
from ansible.module_utils.repo_manager.config import pulp_container_commands
from ansible.module_utils.repo_manager.container_repo_utils import (
    create_container_repository,
    extract_existing_tags,
    sync_container_repository,
    repository_creation_lock
)
from ansible.module_utils.repo_manager.tag_validator import validate_tag_via_pulp_sync

file_lock = Lock()

# Per-operation lock manager for thread-safe remote operations
# Lock key is the remote name — ensures only one thread modifies a given remote at a time
_operation_locks = {}
_operation_locks_lock = Lock()


def _get_operation_lock(key):
    """
    Get or create a lock for a specific operation key.

    Key is the remote name — ensures only one thread modifies a given remote at a time.
    This prevents race conditions when multiple threads process different tags
    for the same image (same remote).

    Args:
        key (str): The operation key (remote name) to get a lock for.

    Returns:
        Lock: The lock for this specific operation key.
    """
    with _operation_locks_lock:
        if key not in _operation_locks:
            _operation_locks[key] = Lock()
        return _operation_locks[key]


def _image_already_synced(repository_name, tag, logger):
    """
    Check if a specific tag already exists in the Pulp repository.

    Args:
        repository_name (str): Name of the Pulp repository.
        tag (str): Specific tag to check.
        logger: Logger instance.

    Returns:
        bool: True if the specific tag exists, False otherwise.
    """
    try:
        # Check if repository has any content
        cmd = f"pulp container repository show --name {repository_name}"
        result = execute_command(cmd, logger, type_json=True)

        if result and "stdout" in result:
            repo_data = result["stdout"]
            version_href = repo_data.get("latest_version_href")

            # If repository has no content (version 0), tag doesn't exist
            if not version_href or version_href.endswith("/versions/0/"):
                return False

            # Check if SPECIFIC tag exists in repository content
            tags_cmd = (
                f"pulp show --href '/pulp/api/v3/content/container/tags/"
                f"?repository_version={version_href}&name={tag}'"
            )
            tags_result = execute_command(tags_cmd, logger, type_json=True)

            if tags_result and "stdout" in tags_result:
                tags_data = tags_result["stdout"]
                results = tags_data.get("results", [])

                # Check if SPECIFIC tag exists
                if len(results) > 0:
                    logger.info(
                        f"Tag '{tag}' already exists in repository {repository_name}. "
                        f"Skipping sync."
                    )
                    return True

        return False
    except Exception as e:
        logger.warning(f"Error checking if image synced: {e}")
        return False


def create_container_remote_with_auth(
    remote_name, remote_url, package, policy_type,
    tag, logger, docker_username, docker_secret_token
):
    """
    Create a container remote with authentication.

    Creates a new container remote or updates an existing one with the provided tag
    and authentication credentials.

    Parameters:
        remote_name (str): Name of the container remote.
        remote_url (str): URL of the container remote.
        package (str): Package name.
        policy_type (str): Policy type.
        tag (str): Tag to add to the container remote.
        logger (object): Logger instance.
        docker_username (str): Docker username.
        docker_password (str): Docker password.

    Returns:
        bool: True if the container remote was created or updated successfully,
              False otherwise.
    """
    try:
        docker_password = docker_password_cipher.decrypt(
            docker_secret_token.encode("utf-8")
        ).decode("utf-8")
        remote_exists = execute_command(pulp_container_commands["show_container_remote"] % remote_name, logger)
        if not remote_exists:
            tags_json = json.dumps([tag])  # --> '["1.25.2-alpine"]'
            create_command = pulp_container_commands[
                "create_container_remote_auth"
            ] % (
                remote_name, remote_url, package, policy_type, tags_json,
                docker_username, docker_password
            )

            result = execute_command(create_command, logger)
            if result:
                logger.info(f"Remote '{remote_name}' created successfully with auth.")
                return True
            logger.error(f"Failed to create remote '{remote_name}' with auth.")
            return False

        logger.info(f"Remote '{remote_name}' already exists. Checking tags.")
        existing_tags = extract_existing_tags(remote_name, logger)
        if tag in existing_tags:
            logger.info(f"Tag '{tag}' already exists. No update needed.")
            return True

        new_tags = existing_tags + [tag]
        tags_str = json.dumps(new_tags)

        update_command = pulp_container_commands[
            "update_container_remote_auth"
        ] % (
            remote_name, remote_url, package, policy_type, tags_str,
            docker_username, docker_password
        )
        result = execute_command(update_command, logger)
        if result:
            logger.info(
                f"Remote '{remote_name}' updated successfully with auth and tags: {new_tags}"
            )
            return True
        logger.error(f"Failed to update remote '{remote_name}' with auth.")
        return False

    except Exception as error:
        logger.error(f"Error in create/update remote '{remote_name}' with auth: {error}")
        return False


def create_container_remote(remote_name, remote_url, package, policy_type, tag, logger):
    """
    Creates or updates a container remote with the specified tag.

    If the remote does not exist, it is created with the provided tag. If the remote
    already exists, the function retrieves the current tags, checks if the new tag is
    already included, and updates the remote if necessary.

    Args:
        remote_name (str): The name of the container remote.
        remote_url (str): The URL of the container remote.
        package (str): The upstream package name.
        policy_type (str): The policy type for the remote (e.g., "immediate" or "on_demand").
        tag (str): The tag to be added to the include_tags list.
        logger (Logger): Logger instance for logging messages.

    Returns:
        bool: True if the remote was successfully created or updated, False otherwise.
    """
    try:
        # Check if the remote exists
        remote_exists = execute_command(
            pulp_container_commands["show_container_remote"] % remote_name, logger
        )
        if not remote_exists:
            # If remote does not exist, create it with the provided tag
            command = pulp_container_commands["create_container_remote"] % (
                remote_name, remote_url, package, policy_type, tag
            )
            result = execute_command(command, logger)
            if result:
                logger.info(f"Remote '{remote_name}' created successfully.")
                return True
            logger.error(f"Failed to create remote '{remote_name}'.")
            return False

        logger.info(f"Remote '{remote_name}' already exists. Updating include_tags.")
        # Retrieve existing tags
        existing_tags = extract_existing_tags(remote_name, logger)
        # If the tag already exists, no update is needed
        if tag in existing_tags:
            logger.info(
                f"Tag '{tag}' already exists for remote '{remote_name}'. No update needed."
            )
            return True
        # Append new tag and update
        new_tags = existing_tags + [tag]
        tags_json = json.dumps(new_tags)  # Ensuring proper JSON formatting
        update_command = pulp_container_commands["update_container_remote"] % (
            remote_name, remote_url, package, policy_type, tags_json
        )
        result = execute_command(update_command, logger)
        if result:
            logger.info(f"Remote '{remote_name}' updated successfully with tags: {new_tags}")
            return True
        logger.error(f"Failed to update remote '{remote_name}'.")
        return False

    except Exception as error:
        logger.error(f"Error in create/update remote '{remote_name}': {error}")
        return False


def create_container_remote_digest(remote_name, remote_url, package, policy_type, logger):
    """
    Creates a container remote for a given package.
    Args:
        remote_name (str): The name of the remote.
        remote_url (str): The URL of the remote.
        package (str): The package to create the remote for.
        policy_type (str): The policy type for the remote.
    Returns:
        bool: True if the remote was created or updated successfully, False otherwise.
    Raises:
        Exception: If there was an error creating or updating the remote.
    """
    try:
        if not execute_command(
            pulp_container_commands["show_container_remote"] % (remote_name), logger
        ):
            command = pulp_container_commands[
                "create_container_remote_for_digest"
            ] % (remote_name, remote_url, package, policy_type)
            result = execute_command(command, logger)
            logger.info(f"Remote created successfully: {remote_name}")
            return result

        logger.info(f"Remote {remote_name} already exists.")
        command = pulp_container_commands[
            "update_remote_for_digest"
        ] % (remote_name, remote_url, package, policy_type)
        result = execute_command(command, logger)
        logger.info(f"Remote updated successfully: {remote_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to create remote {remote_name}. Error: {e}")
        return False


def get_repo_url_and_content(package):
    """
    Get the repository URL and content from a given package.
    Parameters:
        package (str): The package to extract the URL and content from.
    Returns:
        tuple: A tuple containing the repository URL and content.
    Raises:
        ValueError: If the package prefix is not supported.
    """
    patterns = {
        r"^(ghcr\.io)(:\d+)?(/.+)": "https://ghcr.io",
        r"^(docker\.io)(:\d+)?(/.+)": "https://registry-1.docker.io",
        r"^(quay\.io)(:\d+)?(/.+)": "https://quay.io",
        r"^(registry\.k8s\.io)(:\d+)?(/.+)": "https://registry.k8s.io",
        r"^(nvcr\.io)(:\d+)?(/.+)": "https://nvcr.io",
        r"^(public\.ecr\.aws)(:\d+)?(/.+)": "https://public.ecr.aws",
        r"^(gcr\.io)(:\d+)?(/.+)": "https://gcr.io",
    }
    for pattern, repo_url in patterns.items():
        match = re.match(pattern, package)
        if match:
            base_url = repo_url

            # If user provided a port, preserve it
            if match.group(2):
                base_url = f"{repo_url}{match.group(2)}"

            package_content = match.group(3).lstrip("/")
            return base_url, package_content

    # fallback for private / IP-based registries
    match = re.match(r"^(?P<registry>[^/]+)(?P<path>/.*)$", package)
    if match:
        return f"https://{match.group('registry')}", match.group("path").lstrip("/")

    raise ValueError(f"Invalid package format: {package}")


# def get_repo_url_and_content(package):
#     """
#     Get the repository URL and content from a given package.
#     Parameters:
#         package (str): The package to extract the URL and content from.
#     Returns:
#         tuple: A tuple containing the repository URL and content.
#     Raises:
#         ValueError: If the package prefix is not supported.
#     """
#     patterns = {
#          r"^(ghcr\.io)(/.+)": "https://ghcr.io",
#          r"^(docker\.io)(/.+)": "https://registry-1.docker.io",
#          r"^(quay\.io)(/.+)": "https://quay.io",
#          r"^(registry\.k8s\.io)(/.+)": "https://registry.k8s.io",
#          r"^(nvcr\.io)(/.+)": "https://nvcr.io",
#          r"^(public\.ecr\.aws)(/.+)": "https://public.ecr.aws",
#          r"^(gcr\.io)(/.+)": "https://gcr.io"
#     }
#     for pattern, repo_url in patterns.items():
#         match = re.match(pattern, package)
#         if match:
#             base_url = repo_url
#             package_content = match.group(2).lstrip("/")  # Remove leading slash
#             return base_url, package_content

#     raise ValueError(f"Unsupported package prefix for package: {package}")

def process_image(package, status_file_path, version_variables,
                  user_registries, docker_username, docker_secret_token, logger):
    """
    Thread-safe image processing with mandatory tag validation.

    ENFORCEMENTS:
    1. Tag validation is REQUIRED before remote creation
    2. Invalid tags are REJECTED (no fail-open)
    3. Remote-level locking prevents concurrent modifications
    4. Strict validation infrastructure requirements

    PRESERVED:
    - Repository naming (podman pull compatible)
    - Distribution naming
    - Remote naming (single remote per image)
    - Tag accumulation in remote

    THREAD SAFETY:
    - Operation lock on remote name ensures only one thread modifies a given remote
    - Different remotes can be processed in parallel
    - No rollback needed - validation gate prevents bad state

    Args:
        package (dict): The package to process.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        cluster_os_type (str): The type of the cluster operating system.
        cluster_os_version (str): The version of the cluster operating system.
        user_registry_flag (bool): if image needs to be processed from user_registry
        logger (Logger): The logger.
    Returns:
        str: "Success" if the image was processed successfully, "Failed" otherwise.
    """
    logger.info(f"--- {process_image.__name__} START ---")
    status = "Success"
    result = False

    # Read container sync policy from config
    from ansible.module_utils.repo_manager.repo_settings import (
        _config, get_container_sync_policy
    )
    policy_type = get_container_sync_policy(_config)

    base_url, package_content = get_repo_url_and_content(package['package'])
    package_identifier = None
    tag_val = None

    # Check user registries for image packages
    if user_registries:
        result, package_identifier = handle_user_image_registry(
            package,
            package_content,
            version_variables,
            user_registries,
            logger
        )

        if not result:
            logger.info(f"Image {package['package']} will not be synced to Pulp.")
            status = "Failed"
            return status

        logger.info(f"Image {package['package']} synced to Pulp.")
        status = "Success"
        return status

    try:
        repo_name_prefix = "container_repo_"
        repository_name = f"{repo_name_prefix}{package['package'].replace('/', '_').replace(':', '_')}"
        remote_name = f"remote_{package['package'].replace('/', '_').replace(':', '_')}"
        package_identifier = package['package']

        # Create container repository first (must exist before idempotency check)
        with repository_creation_lock:
            result = create_container_repository(repository_name, logger)
        if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
            raise RuntimeError(f"Failed to create repository: {repository_name}")

        # Process digest or tag
        if "digest" in package:
            package_identifier += f":{package['digest']}"
            tag_val = package['digest']  # Use digest as tag for idempotency check

            # Get per-tag lock for this digest
            tag_lock = _get_operation_lock(tag_val)

            with tag_lock:
                # Check idempotency for digest
                if _image_already_synced(repository_name, tag_val, logger):
                    logger.info(f"Image {package_identifier} already synced. Skipping.")
                    write_status_to_file(
                        status_file_path, package_identifier, package['type'],
                        "Success", logger, file_lock
                    )
                    return "Success"

                result = create_container_remote_digest(
                    remote_name, base_url, package_content, policy_type, logger
                )
                if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
                    raise RuntimeError(f"Failed to create remote digest: {remote_name}")

        elif "tag" in package:
            tag_template = Template(package['tag'])
            tag_val = tag_template.render(**version_variables)
            package_identifier += f":{package['tag']}"

            # ═══ STEP 1: Pre-validate tag ═══
            logger.info(f"Validating tag '{tag_val}' for {package['package']}...")

            tag_valid = validate_tag_via_pulp_sync(
                image_name=package['package'],
                tag=tag_val,
                logger=logger,
                pulp_container_commands=pulp_container_commands,
                execute_command=execute_command,
                create_container_repository=create_container_repository,
                get_repo_url_and_content=get_repo_url_and_content
            )

            if not tag_valid:
                logger.error(
                    f"SKIPPING: Tag '{tag_val}' does not exist upstream "
                    f"for {package['package']}."
                )
                status = "Skipped-InvalidTag"
                write_status_to_file(
                    status_file_path, package_identifier, package['type'],
                    status, logger, file_lock
                )
                return status

            # Get operation lock for this remote
            op_lock = _get_operation_lock(remote_name)

            with op_lock:
                # Check idempotency for tag
                if _image_already_synced(repository_name, tag_val, logger):
                    logger.info(f"Image {package_identifier} already synced. Skipping.")
                    write_status_to_file(
                        status_file_path, package_identifier, package['type'],
                        "Success", logger, file_lock
                    )
                    return "Success"

                if package['package'].startswith('docker.io/') and docker_username and docker_secret_token:
                    result = create_container_remote_with_auth(
                        remote_name, base_url, package_content, policy_type,
                        tag_val, logger, docker_username, docker_secret_token
                    )
                else:
                    result = create_container_remote(
                        remote_name, base_url, package_content, policy_type, tag_val, logger
                    )

                if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
                    raise RuntimeError(f"Failed to create remote: {remote_name}")

                # Sync and distribute (inside operation lock)
                # Pass tag_val if it exists (for tag-based images), otherwise None (for digest-based images)
                tag_to_pass = tag_val if "tag" in package else None
                result = sync_container_repository(
                    repository_name, remote_name, package_content, logger, tag=tag_to_pass
                )
                if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
                    raise RuntimeError(f"Failed to sync repository: {repository_name}")

    except Exception as e:
        status = "Failed"
        logger.error(f"Failed to process image: {package_identifier}. Error: {e}")

    write_status_to_file(
        status_file_path, package_identifier, package['type'], status, logger, file_lock
    )
    logger.info(f"--- {process_image.__name__} END ---")
    return status
