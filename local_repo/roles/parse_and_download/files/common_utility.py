# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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

"""
Module: common_utility.py
This module provides utility functions for managing package statuses and running createrepo.
"""

import subprocess
import os
import shlex

def update_status(package_name, package_type, status, status_file_path):
    """
    Update the status of a package in the status file.

    package_name: The name of the package.
    package_type: The type of the package.
    status: The status of the package.
    status_file_path: The path to the status file.
    """
    # Read existing statuses from the status file
    try:
        with open(status_file_path, 'r', encoding='utf-8') as status_file:
            existing_statuses = status_file.readlines()
    except FileNotFoundError:
        existing_statuses = []

    # Skip writing entries with status "Skipped"
    #if status == "Skipped":
    #    return

    package_status = f"{package_name},{package_type},{status}\n"

    found = False
    # Check if the status entry already exists in the status file
    if existing_statuses:
        for i, existing_status in enumerate(existing_statuses):
            if existing_status.startswith(f"{package_name},{package_type},"):
                existing_statuses[i] = package_status
                found = True
                break

    if not found:
        # If the entry doesn't exist, append it to the file
        existing_statuses.append(package_status)

    # Write the updated status to the specified file
    with open(status_file_path, 'w', encoding='utf-8') as status_file:
        status_file.writelines(existing_statuses)

def run_createrepo_rhel(directory):
    """
    Run createrepo command on the specified directory.

    directory: The directory path where createrepo will be executed.
    """
    directory = shlex.quote(directory).strip("'\"")
    command = ["createrepo", directory]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running createrepo in {directory}: {e}")

def run_dpkg_scan(directory):
    """
    Run dpkg-scanpackages command on the specified directory.

    directory: The directory path where dpkg-scanpackages will be executed.
    """
    try:
        # Change directory to the specified directory
        os.chdir(directory)

        # Run dpkg-scanpackages command
        command = ["dpkg-scanpackages", ".", "/dev/null"]
        with open("Packages", "w") as output_file:
            subprocess.run(command, stdout=output_file, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running dpkg-scanpackages in {directory}: {e}")

def run_createrepo_on_rhel_directories(repo_store_path, cluster_os_type, cluster_os_version, version_variables):
    """
    Run createrepo on all relevant directories.

    repo_store_path: The base path where repositories are stored.
    cluster_os_type: The type of the cluster operating system.
    cluster_os_version: The version of the cluster operating system.
    version_variables: A dictionary containing version variables for different packages.
    """

    base_directories = [
        os.path.join(repo_store_path, 'cluster', cluster_os_type, cluster_os_version, 'rpm')
    ]

    if len(version_variables.get('beegfs_version', '').strip()) > 0:
        base_directories.append(os.path.join(repo_store_path, 'cluster', 'yum', 'beegfs',
                    version_variables.get('beegfs_version', '')))
    if len(version_variables.get('rocm_version', '').strip()) > 0:
        base_directories.append(os.path.join(repo_store_path, 'cluster', 'yum', 'rocm',
                    version_variables.get('rocm_version', '')))
    if len(version_variables.get('amdgpu_version', '').strip()) > 0:
        base_directories.append(os.path.join(repo_store_path, 'cluster', 'yum', 'amdgpu',
                    version_variables.get('amdgpu_version', '')))

    for directory in base_directories:
        if os.path.exists(directory):
            run_createrepo_rhel(directory)

def run_createrepo_on_ubuntu_directories(repo_store_path, cluster_os_type, cluster_os_version, version_variables):
    """
    Run createrepo on all relevant directories.

    repo_store_path: The base path where repositories are stored.
    cluster_os_type: The type of the cluster operating system.
    cluster_os_version: The version of the cluster operating system.
    version_variables: A dictionary containing version variables for different packages.
    """

    base_directories = [
        os.path.join(repo_store_path, 'cluster', cluster_os_type, cluster_os_version, 'deb')
    ]

    if len(version_variables.get('beegfs_version', '').strip()) > 0:
        base_directories.append(os.path.join(repo_store_path, 'cluster', 'apt', 'beegfs',
                    version_variables.get('beegfs_version', '')))
    if len(version_variables.get('rocm_version', '').strip()) > 0:
        base_directories.append(os.path.join(repo_store_path, 'cluster', 'apt', 'rocm',
                    version_variables.get('rocm_version', '')))
    if len(version_variables.get('amdgpu_version', '').strip()) > 0:
        base_directories.append(os.path.join(repo_store_path, 'cluster', 'apt', 'amdgpu',
                    version_variables.get('amdgpu_version', '')))
    if len(version_variables.get('intelgaudi_version', '').strip()) > 0:
        base_directories.append(os.path.join(repo_store_path, 'cluster', 'apt', 'intelgaudi',
                    version_variables.get('intelgaudi_version', '')))
        if os.path.exists(os.path.join(repo_store_path, 'cluster', 'apt', 'intel')):
            base_directories.append(os.path.join(repo_store_path, 'cluster', 'apt', 'intel',
                        version_variables.get('intelgaudi_version', '')))
    for directory in base_directories:
        if os.path.exists(directory):
            run_dpkg_scan(directory)
