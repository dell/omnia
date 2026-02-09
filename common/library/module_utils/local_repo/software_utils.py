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
# pylint: disable=import-error,no-name-in-module,too-many-branches,too-many-statements

"""
This module util contains all custom software utilities used across custom modules
"""
from collections import defaultdict
import os
import json
import csv
import re
import yaml
from jinja2 import Template
import requests
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.common_functions import is_encrypted, process_file, get_arch_from_sw_config
from ansible.module_utils.local_repo.parse_and_download import execute_command
# Import default variables from config.py
from ansible.module_utils.local_repo.config import (
    PACKAGE_TYPES,
    CSV_COLUMNS,
    SOFTWARE_CONFIG_SUBDIR,
    DEFAULT_STATUS_FILENAME,
    RPM_LABEL_TEMPLATE,
    RHEL_OS_URL,
    SOFTWARES_KEY,
    REPO_CONFIG,
    ARCH_SUFFIXES,
    ADDITIONAL_REPOS_KEY,
    pulp_container_commands
)


def load_json(file_path):
    """
    Load JSON data from a file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The loaded JSON data.

    Raises:
        FileNotFoundError: If the file is not found.
        ValueError: If the JSON parsing fails.
    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Error: File '{file_path}' not found.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Error: Failed to parse JSON in file '{file_path}'.") from exc


def load_yaml(file_path):
    """
    Load YAML data from a file.

    Args:
        file_path (str): The path to the YAML file.

    Returns:
        dict: The loaded YAML data.

    Raises:
        FileNotFoundError: If the file is not found.
        yaml.YAMLError: If the YAML parsing fails.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def get_json_file_path(software_name, cluster_os_type,
                       cluster_os_version, user_json_path, arch):
    """
    Generate the file path for a JSON file based on the provided software name,
     cluster OS type, cluster OS version, and user JSON path.

    Parameters:
        software_name (str): The name of the software.
        cluster_os_type (str): The type of the cluster operating system.
        cluster_os_version (str): The version of the cluster operating system.
        user_json_path (str): The path to the user JSON file.
        arch: Architecture for a particular software

    Returns:
        str or None: The file path for the JSON file if it exists, otherwise None.
    """
    base_path = os.path.dirname(os.path.abspath(user_json_path))
    json_path = os.path.join(base_path,
            f'{SOFTWARE_CONFIG_SUBDIR}/{arch}/{cluster_os_type}/{cluster_os_version}/{software_name}.json'
        )
    return json_path


def get_csv_file_path(software_name, user_csv_dir, arch):
    """
    Generates the absolute path of the CSV file based on the software name
    and the user-provided CSV directory.

    Parameters:
        software_name (str): The name of the software.
        user_csv_dir (str): The directory path where the CSV file is located.
        arch: Architecture of the software

    Returns:
        str: The absolute path of the CSV file if it exists, otherwise None.
    """
    status_csv_file_path = os.path.join(
          user_csv_dir, arch, software_name, DEFAULT_STATUS_FILENAME
        )
    return status_csv_file_path


