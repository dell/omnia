# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

# pylint: disable=import-error,no-name-in-module,line-too-long
import multiprocessing
from ansible.module_utils.local_repo.parse_and_download import execute_command
from ansible.module_utils.local_repo.config import (
    pulp_container_commands
)
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
remote_creation_lock = multiprocessing.Lock()
repository_creation_lock = multiprocessing.Lock()

def create_container_repository(repo_name,logger):
    """
    Creates a container repository.
    Args:
        repo_name (str): The name of the repository.
    Returns:
        bool: True if the repository was created successfully or already exists, False if there was an error.
    """
    try:
        if not execute_command(pulp_container_commands["show_container_repo"] % (repo_name), logger):
            command = pulp_container_commands["create_container_repo"] % (repo_name)
            result = execute_command(command,logger)
            logger.info(f"Repository created successfully: {repo_name}")
            return result
        else:
            logger.info(f"Repository {repo_name} already exists.")
            return True
    except Exception as e:
        logger.error(f"Failed to create repository {repo_name}. Error: {e}")
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
        command = pulp_container_commands["list_container_remote_tags"] % remote_name
        result = execute_command(command, logger, type_json=True)

        if not result or not isinstance(result, dict) or "stdout" not in result:
            logger.error("Failed to fetch remote tags.")
            return []

        remotes = result["stdout"]
        if not isinstance(remotes, list) or len(remotes) == 0:
            logger.error("Unexpected data format for remote tags.")
            return []

        return remotes[0].get("include_tags", [])

    except Exception as e:
        logger.error(f"Error extracting tags: {e}")
        return []

def create_container_distribution(repo_name,package_content,logger):
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
        if not execute_command(pulp_container_commands["show_container_distribution"] % (repo_name), logger):
            command = pulp_container_commands["distribute_container_repository"] % (repo_name, repo_name, package_content)
            return execute_command(command,logger)
        else:
            command = pulp_container_commands["update_container_distribution"] % (repo_name, repo_name, package_content)
            return execute_command(command,logger)
    except Exception as e:
        logger.error(f"Error creating distribution {repo_name}: {e}")
        return False

def sync_container_repository(repo_name, remote_name, package_content, logger):
    """
    Synchronizes and distribute container repository with a remote.
    Args:
        repo_name (str): The name of the repository.
        remote_name (str): The name of the remote.
        package_content (str): Upstream name.
    Returns:
        bool: True if the synchronization is successful, False otherwise.
    """
    try:
        command = pulp_container_commands["sync_container_repository"] % (repo_name, remote_name)
        result = execute_command(command,logger)
        if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
            return False
        else:
            result = create_container_distribution(repo_name,package_content,logger)
            return result
    except Exception as e:
        logger.error(f"Failed to synchronize repository {repo_name} with remote {remote_name}. Error: {e}")
        return False
