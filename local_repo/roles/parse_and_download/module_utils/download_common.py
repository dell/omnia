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
import subprocess
import shlex
import tarfile
import shutil
from jinja2 import Template
from ansible.module_utils.standard_logger import setup_standard_logger
from ansible.module_utils.parse_and_download import write_status_to_file,execute_command
 
# Pulp command templates
pulp_file_commands = {
    "create_repository": "pulp file repository create --name %s",
    "show_repository": "pulp file repository show --name %s",
    "download_content": "wget -c -O %s %s",
    "content_upload": "pulp file content upload --repository %s --file %s --relative-path %s",
    "publication_create": "pulp file publication create --repository %s",
    "show_distribution": "pulp file distribution show --name %s",
    "distribution_create": "pulp file distribution create --name %s --base-path %s --repository %s",
    "distribution_update": "pulp file distribution update --name %s --base-path %s --repository %s",
}
 
def process_file(repository_name, output_file, relative_path, base_path, distribution_name, url, file_path, logger):
    """
    Process a file using Pulp, ensuring it is downloaded and stored in the specified file_path.
 
    Args:
        repository_name (str): Name of the Pulp repository.
        output_file (str): Name of the output file.
        relative_path (str): Relative path for the file in Pulp.
        base_path (str): Base path for the distribution.
        distribution_name (str): Name of the distribution.
        url (str): URL of the file to be downloaded.
        file_path (str): Path where the file should be stored.
        logger (logging.Logger): Logger instance for logging.
 
    Returns:
        str: "Success" if the process is successful, otherwise "Failed".
    """
    logger.info("#" * 30 + f" {process_file.__name__} start " + "#" * 30)  # Start of function
    status = "Success"
    try:
        logger.info(f"Processing file: {url}")
 
        # Step 1: Check if the file exists in the file path; download if not
        logger.info("Step 1: Checking if the file exists in the manifest path...")
        if os.path.exists(file_path):
            logger.info(f"File already exists: {file_path}. Skipping download.")
        else:
            logger.info("File does not exist. Downloading file...")
            download_command = pulp_file_commands["download_content"] % (file_path, url)
            if not execute_command(download_command, logger):
                logger.error(f"Failed to download the file: {url}")
                return "Failed"
            logger.info(f"File downloaded to: {file_path}")
 
        # Step 2: Check if the repository exists; create if not
        logger.info("Step 2: Checking repository...")
        if not execute_command(pulp_file_commands["show_repository"] % (repository_name), logger):
            logger.info(f"Repository {repository_name} does not exist. Creating it...")
            if not execute_command(pulp_file_commands["create_repository"] % (repository_name), logger):
                logger.error(f"Failed to create repository: {repository_name}")
                return "Failed"
        else:
            logger.info(f"Repository {repository_name} already exists.")
 
        # Step 3: Upload the content to the repository
        logger.info("Step 3: Uploading content...")
        if not execute_command(pulp_file_commands["content_upload"] % (repository_name, file_path, relative_path), logger):
            logger.error(f"Failed to upload content to repository: {repository_name}")
            return "Failed"
 
        # Step 4: Create a publication
        logger.info("Step 4: Creating publication...")
        if not execute_command(pulp_file_commands["publication_create"] % (repository_name), logger):
            logger.error(f"Failed to create publication for repository: {repository_name}")
            return "Failed"
 
        # Step 5: Check if the distribution exists
        logger.info("Step 5: Checking distribution...")
        if not execute_command(pulp_file_commands["show_distribution"] % (distribution_name), logger):
            logger.info(f"Distribution {distribution_name} does not exist. Creating it...")
            if not execute_command(pulp_file_commands["distribution_create"] % (distribution_name, base_path, repository_name), logger):
                logger.error(f"Failed to create distribution: {distribution_name}")
                return "Failed"
        else:
            logger.info(f"Distribution {distribution_name} already exists. Updating it...")
            if not execute_command(pulp_file_commands["distribution_update"] % (distribution_name, base_path, repository_name), logger):
                logger.error(f"Failed to update distribution: {distribution_name}")
                return "Failed"
 
        logger.info(f"Processing for file {url} completed successfully!")
        return "Success"
 
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return "Failed"
 
    finally:
        logger.info("#" * 30 + f" {process_file.__name__} end " + "#" * 30)  # End of function
 
