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

import subprocess
import os
from ansible.module_utils.parse_and_download import write_status_to_file
 
def process_rpm(package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, logger):
    """
    Downloads a list of RPM packages and writes the status of the download to a file.

    Args:
        package (dict): A dictionary containing the package name and a list of RPMs to download.
        repo_store_path (str): The path to the repository store.
        status_file_path (str): The path to the status file.
        cluster_os_type (str): The type of the cluster operating system.
        cluster_os_version (str): The version of the cluster operating system.
        logger (logging.Logger): The logger object.

    Returns:
        str: The status of the download.

    Raises:
        Exception: If an error occurs during the download process.
    """

    logger.info("#" * 30 + f" {process_rpm.__name__} start " + "#" * 30)  # Start of function
    try:
        rpm_list = list(set(package["rpm_list"]))
        logger.info(f"{package['package']} - List of rpms is {rpm_list}")
        rpm_directory = os.path.join(repo_store_path, 'offline_repo', 'cluster', cluster_os_type, cluster_os_version, 'rpm')
        logger.info(f"rpm_dir {rpm_directory}")
        os.makedirs(rpm_directory, exist_ok=True)
        dnf_download_command = ['dnf', 'download', '--resolve', '--alldeps', '--arch=x86_64,noarch',
            f'--destdir={rpm_directory}'] + rpm_list
        rpm_result = subprocess.run(dnf_download_command, check=False, capture_output=True, text=True)
        logger.info(f"RPM Download success stdout {rpm_result.stdout}")
        logger.info(f"Return code {rpm_result.returncode}")
        if rpm_result.returncode == 0:
            logger.info(f"RPM download Successful {rpm_result.stdout}")
            status = "Success"
        else:
            logger.error(f"RPM error Return code - {rpm_result.returncode} \nstderr - {rpm_result.stderr}")
            status = "Failed"
    except Exception as e:
        logger.error(f"Error processing rpm packages: {str(e)}")
        status = "Failed"
    finally:
        write_status_to_file(status_file_path, package["package"], "rpm", status, logger)
        logger.info("#" * 30 + f" {process_rpm.__name__} end " + "#" * 30)
        return status
