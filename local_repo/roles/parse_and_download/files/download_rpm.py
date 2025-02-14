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
Module to handle download processes for rpm and debian packages
"""
import subprocess
import re
import os, shlex
from jinja2 import Template
from common_utility import update_status

def process_rpm_package(package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, repo_config, version_variables, cluster_name):
    """
    Process an rpm package
    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
        cluster_os_type: Cluster OS type.
        cluster_os_version: Cluster OS version.
        repo_config: Repository configuration.
        version_variables: Variables for rendering version template.

    """
    repo_name = package['repo_name']
    package_type = package['type']
    package_template = Template(package.get('package', None))  # Use Jinja2 Template for package
    # Render the packages, substituting Jinja variables if present
    package_name = package_template.render(**version_variables)
    package_name = shlex.quote(package_name).strip("'\"")
    print(f"Processing RPM: {package_name},Repo Name: {repo_name},Repo Config: {repo_config}")

    # Specify the repository names that should be skipped
    skip_repos = ['appstream', 'baseos']

    omnia_always = ['amdgpu', 'cuda', 'ofed']

    # Construct the path based on the provided repository store format
    if cluster_name == 'beegfs':
        rpm_directory = os.path.join(repo_store_path, 'cluster', 'yum', 'beegfs',
                version_variables.get('beegfs_version', ''))
    elif cluster_name == 'amdgpu':
        rpm_directory = os.path.join(repo_store_path, 'cluster', 'yum', 'amdgpu',
                version_variables.get('amdgpu_version', ''))
    elif cluster_name == 'rocm':
        rpm_directory = os.path.join(repo_store_path, 'cluster', 'yum', 'rocm',
                version_variables.get('rocm_version', ''))
    else:
        rpm_directory = os.path.join(repo_store_path, 'cluster', cluster_os_type, cluster_os_version, 'rpm')

    # shlex quote rpm_directory
    rpm_directory = shlex.quote(rpm_directory).strip("'\"")

    # Default status value
    status = "Skipped"

    # Check if the specified repo_name is in the list of repos to be skipped
    if repo_name not in skip_repos:
        try:
            # Different logic based on repo_config value
            if repo_config == 'always' or cluster_name in omnia_always:
                # Ensure the directory exists
                os.makedirs(rpm_directory, exist_ok=True)
                # Step 1: Download the main package without resolving dependencies
                subprocess.run(['dnf', 'download', package_name, '--arch=x86_64,noarch',
                        f'--destdir={rpm_directory}'], check=True)
                # Step 2: Query dependencies of the main package
                dependencies_cmd = ['repoquery', '--requires', '--resolve', '--recursive', '--arch=x86_64,noarch', package_name]
                if package_name =='rocm':
                    dependencies_cmd = ['repoquery', '--disablerepo=*', '--enablerepo=omnia_repo_rocm', '--requires', '--resolve', '--recursive',
                            '--arch=x86_64,noarch', package_name]
                dependencies = subprocess.check_output(dependencies_cmd, text=True).splitlines()
                dependencies = [dep for dep in dependencies if any(arch in dep for arch in ['x86_64', 'noarch'])]

                # Print the list of dependencies
                print(f"Dependencies of {package_name}: {dependencies}")

                # Step 3: Download the dependencies of the main package without resolving
                if dependencies:
                    # Ensure the directory exists
                    os.makedirs(rpm_directory, exist_ok=True)
                    # Modify the destination directory to the custom path based on repo_name
                    subprocess.run(['dnf', 'download', '--arch=x86_64,noarch',
                            f'--destdir={rpm_directory}'] + dependencies, check=True)
                    print("Dependencies downloaded successfully.")
                else:
                    print("No dependencies to download.")

                print(f"RPM Package {package_name} downloaded successfully.")

                # Set status to "Success" only if all steps are successful
                status = "Success"

            elif repo_config == 'partial' and cluster_name not in omnia_always:
                try:
                    # Step 0: Check if the package is available in user repos
                    subprocess.run(['dnf', 'list', 'available', package_name, '--disablerepo=omnia_repo*'], check=True)
                    # If the command succeeds, the package is available in user repos
                    print(f"Package {package_name} is available in user repos. No need to download.")
                    status = "Skipped"
                except subprocess.CalledProcessError:
                    # If the command fails, the package is not available in user repos
                    print(f"Package {package_name} is not available in user repos. Proceeding to download main package...")

                    # Ensure the directory exists
                    os.makedirs(rpm_directory, exist_ok=True)

                    # Step 1: Download the main package without resolving dependencies
                    subprocess.run(['dnf', 'download', package_name, '--arch=x86_64,noarch', f'--destdir={rpm_directory}'], check=True)
                    status = "Success"

                # Step 2: Query dependencies of the main package
                dependencies_cmd = ['repoquery', '--requires', '--resolve', '--recursive', '--arch=x86_64,noarch', package_name]
                if package_name =='rocm':
                    dependencies_cmd = ['repoquery', '--disablerepo=*', '--enablerepo=omnia_repo_rocm', '--requires', '--resolve', '--recursive', '--arch=x86_64,noarch', package_name]
                dependencies = subprocess.check_output(dependencies_cmd, text=True).splitlines()
                dependencies = [dep for dep in dependencies if any(arch in dep for arch in ['x86_64', 'noarch'])]

                # Step 3: Check if each dependency is available in user repos
                for dependency in dependencies:
                    dependency = shlex.quote(dependency).strip("'\"")
                    try:
                        subprocess.run(['dnf', 'list', 'available', dependency, '--disablerepo=omnia_repo*'], check=True)
                        # If the command succeeds, the dependency is available in user repos
                        print(f"Dependency {dependency} is available in user repos. No need to download.")
                    except subprocess.CalledProcessError:
                        # If the command fails, the dependency is not available in user repos
                        print(f"Dependency {dependency} is not available in user repos. Proceeding to download...")

                        # Ensure the directory exists
                        os.makedirs(rpm_directory, exist_ok=True)

                        # Download the dependency without resolving
                        subprocess.run(['dnf', 'download', dependency, '--arch=x86_64,noarch', f'--destdir={rpm_directory}'], check=True)
                # Print success message
                print(f"RPM Package {package_name} downloaded successfully.")

            elif repo_config == 'never' and cluster_name not in omnia_always:
                status = "Skipped"
                print(f"RPM Package {package_name} wont be downloaded when repo_config is never")

        except subprocess.CalledProcessError:
            print(f"Error: Unable to process RPM Package {package_name}")
            status = "Failed"

    else:
        print(f"Skipping RPM  {package_name} from repo {repo_name} based on repo_config: {repo_config}.")

    # Update status in your status file or perform further processing
    update_status(package_name, package_type, status, status_file_path)
