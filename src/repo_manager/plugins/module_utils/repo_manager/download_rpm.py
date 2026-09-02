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
from collections import OrderedDict
from pathlib import Path
from ansible.module_utils.repo_manager.config import (
    DNF_COMMANDS,
    DNF_INFO_COMMANDS,
    PULP_DISTRIBUTION_ROOT_PARTS,
)
from multiprocessing import Lock
from ansible.module_utils.repo_manager.parse_and_download import write_status_to_file, _prefix_repo_name_with_arch

file_lock = Lock()

# Per-repository locks for RPM operations
_rpm_repository_locks = {}
_rpm_locks_lock = Lock()


# Cache for repo existence checks to avoid repeated Pulp API calls
_repo_exists_cache = {}


def _check_repo_exists_in_pulp(repo_name, logger):
    """
    Check if an RPM repository exists in Pulp.

    Args:
        repo_name (str): Name of the repository to check
        logger: Logger instance

    Returns:
        bool: True if repo exists, False otherwise
    """
    # Check cache first
    if repo_name in _repo_exists_cache:
        return _repo_exists_cache[repo_name]

    try:
        result = subprocess.run(
            ['pulp', 'rpm', 'repository', 'show', '--name', repo_name],
            capture_output=True, text=True, check=False
        )
        exists = result.returncode == 0
        _repo_exists_cache[repo_name] = exists
        if not exists:
            logger.warning(f"Repository '{repo_name}' does not exist in Pulp")
        return exists
    except Exception as e:
        logger.error(f"Error checking repository existence: {e}")
        _repo_exists_cache[repo_name] = False
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


def _dnf_cache_option(repo_store_path, arch_key):
    """Create and return the isolated Repo Manager DNF cache option."""
    cache_directory = os.path.join(
        repo_store_path, ".data", "dnf_cache", arch_key
    )
    os.makedirs(cache_directory, mode=0o755, exist_ok=True)
    return f"--setopt=cachedir={cache_directory}"


def _catalog_repo_priority_option(pkg_name, repo_mapping, status_file_path, logger):
    """Prefer the package's catalog-mapped Pulp repo while resolving dependencies."""
    repo_name = repo_mapping.get(pkg_name, "")
    if not repo_name:
        return None
    prefixed_repo_name = _prefix_repo_name_with_arch(
        repo_name, status_file_path, logger
    )
    return f"--setopt={prefixed_repo_name}.priority=1"


def _group_rpms_by_catalog_repo(rpm_list, repo_mapping, status_file_path, logger):
    """Group packages so every DNF invocation has one preferred source repo."""
    grouped = OrderedDict()
    for pkg_name in rpm_list:
        priority_option = _catalog_repo_priority_option(
            pkg_name, repo_mapping, status_file_path, logger
        )
        grouped.setdefault(priority_option, []).append(pkg_name)
    return grouped


def _build_dnf_download_command(
        arch_key, repo_store_path, rpm_directory, packages,
        preferred_repo_option=None):
    """Build a fresh, Pulp-only, architecture-isolated DNF download command."""
    command = list(DNF_COMMANDS[arch_key])
    command.append(_dnf_cache_option(repo_store_path, arch_key))
    if preferred_repo_option:
        command.append(preferred_repo_option)
    command.append(f"--destdir={rpm_directory}")
    command.extend(packages)
    return command


def _validated_dnf_architecture(architecture):
    """Return a supported DNF architecture without implicit ARM fallback."""
    arch_key = str(architecture or "").lower()
    if arch_key not in DNF_COMMANDS or arch_key not in DNF_INFO_COMMANDS:
        raise ValueError(f"Unsupported RPM architecture: {architecture}")
    return arch_key


def _catalog_package_type(package_name, rpm_type_mapping):
    """Return the original catalog RPM type with a backward-compatible default."""
    package_type = rpm_type_mapping.get(package_name, "rpm")
    return package_type if package_type in ("rpm", "rpm_repo") else "rpm"


def _write_rpm_status(status_file_path, package_name, status, logger,
                      repo_mapping, rpm_type_mapping):
    """Write status using the package's original catalog identity."""
    write_status_to_file(
        status_file_path,
        package_name,
        _catalog_package_type(package_name, rpm_type_mapping),
        status,
        logger,
        file_lock,
        repo_mapping.get(package_name, ""),
    )


