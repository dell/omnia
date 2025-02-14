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

import os
import json
import csv
import yaml
from collections import defaultdict
import re
from jinja2 import Template
 
 
PACKAGE_TYPES = ['rpm', 'deb', 'tarball', 'image', 'manifest', 'git',
                 'pip_module', 'deb', 'shell', 'ansible_galaxy_collection', 'iso']
 
# PACKAGE_TYPES = ["rpm"]
CSV_COLUMNS = {"column1": "name", "column2": "status"}
 
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
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: File '{file_path}' not found.")
    except json.JSONDecodeError:
        raise ValueError(f"Error: Failed to parse JSON in file '{file_path}'.")
 
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
 
 
def get_json_file_path(software_name, cluster_os_type, cluster_os_version, user_json_path):
    """
    Generate the file path for a JSON file based on the provided software name, cluster OS type, cluster OS version, and user JSON path.
 
    Parameters:
        software_name (str): The name of the software.
        cluster_os_type (str): The type of the cluster operating system.
        cluster_os_version (str): The version of the cluster operating system.
        user_json_path (str): The path to the user JSON file.
 
    Returns:
        str or None: The file path for the JSON file if it exists, otherwise None.
    """
    base_path = os.path.dirname(os.path.abspath(user_json_path))
    json_path = os.path.join(base_path, f'config/{cluster_os_type}/{cluster_os_version}/{software_name}.json')
    if json_path and os.path.exists(json_path):
        return json_path
    return None
 
def get_csv_file_path(software_name, user_csv_dir):
    """
    Generates the absolute path of the CSV file based on the software name and the user-provided CSV directory.
    
    Parameters:
        software_name (str): The name of the software.
        user_csv_dir (str): The directory path where the CSV file is located.
    
    Returns:
        str: The absolute path of the CSV file if it exists, otherwise None.
    """
    absolute_path = os.path.join(os.getcwd(), user_csv_dir)
    user_abs_dir = os.path.dirname(absolute_path)
    csv_file_path = f'{user_abs_dir}/log/{software_name}/status.csv'
    if os.path.exists(csv_file_path):
        return csv_file_path
 
 
def transform_package_dict(data):
    """
    Transforms a dictionary of packages into a new dictionary.

    Args:
        data (dict): A dictionary of packages, where each key is a string and
                     each value is a list of dictionaries. Each dictionary in
                     the list represents a package and contains the following
                     keys: "type" (a string) and "package" (a string).

    Returns:
        dict: A new dictionary where each key is a string and each value is
              a list of dictionaries. Each dictionary in the list represents
              a package and contains the following keys: "type" (a string),
              "package" (a string), and "rpm_list" (a list of strings) if the
              package type is "rpm".
    """
    result = {}
    rpm_packages = defaultdict(list)
 
    for key, items in data.items():
        transformed_items = []
 
        for item in items:
            if item.get("type") == "rpm":
                rpm_packages[key].append(item["package"])
            else:
                transformed_items.append(item)
 
        if rpm_packages[key]:
            transformed_items.append({
                "package": f"RPMs for {key}",
                "rpm_list": rpm_packages[key],
                "type": "rpm"
            })
 
        result[key] = transformed_items
 
    return result
 
def parse_repo_urls(local_repo_config_path, version_variables):
    """
    Parses the repository URLs from the given local repository configuration file.

    Args:
        local_repo_config_path (str): The path to the local repository configuration file.
        version_variables (dict): A dictionary of version variables.

    Returns:
        str: The parsed repository URLs as a JSON string.

    """
    
    local_yaml = load_yaml(local_repo_config_path)
    repo_entries = local_yaml.get("omnia_repo_url_rhel", [])
    parsed_repos = []
 
    for repo in repo_entries:
        name = repo.get("name", "unknown")  # Default name
        url = repo.get("url", "")  # Default to empty string if missing
        gpgkey = repo.get("gpgkey")  # Default is None (no need to specify explicitly)
        version = version_variables.get(f"{name}_version")  # Extract version dynamically
 
        # Render URL using Jinja2 templating
        try:
            rendered_url = Template(url).render(version_variables)
        except Exception as e:
            print(f"Warning: Error rendering URL {url} - {str(e)}")
            rendered_url = url  # Fallback to original URL
 
        parsed_repos.append({
            "package": name,
            "url": rendered_url,
            "gpgkey": gpgkey if gpgkey else "null",  # Ensure None if empty
            "version": version if version else "null"  # Ensure None if empty
        })
 
    return json.dumps(parsed_repos)
 
 