def process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, url, file_path, logger):
    """
    Process a file using Pulp, ensuring it is stored in the specified file_path.
 
    Args:
        repository_name (str): Name of the Pulp repository.
        output_file (str): Name of the output file.
        relative_path (str): Relative path for the file in Pulp.
        base_path (str): Base path for the distribution.
        distribution_name (str): Name of the distribution.
        url (str): URL of the file to be downloaded.
        file_path (str): Path where the file should be stored.
        logger (logging.Logger): Logger instance for logging.
 
    Returns:
        str: "Success" if the process is successful, otherwise "Failed".
    """
    logger.info("#" * 30 + f" {process_file_without_download.__name__} start " + "#" * 30)  # Start of function
    status = "Success"
    try:
        logger.info(f"Processing file: {url}")
 
        # Step 1: Check if the repository exists; create if not
        logger.info("Step 1: Checking repository...")
        if not execute_command(pulp_file_commands["show_repository"] % (repository_name), logger):
            logger.info(f"Repository {repository_name} does not exist. Creating it...")
            if not execute_command(pulp_file_commands["create_repository"] % (repository_name), logger):
                logger.error(f"Failed to create repository: {repository_name}")
                return "Failed"
        else:
            logger.info(f"Repository {repository_name} already exists.")
 
        # Step 2: Upload the content to the repository
        logger.info("Step 2: Uploading content...")
        if not execute_command(pulp_file_commands["content_upload"] % (repository_name, file_path, relative_path), logger):
            logger.error(f"Failed to upload content to repository: {repository_name}")
            return "Failed"
 
        # Step 3: Create a publication
        logger.info("Step 3: Creating publication...")
        if not execute_command(pulp_file_commands["publication_create"] % (repository_name), logger):
            logger.error(f"Failed to create publication for repository: {repository_name}")
            return "Failed"
 
        # Step 4: Check if the distribution exists
        logger.info("Step 4: Checking distribution...")
        if not execute_command(pulp_file_commands["show_distribution"] % (distribution_name), logger):
            logger.info(f"Distribution {distribution_name} does not exist. Creating it...")
            if not execute_command(pulp_file_commands["distribution_create"] % (distribution_name, base_path, repository_name), logger):
                logger.error(f"Failed to create distribution: {distribution_name}")
                return "Failed"
        else:
            logger.info(f"Distribution {distribution_name} already exists. Updating it...")
            if not execute_command(pulp_file_commands["distribution_update"] % (distribution_name, base_path, repository_name), logger):
                logger.error(f"Failed to update distribution: {distribution_name}")
                return "Failed"
 
        logger.info(f"Processing for file {url} completed successfully!")
        return "Success"
 
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return "Failed"
 
    finally:
        logger.info("#" * 30 + f" {process_file_without_download.__name__} end " + "#" * 30)  # End of function
 
 
def process_manifest(file,repo_store_path, status_file_path,logger):
    """
    Process a manifest file.
 
    Args:
        file (dict): The file to process.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        logger (logging.Logger): The logger.
 
    Returns:
        str: The status of the processing.
 
    Raises:
        Exception: If an error occurs.    
    """
 
    logger.info("#" * 30 + f" {process_manifest.__name__} start " + "#" * 30)  # Start of function
    try:
        # Extract file details
        package_name = file["package"]
        url = file.get('url', None)
        url = shlex.quote(url).strip("'\"")
        package_type = file["type"]
 
        # Using wget to check if the URL exists (returns 0 for success, non-zero for failure)
        subprocess.run(['wget', '-q', '--spider', '--tries=1', url], check=True)
 
        # Ensure the manifest directory exists
        manifest_directory = os.path.join(repo_store_path, "offline_repo", "cluster", "manifest", package_name)
        os.makedirs(manifest_directory, exist_ok=True)
 
        # # Determine the manifest file path
        file_path = os.path.join(manifest_directory, f"{package_name}.yaml")
 
        repository_name = "manifest" + package_name
        output_file =  package_name + ".yml"
        relative_path = output_file
        base_path = manifest_directory.strip("/")
        distribution_name = repository_name
        status = "Success"
        status = process_file(repository_name, output_file, relative_path, base_path, distribution_name, url, file_path, logger)
    except Exception as e:
        logger.error(f"Error processing manifest: {e}")
        status= "Failed"
 
    finally:
        # Write the status to the file
        write_status_to_file(status_file_path, package_name, package_type, status, logger)
 
        logger.info("#" * 30 + f" {process_manifest.__name__} end " + "#" * 30)  # End of function
        return status
 
