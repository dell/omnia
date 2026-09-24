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
# pylint:
# disable=import-error,line-too-long,no-name-in-module,too-many-return-statements,too-many-statements,too-many-arguments,too-many-branches,too-many-locals,too-many-nested-blocks

"""
Handle pulp file downloads for local repository.

This module provides:
- File download operations for various content types
- Download task processing and management
- Content validation and error handling
- Download status tracking and reporting
"""
import base64
import json
import logging
import os
import shutil
import subprocess
import time
from multiprocessing import Lock
from urllib.parse import quote, urlsplit
import requests
from requests.adapters import HTTPAdapter
from ansible.module_utils.repo_manager.parse_and_download import write_status_to_file, execute_command
from ansible.module_utils.repo_manager.rest_client import RestClient
from ansible.module_utils.repo_manager.common_functions import load_pulp_config
from ansible.module_utils.repo_manager.config import (
    ARCH_SUFFIXES,
    REPO_MANAGER_RUNTIME_DIR,
    CLI_FILE_PATH,
    ISO_TIMEOUT_MIN,
    TAR_TIMEOUT_MIN,
    FILE_TIMEOUT_MIN,
    TASK_POLL_INTERVAL,
    FILE_URI,
    OS_TARGET_PYTHON,
    ARCH_PIP_PLATFORMS,
    PULP_DISTRIBUTION_ROOT,
    PULP_DISTRIBUTION_ROOT_PARTS,
    PULP_SSL_CA_CERT,
)
from ansible.module_utils.repo_manager.pulp_commands import (
    pulp_file_commands,
    pulp_python_commands,
)
from ansible.module_utils.repo_manager.pulp_file_python_manager import (
    ensure_pulp_object,
    reconcile_file_content,
    reconcile_pulp_distribution,
    reconcile_python_content,
)
from ansible.module_utils.repo_manager.python_artifact_processor import (
    artifacts_are_platform_independent,
    build_pip_platform_args,
    download_python_artifacts,
)
from ansible.module_utils.repo_manager.git_artifact_processor import (
    create_git_tarball,
    resolve_git_ref,
)
from ansible.module_utils.repo_manager.shared_artifact_state import (
    SharedArtifactCache,
    SharedArtifactStateError,
    build_source_key,
    file_sha256,
    probe_http_validator,
)
from ansible.module_utils.repo_manager.software_utils import build_repo_name
from ansible.module_utils.repo_manager.security_utils import (
    render_catalog_placeholders,
    validate_artifact_url,
    normalize_pulp_distribution_url,
    parse_python_requirement,
    validate_artifact_identifier,
    validate_python_package_version,
    validate_python_repository_id,
    validate_repository_id,
)

file_lock = Lock()

# Per-resource locks for Pulp operations (non-image types)
_repository_locks = {}
_distribution_locks = {}
_locks_lock = Lock()


def _shared_artifact_cache(content_base_dir, logger):
    """Return the optional verified cache for this configured data root."""
    try:
        return SharedArtifactCache.from_content_base_dir(
            content_base_dir, PULP_DISTRIBUTION_ROOT, logger
        )
    except SharedArtifactStateError:
        logger.info(
            "Shared artifact cache is unavailable for this content path; "
            "normal processing will continue"
        )
        return None


def _content_architecture(content_base_dir):
    """Return the architecture encoded in a managed content path."""
    path_parts = os.path.normpath(content_base_dir).split(os.sep)
    root_parts = list(PULP_DISTRIBUTION_ROOT_PARTS)
    for index in range(len(path_parts) - len(root_parts) + 1):
        if path_parts[index:index + len(root_parts)] != root_parts:
            continue
        architecture_index = index + len(root_parts)
        if architecture_index < len(path_parts):
            architecture = path_parts[architecture_index]
            if architecture in ARCH_SUFFIXES:
                return architecture
    return None


def _ensure_pulp_object(show_command, create_command, object_label, logger):
    """Compatibility facade for the shared File/Python lifecycle helper."""
    return ensure_pulp_object(
        show_command, create_command, object_label, logger, execute_command
    )


def _reconcile_pulp_distribution(
        show_command, create_command, update_command, object_label, logger,
        repository_show_command=None):
    """Compatibility facade for fail-closed distribution reconciliation."""
    return reconcile_pulp_distribution(
        show_command, create_command, update_command, object_label,
        logger, execute_command, repository_show_command,
    )


def _reconcile_file_content(repository_name, file_path, relative_path, logger):
    """Compatibility facade for exact File content reconciliation."""
    return reconcile_file_content(
        repository_name, file_path, relative_path, logger, execute_command
    )


def _reconcile_python_content(repository_name, file_path, logger):
    """Compatibility facade for exact Python content reconciliation."""
    return reconcile_python_content(
        repository_name, file_path, logger, execute_command
    )


def get_repository_lock(repo_name):
    """
    Get or create lock for specific repository.

    This allows different repositories to be processed in parallel
    while preventing race conditions for the same repository.

    Args:
        repo_name (str): The repository name to get a lock for.

    Returns:
        Lock: The lock for this specific repository.
    """
    with _locks_lock:
        if repo_name not in _repository_locks:
            _repository_locks[repo_name] = Lock()
        return _repository_locks[repo_name]


def get_distribution_lock(dist_name):
    """
    Get or create lock for specific distribution.

    Args:
        dist_name (str): The distribution name to get a lock for.

    Returns:
        Lock: The lock for this specific distribution.
    """
    with _locks_lock:
        if dist_name not in _distribution_locks:
            _distribution_locks[dist_name] = Lock()
        return _distribution_locks[dist_name]


# Mapping from task type to the prefix used in the Pulp repo name.
# E.g. a tarball package "helm-v3.19.0" becomes "tarballhelm-v3.19.0".
TASK_TYPE_PREFIX = {
    "manifest": "manifest",
    "git": "git",
    "shell": "shell",
    "ansible_galaxy_collection": "ansible_galaxy_collection",
    "tarball": "tarball",
    "iso": "iso",
    "pip_module": "pip_module",
    "rpm_file": "",
}