def set_version_variables(user_data, software_names, cluster_os_version):
    """
    Generates a dictionary of version variables from the user data.

    Args:
        user_data (dict): The user data containing the software information.
        software_names (list): The list of software names to extract versions for.
        cluster_os_version (str): The version of the cluster operating system.

    Returns:
        dict: A dictionary of version variables, where the keys are the software names
              and the values are the corresponding versions.
    """

    version_variables = {}
 
    # Iterate through 'softwares' to extract versions
    for software in user_data.get('softwares', []):
        name = software.get('name')
        if name in software_names and 'version' in software:
            version_variables[f"{name}_version"] = software['version']
 
    # Iterate through subgroup keys and extract versions
    for key in software_names:
        for item in user_data.get(key, []):
            name = item.get('name')
            if 'version' in item:
                version_variables[f"{name}_version"] = item['version']
    version_variables["cluster_os_version"] = cluster_os_version
    return version_variables
 
def get_subgroup_dict(user_data):
    """
    Returns a dictionary and a list. The dictionary contains the subgroup names as keys and a list of
    subgroups as values. The list contains the names of the softwares.

    Parameters:
        user_data (dict): A dictionary containing the user data.

    Returns:
        tuple: A tuple containing the subgroup dictionary and the list of software names.
    """

    subgroup_dict = {}
    software_names=[]
    for sw in user_data.get('softwares', []):
            software_name = sw['name']
            software_names.append(software_name)
            subgroups = [sw['name']] + [item['name'] for item in user_data.get(software_name, [])]
            subgroup_dict[software_name] = subgroups if isinstance(user_data.get(software_name), list) else [sw['name']]
    return subgroup_dict , software_names
 
def get_failed_software(file_name):
    """
    Retrieves a list of failed software from a CSV file.
 
    Parameters:
        file_name (str): The name of the CSV file.
 
    Returns:
        list: A list of failed software.
    """
    failed_software = []
 
    if not os.path.isfile(file_name):  # Check before opening
        return failed_software
 
    with open(file_name, mode='r') as csv_file:
        reader = csv.DictReader(csv_file)
        failed_software = [row.get(CSV_COLUMNS["column1"], "").strip()
                           for row in reader
                           if row.get(CSV_COLUMNS["column2"], "").strip().lower() == "failed"]
 
    return failed_software
 
def parse_json_data(file_path, package_types, failed_list=None, subgroup_list=None):
    """
    Retrieves a filtered list of items from a JSON file.
 
    Parameters:
        file_path (str): The path to the JSON file.
        package_types (list): A list of package types to filter.
        failed_list (list, optional): A list of failed packages to filter. Defaults to None.
        subgroup_list (list, optional): A list of subgroups to filter. Defaults to None.
 
    Returns:
        list: The filtered list of items.
    """
    data = load_json(file_path)
    filtered_list = []
 
    for key, package in data.items():  # k8s
        if subgroup_list is None or key in subgroup_list:
            for value in package.values():  # cluster
                filtered_list.extend([
                    item for item in value  # dict
                    if item.get("type") in package_types and
                    (failed_list is None or item.get("package") in failed_list)
                ])
 
    return filtered_list
 
def check_csv_existence(software, path):
    """
    Checks if a CSV file exists for a given software.
 
    Parameters:
        software (str): The name of the software.
        path (str): The path to the CSV file.
 
    Returns:
        bool: True if the CSV file exists, False otherwise.
    """
    return os.path.isfile(path)
 
def process_software(software, fresh_installation, json_path, csv_path, subgroup_list):
    """
    Processes the given software by parsing JSON data and returning a filtered list of items.
 
    Parameters:
        software (str): The name of the software.
        fresh_installation (bool): Indicates whether it is a fresh installation.
        json_path (str): The path to the JSON file.
        csv_path (str): The path to the CSV file.
        subgroup_list (list, optional): A list of subgroups to filter. Defaults to None.
 
    Returns:
        list: The filtered list of items.
    """
    failed_packages = None if fresh_installation else get_failed_software(csv_path)
    return parse_json_data(json_path, PACKAGE_TYPES, failed_packages, subgroup_list)
 
def get_software_names(data_path):
    """
    Retrieves a list of software names from a given data path.
 
    Parameters:
        data_path (str): The path to the data file.
 
    Returns:
        list: A list of software names.
    """
    data = load_json(data_path)
    return [software['name'] for software in data.get('softwares', [])]