def process_git(file,repo_store_path, status_file_path,logger):
    """
    Process a Git package.
 
    Args:
        file (dict): A dictionary containing the package information.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        logger (logging.Logger): The logger instance.
 
    Returns:
        str: The status of the Git package processing.
 
    Raises:
        subprocess.CalledProcessError: If an error occurs while executing Git commands.
        Exception: If an error occurs while processing the Git package.
    """
 
    logger.info("#" * 30 + f" {process_git.__name__} start " + "#" * 30)  # Start of function
    try:
        package_name = file['package']
        package_name = shlex.quote(package_name).strip("'\"")
 
        url = file.get('url', None)
        url = shlex.quote(url).strip("'\"")
        version = file.get('version', None)
        version = shlex.quote(version).strip("'\"")
 
        package_type = file['type']
        logger.info(f"Processing Git Package: {package_name}, URL: {url}, Version: {version}")
 
        # Assuming you have a specific path to store Git packages
        git_modules_directory = os.path.join(repo_store_path, "offline_repo", 'cluster', 'git', package_name)
        os.makedirs(git_modules_directory, exist_ok=True)  # Ensure the directory exists
 
        clone_directory = os.path.join(git_modules_directory, package_name)
        clone_directory = shlex.quote(clone_directory).strip("'\"")
        tarball_path = os.path.join(git_modules_directory, f'{package_name}.tar.gz')
        repository_name = "git" + package_name
        output_file = package_name + ".tar.gz"
        relative_path = output_file
        base_path = git_modules_directory.strip("/")
        distribution_name = repository_name
 
        # Step 1: Clone the repository and create a tarball
        logger.info("Step 1: Cloning repository and creating tarball...")
        if not os.path.exists(clone_directory):
            clone_command = ['git', 'clone', '--branch', version, url, clone_directory]
            subprocess.run(clone_command, check=True)
 
            # Create a tarball of the cloned repository in the same directory
            with tarfile.open(tarball_path, 'w:gz') as tar:
                tar.add(clone_directory, arcname=package_name)
 
        else:
            logger.info(f"Git repository {file['package']} already cloned. Skipping clone.")
 
        # Step 2: Process the downloaded git tarball file using Pulp commands
        logger.info("Step 2: Processing git tarball with Pulp...")
        status = "Success"
        status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, url, tarball_path,logger)
 
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing Git commands: {e}")
        status= "Failed"
    except Exception as e:
        logger.error(f"Error processing Git package: {e}")
        status= "Failed"
 
    finally:
        # Write the status to the file
        write_status_to_file(status_file_path, package_name, package_type, status, logger)
 
        logger.info("#" * 30 + f" {process_git.__name__} end " + "#" * 30)  # End of function
        return status
 