def build_task_repo_name(task, arc, cluster_os_type, cluster_os_version,
                         version_variables=None):
    """Build the Pulp repository name for a download task.

    Resolves supported version placeholders in the package name, prepends
    the type-specific prefix, and delegates to ``build_repo_name()``.

    Args:
        task (dict): Task dict with at least ``package`` and ``type`` keys.
        arc (str): Architecture (e.g. ``x86_64``).
        cluster_os_type (str): OS type (e.g. ``rhel``).
        cluster_os_version (str): OS version (e.g. ``10.0``).
        version_variables (dict, optional): Values for catalog placeholders.
            Required for tarball / iso tasks whose package
            name may contain ``{{ … }}`` placeholders.

    Returns:
        str: Fully-qualified Pulp repository name.
    """
    raw_name = task.get("package", "")
    raw_name = render_catalog_placeholders(
        raw_name, version_variables or {}, "package name"
    )
    prefix = TASK_TYPE_PREFIX.get(task.get("type", ""), "")
    if task.get("type") == "pip_module":
        _package_name, _version, raw_name = parse_python_requirement(
            raw_name, task.get("version")
        )
        return validate_python_repository_id(build_repo_name(
            arc.lower(), cluster_os_type, cluster_os_version, prefix + raw_name
        ))

    raw_name = validate_artifact_identifier(raw_name)
    return validate_repository_id(build_repo_name(
        arc.lower(), cluster_os_type, cluster_os_version, prefix + raw_name
    ))


def build_content_base_dir(repo_store_path, arc, cluster_os_type, cluster_os_version):
    """Return the common base directory for offline content.

    Every process_* function stores artefacts under::

        <repo_store_path>/offline_repo/cluster/<arc>/<os_type>/<os_version>/

    Building this once avoids repeating the same ``os.path.join`` in every
    function.

    Args:
        repo_store_path (str): Root store path (e.g. ``{{ omnia_base_dir }}``).
        arc (str): Architecture (e.g. ``x86_64``).
        cluster_os_type (str): OS type (e.g. ``rhel``).
        cluster_os_version (str): OS version (e.g. ``10.0``).

    Returns:
        str: Absolute path to the base content directory.
    """
    return os.path.join(
        repo_store_path, *PULP_DISTRIBUTION_ROOT_PARTS,
        arc.lower(), cluster_os_type, cluster_os_version,
    )


def get_pulp_base_path(absolute_path):
    """Convert absolute filesystem path to Pulp distribution base_path.

    Pulp base_path must be relative to the content root. The configured
    distribution root is retained in the published path (for example,
    ``offline_repo/cluster/x86_64/rhel/10.0/git/karavi-observability``).

    Args:
        absolute_path (str): Absolute directory path on the filesystem.

    Returns:
        str: Relative base_path for Pulp distribution.
    """
    normalized = os.path.normpath(absolute_path)
    marker = os.sep + PULP_DISTRIBUTION_ROOT.replace('/', os.sep) + os.sep
    if marker in normalized:
        idx = normalized.find(marker) + 1
        return normalized[idx:].replace(os.sep, '/').strip('/')
    # Fallback: compute relative to the Omnia base directory
    repo_base = os.environ.get(
        'REPO_MANAGER_DATA_PATH', REPO_MANAGER_RUNTIME_DIR
    )
    return os.path.relpath(absolute_path, repo_base).replace(
        os.sep, '/'
    ).strip('/')


CHUNK_SIZE = 10 * 1024 * 1024  # 10MB
MAX_RETRY = 5  # retry resume up to 5 times


