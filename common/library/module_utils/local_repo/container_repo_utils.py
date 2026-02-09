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
#pylint: disable=import-error,no-name-in-module

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
        bool: True if the repository was created successfully or already exists,
              False if there was an error.
    """
    try:
        if not execute_command(pulp_container_commands["show_container_repo"] % (repo_name),
                              logger):
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
        if not execute_command(pulp_container_commands["show_container_distribution"] % (repo_name),
            logger):
            command = pulp_container_commands["distribute_container_repository"] % (repo_name,
                      repo_name, package_content)
            return execute_command(command,logger)
        else:
            command = pulp_container_commands["update_container_distribution"] % (repo_name,
                      repo_name, package_content)
            return execute_command(command,logger)
    except Exception as e:
        logger.error(f"Error creating distribution {repo_name}: {e}")
        return False

def sync_container_repository(repo_name, remote_name, package_content, logger, tag=None):
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
        logger.info(f"Getting repository version before sync for {repo_name}")
        verify_command = pulp_container_commands["show_container_repo"] % repo_name
        verify_result_before = execute_command(verify_command, logger, type_json=True)
        
        version_before = None
        if verify_result_before and isinstance(verify_result_before, dict) and "stdout" in verify_result_before:
            repo_data_before = verify_result_before["stdout"]
            if isinstance(repo_data_before, dict):
                version_before = repo_data_before.get("latest_version_href")
                logger.info(f"Repository version before sync: {version_before}")
        
        command = pulp_container_commands["sync_container_repository"] % (repo_name, remote_name)
        result = execute_command(command,logger)
        if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
            logger.error(f"Sync command failed for repository {repo_name}")
            return False
        
        logger.info(f"Validating sync result for repository {repo_name}")
        verify_result_after = execute_command(verify_command, logger, type_json=True)
        
        if verify_result_after and isinstance(verify_result_after, dict) and "stdout" in verify_result_after:
            repo_data_after = verify_result_after["stdout"]
            if isinstance(repo_data_after, dict):
                version_after = repo_data_after.get("latest_version_href")
                logger.info(f"Repository version after sync: {version_after}")
                
                if not version_after or version_after.endswith("/versions/0/"):
                    logger.error(f"Sync completed but no content was downloaded for {repo_name}. "
                               f"The specified image tag likely does not exist in the upstream registry.")
                    return False
                
                if version_before and version_after and version_before == version_after:
                    # Check if tag actually exists using precise Pulp commands
                    try:
                        # Step 1: Get distribution to find repository href
                        dist_command = f"pulp container distribution show --name {repo_name}"
                        dist_result = execute_command(dist_command, logger, type_json=True)
                        
                        if not dist_result or not isinstance(dist_result, dict) or "stdout" not in dist_result:
                            logger.error(f"Failed to get distribution info for {repo_name}. Assuming tag doesn't exist.")
                            return False
                        
                        dist_data = dist_result["stdout"]
                        if not isinstance(dist_data, dict) or "repository" not in dist_data:
                            logger.error(f"Invalid distribution data for {repo_name}. Assuming tag doesn't exist.")
                            return False
                        
                        repo_href = dist_data["repository"]
                        logger.info(f"Found repository href: {repo_href}")
                        
                        # Step 2: Get repository version href
                        repo_command = f"pulp container repository show --href {repo_href}"
                        repo_result = execute_command(repo_command, logger, type_json=True)
                        
                        if not repo_result or not isinstance(repo_result, dict) or "stdout" not in repo_result:
                            logger.error(f"Failed to get repository info for {repo_href}. Assuming tag doesn't exist.")
                            return False
                        
                        repo_data = repo_result["stdout"]
                        if not isinstance(repo_data, dict) or "latest_version_href" not in repo_data:
                            logger.error(f"Invalid repository data for {repo_href}. Assuming tag doesn't exist.")
                            return False
                        
                        repo_ver_href = repo_data["latest_version_href"]
                        logger.info(f"Found repository version href: {repo_ver_href}")
                        
                        # Step 3: Check if tag exists in content
                        tags_command = f"pulp show --href '/pulp/api/v3/content/container/tags/?repository_version={repo_ver_href}'"
                        tags_result = execute_command(tags_command, logger, type_json=True)
                        
                        if not tags_result or not isinstance(tags_result, dict) or "stdout" not in tags_result:
                            logger.error(f"Failed to get content tags for {repo_ver_href}. Assuming tag doesn't exist.")
                            return False
                        
                        tags_data = tags_result["stdout"]
                        if not isinstance(tags_data, dict) or "results" not in tags_data:
                            logger.error(f"Invalid tags data for {repo_ver_href}. Assuming tag doesn't exist.")
                            return False
                        
                        tags = tags_data["results"]
                        tag_exists = False
                        
                        # Use the tag parameter if provided, otherwise fall back to checking package_content
                        tag_to_check = tag if tag else package_content
                        
                        for tag_item in tags:
                            if isinstance(tag_item, dict) and "name" in tag_item and tag_item["name"] == tag_to_check:
                                tag_exists = True
                                break
                        
                        if tag_exists:
                            logger.info(f"Tag '{tag_to_check}' already exists in Pulp repository {repo_name}. No sync needed - image is already available.")
                        else:
                            logger.error(f"Sync completed but repository version did not change for {repo_name}. "
                                       f"Version remained at {version_after}. "
                                       f"Tag '{tag_to_check}' does not exist in Pulp repository content. "
                                       f"This indicates the tag likely does not exist in the upstream registry.")
                            return False
                            
                    except Exception as e:
                        logger.error(f"Error checking repository tag existence: {e}. Assuming tag doesn't exist.")
                        return False
                
                logger.info(f"Sync validation successful: repository {repo_name} version changed from {version_before} to {version_after}")
        
        result = create_container_distribution(repo_name,package_content,logger)
        return result
    except Exception as e:
        logger.error(f"Failed to synchronize repository {repo_name} with remote {remote_name}. Error: {e}")
        return False
