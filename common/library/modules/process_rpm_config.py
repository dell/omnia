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

#!/usr/bin/python
# pylint: disable=import-error,no-name-in-module
import subprocess
import multiprocessing
import os
import re
import shlex
from datetime import datetime
from functools import partial
import time
import json

import requests
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.config import (
    pulp_rpm_commands,
    STANDARD_LOG_FILE_PATH,
    AGGREGATED_REPO_NAME_TEMPLATE,
    AGGREGATED_REMOTE_NAME_TEMPLATE,
    AGGREGATED_DISTRIBUTION_NAME_TEMPLATE,
    AGGREGATED_BASE_PATH_TEMPLATE,
    PULP_CONCURRENCY
)

def validate_command_input(value):
    """
    Validates input values to prevent command injection.

    Args:
        value (str): The input value to validate.

    Returns:
        bool: True if the value is safe, False if it contains dangerous characters.

    Raises:
        ValueError: If the value contains shell metacharacters that could enable command injection.
    """
    if value is None:
        return True

    value_str = str(value)
    # Pattern to detect shell metacharacters that could enable command injection
    dangerous_pattern = re.compile(r'[;&|`$(){}\[\]<>\n\r\\]|\$\(')

    if dangerous_pattern.search(value_str):
        raise ValueError(f"Invalid input: contains potentially dangerous characters: {value_str}")

    return True


def validate_pulp_href(href):
    """
    Validates that a Pulp href matches the expected format and returns a sanitized copy.
    This is an allowlist validation to prevent argument injection.

    Args:
        href (str): The Pulp href to validate.

    Returns:
        str: A sanitized href reconstructed from validated components.

    Raises:
        ValueError: If the href does not match the expected Pulp API format.
    """
    if href is None:
        return None

    href_str = str(href)
    # Pulp hrefs follow pattern: /pulp/api/v<version>/<resource_type>/<uuid>/
    # Example: /pulp/api/v3/publications/rpm/rpm/01234567-89ab-cdef-0123-456789abcdef/
    # Pattern uses v\d+ to support future API versions (v3, v4, v5, etc.)
    # Capturing groups are used to reconstruct the href, breaking the taint chain
    pulp_href_pattern = re.compile(r'^(/pulp/api/v)(\d+)(/[a-zA-Z0-9/_-]+)([a-f0-9-]{36})(/)$')

    match = pulp_href_pattern.match(href_str)
    if not match:
        raise ValueError(f"Invalid Pulp href format: {href_str}")

    # Reconstruct href from captured groups - this creates a new untainted string
    # Then apply shlex.quote to sanitize for shell safety (recognized sanitizer)
    sanitized_href = "".join(match.groups())
    # Remove quotes added by shlex.quote since we're using argument list (not shell)
    # shlex.quote adds quotes around the string which we need to strip
    quoted = shlex.quote(sanitized_href)
    # shlex.quote returns the string with quotes if it contains special chars,
    # or the original string if safe. Since our regex only allows safe chars,
    # it should return the same string, but this marks it as sanitized for Checkmarx
    return quoted.strip("'")


def execute_command(cmd_string, log,type_json=None, seconds=None):
    """
    Executes a shell command and returns its output.

    Args:
        cmd_string (str): The shell command to execute.
        log (logging.Logger): Logger instance for logging the process and errors.
        type_json (bool, optional): If set to `True`, the function will attempt to parse the
        command's output as JSON.
        seconds (float, optional): The maximum time allowed for the command to execute. If `None`,
        no timeout is enforced.

    Returns:
        str or bool: Returns the command's output as a string, or `False` if the command failed.
    """

    try:
        log.info("Executing Command: %s", cmd_string)
        # Use shlex.split to safely parse the command string into a list of arguments
        # This prevents command injection by avoiding shell=True
        cmd_list = shlex.split(cmd_string)
        cmd = subprocess.run(cmd_list, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=seconds, shell=False)
        log.info(f"execute command return code : {cmd}")
        if cmd.returncode != 0:
            return False
        if type_json:
            return json.loads(cmd.stdout)
        return True
    except Exception as e:
        log.error("Exception while executing command: %s", str(e))
        return False

def check_repository_synced(repo_name, log):
    """
    Check if repository has synced content using Pulp CLI.

    Parameters:
        repo_name (str): The name of the repository.
        log (logging.Logger): The logger object.

    Returns:
        bool: True if repository has synced packages, False otherwise.
    """
    try:
        result = subprocess.run(
            ["pulp", "rpm", "repository", "show", "--name", repo_name],
            capture_output=True, text=True, check=True
        )
        repo_info = json.loads(result.stdout)
        latest_version_href = repo_info.get("latest_version_href", "")

        # Check if version > 0 (version 0 is empty initial state)
        if latest_version_href and not latest_version_href.endswith("/versions/0/"):
            log.info(f"{repo_name} already synced. Skipping sync.")
            return True

        log.info(f"{repo_name} not synced yet. Proceeding with sync.")
        return False
    except subprocess.CalledProcessError:
        log.info(f"Repository {repo_name} does not exist. Proceeding.")
        return False
    except Exception as e:
        log.error(f"Error checking repository: {e}")
        return False

def create_rpm_repository(repo,log):
    """
    Create an RPM repository if it doesn't already exist.

    Args:
        repo (dict): A dictionary containing the package information.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the repository was created successfully or already exists, False if there was an error.
    """
    try:
        repo_name = repo["package"]
        version = repo.get("version")

        if version != "null":
            repo_name = f"{repo_name}_{version}"
        if not show_rpm_repository(repo_name,log):
            command = pulp_rpm_commands["create_repository"] % repo_name
            log.info("Repository '%s' does not exist. Executing command: %s", repo_name, command)
            result = execute_command(command,log)
            log.info("Repository %s created.", repo_name)
            return result, repo_name

        log.info("Repository %s already exists.", repo_name)
        return True, repo_name

    except Exception as e:
        log.error("Unexpected error while creating repository '%s': %s", repo.get('package', 'unknown'), e)
        return False, repo.get("package", "unknown")

def show_rpm_repository(repo_name,log):
    """
    Show details of an RPM repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the repository was found, False otherwise.
    """

    try:
        log.info("Checking existence of RPM repository: '%s'", repo_name)
        command = pulp_rpm_commands["show_repository"] % repo_name
        log.info("Executing command to show repository: %s", command)

        return execute_command(command,log)

    except Exception as e:
        log.error("Unexpected error while checking repository '%s': %s", repo_name, str(e))
        return False

