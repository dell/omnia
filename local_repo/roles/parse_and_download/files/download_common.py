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
Module to handle download processes for various package types such as pip_module,git,
tarball,manifest,ansible-galaxy collection.
"""

import subprocess
import os, shlex
import sys
import tarfile
from jinja2 import Template
import shutil
from common_utility import update_status

def process_pip_package(package, repo_store_path, status_file_path):
    """
    Process a pip package.

    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
    """

    python_version = os.path.basename(sys.executable)
    package_name = package['package']
    package_name = shlex.quote(package_name).strip("'\"")

    version = package.get('version', None)
    package_type = package['type']
    print(f"Processing Pip Package: {package_name}, Version: {version}")

    # Assuming you have a specific path to store pip packages
    pip_modules_directory = os.path.join(repo_store_path, 'cluster', 'pip_module')
    os.makedirs(pip_modules_directory, exist_ok=True)  # Ensure the directory exists
    pip_modules_directory = shlex.quote(pip_modules_directory).strip("'\"")

    # Pip specific processing logic goes here
    # ...

    # Download the package
    download_command = [
        python_version, '-m', 'pip', 'download',
        package_name,
        '-d', pip_modules_directory
    ]

    try:
        # Run the download command
        subprocess.run(download_command, check=True)
        status = 'Success'
    except subprocess.CalledProcessError:
        print(f"Error: Unable to download Pip Package {package_name}")
        status = 'Failed'

    # Update the status
    update_status(package_name, package_type, status, status_file_path)

def process_git_package(package, repo_store_path, status_file_path):
    """
    Process a Git package.

    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
    """

    package_name = package['package']
    package_name = shlex.quote(package_name).strip("'\"")

    url = package.get('url', None)
    url = shlex.quote(url).strip("'\"")

    version = package.get('version', None)
    version = shlex.quote(version).strip("'\"")

    package_type = package['type']
    print(f"Processing Git Package: {package_name}, URL: {url}, Version: {version}")

    # Assuming you have a specific path to store Git packages
    git_modules_directory = os.path.join(repo_store_path, 'cluster', 'git')
    os.makedirs(git_modules_directory, exist_ok=True)  # Ensure the directory exists

    clone_directory = os.path.join(git_modules_directory, package_name)
    clone_directory = shlex.quote(clone_directory).strip("'\"")
    tarball_path = os.path.join(git_modules_directory, f'{package_name}.tar.gz')

    try:
        # Using wget to check if the URL exists (returns 0 for success, non-zero for failure)
        subprocess.run(['wget', '-q', '--spider', '--tries=1', url], check=True)
        # Clone the repository only if it doesn't exist
        if not os.path.exists(clone_directory):
            clone_command = ['git', 'clone', '--branch', version, url, clone_directory]
            subprocess.run(clone_command, check=True)

            # Create a tarball of the cloned repository in the same directory
            with tarfile.open(tarball_path, 'w:gz') as tar:
                tar.add(clone_directory, arcname=package_name)

            status = "Success"
        else:
            print(f"Git Package {package_name} already exists in {clone_directory}. Skipping download.")
            status = "Success"
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with return code {e.returncode}")
        # Set status as "Failed"
        status = "Failed"

    # Update the status
    update_status(package_name, package_type, status, status_file_path)


def process_tarball_package(package, repo_store_path, status_file_path, version_variables):
    """
    Process a tarball package.

    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
        version_variables: Variables for rendering version template.
    """
    path = None
    url = None
    path_support = False
    url_support = True
    package_template = Template(package.get('package', None))  # Use Jinja2 Template for package
    package_name = package_template.render(**version_variables)
    package_type = package['type']
    if 'url' in package:
        url_template = Template(package.get('url', None))  # Use Jinja2 Template for URL
        # Render the URL, substituting Jinja variables if present
        url = url_template.render(**version_variables)
    if 'path' in package:
        path = package['path']

    print(f"Processing Tarball Package: {package_name}, URL: {url}, Path: {path}")
    url = shlex.quote(url).strip("'\"")

    if path is not None and len(path) > 1:
        if os.path.isfile(path):
            path_support = True
            url_support = False

    # Creating the local path to save the tarball
    tarball_directory = os.path.join(repo_store_path, 'cluster', 'tarball')

    print(f"Processing tarball to directory: {tarball_directory}")
    os.makedirs(tarball_directory, exist_ok=True)  # Ensure the directory exists

    # Use the package name for the tarball filename
    tarball_path = os.path.join(tarball_directory, f"{package_name}.tar.gz")
    tarball_path = shlex.quote(tarball_path).strip("'\"")

    if path_support == False and url_support == True:
        try:
            # Using wget to check if the URL exists (returns 0 for success, non-zero for failure)
            subprocess.run(['wget', '-q', '--spider', '--tries=1', url], check=True)

            # Check if the tarball already exists
            if os.path.exists(tarball_path):
                print(f"Tarball Package {package_name} already exists at {tarball_path}")
                try:
                    print("Verifying for package download completion")
                    subprocess.run(['wget', '-c','-O', tarball_path, url], check=True)
                    status = "Success"
                except subprocess.CalledProcessError:
                    status = "Failed"
            elif url:
                # Using wget to download the tarball from the URL
                try:
                    subprocess.run(['wget', '-O', tarball_path, url], check=True)
                    status = "Success"
                except subprocess.CalledProcessError:
                    status = "Failed"
            else:
                status = "No URL provided"
        except subprocess.CalledProcessError:
            print(f"Error: Package {package_name} not found at {url}")
            status = "Failed"
    elif path_support == True and url_support == False:
        try:
            shutil.copy(path, tarball_path)
            status = "Success"
        except:
            status = "Failed"

    # Update the status
    update_status(package_name, package_type, status, status_file_path)


def process_manifest_package(package,repo_store_path, status_file_path):
    """
    Process a manifest package.

    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
    """
    package_name = package['package']
    url = package.get('url', None)
    url = shlex.quote(url).strip("'\"")
    package_type = package['type']
    print(f"Processing Manifest Package: {package_name}, URL: {url}")

    # Creating the local path to save the manifest file
    manifest_directory = os.path.join(repo_store_path, 'cluster', 'manifest')
    os.makedirs(manifest_directory, exist_ok=True)  # Ensure the directory exists

    manifest_path = os.path.join(manifest_directory, f"{package_name}.yaml")

    try:
        # Using wget to check if the URL exists (returns 0 for success, non-zero for failure)
        subprocess.run(['wget', '-q', '--spider', '--tries=1', url], check=True)

        # Check if the manifest file already exists
        if os.path.exists(manifest_path):
            print(f"Manifest Package {package_name} already exists at {manifest_path}")
            try:
                print("Verifying for package download completion")
                subprocess.run(['wget', '-c','-O', manifest_path, url], check=True)
                status = "Success"
            except subprocess.CalledProcessError:
                status = "Failed"
        else:
            # Download the manifest file from the URL
            subprocess.run(['wget', '-O', manifest_path, url], check=True)
            status = "Success"
    except subprocess.CalledProcessError:
        print(f"Error: Package {package_name} not found at {url}")
        status = "Failed"

    # Update the status
    update_status(package_name, package_type, status, status_file_path)

def process_shell_package(package,repo_store_path, status_file_path):
    """
    Process a shell package.

    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
    """
    package_name = package['package']
    url = package.get('url', None)
    package_type = package['type']
    print(f"Processing sh Package: {package_name}, URL: {url}")

    # Creating the local path to save the sh file
    sh_directory = os.path.join(repo_store_path, 'cluster', 'shell')
    os.makedirs(sh_directory, exist_ok=True)  # Ensure the directory exists

    sh_path = os.path.join(sh_directory, f"{package_name}.sh")

    try:
        # Using wget to check if the URL exists (returns 0 for success, non-zero for failure)
        subprocess.run(['wget', '-q', '--spider', '--tries=1', url], check=True)

        # Check if the sh file already exists
        if os.path.exists(sh_path):
            print(f"sh Package {package_name} already exists at {sh_path}")
            status = "Success"
        else:
            # Download the sh file from the URL
            subprocess.run(['wget', '-O', sh_path, url], check=True)
            status = "Success"
    except subprocess.CalledProcessError:
        print(f"Error: Package {package_name} not found at {url}")
        status = "Failed"

    # Update the status
    update_status(package_name, package_type, status, status_file_path)

def process_ansible_galaxy_collection(package, repo_store_path, status_file_path):
    """
    Process ansible-galaxy collection package.

    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
    """
    package_name = package['package']
    version = package.get('version', None)

    package_name = shlex.quote(package_name).strip("'\"")
    version = shlex.quote(version).strip("'\"")

    package_type = package['type']
    print(f"Processing Ansible Galaxy Collection Package: {package_name}, Version: {version}")

    # Assuming you have a specific path to store Ansible Galaxy Collections
    galaxy_collections_directory = os.path.join(repo_store_path, 'cluster', 'ansible_galaxy_collection')
    galaxy_collections_directory = shlex.quote(galaxy_collections_directory).strip("'\"")
    os.makedirs(galaxy_collections_directory, exist_ok=True)  # Ensure the directory exists

    # Check if the tarball already exists
    collections_tarball_path = os.path.join(galaxy_collections_directory, f'{package_name.replace(".", "-")}-{version}.tar.gz')
    if os.path.exists(collections_tarball_path):
        print(f"Ansible Galaxy Collection {package_name}:{version} already exists at {collections_tarball_path}. Skipping download.")
        status = "Success"
    else:
        # Example: Using subprocess.run with ansible-galaxy command to download the collection
        download_command = [
            'ansible-galaxy',
            'collection',
            'download',
            f'{package_name}:{version}',
            f'--download-path={galaxy_collections_directory}'
        ]

        try:
            subprocess.run(download_command, check=True)
            print(f"Ansible Galaxy Collection {package_name}:{version} downloaded successfully.")
            status = "Success"
        except subprocess.CalledProcessError:
            print(f"Error: Unable to download Ansible Galaxy Collection {package_name}:{version}")
            status = "Failed"

    # Update the status
    update_status(package_name, package_type, status, status_file_path)

def process_iso_package(package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, repo_config, version_variables):
    """
    Process iso package.
    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
        cluster_os_type: Cluster OS type.
        cluster_os_version: Cluster OS version.
        repo_config: Repository configuration.
        version_variables: Variables for rendering version template.
    """
    path = None
    url = None
    path_support = False
    url_support = True
    package_name = package['package']
    package_type = package['type']
    if 'url' in package:
        url_template = Template(package.get('url', None))  # Use Jinja2 Template for URL
        # Render the URL, substituting Jinja variables if present
        url = url_template.render(**version_variables)
    if 'path' in package:
        path = package['path']

    print(f"Processing iso Package: {package_name}, URL: {url}, Path: {path}")

    if path is not None and len(path) > 1:
        if os.path.isfile(path):
            path_support = True
            url_support = False

    iso_directory = os.path.join(repo_store_path, 'cluster', cluster_os_type, cluster_os_version, 'iso', package_name, version_variables.get(f"{package_name}_version", ''))

    print(f"Processing iso Package to directory: {iso_directory}")

    os.makedirs(iso_directory, exist_ok=True)

    if path_support == False and url_support == True:
        try:
            download_file_name = url.split('/')
            print(f"Download file name: {download_file_name[-1]}")
            iso_file_path = os.path.join(iso_directory, download_file_name[-1])
            # Check if the file already exists
            if os.path.exists(iso_file_path):
                print(f"ISO Package {package_name} already exists at {iso_directory}")
                status = "Success"
            else:
                # Using wget to check if the URL exists (returns 0 for success, non-zero for failure)
                subprocess.run(['wget', '-q', '--spider', '--tries=1', url], check=True)
                iso_tmp_file =  os.path.join('/tmp', download_file_name[-1])
                # Using wget to download the iso file from the URL
                subprocess.run(['wget', '-O', iso_tmp_file, url], check=True)
                shutil.move(iso_tmp_file, iso_file_path)
                status = "Success"
        except:
            status = "Failed"
    elif path_support == True and url_support == False:
        try:
            shutil.copy(path, iso_directory)
            status = "Success"
        except:
            status = "Failed"

    # Update the status
    update_status(package_name, package_type, status, status_file_path)