# Function to process a shell file
def process_shell(file,repo_store_path, status_file_path,logger):
    """
    Process a shell package.
 
    Args:
        file (dict): A dictionary containing the package information.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        logger (logging.Logger): The logger instance.
 
    Returns:
        str: The status of the shell package processing.
 
    Raises:
        Exception: If an error occurs while processing the shell package.
    """
    logger.info("#" * 30 + f" {process_shell.__name__} start " + "#" * 30)  # Start of function
    try:
        package_name = file['package']
        url = file.get('url', None)
        package_type = file['type']
        logger.info(f"Processing sh Package: {package_name}, URL: {url}")
 
        # Creating the local path to save the sh file
        sh_directory = os.path.join(repo_store_path, "offline_repo", 'cluster', 'shell', package_name)
        os.makedirs(sh_directory, exist_ok=True)  # Ensure the directory exists
 
        sh_path = os.path.join(sh_directory, f"{package_name}.sh")
        repository_name = "shell" + package_name
        output_file = package_name + ".sh"
        relative_path = output_file
        base_path = sh_directory.strip("/")
        distribution_name = repository_name
        status = "Success"
        status = process_file(repository_name, output_file, relative_path, base_path, distribution_name, url, sh_path, logger )
    except Exception as e:
        logger.error(f"Error processing shell: {e}")
        status = "Failed"
 
    finally:
        # Write the status to the file
        write_status_to_file(status_file_path, package_name, package_type, status, logger)
 
        logger.info("#" * 30 + f" {process_shell.__name__} end " + "#" * 30)  # End of function
        return status
 
def process_ansible_galaxy_collection(file, repo_store_path, status_file_path, logger):
    """
    Process an Ansible Galaxy Collection.
 
    Args:
        file (dict): A dictionary containing the package information.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        logger (logging.Logger): The logger instance.
 
    Returns:
        str: The status of the Ansible Galaxy Collection processing.
 
    Raises:
        subprocess.CalledProcessError: If an error occurs while executing ansible-galaxy commands.
        Exception: If an error occurs while processing the Ansible Galaxy Collection.
   
    """
    logger.info("#" * 30 + f" {process_ansible_galaxy_collection.__name__} start " + "#" * 30)  # Start of function
    try:
        package_name = file['package']
        version = file.get('version', None)
 
        package_name = shlex.quote(package_name).strip("'\"")
        version = shlex.quote(version).strip("'\"")
 
        package_type = file['type']
        logger.info(f"Processing Ansible Galaxy Collection Package: {package_name}, Version: {version}")
 
        # Assuming you have a specific path to store Ansible Galaxy Collections
        galaxy_collections_directory = os.path.join(repo_store_path, "offline_repo", 'cluster', 'ansible_galaxy_collection', package_name)
        galaxy_collections_directory = shlex.quote(galaxy_collections_directory).strip("'\"")
        os.makedirs(galaxy_collections_directory, exist_ok=True)  # Ensure the directory exists
        collections_tarball_path = os.path.join(galaxy_collections_directory, f'{package_name.replace(".", "-")}-{version}.tar.gz')
        repository_name = "ansible_galaxy_collection" + package_name
        output_file = f"{file['package'].replace('.', '-')}-{file['version']}.tar.gz"
        relative_path = output_file
        base_path = galaxy_collections_directory.strip("/")
        distribution_name = repository_name
 
        logger.info(f"Processing Ansible Galaxy Collection: {file['package']}")
 
        # Check if the tarball already exists
 
        if os.path.exists(collections_tarball_path):
            logger.info(f"Ansible Galaxy Collection {package_name}:{version} already exists at {collections_tarball_path}. Skipping download.")
            logger.info("Processing the Ansible Galaxy collection tarball with Pulp...")
            status = "Success"
            status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, file["package"], collections_tarball_path, logger)
        else:
            # Example: Using subprocess.run with ansible-galaxy command to download the collection
            download_command = [
            'ansible-galaxy',
            'collection',
            'download',
            f'{package_name}:{version}',
            f'--download-path={galaxy_collections_directory}']
            try:
                subprocess.run(download_command, check=True)
                logger.info(f"Ansible Galaxy Collection {package_name}:{version} downloaded successfully.")
                 # Process the downloaded tarball file using Pulp commands
                logger.info("Processing the Ansible Galaxy collection tarball with Pulp...")
                status = "Success"
                status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, file["package"], collections_tarball_path, logger)
 
            except subprocess.CalledProcessError:
                logger.error(f"Error: Unable to download Ansible Galaxy Collection {package_name}:{version}")
                status = "Failed"
            except Exception as e:
                logger.error(f"Error processing ansible-galaxy-collection: {e}")
                status = "Failed"
 
 
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing ansible-galaxy commands: {e}")
        status = "Failed"
    except Exception as e:
        logger.error(f"Error processing Ansible Galaxy collection: {e}")
        status = "Failed"
 
    finally:
        # Write the status to the file
        write_status_to_file(status_file_path, package_name, package_type, status, logger)
 
        logger.info("#" * 30 + f" {process_ansible_galaxy_collection.__name__} end " + "#" * 30)  # End of function
        return status
 