def is_remote_url_reachable(remote_url, timeout=10,
                            client_cert=None, client_key=None, ca_cert=None):
    """
    Check if a remote URL is reachable with or without SSL client certs.
    If SSL certs are provided, the function will attempt to use them; otherwise,
    it defaults to a standard HTTP request.
    Args:
        remote_url (str): The URL to check for reachability.
        timeout (int, optional): The maximum number of seconds to wait for a response.
        Defaults to 10.
        client_cert (str, optional): Path to the client certificate file. Defaults to None.
        client_key (str, optional): Path to the client key file. Defaults to None.
        ca_cert (str, optional): Path to the CA certificate file. Defaults to None.
    Returns:
        bool: True if the URL is reachable (HTTP status 200), False otherwise.
    """
    try:
        # Check if SSL certs are provided and handle accordingly
        if client_cert and client_key and ca_cert:
            response = requests.get(
                remote_url,
                cert=(client_cert, client_key),
                verify=ca_cert,
                timeout=timeout
            )
        else:
            # Proceed with a regular HTTP request if no SSL certs are provided
            response = requests.get(remote_url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

def transform_package_dict(data, arch_val,logger):
    """
    Transforms a dictionary of packages and organizes them by architecture.

    Args:
        data (dict): Dictionary of packages where each key is a software name,
                     and each value is a list of package dicts.
        arch_val: Current architecture being parsed for the software
        logger (logging.Logger): Logger instance used for structured logging of process steps.

    Returns:
        dict: A dictionary where each key is an architecture (e.g., 'x86_64', 'aarch64'),
              and each value is a dictionary of software mapped to their transformed task list.
    """
    result = defaultdict(dict)

    for sw_name, items in data.items():
        transformed_items = []
        rpm_packages = []
        repo_mapping = {}

        for item in items:
            if item.get("type") == "rpm":
                rpm_packages.append(item["package"])
                # Preserve repo_name if available
                if "repo_name" in item:
                    repo_mapping[item["package"]] = item["repo_name"]
            elif item.get("type") == "rpm_list":
                rpm_packages.extend(item["package_list"])
                # Preserve repo_mapping if available
                if "repo_mapping" in item:
                    repo_mapping.update(item["repo_mapping"])
            else:
                transformed_items.append(item)

        if rpm_packages:
            rpm_task = {
                "package": RPM_LABEL_TEMPLATE.format(key=sw_name),
                "rpm_list": rpm_packages,
                "type": "rpm"
            }
            # Add repo_mapping if we have any
            if repo_mapping:
                rpm_task["repo_mapping"] = repo_mapping
            transformed_items.append(rpm_task)

        result[arch_val][sw_name] = transformed_items
        logger.info(f"Finished processing %s. Result: %s", sw_name, transformed_items)

    final_result = dict(result)
    logger.info("Transformation complete for arch '%s'. Final result keys: %s", arch_val, list(final_result.keys()))
    return final_result


def parse_repo_urls(repo_config, local_repo_config_path,
                    version_variables, vault_key_path, sub_urls,logger,sw_archs=None):
    """
    Parses the repository URLs from the given local repository configuration file.
    Args:
        repo_config (str): Repo configuration
        local_repo_config_path (str): The path to the local repository configuration file.
        version_variables (dict): A dictionary of version variables.
        vault_key_path: Ansible vault key path
        sub_urls (dict): Mapping of architectures to subscription URLs that override 
                         default RHEL URLs when provided.
        logger (logging.Logger): Logger instance used for structured logging of process steps.
        sw_archs (list, optional): List of architectures to process based on software_config.json.
                                   If None, defaults to ARCH_SUFFIXES.
    Returns:
        tuple: A tuple where the first element is either the parsed repository URLs as a JSON string
               (on success) or the rendered URL (if unreachable),
                and the second element is a boolean
               indicating success (True) or failure (False).
        str: The parsed repository URLs as a JSON string.
    """
    local_yaml = load_yaml(local_repo_config_path)
    repo_entries = {}
    user_repo_entry = {}
    rhel_repo_entry = {}

    archs_to_process = sw_archs if sw_archs else ARCH_SUFFIXES
    logger.info(f"Processing repository URLs for architectures: {archs_to_process}")

    for arch in archs_to_process:

        # Always ensure these are lists
        rhel_repo_entry[arch] = list(local_yaml.get(f"rhel_os_url_{arch}") or [])
        repo_entries[arch] = list(local_yaml.get(f"omnia_repo_url_rhel_{arch}") or [])
        user_repo_entry[arch] = list(local_yaml.get(f"user_repo_url_{arch}") or [])
        # In case of Subscription, Subscription URLs take precedence if present and non-empty
        if sub_urls and arch in sub_urls and sub_urls[arch]:
            logger.info(f"Subscription URLs detected for arch {arch}. Overriding RHEL URLs.")
            if not isinstance(rhel_repo_entry.get(arch), list):
                rhel_repo_entry[arch] = []
            rhel_repo_entry[arch] = list(sub_urls[arch])
            logger.info(f" Updated RHEL URLs: {rhel_repo_entry[arch]}")

    parsed_repos = []
    vault_key_path = os.path.join(
        vault_key_path, ".local_repo_credentials_key")

    # Handle user repositories
    for arch, repo_list in user_repo_entry.items():
        if not repo_list:
            logger.info(f"No user repository entries found for {arch}")
            continue
        for url_ in repo_list:
            name = url_.get("name", "unknown")
            url = url_.get("url", "")
            gpgkey = url_.get("gpgkey", "")
            ca_cert = url_.get("sslcacert", "")
            client_key = url_.get("sslclientkey", "")
            client_cert = url_.get("sslclientcert", "")
            policy_given = url_.get("policy", repo_config)
            policy = REPO_CONFIG.get(policy_given)

            logger.info(f"Processing user repo '{name}' for arch '{arch}' - URL: {url}")

            for path in [ca_cert, client_key, client_cert]:
                mode = "decrypt"
                if path and is_encrypted(path):
                    result, message = process_file(path, vault_key_path, mode)
                    if result is False:
                        logger.error(f"Decryption failed for user repo path: {path} | Error: {message}")
                        return f"Error during decrypt for user repository path:{path}", False

            if not is_remote_url_reachable(url, client_cert=client_cert,
                                           client_key=client_key, ca_cert=ca_cert):
                logger.error(f"User repo URL unreachable: {url}")
                return url, False

            parsed_repos.append({
                "package": name,
                "url": url,
                "gpgkey": gpgkey if gpgkey else "null",
                "version": "null",
                "ca_cert": ca_cert,
                "client_key": client_key,
                "client_cert": client_cert,
                "policy": policy,
                "sw_arch": arch
            })

            logger.info(f"Added user repo entry: {name}")

    # Handle RHEL repositories
    for arch, repo_list in rhel_repo_entry.items():
        for url_ in repo_list:
            name = url_.get("name", "unknown")
            url = url_.get("url", "")
            gpgkey = url_.get("gpgkey", "")
            ca_cert = url_.get("sslcacert", "")
            client_key = url_.get("sslclientkey", "")
            client_cert = url_.get("sslclientcert", "")
            policy_given = url_.get("policy", repo_config)
            policy = REPO_CONFIG.get(policy_given)

            logger.info(f"Processing RHEL repo '{name}' for arch '{arch}' - URL: {url}")

            for path in [ca_cert, client_key, client_cert]:
                mode = "decrypt"
                if path and is_encrypted(path):
                    result, message = process_file(path, vault_key_path, mode)
                    if result is False:
                        logger.error(f"Decryption failed for RHEL repo path: {path} | Error: {message}")
                        return f"Error during decrypt for rhel repository path:{path}", False

            if not is_remote_url_reachable(url, client_cert=client_cert,
                                           client_key=client_key, ca_cert=ca_cert):
                logger.error(f"RHEL repo URL unreachable: {url}")
                return url, False

            # if not is_remote_url_reachable(url):
            #     return url, False

            parsed_repos.append({
                "package": name,
                "url": url,
                "gpgkey": gpgkey if gpgkey else "null",
                "version": "null",
                "ca_cert": ca_cert,
                "client_key": client_key,
                "client_cert": client_cert,
                "policy": policy,
                "sw_arch": arch
            })
            logger.info(f"Added RHEL repo entry: {name}")

    # Handle OMNIA repositories
    seen_urls = set()
    for arch, entries in repo_entries.items():
        if not entries:
            logger.info(f"No OMNIA repository entries found for {arch}")
            continue

        for repo in entries:
            name = repo.get("name", "unknown")
            url = repo.get("url", "")
            gpgkey = repo.get("gpgkey", "")
            policy_given = repo.get("policy", repo_config)
            policy = REPO_CONFIG.get(policy_given)
            logger.info(f"Processing OMNIA repo '{name}' for arch '{arch}' - Template URL: {url}")

            # Find unresolved template vars in URL
            template_vars_url = re.findall(r"{{\s*(\w+)\s*}}", url)
            unresolved_url = [var for var in template_vars_url if var not in version_variables]
            if unresolved_url:
                logger.info(f"Unresolved template vars in URL '{url}': {unresolved_url}")
                continue

            try:
                rendered_url = Template(url).render(version_variables)
            except Exception:
                logger.error(f"Failed to render URL template '{url}' | Error: {e}")
                rendered_url = url  # fallback

            if rendered_url in seen_urls:
                logger.info(f"Skipping duplicate URL: {rendered_url}")
                continue
            seen_urls.add(rendered_url)

            # # Skip reachability check for URLs containing k8s, cri-o, oneapi, snoopy, nvidia
            if not any(skip_str in rendered_url for skip_str in ["k8s", "cri-o", "oneapi", "snoopy", "nvidia"]):
                if not is_remote_url_reachable(rendered_url):
                    logger.error(f"OMNIA repo URL unreachable: {rendered_url}")
                    return rendered_url, False

            # Handle gpgkey rendering (if present)
            rendered_gpgkey = "null"
            if gpgkey:
                template_vars_gpg = re.findall(r"{{\s*(\w+)\s*}}", gpgkey)
                unresolved_gpg = [var for var in template_vars_gpg if var not in version_variables]
                if unresolved_gpg:
                    continue

                try:
                    rendered_gpgkey = Template(gpgkey).render(version_variables)
                except Exception:
                    rendered_gpgkey = gpgkey  # fallback to original

            sw_name = f"{arch}_{name}"
            version = "null"
            for var in template_vars_url:
                if var in version_variables:
                    version = version_variables[var]
                    break

            parsed_repos.append({
                "package": sw_name,
                "url": rendered_url,
                "gpgkey": rendered_gpgkey,
                "version": version if version else "null",
                "policy": policy,
                "sw_arch": arch
            })
            logger.info(f"Added OMNIA repo entry: {arch}_{name}")

    logger.info(f"Successfully parsed {len(parsed_repos)} repository entries.")
    return parsed_repos, True

def set_version_variables(user_data, software_names, cluster_os_version,logger):
    """
    Generates a dictionary of version variables from the user data.
    Args:
        user_data (dict): The user data containing the software information.
        software_names (list): The list of software names to extract versions for.
        cluster_os_version (str): The version of the cluster operating system.
        logger (logging.Logger): Logger instance used for structured logging of process steps.
    Returns:
        dict: A dictionary of version variables, where the keys are the software names
              and the values are the corresponding versions.
    """
    version_variables = {}

    for software in user_data.get(SOFTWARES_KEY, []):
        name = software.get('name')
        if name in software_names and 'version' in software:
            version_variables[f"{name}_version"] = software['version']
            logger.info("Added version variable from SOFTWARES_KEY: %s = %s", f"{name}_version", software['version'])

    for key in software_names:
        for item in user_data.get(key, []):
            name = item.get('name')
            if 'version' in item:
                version_variables[f"{name}_version"] = item['version']

    version_variables["cluster_os_version"] = cluster_os_version
    logger.info("Added cluster_os_version: %s", cluster_os_version)

    logger.info("Version variables generated: %s", version_variables)
    return version_variables


def get_subgroup_dict(user_data,logger):
    """
    Returns a tuple containing a dictionary mapping software names to subgroup lists,
    and a list of software names.
    """
    logger.info("Starting get_subgroup_dict()")
    subgroup_dict = {}
    software_names = []

    for sw in user_data.get(SOFTWARES_KEY, []):
        software_name = sw['name']
        software_names.append(software_name)
        subgroups = [sw['name']] + [item['name']
                                    for item in user_data.get(software_name, [])]
        subgroup_dict[software_name] = subgroups if isinstance(
            user_data.get(software_name), list) else [sw['name']]

    logger.info("Completed get_subgroup_dict(). Found %d software entries.", len(software_names))
    logger.info("Final subgroup_dict: %s", subgroup_dict)

    return subgroup_dict, software_names


def get_csv_software(file_name):

    """

    Retrieves a list of software names from a CSV file.
 
    Parameters:

        file_name (str): The name of the CSV file.
 
    Returns:

        list: A list of software names.

    """

    csv_software = []

    if not os.path.isfile(file_name):
        return csv_software

    with open(file_name, mode='r') as csv_file:
        reader = csv.DictReader(csv_file)
        csv_software = [row.get(CSV_COLUMNS["column1"], "").strip()
                        for row in reader]

    return csv_software


def get_failed_software(file_path):
    """
    Retrieves a list of failed software from a CSV file.

    Parameters:
        file_path (str): The filepath of the status.csv file.

    Returns:
        list: A list of software names that failed.
    """
    failed_software = []

    if not os.path.isfile(file_path):
        return failed_software

    with open(file_path, mode='r') as csv_file:
        reader = csv.DictReader(csv_file)
        failed_software = [
            str(row.get(CSV_COLUMNS["column1"]) or "").strip()
            for row in reader
            if str(row.get(CSV_COLUMNS["column2"]) or "").strip().lower() in ["", "failed"]
    ]
    return failed_software

def check_additional_image_in_pulp(image_entry, logger):
    """
    Checks if image present in additional_packages.json is configured in Pulp.
    """
    image_name = image_entry.get("package")
    image_tag = image_entry.get("tag", None)
    image_digest = image_entry.get("digest", None)

    logger.info("Checking if %s is present in Pulp", image_name)

    dist_name_prefix = "container_repo_"
    transformed_dist_name = (f"{dist_name_prefix}{image_name.replace('/', '_').replace(':', '_')}")

    repo_href_result = None
    latest_version_href_result = None
    tags_output_result = None

    show_dist_cmd = (pulp_container_commands["container_distribution_show"] % transformed_dist_name)
    repo_href_result = execute_command(show_dist_cmd, logger)
    logger.info("repo_href_result: %s", repo_href_result)

    if repo_href_result.get("stderr") and "Error:" in repo_href_result.get("stderr", ""):
        logger.info("Distribution %s not found in Pulp", transformed_dist_name)
        return {
            "type": "image",
            "package": image_name,
            "tag": image_tag,
        }
    else:
        logger.info("Distribution %s found in Pulp", transformed_dist_name)
        repo_href = repo_href_result["stdout"]
        show_repo_cmd = (pulp_container_commands["show_repository_version"] % repo_href)
        latest_version_href_result = execute_command(show_repo_cmd, logger)
        logger.info("latest_version_href_result: %s", latest_version_href_result)
        if latest_version_href_result.get("stderr") and "Error:" in latest_version_href_result.get("stderr", ""):
            logger.info("No repository version found. Empty repository")
            return {
                "type": "image",
                "package": image_name,
                "tag": image_tag,
            }
        else:
            logger.info("Repository version found in Pulp")
            latest_version_href = latest_version_href_result["stdout"]
            show_tags_cmd = (pulp_container_commands["list_image_tags"] % latest_version_href)
            tags_output_result = execute_command(show_tags_cmd, logger, type_json=True)
            logger.info("tags_output_result: %s", tags_output_result)
            if tags_output_result.get("stderr") and "Error:" in tags_output_result.get("stderr", ""):
                logger.info("No tags found for %s", image_name)
                return {
                    "type": "image",
                    "package": image_name,
                    "tag": image_tag,
                }
            else:
                logger.info("Tags found for %s", image_name)
                tag_names = [tag["name"] for tag in tags_output_result.get("stdout", {}).get("results", [])]
                logger.info("tag_names: %s", tag_names)
                if image_tag and image_tag not in tag_names:
                    logger.info("Tag %s not found for image %s in Pulp", image_tag, image_name)
                    return {
                        "type": "image",
                        "package": image_name,
                        "tag": image_tag,
                    }
                elif image_digest and image_digest not in tag_names:
                    logger.info("Digest %s not found for image %s in Pulp", image_digest, image_name)
                    return {
                        "type": "image",
                        "package": image_name,
                        "tag": image_digest,
                    }
                else:
                    logger.info("No download required as image is already present in Pulp")
                    return {}

def parse_json_data(file_path, package_types,logger, failed_list=None, subgroup_list=None):
    """
    Retrieves a filtered list of items from a JSON file.

    Parameters:
        file_path (str): The path to the JSON file.
        package_types (list): A list of package types to filter.
        logger (logging.Logger): Logger instance used for structured logging of process steps.
        failed_list (list, optional): A list of failed packages. Defaults to None.
        subgroup_list (list, optional): A list of subgroups to filter. Defaults to None.

    Returns:
        list: The filtered list of items.
    """
    logger.info("Starting parse_json_data() for file: %s", file_path)
    try:
        data = load_json(file_path)
        logger.info("Successfully loaded JSON file: %s", file_path)
    except Exception as e:
        logger.error("Failed to load JSON file '%s': %s", file_path, e)
        raise

    filtered_list = []

    # Check if file name is additional_packages.json
    is_additional_packages = file_path.endswith("additional_packages.json")
    logger.info("additional_packages present: %s", is_additional_packages)

    for key, package in data.items():
        if subgroup_list is None or key in subgroup_list:
            for value in package.values():
                for item in value:
                    # For every image, check if it is present in Pulp
                    if is_additional_packages and item.get("type") == "image":
                        logger.info("Calling function to check %s existence in Pulp", item)
                        tag_missing_entry = check_additional_image_in_pulp(item, logger)
                        logger.info("tag_missing_entry: %s", tag_missing_entry)
                        if tag_missing_entry == {}:
                            continue
                        if tag_missing_entry:
                            filtered_list.append(tag_missing_entry)
                        continue

                    # Get package name
                    pkg_name = item.get("package")

                    # Construct possible match keys based on available fields
                    match_keys = {pkg_name}  # Base case: package name only

                    if "tag" in item and item["tag"]:
                        # Add package:tag
                        match_keys.add(f"{pkg_name}:{item['tag']}")

                    if "digest" in item and item["digest"]:
                        # Add package:digest
                        match_keys.add(f"{pkg_name}:{item['digest']}")

                    # Apply filtering
                    if item.get("type") in package_types and (failed_list is None or any(match in failed_list for match in match_keys)):
                        filtered_list.append(item)

    logger.info("Final filtered list: %s", filtered_list)
    return filtered_list


def check_csv_existence(path):
    """
    Checks if a CSV file exists at the given path.

    Parameters:
        path (str): The path to the CSV file.

    Returns:
        bool: True if the CSV file exists, False otherwise.
    """
    if isinstance(path, str):
        return os.path.isfile(path)

def read_status_csv(csv_path):
    """Reads the status.csv file and returns a list of row dictionaries."""
    with open(csv_path, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]

def get_new_packages_not_in_status(json_path, csv_path, subgroup_list,logger):
    """
    Reads packages from a JSON file and status rows from a CSV file,
    then returns packages from JSON that are not present in the CSV.
    Handles grouped RPM entries like 'RPMs for <group>'.
    
    Parameters:
        json_path (str): Path to JSON file containing 'all_input_packages'.
        csv_path (str): Path to CSV file containing status rows.
        subgroup_list (list, optional): A list of subgroups to filter. Defaults to None.
        logger (logging.Logger): Logger instance used for structured logging of process steps.
    
    Returns:
        list: List of new packages not in the status CSV.
    """

    all_packages = []
    new_packages = []

    try:
        status_csv_content = read_status_csv(csv_path)
        logger.info("Successfully read status CSV: %s", csv_path)
    except Exception as e:
        logger.error("Failed to read CSV file '%s': %s", csv_path, e)
        raise

    names = [row['name'] for row in status_csv_content]
    # Read all packages from JSON
    try:
        all_packages = parse_json_data(json_path, PACKAGE_TYPES, logger,None, subgroup_list)
        logger.info("Total packages loaded from JSON: %d", len(all_packages))
    except Exception as e:
        logger.error("Failed to parse JSON file '%s': %s", json_path, e)
        raise

    for pkg in all_packages:
        if pkg["type"] == "image":
            # Check exact package:tag or package:digest combination
            pkg_base = pkg.get("package", "").strip()
            pkg_identifier = pkg_base

            if "tag" in pkg:
                pkg_identifier += f":{pkg['tag']}"
            elif "digest" in pkg:
                pkg_identifier += f":{pkg['digest']}"

            if pkg_identifier not in names:
                new_packages.append(pkg)
        else:
            if pkg.get("package") not in names:
                new_packages.append(pkg)
    logger.info("New packages list: %s", new_packages)

    logger.info("Finished get_new_packages_not_in_status()")

    return new_packages

def process_software(software, fresh_installation, json_path, csv_path, subgroup_list,logger):
    """
    Processes the given software by parsing JSON data and returning a filtered list of items.
 
    Parameters:
        software (str): The name of the software.
        fresh_installation (bool): Indicates whether it is a fresh installation.
        json_path (str): The path to the JSON file.
        csv_path (str): The path to the CSV file.
        subgroup_list (list, optional): A list of subgroups to filter. Defaults to None.
        logger (logging.Logger): Logger instance used for structured logging of process steps.
 
    Returns:
        list: The filtered list of items.
    """
    # Determine failed packages
    if fresh_installation:
        failed_packages = None
        logger.info("Fresh installation detected — skipping failed package check.")
    else:
        try:
            failed_packages = None if fresh_installation else get_failed_software(csv_path)
            logger.info("Failed packages: %s", failed_packages)
        except Exception as e:
            logger.error("Failed to retrieve failed packages from '%s': %s", csv_path, e)
            raise
    rpm_package_type = ['rpm']
    rpm_tasks = []
    if failed_packages is not None and any("RPMs" in software for software in failed_packages):
        logger.info("Detected failed RPM packages for software: %s", software)
        try:
            rpm_tasks = parse_json_data(
                json_path, rpm_package_type, logger, None, subgroup_list)
        except Exception as e:
            logger.error("Error parsing RPM JSON data from '%s': %s", json_path, e)
            raise
    else:
        logger.info("No failed RPM packages found for: %s", software)

    # Parse main JSON data
    try:
        combined = parse_json_data(
            json_path, PACKAGE_TYPES,logger,failed_packages, subgroup_list) + rpm_tasks
        logger.info("Successfully parsed JSON data for %s. Total combined tasks: %d",software, len(combined))
    except Exception as e:
        logger.error("Error parsing main JSON data for '%s': %s", software, e)
        raise

    logger.info("Completed process_software() for %s", software)
    logger.info("Final combined tasks: %s", combined)

    return combined, failed_packages

def get_software_names(json_file_path):
    with open(json_file_path, "r") as f:
        data = json.load(f)

    softwares = data.get("softwares", [])
    return softwares

def get_software_names_and_arch(json_data, arch):
    softwares = json_data.get("softwares", [])
    result = []
    sw_arch_dict = {}

    for sw in softwares:
        sw_arch_dict = get_arch_from_sw_config(sw["name"],json_data)
        sw_arch = sw_arch_dict[sw["name"]]
        if arch in sw_arch:
            result.append(sw["name"])

    return result

def remove_duplicates_from_trans(trans):
    """
    Remove duplicate software entries from the transform output.
    The function modifies the input `trans` dictionary in-place and also returns it.
    Args:
        trans (dict): Dictionary returned from `transform_package_dict()` containing
                      architecture → software groups → package lists.
    Returns:
        dict: Deduplicated `trans` dictionary with unique package entries preserved.
    """

    for arch, groups in trans.items():
        for group, items in groups.items():

            if group == "default_packages":  # Handle nested rpm_list case
                for pkg in items:
                    if pkg.get("type") == "rpm" and "rpm_list" in pkg:
                        pkg["rpm_list"] = list(dict.fromkeys(pkg["rpm_list"]))
                continue

            unique = {}
            cleaned = []

            for item in items:
                type_ = item.get("type")

                if type_ == "image":
                    # Use digest if present, otherwise use tag
                    identifier = item.get("digest") or item.get("tag")
                    key = (item.get("package"), identifier)

                elif type_ == "pip_module":
                    key = item.get("package")

                elif type_ in ["tarball", "manifest"]:
                    key = item.get("url") or item.get("package")

                elif type_ == "git":
                    key = (item.get("url"), item.get("version"))

                elif type_ == "rpm" and "rpm_list" in item:
                    item["rpm_list"] = list(dict.fromkeys(item["rpm_list"]))
                    key = item.get("package")

                else:
                    key = str(item)

                if key not in unique:
                    unique[key] = True
                    cleaned.append(item)

            groups[group] = cleaned

    return trans


def parse_additional_repos(local_repo_config_path, repo_config, vault_key_path, logger):
    """
    Parses additional repository URLs from the local repository configuration file.
    These repos are aggregated into a single Pulp repository per architecture.

    Args:
        local_repo_config_path (str): The path to the local repository configuration file.
        repo_config (str): Global repo configuration policy from software_config.json.
        vault_key_path (str): Ansible vault key path for decrypting SSL certificates.
        logger (logging.Logger): Logger instance for structured logging.

    Returns:
        tuple: (additional_repos_config, error_message)
            - additional_repos_config (dict): Dictionary with arch as key and list of repo configs as value.
            - error_message (str or None): Error message if validation fails, None otherwise.
    """
    logger.info("Starting parse_additional_repos()")
    local_yaml = load_yaml(local_repo_config_path)

    additional_repos_config = {}
    policy = REPO_CONFIG.get(repo_config, "on_demand")

    vault_key_full_path = os.path.join(vault_key_path, ".local_repo_credentials_key")

    for arch in ARCH_SUFFIXES:
        key = f"{ADDITIONAL_REPOS_KEY}_{arch}"
        repo_list = local_yaml.get(key) or []

        if not repo_list:
            logger.info(f"No additional repos found for {arch}")
            additional_repos_config[arch] = []
            continue

        # Validate for duplicate names within this arch
        names_seen = set()
        for repo in repo_list:
            name = repo.get("name", "")
            if name in names_seen:
                error_msg = f"Duplicate name '{name}' found in {key}. Each repo must have a unique name."
                logger.error(error_msg)
                return None, error_msg
            names_seen.add(name)

        parsed_repos = []
        for repo in repo_list:
            name = repo.get("name", "unknown")
            url = repo.get("url", "")
            gpgkey = repo.get("gpgkey", "")
            ca_cert = repo.get("sslcacert", "")
            client_key = repo.get("sslclientkey", "")
            client_cert = repo.get("sslclientcert", "")

            logger.info(f"Processing additional repo '{name}' for arch '{arch}' - URL: {url}")

            # Decrypt SSL certificates if encrypted
            for path in [ca_cert, client_key, client_cert]:
                if path and is_encrypted(path):
                    result, message = process_file(path, vault_key_full_path, "decrypt")
                    if result is False:
                        error_msg = f"Decryption failed for additional repo path: {path} | Error: {message}"
                        logger.error(error_msg)
                        return None, error_msg

            # Check URL reachability
            if not is_remote_url_reachable(url, client_cert=client_cert,
                                           client_key=client_key, ca_cert=ca_cert):
                error_msg = f"Additional repo URL unreachable: {url}"
                logger.error(error_msg)
                return None, error_msg

            parsed_repos.append({
                "name": name,
                "url": url,
                "gpgkey": gpgkey if gpgkey else "",
                "ca_cert": ca_cert,
                "client_key": client_key,
                "client_cert": client_cert,
                "policy": policy,
                "arch": arch
            })
            logger.info(f"Added additional repo entry: {name}")

        additional_repos_config[arch] = parsed_repos

    logger.info(f"Successfully parsed additional repos. x86_64: {len(additional_repos_config.get('x86_64', []))}, "
                f"aarch64: {len(additional_repos_config.get('aarch64', []))}")
    return additional_repos_config, None


def validate_additional_repos_names(local_repo_config_path, logger):
    """
    Validates that names in additional_repos_* do not conflict with names in other repo keys.

    Args:
        local_repo_config_path (str): The path to the local repository configuration file.
        logger (logging.Logger): Logger instance for structured logging.

    Returns:
        tuple: (is_valid, error_message)
            - is_valid (bool): True if validation passes, False otherwise.
            - error_message (str or None): Error message if validation fails, None otherwise.
    """
    logger.info("Starting validate_additional_repos_names()")
    local_yaml = load_yaml(local_repo_config_path)

    # Keys to check for conflicts
    other_repo_keys = {
        "x86_64": ["user_repo_url_x86_64", "rhel_os_url_x86_64", "omnia_repo_url_rhel_x86_64"],
        "aarch64": ["user_repo_url_aarch64", "rhel_os_url_aarch64", "omnia_repo_url_rhel_aarch64"]
    }

    for arch in ARCH_SUFFIXES:
        additional_key = f"{ADDITIONAL_REPOS_KEY}_{arch}"
        additional_repos = local_yaml.get(additional_key) or []

        if not additional_repos:
            continue

        # Get all names from additional_repos for this arch
        additional_names = {repo.get("name", "") for repo in additional_repos if repo.get("name")}

        # Check against other repo keys for the same arch
        for other_key in other_repo_keys.get(arch, []):
            other_repos = local_yaml.get(other_key) or []
            for repo in other_repos:
                other_name = repo.get("name", "")
                if other_name in additional_names:
                    error_msg = (f"Name '{other_name}' in {additional_key} conflicts with "
                                 f"existing repo name in {other_key}. Please use a unique name.")
                    logger.error(error_msg)
                    return False, error_msg

    logger.info("Additional repos name validation passed.")
    return True, None
