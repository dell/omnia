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

#!/usr/bin/python

import json
import logging
import os
import re
import shutil
import tempfile
from subprocess import PIPE, Popen
from urllib.parse import urlparse

# Third-party libraries
from git import Repo
from packaging.version import InvalidVersion, Version
from prettytable import PrettyTable
import yaml

# Ansible modules
from ansible.module_utils.basic import AnsibleModule

SKIP_TYPES = ["rpm", "deb", "manifest", "pip_module", "git"]
SKIP_PACKAGES = ["ghcr.io/k8snetworkplumbingwg/multus-cni"]

# ============================================================================================
#                              Logging Configuration
# ============================================================================================

def setup_logging(log_dir):
    """Configure logging to file and console with specified log directory"""
    try:
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, 'kubespray_processor.log')

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured. Log file: {log_file}")
        return logger
    except Exception as e:
        print(f"Failed to configure logging: {str(e)}")
        raise

# Initialize logger as None, will be set in run_module
logger = None

# ============================================================================================
#                              Custom Exceptions
# ============================================================================================
class DirectoryOperationError(Exception):
    """Raised when directory operations fail"""

class FileOperationError(Exception):
    """Raised when file operations fail"""

class GitOperationError(Exception):
    """Raised when git operations fail"""

class CommandExecutionError(Exception):
    """Raised when command execution fails"""

class InvalidVersionError(Exception):
    """Raised when version comparison fails"""

class InvalidInputError(Exception):
    """Raised when input validation fails"""

# ============================================================================================
#                              Common functions
# ============================================================================================
def verify_file_exists(file_path: str) -> bool:
    """Verify if a file exists.
    
    Args:
        file_path: Path to the file to verify
        
    Returns:
        bool: True if file exists, False otherwise
        
    Raises:
        FileOperationError: If verification fails
    """
    try:
        exists = os.path.exists(file_path) and os.path.isfile(file_path)
        logger.debug("File %s %s", file_path, "exists" if exists else "does not exist")
        return exists
    except OSError as e:
        logger.error("OS error verifying file existence: %s", str(e))
        raise FileOperationError(f"OS error verifying {file_path}") from e
    except Exception as e:
        logger.error("Unexpected error verifying file: %s", str(e))
        raise FileOperationError(f"Unexpected error with {file_path}") from e

def delete_directory(dir_path):
    """Safely delete a directory and its contents."""
    try:
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path)
            logger.info("Directory '%s' and its contents have been deleted.", dir_path)
        else:
            logger.warning("Directory '%s' does not exist to delete.", dir_path)
    except PermissionError as e:
        logger.error("Permission denied to delete '%s': %s", dir_path, str(e))
        raise DirectoryOperationError(f"Permission denied to delete directory: {dir_path}") from e
    except OSError as e:
        logger.error("Error deleting directory '%s': %s", dir_path, str(e))
        raise DirectoryOperationError(f"Error deleting directory: {dir_path}") from e


def recreate_directory(base_path, branch_name, kube_version):
    """
    Recreate directories for kubespray branch and version.

    Parameters:
        base_path (str): Base path for directory creation.
        branch_name (str): Name of the kubespray branch.
        kube_version (str): Kubernetes version.

    Returns:
        tuple: A tuple containing the paths to the recreated directories.
    """
    try:
        directory_path = os.path.join(base_path, f'kubespray-{branch_name}')
        version_path = os.path.join(base_path, kube_version)

        # Delete existing directories if they exist
        for path in [directory_path, version_path]:
            if os.path.exists(path):
                shutil.rmtree(path)
                logger.info("Deleted existing directory: %s", path)

        # Create new directories
        os.makedirs(directory_path, exist_ok=True)
        os.makedirs(version_path, exist_ok=True)

        logger.info("Directory created at: %s", directory_path)
        logger.info("Version directory created at: %s", version_path)

        return directory_path, version_path
    except OSError as e:
        logger.error("Error recreating directories: %s", str(e))
        raise DirectoryOperationError(f"Failed to recreate directories: {str(e)}") from e