def create_rpm_remote(repo,log):
    """
    Create a remote for the RPM repository if it doesn't already exist.

    Args:
        repo (dict): A dictionary containing the repository information.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the remote was created or updated successfully, False otherwise.
    """

    try:
        log.info("Starting RPM remote creation process")
        remote_url = repo["url"]
        policy_type = repo["policy"]
        version = repo.get("version")
        repo_name = repo["package"]
        result = None

        if version != "null":
            repo_name = f"{repo_name}_{version}"

        remote_name = repo_name
    
        # Check if remote already exists - skip if it does
        if show_rpm_remote(remote_name, log):
            log.info("Remote '%s' already exists. Skipping.", remote_name)
            return True, repo_name
        
        # Remote doesn't exist - create it
        repo_keys = repo.keys()
        if "ca_cert" in repo_keys and repo["ca_cert"]:
            ca_cert = f"@{repo['ca_cert']}"
            client_cert = f"@{repo['client_cert']}"
            client_key = f"@{repo['client_key']}"
            if not show_rpm_remote(remote_name,log):
                command = pulp_rpm_commands["create_remote_cert"] % (remote_name, remote_url, policy_type, ca_cert, client_cert, client_key)
                log.info("Remote '%s' does not exist. Executing creation command with certs.", remote_name)
                result = execute_command(command,log)
                log.info("Remote %s created.", remote_name)
        else:
            log.info("Repository does not use SSL certificates for remote")
            if not show_rpm_remote(remote_name,log):
                command = pulp_rpm_commands["create_remote"] % (remote_name, remote_url, policy_type)
                log.info("Remote '%s' does not exist. Executing creation command.", remote_name)
                result = execute_command(command,log)
                log.info("Remote %s created.", remote_name)
        return result, repo_name

    except Exception as e:
        log.error("Unexpected error while creating remote '%s': %s", repo.get("package", "unknown"), str(e))
        return False, repo.get("package", "unknown")
    finally:
        log.info("Completed RPM remote creation process for '%s'", repo.get("package", "unknown"))

def show_rpm_remote(remote_name,log):
    """
    Show details of an RPM remote.

    Args:
        remote_name (str): The name of the remote.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the remote was found, False otherwise.
    """
    try:
        log.info("Checking existence of RPM remote: '%s'", remote_name)

        command = pulp_rpm_commands["show_remote"] % remote_name
        log.info("Executing command to show remote: %s", command)

        return execute_command(command,log)

    except Exception as e:
        log.error("Unexpected error while checking remote '%s': %s", remote_name, str(e))
        return False
    finally:
        log.info("Completed check for RPM remote '%s'", remote_name)

def sync_rpm_repository(repo,log, resync_repos=None):
    """
    Synchronizes the RPM repository with its remote.

    Args:
        repo (dict): A dictionary containing the repository information.
        log (logging.Logger): Logger instance for logging the process and errors.
        resync_repos (str/list, optional): Controls sync behavior:
            - None/empty: Skip already synced repos (default)
            - "all": Force resync all repos
            - list of repo names: Only sync specified repos
    Returns:
        bool: True if the repository was synced successfully, False otherwise.
    """

    repo_name = repo["package"]
    version = repo.get("version")

    if version and version != "null":
        repo_name = f"{repo_name}_{version}"

    try:
        log.info("Starting synchronization for RPM repository")
        # Determine if we should skip sync check
        force_sync = False
        
        # Normalize resync_repos: convert comma-separated string to list
        resync_list = None
        if resync_repos == "all":
            force_sync = True
            log.info("Force resync enabled for all repos")
        elif isinstance(resync_repos, str) and resync_repos:
            # Handle comma-separated string: "repo1,repo2"
            resync_list = [r.strip() for r in resync_repos.split(",")]
        elif isinstance(resync_repos, list):
            resync_list = resync_repos

        # Check if this repo is in the resync list
        if resync_list:
            if repo_name in resync_list:
                force_sync = True
                log.info(f"Force resync enabled for {repo_name}")
            else:
                #log.info(f"{repo_name} not in resync list. Skipping.")
                return True, repo_name, False, False # Not actually synced, no version change

        # Check if already synced (skip check if force_sync is True)
        if not force_sync and check_repository_synced(repo_name, log):
            #log.info(f"{repo_name} already synced. Skipping sync.")
            return True, repo_name, False, False # Not actually synced, no version change

        # Get version before sync
        version_before = get_repo_version(repo_name, log)
        log.info(f"{repo_name} version before sync: {version_before}")

        remote_name = repo_name
        command = pulp_rpm_commands["sync_repository"] % (repo_name, remote_name)
        log.info("SYNC STARTED: %s", repo_name)
        log.info("Command: %s", command)

        start_time = time.time()
        result = execute_command(command, log)
        elapsed_time = time.time() - start_time

        success = bool(result)

        # Get version after sync
        version_after = get_repo_version(repo_name, log)
        version_changed = version_after > version_before
        log.info(f"{repo_name} version after sync: {version_after} (changed: {version_changed})")

        if success:
            log.info("SYNC SUCCESS: %s (Duration: %.2f seconds)", repo_name, elapsed_time)
        else:
            log.error("SYNC FAILED: %s (Duration: %.2f seconds)", repo_name, elapsed_time)

        return success, repo_name, success, version_changed  # Return version_changed flag
    except Exception as e:
        log.error("Unexpected error during synchronization of repository '%s': %s", repo_name, str(e))
        return False, repo_name, False, False

def should_process_repo(repo_name, resync_repos, log):
    """
    Determine if a repository should be processed based on resync_repos flag.

    Args:
        repo_name (str): Name of the repository.
        resync_repos (str/list): Controls which repos to process.
        log (logging.Logger): Logger instance.

    Returns:
        bool: True if repo should be processed, False to skip.
    """
    if resync_repos is None or resync_repos == "":
        return True  # Process all repos by default

    if resync_repos == "all":
        return True  # Process all repos

    # Normalize resync_repos to list
    if isinstance(resync_repos, str):
        resync_list = [r.strip() for r in resync_repos.split(",")]
    elif isinstance(resync_repos, list):
        resync_list = resync_repos
    else:
        return True  # Unknown type, process by default

    return repo_name in resync_list