def download_file_distribution(distribution_name, dl_directory, relative_path, logger):
    """
    Download a file from a given distribution and save it locally.

    Args:
        distribution_name (str): Name of the distribution from which the file will be downloaded.
        dl_directory (str): Local directory path where the downloaded file should be stored.
        relative_path (str): Relative path of the file in the distribution.
        logger (logging.Logger): Logger instance for logging download progress, success, or errors.

    Returns:
        str: "Success" if the download is completed successfully.

    Raises:
        subprocess.CalledProcessError: If the file download command fails.
        Exception: For any other unexpected errors encountered during execution.
    """

    def sanitize_path(base_directory: str, requested_path: str) -> str:
        if not requested_path or os.path.isabs(requested_path):
            raise ValueError("Invalid path traversal detected")
        path_segments = requested_path.replace("\\", "/").split("/")
        if any(segment in ("", ".", "..") for segment in path_segments):
            raise ValueError("Invalid path traversal detected")
        base_directory = os.path.abspath(base_directory)
        safe_path = os.path.abspath(os.path.join(base_directory, requested_path))
        if os.path.commonpath((base_directory, safe_path)) != base_directory:
            raise ValueError("Invalid path traversal detected")
        return safe_path

    try:
        cmd = pulp_file_commands["show_distribution"] % distribution_name
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)

        pulp_config = load_pulp_config(CLI_FILE_PATH)
        base_url = normalize_pulp_distribution_url(
            data.get("base_url"), pulp_config.get("base_url")
        )
        full_url = f"{base_url}{quote(relative_path, safe='/@:+,=~.-_')}"

        local_path = sanitize_path(dl_directory, relative_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        retry = 0
        while retry <= MAX_RETRY:

            downloaded_bytes = os.path.getsize(local_path) if os.path.exists(local_path) else 0
            headers = {"Range": f"bytes={downloaded_bytes}-"} if downloaded_bytes > 0 else {}

            session = requests.Session()
            session.mount("https://", HTTPAdapter(max_retries=3))

            try:
                logger.info(f"Attempt {retry + 1}: Downloading from byte {downloaded_bytes}")

                with session.get(
                    full_url,
                    stream=True,
                    headers=headers,
                    verify=(
                        os.environ.get("PULP_CA_BUNDLE")
                        or PULP_SSL_CA_CERT
                    ),
                    timeout=(30, 600)
                ) as r:

                    if r.status_code == 416:
                        logger.info("File already complete. No download needed.")
                        return "Success"

                    if r.status_code not in (200, 206):
                        logger.error(f"HTTP error: {r.status_code}")
                        raise requests.exceptions.HTTPError("Bad status code")

                    total = int(r.headers.get("Content-Length", 0))
                    total_size = downloaded_bytes + total

                    mode = "ab" if downloaded_bytes else "wb"

                    with open(local_path, mode) as f:
                        current = downloaded_bytes
                        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                            if not chunk:
                                continue
                            f.write(chunk)
                            current += len(chunk)
                            logger.info(
                                f"Progress: {
                                    round(
                                        (current / total_size) * 100,
                                        2)}% ({current}/{total_size} bytes)")

                # Final size check
                if os.path.getsize(local_path) == total_size:
                    logger.info(f"Download completed successfully: {local_path}")
                    return "Success"
                raise ValueError("File size mismatch after download")

            except (requests.exceptions.RequestException, IOError, ValueError):
                logger.error("File distribution download was interrupted")
                retry += 1
                wait = 5 * retry
                logger.info(f"Retrying in {wait} seconds...")
                time.sleep(wait)

        logger.error("Max retries exceeded, download failed.")
        return "Failed"

    except (
            json.JSONDecodeError,
            requests.exceptions.RequestException,
            subprocess.SubprocessError,
            IOError,
            OSError,
            TypeError,
            ValueError,
    ):
        logger.error("File distribution download failed validation or execution")
        return "Failed"


def wait_for_task(task_href, base_url, username, password, logger, timeout=3600, interval=3):
    """
    Polls a Pulp task until it reaches a terminal state: completed, failed, or canceled.

    Args:
        task_href (str): Relative URL to the task
        base_url (str): Base URL of the Pulp server
        username (str): Username for basic auth.
        password (str): Password for basic auth.
        logger (logging.Logger): Logger instance.
        timeout (int): Max time to wait in seconds. Default is 3600 (1 hour).
        interval (int): Polling interval in seconds. Default is 3.

    Returns:
        bool: True if task completed successfully, False if failed, canceled, or timeout.
    """
    rest_client = RestClient(base_url, username, password)

    parsed_base = base_url.rstrip('/')
    if task_href.startswith(parsed_base):
        uri = task_href[len(parsed_base):]
    else:
        uri = task_href

    start = time.time()

    while (time.time() - start) < timeout:
        task = rest_client.get(uri)
        if task is None:
            logger.error(f"Failed to get task info from {uri}")
            return False

        state = task.get("state", "unknown")
        if state == "completed":
            return True
        if state in ("failed", "canceled"):
            return False

        time.sleep(interval)

    logger.error("Timeout waiting for task to complete")
    return False


def handle_file_upload(repository_name, relative_path, file_url, timeout_minutes, logger):
    """
    Ensure repository exists, then POST a file to Pulp and wait for the task to complete.

    Args:
        repository_name (str): Name of the repository.
        relative_path (str): Relative path for the file in the repository.
        file_url (str): URL of the file to upload.
        timeout_minutes (int): Maximum time in minutes to wait for task completion.
        logger (logging.Logger): Logger instance.

    Returns:
        str: "Success" if operation completes successfully, "Failed" otherwise.
    """
    repository_name = validate_repository_id(repository_name)
    file_url = validate_artifact_url(file_url)
    repo_lock = get_repository_lock(repository_name)
    with repo_lock:
        ensured, repo_info = _ensure_pulp_object(
            pulp_file_commands["show_repository"] % repository_name,
            pulp_file_commands["create_repository"] % repository_name,
            f"File repository {repository_name}",
            logger,
        )
    if not ensured or not isinstance(repo_info, dict):
        return "Failed"
    pulp_href = repo_info.get("pulp_href")
    if not pulp_href:
        logger.error("File repository response has no Pulp href")
        return "Failed"

    # Load config for authentication and base_url
    config = load_pulp_config(CLI_FILE_PATH)
    base_url = config["base_url"]
    passcode = base64.b64decode(config["password"].encode()).decode()

    # Initialize RestClient
    logger.info("Initializing RestClient for POST request...")
    client = RestClient(base_url, config["username"], passcode)

    data = {
        "file_url": file_url,
        "relative_path": relative_path,
        "repository": pulp_href
    }
    logger.info(f"Sending POST request to upload file from '{file_url}' to repository '{repository_name}'...")
    response = client.post(FILE_URI, data)

    if not response:
        logger.error(f"Failed to POST file to repository {repository_name}.")
        return "Failed"

    task_href = response.get("task")
    if not task_href:
        logger.error("Task href not found in POST response.")
        return "Failed"

    # Wait for task completion
    timeout_seconds = timeout_minutes * 60
    logger.info(f"Waiting for task {task_href} to complete (timeout: {timeout_minutes} min)...")
    task_result = wait_for_task(task_href, base_url, config["username"], passcode,
                                logger, timeout=timeout_seconds, interval=TASK_POLL_INTERVAL)
    if task_result:
        logger.info(f"File successfully uploaded to repository '{repository_name}'.")
        return "Success"
    logger.error(f"Task {task_href} failed or timed out. File upload to repository '{repository_name}' failed.")
    return "Failed"


def handle_post_request(repository_name, relative_path, base_path, file_url, timeout_minutes, logger):
    """
    Handles the full Pulp upload and distribution process for a given repository and file.
    Args:
        repository_name (str): Name of the Pulp repository.
        relative_path (str): Path where the file should be stored inside the repository.
        base_path (str): The base path for the distribution.
        file_url (str): URL of the file to be uploaded.
        timeout_minutes (int): Maximum time in minutes to wait for upload task completion.
        logger (logging.Logger): Logger for logging messages and errors.

    Returns:
        str: "Success" if the operation completes successfully, "Failed" otherwise.
    """
    repository_name = validate_repository_id(repository_name)

    result = handle_file_upload(repository_name, relative_path, file_url, timeout_minutes, logger)
    if result == "Success":
        distribution_name = repository_name
        logger.info("Creating publication...")
        if not execute_command(
                pulp_file_commands["publication_create"] % repository_name,
                logger):
            logger.error(f"Failed to create publication for repository: {repository_name}")
            return "Failed"

        # Get lock for this specific distribution
        dist_lock = get_distribution_lock(distribution_name)

        with dist_lock:
            logger.info("Checking distribution...")
            if not _reconcile_pulp_distribution(
                    pulp_file_commands["show_distribution"] % distribution_name,
                    pulp_file_commands["distribution_create"] % (
                        distribution_name, base_path, repository_name,
                    ),
                    pulp_file_commands["distribution_update"] % (
                        distribution_name, base_path, repository_name,
                    ),
                    f"File distribution {distribution_name}",
                    logger,
                    pulp_file_commands["show_repository"] % repository_name,
            ):
                result = "Failed"
    return result


def process_file(repository_name, _output_file, relative_path,
                 base_path, distribution_name, url, file_path, logger):
    """
    Process a file using Pulp, ensuring it is downloaded and stored in the specified file_path.

    Args:
        repository_name (str): Name of the Pulp repository.
        _output_file (str): Name of the output file (unused).
        relative_path (str): Relative path for the file in Pulp.
        base_path (str): Base path for the distribution.
        distribution_name (str): Name of the distribution.
        url (str): URL of the file to be downloaded.
        file_path (str): Path where the file should be stored.
        logger (logging.Logger): Logger instance for logging.

    Returns:
        str: "Success" if the process is successful, otherwise "Failed".
    """
    logger.info("#" * 30 + " %s start " + "#" * 30, process_file.__name__)  # Start of function
    status = "Success"
    try:
        repository_name = validate_repository_id(repository_name)
        distribution_name = validate_repository_id(distribution_name)
        url = validate_artifact_url(url)
        logger.info(f"Processing file: {url}")
        # Step 1: Check if the file exists in the file path; download if not
        logger.info("Step 1: Checking if the file exists in the manifest path...")
        if os.path.exists(file_path):
            logger.info(f"File already exists: {file_path}. Skipping download.")
        else:
            logger.info("File does not exist. Downloading file...")
            download_command = ["wget", "-c", "-O", file_path, url]
            if not execute_command(download_command, logger):
                logger.error(f"Failed to download the file: {url}")
                return "Failed"
            logger.info(f"File downloaded to: {file_path}")
        # Step 2: Check if the repository exists; create if not
        logger.info("Step 2: Checking repository...")

        # Get lock for this specific repository
        repo_lock = get_repository_lock(repository_name)

        with repo_lock:
            ensured, _details = _ensure_pulp_object(
                pulp_file_commands["show_repository"] % repository_name,
                pulp_file_commands["create_repository"] % repository_name,
                f"File repository {repository_name}",
                logger,
            )
            if not ensured:
                return "Failed"
        # Step 3: Upload the content to the repository
        logger.info("Step 3: Uploading content...")
        if not _reconcile_file_content(
                repository_name, file_path, relative_path, logger):
            logger.error(
                "Failed to reconcile content in repository: %s",
                repository_name,
            )
            return "Failed"
        # Step 4: Create a publication
        logger.info("Step 4: Creating publication...")
        if not execute_command(
                pulp_file_commands["publication_create"] % repository_name,
                logger):
            logger.error(f"Failed to create publication for repository: {repository_name}")
            return "Failed"
        # Step 5: Check if the distribution exists
        logger.info("Step 5: Checking distribution...")

        # Get lock for this specific distribution
        dist_lock = get_distribution_lock(distribution_name)

        with dist_lock:
            if not _reconcile_pulp_distribution(
                    pulp_file_commands["show_distribution"] % distribution_name,
                    pulp_file_commands["distribution_create"] % (
                        distribution_name, base_path, repository_name,
                    ),
                    pulp_file_commands["distribution_update"] % (
                        distribution_name, base_path, repository_name,
                    ),
                    f"File distribution {distribution_name}",
                    logger,
                    pulp_file_commands["show_repository"] % repository_name,
            ):
                return "Failed"
        logger.info(f"Processing for file {url} completed successfully!")
        return status
    except (subprocess.CalledProcessError, requests.exceptions.RequestException, IOError, OSError):
        logger.error("Error processing file")
        return "Failed"
    finally:
        logger.info("#" * 30 + " %s end " + "#" * 30, process_file.__name__)  # End of function


def process_file_without_download(repository_name, _output_file, relative_path,
                                  base_path, distribution_name, _url, file_path, logger):
    """
    Process a file using Pulp, ensuring it is stored in the specified file_path.
    Args:
        repository_name (str): Name of the Pulp repository.
        _output_file (str): Name of the output file (unused).
        relative_path (str): Relative path for the file in Pulp.
        base_path (str): Base path for the distribution.
        distribution_name (str): Name of the distribution.
        _url (str): URL of the file to be downloaded (unused).
        file_path (str): Path where the file should be stored.
        logger (logging.Logger): Logger instance for logging.
    Returns:
        str: "Success" if the process is successful, otherwise "Failed".
    """
    logger.info("#" * 30 + " %s start " + "#" * 30, process_file_without_download.__name__)
    status = "Success"
    try:
        repository_name = validate_repository_id(repository_name)
        distribution_name = validate_repository_id(distribution_name)
        logger.info(f"Processing file: {_url}")

        # Get lock for this specific repository
        repo_lock = get_repository_lock(repository_name)

        with repo_lock:
            # Step 1: Check if the repository exists; create if not
            logger.info("Step 1: Checking repository...")
            ensured, _details = _ensure_pulp_object(
                pulp_file_commands["show_repository"] % repository_name,
                pulp_file_commands["create_repository"] % repository_name,
                f"File repository {repository_name}",
                logger,
            )
            if not ensured:
                return "Failed"

        # Step 2: Upload the content to the repository
        logger.info("Step 2: Uploading content...")
        if not _reconcile_file_content(
                repository_name, file_path, relative_path, logger):
            logger.error(
                "Failed to reconcile content in repository: %s",
                repository_name,
            )
            return "Failed"

        # Step 3: Create a publication
        logger.info("Step 3: Creating publication...")
        if not execute_command(
                pulp_file_commands["publication_create"] % repository_name,
                logger):
            logger.error(f"Failed to create publication for repository: {repository_name}")
            return "Failed"

        # Get lock for this specific distribution
        dist_lock = get_distribution_lock(distribution_name)

        with dist_lock:
            # Step 4: Check if the distribution exists
            logger.info("Step 4: Checking distribution...")
            if not _reconcile_pulp_distribution(
                    pulp_file_commands["show_distribution"] % distribution_name,
                    pulp_file_commands["distribution_create"] % (
                        distribution_name, base_path, repository_name,
                    ),
                    pulp_file_commands["distribution_update"] % (
                        distribution_name, base_path, repository_name,
                    ),
                    f"File distribution {distribution_name}",
                    logger,
                    pulp_file_commands["show_repository"] % repository_name,
            ):
                return "Failed"
        logger.info(f"Processing for file {_url} completed successfully!")
        return status

    except (subprocess.CalledProcessError, requests.exceptions.RequestException, IOError, OSError):
        logger.error("Error processing file")
        return "Failed"
    finally:
        logger.info("#" * 30 + " %s end " + "#" * 30, process_file_without_download.__name__)


def process_manifest(file, status_file_path, content_base_dir, repo_name, logger):
    """
    Process a manifest file.
    Args:
        file (dict): The file to process.
        status_file_path (str): The path to the status file.
        content_base_dir (str): Pre-built base directory for offline content.
        repo_name (str): Pre-built Pulp repository name.
        logger (logging.Logger): The logger.
    Returns:
        str: The status of the processing.
    Raises:
        Exception: If an error occurs.
    """
    logger.info("#" * 30 + " %s start " + "#" * 30, process_manifest.__name__)  # Start of function
    package_type = None  # Initialize to avoid E0601 error
    package_name = "unknown"
    status = "Failed"
    try:
        package_name = validate_artifact_identifier(file["package"])
        url = validate_artifact_url(file.get('url', None))
        repository_name = validate_repository_id(repo_name)
        package_type = file["type"]

        manifest_directory = os.path.join(content_base_dir, "manifest", package_name)
        output_file = package_name + ".yml"
        relative_path = output_file
        base_path = get_pulp_base_path(manifest_directory)
        manifest_path = os.path.join(manifest_directory, output_file)
        source_validator = probe_http_validator(url, logger)
        cache = _shared_artifact_cache(content_base_dir, logger)
        source_key = build_source_key(
            "manifest", url, compatibility="any"
        ) if source_validator else None
        restored = cache.restore(
            source_key,
            manifest_directory,
            repository_name,
            source_validator,
        ) if cache and source_key else []

        if restored:
            logger.info("Reusing verified manifest source bytes")
            status = process_file_without_download(
                repository_name, output_file, relative_path, base_path,
                repository_name, url, restored[0], logger,
            )
        else:
            subprocess.run(
                ['wget', '-q', '--spider', '--tries=1', url], check=True
            )
            status = handle_post_request(
                repository_name, relative_path, base_path, url,
                FILE_TIMEOUT_MIN, logger,
            )
            if status == "Success":
                os.makedirs(manifest_directory, exist_ok=True)
                status = download_file_distribution(
                    repository_name, manifest_directory, relative_path, logger
                )
                if status == "Success" and cache and source_key:
                    final_validator = probe_http_validator(url, logger)
                    if final_validator == source_validator:
                        cache.record(
                            source_key,
                            "manifest",
                            [manifest_path],
                            repository_name,
                            source_validator,
                        )
                    else:
                        logger.info(
                            "Manifest source changed during transfer; "
                            "cross-context reuse was not recorded"
                        )
    except (subprocess.CalledProcessError, requests.exceptions.RequestException,
            IOError, OSError, ValueError):
        logger.error("Error processing manifest")
        status = "Failed"
    finally:
        if package_type is not None:
            write_status_to_file(status_file_path, package_name, package_type,
                                 status, logger, file_lock)
        logger.info("#" * 30 + " %s end " + "#" * 30, process_manifest.__name__)  # End of function
    return status


def process_git(file, status_file_path, content_base_dir, repo_name, logger):
    """
    Process a Git package.
    Args:
        file (dict): A dictionary containing the package information.
        status_file_path (str): The path to the status file.
        content_base_dir (str): Pre-built base directory for offline content.
        repo_name (str): Pre-built Pulp repository name.
        logger (logging.Logger): The logger instance.
    Returns:
        str: The status of the Git package processing.
    Raises:
        subprocess.CalledProcessError: If an error occurs while executing Git commands.
        Exception: If an error occurs while processing the Git package.
    """
    logger.info("#" * 30 + " %s start " + "#" * 30, process_git.__name__)  # Start of function
    package_type = None  # Initialize to avoid E0601 error
    package_name = "unknown"
    status = "Failed"
    try:
        package_name = validate_artifact_identifier(file['package'])

        url = validate_artifact_url(file.get('url', None))
        version = file.get('version', None)
        repository_name = validate_repository_id(repo_name)
        package_type = file['type']
        logger.info(f"Processing Git Package: {package_name}, URL: {url}, Version: {version}")

        git_modules_directory = os.path.join(content_base_dir, 'git', package_name)
        os.makedirs(git_modules_directory, exist_ok=True)
        tarball_path = os.path.join(git_modules_directory, f'{package_name}.tar.gz')
        output_file = package_name + ".tar.gz"
        relative_path = output_file
        base_path = get_pulp_base_path(git_modules_directory)
        distribution_name = repository_name

        logger.info("Step 1: Resolving immutable Git source identity...")
        object_id = resolve_git_ref(url, version)
        source_key = build_source_key(
            "git", url, version=object_id, compatibility="any"
        )
        cache = _shared_artifact_cache(content_base_dir, logger)
        restored = cache.restore(
            source_key, git_modules_directory, repository_name
        ) if cache else []
        if restored:
            tarball_path = restored[0]
            logger.info("Reusing verified Git archive for object %s", object_id)
        else:
            logger.info("Creating Git archive for object %s", object_id)
            create_git_tarball(
                url, version, object_id, package_name, tarball_path
            )
            if cache:
                cache.record(
                    source_key, "git", [tarball_path], repository_name
                )

        logger.info("Step 2: Processing git tarball with Pulp...")
        status = process_file_without_download(repository_name, output_file, relative_path,
                                               base_path, distribution_name, url, tarball_path, logger)

    except subprocess.SubprocessError:
        logger.error("Error executing Git commands")
        status = "Failed"
    except (requests.exceptions.RequestException, IOError, OSError, KeyError,
            ValueError):
        logger.error("Error processing Git package")
        status = "Failed"

    finally:
        # Write the status to the file
        if package_type is not None:
            write_status_to_file(status_file_path, package_name, package_type,
                                 status, logger, file_lock)

        logger.info("#" * 30 + " %s end " + "#" * 30, process_git.__name__)  # End of function
    return status

# Function to process a shell file


def process_shell(file, status_file_path, content_base_dir, repo_name, logger):
    """Process and safely reuse one verified shell artifact."""
    logger.info("#" * 30 + " %s start " + "#" * 30, process_shell.__name__)
    package_name = "unknown"
    package_type = None
    status = "Failed"
    try:
        package_name = validate_artifact_identifier(file['package'])
        url = validate_artifact_url(file.get('url', None))
        package_type = file['type']
        repository_name = validate_repository_id(repo_name)
        logger.info("Processing shell package: %s", package_name)

        sh_directory = os.path.join(content_base_dir, 'shell', package_name)
        os.makedirs(sh_directory, exist_ok=True)
        sh_path = os.path.join(sh_directory, f"{package_name}.sh")
        output_file = package_name + ".sh"
        relative_path = output_file
        base_path = get_pulp_base_path(sh_directory)
        source_validator = probe_http_validator(url, logger)
        cache = _shared_artifact_cache(content_base_dir, logger)
        source_key = build_source_key(
            "shell", url, compatibility="any"
        ) if source_validator else None
        restored = cache.restore(
            source_key, sh_directory, repository_name, source_validator
        ) if cache and source_key else []

        if restored:
            logger.info("Reusing verified shell source bytes")
            status = process_file_without_download(
                repository_name, output_file, relative_path, base_path,
                repository_name, url, restored[0], logger,
            )
        else:
            had_existing_file = os.path.isfile(sh_path)
            status = process_file(
                repository_name, output_file, relative_path, base_path,
                repository_name, url, sh_path, logger,
            )
            if (
                    status == "Success" and not had_existing_file
                    and cache and source_key):
                final_validator = probe_http_validator(url, logger)
                if final_validator == source_validator:
                    cache.record(
                        source_key, "shell", [sh_path], repository_name,
                        source_validator,
                    )
                else:
                    logger.info(
                        "Shell source changed during transfer; "
                        "cross-context reuse was not recorded"
                    )
    except (subprocess.CalledProcessError, requests.exceptions.RequestException,
            IOError, OSError, KeyError, TypeError, ValueError):
        logger.error("Error processing shell")
        status = "Failed"
    finally:
        if package_type is not None:
            write_status_to_file(
                status_file_path, package_name, package_type, status,
                logger, file_lock,
            )
        logger.info("#" * 30 + " %s end " + "#" * 30, process_shell.__name__)
    return status


def process_ansible_galaxy_collection(
        file, status_file_path, content_base_dir, repo_name, logger):
    """Process one pinned Galaxy collection with verified byte reuse."""
    logger.info(
        "#" * 30 + " %s start " + "#" * 30,
        process_ansible_galaxy_collection.__name__,
    )
    package_name = "unknown"
    package_type = None
    status = "Failed"
    try:
        package_name = validate_artifact_identifier(file['package'])
        version = validate_python_package_version(file.get('version', None))
        repository_name = validate_repository_id(repo_name)
        package_type = file['type']
        logger.info(
            "Processing Ansible Galaxy collection: %s:%s",
            package_name,
            version,
        )

        galaxy_directory = os.path.join(
            content_base_dir, 'ansible_galaxy_collection', package_name
        )
        os.makedirs(galaxy_directory, exist_ok=True)
        output_file = f"{package_name.replace('.', '-')}-{version}.tar.gz"
        collection_path = os.path.join(galaxy_directory, output_file)
        base_path = get_pulp_base_path(galaxy_directory)
        cache = _shared_artifact_cache(content_base_dir, logger)
        source_key = build_source_key(
            "ansible_galaxy_collection",
            package_name,
            version=version,
            compatibility="any",
        )
        restored = cache.restore(
            source_key, galaxy_directory, repository_name
        ) if cache else []
        downloaded_now = False

        if restored:
            collection_path = restored[0]
            logger.info("Reusing verified Galaxy collection archive")
        elif not os.path.isfile(collection_path):
            subprocess.run([
                'ansible-galaxy', 'collection', 'download',
                f'{package_name}:{version}',
                f'--download-path={galaxy_directory}',
            ], check=True)
            downloaded_now = True

        if not os.path.isfile(collection_path) or os.path.islink(collection_path):
            raise OSError("Galaxy collection archive was not created")
        if downloaded_now and cache:
            cache.record(
                source_key,
                "ansible_galaxy_collection",
                [collection_path],
                repository_name,
            )

        status = process_file_without_download(
            repository_name, output_file, output_file, base_path,
            repository_name, package_name, collection_path, logger,
        )
    except (requests.exceptions.RequestException, IOError, OSError, KeyError,
            TypeError, ValueError, subprocess.CalledProcessError):
        logger.error("Error processing Ansible Galaxy collection")
        status = "Failed"
    finally:
        if package_type is not None:
            write_status_to_file(
                status_file_path, package_name, package_type, status,
                logger, file_lock,
            )
        logger.info(
            "#" * 30 + " %s end " + "#" * 30,
            process_ansible_galaxy_collection.__name__,
        )
    return status


def process_tarball(package, status_file_path, version_variables, content_base_dir, repo_name, logger):
    """
    Process a tarball package.

    Args:
        package (dict): The package information.
        status_file_path (str): The path to the status file.
        version_variables (dict): The version variables.
        content_base_dir (str): Pre-built base directory for offline content.
        repo_name (str): Pre-built Pulp repository name.
        logger (logging.Logger): The logger.

    Returns:
        str: The status of the operation.
    """
    logger.info("#" * 30 + " %s start " + "#" * 30, process_tarball.__name__)  # Start of function

    package_name = "unknown"
    package_type = package.get('type')
    status = "Failed"
    try:
        package_name = validate_artifact_identifier(
            render_catalog_placeholders(
                package.get('package'), version_variables,
                "tarball package name",
            )
        )
        repository_name = validate_repository_id(repo_name)
        url = None
        if package.get('url') is not None:
            url = validate_artifact_url(render_catalog_placeholders(
                package.get('url'), version_variables, "tarball URL"
            ))
        path = package.get('path')

        logger.info(
            "Processing Tarball Package: %s, URL: %s, Path: %s",
            package_name, url, path,
        )
        tarball_directory = os.path.join(
            content_base_dir, 'tarball', package_name
        )
        tarball_path = os.path.join(
            tarball_directory, f"{package_name}.tar.gz"
        )
        output_file = package_name + ".tar.gz"
        relative_path = output_file
        base_path = get_pulp_base_path(tarball_directory)
        cache = _shared_artifact_cache(content_base_dir, logger)
        compatibility = _content_architecture(content_base_dir)

        if path and os.path.isfile(path) and not os.path.islink(path):
            source_digest = file_sha256(path)
            source_key = build_source_key(
                "tarball", os.path.realpath(path), version=source_digest,
                compatibility=compatibility,
            ) if compatibility else None
            restored = cache.restore(
                source_key, tarball_directory, repository_name
            ) if cache and source_key else []
            if restored:
                tarball_path = restored[0]
                logger.info("Reusing verified local tarball bytes")
            else:
                os.makedirs(tarball_directory, exist_ok=True)
                if os.path.realpath(path) != os.path.realpath(tarball_path):
                    shutil.copy2(path, tarball_path)
                if cache and source_key:
                    cache.record(
                        source_key, "tarball", [tarball_path], repository_name
                    )
            status = process_file_without_download(
                repository_name, output_file, relative_path, base_path,
                repository_name, package_name, tarball_path, logger,
            )
        elif url:
            source_validator = probe_http_validator(url, logger)
            source_key = build_source_key(
                "tarball", url, compatibility=compatibility
            ) if source_validator and compatibility else None
            restored = cache.restore(
                source_key,
                tarball_directory,
                repository_name,
                source_validator,
            ) if cache and source_key else []
            if restored:
                logger.info("Reusing verified remote tarball bytes")
                status = process_file_without_download(
                    repository_name, output_file, relative_path, base_path,
                    repository_name, url, restored[0], logger,
                )
            else:
                agent = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/132.0.0.0 Safari/537.36"
                )
                subprocess.run([
                    'wget', '-q', '--spider', '--tries=1',
                    '--user-agent', agent, url,
                ], check=True)
                status = handle_post_request(
                    repository_name, relative_path, base_path, url,
                    TAR_TIMEOUT_MIN, logger,
                )
                if status == "Success":
                    os.makedirs(tarball_directory, exist_ok=True)
                    status = download_file_distribution(
                        repository_name, tarball_directory,
                        relative_path, logger,
                    )
                    if status == "Success" and cache and source_key:
                        final_validator = probe_http_validator(url, logger)
                        if final_validator == source_validator:
                            cache.record(
                                source_key,
                                "tarball",
                                [tarball_path],
                                repository_name,
                                source_validator,
                            )
                        else:
                            logger.info(
                                "Tarball source changed during transfer; "
                                "cross-context reuse was not recorded"
                            )
        else:
            logger.error("Tarball requires a valid URL or regular local file")
    except (subprocess.CalledProcessError, requests.RequestException,
            IOError, OSError, KeyError, TypeError, ValueError,
            SharedArtifactStateError):
        logger.error("Error processing tarball")
        status = "Failed"
    finally:
        if package_type is not None:
            write_status_to_file(
                status_file_path, package_name, package_type,
                status, logger, file_lock,
            )
        logger.info(
            "#" * 30 + " %s end " + "#" * 30,
            process_tarball.__name__,
        )
    return status