def _download_rpm_packages(
        rpm_list, repo_store_path, status_file_path, cluster_os_type,
        cluster_os_version, arc, logger, repo_mapping, rpm_type_mapping,
        require_mapped_repo=False):
    """Download requested RPMs and dependencies through architecture-scoped Pulp repos."""
    sw_json_name = Path(status_file_path).parent.name
    rpm_directory = os.path.join(
        repo_store_path, *PULP_DISTRIBUTION_ROOT_PARTS, arc.lower(),
        cluster_os_type, cluster_os_version, 'rpm', sw_json_name
    )
    logger.info("rpm_dir %s", rpm_directory)
    os.makedirs(rpm_directory, exist_ok=True)

    arch_key = _validated_dnf_architecture(arc)
    download_candidates = []
    failed = []

    for pkg in rpm_list:
        pkg_repo_name = repo_mapping.get(pkg, "")
        if require_mapped_repo and not pkg_repo_name:
            failed.append(pkg)
            _write_rpm_status(
                status_file_path, pkg, "Failed", logger,
                repo_mapping, rpm_type_mapping
            )
            logger.error(
                "Package '%s' cannot be downloaded because its catalog source "
                "does not define repo_name", pkg
            )
            continue

        if require_mapped_repo:
            prefixed_repo_name = _prefix_repo_name_with_arch(
                pkg_repo_name, status_file_path, logger
            )
            if not _check_repo_exists_in_pulp(prefixed_repo_name, logger):
                failed.append(pkg)
                _write_rpm_status(
                    status_file_path, pkg, "Failed", logger,
                    repo_mapping, rpm_type_mapping
                )
                logger.error(
                    "Package '%s' cannot be downloaded because repository '%s' "
                    "does not exist in Pulp", pkg, prefixed_repo_name
                )
                continue

        download_candidates.append(pkg)

    command_results = {}
    grouped_rpms = _group_rpms_by_catalog_repo(
        download_candidates, repo_mapping, status_file_path, logger
    )
    for preferred_repo_option, repo_rpms in grouped_rpms.items():
        dnf_download_command = _build_dnf_download_command(
            arch_key, repo_store_path, rpm_directory, repo_rpms,
            preferred_repo_option
        )
        logger.info("Executing command: %s", " ".join(dnf_download_command))
        result = subprocess.run(
            dnf_download_command,
            check=False,
            capture_output=True,
            text=True
        )
        logger.info("Return code: %s", result.returncode)
        if result.returncode != 0 and result.stderr and result.stderr.strip():
            logger.error("STDERR: %s", result.stderr.strip())
        logger.debug("STDOUT:\n%s", result.stdout)
        logger.debug("STDERR:\n%s", result.stderr)
        for pkg in repo_rpms:
            command_results[pkg] = result

    downloaded = []
    retry_packages = []
    for pkg in download_candidates:
        pkg_result = command_results[pkg]
        stderr_lines = (pkg_result.stderr or "").splitlines()
        pkg_not_found = any(
            pkg in line and (
                "No match for argument" in line
                or "No package" in line
                or "not found" in line.lower()
            )
            for line in stderr_lines
        )
        if _check_rpm_downloaded(rpm_directory, pkg) and not pkg_not_found:
            downloaded.append(pkg)
            _write_rpm_status(
                status_file_path, pkg, "Success", logger,
                repo_mapping, rpm_type_mapping
            )
            logger.info("Package '%s' downloaded successfully.", pkg)
        else:
            retry_packages.append(pkg)
            if pkg_not_found:
                logger.warning(
                    "Package '%s' not found in configured repositories", pkg
                )

    if retry_packages:
        logger.warning("Retrying failed packages individually: %s", retry_packages)
    for pkg in retry_packages:
        preferred_repo_option = _catalog_repo_priority_option(
            pkg, repo_mapping, status_file_path, logger
        )
        command = _build_dnf_download_command(
            arch_key, repo_store_path, rpm_directory, [pkg],
            preferred_repo_option
        )
        logger.info("Executing command: %s", " ".join(command))
        retry_result = subprocess.run(
            command, check=False, capture_output=True, text=True
        )
        logger.info("Return code: %s", retry_result.returncode)
        if (retry_result.returncode != 0 and retry_result.stderr
                and retry_result.stderr.strip()):
            logger.error("STDERR: %s", retry_result.stderr.strip())

        retry_stderr = (retry_result.stderr or "").lower()
        pkg_invalid = any(error in retry_stderr for error in (
            "no match for argument", "no package", "not found",
            "unable to find a match"
        ))
        if (retry_result.returncode == 0
                and _check_rpm_downloaded(rpm_directory, pkg)):
            downloaded.append(pkg)
            _write_rpm_status(
                status_file_path, pkg, "Success", logger,
                repo_mapping, rpm_type_mapping
            )
            logger.info("Package '%s' downloaded successfully on retry.", pkg)
        else:
            failed.append(pkg)
            _write_rpm_status(
                status_file_path, pkg, "Failed", logger,
                repo_mapping, rpm_type_mapping
            )
            if pkg_invalid:
                logger.error(
                    "Package '%s' does not exist in configured repositories.", pkg
                )
            else:
                logger.error("Package '%s' still failed after retry.", pkg)

    return downloaded, failed