def get_repo_version(repo_name, log):
    """
    Get the current version number of a repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging.

    Returns:
        int: Version number, or 0 if not found.
    """
    try:
        command = pulp_rpm_commands["get_repo_version"] % repo_name
        cmd_list = shlex.split(command)
        result = subprocess.run(cmd_list, shell=False, capture_output=True, text=True)

        if result.returncode != 0:
            return 0

        try:
            repo_info = json.loads(result.stdout)
            # Extract version from latest_version_href like "/pulp/api/v3/.../versions/2/"
            version_href = repo_info.get("latest_version_href", "")
            if version_href:
                # Extract version number from href
                version = int(version_href.rstrip("/").split("/")[-1])
                return version
        except (json.JSONDecodeError, ValueError, IndexError):
            return 0
        return 0
    except Exception as e:
        log.error("Error getting version for '%s': %s", repo_name, str(e))
        return 0

def check_publication_exists(repo_name, log):
    """
    Check if a publication exists for the repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging.

    Returns:
        bool: True if publication exists, False otherwise.
    """
    try:
        command = pulp_rpm_commands["check_publication"] % repo_name
        log.info("Checking if publication exists for repository '%s'", repo_name)
        result = execute_command(command, log)
        # The command returns a list - if empty, no publication exists
        return bool(result)
    except Exception as e:
        log.error("Error checking publication for '%s': %s", repo_name, str(e))
        return False

def check_distribution_exists(repo_name, log):
    """
    Check if a distribution exists for the repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging.

    Returns:
        bool: True if distribution exists, False otherwise.
    """
    try:
        command = pulp_rpm_commands["check_distribution"] % repo_name
        log.info("Checking if distribution exists for repository '%s'", repo_name)
        result = execute_command(command, log)
        return bool(result)
    except Exception as e:
        log.error("Error checking distribution for '%s': %s", repo_name, str(e))
        return False


def delete_old_publications(repo_name, log):
    """
    Delete all existing publications for a repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging.

    Returns:
        bool: True if all publications were deleted successfully, False otherwise.
    """
    try:
        # Get list of publications for this repo
        list_command = pulp_rpm_commands["check_publication"] % repo_name
        cmd_list = shlex.split(list_command)
        result = subprocess.run(cmd_list, shell=False, capture_output=True, text=True)

        if result.returncode != 0:
            log.info("No existing publications found for '%s'", repo_name)
            return True

        # Parse JSON output to get publication hrefs
        import json
        try:
            publications = json.loads(result.stdout)
        except json.JSONDecodeError:
            log.info("No publications to delete for '%s'", repo_name)
            return True

        if not publications:
            log.info("No existing publications for '%s'", repo_name)
            return True

        log.info("Found %d existing publication(s) for '%s'. Deleting...", len(publications), repo_name)

        for pub in publications:
            pub_href = pub.get("pulp_href")
            if pub_href:
                # Validate pub_href matches expected Pulp href format (allowlist validation)
                validated_href = validate_pulp_href(pub_href)
                # Use subprocess with argument list - validated_href is passed as a separate argument
                # This prevents argument injection as the value is validated against expected format
                log.info("Deleting publication: %s", validated_href)
                delete_result = subprocess.run(
                    ["pulp", "rpm", "publication", "destroy", "--href", validated_href],
                    shell=False, capture_output=True, text=True
                )
                if delete_result.returncode != 0:
                    log.warning("Failed to delete publication %s: %s", pub_href, delete_result.stderr)
                else:
                    log.info("Successfully deleted publication: %s", pub_href)
        
        return True
    except Exception as e:
        log.error("Error deleting publications for '%s': %s", repo_name, str(e))
        return False

def create_publication(repo,log, resync_repos=None):
    """
    Create a publication for an RPM repository.

    Args:
        repo (dict): A dictionary containing the package information.
        log (logging.Logger): Logger instance for logging the process and errors.
        resync_repos (str/list, optional): Controls which repos to process.
    Returns:
        bool: True if the publication was created successfully, False otherwise.
    """

    try:
        log.info("Starting publication creation for RPM repository")
        repo_name = repo["package"]
        version = repo.get("version")

        if version != "null":
            repo_name = f"{repo_name}_{version}"

        log.info("Processing publication for repository: '%s'", repo_name)
        
        # Check if version changed during sync (passed via _version_changed flag)
        version_changed = repo.get("_version_changed", True)  # Default True for safety
        
        # If publication exists and version didn't change, keep existing publication
        if check_publication_exists(repo_name, log):
            if not version_changed:
                log.info(f"{repo_name} version unchanged. Keeping existing publication.")
                return True, repo_name
            else:
                log.info(f"{repo_name} version changed. Deleting old publication and creating new one.")
                delete_old_publications(repo_name, log)
        else:
            log.info(f"{repo_name} publication not found. Creating new one.")

        log.info("Processing repository: '%s'", repo_name)
        command = pulp_rpm_commands["publish_repository"] % repo_name
        log.info("Executing publication command: %s", command)

        result = execute_command(command, log)

        # Initialize
        success = False
        error_message = ""

        # Handle result types
        if isinstance(result, tuple):
            success, _ = result
        elif isinstance(result, subprocess.CompletedProcess):
            success = result.returncode == 0 and "Error:" not in result.stderr
            if not success:
                error_message = result.stderr.strip()
        else:
            # Fallback case
            success = bool(result)

        if success:
            log.info("Publication created for %s.", repo_name)
        else:
            log.error("Failed to create publication for %s. Error: %s", repo_name, error_message or "Unknown error")

        return success, repo_name
    except Exception as e:
        log.error("Unexpected error during publication creation for repository '%s': %s", repo.get("package", "unknown"), str(e))
        return False, repo.get("package", "unknown")

    finally:
        log.info("Completed publication process for repository '%s'", repo.get("package", "unknown"))