def process_tarball(package, repo_store_path, status_file_path, version_variables, logger):
    """
    Process a tarball package.
 
    Args:
        package (dict): The package information.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        version_variables (dict): The version variables.
        logger (logging.Logger): The logger.
 
    Returns:
        str: The status of the operation.
    """
    logger.info("#" * 30 + f" {process_tarball.__name__} start " + "#" * 30)  # Start of function
 
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
 
    logger.info(f"Processing Tarball Package: {package_name}, URL: {url}, Path: {path}")
    url = shlex.quote(url).strip("'\"")
 
    if path is not None and len(path) > 1:
        if os.path.isfile(path):
            path_support = True
            url_support = False
 
    # Creating the local path to save the tarball
    tarball_directory = os.path.join(repo_store_path, "offline_repo", 'cluster', 'tarball', package_name)
 
    logger.info(f"Processing tarball to directory: {tarball_directory}")
    os.makedirs(tarball_directory, exist_ok=True)  # Ensure the directory exists
 
    # Use the package name for the tarball filename
    tarball_path = os.path.join(tarball_directory, f"{package_name}.tar.gz")
    tarball_path = shlex.quote(tarball_path).strip("'\"")
 
    repository_name = "tarball" + package_name
    output_file = package_name + ".tar.gz"
    relative_path = output_file
    base_path = tarball_directory.strip("/")
    distribution_name = repository_name
 
    if path_support == False and url_support == True:
        try:
            # Using wget to check if the URL exists (returns 0 for success, non-zero for failure)
            subprocess.run(['wget', '-q', '--spider', '--tries=1', url], check=True)
 
            # Check if the tarball already exists
            if os.path.exists(tarball_path):
                logger.info(f"Tarball Package {package_name} already exists at {tarball_path}")
                try:
                    logger.info("Verifying for package download completion")
                    subprocess.run(['wget', '-c','-O', tarball_path, url], check=True)
                    status = "Success"
                    status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, package_name, tarball_path, logger)
 
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error executing tarball commands: {e}")
                    status = "Failed"
                except Exception as e:
                    logger.error(f"Error processing tarball: {e}")
                    status = "Failed"
                finally:
                    # Write the status to the file
                    write_status_to_file(status_file_path, package_name, package_type, status, logger)
                    logger.info("#" * 30 + f" {process_tarball.__name__} end " + "#" * 30)  # End of function
                    return status
            elif url:
                # Using wget to download the tarball from the URL
                try:
                    subprocess.run(['wget', '-O', tarball_path, url], check=True)
                    status = "Success"
                    status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, package_name, tarball_path, logger)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error executing tarball commands: {e}")
                    status = "Failed"
                except Exception as e:
                    logger.error(f"Error processing tarball: {e}")
                    status = "Failed"
                finally:
                    # Write the status to the file
                    write_status_to_file(status_file_path, package_name, package_type, status, logger)
                    logger.info("#" * 30 + f" {process_tarball.__name__} end " + "#" * 30)  # End of function
                    return status
            else:
                status = "No URL provided"
        except subprocess.CalledProcessError:
            logger.error(f"Error: Package {package_name} not found at {url}")
            status = "Failed"
    elif path_support == True and url_support == False:
        try:
            shutil.copy(path, tarball_path)
            status = "Success"
            status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, package_name, tarball_path, logger)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing tarball commands: {e}")
            status = "Failed"
        except Exception as e:
            logger.error(f"Error processing tarball: {e}")
            status = "Failed"
        finally:
            # Write the status to the file
            write_status_to_file(status_file_path, package_name, package_type, status, logger)
            logger.info("#" * 30 + f" {process_tarball.__name__} end " + "#" * 30)  # End of function
            return status
 
