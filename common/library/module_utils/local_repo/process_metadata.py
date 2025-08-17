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

# pylint: disable=import-error,no-name-in-module
#!/usr/bin/python

from datetime import datetime
from pathlib import Path
import os
import json
import yaml
# Import default variables from config.py
from ansible.module_utils.local_repo.config import ARCH_SUFFIXES

def load_yaml(path):
    """
    Load YAML content from the given file path.

    Returns an empty dictionary if the file does not exist,
    or if the file is empty/null.
    """
    if not os.path.isfile(path):
        return {}
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}

def write_yaml(path, data):
    """
    Write the given data (dict) to a file in YAML format.

    Uses block-style formatting (not flow style).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)

def load_config(config_path: str) -> dict:
    """
    Load and parse JSON configuration from the specified file path.

    Raises FileNotFoundError if the file does not exist.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path) as f:
        return json.load(f)

def generate_policy_dict(repo_list, default_policy):
    """
    Generate a dictionary mapping each repository name (normalized) to its policy.

    If a repository does not define a 'policy', use the provided default_policy.
    """
    policy_dict = {}
    for repo in repo_list:
        name_key = f"{repo['name'].replace('-', '_')}_policy"
        # Use the repo's policy or the default if not provided
        policy_value = repo.get('policy', default_policy)
        policy_dict[name_key] = policy_value
    return policy_dict

def update_metadata_file(file_path: str, repo_src_name: str, new_policy: dict):
    """
    Update the metadata YAML file with a new policy for a given repository source name.

    - Loads existing metadata from the file.
    - Updates or adds the new policy under the given repo_src_name key.
    - Writes the updated metadata back to the file.
    """
    if os.path.exists(file_path):
        existing_metadata = load_yaml(file_path)
    else:
        existing_metadata = {}

    existing_metadata[repo_src_name] = new_policy
    write_yaml(file_path, existing_metadata)