def process_iso(package, status_file_path,
                version_variables, content_base_dir, repo_name, logger):
    """Process an ISO and reuse bytes only within the same architecture."""
    logger.info("#" * 30 + " %s start " + "#" * 30, process_iso.__name__)
    package_name = "unknown"
    package_type = None
    status = "Failed"
    try:
        package_name = validate_artifact_identifier(package['package'])
        package_type = package['type']
        repository_name = validate_repository_id(repo_name)
        configured_path = package.get('path')
        url = None
        if package.get('url') is not None:
            url = validate_artifact_url(render_catalog_placeholders(
                package.get('url'), version_variables, "ISO URL"
            ))

        iso_directory = os.path.join(content_base_dir, 'iso', package_name)
        os.makedirs(iso_directory, exist_ok=True)
        base_path = get_pulp_base_path(iso_directory)
        compatibility = _content_architecture(content_base_dir)
        cache = _shared_artifact_cache(content_base_dir, logger)

        if (
                configured_path and os.path.isfile(configured_path)
                and not os.path.islink(configured_path)):
            output_file = validate_artifact_identifier(
                os.path.basename(configured_path)
            )
            iso_file_path = os.path.join(iso_directory, output_file)
            source_digest = file_sha256(configured_path)
            source_key = build_source_key(
                "iso",
                os.path.realpath(configured_path),
                version=source_digest,
                compatibility=compatibility,
            ) if compatibility else None
            restored = cache.restore(
                source_key, iso_directory, repository_name
            ) if cache and source_key else []
            if restored:
                iso_file_path = restored[0]
                logger.info("Reusing verified local ISO bytes")
            else:
                if os.path.realpath(configured_path) != os.path.realpath(
                        iso_file_path):
                    shutil.copy2(configured_path, iso_file_path)
                if cache and source_key:
                    cache.record(
                        source_key, "iso", [iso_file_path], repository_name
                    )
            status = process_file_without_download(
                repository_name, output_file, output_file, base_path,
                repository_name, package_name, iso_file_path, logger,
            )
        elif url:
            output_file = validate_artifact_identifier(
                os.path.basename(urlsplit(url).path)
            )
            iso_file_path = os.path.join(iso_directory, output_file)
            source_validator = probe_http_validator(url, logger)
            source_key = build_source_key(
                "iso", url, compatibility=compatibility
            ) if source_validator and compatibility else None
            restored = cache.restore(
                source_key,
                iso_directory,
                repository_name,
                source_validator,
            ) if cache and source_key else []
            if restored:
                logger.info("Reusing verified remote ISO bytes")
                status = process_file_without_download(
                    repository_name, output_file, output_file, base_path,
                    repository_name, url, restored[0], logger,
                )
            else:
                subprocess.run(
                    ['wget', '-q', '--spider', '--tries=1', url], check=True
                )
                status = handle_post_request(
                    repository_name, output_file, base_path, url,
                    ISO_TIMEOUT_MIN, logger,
                )
                if status == "Success":
                    status = download_file_distribution(
                        repository_name, iso_directory, output_file, logger
                    )
                if status == "Success" and cache and source_key:
                    final_validator = probe_http_validator(url, logger)
                    if final_validator == source_validator:
                        cache.record(
                            source_key,
                            "iso",
                            [iso_file_path],
                            repository_name,
                            source_validator,
                        )
                    else:
                        logger.info(
                            "ISO source changed during transfer; "
                            "cross-context reuse was not recorded"
                        )
        else:
            logger.error("ISO requires a valid URL or regular local file")
    except (subprocess.CalledProcessError, requests.exceptions.RequestException,
            IOError, OSError, KeyError, TypeError, ValueError,
            SharedArtifactStateError):
        logger.error("Error processing ISO")
        status = "Failed"
    finally:
        if package_type is not None:
            write_status_to_file(
                status_file_path, package_name, package_type, status,
                logger, file_lock,
            )
        logger.info("#" * 30 + " %s end " + "#" * 30, process_iso.__name__)
    return status