def process_iso(package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, version_variables, logger):
    """
    Process an ISO package.
 
    Args:
        package (dict): A dictionary containing the package information.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        cluster_os_type (str): The type of the cluster operating system.
        cluster_os_version (str): The version of the cluster operating system.
        version_variables (dict): A dictionary of version variables.
        logger (logging.Logger): The logger instance.
 
    Returns:
        str: The status of the ISO package processing.
 
    Raises:
        subprocess.CalledProcessError: If an error occurs while executing iso commands.
        Exception: If an error occurs while processing the ISO package.
    """
    logger.info("#" * 30 + f" {process_iso.__name__} start " + "#" * 30)  # Start of function
    path = None
    url = None
    path_support = False
    url_support = True
    package_name = package['package']
    package_type = package['type']
    repository_name = "iso" + package_name
 
    distribution_name = repository_name
    if 'url' in package:
        url_template = Template(package.get('url', None))  # Use Jinja2 Template for URL
        # Render the URL, substituting Jinja variables if present
        url = url_template.render(**version_variables)
    if 'path' in package:
        path = package['path']
 
    logger.info(f"Processing iso Package: {package_name}, URL: {url}, Path: {path}")
 
    if path is not None and len(path) > 1:
        if os.path.isfile(path):
            path_support = True
            url_support = False
 
    iso_directory = os.path.join(repo_store_path, "offline_repo", 'cluster', cluster_os_type, cluster_os_version, 'iso', package_name)
    base_path = iso_directory.strip("/")
    logger.info(f"Processing iso Package to directory: {iso_directory}")
 
    os.makedirs(iso_directory, exist_ok=True)
 
    if path_support == False and url_support == True:
        try:
            download_file_name = url.split('/')
            logger.info(f"Download file name: {download_file_name[-1]}")
            iso_file_path = os.path.join(iso_directory, download_file_name[-1])
            output_file = download_file_name[-1]
            relative_path = output_file
            # Check if the file already exists
            if os.path.exists(iso_file_path):
                logger.info(f"ISO Package {package_name} already exists at {iso_directory}")
                # Process the iso file using Pulp commands
                logger.info("Processing iso with Pulp...")
                status = "Success"
                status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, package_name, iso_file_path, logger)
            else:
                # Using wget to check if the URL exists (returns 0 for success, non-zero for failure)
                subprocess.run(['wget', '-q', '--spider', '--tries=1', url], check=True)
                iso_tmp_file =  os.path.join('/tmp', download_file_name[-1])
                # Using wget to download the iso file from the URL
                subprocess.run(['wget', '-O', iso_tmp_file, url], check=True)
                shutil.move(iso_tmp_file, iso_file_path)
                # Process the iso file using Pulp commands
                logger.info("Processing iso with Pulp...")
                status = "Success"
                status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, package_name, iso_file_path, logger)
 
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing iso commands: {e}")
            status = "Failed"
        except Exception as e:
            logger.error(f"Error processing iso: {e}")
            status = "Failed"
        finally:
            # Write the status to the file
            write_status_to_file(status_file_path, package_name, package_type, status, logger)
            logger.info("#" * 30 + f" {process_iso.__name__} end " + "#" * 30)  # End of function
            return status
 
    elif path_support == True and url_support == False:
        try:
            shutil.copy(path, iso_directory)
            download_file_name = path.split('/')
            iso_file_path = os.path.join(iso_directory, download_file_name[-1])
            output_file = download_file_name[-1]
            relative_path = output_file
            # Process the iso file using Pulp commands
            logger.info("Processing iso with Pulp...")
            status = "Success"
            status = process_file_without_download(repository_name, output_file, relative_path, base_path, distribution_name, package_name, iso_file_path, logger)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing iso commands: {e}")
            status = "Failed"
        except Exception as e:
            logger.error(f"Error processing iso: {e}")
            status = "Failed"
        finally:
            # Write the status to the file
            write_status_to_file(status_file_path, package_name, package_type, status, logger)
            logger.info("#" * 30 + f" {process_iso.__name__} end " + "#" * 30)  # End of function
            return status
 
