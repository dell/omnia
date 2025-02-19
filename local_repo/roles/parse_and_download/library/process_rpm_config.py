# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.standard_logger import setup_standard_logger
import json
import logging
import subprocess
import multiprocessing
import sys
import os
import requests
from datetime import datetime
from functools import partial

# Define pulp_rpm_commands and rpm_config here as in your existing code
pulp_rpm_commands = {
    "create_repository": "pulp rpm repository create --name %s",
    "pulp_cleanup": "pulp orphan cleanup",
    "show_repository": "pulp rpm repository show --name %s",
    "create_remote": "pulp rpm remote create --name %s --url %s --policy %s",
    "show_remote": "pulp rpm remote show --name %s",
    "update_remote": "pulp rpm remote update --name %s --url %s --policy %s",
    "sync_repository": "pulp rpm repository sync --name %s --remote %s",
    "publish_repository": "pulp rpm publication create --repository %s",
    "distribute_repository": "pulp rpm distribution create --name %s  --base-path %s  --repository %s",
    "update_distribution": "pulp rpm distribution update --name %s  --base-path %s  --repository %s",
    "check_distribution": "pulp rpm distribution show --name %s"
}


def execute_command(cmd_string, log,type_json=None, seconds=None):
    """
    Executes a shell command and returns its output.

    Args:
        cmd_string (str): The shell command to execute.
        log (logging.Logger): Logger instance for logging the process and errors.
        type_json (bool, optional): If set to `True`, the function will attempt to parse the command's output as JSON.
        seconds (float, optional): The maximum time allowed for the command to execute. If `None`, no timeout is enforced.

    Returns:
        str or bool: Returns the command's output as a string, or `False` if the command failed.
    """

    try:
        log.info("Executing Command: %s", cmd_string)
        cmd = subprocess.run(cmd_string, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=seconds, shell=True)
        if cmd.returncode != 0:
            return False
        if type_json:
            return json.loads(cmd.stdout)
        return cmd.stdout.strip()
    except Exception as e:
        log.error("Exception while executing command: %s", str(e))
        return False

def skip_config(package_name, version, log):
    """
    Check if the distribution should be skipped based on package name and version.

    Args:
        package_name (str): The name of the package.
        version (str): The version of the package.
        log (logging.Logger): Logger instance for logging the process.

    Returns:
        bool: True if the repository should be skipped, False otherwise.
    """
    if package_name in ["beegfs", "rocm", "amdgpu"] and version == "null":
        log.info(f"Skipping repository {package_name} due to missing version in software_config.json.")
        return True
    return False

def check_packages_and_get_url(distribution_name,log):
    """
    Check if packages exist in the distribution and return the base URL.

    Parameters:
        distribution_name (str): The name of the distribution.
        log (logging.Logger): The logger object.

    Returns:
        bool: True if packages exist in the distribution, False otherwise.
    """
    try:
        result = subprocess.run(
            ["pulp", "rpm", "distribution", "list", "--name", distribution_name, "--field", "base_url"],
            capture_output=True, text=True, check=True
        )
        base_urls = json.loads(result.stdout)
        if not base_urls:
            return False

        base_url = base_urls[0]["base_url"]
        response = requests.get(base_url)
        if response.status_code == 200 and "Packages/" in response.text:
            log.info(f"{distribution_name} packages directory exists. Skipping.")
            return True
        else:
            log.info(f"{distribution_name} packages directory does not exist. Proceeding.")
            return False
    except Exception as e:
        log.error(f"Error: {e}")
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

    repo_name = repo["package"]
    version = repo.get("version")

    if skip_config(repo_name, version, log):
        return False

    if version != "null":
        repo_name = f"{repo_name}_{version}"
    if not show_rpm_repository(repo_name,log):
        command = pulp_rpm_commands["create_repository"] % repo_name
        result = execute_command(command,log)
        log.info("Repository %s created.", repo_name)
        return result

    log.info("Repository %s already exists.", repo_name)
    return True

def show_rpm_repository(repo_name,log):
    """
    Show details of an RPM repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the repository was found, False otherwise.
    """

    command = pulp_rpm_commands["show_repository"] % repo_name
    return execute_command(command,log)

def create_rpm_remote(repo,log):
    """
    Create a remote for the RPM repository if it doesn't already exist.

    Args:
        repo (dict): A dictionary containing the repository information.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the remote was created or updated successfully, False otherwise.
    """

    remote_url = repo["url"]
    policy_type = "on_demand"
    version = repo.get("version")
    repo_name = repo["package"]

    if skip_config(repo_name, version, log):
        return False

    if version != "null":
        repo_name = f"{repo_name}_{version}"

    remote_name = repo_name
    if not show_rpm_remote(remote_name,log):
        command = pulp_rpm_commands["create_remote"] % (remote_name, remote_url, policy_type)
        result = execute_command(command,log)
        log.info("Remote %s created.", remote_name)
        return result
    else:
        command = pulp_rpm_commands["update_remote"] % (remote_name, remote_url, policy_type)
        log.info("Remote %s already exists.", remote_name)
        result = execute_command(command,log)
        return result

def show_rpm_remote(remote_name,log):
    """
    Show details of an RPM remote.

    Args:
        remote_name (str): The name of the remote.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the remote was found, False otherwise.
    """

    command = pulp_rpm_commands["show_remote"] % remote_name
    return execute_command(command,log)