def _get_target_python_version(cluster_os_type, cluster_os_version, logger):
    """Resolve the target Python version from OS type and version.

    Args:
        cluster_os_type (str): e.g. 'rhel'.
        cluster_os_version (str): e.g. '10.0'.
        logger: Logger instance.

    Returns:
        str or None: Python version string (e.g. '3.12') or None.
    """
    os_map = OS_TARGET_PYTHON.get(cluster_os_type, {})
    major = cluster_os_version.split(".")[0] if cluster_os_version else ""
    py_ver = os_map.get(major)
    if py_ver:
        logger.info(f"Target Python resolved: {cluster_os_type} {cluster_os_version} -> Python {py_ver}")
    return py_ver


def _build_pip_platform_args(target_python, arc, logger):
    """Build pip download argv for cross-version/cross-platform downloads.

    Args:
        target_python (str): e.g. '3.12'.
        arc (str): e.g. 'x86_64'.
        logger: Logger instance.

    Returns:
        list: Extra CLI arguments for pip download.
    """
    return build_pip_platform_args(
        target_python, arc, ARCH_PIP_PLATFORMS, logger
    )


def process_pip(package, status_file_path, content_base_dir, repo_name,
                cluster_os_type="", cluster_os_version="", arc="",
                logger=None):
    """
    Process a pip package using Pulp.

    Args:
        package (dict): Package info with 'package' (name) and optional 'version'.
        status_file_path (str): Path to log processing status.
        content_base_dir (str): Pre-built base directory for offline content.
        repo_name (str): Pre-built Pulp repository name.
        cluster_os_type (str): Target OS type (e.g. 'rhel').
        cluster_os_version (str): Target OS version (e.g. '10.0').
        arc (str): Target architecture (e.g. 'x86_64').
        logger (logging.Logger): The logger instance.

    Returns:
        str: "Success" if the process is successful, otherwise "Failed".
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info("#" * 30 + " %s start " + "#" * 30, process_pip.__name__)
    status = "Success"  # Default status, updated if any step fails
    package_type = None  # Initialize to avoid E0601 error
    package_name = "unknown"

    try:
        package_type = package['type']
        requirement_name, version, package_name = parse_python_requirement(
            package['package'], package.get('version')
        )
        pip_repo = validate_python_repository_id(repo_name)
        distribution_name = pip_repo

        logger.info(f"Processing Pip Package: {package_name}, Version: {version}")

        # Define storage path
        pip_package_directory = os.path.join(content_base_dir, 'pip_module', package_name)
        base_package_directory = get_pulp_base_path(pip_package_directory)

        os.makedirs(pip_package_directory, exist_ok=True)  # Ensure directory exists

        # Step 1: Download the package with target-platform-aware flags.
        # The container runs Python 3.13 (Fedora 42) but targets run Python 3.12
        # (RHEL 10.0).  Without --python-version, pip downloads cp313 wheels that
        # cannot be installed on cp312 nodes (e.g. cffi, cryptography).
        logger.info("Step 1: Downloading package...")
        target_python = _get_target_python_version(cluster_os_type, cluster_os_version, logger)
        pkg_spec = (
            f"{requirement_name}=={version}" if version else requirement_name
        )
        if not target_python:
            status = "Failed"
            logger.error(
                "No target Python mapping exists for %s %s",
                cluster_os_type,
                cluster_os_version,
            )
            return status

        cache = _shared_artifact_cache(content_base_dir, logger)
        architecture_key = None
        portable_key = None
        downloaded_artifacts = []
        if version:
            architecture_key = build_source_key(
                "pip_module",
                pkg_spec,
                version=target_python,
                compatibility=arc,
            )
            portable_key = build_source_key(
                "pip_module",
                pkg_spec,
                version=target_python,
                compatibility="any",
            )
            if cache:
                downloaded_artifacts = cache.restore(
                    portable_key, pip_package_directory, pip_repo
                )
                if not downloaded_artifacts:
                    downloaded_artifacts = cache.restore(
                        architecture_key, pip_package_directory, pip_repo
                    )
                if downloaded_artifacts:
                    logger.info(
                        "Reusing verified Python distributions for %s",
                        pkg_spec,
                    )

        if not downloaded_artifacts:
            downloaded_artifacts = download_python_artifacts(
                pkg_spec,
                pip_package_directory,
                target_python,
                arc,
                ARCH_PIP_PLATFORMS,
                execute_command,
                logger,
            )
        if not downloaded_artifacts:
            status = "Failed"
            logger.error("No target-compatible Python artifact was downloaded")
            return status
        if cache and architecture_key:
            cache.record(
                architecture_key,
                "pip_module",
                downloaded_artifacts,
                pip_repo,
            )
            if artifacts_are_platform_independent(downloaded_artifacts):
                cache.record(
                    portable_key,
                    "pip_module",
                    downloaded_artifacts,
                    pip_repo,
                )

        # Step 2: Create the Pulp repository if it does not exist
        logger.info("Step 2: Checking repository existence...")
        repo_lock = get_repository_lock(pip_repo)
        with repo_lock:
            ensured, _details = _ensure_pulp_object(
                pulp_python_commands["show_repository"] % pip_repo,
                pulp_python_commands["create_repository"] % pip_repo,
                f"Python repository {pip_repo}",
                logger,
            )
        if not ensured:
            status = "Failed"
            return status

        # Step 3: Upload the package(s) to Pulp
        logger.info("Step 3: Uploading package to Pulp...")
        for artifact_path in downloaded_artifacts:
            if not _reconcile_python_content(
                    pip_repo, artifact_path, logger):
                status = "Failed"
                logger.error(
                    "Failed to upload Python distribution to %s",
                    pip_repo,
                )
                return status

        # Step 4: Publish the repository
        logger.info("Step 4: Publishing the repository...")
        if not execute_command(
                pulp_python_commands["publication_create"] % pip_repo,
                logger):
            status = "Failed"
            logger.error(f"Failed to publish repository {pip_repo}. Aborting process.")
            return status  # Stop further steps

        # Step 5: Create or update the distribution
        logger.info("Step 5: Configuring distribution...")
        dist_lock = get_distribution_lock(distribution_name)
        with dist_lock:
            if not _reconcile_pulp_distribution(
                    pulp_python_commands["show_distribution"] % distribution_name,
                    pulp_python_commands["distribution_create"] % (
                        distribution_name, pip_repo, base_package_directory,
                    ),
                    pulp_python_commands["distribution_update"] % (
                        distribution_name, pip_repo, base_package_directory,
                    ),
                    f"Python distribution {distribution_name}",
                    logger,
                    pulp_python_commands["show_repository"] % pip_repo,
            ):
                status = "Failed"
                return status

        logger.info(f"Package {package_name} processed successfully!")

    except (subprocess.CalledProcessError, requests.exceptions.RequestException,
            IOError, OSError, KeyError, ValueError) as error:
        logger.error(
            "Unexpected %s while processing %s.",
            type(error).__name__, package_name
        )
        status = "Failed"

    finally:
        # Write status to file
        if package_type is not None:
            write_status_to_file(status_file_path, package_name, package_type, status, logger, file_lock)

        logger.info("#" * 30 + " %s end " + "#" * 30, process_pip.__name__)
    return status


def process_rpm_file(
        package, status_file_path, content_base_dir, repo_name_arg, logger):
    """Compatibility facade for repository-bound direct RPM processing."""
    # Imported lazily because the focused processor reuses Pulp lifecycle
    # primitives defined in this module.
    from ansible.module_utils.repo_manager.rpm_file_artifact_processor import (  # pylint: disable=import-outside-toplevel
        process_rpm_file as process_rpm_file_impl,
    )
    return process_rpm_file_impl(
        package, status_file_path, content_base_dir, repo_name_arg, logger
    )