def update_yaml_variables(clone_path, updates):
    """
    Updates variables in a YAML file.

    Parameters:
        clone_path (str): Path to the base directory containing YAML files.
        updates (dict): Dictionary containing key-value pairs to be updated.

    Returns:
        tuple: (bool indicating if update succeeded, str or None with old value if applicable).
    """
    try:
        # Determine the correct YAML file path
        possible_paths = [
            os.path.join(clone_path, 'roles/kubespray_defaults/defaults/main/main.yml'),
            os.path.join(clone_path, 'roles/kubespray-defaults/defaults/main/main.yml'),
            os.path.join(clone_path, 'roles/kubespray-defaults/defaults/main.yaml')
        ]

        actual_path = next((path for path in possible_paths if verify_file_exists(path)), None)

        if not actual_path:
            logger.error("No YAML file found in %s", clone_path)
            return False, None

        logger.info("File present in path: %s", actual_path)

        with open(actual_path, 'r') as file:
            yaml_content = yaml.safe_load(file)

        updated = False
        old_value = None

        for key, value in updates.items():
            if key in yaml_content:
                old_value = yaml_content[key]
                if not str(old_value).startswith('v'):
                    logger.info("%s old value %s new value", old_value, value)
                    value = value.lstrip('v')
                yaml_content[key] = value
                logger.info("%s key updated with value %s in the YAML file %s", key, value, actual_path)
                updated = True
            else:
                logger.warning("%s key not found in the YAML file %s", key, actual_path)

        if not updated:
            logger.warning("No variables were updated.")
            return False, None

        with open(actual_path, 'w') as file:
            yaml.safe_dump(yaml_content, file)

        return True, old_value

    except yaml.YAMLError as e:
        logger.error("YAML parsing error: %s", str(e))
        raise FileOperationError(f"YAML parsing error: {str(e)}") from e
    except (OSError, IOError) as e:
        logger.error("Error updating YAML file: %s", str(e))
        raise FileOperationError(f"Error updating YAML file: {str(e)}") from e