def _validate_rpm_packages(
        rpm_list, repo_store_path, status_file_path, arc, logger,
        repo_mapping, rpm_type_mapping):
    """Validate ordinary partial-policy RPMs without downloading their payloads."""
    arch_key = _validated_dnf_architecture(arc)
    dnf_cache_option = _dnf_cache_option(repo_store_path, arch_key)
    valid_packages = []
    invalid_packages = []

    for pkg in rpm_list:
        pkg_repo_name = repo_mapping.get(pkg, "")
        if not pkg_repo_name:
            invalid_packages.append(pkg)
            _write_rpm_status(
                status_file_path, pkg, "Failed", logger,
                repo_mapping, rpm_type_mapping
            )
            logger.error(
                "Package '%s' cannot be validated because its catalog source "
                "does not define repo_name", pkg
            )
            continue

        prefixed_repo_name = _prefix_repo_name_with_arch(
            pkg_repo_name, status_file_path, logger
        )
        if not _check_repo_exists_in_pulp(prefixed_repo_name, logger):
            invalid_packages.append(pkg)
            _write_rpm_status(
                status_file_path, pkg, "Failed", logger,
                repo_mapping, rpm_type_mapping
            )
            logger.error(
                "Package '%s' skipped - repository '%s' does not exist in Pulp. "
                "Please sync the repository first.", pkg, prefixed_repo_name
            )
            continue

        dnf_info_command = DNF_INFO_COMMANDS[arch_key] + [
            dnf_cache_option,
            f"--repo={prefixed_repo_name}",
            pkg,
        ]
        logger.info("Executing command: %s", " ".join(dnf_info_command))
        result = subprocess.run(
            dnf_info_command,
            check=False,
            capture_output=True,
            text=True
        )
        logger.info("Return code: %s", result.returncode)
        if result.returncode != 0 and result.stderr and result.stderr.strip():
            logger.error("STDERR: %s", result.stderr.strip())
        if result.returncode == 0:
            valid_packages.append(pkg)
            _write_rpm_status(
                status_file_path, pkg, "Success", logger,
                repo_mapping, rpm_type_mapping
            )
            logger.info("Package '%s' validated successfully", pkg)
        else:
            invalid_packages.append(pkg)
            _write_rpm_status(
                status_file_path, pkg, "Failed", logger,
                repo_mapping, rpm_type_mapping
            )
            logger.error(
                "Package '%s' validation failed. Package may not exist in "
                "repository '%s'.", pkg, prefixed_repo_name
            )

    return valid_packages, invalid_packages


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

    logger.info(f"--- {process_rpm.__name__} START ---")
    status = "Failed"

    try:
        repo_mapping = package.get("repo_mapping", {})
        rpm_type_mapping = package.get("rpm_type_mapping", {})
        rpm_list = list(dict.fromkeys(package["rpm_list"]))
        logger.info("%s - List of rpms is %s", package["package"], rpm_list)

        if repo_config_value == "always":
            download_packages = rpm_list
            validation_packages = []
            require_mapped_repo = False
        else:
            download_packages = [
                pkg for pkg in rpm_list
                if _catalog_package_type(pkg, rpm_type_mapping) == "rpm_repo"
            ]
            validation_packages = [
                pkg for pkg in rpm_list if pkg not in download_packages
            ]
            require_mapped_repo = True
            logger.info(
                "Partial policy: validating %d rpm package(s) with dnf info and "
                "downloading %d rpm_repo package(s) with dependencies",
                len(validation_packages), len(download_packages)
            )

        successful_packages = []
        failed_packages = []
        if download_packages:
            downloaded, download_failed = _download_rpm_packages(
                download_packages, repo_store_path, status_file_path,
                cluster_os_type, cluster_os_version, arc, logger,
                repo_mapping, rpm_type_mapping, require_mapped_repo
            )
            successful_packages.extend(downloaded)
            failed_packages.extend(download_failed)

        if validation_packages:
            validated, validation_failed = _validate_rpm_packages(
                validation_packages, repo_store_path, status_file_path, arc,
                logger, repo_mapping, rpm_type_mapping
            )
            successful_packages.extend(validated)
            failed_packages.extend(validation_failed)

        if not failed_packages and len(successful_packages) == len(rpm_list):
            status = "Success"
        elif successful_packages:
            status = "Partial"
        else:
            status = "Failed"

    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        status = "Failed"
        repo_mapping = package.get("repo_mapping", {})
        rpm_type_mapping = package.get("rpm_type_mapping", {})
        for pkg in package.get("rpm_list", []):
            _write_rpm_status(
                status_file_path, pkg, "Failed", logger,
                repo_mapping, rpm_type_mapping
            )

    finally:
        logger.info(f"Overall status for {package['package']}: {status}")
        logger.info(f"--- {process_rpm.__name__} END ---")
    return status