def append_metadata_footer(output_file: str, repo_mode: str):
    """
    Append additional metadata footer information to the metadata YAML file.

    - Adds/updates the 'repository_mode' key with the given repo_mode value.
    - Adds/updates the 'lastrun_timestamp' with the current UTC timestamp.
    - Writes the updated metadata back to the file.
    """
    metadata = load_yaml(output_file)
    metadata['repository_mode'] = repo_mode
    metadata['lastrun_timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    write_yaml(output_file, metadata)

def deep_update(orig_dict, new_dict):
    """
    Recursively update a dictionary with another dictionary.

    - For each key in new_dict:
      - If the value is a dictionary and the corresponding value in orig_dict is also a dictionary,
        recursively update the nested dictionary.
      - Otherwise, set or overwrite the value in orig_dict with the value from new_dict.
    - Returns the updated orig_dict.
    """
    for key, value in new_dict.items():
        if isinstance(value, dict):
            # Recursively update nested dictionaries
            orig_dict[key] = deep_update(orig_dict.get(key, {}), value)
        else:
            # Overwrite or add the value
            orig_dict[key] = value
    return orig_dict

def get_diff(base, other):
    """
    Compute the difference between two dictionaries.

    - For each key in 'other':
      - If the key does not exist in 'base', include it in the diff.
      - If the value is a dictionary in both 'base' and 'other',
        compute the nested difference recursively.
      - If the values differ, include the value from 'other' in the diff.
    - Returns a dictionary containing only the differing keys and values.
    """

    diff = {}
    for key, value in other.items():
        if key not in base:
            diff[key] = value
        elif isinstance(value, dict) and isinstance(base.get(key), dict):
            nested_diff = get_diff(base[key], value)
            if nested_diff:
                diff[key] = nested_diff
        elif base[key] != value:
             # Value differs
            diff[key] = value
    return diff

def get_os_type(config):
    """
    Extract and validate the OS type from the given configuration.

    - Reads the value of 'cluster_os_type' from the config dictionary.
    - Converts it to lowercase for consistency.
    - Validates that the OS type is one of the supported values: 'rhel', 'rockey', or 'ubuntu'.
    - If the OS type is not supported, the module fails with an error.
    - Returns the validated OS type string.

    Parameters:
        config (dict): Configuration dictionary that should contain 'cluster_os_type'.

    Returns:
        str: Validated OS type.
    """
    cluster_os_type = config.get('cluster_os_type', '').lower()

    if cluster_os_type not in ['rhel', 'rockey', 'ubuntu']:
        raise ValueError(f"Unsupported cluster_os_type: {cluster_os_type}")

    return cluster_os_type


def handle_generate_metadata(sw_config,repo_data,output_file):
    """
    Generates metadata for repository configurations based on the provided software configuration
    and repository data files. The metadata is written to the specified output file.

    Parameters:
        sw_config (str): Path to the software configuration JSON file.
        repo_data (str): Path to the local repository YAML data file.
        output_file (str): Path where the generated metadata should be written.

    Returns:
        dict: A dictionary containing the last repo key processed and its generated policy.
    """

    # Load the software configuration and repo data from files
    config = load_config(sw_config)
    repo_data = load_yaml(repo_data)

    # Fetch the default repository policy, fallback to "always" if not set
    default_policy = config.get("repo_config", "always")

    # Determine the OS type from the config (e.g., rhel, ubuntu, etc.)
    os_type = get_os_type(config)

    # Define the keys in the repo_data to process, based on OS type
    keys_to_process = (
        [f'user_repo_url_{arch}' for arch in ARCH_SUFFIXES] +
        [f'omnia_repo_url_{os_type}_{arch}' for arch in ARCH_SUFFIXES] +
        [f'{os_type}_os_url_{arch}' for arch in ARCH_SUFFIXES]
    )
    # Iterate over each key and generate/update policy metadata
    for key in keys_to_process:
        repo_list = repo_data.get(key, [])
        if not repo_list:
            continue  # Skip processing if key is missing or value is None/empty
        repo_src_name = key
        new_policy = generate_policy_dict(repo_list, default_policy)
        update_metadata_file(output_file, repo_src_name, new_policy)

    # Append common footer metadata such as repo mode and timestamp
    append_metadata_footer(output_file,default_policy)

    # Return the last policy generated as a summary result
    return {repo_src_name: new_policy}


def handle_compare_data(original_file,updated_file,ignore_keys):
    """
    Compares two YAML files after removing specified keys from both.

    This function is typically used to check whether two metadata files are
    identical, ignoring fields that are expected to change (e.g., timestamps).

    Parameters:
        original_file (str): Path to the original YAML file.
        updated_file (str): Path to the updated YAML file.
        ignore_keys (list): List of keys to ignore during comparison.

    Returns:
        dict: {
            "changed": True if files differ (ignoring ignored keys),
            "identical": True if files are the same (after ignoring keys)
        }
    """

    original_data = load_yaml(original_file)
    updated_data = load_yaml(updated_file)

    # Remove ignore_keys from both datasets
    for key in ignore_keys:
        original_data.pop(key, None)
        updated_data.pop(key, None)

    # Compare the filtered data
    same = original_data == updated_data
    # Return the result of comparison
    return {
        "changed": not same, # True if files are different
        "identical": same    # True if files are identical
    }


def handle_update_data(original_file,updated_file,ignore_keys):
    """
    Updates the original metadata file with differences from the updated file,
    excluding specified keys, and appends a 'lastrun_timestamp'.

    Parameters:
        original_file (str): Path to the existing metadata file.
        updated_file (str): Path to the new metadata file to merge from.
        ignore_keys (list): List of top-level keys to ignore when comparing.

    Returns:
        dict: {
            "changed": True if any differences were found and merged,
            "diff": Dictionary of the detected differences
        }
    """

    original_data = load_yaml(original_file)
    updated_data = load_yaml(updated_file)

    # Remove keys that should be ignored during diff
    for key in ignore_keys:
        original_data.pop(key, None)
        updated_data.pop(key, None)

    # Compute the differences between the cleaned original and updated data
    diff = get_diff(original_data, updated_data)

    if diff:
        # If differences exist, apply them using deep merge
        new_data = deep_update(original_data, diff)
        new_data['lastrun_timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        # Write merged data back to the original file
        write_yaml(original_file, new_data)
    else:
        # If no differences, just update the timestamp
        new_data = original_data
        new_data['lastrun_timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        write_yaml(original_file, new_data)

    # Delete the temporary updated metadata file
    Path(updated_file).unlink(missing_ok=True)

    # Return whether the original file was changed and the diff
    return {
        "changed": bool(diff),   
        "diff": diff             
    }
