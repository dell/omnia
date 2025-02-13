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

import re
from jinja2 import Template
from ansible.module_utils.standard_logger import setup_standard_logger
from ansible.module_utils.parse_and_download import execute_command
 
pulp_container_commands = {
    "create_container_repo": "pulp container repository create --name %s",
    "show_container_repo": "pulp container repository show --name %s",
    "create_container_remote": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --include-tags '[\"%s\"]'",
    "create_container_remote_for_digest": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s",
    "update_remote_for_digest": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s",
    "update_container_remote": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s --include-tags '[\"%s\"]'",
    "show_container_remote": "pulp container remote show --name %s",
    "show_container_distribution": "pulp container distribution show --name %s",
    "sync_container_repository": "pulp container repository sync --name %s --remote %s",
    "distribute_container_repository": "pulp container distribution create --name %s --repository %s --base-path %s",
    "update_container_distribution": "pulp container distribution update --name %s --repository %s --base-path %s"
}
 
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
            return True
        else:
            logger.info(f"Repository {repo_name} already exists.")
            return True
    except Exception as e:
        logger.error(f"Failed to create repository {repo_name}. Error: {e}")
        return False
 
 
def create_container_remote(remote_name, remote_url, package, policy_type, tag, logger):
    """
    Create or update a container remote.
 
    Args:
        remote_name (str): The name of the remote.
        remote_url (str): The URL of the remote.
        package (str): The package to create the remote for.
        policy_type (str): The policy type for the remote.
        tag (str): The tag for the remote.
 
    Returns:
        bool: True if the remote was created or updated successfully, False otherwise.
 
    Raises:
        Exception: If there was an error creating or updating the remote.
    """
    try:
        if not execute_command(pulp_container_commands["show_container_remote"] % (remote_name), logger):
            command = pulp_container_commands["create_container_remote"] % (remote_name, remote_url, package, policy_type, tag)
            result = execute_command(command,logger)
            logger.info(f"Remote created successfully: {remote_name}")
            return True
        else:
            logger.info(f"Remote {remote_name} already exists.")
            command = pulp_container_commands["update_container_remote"] % (remote_name, remote_url, package, policy_type, tag)
            result = execute_command(command,logger)
            logger.info(f"Remote updated successfully: {remote_name}")
            return True
    except Exception as e:
        logger.error(f"Failed to create remote {remote_name}. Error: {e}")
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
        if not execute_command(pulp_container_commands["show_container_remote"] % (remote_name), logger):
            command = pulp_container_commands["create_container_remote_for_digest"] % (remote_name, remote_url, package, policy_type)
            result = execute_command(command,logger)
            logger.info(f"Remote created successfully: {remote_name}")
            return True
        else:
            logger.info(f"Remote {remote_name} already exists.")
            command = pulp_container_commands["update_remote_for_digest"] % (remote_name, remote_url, package, policy_type)
            result = execute_command(command,logger)
            logger.info(f"Remote updated successfully: {remote_name}")
            return True
    except Exception as e:
        logger.error(f"Failed to create remote {remote_name}. Error: {e}")
        return False
 
def sync_container_repository(repo_name, remote_name, logger):
    """
    Synchronizes a container repository with a remote.
 
    Args:
        repo_name (str): The name of the repository.
        remote_name (str): The name of the remote.
 
    Returns:
        bool: True if the synchronization is successful, False otherwise.
    """
    try:
        command = pulp_container_commands["sync_container_repository"] % (repo_name, remote_name)
        result = execute_command(command,logger)
        return True
    except Exception as e:
        logger.error(f"Failed to synchronize repository {repo_name} with remote {remote_name}. Error: {e}")
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
         r"^(ghcr\.io)(/.+)": "https://ghcr.io",
         r"^(docker\.io)(/.+)": "https://registry-1.docker.io",
         r"^(quay\.io)(/.+)": "https://quay.io",
         r"^(registry\.k8s\.io)(/.+)": "https://registry.k8s.io",
         r"^(nvcr\.io)(/.+)": "https://nvcr.io",
         r"^(public\.ecr\.aws)(/.+)": "https://public.ecr.aws",
         r"^(gcr\.io)(/.+)": "https://gcr.io"
    }
 
    for pattern, repo_url in patterns.items():
        match = re.match(pattern, package)
        if match:
            base_url = repo_url
            package_content = match.group(2).lstrip("/")  # Remove leading slash
            return base_url, package_content
 
    raise ValueError(f"Unsupported package prefix for package: {package}")
 
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

 
def process_image(package,repo_store_path, status_file_path, cluster_os_type, cluster_os_version, version_variables, logger):
    """
    Process an image.
 
    Args:
        package (dict): The package to process.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        cluster_os_type (str): The type of the cluster operating system.
        cluster_os_version (str): The version of the cluster operating system.
        logger (Logger): The logger.
 
    Returns:
        str: "Success" if the image was processed successfully, "Failed" otherwise.
    """
    logger.info("#" * 30 + f" {process_image.__name__} start " + "#" * 30)
    try:
        policy_type = "immediate"
        base_url, package_content = get_repo_url_and_content(package['package'])
        repo_name_prefix = "container_repo_"
        repository_name = f"{repo_name_prefix}{package['package'].replace('/', '_').replace(':', '_')}"
        remote_name = f"remote_{package['package'].replace('/', '_')}"
        if not create_container_repository(repository_name, logger):
            raise Exception(f"Failed to create repository: {repository_name}")
 
        if "digest" in package:
            if not create_container_remote_digest(remote_name, base_url, package_content, policy_type,logger):
                raise Exception(f"Failed to create remote digest: {remote_name}")
        elif "tag" in package:
            tag_template = Template(package.get('tag', None))  # Use Jinja2 Template for URL
            tag_val = tag_template.render(**version_variables)

            if not create_container_remote(remote_name, base_url, package_content, policy_type, tag_val, logger):
                raise Exception(f"Failed to create remote: {remote_name}")
 
        if not sync_container_repository(repository_name, remote_name, logger):
            raise Exception(f"Failed to sync repository: {repository_name}")
 
        if not create_container_distribution(repository_name, package_content, logger):
            raise Exception(f"Failed to create distribution: {repository_name}")
 
        return "Success"
    except Exception as e:
        logger.error(f"Failed to process image: {package['package']}. Error: {e}")
        return "Failed"
 