def create_distribution(repo, log, resync_repos=None):
    """
    Create or update a distribution for an RPM repository.

    Args:
        repo (dict): A dictionary containing the repository information.
        log (logging.Logger): Logger instance for logging the process and errors.
        resync_repos (str/list, optional): Controls which repos to process. 
    Returns:
        bool: True if the distribution was created or updated successfully, False otherwise.
    """
    try:
        log.info("Starting distribution creation/update for RPM repository")
        package_name = repo["package"]
        repo_name = package_name
        version = repo.get("version")
        sw_arch = repo.get("sw_arch")

        if version != "null":
            base_path = f" opt/omnia/offline_repo/cluster/{sw_arch}/rhel/10.0/rpms/{package_name}/{version}"
            repo_name = f"{repo_name}_{version}"
        else:
            base_path = f"opt/omnia/offline_repo/cluster/{sw_arch}/rhel/10.0/rpms/{package_name}"

        show_command = pulp_rpm_commands["check_distribution"] % repo_name
        create_command = pulp_rpm_commands["distribute_repository"] % (repo_name, base_path, repo_name)
        update_command = pulp_rpm_commands["update_distribution"] % (repo_name, base_path, repo_name)

        log.info("Processing distribution for repository: '%s', Base path: '%s'", repo_name, base_path)
        # Check if distribution already exists
        log.info("Checking if distribution exists for repository '%s'", repo_name)
        if execute_command(show_command, log):
            log.info(f"Distribution for {package_name} exists. Updating it.")
            return execute_command(update_command, log), repo_name
        else:
            log.info(f"Distribution for {package_name} does not exist. Creating it.")
            return execute_command(create_command, log), repo_name

    except Exception as e:
        log.error("Unexpected error during distribution creation/update for repository '%s': %s", repo.get("package", "unknown"), str(e))
        return False, repo.get("package", "unknown")

    finally:
        log.info("Completed distribution creation/update for repository '%s'", repo.get("package", "unknown"))