def sync_rpm_repository(repo,log):
    """
    Synchronizes the RPM repository with its remote.

    Args:
        repo (dict): A dictionary containing the repository information.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the repository was synced successfully, False otherwise.
    """

    repo_name = repo["package"]
    version = repo.get("version")

    if skip_config(repo_name, version, log):
        return False

    if version != "null":
        repo_name = f"{repo_name}_{version}"

    if check_packages_and_get_url(repo_name,log):
        return True
    else:
        remote_name= repo_name
        command = pulp_rpm_commands["sync_repository"] % (repo_name, remote_name)
        result = execute_command(command,log)
        log.info("Repository synced for %s.", repo_name)
        return result

def create_publication(repo,log):
    """
    Create a publication for an RPM repository.

    Args:
        repo (dict): A dictionary containing the package information.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the publication was created successfully, False otherwise.
    """

    repo_name = repo["package"]
    version = repo.get("version")

    if skip_config(repo_name, version, log):
        return False

    if version != "null":
        repo_name = f"{repo_name}_{version}"

    command = pulp_rpm_commands["publish_repository"] % repo_name
    result = execute_command(command,log)
    log.info("Publication created for %s.", repo_name)
    return result

def create_distribution(repo, log):
    """
    Create or update a distribution for an RPM repository.

    Args:
        repo (dict): A dictionary containing the repository information.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the distribution was created or updated successfully, False otherwise.
    """

    package_name = repo["package"]
    repo_name = package_name
    version = repo.get("version")

    if skip_config(repo_name, version, log):
        return False

    if version != "null":
        base_path = f" opt/omnia/offline_repo/cluster/rhel/rpms/{package_name}/{version}"
        repo_name = f"{repo_name}_{version}"
    else:
        base_path = f"opt/omnia/offline_repo/cluster/rhel/rpms/{package_name}"

    show_command = pulp_rpm_commands["check_distribution"] % repo_name
    create_command = pulp_rpm_commands["distribute_repository"] % (repo_name, base_path, repo_name)
    update_command = pulp_rpm_commands["update_distribution"] % (repo_name, base_path, repo_name)

    # Check if distribution already exists
    if execute_command(show_command, log):
        log.info(f"Distribution for {package_name} exists. Updating it.")
        return execute_command(update_command, log)
    else:
        log.info(f"Distribution for {package_name} does not exist. Creating it.")
        return execute_command(create_command, log)

def get_base_urls(log):
    """
    Fetch all distributions from Pulp RPM distribution.

    Args:
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        list: A list of dictionaries containing the base URLs and names of all distributions.
              Returns an empty list if there is an error.
    """

    result = subprocess.run(['pulp', 'rpm', 'distribution', 'list', '--field', 'base_url,name'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        log.info(f"Error fetching distributions: {result.stderr}")
        return []

    # Parse the JSON output to get all distributions
    try:
        distributions = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        log.error(f"Error parsing JSON output: {e}")
        return []

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

    repo_file_path = "/etc/yum.repos.d/pulp.repo"

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
    with open(repo_file_path, 'w') as repo_file:
        repo_file.write(repo_content.strip() + "\n")

    log.info(f"Created {repo_file_path} with {len(distributions)} repositories")

def manage_rpm_repositories_multiprocess(rpm_config,log):
    """
    Manage RPM repositories using multiprocessing.

    Args:
        rpm_config (list): A list of dictionaries containing the configuration for each RPM repository.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        None
    """

    # Step 1: Concurrent repository creation
    cpu_count=os.cpu_count()
    process=min(cpu_count, len(rpm_config))
    log.info(f"Number of process = {process}")

    with multiprocessing.Pool(processes=process) as pool:
        pool.map(partial(create_rpm_repository, log=log), rpm_config)

    # Step 2: Concurrent remote creation
    with multiprocessing.Pool(processes=process) as pool:
        pool.map(partial(create_rpm_remote, log=log), rpm_config)

    # Step 3: Concurrent synchronization
    with multiprocessing.Pool(processes=process) as pool:
        pool.map(partial(sync_rpm_repository, log=log), rpm_config)

    # Step 4: Concurrent publication creation
    with multiprocessing.Pool(processes=process) as pool:
        pool.map(partial(create_publication, log=log), rpm_config)

    # Step 5: Concurrent distribution creation
    with multiprocessing.Pool(processes=process) as pool:
        pool.map(partial(create_distribution, log=log), rpm_config)

    base_urls = get_base_urls(log)
    create_yum_repo_file(base_urls, log)

def main():
    """
    The main function of the module.

    This function sets up the argument specifications for the module and initializes the logger.
    It then retrieves the `local_config` and `log_dir` parameters from the module.

    The `local_config` parameter is used to replace single quotes with double quotes to make it valid JSON.
    The JSON string is then parsed and stored in the `rpm_config` variable.

    The `manage_rpm_repositories_multiprocess` function is called with the `rpm_config` and `log` as arguments.

    Finally, the function exits with a JSON response indicating that the RPM configuration has been processed.

    Parameters:
        None

    Returns:
        None
    """
    module_args = dict(
        local_config=dict(type="str", required=True),
        log_dir=dict(type="str", required=False, default="/tmp/thread_logs")
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    # Get the local_config parameter from the module
    local_config = module.params["local_config"]
    log_dir = module.params["log_dir"]

    log = setup_standard_logger(log_dir)

    start_time = datetime.now().strftime("%I:%M:%S %p")

    log.info(f"Start execution time: {start_time}")


    # Replace single quotes with double quotes to make it valid JSON
    valid_json_str = local_config.replace("'", '"')

    # Parse the string as JSON
    try:
        rpm_config = json.loads(valid_json_str)
    except json.JSONDecodeError as e:
        module.fail_json(msg=f"Error parsing JSON: {e}")

    # Call the function to manage RPM repositories
    manage_rpm_repositories_multiprocess(rpm_config,log)

    module.exit_json(changed=True, result="RPM Config Processed")

if __name__ == "__main__":
    main()

