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

"""Direct RPM-file processing with repository-bound serving reconciliation."""

import os
import subprocess
import tempfile
from urllib.parse import urlsplit

import requests

from ansible.module_utils.repo_manager.download_common import (
    _ensure_pulp_object,
    _reconcile_pulp_distribution,
    execute_command,
    file_lock,
    get_distribution_lock,
    get_pulp_base_path,
    get_repository_lock,
)
from ansible.module_utils.repo_manager.parse_and_download import (
    write_status_to_file,
)
from ansible.module_utils.repo_manager.pulp_commands import pulp_rpm_commands
from ansible.module_utils.repo_manager.security_utils import (
    validate_artifact_identifier,
    validate_artifact_url,
    validate_repository_id,
)


def _ensure_local_rpm(url, rpm_path, logger):
    """Atomically download a missing RPM without retaining partial bytes."""
    if os.path.lexists(rpm_path):
        if os.path.islink(rpm_path) or not os.path.isfile(rpm_path):
            logger.error("Existing direct RPM path is not a regular file")
            return False
        return True

    subprocess.run(
        ['wget', '-q', '--spider', '--tries=1', url], check=True
    )
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(rpm_path)}.",
        suffix=".tmp",
        dir=os.path.dirname(rpm_path),
    )
    os.close(descriptor)
    try:
        if not execute_command(["wget", "-O", temporary_path, url], logger):
            logger.error("Failed to download direct RPM package")
            return False
        if (
                os.path.islink(temporary_path)
                or not os.path.isfile(temporary_path)):
            logger.error("Downloaded direct RPM is not a regular file")
            return False
        os.replace(temporary_path, rpm_path)
        return True
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def process_rpm_file(
        package, status_file_path, content_base_dir, repo_name_arg, logger):
    """Download one direct RPM and reconcile its exact Pulp repository."""
    logger.info("#" * 30 + " %s start " + "#" * 30, process_rpm_file.__name__)
    package_name = "unknown"
    package_type = None
    repo_name = repo_name_arg
    status = "Failed"
    try:
        package_name = validate_artifact_identifier(package['package'])
        package_type = package['type']
        repo_name = validate_repository_id(repo_name_arg)
        url = package.get('url')
        if not url:
            logger.error("No URL provided for RPM file package: %s", package_name)
            return status
        url = validate_artifact_url(url)

        rpm_directory = os.path.join(
            content_base_dir, "rpm_file", package_name
        )
        os.makedirs(rpm_directory, exist_ok=True)
        filename = validate_artifact_identifier(
            os.path.basename(urlsplit(url).path)
        )
        rpm_path = os.path.join(rpm_directory, filename)

        if not _ensure_local_rpm(url, rpm_path, logger):
            return status

        with get_repository_lock(repo_name):
            ensured, _details = _ensure_pulp_object(
                pulp_rpm_commands["show_repository"] % repo_name,
                pulp_rpm_commands["create_repository"] % repo_name,
                f"RPM repository {repo_name}",
                logger,
            )
        if not ensured:
            return status

        if not execute_command(
                pulp_rpm_commands["upload_content"] % (repo_name, rpm_path),
                logger):
            logger.error("Failed to upload direct RPM content")
            return status

        if not execute_command(
                pulp_rpm_commands["publish_repository"] % repo_name, logger):
            logger.error("Failed to publish direct RPM repository")
            return status

        base_path = get_pulp_base_path(os.path.join(
            content_base_dir, "rpms", repo_name
        ))
        with get_distribution_lock(repo_name):
            ready = _reconcile_pulp_distribution(
                pulp_rpm_commands["check_distribution"] % repo_name,
                pulp_rpm_commands["distribute_repository"] % (
                    repo_name, base_path, repo_name,
                ),
                pulp_rpm_commands["update_distribution"] % (
                    repo_name, base_path, repo_name,
                ),
                f"RPM distribution {repo_name}",
                logger,
                pulp_rpm_commands["show_repository"] % repo_name,
            )
        if not ready:
            return status

        if not execute_command(
                pulp_rpm_commands["update_distribution_repo_config"]
                % repo_name,
                logger):
            logger.warning(
                "Failed to enable repo config generation for %s", repo_name
            )

        status = "Success"
        logger.info("RPM file package %s processed successfully", package_name)
        return status
    except (subprocess.CalledProcessError, requests.RequestException,
            IOError, OSError, KeyError, TypeError, ValueError):
        logger.error("Error processing direct RPM package")
        return status
    finally:
        if package_type is not None:
            write_status_to_file(
                status_file_path, package_name, package_type, status,
                logger, file_lock, repo_name,
            )
        logger.info(
            "#" * 30 + " %s end " + "#" * 30,
            process_rpm_file.__name__,
        )
