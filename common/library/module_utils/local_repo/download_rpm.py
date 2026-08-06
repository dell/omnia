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

# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments
"""This module handles downloading RPM files for local repository"""

import subprocess
import os
import glob
import json
import shutil
from pathlib import Path
from ansible.module_utils.local_repo.config import (
    DNF_COMMANDS,
    DNF_INFO_COMMANDS,
    PULP_RPM_PACKAGES_API
)
from multiprocessing import Lock
from ansible.module_utils.local_repo.parse_and_download import write_status_to_file, _prefix_repo_name_with_arch

file_lock = Lock()


def _is_dnf_available():
    """Check if dnf binary is available on the system."""
    return shutil.which('dnf') is not None


def _pulp_cmd(cmd_string, logger=None):
    """Run a pulp CLI command and return parsed JSON output, or None on failure."""
    result = subprocess.run(cmd_string, shell=True, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        if logger:
            logger.debug(f"Pulp command failed: {cmd_string}, stderr: {result.stderr}")
        return None
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _pulp_get_repo_version(repo_name, logger):
    """Get latest_version_href for a Pulp RPM repository."""
    data = _pulp_cmd(f"pulp rpm repository show --name {repo_name}", logger)
    if isinstance(data, dict):
        return data.get("latest_version_href", "")
    return ""


def _pulp_find_package(pkg_name, repo_name, logger):
    """Find RPM package in a Pulp repository. Returns package info dict or None."""
    version_href = _pulp_get_repo_version(repo_name, logger)
    if not version_href:
        return None
    api_url = f"{PULP_RPM_PACKAGES_API}?name={pkg_name}&repository_version={version_href}&limit=1"
    data = _pulp_cmd(f"pulp show --href '{api_url}'", logger)
    if isinstance(data, dict) and data.get("count", 0) > 0:
        return data.get("results", [None])[0]
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return None


def _pulp_validate_package(pkg_name, repo_name, logger):
    """Check if package exists in Pulp repo (replaces dnf info)."""
    return _pulp_find_package(pkg_name, repo_name, logger) is not None


def _pulp_download_rpm(pkg_name, repo_name, rpm_directory, logger):
    """Download a single RPM from Pulp distribution (replaces dnf download)."""
    pkg_info = _pulp_find_package(pkg_name, repo_name, logger)
    if not pkg_info:
        logger.error(f"Package '{pkg_name}' not found in Pulp repo '{repo_name}'")
        return False
    location_href = pkg_info.get("location_href", "")
    if not location_href:
        logger.error(f"No location_href for package '{pkg_name}'")
        return False
    dist_data = _pulp_cmd(f"pulp rpm distribution show --name {repo_name}", logger)
    if not isinstance(dist_data, dict) or not dist_data.get("base_url"):
        logger.error(f"Could not get distribution URL for '{repo_name}'")
        return False
    base_url = dist_data["base_url"].rstrip("/")
    download_url = f"{base_url}/{location_href}"
    logger.info(f"Downloading '{pkg_name}' from {download_url}")
    dl_result = subprocess.run(
        ["wget", "-c", "-q", "--no-check-certificate", "-P", rpm_directory, download_url],
        check=False, capture_output=True, text=True
    )
    if dl_result.returncode == 0 or _check_rpm_downloaded(rpm_directory, pkg_name):
        return True
    logger.error(f"wget failed for '{pkg_name}': {dl_result.stderr}")
    return False

def _check_rpm_downloaded(rpm_directory, pkg_name):
    """
    Check if an RPM file for the given package exists in the directory.
    This is more reliable than parsing DNF output which varies between DNF4 and DNF5.

    Args:
        rpm_directory (str): Directory where RPMs are downloaded
        pkg_name (str): Package name to check for

    Returns:
        bool: True if RPM file exists for the package
    """
    # Look for RPM files that start with the package name
    # Pattern: pkg_name-version-release.arch.rpm
    pattern = os.path.join(rpm_directory, f"{pkg_name}-[0-9]*.rpm")
    matches = glob.glob(pattern)
    if matches:
        return True

    # Also check for exact match pattern (some packages have numbers in name)
    pattern2 = os.path.join(rpm_directory, f"{pkg_name}-*.rpm")
    for match in glob.glob(pattern2):
        # Extract just the filename
        filename = os.path.basename(match)
        # Check if filename starts with pkg_name followed by a dash and version
        if filename.startswith(f"{pkg_name}-"):
            return True

    return False

def process_rpm(package, repo_store_path, status_file_path, cluster_os_type,
               cluster_os_version, repo_config_value, arc, logger):
    """
        Downloads RPMs using DNF based on repo configuration, retries failures,
        writes status to file, and returns overall status: Success, Partial, or Failed.
    Args:
            package (dict): Package info with "package" name and "rpm_list".
            repo_store_path (str): Local path to store downloaded RPMs.
            status_file_path (str): CSV path to record RPM download status.
            cluster_os_type (str): OS type (e.g., "rhel").
            cluster_os_version (str): OS version (e.g., "9.2").
            repo_config_value (str): Repo mode: "always", "partial"
            arc (str): Architecture ("x86_64" or "aarch64").
            logger (Logger): Logger instance.

        Returns:
            str: "Success", "Partial", or "Failed".
    """

    logger.info("#" * 30 + f" {process_rpm.__name__} start " + "#" * 30)

    try:
        # Get repo_mapping for individual RPM repo names
        repo_mapping = package.get("repo_mapping", {})

        if repo_config_value == "always":
            rpm_list = list(set(package["rpm_list"]))
            logger.info(f"{package['package']} - List of rpms is {rpm_list}")

            sw_json_name = Path(status_file_path).parent.name
            logger.info(f"Software rpms : {sw_json_name}")

            rpm_directory = os.path.join(
                repo_store_path, 'offline_repo',
                'cluster', arc.lower(), cluster_os_type, cluster_os_version, 'rpm', sw_json_name
            )
            logger.info(f"rpm_dir {rpm_directory}")
            os.makedirs(rpm_directory, exist_ok=True)

            arch_key = "x86_64" if arc.lower() in ("x86_64") else "aarch64"

            downloaded = []
            failed = []

            if _is_dnf_available():
               # First try to download all at once
                dnf_download_command = (
                    DNF_COMMANDS[arch_key]
                    + [f"--destdir={rpm_directory}"]
                    + rpm_list
                )

                result = subprocess.run(
                    dnf_download_command,
                    check=False,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Return code {result.returncode}")
                logger.debug(f"STDOUT:\n{result.stdout}")
                logger.debug(f"STDERR:\n{result.stderr}")

                stdout_lines = result.stdout.splitlines()
                stderr_lines = result.stderr.splitlines()

                # Detect successes/failures from combined run
                # Use filesystem check instead of parsing output (works with both DNF4 and DNF5)
                for pkg in rpm_list:
                    # Get repo_name for this specific RPM from mapping
                    pkg_repo_name = repo_mapping.get(pkg, "")

                    # Check if package was downloaded by looking for the RPM file
                    pkg_downloaded = _check_rpm_downloaded(rpm_directory, pkg)

                    # Also check for "No match for argument" or "No package" errors in stderr
                    pkg_not_found = False
                    for line in stderr_lines:
                        if pkg in line and ("No match for argument" in line or
                                           "No package" in line or
                                           "not found" in line.lower()):
                            pkg_not_found = True
                            break

                    if pkg_downloaded and not pkg_not_found:
                        downloaded.append(pkg)
                        write_status_to_file(status_file_path, pkg, "rpm", "Success", logger, file_lock, pkg_repo_name)
                        logger.info(f"Package '{pkg}' downloaded successfully.")
                    else:
                        failed.append(pkg)
                        if pkg_not_found:
                            logger.warning(f"Package '{pkg}' not found in configured repositories")

                # Retry failed ones individually
                if failed:
                    logger.warning(f"Retrying failed packages individually: {failed}")
                    for pkg in failed[:]:
                        cmd = DNF_COMMANDS[arch_key] + [f'--destdir={rpm_directory}', pkg]
                        retry_res = subprocess.run(cmd, check=False, capture_output=True, text=True)
                        # Get repo_name for this specific RPM from mapping
                        pkg_repo_name = repo_mapping.get(pkg, "")

                        # Check for package not found errors
                        retry_stderr = retry_res.stderr.lower()
                        pkg_invalid = any(err in retry_stderr for err in [
                            "no match for argument",
                            "no package",
                            "not found",
                            "unable to find a match"
                        ])

                        # Check if RPM file exists after retry (works with both DNF4 and DNF5)
                        if retry_res.returncode == 0 and _check_rpm_downloaded(rpm_directory, pkg):
                            downloaded.append(pkg)
                            failed.remove(pkg)
                            write_status_to_file(status_file_path, pkg, "rpm", "Success", logger, file_lock, pkg_repo_name)
                            logger.info(f"Package '{pkg}' downloaded successfully on retry.")
                        else:
                            write_status_to_file(status_file_path, pkg, "rpm", "Failed", logger, file_lock, pkg_repo_name)
                            if pkg_invalid:
                                logger.error(f"Package '{pkg}' does not exist in configured repositories.")
                            else:
                                logger.error(f"Package '{pkg}' still failed after retry.")

            else:
                # Pulp-based download (dnf not available, e.g. Wolfi container)
                logger.info("dnf not available, using Pulp CLI for RPM download")
                for pkg in rpm_list:
                    pkg_repo_name = repo_mapping.get(pkg, "")
                    if pkg_repo_name:
                        prefixed_repo_name = _prefix_repo_name_with_arch(pkg_repo_name, status_file_path, logger)
                        if _pulp_download_rpm(pkg, prefixed_repo_name, rpm_directory, logger):
                            downloaded.append(pkg)
                            write_status_to_file(status_file_path, pkg, "rpm", "Success", logger, file_lock, pkg_repo_name)
                            logger.info(f"Package '{pkg}' downloaded successfully via Pulp.")
                        else:
                            failed.append(pkg)
                            write_status_to_file(status_file_path, pkg, "rpm", "Failed", logger, file_lock, pkg_repo_name)
                            logger.error(f"Package '{pkg}' download failed via Pulp.")
                    else:
                        failed.append(pkg)
                        logger.warning(f"No repo_name mapping for package '{pkg}', cannot download via Pulp")
                        write_status_to_file(status_file_path, pkg, "rpm", "Failed", logger, file_lock, "")

            # Determine final status
            if not failed:
                status = "Success"
            elif downloaded:
                status = "Partial"
            else:
                status = "Failed"

        else:
            logger.info("RPM won't be downloaded when repo_config is partial or never")

            arch_key = "x86_64" if arc.lower() in ("x86_64") else "aarch64"
            valid_packages = []
            invalid_packages = []
            use_dnf = _is_dnf_available()

            if use_dnf:
                logger.info("Validating package availability using dnf info...")
            else:
                logger.info("dnf not available, validating package availability using Pulp CLI...")

            for pkg in package["rpm_list"]:
                # Get repo_name for this specific RPM from mapping
                pkg_repo_name = repo_mapping.get(pkg, "")

                if not pkg_repo_name:
                    # Skip validation if no specific repo is defined
                    logger.warning(f"No repo_name defined for package '{pkg}', skipping validation")
                    continue

                # Apply architecture prefixing if needed
                prefixed_repo_name = _prefix_repo_name_with_arch(pkg_repo_name, status_file_path, logger)

                if use_dnf:
                    # Validate package using dnf info with specific repo
                    dnf_info_command = DNF_INFO_COMMANDS[arch_key] + [
                        f"--repo={prefixed_repo_name}",  # Search specific repo from JSON
                        pkg
                    ]
                    result = subprocess.run(
                        dnf_info_command,
                        check=False,
                        capture_output=True,
                        text=True
                    )
                    pkg_exists = result.returncode == 0
                else:
                    # Validate package using Pulp CLI
                    pkg_exists = _pulp_validate_package(pkg, prefixed_repo_name, logger)

                if pkg_exists:
                    # Package exists and is available
                    valid_packages.append(pkg)
                    write_status_to_file(
                        status_file_path, pkg, "rpm", "Success",
                        logger, file_lock, pkg_repo_name
                    )
                    logger.info(f"Package '{pkg}' validated successfully")
                else:
                    # Package not found or invalid
                    invalid_packages.append(pkg)
                    write_status_to_file(
                        status_file_path, pkg, "rpm", "Failed",
                        logger, file_lock, pkg_repo_name
                    )
                    logger.error(
                        f"Package '{pkg}' validation failed. "
                        f"Package may not exist in repository '{prefixed_repo_name}'."
                    )

            # Determine final status based on validation results
            if not invalid_packages:
                status = "Success"
            elif valid_packages:
                status = "Partial"
            else:
                status = "Failed"

            logger.info(
                f"Validation complete - Valid: {len(valid_packages)}, "
                f"Invalid: {len(invalid_packages)}"
            )

    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        status = "Failed"
        for pkg in package.get("rpm_list", []):
            # Get repo_name for this specific RPM from mapping
            pkg_repo_name = repo_mapping.get(pkg, "")
            write_status_to_file(status_file_path, pkg, "rpm", "Failed", logger, file_lock, pkg_repo_name)

    finally:
        logger.info(f"Overall status for {package['package']}: {status}")
        logger.info("#" * 30 + f" {process_rpm.__name__} end " + "#" * 30)
    return status