def process_pip(package, repo_store_path, status_file_path, logger):
    """
    Process a pip package using Pulp.
 
    Args:
        package (dict): Package info with 'package' (name) and optional 'version'.
        repo_store_path (str): Path to store the downloaded package.
        status_file_path (str): Path to log processing status.
 
    Returns:
        str: "Success" if the process is successful, otherwise "Failed".
    """
    logger.info("#" * 30 + f" {process_pip.__name__} start " + "#" * 30)
    status = "Success"  # Default status, updated if any step fails
 
    try:
        package_name = shlex.quote(package['package']).strip("'\"")
        package_type = package['type']
        version = package.get('version', None)
        pip_repo = "pip_module" + package_name
        distribution_name = pip_repo
 
        logger.info(f"Processing Pip Package: {package_name}, Version: {version}")
 
        # Define storage path
        pip_package_directory = os.path.join(repo_store_path, "offline_repo", 'cluster', 'pip_module', package_name)
        base_package_directory = os.path.join(repo_store_path, "offline_repo", 'cluster', 'pip_module', package_name)
        base_package_directory = base_package_directory.strip("/")
 
        os.makedirs(pip_package_directory, exist_ok=True)  # Ensure directory exists
 
        # Step 1: Download the package
        logger.info("Step 1: Downloading package...")
        download_command = f"pip download -d {shlex.quote(pip_package_directory)} {package_name}"
        if version:
            download_command += f"=={version}"
 
        if not execute_command(download_command, logger):
            status = "Failed"
            logger.error(f"Failed to download {package_name}. Aborting process.")
            return status  # Stop further steps
 
        # Step 2: Create the Pulp repository if it does not exist
        logger.info("Step 2: Checking repository existence...")
        if not execute_command(f"pulp python repository show --name {pip_repo}", logger):
            logger.info(f"Repository {pip_repo} does not exist. Creating it...")
            if not execute_command(f"pulp python repository create --name {pip_repo}", logger):
                status = "Failed"
                logger.error(f"Failed to create repository {pip_repo}. Aborting process.")
                return status  # Stop further steps
 
        # Step 3: Upload the package(s) to Pulp
        logger.info("Step 3: Uploading package to Pulp...")
        for whl_file in os.listdir(pip_package_directory):
            whl_path = os.path.join(pip_package_directory, whl_file)
            if whl_file.endswith(".whl"):
                relative_path = whl_file  # Keep the filename as-is
                upload_command = f"pulp python content upload --repository {pip_repo} --file {whl_path} --relative-path {relative_path}"
                if not execute_command(upload_command, logger):
                    status = "Failed"
                    logger.error(f"Failed to upload {whl_file} to {pip_repo}. Aborting process.")
                    return status  # Stop further steps
 
        # Step 4: Publish the repository
        logger.info("Step 4: Publishing the repository...")
        if not execute_command(f"pulp python publication create --repository {pip_repo}", logger):
            status = "Failed"
            logger.error(f"Failed to publish repository {pip_repo}. Aborting process.")
            return status  # Stop further steps
 
        # Step 5: Create or update the distribution
        logger.info("Step 5: Configuring distribution...")
        if not execute_command(f"pulp python distribution show --name {distribution_name}", logger):
            logger.info(f"Distribution {distribution_name} does not exist. Creating it...")
            if not execute_command(f"pulp python distribution create --name {distribution_name} --repository {pip_repo} --base-path {base_package_directory}", logger):
                status = "Failed"
                logger.error(f"Failed to create distribution {distribution_name}. Aborting process.")
                return status  # Stop further steps
        else:
            logger.info("Updating existing distribution...")
            if not execute_command(f"pulp python distribution update --name {distribution_name} --repository {pip_repo} --base-path {base_package_directory}", logger):
                status = "Failed"
                logger.error(f"Failed to update distribution {distribution_name}. Aborting process.")
                return status  # Stop further steps
 
        logger.info(f"Package {package_name} processed successfully!")
 
    except Exception as e:
        logger.error(f"Unexpected error while processing {package_name}: {str(e)}")
        status = "Failed"
 
    finally:
        # Write status to file
        write_status_to_file(status_file_path, package_name, package_type, status, logger)
 
        logger.info("#" * 30 + f" {process_pip.__name__} end " + "#" * 30)
        return status