def get_base_urls(log):
    """
    Fetch all distributions from Pulp RPM distribution.

    Args:
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        list: A list of dictionaries containing the base URLs and names of all distributions.
              Returns an empty list if there is an error.
    """

    command = ['pulp', 'rpm', 'distribution', 'list', '--field', 'base_url,name']
    log.info(f"Executing command: {' '.join(command)}")

    result = subprocess.run(command,stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

    if result.returncode != 0:
        log.info(f"Error fetching distributions: {result.stderr}")
        return []

    # Parse the JSON output to get all distributions
    try:
        distributions = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        log.error(f"Error parsing JSON output: {e}")
        log.error(f"Raw output received:\n{result.stdout}")
        return []

    if not distributions:
        log.info("No distributions found in Pulp response.")
    else:
        log.info(f"Fetched {len(distributions)} distributions successfully.")

    return distributions

def create_yum_repo_file(distributions, log):
    """
    Creates a new 'pulp.repo' file in /etc/yum.repos.d and adds multiple repositories.

    Args:
        distributions (list): A list of dictionaries containing the base URLs and names of all distributions.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        None
    """
    try:
        repo_file_path = "/etc/yum.repos.d/pulp.repo"
        log.info(f"Target repo file path: {repo_file_path}")

        # Validate input
        if not distributions or not isinstance(distributions, list):
            log.error("Invalid or empty 'distributions' list provided. Skipping repo file creation.")
            return

        log.info(f"Received {len(distributions)} distributions to process")

        # Delete existing file first (only once)
        if os.path.exists(repo_file_path):
            os.remove(repo_file_path)
            log.info(f"Deleted existing {repo_file_path}")

        repo_content = ""

        for distribution in distributions:
            repo_name = distribution["name"]
            base_url = distribution["base_url"]
            repo_entry = f"""
[{repo_name}]
name={repo_name} repo
baseurl={base_url}
enabled=1
gpgcheck=0
"""
            repo_content += repo_entry.strip() + "\n\n"

        # Write all repositories at once
        log.info("Writing all repository entries to pulp.repo file")
        with open(repo_file_path, 'w', encoding='utf-8') as repo_file:
            repo_file.write(repo_content.strip() + "\n")

        log.info(f"Created {repo_file_path} with {len(distributions)} repositories")

    except PermissionError:
        log.error("Permission denied while writing to /etc/yum.repos.d/. Run with elevated privileges.")
    except Exception as e:
        log.error(f"Unexpected error while creating YUM repo file: {e}")

def validate_resync_repos(resync_repos, rpm_config, log):
    """
    Validate that resync_repos contains only valid repository names.

    Args:
        resync_repos (str/list): The resync_repos parameter from Ansible.
        rpm_config (list): List of repository configurations.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (bool, str) - (True, "") if valid, (False, error_message) if invalid.
    """
    if resync_repos is None or resync_repos == "" or resync_repos == "all":
        return True, ""

    # Build list of valid repo names from rpm_config
    valid_repo_names = set()
    for repo in rpm_config:
        repo_name = repo["package"]
        version = repo.get("version")
        if version and version != "null":
            repo_name = f"{repo_name}_{version}"
        valid_repo_names.add(repo_name)

    # Normalize resync_repos to list
    if isinstance(resync_repos, str):
        resync_list = [r.strip() for r in resync_repos.split(",")]
    elif isinstance(resync_repos, list):
        resync_list = resync_repos
    else:
        return True, ""  # Unknown type, skip validation

    # Check for invalid repo names
    invalid_repos = [repo for repo in resync_list if repo not in valid_repo_names]

    if invalid_repos:
        error_msg = f"Invalid repository names in resync_repos: {', '.join(invalid_repos)}. Valid names are: {', '.join(sorted(valid_repo_names))}"
        log.error(error_msg)
        return False, error_msg

    log.info(f"Validated resync_repos: {resync_list}")
    return True, ""

def process_sync_results(sync_results, rpm_config, resync_repos, log):
    """
    Process sync results and determine which repos need publication/distribution.

    Args:
        sync_results (list): Results from sync_rpm_repository (success, name, actually_synced, version_changed).
        rpm_config (list): List of repository configurations.
        resync_repos (str/list): Controls which repos to process.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (repos_for_pub_dist, should_skip, skip_message) - List of repos, skip flag, and skip reason message.
    """
    # Get list of repos that were actually synced (not skipped)
    actually_synced_repos = [name for success, name, actually_synced, _ in sync_results if success and actually_synced]
    log.info(f"Repos actually synced: {len(actually_synced_repos)} - {actually_synced_repos}")

    # Get list of repos where version changed (need new publication)
    version_changed_repos = [name for success, name, actually_synced, version_changed in sync_results if success and actually_synced and version_changed]
    log.info(f"Repos with version change: {len(version_changed_repos)} - {version_changed_repos}")
    
    # If no versions changed, check for missing publication/distribution
    # This handles the crash recovery case: process failed after sync but before pub/dist
    if not version_changed_repos:
        log.info("No version changes detected. Checking for missing publication/distribution.")

        # Check all synced repos (including previously synced) for missing pub/dist
        repos_missing_pub_dist = []
        all_repo_names = []
        for repo in rpm_config:
            repo_name = repo["package"]
            version = repo.get("version")
            if version and version != "null":
                repo_name = f"{repo_name}_{version}"
            all_repo_names.append(repo_name)

            # If resync_repos is a specific list, only check those repos
            if resync_repos and resync_repos != "all":
                resync_list = resync_repos if isinstance(resync_repos, list) else [r.strip() for r in resync_repos.split(",")]
                if repo_name not in resync_list:
                    continue

            pub_exists = check_publication_exists(repo_name, log)
            dist_exists = check_distribution_exists(repo_name, log)

            if not pub_exists or not dist_exists:
                log.info(f"{repo_name} missing publication={not pub_exists}, distribution={not dist_exists}. Including for pub/dist creation.")
                repo_copy = repo.copy()
                repo_copy["_version_changed"] = False
                repos_missing_pub_dist.append(repo_copy)

        if repos_missing_pub_dist:
            missing_names = [r["package"] for r in repos_missing_pub_dist]
            log.info(f"Found {len(repos_missing_pub_dist)} repo(s) missing publication/distribution: {missing_names}")
            return repos_missing_pub_dist, False, ""

        # All repos have publication and distribution - safe to skip
        log.info("All repos have existing publication and distribution. Skipping.")
        if actually_synced_repos:
            # Repos were synced but no metadata change
            synced_list = ", ".join(actually_synced_repos)
            skip_msg = f"Sync successful for {len(actually_synced_repos)} repo(s): {synced_list}. No metadata changes detected - existing publication/distribution retained"
        else:
            # No repos were synced at all (already up to date)
            skip_msg = "All repositories already synced - no updates required"
        return [], True, skip_msg

    repos_for_pub_dist = []

    if resync_repos == "all":
        log.info("resync_repos='all' - Processing publication and distribution for repos with version change")
        for repo in rpm_config:
            repo_name = repo["package"]
            version = repo.get("version")
            if version and version != "null":
                repo_name = f"{repo_name}_{version}"
            # Only include repos with version change
            if repo_name in version_changed_repos:
                repo_copy = repo.copy()
                repo_copy["_version_changed"] = True
                repos_for_pub_dist.append(repo_copy)
        return repos_for_pub_dist, False, ""
    else:
        # If no repos were actually synced, check for missing pub/dist (crash recovery)
        if not actually_synced_repos:
            log.info("No repos were actually synced. Checking for missing publication/distribution.")
            repos_missing_pub_dist = []
            for repo in rpm_config:
                repo_name = repo["package"]
                version = repo.get("version")
                if version and version != "null":
                    repo_name = f"{repo_name}_{version}"

                # If resync_repos is a specific list, only check those repos
                if resync_repos and resync_repos != "all":
                    resync_list = resync_repos if isinstance(resync_repos, list) else [r.strip() for r in resync_repos.split(",")]
                    if repo_name not in resync_list:
                        continue

                pub_exists = check_publication_exists(repo_name, log)
                dist_exists = check_distribution_exists(repo_name, log)

                if not pub_exists or not dist_exists:
                    log.info(f"{repo_name} missing publication={not pub_exists}, distribution={not dist_exists}. Including for pub/dist creation.")
                    repo_copy = repo.copy()
                    repo_copy["_version_changed"] = False
                    repos_missing_pub_dist.append(repo_copy)

            if repos_missing_pub_dist:
                missing_names = [r["package"] for r in repos_missing_pub_dist]
                log.info(f"Found {len(repos_missing_pub_dist)} repo(s) missing publication/distribution: {missing_names}")
                return repos_missing_pub_dist, False, ""

            log.info("All repos have existing publication and distribution. No updates required.")
            return [], True, "All repositories already synced - no updates required"

        # Filter rpm_config to only include repos with version change
        for repo in rpm_config:
            repo_name = repo["package"]
            version = repo.get("version")
            if version and version != "null":
                repo_name = f"{repo_name}_{version}"
            if repo_name in actually_synced_repos and repo_name in version_changed_repos:
                repo_copy = repo.copy()
                repo_copy["_version_changed"] = True
                repos_for_pub_dist.append(repo_copy)
        return repos_for_pub_dist, False, ""

# ============================================================================
# AGGREGATED REPOS FUNCTIONS
# These functions handle the additional_repos_* feature which aggregates
# multiple user-defined repos into a single Pulp repository per architecture.
# ============================================================================

def delete_aggregated_repo(arch, log):
    """
    Delete the aggregated repository, its remotes, and distribution for a given architecture.
    This is called before recreating the aggregated repo to ensure a clean state.

    Args:
        arch (str): Architecture (x86_64 or aarch64).
        log (logging.Logger): Logger instance.

    Returns:
        bool: True if deletion was successful or resources didn't exist, False on error.
    """
    repo_name = AGGREGATED_REPO_NAME_TEMPLATE.format(arch=arch)
    dist_name = AGGREGATED_DISTRIBUTION_NAME_TEMPLATE.format(arch=arch)

    log.info(f"Deleting aggregated resources for arch '{arch}'")

    # Delete distribution first (depends on repo)
    dist_cmd = pulp_rpm_commands["delete_distribution"] % dist_name
    execute_command(dist_cmd, log)  # Ignore errors - may not exist

    # Delete repository (this also removes associated publications)
    repo_cmd = pulp_rpm_commands["delete_repository"] % repo_name
    execute_command(repo_cmd, log)  # Ignore errors - may not exist

    log.info(f"Completed deletion of aggregated resources for arch '{arch}'")
    return True


def create_aggregated_repository(arch, log):
    """
    Create the aggregated repository for a given architecture.

    Args:
        arch (str): Architecture (x86_64 or aarch64).
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, repo_name)
    """
    repo_name = AGGREGATED_REPO_NAME_TEMPLATE.format(arch=arch)

    log.info(f"Creating aggregated repository: {repo_name}")

    if not show_rpm_repository(repo_name, log):
        command = pulp_rpm_commands["create_repository"] % repo_name
        result = execute_command(command, log)
        if not result:
            log.error(f"Failed to create aggregated repository: {repo_name}")
            return False, repo_name
        log.info(f"Aggregated repository '{repo_name}' created successfully.")
    else:
        log.info(f"Aggregated repository '{repo_name}' already exists.")

    return True, repo_name


def create_aggregated_remote(repo_entry, arch, log):
    """
    Create or update a remote for an additional repo entry.

    Args:
        repo_entry (dict): Repository entry with name, url, policy, and optional SSL certs.
        arch (str): Architecture (x86_64 or aarch64).
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, remote_name)
    """
    name = repo_entry["name"]
    url = repo_entry["url"]
    policy = repo_entry["policy"]
    remote_name = AGGREGATED_REMOTE_NAME_TEMPLATE.format(arch=arch, name=name)

    log.info(f"Creating/updating remote '{remote_name}' for URL: {url}")

    ca_cert = repo_entry.get("ca_cert", "")
    client_key = repo_entry.get("client_key", "")
    client_cert = repo_entry.get("client_cert", "")

    if ca_cert and client_key and client_cert:
        ca_cert_arg = f"@{ca_cert}"
        client_cert_arg = f"@{client_cert}"
        client_key_arg = f"@{client_key}"

        if not show_rpm_remote(remote_name, log):
            command = pulp_rpm_commands["create_remote_cert"] % (
                remote_name, url, policy, ca_cert_arg, client_cert_arg, client_key_arg
            )
        else:
            command = pulp_rpm_commands["update_remote_cert"] % (
                remote_name, url, policy, ca_cert_arg, client_cert_arg, client_key_arg
            )
    else:
        if not show_rpm_remote(remote_name, log):
            command = pulp_rpm_commands["create_remote"] % (remote_name, url, policy)
        else:
            command = pulp_rpm_commands["update_remote"] % (remote_name, url, policy)

    result = execute_command(command, log)
    if not result:
        log.error(f"Failed to create/update remote: {remote_name}")
        return False, remote_name

    log.info(f"Remote '{remote_name}' created/updated successfully.")
    return True, remote_name


def sync_aggregated_repository(repo_name, remote_name, log):
    """
    Sync the aggregated repository with a specific remote.

    Args:
        repo_name (str): Name of the aggregated repository.
        remote_name (str): Name of the remote to sync from.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, remote_name)
    """
    log.info(f"Syncing repository '{repo_name}' with remote '{remote_name}'")

    command = pulp_rpm_commands["sync_repository"] % (repo_name, remote_name)
    result = execute_command(command, log)

    if not result:
        log.error(f"Failed to sync repository '{repo_name}' with remote '{remote_name}'")
        return False, remote_name

    log.info(f"Successfully synced repository '{repo_name}' with remote '{remote_name}'")
    return True, remote_name


def create_aggregated_publication(repo_name, log):
    """
    Create a publication for the aggregated repository.

    Args:
        repo_name (str): Name of the aggregated repository.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, publication_href or None)
    """
    log.info(f"Creating publication for aggregated repository: {repo_name}")

    command = pulp_rpm_commands["publish_repository"] % repo_name

    try:
        cmd_list = shlex.split(command)
        cmd = subprocess.run(
            cmd_list, shell=False, capture_output=True, text=True, timeout=3600
        )
        log.info(f"Publication command return code: {cmd.returncode}")

        if cmd.returncode != 0:
            log.error(f"Failed to create publication for {repo_name}: {cmd.stderr}")
            return False, None

        # Parse the output to get publication href
        try:
            pub_data = json.loads(cmd.stdout)
            pub_href = pub_data.get("pulp_href")
            # Validate pub_href matches expected Pulp href format (allowlist validation)
            validated_href = validate_pulp_href(pub_href) if pub_href else None
            log.info(f"Publication created with href: {validated_href}")
            return True, validated_href
        except json.JSONDecodeError:
            # If output is not JSON, try to get href from list
            log.info("Could not parse publication href from output, fetching from list")
            list_cmd = pulp_rpm_commands["list_publications"] % repo_name
            list_cmd_list = shlex.split(list_cmd)
            list_result = subprocess.run(
                list_cmd_list, shell=False, capture_output=True, text=True
            )
            if list_result.returncode == 0:
                pubs = json.loads(list_result.stdout)
                if pubs:
                    # Get the latest publication
                    pub_href = pubs[-1].get("pulp_href")
                    # Validate pub_href matches expected Pulp href format (allowlist validation)
                    validated_href = validate_pulp_href(pub_href) if pub_href else None
                    log.info(f"Got publication href from list: {validated_href}")
                    return True, validated_href
            return True, None

    except Exception as e:
        log.error(f"Exception during publication creation: {e}")
        return False, None


def create_aggregated_distribution(arch, pub_href, log):
    """
    Create or update the distribution for the aggregated repository.

    Args:
        arch (str): Architecture (x86_64 or aarch64).
        pub_href (str): Publication href to associate with distribution.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, distribution_name)
    """
    repo_name = AGGREGATED_REPO_NAME_TEMPLATE.format(arch=arch)
    dist_name = AGGREGATED_DISTRIBUTION_NAME_TEMPLATE.format(arch=arch)
    base_path = AGGREGATED_BASE_PATH_TEMPLATE.format(arch=arch)

    log.info(f"Creating/updating distribution '{dist_name}' with base_path '{base_path}'")

    # Validate pub_href matches expected Pulp href format (allowlist validation)
    validated_href = validate_pulp_href(pub_href) if pub_href else None

    # Check if distribution exists
    show_cmd = pulp_rpm_commands["check_distribution"] % dist_name

    if execute_command(show_cmd, log):
        # Distribution exists - update with new publication
        if validated_href:
            # Use subprocess with argument list - validated_href is passed as a separate argument
            # This prevents argument injection as the value is validated against expected format
            log.info(f"Updating distribution '{dist_name}' with publication href")
            update_result = subprocess.run(
                ["pulp", "rpm", "distribution", "update", "--name", dist_name, "--publication", validated_href],
                shell=False, capture_output=True, text=True
            )
            result = update_result.returncode == 0
        else:
            # Update with repository reference
            update_cmd = pulp_rpm_commands["update_distribution"] % (dist_name, base_path, repo_name)
            result = execute_command(update_cmd, log)

        if not result:
            log.error(f"Failed to update distribution: {dist_name}")
            return False, dist_name
        log.info(f"Distribution '{dist_name}' updated successfully.")
    else:
        # Create new distribution
        create_cmd = pulp_rpm_commands["distribute_repository"] % (dist_name, base_path, repo_name)
        result = execute_command(create_cmd, log)

        if not result:
            log.error(f"Failed to create distribution: {dist_name}")
            return False, dist_name
        log.info(f"Distribution '{dist_name}' created successfully.")

    return True, dist_name


def manage_aggregated_repos(additional_repos_config, log):
    """
    Manage aggregated repositories for additional_repos_* entries.
    This function handles the complete workflow:
    1. Delete existing aggregated repo (always recreate for clean state)
    2. Create new aggregated repository
    3. Create remotes for each repo entry
    4. Sync each remote to the aggregated repository
    5. Create publication
    6. Create/update distribution

    Args:
        additional_repos_config (dict): Dictionary with arch as key and list of repo configs as value.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, error_message)
    """
    log.info("Starting management of aggregated repositories")

    for arch in ["x86_64", "aarch64"]:
        repos = additional_repos_config.get(arch, [])
        repo_name = AGGREGATED_REPO_NAME_TEMPLATE.format(arch=arch)

        log.info(f"Processing aggregated repos for arch '{arch}': {len(repos)} repos")

        # Step 1: Delete existing aggregated repo for clean state
        log.info(f"Step 1: Deleting existing aggregated repo for {arch}")
        delete_aggregated_repo(arch, log)

        # Step 2: Create aggregated repository
        log.info(f"Step 2: Creating aggregated repository for {arch}")
        success, _ = create_aggregated_repository(arch, log)
        if not success:
            return False, f"Failed to create aggregated repository for {arch}"

        # Step 3 & 4: Create remotes and sync (only if there are repos)
        if repos:
            sync_failures = []

            for repo_entry in repos:
                # Create remote
                log.info(f"Step 3: Creating remote for '{repo_entry['name']}'")
                success, remote_name = create_aggregated_remote(repo_entry, arch, log)
                if not success:
                    return False, f"Failed to create remote for {repo_entry['name']}"

                # Sync to aggregated repo
                log.info(f"Step 4: Syncing remote '{remote_name}' to aggregated repo")
                success, _ = sync_aggregated_repository(repo_name, remote_name, log)
                if not success:
                    sync_failures.append(repo_entry['name'])

            # Check if all syncs succeeded
            if sync_failures:
                return False, f"Failed to sync repos for {arch}: {', '.join(sync_failures)}"

        # Step 5: Create publication
        log.info(f"Step 5: Creating publication for {arch}")
        success, pub_href = create_aggregated_publication(repo_name, log)
        if not success:
            return False, f"Failed to create publication for aggregated repo {arch}"

        # Step 6: Create/update distribution
        log.info(f"Step 6: Creating/updating distribution for {arch}")
        success, _ = create_aggregated_distribution(arch, pub_href, log)
        if not success:
            return False, f"Failed to create distribution for aggregated repo {arch}"

        log.info(f"Successfully completed aggregated repo management for {arch}")

    log.info("Completed management of all aggregated repositories")
    return True, "success"

def manage_rpm_repositories_multiprocess(rpm_config, log, sw_archs=None, resync_repos=None):
    """
    Manage RPM repositories using multiprocessing.

    Args:
        rpm_config (list): A list of dictionaries containing the configuration for each RPM repository.
        log (logging.Logger): Logger instance for logging the process and errors.
        sw_archs (list, optional): List of architectures to process based on software_config.json.
                                   If provided, only repos matching these archs are processed.
        resync_repos (str/list, optional): Controls sync behavior:
            - None/empty: Skip already synced repos (default)
            - "all": Force resync all repos
            - list of repo names: Only sync specified repos
    Returns:
        tuple: (bool, str) indicating success and a message
    """

    # Filter rpm_config by sw_archs if provided
    if sw_archs:
        log.info(f"Filtering repositories for architectures: {sw_archs}")
        rpm_config = [repo for repo in rpm_config if repo.get("sw_arch") in sw_archs]
        log.info(f"Filtered to {len(rpm_config)} repositories")

    if not rpm_config:
        log.info("No repositories to process after filtering")
        return True, "No repositories to process"

    # Validate resync_repos contains valid repository names
    is_valid, error_msg = validate_resync_repos(resync_repos, rpm_config, log)
    if not is_valid:
        return False, error_msg

    cpu_count = os.cpu_count()
    process = min(cpu_count, len(rpm_config))
    #log.info(f"Number of processes = {process}")
    log.info(f"Number of processes for lightweight operations = {process}")

    # Calculate actual repos to process based on resync_repos
    # This determines the effective concurrency for sync/publish/distribute
    if resync_repos is None or resync_repos == "" or resync_repos == "all":
        repos_to_process_count = len(rpm_config)
    else:
        # Count repos that match resync_repos
        if isinstance(resync_repos, str):
            resync_list = [r.strip() for r in resync_repos.split(",")]
        else:
            resync_list = resync_repos
        repos_to_process_count = len(resync_list)

    log.info(f"Repos to actually process (based on resync_repos): {repos_to_process_count}")

    # Use configurable concurrency from config.py for resource-intensive operations
    # This prevents overwhelming the Pulp server, especially on NFS storage
    # Adjust PULP_CONCURRENCY via Ansible or in config.py::
    #   - For NFS storage: Use 1 (prevents 500/502/504 errors)
    #   - For local storage: Use 2 for optimal performance
    #   - For high-performance SAN: Can try 3-4 (monitor for errors)
    # Cap by actual repos to process, not total rpm_config
    pulp_process = min(PULP_CONCURRENCY, repos_to_process_count)
    #pulp_process = min(PULP_CONCURRENCY, process)

    log.info(f"Configured pulp concurrency: {PULP_CONCURRENCY}")
    log.info(f"Actual pulp processes (capped by repo to process): {pulp_process}")

    # Step 1: Concurrent repository creation
    log.info("Step 1: Starting concurrent RPM repository creation")
    with multiprocessing.Pool(processes=process) as pool:
        result = pool.map(partial(create_rpm_repository, log=log), rpm_config)
    failed = [name for success, name in result if not success]
    if failed:
        log.error("Failed during creation of RPM repository for: %s", ", ".join(failed))
        return False, f"During creation of RPM repository for: {', '.join(failed)}"

    # Step 2: Concurrent remote creation
    log.info("Step 2: Starting concurrent RPM remote creation")
    with multiprocessing.Pool(processes=process) as pool:
        sync_result = pool.map(partial(create_rpm_remote, log=log), rpm_config)
    failed = [name for success, name in sync_result if not success]
    if failed:
        log.error("Failed during creation of RPM remote for: %s", ", ".join(failed))
        return False, f"During creation of RPM remote for: {', '.join(failed)}"

    # Step 3: Concurrent synchronization
    log.info("Step 3: Starting concurrent RPM repository synchronization")
    with multiprocessing.Pool(processes=pulp_process) as pool:
        sync_results = pool.map(partial(sync_rpm_repository, log=log, resync_repos=resync_repos), rpm_config)
    failed = [name for success, name, _, _ in sync_results if not success]
    if failed:
        log.error("Failed during synchronization of RPM repository for: %s", ", ".join(failed))
        return False, f"During synchronization of RPM repository for: {', '.join(failed)}. Please refer to the troubleshooting guide for more information."

    # Process sync results and get repos for publication/distribution
    repos_for_pub_dist, should_skip, skip_message  = process_sync_results(sync_results, rpm_config, resync_repos, log)
    
    if should_skip:
        return True, skip_message

    # Step 4: Concurrent publication creation
    # Deletes old publications and creates new ones
    log.info("Step 4: Starting concurrent RPM publication creation")
    log.info(f"Processing publication for {len(repos_for_pub_dist)} repos")
    with multiprocessing.Pool(processes=min(pulp_process, len(repos_for_pub_dist))) as pool:
        result = pool.map(partial(create_publication, log=log, resync_repos=resync_repos), repos_for_pub_dist)
    failed = [name for success, name in result if not success]
    if failed:
        log.error("Failed during publication of RPM repository for: %s", ", ".join(failed))
        return False, f"During publication of RPM repository for: {', '.join(failed)}. Please refer to the troubleshooting guide for more information."

    # Step 5: Concurrent distribution creation/update
    log.info("Step 5: Starting concurrent RPM distribution creation/update")
    log.info(f"Processing distribution for {len(repos_for_pub_dist)} repos")
    with multiprocessing.Pool(processes=min(pulp_process, len(repos_for_pub_dist))) as pool:
        result = pool.map(partial(create_distribution, log=log, resync_repos=resync_repos), repos_for_pub_dist)
    failed = [name for success, name in result if not success]
    if failed:
        log.error("Failed during distribution of RPM repository for: %s", ", ".join(failed))
        return False, f"During distribution of RPM repository for: {', '.join(failed)}"

    # --- STEP 6: Fetch Base URLs and Create YUM Repo File ---
    log.info("Step 6: Fetching base URLs and creating yum repo file")
    base_urls = get_base_urls(log)
    if not base_urls:
        log.error("No base URLs retrieved from Pulp. Skipping repo file creation.")
        return False, "Base URLs fetch failed — repo file not created."

    log.info(f"Fetched {len(base_urls)} base URLs from Pulp.")
    create_yum_repo_file(base_urls, log)
    log.info("Successfully created yum repo file with fetched base URLs.")

    # Return appropriate success message based on resync_repos
    if resync_repos == "all":
        return True, "Resync completed successfully for all repositories"
    elif resync_repos:
        if isinstance(resync_repos, str):
            repos_list = resync_repos
        else:
            repos_list = ", ".join(resync_repos)
        return True, f"Resync completed successfully for specified repositories: {repos_list}"
    
    return True, "RPM repository sync and configuration completed successfully"

def main():
    """
    The main function of the module.

    This function sets up the argument specifications for the module and initializes the logger.
    It then retrieves the `local_config` and `log_dir` parameters from the module.

    The `local_config` parameter is used to replace single quotes with double quotes to make it valid JSON.
    The JSON string is then parsed and stored in the `rpm_config` variable.

    The `manage_rpm_repositories_multiprocess` function is called with the `rpm_config` and `log` as arguments.

    If `additional_repos_config` is provided, the `manage_aggregated_repos` function is called to handle
    the aggregated repositories feature.

    Finally, the function exits with a JSON response indicating that the RPM configuration has been processed.

    Parameters:
        None

    Returns:
        None
    """
    module_args = {
        "local_config": {"type": "list", "required": True},
        "log_dir": {"type": "str", "required": False, "default": "/tmp/thread_logs"},
        "additional_repos_config": {"type": "dict", "required": False, "default": None},
        "pulp_concurrency": {"type": "int", "required": False, "default": None},
        "sw_archs": {"type": "list", "required": False, "default": None},
        "resync_repos": {"type": "raw", "required": False, "default": None}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    # Get the local_config parameter from the module
    rpm_config = module.params["local_config"]
    log_dir = module.params["log_dir"]
    additional_repos_config = module.params["additional_repos_config"]
    pulp_concurrency = module.params["pulp_concurrency"]
    sw_archs = module.params["sw_archs"]
    resync_repos = module.params["resync_repos"]

    log = setup_standard_logger(log_dir)

    # Optional override from Ansible (keep config.py defaults if unset)
    global PULP_CONCURRENCY

    if pulp_concurrency is not None:
        if pulp_concurrency < 1:
            module.fail_json(msg="pulp_concurrency must be >= 1")
        PULP_CONCURRENCY = pulp_concurrency

    log.info(f"Configured pulp concurrency: {PULP_CONCURRENCY}")

    start_time = datetime.now().strftime("%I:%M:%S %p")

    log.info(f"Start execution time: {start_time}")

    log.info(f"Architectures to process: {sw_archs}")
    log.info(f"Resync repos setting: {resync_repos}")
    # Call the function to manage RPM repositories
    result, output = manage_rpm_repositories_multiprocess(rpm_config, log, sw_archs, resync_repos)

    if result is False:
        module.fail_json(msg=f"Error {output}, check {STANDARD_LOG_FILE_PATH}")

    # Handle aggregated repos if additional_repos_config is provided
    if additional_repos_config:
        log.info("Processing additional_repos aggregated repositories")
        result, output = manage_aggregated_repos(additional_repos_config, log)
        if result is False:
            module.fail_json(msg=f"Error in aggregated repos: {output}, check {STANDARD_LOG_FILE_PATH}")
        log.info("Successfully processed additional_repos aggregated repositories")

    module.exit_json(changed=True, result=output)

if __name__ == "__main__":
    main()