def update_arch_variables(clone_path, update_arch):
    """
    Updates architecture-specific variables in a YAML file.

    Parameters:
        clone_path (str): Path to the directory where the YAML file is located.
        update_arch (dict): A dictionary containing the keys and values to update in the YAML file.

    Returns:
        bool: True if at least one variable was updated, False otherwise.
    """
    possible_paths = [
        os.path.join(clone_path, 'roles/kubespray_defaults/defaults/main/download.yml'),
        os.path.join(clone_path, 'roles/kubespray-defaults/defaults/main/download.yml')
    ]
    actual_path = next((path for path in possible_paths if verify_file_exists(path)), None)

    if not actual_path:
        logger.error("No YAML file found in %s", clone_path)
        return False

    logger.info("Using YAML file: %s", actual_path)

    with open(actual_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    with open(actual_path, 'w', encoding='utf-8') as f:
        for line in lines:
            for key, value in update_arch.items():
                if line.strip().startswith(f"{key}:"):
                    logger.info("%s updated from line: %s -> %s: %s",
                                key, line.strip(), key, value)
                    line = f"{key}: {value}\n"
                    updated = True
            f.write(line)

    if not updated:
        logger.warning("No keys were updated.")

    return updated


def verify_directory_exists(directory_path):
    """
    Verify if a directory exists.

    Parameters:
        directory_path (str): The directory path to check.

    Returns:
        bool: True if the directory exists, False otherwise.
    """
    try:
        exists = os.path.exists(directory_path) and os.path.isdir(directory_path)
        if exists:
            logger.debug("The directory %s exists", directory_path)
        else:
            logger.debug("The directory %s does not exist", directory_path)
        return exists
    except OSError as e:
        logger.error("Error verifying directory existence: %s", str(e))
        raise DirectoryOperationError(f"Error verifying directory existence: {str(e)}") from e


def execute_command(cmd):
    """
    Execute a shell command and capture its output.

    Parameters:
        cmd (str): The command to execute.

    Returns:
        tuple: (stdout, stderr) output strings.

    Raises:
        CommandExecutionError: If the command fails.
    """
    try:
        logger.info("Executing command: %s", cmd)
        process = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        out, err = process.communicate()
        rc = process.returncode

        if rc == 0:
            status = (out.decode("utf-8").strip(), err.decode("utf-8").strip())
            logger.debug("Command output: %s", status)
            return status

        error_msg = "Command '%s' failed with return code %d. Error: %s" % (
            cmd, rc, err.decode("utf-8")
        )
        logger.error("%s", error_msg)
        raise CommandExecutionError(error_msg)

    except OSError as e:
        logger.error("Error executing command '%s': %s", cmd, str(e))
        raise CommandExecutionError(f"Error executing command: {str(e)}") from e


def load_file(file_path, mode):
    """
    Load content from a file and return as a list of lines.

    Parameters:
        file_path (str): Path to the file.
        mode (str): File open mode, e.g. 'r'.

    Returns:
        list|bool: List of lines or False if file not found.
    """
    try:
        if not verify_file_exists(file_path):
            return False

        with open(file_path, mode, encoding="utf-8") as f:
            return f.read().splitlines()

    except IOError as e:
        logger.error("Error reading file %s: %s", file_path, str(e))
        raise FileOperationError(f"Error reading file: {str(e)}") from e


def load_json(file_path, mode):
    """
    Load and parse JSON content from a file.

    Parameters:
        file_path (str): Path to the JSON file.
        mode (str): File open mode, e.g. 'r'.

    Returns:
        dict|bool: Parsed JSON data or False if file not found.
    """
    try:
        if not verify_file_exists(file_path):
            return False

        with open(file_path, mode, encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError as e:
        logger.error("JSON parsing error in %s: %s", file_path, str(e))
        raise FileOperationError(f"JSON parsing error: {str(e)}") from e
    except IOError as e:
        logger.error("Error reading JSON file %s: %s", file_path, str(e))
        raise FileOperationError(f"Error reading JSON file: {str(e)}") from e


def write_json(file_path, json_data):
    """
    Write JSON data to a file.

    Parameters:
        file_path (str): Path to the output file.
        json_data (dict): Data to write.

    Raises:
        FileOperationError: If writing fails.
    """
    try:
        with open(file_path, 'w', encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)
        logger.info("Successfully wrote JSON data to %s", file_path)

    except IOError as e:
        logger.error("Error writing JSON file %s: %s", file_path, str(e))
        raise FileOperationError(f"Error writing JSON file: {str(e)}") from e
    except TypeError as e:
        logger.error("Invalid JSON data: %s", str(e))
        raise FileOperationError(f"Invalid JSON data: {str(e)}") from e


# ============================================================================================
#                              Git related functions
# ============================================================================================
def is_version_within_range(clone_to_path, input_version, arch):
    """
    Check if the given input_version is within the kubelet_checksums range for a specific architecture.

    Parameters:
        clone_to_path (str): Path to the cloned kubespray directory.
        input_version (str): The Kubernetes version to check.
        arch (str): Architecture name (e.g., 'amd64').

    Returns:
        tuple: (bool: True if input_version is within range, 
                list: Available compatible versions)
    """
    try:
        possible_paths = [
            os.path.join(clone_to_path, 'roles/kubespray-defaults/defaults/main/checksums.yml'),
            os.path.join(clone_to_path, 'roles/kubespray_defaults/vars/main/checksums.yml')
        ]

        actual_path = None
        for path in possible_paths:
            if verify_file_exists(path):
                actual_path = path
                break

        if not actual_path:
            logger.error("No YAML file found in possible paths.")
            return False, []

        logger.info("Using checksums file at: %s", actual_path)

        with open(actual_path, 'r', encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or 'kubelet_checksums' not in data:
            logger.warning("Missing or invalid 'kubelet_checksums' in YAML.")
            return False, []

        if arch not in data['kubelet_checksums']:
            logger.warning("Architecture '%s' not found in 'kubelet_checksums'", arch)
            return False, []

        raw_versions = data['kubelet_checksums'][arch]
        version_list = []
        compatible_versions = []

        try:
            version_list = sorted([Version(v.lstrip('v')) for v in raw_versions.keys()])
            compatible_versions = [str(v) for v in version_list]
        except (InvalidVersion, AttributeError) as e:
            logger.error("Error parsing versions: %s", str(e))
            return False, []

        if not version_list:
            logger.warning("No valid versions found under architecture '%s'", arch)
            return False, []

        version_min = version_list[0]
        version_max = version_list[-1]

        try:
            input_ver = Version(input_version.lstrip('v'))
        except InvalidVersion as e:
            logger.error("Invalid input version format: %s", str(e))
            # Return all available versions when input version is invalid
            return False, compatible_versions

        if input_ver in version_list and raw_versions.get(f"v{input_ver}") == 0:
            logger.error("Version %s has invalid checksum value (0)", input_version)
            return False, compatible_versions

        result = version_min <= input_ver <= version_max
        logger.info("Version %s within range %s to %s: %s",
                   input_version, version_min, version_max, result)
        return result, compatible_versions

    except Exception as e:
        logger.error("Error checking version range: %s", str(e))
        return False, []


def get_latest_tag(repo_url):
    """
    Get the latest valid semantic version tag from the repository.

    Parameters:
        repo_url (str): The Git repository URL.

    Returns:
        str: The latest tag name.

    Raises:
        GitOperationError: If no valid tags are found or repo clone fails.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        logger.info("Fetching latest tag from %s", repo_url)
        repo = Repo.clone_from(repo_url, temp_dir)
        repo.git.fetch('--tags')

        valid_tags = []
        for tag in repo.tags:
            try:
                version = Version(tag.name.lstrip('v'))
                valid_tags.append((version, tag))
            except InvalidVersion:
                logger.warning("Skipping invalid version tag: %s", tag.name)

        if not valid_tags:
            logger.error("No valid tags found in repository")
            raise GitOperationError("No valid tags found in repository")

        latest_tag = sorted(valid_tags, key=lambda t: t[0], reverse=True)[0][1]
        logger.info("Latest tag found: %s", latest_tag.name)
        return latest_tag.name

    except (OSError, GitOperationError) as e:
        logger.error("Error fetching tags: %s", str(e))
        raise GitOperationError(f"Error fetching tags: {str(e)}") from e
    finally:
        try:
            shutil.rmtree(temp_dir)
        except OSError as e:
            logger.warning("Error cleaning up temp directory: %s", str(e))


def kubespray_dir_name(tag_name):
    """
    Generate directory name for a given kubespray tag.

    Parameters:
        tag_name (str): The Git tag name.

    Returns:
        str: Directory name formatted as 'kubespray-<tag>'.
    """
    return f"kubespray-{tag_name}"


def clone_kubespray_tag(repo_url, tag_name, base_path="./"):
    """
    Clone a specific kubespray tag from a Git repository.

    Parameters:
        repo_url (str): Repository URL.
        tag_name (str): Tag to be cloned.
        base_path (str): Directory to clone into.

    Raises:
        GitOperationError: If the clone fails.
    """
    dir_name = kubespray_dir_name(tag_name)
    clone_to_path = os.path.join(base_path, dir_name)

    if os.path.exists(clone_to_path):
        logger.warning("Directory '%s' already exists. Skipping.", clone_to_path)
        return

    try:
        logger.info("Cloning tag '%s' from %s", tag_name, repo_url)
        repo = Repo.clone_from(repo_url, clone_to_path)
        repo.git.checkout(tag_name)
        logger.info("Cloned to '%s' at tag '%s'", clone_to_path, tag_name)
    except Exception as e:
        logger.error("Failed to clone %s: %s", tag_name, str(e))
        raise GitOperationError(f"Failed to clone tag: {str(e)}") from e


def delete_kubespray_tag(tag_name, base_path="./"):
    """
    Delete a cloned kubespray tag directory.

    Parameters:
        tag_name (str): Tag name used to form the directory name.
        base_path (str): Parent path of the kubespray directory.

    Raises:
        DirectoryOperationError: If the directory deletion fails.
    """
    dir_name = kubespray_dir_name(tag_name)
    dir_to_delete = os.path.join(base_path, dir_name)

    if os.path.exists(dir_to_delete):
        try:
            shutil.rmtree(dir_to_delete)
            logger.info("Deleted '%s'", dir_to_delete)
        except OSError as e:
            logger.error("Error deleting %s: %s", dir_to_delete, str(e))
            raise DirectoryOperationError(f"Error deleting directory: {str(e)}") from e
    else:
        logger.warning("Directory '%s' does not exist. Nothing to delete.", dir_to_delete)


def clone_latest_tag(kube_version, base_path, arch, n_latest=3):
    """
    Clone the latest kubespray tag that supports the given Kubernetes version.

    Parameters:
        kube_version (str): Desired Kubernetes version.
        base_path (str): Path to clone into.
        arch (str): Architecture to check compatibility.
        n_latest (int): Number of latest tags to try.

    Returns:
        tuple: (str: Compatible tag name if found, else None,
                list: Available compatible versions)
    """
    temp_dir = tempfile.mkdtemp()
    compatible_versions = {}
    try:
        if not repo_url:
            raise GitOperationError("Repository URL not specified")

        logger.info("Cloning repository to check tags: %s", repo_url)
        repo = Repo.clone_from(repo_url, temp_dir)
        repo.git.fetch('--tags')

        valid_tags = []
        for tag in repo.tags:
            try:
                version = Version(tag.name.lstrip('v'))
                valid_tags.append((version, tag))
            except InvalidVersion:
                logger.debug("Skipping invalid version tag: %s", tag.name)
                continue

        if not valid_tags:
            logger.error("No valid tags found in repository")
            return None, []

        valid_tags.sort(key=lambda t: t[0], reverse=True)

        for i, (_, tag) in enumerate(valid_tags[:n_latest]):
            tag_name = tag.name
            logger.info("Checking tag %s (%d/%d)", tag_name, i + 1, n_latest)

            dir_name = kubespray_dir_name(tag_name)
            clone_to_path = os.path.join(base_path, dir_name)

            if not os.path.exists(clone_to_path):
                try:
                    clone_kubespray_tag(repo_url, tag_name, base_path)
                except GitOperationError as e:
                    logger.error("Failed to clone tag %s: %s", tag_name, str(e))
                    continue

            version_result, versions = is_version_within_range(clone_to_path, kube_version, arch)
            compatible_versions[tag_name] = versions
            if version_result:
                logger.info("Found compatible tag %s for %s", tag_name, kube_version)
                return tag_name, compatible_versions
            
            
            logger.info("Tag %s doesn't support %s. Available versions: %s", 
                       tag_name, kube_version, ", ".join(versions) if versions else "none")


        logger.error("No compatible tag found for %s in %d latest tags. Available versions: %s", 
                    kube_version, n_latest, ", ".join(compatible_versions[tag_name]) if compatible_versions[tag_name] else "none")
        return None, compatible_versions

    except Exception as e:
        logger.error("Error in clone_latest_tag: %s", str(e))
        return None, []
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning("Error cleaning up temp directory: %s", str(e))


def clone_kubespray(repo_url, tag_name, clone_to_path):
    """
    Clone the kubespray repository at a specific tag.

    Parameters:
        repo_url (str): URL of the Git repository.
        tag_name (str): Tag to checkout after cloning.
        clone_to_path (str): Directory path to clone the repository into.

    Raises:
        GitOperationError: If cloning or checkout fails.
    """
    try:
        logger.info("Cloning repository %s with tag %s to %s", repo_url, tag_name, clone_to_path)
        repo = Repo.clone_from(repo_url, clone_to_path)
        repo.git.checkout(tag_name)
        logger.info("Repository cloned to %s with tag %s", clone_to_path, tag_name)
    except Exception as e:
        logger.error("An error occurred while cloning the repository: %s", str(e))
        raise GitOperationError(f"Error cloning repository: {str(e)}") from e


# ============================================================================================
#                              Parse image list to process kubespary images
# ============================================================================================
def extract_image_name_and_tag(url):
    """
    Extract image name and tag from a URL.

    Parameters:
        url (str): Image URL (e.g., 'registry/repo/image:tag').

    Returns:
        tuple: (image_name, image_tag)
    """
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path
        filename = os.path.basename(path)

        if ':' in filename:
            image_name, image_tag = filename.split(':', 1)
        else:
            image_name, image_tag = filename, 'latest'

        return image_name, image_tag

    except (AttributeError, ValueError, TypeError) as e:
        logger.error("Error extracting image name and tag from %s: %s", url, str(e))
        raise InvalidInputError(f"Error parsing image URL: {str(e)}") from e


def get_k8s_data(k8_file_type, k8_file_path, package_types, software_name):
    """
    Load and validate Kubernetes package data from a JSON file.

    Parameters:
        k8_file_type (str): Specific package type to extract (e.g., 'image').
        k8_file_path (str): Path to the Kubernetes JSON file.
        package_types (list): Valid list of expected package types.
        software_name (str): Name of software ('k8s' or 'service_k8s')

    Returns:
        list|dict|bool: Filtered list by type, full dict, or False if validation fails.

    Raises:
        FileOperationError: If loading or processing fails.
        InvalidInputError: If an invalid type is passed.
    """
    try:
        filetype_inv = {
            "rpm": [],
            "deb": [],
            "tarball": [],
            "image": [],
            "manifest": [],
            "pip_module": [],
            "git": []
        }
        error_data = []

        if k8_file_type and k8_file_type not in package_types:
            logger.error("Not valid package type: %s", k8_file_type)
            raise InvalidInputError(f"Invalid package type: {k8_file_type}")

        k8_json_data = load_json(k8_file_path, 'r')
        if not k8_json_data:
            raise FileOperationError(f"Failed to load JSON data from {k8_file_path}")

        for package_info in k8_json_data.get(software_name, {}).get('cluster', []):
            package_type = package_info.get("type")
            package_name = package_info.get("package")

            if package_type not in package_types:
                logger.warning(
                    "Package type %s for package %s is not in the allowed types: %s",
                    package_type, package_name, package_types
                )
                error_data.append({package_type: package_info})
            else:
                filetype_inv[package_type].append(package_info)

        if error_data:
            logger.error("Found packages with invalid types")
            return False

        if k8_file_type:
            return filetype_inv.get(k8_file_type, [])

        return filetype_inv

    except (OSError, TypeError, KeyError, ValueError) as e:
        logger.error("Error processing k8s data: %s", str(e))
        raise FileOperationError(f"Error processing k8s data: {str(e)}") from e


def extract_version_from_url(url):
    """
    Extract the version string from a URL using a regex pattern.

    Parameters:
        url (str): The URL containing a version string.

    Returns:
        str|None: Extracted version string or None if no version is found.

    Raises:
        InvalidInputError: If URL parsing fails unexpectedly.
    """
    try:
        # Regex to match common semantic version formats
        pattern = r'(?:v|/|-|_|\.)([\d]+(?:\.[\d]+)+)(?=[/-_.]|$)'

        helm_match = re.search(r'v(\d+\.\d+\.\d+)', url)
        if helm_match:
            return helm_match.group(1)

        match = re.search(pattern, url)
        if match:
            version = match.group(1).strip('.')
            logger.debug("Extracted version %s from %s", version, url)
            return version

        logger.warning("Could not extract version from URL: %s", url)
        return None

    except (re.error, AttributeError, TypeError) as e:
        logger.error("Error extracting version from URL %s: %s", url, str(e))
        raise InvalidInputError(f"Error extracting version from URL: {str(e)}") from e


def print_not_found_packages(not_found_packages):
    """
    Print a formatted table of packages not found.

    Parameters:
        not_found_packages (list): List of dicts with 'package' and 'url' keys.
    """
    try:
        table = PrettyTable()
        table.field_names = ["package_name", "url"]

        for package in not_found_packages:
            package_name = package.get('package')
            url = package.get('url')
            table.add_row([package_name, url])

        logger.info("\nPackages not found:\n%s", table)

    except Exception as e:  # Justified use of generic catch for table formatting
        logger.error("Error printing not found packages: %s", str(e))
        raise


def print_not_found_images(not_found_images):
    """
    Print a formatted table of images not found.

    Parameters:
        not_found_images (list): List of dicts with 'package' and 'tag' keys.
    """
    try:
        table = PrettyTable()
        table.field_names = ["package_name", "tag"]

        for package in not_found_images:
            package_name = package.get('package', '').split('/')[-1]
            tag = package.get('tag')
            table.add_row([package_name, tag])

        logger.info("\nImages not found:\n%s", table)

    except Exception as e:  # Justified use of generic catch for display logic
        logger.error("Error printing not found images: %s", str(e))
        raise


def process_file_list(files_list_path, filetype_inv, final_k8s_data, software_name):
    """
    Process the list of tarball file URLs and update filetype_inv and final_k8s_data accordingly.

    Parameters:
        files_list_path (str): Path to the file containing tarball URLs.
        filetype_inv (list): List of expected tarball packages to update.
        final_k8s_data (dict): Dictionary to append updated package data to.
        software_name (str): Name of software ('k8s' or 'service_k8s')

    Returns:
        bool: True if processing is successful.

    Raises:
        FileOperationError: If file cannot be read or processing fails.
    """
    try:
        file_type = "tarball"
        updated_packages = []

        files_list = load_file(files_list_path, 'r')
        if not files_list:
            raise FileOperationError(f"Failed to load file list from {files_list_path}")

        tarball_count = 0

        for url in files_list:
            url_split_data = url.split('/')

            if 'gvisor' in url_split_data:
                continue

            if 'archive' in url_split_data:
                index = url_split_data.index('archive')
                package_name = (
                    url_split_data[index - 1] +
                    '.archive-' +
                    url_split_data[-1]
                        .replace('.tar.gz', '')
                        .replace('.tgz', '')
                )
            else:
                package_name = url_split_data[-1] \
                    .replace('.tar.gz', '') \
                    .replace('.tgz', '')

            search_name = package_name.split('-')[0] if '-' in package_name else package_name

            version = extract_version_from_url(url)
            if not version:
                logger.warning("Could not extract version from URL: %s", url)
                continue

            for item in filetype_inv:
                if item.get('package', '').split('-')[0] == search_name:
                    item['url'] = url
                    item['package'] = f"{search_name}-v{version}"
                    updated_packages.append({
                        'package': item['package'],
                        'type': file_type,
                        'url': url
                    })
                    tarball_count += 1
                    break

        logger.info("Processed %d tarballs from %d expected", tarball_count, len(filetype_inv))

        final_k8s_data[software_name]["cluster"].extend(filetype_inv)

        diff_in_list1 = [item for item in filetype_inv if item not in updated_packages]
        if diff_in_list1:
            print_not_found_packages(diff_in_list1)

        return True

    except (OSError, IOError, KeyError, TypeError) as e:
        logger.error("Error processing file list: %s", str(e))
        raise FileOperationError(f"Error processing file list: {str(e)}") from e


def process_image_list(images_list_path, filetype_inv, final_k8s_data, software_name):
    """
    Process the image list and update `filetype_inv` and `final_k8s_data` with image metadata.

    Parameters:
        images_list_path (str): Path to the file containing image URLs.
        filetype_inv (list): List of expected images to be updated.
        final_k8s_data (dict): Main output structure to store results under 'k8s.cluster'.
        software_name (str): Name of software ('k8s' or 'service_k8s')

    Returns:
        bool: True if image processing was successful.

    Raises:
        FileOperationError: If file cannot be read or processing fails.
    """
    try:
        file_type = "image"
        updated_images = []

        images_list = load_file(images_list_path, 'r')
        if not images_list:
            raise FileOperationError(f"Failed to load image list from {images_list_path}")

        image_count = 0
        images_list_dict = {}

        for image in images_list:
            image_name, image_tag = extract_image_name_and_tag(image)
            images_list_dict[image_name] = image_tag

        for item in filetype_inv:
            image_name = item.get("package", "").split('/')[-1]

            if image_name in images_list_dict:
                if item["package"] in SKIP_PACKAGES:
                    continue
                item["tag"] = images_list_dict[image_name]
                updated_images.append({
                    'package': item['package'],
                    'tag': item['tag'],
                    'type': file_type
                })
                image_count += 1

        logger.info("Processed %d images from %d expected", image_count, len(filetype_inv))

        final_k8s_data[software_name]["cluster"].extend(filetype_inv)

        diff_in_list1 = [item for item in filetype_inv if item not in updated_images]
        if diff_in_list1:
            print_not_found_images(diff_in_list1)

        return True

    except (OSError, KeyError, TypeError) as e:
        logger.error("Error processing image list: %s", str(e))
        raise FileOperationError(f"Error processing image list: {str(e)}") from e


def generate_k8_jsons_for_version(kube_version, base_path, repo_url, package_types, k8s_json_path, arch, n_latest, software_name, mode="clone", check_version=False):
    """
    Generates a JSON file for a specific Kubernetes version.

    Parameters:
        kube_version (str): Kubernetes version to process
        base_path (str): Base directory path for operations
        repo_url (str): Kubespray repository URL
        package_types (list): List of package types to process
        k8s_json_path (str): Path to output JSON file
        arch (str): Target architecture
        n_latest (int): Number of latest tags to check
        software_name (str): Name of software ('k8s' or 'service_k8s')
        mode (str): Operation mode ('clone', 'delete', 'both')
        check_version (bool): If True, only check version compatibility

    Returns:
        tuple: (bool: success status, 
               str: compatible tag name if check_version=True, 
               list: compatible versions)
    """
    try:
        if not all([kube_version, base_path, repo_url, arch]):
            raise InvalidInputError("Missing required parameters")

        updates = {"kube_version": kube_version}
        update_arch = {"image_arch": arch}

        logger.info("============================ start ============================")
        tag_name, compatible_versions = clone_latest_tag(kube_version, base_path, arch, n_latest)
        
        if tag_name is None:
            error_msg = f"No compatible tag found for version {kube_version}"
            # if compatible_versions:
            #     error_msg += f". Available tags: {', '.join(compatible_versions)}"
            logger.error(error_msg)
            raise GitOperationError(error_msg)

        if check_version:
            logger.info("Version check mode enabled, returning compatible tag and versions")
            return True, tag_name, compatible_versions

        clone_path = os.path.join(base_path, f'kubespray-{tag_name}')
        temp_output_path = os.path.join(base_path, kube_version)
        k8inventory_script = os.path.join(clone_path, "contrib/offline/generate_list.sh")

        command = {
            "generate_templates": f"bash {k8inventory_script} ",
            "copy_files": f"cp -r {clone_path}/contrib/offline/temp {temp_output_path}"
        }
        if not verify_file_exists(k8inventory_script):
            raise FileOperationError(f"Required script missing: {k8inventory_script}")

        # Update YAML variables
        update_success, old_value = update_yaml_variables(clone_path, updates)
        revert_update = {"kube_version": old_value}
        if not update_success:
            raise FileOperationError("Failed to update YAML variables")

        # Update architecture variables
        if not update_arch_variables(clone_path, update_arch):
            raise FileOperationError("Failed to update architecture variables")

        # Execute the generate_list.sh script
        if not execute_command(command["generate_templates"]):
            error_msg = "Failed to execute generate_list.sh"
            logger.error(error_msg)
            raise CommandExecutionError(error_msg)

        if not execute_command(command["copy_files"]):
            error_msg = "Failed to copy generated inventory files"
            logger.error(error_msg)
            raise CommandExecutionError(error_msg)
        # cmd = f"cd {clone_path} && ./contrib/offline/generate_list.sh"
        # execute_command(cmd)

        # Process the generated files
        files_list_path = os.path.join(temp_output_path, "files.list")
        images_list_path = os.path.join(temp_output_path, "images.list")

        updated , old_value = update_yaml_variables(clone_path, revert_update)
        logger.info(f"Reverted the version in yaml file with {revert_update}")
        if not updated:
            error_msg = f"Failed to update old YAML variables in {clone_path}"
            logger.error(error_msg)
            raise FileOperationError(error_msg)

        final_k8s_data = {software_name: {"cluster": []}}

        # Process different package types
        for type_ in SKIP_TYPES:
            try:
                packages = get_k8s_data(type_, k8s_json_path, package_types, software_name)
                final_k8s_data[software_name]["cluster"].extend(packages)
            except Exception as e:
                logger.warning(f"Error processing {type_} packages: {str(e)}")
                continue

        # Process tarballs if in package types
        if "tarball" in package_types:
            filetype_inv = get_k8s_data("tarball", k8s_json_path, package_types, software_name)
            if not process_file_list(files_list_path, filetype_inv, final_k8s_data, software_name):
                raise FileOperationError("Failed to process file list")

        # Process images if in package types
        if "image" in package_types:
            filetype_inv = get_k8s_data("image", k8s_json_path, package_types, software_name)
            if not process_image_list(images_list_path, filetype_inv, final_k8s_data, software_name):
                raise FileOperationError("Failed to process image list")

        # Write final JSON output
        output_json_path = os.path.join(temp_output_path, f"{software_name}_v{kube_version.lstrip('v')}.json")
        write_json(output_json_path, final_k8s_data)

        logger.info(f"Successfully generated JSON for version {kube_version} at {output_json_path}")
        return True, None, compatible_versions

    except Exception as e:
        logger.error(f"Failed to process version {kube_version}: {str(e)}")
        if check_version:
            return False, None, compatible_versions if 'compatible_versions' in locals() else []
        raise

# ============================================================================================
# Ansible Entry Point
# ============================================================================================
def run_module():
    """Run the Ansible module."""
    module_args = {
        "kube_versions": {"type": "list", "required": True},
        "base_path": {"type": "str", "required": True},
        "repo_url": {"type": "str", "required": True},
        "package_types": {"type": "list", "required": True},
        "k8s_json_path": {"type": "str", "required": True},
        "software_name": {"type": "str", "required": True},
        "log_dir": {"type": "str", "required": True},
        "arch": {"type": "str", "required": True},
        "n_latest": {"type": "int", "default": 2},
        "mode": {
            "type": "str", 
            "choices": ["clone", "delete", "both"], 
            "default": "clone"
        },
        "check_version": {
            "type": "bool",
            "default": False
        }
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    try:
        global logger, repo_url
        logger = setup_logging(module.params['log_dir'])
        repo_url = module.params['repo_url']
        
        # Validate required parameters
        if not repo_url:
            module.fail_json(msg="Repository URL is required")

        version_results = {}
        compatible_tags = {}
        compatible_versions_map = {}
        
        for version in module.params['kube_versions']:
            try:
                logger.info(f"Processing Kubernetes version: {version}")
                result, tag_name, compatible_versions = generate_k8_jsons_for_version(
                    version,
                    module.params['base_path'],
                    repo_url,
                    module.params['package_types'],
                    module.params['k8s_json_path'],
                    module.params['arch'],
                    module.params['n_latest'],
                    module.params['software_name'],
                    module.params['mode'],
                    module.params['check_version']
                )
                
                if module.params['check_version']:
                    compatible_tags[version] = tag_name
                    compatible_versions_map[version] = compatible_versions
                    version_results[version] = {
                        'status': 'success' if result else 'failed',
                        'compatible_tag': tag_name,
                        'compatible_versions': compatible_versions
                    }
                else:
                    version_results[version] = {
                        'status': 'success' if result else 'failed',
                        'message': 'Processed successfully' if result else 'Processing failed'
                    }

            except Exception as e:
                error_msg = f"Error processing version {version}: {str(e)}"
                logger.error(error_msg)
                version_results[version] = {
                    'status': 'error',
                    'error': error_msg
                }
                if not module.params['check_version']:
                    module.fail_json(msg=error_msg, version_results=version_results)

        if module.params['check_version']:
            module.exit_json(
                changed=False,
                msg="Version compatibility check completed",
                compatible_tags=compatible_tags,
                compatible_versions=compatible_versions_map,
                version_results=version_results
            )
        else:
            module.exit_json(
                changed=True,
                msg="All versions processed successfully",
                version_results=version_results
            )

    except Exception as e:
        error_msg = f"Unexpected error in run_module: {str(e)}"
        logger.error(error_msg)
        module.fail_json(msg=error_msg)

if __name__ == '__main__':
    run_module()
