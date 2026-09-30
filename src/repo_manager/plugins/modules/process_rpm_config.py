#!/usr/bin/python
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

"""
Ansible module for processing RPM repository configuration and Pulp operations.

This module handles:
- RPM repository creation, synchronization, and management
- Pulp remote and distribution management
- Publication creation and cleanup
- Repository validation and status checking
- YUM repository file generation
"""


# pylint: disable=import-error,no-name-in-module,too-many-lines,too-many-branches,too-many-statements,too-many-locals,too-many-return-statements,too-many-arguments,too-many-positional-arguments
import configparser
import json
import multiprocessing
import os
import platform
import re
import shlex
import subprocess
import tempfile
from datetime import datetime
from functools import partial
import time
import uuid
from urllib.parse import urlsplit

import requests

try:
    from defusedxml import ElementTree
    from defusedxml.common import DefusedXmlException
    _XML_PARSE_EXCEPTIONS = (ElementTree.ParseError, DefusedXmlException)
except ImportError:  # pragma: no cover - production requirements install it
    ElementTree = None
    _XML_PARSE_EXCEPTIONS = ()

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.standard_logger import setup_standard_logger
from ansible.module_utils.repo_manager.config import (
    CLI_FILE_PATH,
    PULP_CLI_EXECUTABLE,
    PULP_REPO_FILE_PATH,
    PULP_SSL_CA_CERT,
    REPO_MANAGER_LOG_DIR,
    AGGREGATED_REPO_SUFFIX,
    AGGREGATED_BASE_PATH_TEMPLATE,
    PULP_DISTRIBUTION_ROOT,
    RPM_SYNC_STUCK_TIMEOUT,
    RPM_PROGRESS_CHECK_INTERVAL,
    RPM_CLEANUP_ON_TIMEOUT,
    RPM_CLI_QUERY_TIMEOUT,
    RPM_CLI_QUERY_RETRIES,
    RPM_CLI_QUERY_RETRY_DELAY,
    RPM_API_UNAVAILABLE_TIMEOUT,
    ARCH_SUFFIXES,
    MIRROR_STATUS_DIR,
    MIRROR_INDEX_FILENAME,
)
from ansible.module_utils.repo_manager.pulp_commands import (
    build_pulp_entity_command,
    build_rpm_remote_command,
    build_rpm_publication_list_command,
    build_rpm_repository_content_list_command,
    build_rpm_repository_content_modify_command,
    build_rpm_repository_version_list_command,
    build_pulp_task_list_command,
    pulp_common_commands,
    pulp_rpm_commands,
    pulp_task_commands,
)
from ansible.module_utils.repo_manager.common_functions import load_pulp_config
from ansible.module_utils.repo_manager.repo_settings import (
    RPM_CONTINUE_ON_FAILURE,
    RPM_THREAD_POOL_SIZE,
    MIN_THREAD_POOL_SIZE,
    MAX_THREAD_POOL_SIZE,
    POLICY_CACHING_MAP,
)
from ansible.module_utils.repo_manager.software_utils import build_repo_name, normalize_repo_name
from ansible.module_utils.repo_manager.pulp_rpm_repository_manager import (
    build_rpm_distribution_identity,
)
from ansible.module_utils.repo_manager.repo_file_utils import (
    atomic_write_repo_file,
    repo_file_error_message,
)
from ansible.module_utils.repo_manager.mirror_status import (
    load_mirror_index,
    mark_package_entries_pending,
    repositories_requiring_retry,
    save_mirror_index,
    update_repository_sync_state,
)
from ansible.module_utils.repo_manager.security_utils import (
    mask_sensitive_data,
    normalize_pulp_distribution_url,
    redact_sensitive_output,
    validate_pulp_policy,
    validate_repository_id,
    validate_repository_url,
)


_TRANSIENT_PULP_ERROR_MARKERS = (
    "500 internal server error",
    "502 bad gateway",
    "503 service unavailable",
    "504 gateway timeout",
    "bad gateway",
    "connection aborted",
    "connection refused",
    "connection reset",
    "failed to establish a new connection",
    "max retries exceeded",
    "read timed out",
    "remote end closed connection",
    "service unavailable",
)
_NOT_FOUND_PULP_ERROR_MARKERS = (
    "could not find",
    "does not exist",
    "no object found",
    "no result found",
    "not found",
)
_PULP_TASK_HREF_PATTERN = re.compile(
    r"(/pulp/api/v\d+/tasks/[a-f0-9-]{36}/)"
)
_ACTIVE_PULP_TASK_STATES = ("waiting", "running", "canceling")
_MAX_REPOMD_BYTES = 1024 * 1024
_PULP_LIST_PAGE_SIZE = 1000

def _log(log, level, repo_name, msg):
    """All repo logs go through here — grep-friendly."""
    text = f"[{repo_name}] - {msg}" if repo_name else msg
    getattr(log, level)(text)


def _effective_worker_count(configured_workers, item_count):
    """Validate a configured RPM limit and cap it to the available work."""
    configured_workers = int(configured_workers)
    if not MIN_THREAD_POOL_SIZE <= configured_workers <= MAX_THREAD_POOL_SIZE:
        raise ValueError(
            f"thread_pool_size must be between {MIN_THREAD_POOL_SIZE} "
            f"and {MAX_THREAD_POOL_SIZE}"
        )
    return min(configured_workers, max(1, item_count))


def _log_summary(log, results, failures, start_time):
    """Simple summary — grep for SUMMARY, FAILED, Overall."""
    elapsed = int(time.time() - start_time)
    m, s = elapsed // 60, elapsed % 60

    # results format: (success, repo_name, success, version_changed)
    ok = [r for r in results if r[0] and r[2]]  # success=True and synced=True
    fail = [r for r in results if not r[0]]  # success=False
    skip = [r for r in results if r[0] and not r[2]]  # success=True but not synced

    log.info("=" * 60)
    log.info("RPM REPO SYNC SUMMARY")
    log.info("=" * 60)
    log.info(f"Total repos:  {len(results)}")
    log.info(f"Successful:   {len(ok)}")
    log.info(f"Failed:       {len(fail)}")
    log.info(f"Skipped:      {len(skip)}")
    log.info(f"Duration:     {m}m {s}s")

    if fail:
        log.info("-" * 44)
        log.info("FAILED REPOS:")
        for _, name, _, _ in fail:
            stage = next((f.split(":")[0] for f in failures if name in f), "unknown")
            log.error(f"  {name} — {stage}")

    if skip:
        log.info("-" * 44)
        log.info("SKIPPED REPOS (already up to date):")
        for _, name, _, _ in skip:
            log.info(f"  {name}")

    log.info("=" * 60)
    if failures:
        log.info("Overall Status: PARTIAL")
    elif not ok and skip:
        log.info("Overall Status: SKIPPED (all up to date)")
    else:
        log.info("Overall Status: SUCCESS")
    log.info("=" * 60)

DOCUMENTATION = r"""
---
module: process_rpm_config
short_description: Process RPM repository configuration
description:
  - Creates, synchronizes, publishes, and distributes RPM repositories in Pulp.
  - Repairs incomplete repository state after an interrupted execution.
options:
  local_config:
    description: Catalog RPM repository definitions.
    required: true
    type: list
    elements: dict
  log_dir:
    description: Directory for repository-processing logs.
    required: false
    type: path
  additional_repos_config:
    description: Aggregated additional repository definitions.
    required: false
    type: dict
  user_repos_config:
    description: User-provided RPM repository definitions by architecture.
    required: false
    type: dict
  thread_pool_size:
    description: Maximum worker count for each RPM processing stage.
    required: false
    type: int
  pulp_concurrency:
    description: Deprecated compatibility alias for I(thread_pool_size).
    required: false
    type: int
  sw_archs:
    description: Catalog-selected architectures to process.
    required: false
    type: list
    elements: str
  resync_repos:
    description: Repository names to resynchronize, or C(all).
    required: false
    type: raw
  exact_mirror:
    description:
      - Enable repository-only exact-mirror reconciliation.
      - Existing Pulp objects are required and are never created by this mode.
      - The default preserves normal Repo Manager download behavior.
    required: false
    default: false
    type: bool
  exact_mirror_preflight:
    description:
      - Validate every exact-mirror target without mutating Pulp or checkpoints.
      - Valid only when I(exact_mirror=true).
    required: false
    default: false
    type: bool
  run_orphan_cleanup:
    description:
      - Run Pulp orphan cleanup after exact reconciliation succeeds.
      - Set only for the final ordered catalog context.
    required: false
    default: false
    type: bool
  cluster_os_type:
    description: Operating-system family for the active catalog context.
    required: true
    type: str
  cluster_os_version:
    description: Operating-system version for the active catalog context.
    required: true
    type: str
  pulp_base_url:
    description: Trusted public HTTPS origin for Pulp distributions.
    required: true
    type: str
  repo_file_path:
    description: Destination path for the generated DNF repository file.
    required: true
    type: path
author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Process RPM configuration
  process_rpm_config:
    local_config: "{{ rpm_repositories }}"
    log_dir: "{{ repo_manager_log_dir }}"
    thread_pool_size: 1
    sw_archs:
      - x86_64
    cluster_os_type: rhel
    cluster_os_version: "10.0"
    pulp_base_url: "{{ pulp_base_url }}"
    repo_file_path: "{{ pulp_repo_file_path }}"
  register: rpm_result
"""

RETURN = r"""
result:
  description: Repository-processing result summary.
  type: raw
  returned: success
"""




def validate_pulp_href(href):
    """
    Validates that a Pulp href matches the expected format and returns a sanitized copy.
    This is an allowlist validation to prevent argument injection.

    Args:
        href (str): The Pulp href to validate.

    Returns:
        str: A sanitized href reconstructed from validated components.

    Raises:
        ValueError: If the href does not match the expected Pulp API format.
    """
    if href is None:
        return None

    href_str = str(href)
    # Pulp hrefs follow pattern: /pulp/api/v<version>/<resource_type>/<uuid>/
    # Example: /pulp/api/v3/publications/rpm/rpm/01234567-89ab-cdef-0123-456789abcdef/
    # Pattern uses v\d+ to support future API versions (v3, v4, v5, etc.)
    # Capturing groups are used to reconstruct the href, breaking the taint chain
    pulp_href_pattern = re.compile(r'^(/pulp/api/v)(\d+)(/[a-zA-Z0-9/_-]+)([a-f0-9-]{36})(/)$')

    match = pulp_href_pattern.match(href_str)
    if not match:
        raise ValueError(f"Invalid Pulp href format: {href_str}")

    # Reconstruct href from captured groups - this creates a new untainted string
    # Then apply shlex.quote to sanitize for shell safety (recognized sanitizer)
    sanitized_href = "".join(match.groups())
    # Remove quotes added by shlex.quote since we're using argument list (not shell)
    # shlex.quote adds quotes around the string which we need to strip
    quoted = shlex.quote(sanitized_href)
    # shlex.quote returns the string with quotes if it contains special chars,
    # or the original string if safe. Since our regex only allows safe chars,
    # it should return the same string, but this marks it as sanitized for Checkmarx
    return quoted.strip("'")


def validate_repository_version_href(href):
    """Validate and return an RPM repository-version HREF."""
    if href is None:
        return None
    pattern = re.compile(
        r"^(/pulp/api/v)(\d+)(/repositories/rpm/rpm/)"
        r"([a-f0-9-]{36})(/versions/)(\d+)(/)$"
    )
    match = pattern.match(str(href))
    if not match:
        raise ValueError(f"Invalid Pulp repository version href: {href}")
    return "".join(match.groups())


def _command_output(result):
    """Return normalized stdout and stderr from a CLI result."""
    if result is None:
        return ""
    def _to_text(value):
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value or "")

    output = "\n".join(
        _to_text(value).strip()
        for value in (result.stdout or "", result.stderr or "")
        if _to_text(value).strip()
    )
    return redact_sensitive_output(output, getattr(result, "args", []))


def _is_transient_pulp_error(result):
    """Return True for retryable Pulp API or transport failures."""
    output = _command_output(result).lower()
    return any(marker in output for marker in _TRANSIENT_PULP_ERROR_MARKERS)


def _is_not_found_pulp_error(result):
    """Return True only when the CLI explicitly reports a missing object."""
    output = _command_output(result).lower()
    return any(marker in output for marker in _NOT_FOUND_PULP_ERROR_MARKERS)


def _run_pulp_cli(
        command, log, repo_name=None, timeout=RPM_CLI_QUERY_TIMEOUT,
        retries=RPM_CLI_QUERY_RETRIES):
    """Run one Pulp CLI command and retry only temporary read failures.

    Callers pass argument lists, and the configured CLI executable is used
    without involving a Python Pulp API.
    This helper is intended for read-only show/list/task queries. Mutations use
    one dispatch attempt and reconcile an uncertain response by correlation ID.
    """
    command = list(command)
    if command and command[0] == "pulp":
        command[0] = PULP_CLI_EXECUTABLE

    attempts = max(1, int(retries))
    tag = f"[{repo_name}] - " if repo_name else ""
    last_result = None

    for attempt in range(1, attempts + 1):
        try:
            last_result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            last_result = subprocess.CompletedProcess(
                args=command,
                returncode=124,
                stdout=exc.stdout or "",
                stderr=f"Pulp CLI query timed out after {timeout} seconds",
            )
        except subprocess.SubprocessError:
            last_result = subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr="Pulp CLI subprocess failed",
            )

        if last_result.returncode == 0:
            return last_result

        retryable = (
            last_result.returncode == 124
            or _is_transient_pulp_error(last_result)
        )
        if not retryable or attempt == attempts:
            return last_result

        log.warning(
            "%sTemporary Pulp CLI failure (attempt %d/%d): %s",
            tag,
            attempt,
            attempts,
            _command_output(last_result) or "unknown error",
        )
        time.sleep(RPM_CLI_QUERY_RETRY_DELAY)

    return last_result


def _query_object_exists(command, log, repo_name):
    """Return True, False, or None for found, missing, or query failure."""
    result = _run_pulp_cli(command, log, repo_name=repo_name)
    if result is not None and result.returncode == 0:
        return True
    if result is not None and _is_not_found_pulp_error(result):
        return False
    _log(
        log,
        "error",
        repo_name,
        f"Unable to determine Pulp object state: "
        f"{_command_output(result) or 'no CLI response'}",
    )
    return None


def _parse_task_href(output):
    """Extract and validate an exact task HREF from Pulp CLI output."""
    match = _PULP_TASK_HREF_PATTERN.search(output or "")
    return validate_pulp_href(match.group(1)) if match else None


def execute_command(command, log, type_json=None, seconds=None, repo_name=None):
    """
    Executes a shell command and returns its output.

    Args:
        command (str or list): Pulp command represented as text or argv.
        log (logging.Logger): Logger instance for logging the process and errors.
        type_json (bool, optional): If set to `True`, the function will attempt to
            parse the command's output as JSON.
        seconds (float, optional): Maximum command duration. Defaults to the
            configured Pulp CLI query timeout.
        repo_name (str, optional): Repository name for log tagging.

    Returns:
        str or bool: Returns the command's output as a string, or `False` if the command failed.
    """

    try:
        tag = f"[{repo_name}] - " if repo_name else ""
        log.info("%sExecuting command: %s", tag, mask_sensitive_data(command))
        cmd_list = (
            [str(value) for value in command]
            if isinstance(command, (list, tuple))
            else shlex.split(command)
        )
        cmd = _run_pulp_cli(
            cmd_list,
            log,
            repo_name=repo_name,
            timeout=seconds or RPM_CLI_QUERY_TIMEOUT,
            retries=1,
        )
        if cmd is None:
            log.error(f"{tag}Command failed without a CLI response")
            return False
        if cmd.returncode != 0:
            log.error(f"{tag}Command failed (rc={cmd.returncode})")
            if cmd.stderr and cmd.stderr.strip():
                stderr_clean = redact_sensitive_output(
                    cmd.stderr.strip().rstrip('.'), cmd.args
                )
                log.error(f"{tag}STDERR: {stderr_clean}")
            return False
        if type_json:
            return json.loads(cmd.stdout)
        return True
    except subprocess.TimeoutExpired:
        log.error("Pulp command timed out")
        return False
    except subprocess.SubprocessError:
        log.error("Pulp subprocess failed")
        return False
    except Exception:
        log.error("Unexpected failure while executing Pulp command")
        return False


def check_repository_synced(repo_name, log):
    """
    Check if repository has synced content using Pulp CLI.

    Parameters:
        repo_name (str): The name of the repository.
        log (logging.Logger): The logger object.

    Returns:
        bool or None: True when synchronized, False when empty, or None when
            repository state could not be queried.
    """
    try:
        result = _run_pulp_cli(
            pulp_rpm_commands["show_repository"] % repo_name,
            log,
            repo_name=repo_name,
        )
        if result is None or result.returncode != 0:
            if result is not None and _is_not_found_pulp_error(result):
                log.info(f"Repository {repo_name} does not exist. Proceeding.")
                return False
            log.error(
                "Unable to check repository '%s': %s",
                repo_name,
                _command_output(result) or "no CLI response",
            )
            return None
        repo_info = json.loads(result.stdout)
        latest_version_href = repo_info.get("latest_version_href", "")

        # Check if version > 0 (version 0 is empty initial state)
        if latest_version_href and not latest_version_href.endswith("/versions/0/"):
            log.info(f"{repo_name} already synced. Skipping sync.")
            return True

        log.info(f"{repo_name} not synced yet. Proceeding with sync.")
        return False
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        log.error("Subprocess error checking repository")
        return None
    except Exception:
        log.error("Error checking repository")
        return None


def create_rpm_repository(repo, log):
    """
    Create an RPM repository if it doesn't already exist.

    Args:
        repo (dict): A dictionary containing the package information.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool: True if the repository was created successfully or already exists,
            False if there was an error.
    """
    try:
        repo_name = _configured_repository_name(repo)
        repository_exists = show_rpm_repository(repo_name, log)
        if repository_exists is None:
            return False, repo_name
        if not repository_exists:
            command = pulp_rpm_commands["create_repository"] % repo_name
            log.info("Repository '%s' does not exist. Executing command: %s", repo_name, command)
            result = execute_command(command, log)
            if not result:
                reconciled_state = show_rpm_repository(repo_name, log)
                if reconciled_state is True:
                    log.info(
                        "Repository %s exists after an uncertain create response.",
                        repo_name,
                    )
                    return True, repo_name
                return False, repo_name
            log.info("Repository %s created.", repo_name)
            return result, repo_name

        log.info("Repository %s already exists.", repo_name)
        return True, repo_name

    except subprocess.CalledProcessError:
        log.error(
            "Pulp command failed while creating repository '%s'",
            repo.get('package', 'unknown')
        )
        return False, repo.get("package", "unknown")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        log.error(
            "Subprocess error while creating repository '%s'",
            repo.get('package', 'unknown')
        )
        return False, repo.get("package", "unknown")
    except Exception:
        log.error(
            "Unexpected error while creating repository '%s'",
            repo.get('package', 'unknown')
        )
        return False, repo.get("package", "unknown")


def show_rpm_repository(repo_name, log):
    """
    Show details of an RPM repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool or None: True if found, False if explicitly missing, or None when
            Pulp could not answer the query.
    """

    try:
        repo_name = validate_repository_id(repo_name)
        log.info("Checking existence of RPM repository: '%s'", repo_name)
        command = pulp_rpm_commands["show_repository"] % repo_name
        log.info("Executing command to show repository: %s", command)

        return _query_object_exists(command, log, repo_name)

    except subprocess.CalledProcessError:
        log.error("Pulp command failed while checking repository '%s'", repo_name)
        return None
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        log.error("Subprocess error while checking repository '%s'", repo_name)
        return None
    except Exception:
        log.error("Unexpected error while checking repository '%s'", repo_name)
        return None


def create_rpm_remote(repo, log):
    """
    Create an RPM remote or update its URL, policy, and certificates.

    Args:
        repo (dict): A dictionary containing the repository information.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        tuple: Success, repository name, and whether URL/policy changed.
    """

    try:
        log.info("Starting RPM remote creation process")
        remote_url = validate_repository_url(repo["url"])
        policy_type = validate_pulp_policy(repo["policy"])
        repo_name = _configured_repository_name({
            "package": repo.get("package") or repo.get("name"),
            "version": repo.get("version"),
        })
        result = None

        remote_name = repo_name

        remote_exists, remote_state = _get_rpm_remote_state(
            remote_name, log
        )
        if remote_exists is None:
            return False, repo_name, False
        remote_changed = (
            not remote_exists
            or str(remote_state.get("url") or "").rstrip("/")
            != remote_url.rstrip("/")
            or remote_state.get("policy") != policy_type
        )
        repo_keys = repo.keys()
        if "ca_cert" in repo_keys and repo["ca_cert"]:
            ca_cert = f"@{repo['ca_cert']}"
            client_cert = f"@{repo['client_cert']}"
            client_key = f"@{repo['client_key']}"
            action = "update" if remote_exists else "create"
            command_key = f"{action}_remote_cert"
            command = pulp_rpm_commands[command_key] % (
                remote_name, remote_url, policy_type,
                ca_cert, client_cert, client_key,
            )
            if remote_exists:
                log.info("Remote '%s' exists. Updating URL, policy, and certificates.", remote_name)
            else:
                log.info(
                    "Remote '%s' does not exist. Executing creation command "
                    "with certs.", remote_name,
                )
            result = execute_command(command, log)
            # Reconcile an uncertain create response without repeating it.
            if result is False and not remote_exists and show_rpm_remote(remote_name, log):
                log.info("Remote '%s' exists after the create response.", remote_name)
                return True, repo_name, True
        else:
            log.info("Repository does not use SSL certificates for remote")
            action = "update" if remote_exists else "create"
            command_key = f"{action}_remote"
            command = pulp_rpm_commands[command_key] % (
                remote_name, remote_url, policy_type,
            )
            if remote_exists:
                log.info("Remote '%s' exists. Updating URL and policy.", remote_name)
            else:
                log.info("Remote '%s' does not exist. Executing creation command.", remote_name)
            result = execute_command(command, log)
            # Reconcile an uncertain create response without repeating it.
            if result is False and not remote_exists and show_rpm_remote(remote_name, log):
                log.info("Remote '%s' exists after the create response.", remote_name)
                return True, repo_name, True
        # Both create and update commands return a truthy result on success.
        return bool(result), repo_name, remote_changed if result else False

    except subprocess.CalledProcessError:
        repo_name_for_error = repo.get("package") or repo.get("name", "unknown")
        log.error("Pulp command failed while creating remote '%s'", repo_name_for_error)
        return False, repo_name_for_error, False
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        repo_name_for_error = repo.get("package") or repo.get("name", "unknown")
        log.error("Subprocess error while creating remote '%s'", repo_name_for_error)
        return False, repo_name_for_error, False
    except Exception:
        repo_name_for_error = repo.get("package") or repo.get("name", "unknown")
        log.error("Unexpected error while creating remote '%s'", repo_name_for_error)
        return False, repo_name_for_error, False
    finally:
        repo_name_for_error = repo.get("package") or repo.get("name", "unknown")
        log.info("Completed RPM remote creation process for '%s'", repo_name_for_error)


def _get_rpm_remote_state(remote_name, log):
    """Return existence and non-secret URL/policy state for an RPM remote."""
    try:
        remote_name = validate_repository_id(remote_name)
        result = _run_pulp_cli(
            pulp_rpm_commands["show_remote"] % remote_name,
            log,
            repo_name=remote_name,
        )
        if result is None or result.returncode != 0:
            if result is not None and _is_not_found_pulp_error(result):
                return False, {}
            log.error("Unable to read RPM remote state for '%s'", remote_name)
            return None, None
        remote_data = json.loads(result.stdout)
        if not isinstance(remote_data, dict):
            return None, None
        return True, {
            "url": remote_data.get("url"),
            "policy": remote_data.get("policy"),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        log.error("Invalid RPM remote state for '%s'", remote_name)
        return None, None
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        log.error("Subprocess error while checking remote '%s'", remote_name)
        return None, None


def show_rpm_remote(remote_name, log):
    """
    Show details of an RPM remote.

    Args:
        remote_name (str): The name of the remote.
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        bool or None: True if found, False if explicitly missing, or None when
            Pulp could not answer the query.
    """
    try:
        remote_exists, _ = _get_rpm_remote_state(remote_name, log)
        return remote_exists

    except subprocess.CalledProcessError:
        log.error("Pulp command failed while checking remote '%s'", remote_name)
        return None
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        log.error("Subprocess error while checking remote '%s'", remote_name)
        return None
    except Exception:
        log.error("Unexpected error while checking remote '%s'", remote_name)
        return None
    finally:
        log.info("Completed check for RPM remote '%s'", remote_name)




def _get_repository_href(repo_name, log):
    """
    Return the Pulp href for a repository.
    
    Args:
        repo_name (str): Repository name
        log (logging.Logger): Logger instance
    
    Returns:
        str: Validated repository href or None if not found.
    """
    try:
        result = _run_pulp_cli(
            pulp_rpm_commands["show_repository"] % repo_name,
            log,
            repo_name=repo_name,
        )
        if result is None or result.returncode != 0:
            _log(log, "debug", repo_name, "Failed to get repository href")
            return None
        repo_data = json.loads(result.stdout)
        href = repo_data.get("pulp_href", "")
        return validate_pulp_href(href) if href else None
    except Exception:
        _log(log, "warning", repo_name, "Error getting repository HREF")
        return None


def _reserved_resource_matches_repository(resource, repository_href):
    """Return whether one Pulp reservation names the exact repository."""
    if not isinstance(resource, str) or not isinstance(repository_href, str):
        return False
    normalized_resource = resource
    for prefix in ("shared:", "exclusive:"):
        if normalized_resource.startswith(prefix):
            normalized_resource = normalized_resource[len(prefix):]
            break
    return normalized_resource == repository_href


def _find_pulp_task_by_cid(task_cid, repository_href, log, repo_name):
    """
    Find the task dispatched by one CLI request using its correlation ID.

    Correlation IDs are unique per sync invocation. The repository href is an
    additional discriminator for Pulp versions that create related child
    tasks with the same correlation ID.

    Args:
        task_cid (str): Unique correlation ID supplied to the Pulp CLI.
        repository_href (str): Repository href reserved by the sync task.
        log (logging.Logger): Logger instance
        repo_name (str): Repository name used for logging.

    Returns:
        str: Exact task href, or None until Pulp exposes the task.
    """
    try:
        result = _run_pulp_cli(
            build_pulp_task_list_command(cid=task_cid, limit=20),
            log,
            repo_name=repo_name,
        )
        if result is None or result.returncode != 0:
            _log(
                log, "warning", repo_name,
                f"Unable to find task for CID {task_cid}: "
                f"{_command_output(result) or 'no CLI response'}",
            )
            return None

        payload = json.loads(result.stdout)
        tasks = payload.get("results", []) if isinstance(payload, dict) else payload
        if not isinstance(tasks, list):
            return None

        active_states = {"waiting", "running", "canceling"}
        candidates = [
            task for task in tasks
            if task.get("state") in active_states
        ] or tasks

        if repository_href:
            reservations_exposed = False
            for task in candidates:
                reserved = task.get("reserved_resources_record", [])
                reservations_exposed = reservations_exposed or bool(reserved)
                if not any(
                        _reserved_resource_matches_repository(
                            resource, repository_href
                        )
                        for resource in reserved):
                    continue
                task_href = task.get("pulp_href")
                return validate_pulp_href(task_href) if task_href else None
            if reservations_exposed:
                return None

        # A CID is generated for exactly one CLI operation. If a Pulp version
        # does not expose reserved resources, prefer the task reporting sync
        # progress and otherwise use the sole/first correlated task.
        for task in candidates:
            if not task.get("progress_reports"):
                continue
            task_href = task.get("pulp_href")
            return validate_pulp_href(task_href) if task_href else None

        if candidates:
            task_href = candidates[0].get("pulp_href")
            return validate_pulp_href(task_href) if task_href else None
        return None
    except (json.JSONDecodeError, ValueError):
        _log(log, "warning", repo_name, "Unable to identify sync task")
        return None
    except Exception:
        _log(log, "warning", repo_name, "Error identifying sync task")
        return None


def _list_active_repository_tasks(repository_href, log, repo_name):
    """List unfinished Pulp tasks that reserve one RPM repository.

    Pulp retains a background task after its calling Ansible process exits.
    Querying by the repository resource lets a rerun find an interrupted sync
    or publication without relying on process-local task identifiers.

    Returns:
        list or None: Validated task records, or None when Pulp state cannot be
            queried safely.
    """
    try:
        validated_href = validate_pulp_href(repository_href)
        command = build_pulp_task_list_command(
            reserved_resource=validated_href,
            states=_ACTIVE_PULP_TASK_STATES,
            limit=100,
            ordering="pulp_created",
        )

        result = _run_pulp_cli(
            command,
            log,
            repo_name=repo_name,
        )
        if result is None or result.returncode != 0:
            _log(
                log, "error", repo_name,
                "Unable to check unfinished Pulp tasks: "
                f"{_command_output(result) or 'no CLI response'}",
            )
            return None

        payload = json.loads(result.stdout) if result.stdout.strip() else []
        tasks = payload.get("results", []) if isinstance(payload, dict) else payload
        if not isinstance(tasks, list):
            raise ValueError("task list response is not a list")

        active_tasks = []
        for task in tasks:
            if task.get("state") not in _ACTIVE_PULP_TASK_STATES:
                continue
            task_href = task.get("pulp_href")
            if not task_href:
                raise ValueError("unfinished task has no HREF")
            active_tasks.append({
                "pulp_href": validate_pulp_href(task_href),
                "name": str(task.get("name") or "unknown"),
                "state": task.get("state"),
            })
        return active_tasks
    except (json.JSONDecodeError, ValueError, AttributeError):
        _log(
            log, "error", repo_name,
            "Invalid unfinished-task response",
        )
        return None
    except Exception:
        _log(
            log, "error", repo_name,
            "Error checking unfinished Pulp tasks",
        )
        return None


def _recover_active_repository_tasks(repository_href, log, repo_name):
    """Wait for tasks left by an interrupted Repo Manager invocation.

    A completed recovered sync satisfies the synchronization stage of the
    rerun. Other recovered operations are followed by the normal exact-state
    publication and distribution reconciliation.

    Returns:
        tuple: (query_succeeded, recovered_sync_completed, error_message)
    """
    tasks = _list_active_repository_tasks(repository_href, log, repo_name)
    if tasks is None:
        return False, False, "unfinished Pulp task state is unavailable"

    recovered_sync = False
    for task in tasks:
        task_href = task["pulp_href"]
        task_name = task["name"]
        _log(
            log, "info", repo_name,
            "Recovering unfinished Pulp task from an earlier run: "
            f"{task_name} ({task_href})",
        )
        success, message = _monitor_pulp_task(task_href, log, repo_name)
        if success and task_name.endswith(".synchronize"):
            recovered_sync = True
        elif not success:
            # The rerun reconciles actual Pulp state below. For example, a
            # failed publication is recreated, while an empty repository is
            # synchronized again. Do not treat an earlier run's failure as the
            # result of this rerun before that reconciliation is attempted.
            _log(
                log, "warning", repo_name,
                f"Earlier task ended unsuccessfully; reconciling state: "
                f"{message}",
            )

    return True, recovered_sync, ""


def _get_pulp_task_progress(task_href, log, repo_name):
    """Return progress and state for one exact Pulp task href."""
    if not task_href:
        return -1, None, "query-error", "task href is unavailable"
    try:
        validated_href = validate_pulp_href(task_href)
        result = _run_pulp_cli(
            pulp_task_commands["show"] % validated_href,
            log,
            repo_name=repo_name,
        )
        if result is None or result.returncode != 0:
            return (
                -1, None, "query-error",
                _command_output(result) or "no CLI response",
            )

        task = json.loads(result.stdout)
        state = task.get("state", "unknown")
        error = task.get("error") or {}
        if isinstance(error, dict):
            error_message = (
                error.get("description") or error.get("reason") or ""
            )
        else:
            error_message = str(error)
        matching_reports = [
            report for report in task.get("progress_reports", [])
            if "downloading" in report.get("code", "")
            or "parsing" in report.get("code", "")
        ]
        active_reports = [
            report for report in matching_reports
            if report.get("state") == "running"
        ]
        reports = active_reports or matching_reports
        if reports:
            report = max(reports, key=lambda item: item.get("done") or 0)
            return report.get("done") or 0, report.get("total"), state, error_message
        if state in {"waiting", "running", "canceling"}:
            return 0, None, state, error_message
        return -1, None, state, error_message
    except (json.JSONDecodeError, ValueError):
        _log(log, "warning", repo_name, "Unable to read sync task")
        return -1, None, "query-error", "Invalid Pulp task response"
    except Exception:
        _log(log, "warning", repo_name, "Error reading sync task")
        return -1, None, "query-error", "Unable to read Pulp task"


def _cancel_pulp_task(task_href, log, repo_name):
    """
    Cancel a Pulp task by href.
    
    Args:
        task_href (str): Pulp task href to cancel
        log (logging.Logger): Logger instance
        repo_name (str): Repository name for logging
    
    Returns:
        bool: True if cancellation succeeded, False otherwise
    """
    try:
        validated_href = validate_pulp_href(task_href)
        result = _run_pulp_cli(
            pulp_task_commands["cancel"] % validated_href,
            log,
            repo_name=repo_name,
            retries=1,
        )
        if result is not None and result.returncode == 0:
            _log(log, "info", repo_name, f"Successfully cancelled Pulp task: {task_href}")
            return True
        else:
            _log(
                log, "error", repo_name,
                f"Failed to cancel Pulp task: "
                f"{_command_output(result) or 'no CLI response'}",
            )
            return False
    except Exception:
        _log(log, "error", repo_name, "Error cancelling Pulp task")
        return False


def _monitor_pulp_task(task_href, log, repo_name):
    """Monitor one exact Pulp task until a terminal state is observed."""
    last_progress_signature = None
    last_progress_time = time.monotonic()
    api_unavailable_since = None
    last_log_time = last_progress_time
    cancellation_requested = False
    cancellation_requested_at = None

    while True:
        done, total, state, error_message = _get_pulp_task_progress(
            task_href, log, repo_name
        )
        now = time.monotonic()

        if state == "query-error":
            if api_unavailable_since is None:
                api_unavailable_since = now
            unavailable_seconds = int(now - api_unavailable_since)
            if unavailable_seconds >= RPM_API_UNAVAILABLE_TIMEOUT:
                message = (
                    "Pulp task state was unavailable for "
                    f"{unavailable_seconds} seconds: {error_message}"
                )
                _log(log, "error", repo_name, message)
                return False, message
            if now - last_log_time >= 60:
                _log(
                    log, "warning", repo_name,
                    "Pulp API temporarily unavailable while monitoring "
                    f"{task_href}: {error_message}",
                )
                last_log_time = now
            time.sleep(RPM_PROGRESS_CHECK_INTERVAL)
            continue

        api_unavailable_since = None

        if state == "completed":
            return True, ""
        if state in {"failed", "canceled"}:
            message = f"Pulp task {state}: {error_message or task_href}"
            if state == "canceled" and cancellation_requested:
                message += "; cancellation confirmed"
            _log(log, "error", repo_name, message)
            return False, message

        if cancellation_requested:
            cancellation_seconds = int(now - cancellation_requested_at)
            if cancellation_seconds >= RPM_API_UNAVAILABLE_TIMEOUT:
                message = (
                    "Pulp did not reach a terminal state within "
                    f"{cancellation_seconds} seconds after cancellation"
                )
                _log(log, "error", repo_name, message)
                return False, message
            if now - last_log_time >= 60:
                _log(
                    log, "warning", repo_name,
                    f"Waiting for task cancellation to finish ({state})",
                )
                last_log_time = now
            time.sleep(RPM_PROGRESS_CHECK_INTERVAL)
            continue

        progress_signature = (state, done, total)
        if progress_signature != last_progress_signature:
            last_progress_signature = progress_signature
            last_progress_time = now
            progress = str(done) if total is None else f"{done}/{total}"
            _log(
                log, "info", repo_name,
                f"Pulp task {state}; progress {progress}",
            )
        else:
            stalled_seconds = int(now - last_progress_time)
            if stalled_seconds >= RPM_SYNC_STUCK_TIMEOUT:
                message = (
                    f"Pulp task made no progress for {stalled_seconds} seconds"
                )
                _log(log, "error", repo_name, message)
                if _cancel_pulp_task(task_href, log, repo_name):
                    cancellation_requested = True
                    cancellation_requested_at = now
                    last_progress_time = now
                    time.sleep(RPM_PROGRESS_CHECK_INTERVAL)
                    continue
                return False, f"{message}; cancellation was not confirmed"
            if now - last_log_time >= 60:
                _log(
                    log, "info", repo_name,
                    f"Pulp task still {state} after {stalled_seconds} "
                    "seconds without reported progress",
                )
                last_log_time = now

        time.sleep(RPM_PROGRESS_CHECK_INTERVAL)


def _execute_pulp_task(command, log, repo_name, repository_href=None,
                       require_task=True):
    """Dispatch one CLI mutation and monitor its correlated Pulp task.

    The mutation is sent exactly once. If its response is interrupted, the
    unique CID is used to recover the server-side task instead of repeating the
    operation.
    """
    task_cid = str(uuid.uuid4())
    command_args = (
        [str(value) for value in command]
        if isinstance(command, (list, tuple))
        else shlex.split(command)
    )
    command_args[1:1] = ["--background", "--cid", task_cid]
    _log(log, "debug", repo_name, f"Pulp correlation ID: {task_cid}")

    result = _run_pulp_cli(
        command_args,
        log,
        repo_name=repo_name,
        retries=1,
    )
    task_href = _parse_task_href(_command_output(result))

    if (
            not task_href
            and result is not None
            and result.returncode == 0
            and not require_task):
        # Some Pulp CRUD commands complete synchronously even with --background.
        return True, None, ""

    if not task_href:
        # A task may have been accepted even if the HTTP response was lost.
        # Use the CID for bounded discovery and never redispatch the mutation.
        for attempt in range(max(1, int(RPM_CLI_QUERY_RETRIES))):
            task_href = _find_pulp_task_by_cid(
                task_cid, repository_href, log, repo_name
            )
            if task_href:
                break
            if attempt + 1 < max(1, int(RPM_CLI_QUERY_RETRIES)):
                time.sleep(RPM_CLI_QUERY_RETRY_DELAY)

    if task_href:
        _log(log, "info", repo_name, f"Monitoring Pulp task {task_href}")
        success, message = _monitor_pulp_task(task_href, log, repo_name)
        return success, task_href, message

    message = _command_output(result) or "Pulp did not return a task HREF"
    _log(log, "error", repo_name, f"Unable to dispatch Pulp task: {message}")
    return False, None, message


def _cleanup_partial_repo(repo_name, previous_version, log):
    """
    Roll back only versions created by a timed-out sync.

    The repository, its last known-good version, publication and distribution
    are deliberately retained. This avoids turning a refresh timeout into a
    complete repository outage.

    Args:
        repo_name (str): Repository name to clean up
        previous_version (int): Latest version before the sync started.
        log (logging.Logger): Logger instance

    Returns:
        bool: True if cleanup succeeded, False otherwise
    """
    try:
        if not RPM_CLEANUP_ON_TIMEOUT:
            _log(log, "info", repo_name, "Timed-out repository retained; rollback disabled")
            return True

        current_version = get_repo_version(repo_name, log)
        if current_version is None:
            _log(
                log, "warning", repo_name,
                "Repository version is unavailable; no rollback attempted",
            )
            return False
        if current_version <= previous_version:
            _log(
                log, "info", repo_name,
                f"Timed-out repository retained at version {current_version}"
            )
            return True

        _log(
            log, "warning", repo_name,
            f"Rolling back versions {previous_version + 1}-{current_version}; "
            f"preserving version {previous_version}"
        )
        for version_number in range(current_version, previous_version, -1):
            command = pulp_rpm_commands["repository_version_destroy"] % (
                repo_name, version_number,
            )
            success, _, error_message = _execute_pulp_task(
                command,
                log,
                repo_name,
                require_task=False,
            )
            if not success:
                _log(
                    log, "warning", repo_name,
                    f"Failed to remove incomplete version {version_number}: "
                    f"{error_message}"
                )
                return False
        _log(log, "info", repo_name, "Incomplete versions removed; repository retained")
        return True
    except Exception:
        _log(log, "error", repo_name, "Error during safe version rollback")
        return False


def sync_rpm_repository_with_monitoring(
        repo, log, resync_repos=None, force_sync_repos=None,
        sync_policy=None):
    """
    Sync RPM repository with progress-based stuck detection.
    
    Drop-in replacement for sync_rpm_repository().
    Same args, same return format.
    
    Dispatches the CLI command in background mode and monitors its exact Pulp
    task. If no progress is reported for RPM_SYNC_STUCK_TIMEOUT seconds while
    the API remains healthy, the exact task is canceled.
    
    Args:
        repo (dict): Repository configuration
        log (logging.Logger): Logger instance
        resync_repos (str/list): Controls sync behavior
        force_sync_repos (iterable): Remotes whose URL or policy changed.
        sync_policy (str): Optional operation-level Pulp sync policy.
    
    Returns:
        tuple: (success, repo_name, actually_synced, version_changed)
    """
    repo_name = _configured_repository_name(repo)
    start = time.time()

    _log(log, "info", repo_name, "=== START REPO ===")

    try:
        _log(log, "info", repo_name, "Step 4/5: Sync started with progress monitoring")

        # Skip logic (same as original)
        force_sync = False
        resync_list = None

        if resync_repos == "all":
            force_sync = True
        elif isinstance(resync_repos, str) and resync_repos:
            resync_list = [r.strip() for r in resync_repos.split(",")]
        elif isinstance(resync_repos, list):
            resync_list = resync_repos
        if repo_name in set(force_sync_repos or ()):
            force_sync = True
            _log(
                log, "info", repo_name,
                "Remote URL or policy changed; synchronization is required",
            )

        # A killed Ansible process does not stop a Pulp background task. Wait
        # for any sync/publication still reserving this repository before
        # reading latest_version_href or deciding that the repository can be
        # skipped. This prevents a recovered sync from creating version N+1
        # after the rerun has already published version N.
        repository_href = _get_repository_href(repo_name, log)
        if not repository_href:
            _log(
                log, "error", repo_name,
                "Repository HREF is unavailable; interrupted tasks cannot "
                "be recovered safely",
            )
            return False, repo_name, False, False
        recovery_ok, recovered_sync, recovery_error = (
            _recover_active_repository_tasks(repository_href, log, repo_name)
        )
        if not recovery_ok:
            _log(
                log, "error", repo_name,
                f"Repository recovery failed: {recovery_error}",
            )
            return False, repo_name, False, False
        if recovered_sync and not force_sync:
            elapsed = int(time.time() - start)
            _log(
                log, "info", repo_name,
                "Step 4/5: Sync — RECOVERED from earlier run",
            )
            _log(
                log, "info", repo_name,
                f"=== END REPO — SUCCESS ({elapsed}s) ===",
            )
            # Mark the repository for exact publication/distribution
            # reconciliation even when Pulp skipped the recovered sync because
            # the upstream metadata had not changed.
            return True, repo_name, True, True
        if recovered_sync:
            _log(
                log, "info", repo_name,
                "Recovered an earlier sync; dispatching another sync because "
                "the remote source changed",
            )

        if resync_list:
            if repo_name in resync_list:
                force_sync = True
            elif not force_sync:
                elapsed = int(time.time() - start)
                _log(log, "info", repo_name, "Step 4/5: Sync — SKIPPED (not in resync list)")
                _log(log, "info", repo_name, f"=== END REPO — SKIPPED ({elapsed}s) ===")
                return True, repo_name, False, False

        if not force_sync:
            repository_synced = check_repository_synced(repo_name, log)
            if repository_synced is None:
                _log(
                    log, "error", repo_name,
                    "Repository state is unavailable; sync was not dispatched",
                )
                return False, repo_name, False, False
            if repository_synced:
                elapsed = int(time.time() - start)
                _log(log, "info", repo_name, "Step 4/5: Sync — SKIPPED (already synced)")
                _log(log, "info", repo_name, f"=== END REPO — SKIPPED ({elapsed}s) ===")
                return True, repo_name, False, False

        version_before = get_repo_version(repo_name, log)
        if version_before is None:
            _log(
                log, "error", repo_name,
                "Unable to record repository version; sync was not dispatched",
            )
            return False, repo_name, False, False
        _log(log, "debug", repo_name, f"Version before sync: {version_before}")

        # A unique CID lets us discover the task created by this exact CLI
        # process. Once discovered, all subsequent reads and cancellation use
        # the immutable task href rather than a repository-wide task search.
        # Dispatch once in background. The exact task state, not the lifetime of
        # a blocking CLI process, determines the synchronization result.
        remote_name = repo_name
        command_key = (
            "sync_repository_exact_mirror"
            if sync_policy == "mirror_content_only"
            else "sync_repository"
        )
        command = pulp_rpm_commands[command_key] % (repo_name, remote_name)
        task_success, task_href, task_error = _execute_pulp_task(
            command,
            log,
            repo_name,
            repository_href=repository_href,
            require_task=True,
        )
        elapsed = int(time.time() - start)

        if not task_success:
            if "cancellation confirmed" in task_error:
                _cleanup_partial_repo(repo_name, version_before, log)
            _log(
                log, "error", repo_name,
                f"Sync task failed ({task_href or 'task unavailable'}): "
                f"{task_error}",
            )
            _log(log, "info", repo_name, f"=== END REPO — FAILED ({elapsed}s) ===")
            return False, repo_name, False, False

        version_after = get_repo_version(repo_name, log)
        if version_after is None:
            _log(
                log, "error", repo_name,
                "Sync completed but the resulting repository version "
                "could not be verified",
            )
            return False, repo_name, False, False
        version_changed = version_after > version_before
        _log(log, "debug", repo_name, f"Version after sync: {version_after} (changed: {version_changed})")

        _log(log, "info", repo_name, f"Step 4/5: Sync — SYNCED ({elapsed}s)")
        _log(log, "info", repo_name, f"=== END REPO — SUCCESS ({elapsed}s) ===")
        return True, repo_name, True, version_changed

    except Exception:
        elapsed = int(time.time() - start)
        _log(log, "error", repo_name, "Repository synchronization failed")
        _log(log, "info", repo_name, f"=== END REPO — FAILED ({elapsed}s) ===")
        return False, repo_name, False, False




def get_repo_version(repo_name, log):
    """
    Get the current version number of a repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging.

    Returns:
        int or None: Version number, 0 for an empty/missing repository, or None
            when Pulp state cannot be queried.
    """
    try:
        command = pulp_rpm_commands["get_repo_version"] % repo_name
        result = _run_pulp_cli(command, log, repo_name=repo_name)

        if result is None or result.returncode != 0:
            if result is not None and _is_not_found_pulp_error(result):
                return 0
            log.error(
                "Unable to get version for '%s': %s",
                repo_name,
                _command_output(result) or "no CLI response",
            )
            return None

        try:
            repo_info = json.loads(result.stdout)
            # Extract version from latest_version_href like "/pulp/api/v3/.../versions/2/"
            version_href = repo_info.get("latest_version_href", "")
            if version_href:
                # Extract version number from href
                version = int(version_href.rstrip("/").split("/")[-1])
                return version
        except (json.JSONDecodeError, ValueError, IndexError):
            return None
        return 0
    except subprocess.CalledProcessError:
        log.error("Pulp command failed while getting version for '%s'", repo_name)
        return None
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        log.error("Subprocess error getting version for '%s'", repo_name)
        return None
    except Exception:
        log.error("Error getting version for '%s'", repo_name)
        return None


def get_repository_latest_version_href(repo_name, log):
    """Return the exact latest repository-version HREF, or None on failure."""
    result = _run_pulp_cli(
        pulp_rpm_commands["show_repository"] % repo_name,
        log,
        repo_name=repo_name,
    )
    if result is None or result.returncode != 0:
        _log(
            log, "error", repo_name,
            "Unable to read latest repository version: "
            f"{_command_output(result) or 'no CLI response'}",
        )
        return None
    try:
        href = json.loads(result.stdout).get("latest_version_href")
        return validate_repository_version_href(href) if href else None
    except (json.JSONDecodeError, ValueError, AttributeError):
        _log(log, "error", repo_name, "Invalid repository response")
        return None


def _list_publications(repo_name, log):
    """Return repository publications, or None when the query failed."""
    command = pulp_rpm_commands["check_publication"] % repo_name
    result = _run_pulp_cli(command, log, repo_name=repo_name)
    if result is None or result.returncode != 0:
        _log(
            log, "error", repo_name,
            "Unable to list publications: "
            f"{_command_output(result) or 'no CLI response'}",
        )
        return None
    try:
        payload = json.loads(result.stdout) if result.stdout.strip() else []
        publications = (
            payload.get("results", []) if isinstance(payload, dict) else payload
        )
        if not isinstance(publications, list):
            raise ValueError("publication list response is not a list")
        return publications
    except (json.JSONDecodeError, ValueError):
        _log(log, "error", repo_name, "Invalid publication response")
        return None


def _publication_version_href(publication):
    """Return a publication's repository-version HREF across CLI versions."""
    return (
        publication.get("repository_version")
        or publication.get("repository_version_href")
    )


def _get_publication_state(repo_name, log, repository_version_href=None):
    """Return (state, href) for the newest matching publication."""
    publications = _list_publications(repo_name, log)
    if publications is None:
        return None, None
    if repository_version_href:
        publications = [
            publication for publication in publications
            if _publication_version_href(publication) == repository_version_href
        ]
    if not publications:
        return False, None

    publications_with_time = [
        publication for publication in publications
        if publication.get("pulp_created")
    ]
    latest_publication = (
        max(
            publications_with_time,
            key=lambda publication: publication["pulp_created"],
        )
        if publications_with_time else publications[-1]
    )
    publication_href = latest_publication.get("pulp_href")
    if not publication_href:
        _log(log, "error", repo_name, "Publication response has no HREF")
        return None, None
    try:
        return True, validate_pulp_href(publication_href)
    except ValueError:
        _log(log, "error", repo_name, "Invalid publication HREF")
        return None, None


def get_distribution_details(repo_name, log):
    """Return distribution JSON, False if missing, or None on query failure."""
    command = pulp_rpm_commands["check_distribution"] % repo_name
    result = _run_pulp_cli(command, log, repo_name=repo_name)
    if result is None or result.returncode != 0:
        if result is not None and _is_not_found_pulp_error(result):
            return False
        _log(
            log, "error", repo_name,
            "Unable to read distribution: "
            f"{_command_output(result) or 'no CLI response'}",
        )
        return None
    try:
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise ValueError("distribution response is not an object")
        return payload
    except (json.JSONDecodeError, ValueError):
        _log(log, "error", repo_name, "Invalid distribution response")
        return None


def check_distribution_exists(repo_name, log, publication_href=None):
    """Return tri-state distribution readiness for an optional publication."""
    distribution = get_distribution_details(repo_name, log)
    if distribution is None:
        return None
    if distribution is False:
        return False
    if publication_href:
        return distribution.get("publication") == publication_href
    return True


def get_latest_publication_href(repo_name, log, repository_version_href=None):
    """
    Get the pulp_href of the latest publication for a repository.

    Args:
        repo_name (str): The name of the repository.
        log (logging.Logger): Logger instance for logging.

    Returns:
        str or None: The pulp_href of the latest publication, or None if not found.
    """
    try:
        state, publication_href = _get_publication_state(
            repo_name, log, repository_version_href
        )
        if state is not True:
            log.info("No matching publications found for '%s'", repo_name)
            return None
        log.info(
            "Latest publication href for '%s': %s",
            repo_name, publication_href,
        )
        return publication_href
    except Exception:
        log.error("Error getting latest publication for '%s'", repo_name)
        return None


def create_publication(repo, log):
    """
    Create a publication for an RPM repository.

    Args:
        repo (dict): A dictionary containing the package information.
        log (logging.Logger): Logger instance for logging the process and errors.
    Returns:
        bool: True if the publication was created successfully, False otherwise.
    """

    try:
        repo_name = _configured_repository_name(repo)

        repository_version_href = get_repository_latest_version_href(
            repo_name, log
        )
        if (
                not repository_version_href
                or repository_version_href.endswith("/versions/0/")):
            _log(
                log, "error", repo_name,
                "Step 5/5: Publication — FAILED: synchronized version missing",
            )
            return False, repo_name

        publication_exists, _ = _get_publication_state(
            repo_name, log, repository_version_href
        )
        if publication_exists is None:
            _log(
                log, "error", repo_name,
                "Step 5/5: Publication — FAILED: state unavailable",
            )
            return False, repo_name
        if publication_exists:
            _log(
                log, "info", repo_name,
                "Step 5/5: Publication — EXISTS for latest version",
            )
            return True, repo_name

        # Create a replacement for the exact latest version. Existing
        # publications remain available until distribution switching succeeds.
        version_number = int(
            repository_version_href.rstrip("/").rsplit("/", maxsplit=1)[-1]
        )
        _log(
            log, "info", repo_name,
            f"Step 5/5: Publication — creating for version {version_number}",
        )
        command = pulp_rpm_commands["publish_repository_version"] % (
            repo_name, version_number
        )
        success, _, error_message = _execute_pulp_task(
            command,
            log,
            repo_name,
            require_task=False,
        )
        if not success:
            _log(
                log, "error", repo_name,
                "Step 5/5: Publication — FAILED: "
                f"{error_message or 'unknown error'}",
            )
            return False, repo_name

        publication_ready, _ = _get_publication_state(
            repo_name, log, repository_version_href
        )
        if publication_ready is not True:
            _log(
                log, "error", repo_name,
                "Step 5/5: Publication — FAILED verification for latest "
                "repository version",
            )
            return False, repo_name

        _log(log, "info", repo_name, "Step 5/5: Publication — CREATED")
        return True, repo_name
    except subprocess.CalledProcessError:
        _log(log, "error", repo.get("package", "unknown"), "Pulp command failed")
        return False, repo.get("package", "unknown")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        _log(log, "error", repo.get("package", "unknown"), "Pulp subprocess failed")
        return False, repo.get("package", "unknown")
    except Exception:
        _log(log, "error", repo.get("package", "unknown"), "Publication failed")
        return False, repo.get("package", "unknown")


def create_distribution(repo, log, cluster_os_type, cluster_os_version):
    """
    Create or update a distribution for an RPM repository.

    Args:
        repo (dict): A dictionary containing the repository information.
        log (logging.Logger): Logger instance for logging the process and errors.
        cluster_os_type (str): The cluster OS type (for example, 'rhel').
        cluster_os_version (str): The cluster OS version (for example, '10.0').
    Returns:
        bool: True if the distribution was created or updated successfully, False otherwise.
    """
    try:
        log.info("Starting distribution creation/update for RPM repository")
        package_name = repo["package"]
        version = repo.get("version")
        sw_arch = repo.get("sw_arch")
        repo_name, base_path = build_rpm_distribution_identity(
            PULP_DISTRIBUTION_ROOT,
            sw_arch,
            cluster_os_type,
            cluster_os_version,
            package_name,
            version,
        )

        create_command = pulp_rpm_commands["distribute_repository"] % (repo_name, base_path, repo_name)
        update_command = pulp_rpm_commands["update_distribution"] % (repo_name, base_path, repo_name)

        log.info("Processing distribution for repository: '%s', Base path: '%s'", repo_name, base_path)
        repository_version_href = get_repository_latest_version_href(
            repo_name, log
        )
        if not repository_version_href:
            log.error(
                "Cannot create distribution for '%s': repository version "
                "is unavailable.", repo_name
            )
            return False, repo_name

        # Link only the publication created for the current repository version.
        pub_href = get_latest_publication_href(
            repo_name, log, repository_version_href
        )
        if not pub_href:
            log.error(
                "No publication for the latest version of '%s' after "
                "publication stage.", repo_name
            )
            return False, repo_name

        distribution = get_distribution_details(repo_name, log)
        if distribution is None:
            return False, repo_name

        if distribution is False:
            log.info(
                "Distribution for %s does not exist. Creating it.",
                package_name,
            )
            success, _, error_message = _execute_pulp_task(
                create_command, log, repo_name, require_task=False
            )
            if not success:
                # A distribution create from an interrupted run can finish
                # immediately before this create, causing this task to report
                # an already-exists conflict. Trust the resulting Pulp state,
                # not that duplicate task's return code.
                distribution = get_distribution_details(repo_name, log)
                if not isinstance(distribution, dict):
                    log.error(
                        "Failed to create distribution '%s': %s",
                        repo_name, error_message,
                    )
                    return False, repo_name
                log.info(
                    "Distribution '%s' exists after a racing create task; "
                    "continuing reconciliation.", repo_name,
                )
            else:
                distribution = get_distribution_details(repo_name, log)
            if not isinstance(distribution, dict):
                log.error(
                    "Distribution '%s' was not visible after creation.",
                    repo_name,
                )
                return False, repo_name
        elif distribution.get("base_path") != base_path:
            log.info(
                "Distribution for %s has a different base path. Updating it.",
                package_name,
            )
            success, _, error_message = _execute_pulp_task(
                update_command, log, repo_name, require_task=False
            )
            if not success:
                distribution = get_distribution_details(repo_name, log)
                if (
                        not isinstance(distribution, dict)
                        or distribution.get("base_path") != base_path):
                    log.error(
                        "Failed to update distribution '%s': %s",
                        repo_name, error_message,
                    )
                    return False, repo_name
                log.info(
                    "Distribution '%s' reached the requested base path after "
                    "a racing update task.", repo_name,
                )
            else:
                distribution = get_distribution_details(repo_name, log)
            if not isinstance(distribution, dict):
                log.error(
                    "Distribution '%s' was not visible after update.",
                    repo_name,
                )
                return False, repo_name

        if distribution.get("publication") != pub_href:
            log.info(
                "Linking distribution '%s' to publication '%s'",
                repo_name, pub_href,
            )
            update_pub_cmd = (
                pulp_rpm_commands["update_distribution_publication"]
                % (repo_name, pub_href)
            )
            success, _, error_message = _execute_pulp_task(
                update_pub_cmd, log, repo_name, require_task=False
            )
            if not success:
                if check_distribution_exists(repo_name, log, pub_href) is not True:
                    log.error(
                        "Failed to link distribution '%s' to its latest "
                        "publication: %s", repo_name, error_message,
                    )
                    return False, repo_name
                log.info(
                    "Distribution '%s' reached the requested publication "
                    "after a racing update task.", repo_name,
                )

        if check_distribution_exists(repo_name, log, pub_href) is not True:
            log.error(
                "Distribution '%s' does not reference publication '%s' "
                "after update.", repo_name, pub_href,
            )
            return False, repo_name

        return True, repo_name

    except subprocess.CalledProcessError:
        log.error(
            "Pulp command failed during distribution update for repository '%s'",
            repo.get("package", "unknown"),
        )
        return False, repo.get("package", "unknown")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        log.error(
            "Subprocess error during distribution update for repository '%s'",
            repo.get("package", "unknown"),
        )
        return False, repo.get("package", "unknown")
    except Exception:
        log.error(
            "Unexpected error during distribution update for repository '%s'",
            repo.get("package", "unknown"),
        )
        return False, repo.get("package", "unknown")

    finally:
        log.info("Completed distribution creation/update for repository '%s'", repo.get("package", "unknown"))


def _configured_pulp_origin():
    """Return the trusted Pulp origin from the configured CLI profile."""
    pulp_config = load_pulp_config(CLI_FILE_PATH)
    return str(pulp_config.get("base_url") or "")


def get_base_urls(log, pulp_base_url=None):
    """
    Fetch all distributions from Pulp RPM distribution.

    Args:
        log (logging.Logger): Logger instance for logging the process and errors.

    Returns:
        list: Normalized distribution dictionaries, or an empty list on error.
    """

    command = pulp_rpm_commands["list_distributions_with_urls"]
    attempts = max(1, int(RPM_CLI_QUERY_RETRIES))
    trusted_origin = pulp_base_url or _configured_pulp_origin()

    for attempt in range(1, attempts + 1):
        log.info(
            "Executing command: %s (attempt %d/%d)",
            " ".join(command), attempt, attempts,
        )
        result = _run_pulp_cli(command, log)

        if result is None or result.returncode != 0:
            log.warning(
                "Unable to fetch Pulp distributions (attempt %d/%d)",
                attempt, attempts,
            )
        else:
            try:
                distributions = json.loads(result.stdout)
                if not isinstance(distributions, list):
                    raise TypeError("distribution response is not a list")
                normalized_distributions = [
                    {
                        "name": validate_repository_id(
                            distribution.get("name")
                        ),
                        "base_url": normalize_pulp_distribution_url(
                            distribution.get("base_url"), trusted_origin
                        ),
                    }
                    for distribution in distributions
                ]
            except (AttributeError, json.JSONDecodeError, TypeError, ValueError):
                log.warning(
                    "Pulp returned incomplete or invalid distribution metadata "
                    "(attempt %d/%d)",
                    attempt, attempts,
                )
            else:
                if normalized_distributions:
                    log.info(
                        "Fetched %d distributions successfully.",
                        len(normalized_distributions),
                    )
                    return normalized_distributions
                log.warning(
                    "Pulp returned no distributions (attempt %d/%d)",
                    attempt, attempts,
                )

        if attempt < attempts:
            time.sleep(RPM_CLI_QUERY_RETRY_DELAY)

    log.error(
        "Unable to obtain a complete, valid Pulp distribution list after %d "
        "attempt(s)",
        attempts,
    )
    return []


def build_repo_priority_map(rpm_config):
    """Return configured DNF priorities keyed by the final Pulp repo name."""
    priorities = {}
    for repo in rpm_config:
        priority = repo.get("priority")
        if priority is None:
            continue

        priorities[_configured_repository_name(repo)] = int(priority)
    return priorities


def build_complete_repo_priority_map(
        rpm_config, repo_file_path, cluster_os_type, cluster_os_version,
        architectures, log, extra_priorities=None):
    """Return priorities for the active context plus earlier contexts.

    The sequential catalog flow rewrites one shared ``pulp.repo`` after every
    OS-version context. Preserve validated priorities belonging to other
    contexts so a later context cannot silently remove an earlier context's
    settings. Priorities for the active context always come from the current
    input, which also makes removing or changing one take effect immediately.
    """
    current_priorities = build_repo_priority_map(rpm_config)
    current_priorities.update(extra_priorities or {})
    active_prefixes = tuple(
        f"{arch}_{cluster_os_type}_{cluster_os_version}_"
        for arch in (architectures or [])
    )
    preserved_priorities = {}

    if repo_file_path and os.path.isfile(repo_file_path):
        parser = configparser.ConfigParser(
            interpolation=None, strict=False
        )
        try:
            with open(repo_file_path, "r", encoding="utf-8") as repo_file:
                parser.read_file(repo_file)
            for section in parser.sections():
                repo_name = validate_repository_id(section)
                if active_prefixes and repo_name.startswith(active_prefixes):
                    continue
                if not parser.has_option(section, "priority"):
                    continue
                priority = parser.getint(section, "priority")
                if 1 <= priority <= 100:
                    preserved_priorities[repo_name] = priority
                else:
                    log.warning(
                        "Ignoring out-of-range DNF priority for repository %s",
                        repo_name,
                    )
        except (OSError, configparser.Error, ValueError) as error:
            log.warning(
                "Unable to preserve priorities from the existing DNF file "
                "(%s); current context priorities will still be applied",
                type(error).__name__,
            )

    preserved_priorities.update(current_priorities)
    return preserved_priorities


def create_yum_repo_file(
        distributions, log, sslcacert=None, repo_priorities=None,
        pulp_base_url=None, repo_file_path=None):
    """
    Create a complete DNF repository file using trusted Pulp URLs.

    Args:
        distributions (list): A list of dictionaries containing the base URLs and names of all distributions.
        log (logging.Logger): Logger instance for logging the process and errors.
        sslcacert (str): Optional path to SSL CA certificate for HTTPS repos.
        repo_priorities (dict): Optional mapping of Pulp repo name to DNF priority.
        pulp_base_url (str): Trusted public Pulp HTTPS origin.
        repo_file_path (str): Destination path for the generated DNF file.

    Returns:
        bool: True when the complete file was atomically replaced.
    """
    try:
        repo_file_path = repo_file_path or PULP_REPO_FILE_PATH
        log.info(f"Target repo file path: {repo_file_path}")

        # Validate input
        if not distributions or not isinstance(distributions, list):
            log.error("Invalid or empty 'distributions' list provided. Skipping repo file creation.")
            return False

        log.info(f"Received {len(distributions)} distributions to process")

        trusted_origin = pulp_base_url or _configured_pulp_origin()
        normalized_distributions = []
        for distribution in distributions:
            normalized_distributions.append({
                "name": validate_repository_id(distribution.get("name")),
                "base_url": normalize_pulp_distribution_url(
                    distribution.get("base_url"), trusted_origin
                ),
            })

        repository_names = [
            distribution["name"] for distribution in normalized_distributions
        ]
        if len(repository_names) != len(set(repository_names)):
            log.error("Pulp returned duplicate RPM distribution names")
            return False
        normalized_distributions.sort(
            key=lambda distribution: distribution["name"]
        )

        # Get system architecture to filter repos
        system_arch = platform.machine()
        log.info(f"System architecture: {system_arch}")

        # Determine SSL configuration based on base_url protocol
        # Check if any distribution uses HTTPS
        uses_https = bool(normalized_distributions)

        # Auto-detect sslcacert if not provided and HTTPS is used
        if uses_https and not sslcacert:
            # Check common certificate locations
            cert_locations = [PULP_SSL_CA_CERT]
            for cert_path in cert_locations:
                if os.path.exists(cert_path):
                    sslcacert = cert_path
                    log.info("Auto-detected the configured Pulp CA certificate")
                    break

        repo_content = ""
        repo_priorities = repo_priorities or {}
        enabled_count = 0
        disabled_count = 0

        for distribution in normalized_distributions:
            repo_name = distribution["name"]
            base_url = distribution["base_url"]

            # Determine if repo should be enabled based on architecture
            # Only enable repos that match the system architecture
            # Repo names follow pattern: {arch}_{os_type}_{version}_{repo_name}
            repo_arch = next(
                (candidate for candidate in ARCH_SUFFIXES
                 if repo_name.startswith(f"{candidate}_")),
                None,
            )

            # Enable repo only if it matches system architecture
            # x86_64 system: enable x86_64 repos, disable aarch64 repos
            # aarch64 system: enable aarch64 repos, disable x86_64 repos
            if repo_arch == system_arch:
                enabled = 1
                enabled_count += 1
            elif repo_arch in ['x86_64', 'aarch64'] and repo_arch != system_arch:
                enabled = 0
                disabled_count += 1
                log.info(f"Disabling repo '{repo_name}' (arch mismatch: repo={repo_arch}, system={system_arch})")
            else:
                # No architecture prefix or unknown pattern - enable by default
                enabled = 1
                enabled_count += 1

            # Build repo entry
            repo_entry = f"""
[{repo_name}]
name={repo_name} repo
baseurl={base_url}
enabled={enabled}
gpgcheck=0"""

            if repo_name in repo_priorities:
                repo_entry += f"\npriority={repo_priorities[repo_name]}"

            # Add SSL configuration for HTTPS URLs
            if base_url.startswith("https://"):
                repo_entry += "\nsslverify=1"
                if sslcacert:
                    repo_entry += f"\nsslcacert={sslcacert}"

            repo_content += repo_entry.strip() + "\n\n"

        # Write beside the target and atomically replace it. A write failure
        # therefore leaves the previously valid repository file untouched.
        log.info("Atomically replacing pulp.repo with all repository entries")
        file_changed = atomic_write_repo_file(
            repo_file_path, repo_content.strip() + "\n"
        )

        action = "Created" if file_changed else "Verified"
        log.info(
            "%s %s with %d repositories (%d enabled, %d disabled)",
            action,
            repo_file_path,
            len(normalized_distributions),
            enabled_count,
            disabled_count,
        )
        if sslcacert:
            log.info("Pulp CA verification is enabled for DNF repositories")
        return True

    except OSError as error:
        log.error(repo_file_error_message(error))
        return False
    except (AttributeError, KeyError, TypeError, ValueError):
        log.error(
            "Invalid Pulp distribution data; existing DNF configuration "
            "was preserved"
        )
        return False


def _configured_repository_name(repo):
    """Return the final Pulp repository name for one configuration entry."""
    repo_name = repo["package"]
    version = str(repo.get("version") or "").strip()
    if version and version.lower() != "null":
        repo_name = f"{repo_name}_{version}"
    return validate_repository_id(repo_name)


def validate_resync_repos(resync_repos, rpm_config, log):
    """
    Validate that resync_repos contains only valid repository names.

    Args:
        resync_repos (str/list): The resync_repos parameter from Ansible.
        rpm_config (list): List of repository configurations.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (bool, str) - (True, "") if valid, (False, error_message) if invalid.
    """
    if resync_repos is None or resync_repos == "" or resync_repos == "all":
        return True, ""

    # Build list of valid repo names from rpm_config
    valid_repo_names = set()
    for repo in rpm_config:
        valid_repo_names.add(_configured_repository_name(repo))

    # Normalize resync_repos to list
    if isinstance(resync_repos, str):
        resync_list = [r.strip() for r in resync_repos.split(",")]
    elif isinstance(resync_repos, list):
        resync_list = resync_repos
    else:
        return True, ""  # Unknown type, skip validation

    # Check for invalid repo names
    invalid_repos = [repo for repo in resync_list if repo not in valid_repo_names]

    if invalid_repos:
        error_msg = f"Invalid repository names in resync_repos: {', '.join(invalid_repos)}. Valid names are: {', '.join(sorted(valid_repo_names))}"
        log.error(error_msg)
        return False, error_msg

    log.info(f"Validated resync_repos: {resync_list}")
    return True, ""


def _requested_repository_names(resync_repos, rpm_config):
    """Return exact repository names explicitly selected for resync."""
    configured_names = {
        _configured_repository_name(repo) for repo in rpm_config
    }
    if resync_repos == "all":
        return configured_names
    if isinstance(resync_repos, str):
        return {
            value.strip() for value in resync_repos.split(",")
            if value.strip()
        }
    if isinstance(resync_repos, list):
        return set(resync_repos)
    return set()


def _load_repository_retry_state(mirror_index_path, log):
    """Load exact repositories that require sync recovery."""
    if not mirror_index_path:
        return set()
    mirror_data = load_mirror_index(mirror_index_path, log)
    return {
        validate_repository_id(repo_name)
        for repo_name in repositories_requiring_retry(mirror_data)
    }


def _package_hashes_for_repositories(
        mirror_data, repository_names, cluster_os_type, cluster_os_version):
    """Return exact RPM identities mapped to context-qualified repositories."""
    packages = mirror_data.get("MirrorIndex", {}).get("packages", {})
    if not isinstance(packages, dict):
        raise ValueError("Mirror index package state is invalid")
    selected = {
        validate_repository_id(repo_name) for repo_name in repository_names
    }
    package_hashes = set()
    for composite_hash, entry in packages.items():
        if not isinstance(entry, dict):
            raise ValueError("Mirror index package entry is invalid")
        if entry.get("type") not in ("rpm", "rpm_repo"):
            continue
        arch = entry.get("arch")
        source_repo = entry.get("repo_name")
        if not isinstance(arch, str) or not isinstance(source_repo, str):
            raise ValueError("Mirror index RPM repository mapping is invalid")
        if not arch or not source_repo:
            continue
        full_repo_name = validate_repository_id(normalize_repo_name(
            source_repo, arch, cluster_os_type, cluster_os_version
        ))
        if full_repo_name in selected:
            package_hashes.add(composite_hash)
    return package_hashes


def _persist_repository_checkpoints(
        mirror_index_path, rpm_config, status_by_repository, log,
        version_href_by_repository=None,
        invalidate_package_repositories=None,
        clear_version_repositories=None,
        cluster_os_type=None, cluster_os_version=None):
    """Atomically persist repository lifecycle checkpoints."""
    if not mirror_index_path or not status_by_repository:
        return True
    try:
        mirror_data = load_mirror_index(mirror_index_path, log)
        version_href_by_repository = version_href_by_repository or {}
        invalidate_package_repositories = set(
            invalidate_package_repositories or ()
        )
        clear_version_repositories = set(
            clear_version_repositories or ()
        )
        if clear_version_repositories.intersection(
                version_href_by_repository):
            raise ValueError(
                "Repository version cannot be set and cleared together"
            )
        policy_by_repository = {
            _configured_repository_name(repo): repo.get("policy", "")
            for repo in rpm_config
        }
        for repo_name, status in status_by_repository.items():
            if repo_name in clear_version_repositories:
                version_href = ""
            else:
                version_href = version_href_by_repository.get(repo_name)
            if version_href:
                version_href = validate_repository_version_href(version_href)
            elif status == "ready":
                version_href = get_repository_latest_version_href(
                    repo_name, log
                )
                if not version_href:
                    _log(
                        log, "error", repo_name,
                        "Repository version is unavailable; ready state was "
                        "not persisted",
                    )
                    return False
            update_repository_sync_state(
                mirror_data,
                repo_name,
                status,
                version_href=version_href,
                policy=policy_by_repository.get(repo_name, ""),
            )
        if invalidate_package_repositories:
            if not cluster_os_type or not cluster_os_version:
                raise ValueError(
                    "OS context is required for RPM package invalidation"
                )
            package_hashes = _package_hashes_for_repositories(
                mirror_data,
                invalidate_package_repositories,
                cluster_os_type,
                cluster_os_version,
            )
            marked_count = mark_package_entries_pending(
                mirror_data, package_hashes
            )
            log.info(
                "Marked %d RPM package checkpoint(s) pending for %d "
                "repository reconciliation target(s)",
                marked_count,
                len(invalidate_package_repositories),
            )
        save_mirror_index(mirror_index_path, mirror_data, log)
        return True
    except (OSError, ValueError):
        log.error("Unable to persist RPM repository recovery state")
        return False


def process_sync_results(sync_results, rpm_config, _resync_repos, log):
    """
    Process sync results and determine which repos need publication/distribution.

    Args:
        sync_results (list): Results from sync_rpm_repository (success, name, actually_synced, version_changed).
        rpm_config (list): List of repository configurations.
        _resync_repos (str/list): Retained for call compatibility. Repository
            completeness reconciliation always covers the active context.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (repos_for_pub_dist, should_skip, skip_message) - List of repos, skip flag, and skip reason message.
    """
    # Successful skipped repositories are deliberately included. They may
    # contain synchronized content but be missing the publication or
    # distribution because an earlier process stopped between stages.
    successful_results = {
        name: (actually_synced, version_changed)
        for success, name, actually_synced, version_changed in sync_results
        if success
    }
    actually_synced_repos = [
        name for name, (actually_synced, _) in successful_results.items()
        if actually_synced
    ]
    log.info(f"Repos actually synced: {len(actually_synced_repos)} - {actually_synced_repos}")

    version_changed_repos = [
        name for name, (actually_synced, version_changed)
        in successful_results.items()
        if actually_synced and version_changed
    ]
    log.info(f"Repos with version change: {len(version_changed_repos)} - {version_changed_repos}")

    repos_for_pub_dist = []
    for repo in rpm_config:
        repo_name = _configured_repository_name(repo)
        result_state = successful_results.get(repo_name)
        if result_state is None:
            continue

        _, version_changed = result_state
        repository_version_href = get_repository_latest_version_href(
            repo_name, log
        )
        publication_exists, publication_href = (
            _get_publication_state(repo_name, log, repository_version_href)
            if repository_version_href else (False, None)
        )
        distribution_exists = (
            check_distribution_exists(repo_name, log, publication_href)
            if publication_href else False
        )
        if not version_changed and publication_exists and distribution_exists:
            continue

        repo_copy = repo.copy()
        repo_copy["_version_changed"] = bool(version_changed)
        repos_for_pub_dist.append(repo_copy)
        log.info(
            "%s requires publication/distribution: version_changed=%s, "
            "current_publication=%s, current_distribution=%s",
            repo_name, version_changed, publication_exists,
            distribution_exists,
        )

    if repos_for_pub_dist:
        log.info(
            "Processing publication/distribution for %d repository(s)",
            len(repos_for_pub_dist),
        )
        return repos_for_pub_dist, False, ""

    if actually_synced_repos:
        synced_list = ", ".join(actually_synced_repos)
        return [], True, (
            f"Sync successful for {len(actually_synced_repos)} repo(s): "
            f"{synced_list}. Existing publications/distributions retained"
        )
    return [], True, "All repositories already synchronized and published"


def validate_repository_readiness(rpm_config, log):
    """Verify exact repository-version/publication/distribution relationships."""
    failures = []
    for repo in rpm_config:
        repo_name = _configured_repository_name(repo)
        missing = []
        repository_version_href = get_repository_latest_version_href(
            repo_name, log
        )
        if (
                not repository_version_href
                or repository_version_href.endswith("/versions/0/")):
            missing.append("synchronized content")
            missing.append("publication")
            publication_href = None
        else:
            publication_state, publication_href = _get_publication_state(
                repo_name, log, repository_version_href
            )
            if publication_state is None:
                missing.append("publication state unavailable")
            elif not publication_state or not publication_href:
                missing.append("publication for latest version")

        if publication_href:
            distribution_state = check_distribution_exists(
                repo_name, log, publication_href
            )
            if distribution_state is None:
                missing.append("distribution state unavailable")
            elif not distribution_state:
                missing.append("distribution for latest publication")
        else:
            missing.append("distribution")
        if missing:
            failure = f"{repo_name} (missing: {', '.join(missing)})"
            failures.append(failure)
            log.error("Repository is not ready: %s", failure)

    return not failures, failures

# ============================================================================
# AGGREGATED REPOS FUNCTIONS
# These functions handle the additional_repos_* feature which aggregates
# multiple user-defined repos into a single Pulp repository per architecture.
# ============================================================================


def delete_aggregated_repo(repo_name, log):
    """
    Delete the aggregated repository, its remotes, and distribution for a given architecture.
    This is called before recreating the aggregated repo to ensure a clean state.

    Note: This only deletes the distribution with the exact repo_name. Old distributions
    with different naming conventions are preserved to allow coexistence during upgrades.

    Args:
        repo_name (str): Pre-built aggregated repository name.
        log (logging.Logger): Logger instance.

    Returns:
        bool: True if deletion was successful or resources didn't exist, False on error.
    """
    dist_name = repo_name

    log.info(f"Deleting aggregated resources for repo '{repo_name}'")

    # Delete distribution by name (only the one matching this repo_name)
    dist_cmd = pulp_rpm_commands["delete_distribution"] % dist_name
    execute_command(dist_cmd, log)  # Ignore errors - may not exist

    # Delete repository (this also removes associated publications)
    repo_cmd = pulp_rpm_commands["delete_repository"] % repo_name
    execute_command(repo_cmd, log)  # Ignore errors - may not exist

    log.info(f"Completed deletion of aggregated resources for repo '{repo_name}'")
    return True


def create_aggregated_repository(repo_name, log):
    """
    Create the aggregated repository for a given architecture.

    Args:
        repo_name (str): Pre-built aggregated repository name.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, repo_name)
    """
    log.info(f"Creating aggregated repository: {repo_name}")

    repository_exists = show_rpm_repository(repo_name, log)
    if repository_exists is None:
        log.error(
            "Unable to determine aggregated repository state: %s", repo_name
        )
        return False, repo_name
    if not repository_exists:
        command = pulp_rpm_commands["create_repository"] % repo_name
        result = execute_command(command, log)
        if not result:
            log.error(f"Failed to create aggregated repository: {repo_name}")
            return False, repo_name
        log.info(f"Aggregated repository '{repo_name}' created successfully.")
    else:
        log.info(f"Aggregated repository '{repo_name}' already exists.")

    return True, repo_name


def _resolve_aggregated_remote_policy(repo_entry):
    """Return a validated Pulp policy for an additional repository remote."""
    policy = str(repo_entry.get("policy", "partial")).lower()
    if policy in ("immediate", "on_demand", "streamed"):
        return validate_pulp_policy(policy)

    caching = repo_entry.get("caching", True)
    if not isinstance(caching, bool):
        raise ValueError("Additional repository caching must be a boolean")
    resolved_policy = POLICY_CACHING_MAP.get((policy, caching), policy)
    return validate_pulp_policy(resolved_policy)


def _selected_additional_architectures(additional_repos_config,
                                       selected_architectures):
    """Return configured architectures in stable execution order."""
    configured = set((additional_repos_config or {}).keys())
    requested = list(selected_architectures or [])
    if requested:
        return [arch for arch in requested if arch in configured]
    ordered = [arch for arch in ARCH_SUFFIXES if arch in configured]
    return ordered + sorted(configured - set(ordered))


def validate_additional_repo_contract(
        additional_repos_config, selected_architectures, rpm_config,
        cluster_os_type, cluster_os_version):
    """Validate one aggregate's policy, priority and source identity contract.

    This check runs before any Pulp mutation so a conflicting aggregate cannot
    partially change repository state.
    """
    active_architectures = []
    aggregate_priorities = {}
    configured_repository_names = {
        _configured_repository_name(repo) for repo in rpm_config
    }

    for arch in _selected_additional_architectures(
            additional_repos_config, selected_architectures):
        repos = (additional_repos_config or {}).get(arch) or []
        if not repos:
            continue
        if not isinstance(repos, list):
            raise ValueError(
                f"additional_repos_config.{arch} must be a list"
            )

        aggregate_name = validate_repository_id(build_repo_name(
            arch, cluster_os_type, cluster_os_version,
            AGGREGATED_REPO_SUFFIX,
        ))
        if aggregate_name in configured_repository_names:
            raise ValueError(
                f"Repository name '{aggregate_name}' is reserved for "
                "additional_repos"
            )

        effective_policies = set()
        effective_priorities = set()
        source_names = set()
        for repo_entry in repos:
            if not isinstance(repo_entry, dict):
                raise ValueError(
                    f"additional_repos_config.{arch} entries must be mappings"
                )
            source_name = validate_repository_id(
                repo_entry.get("original_name") or repo_entry.get("name")
            )
            if source_name in source_names:
                raise ValueError(
                    f"Duplicate additional repository source '{source_name}' "
                    f"for architecture '{arch}'"
                )
            source_names.add(source_name)
            validate_repository_url(repo_entry.get("url"))
            effective_policies.add(
                _resolve_aggregated_remote_policy(repo_entry)
            )

            priority = repo_entry.get("priority")
            if priority is None:
                priority = 99
            if (isinstance(priority, bool) or not isinstance(priority, int)
                    or priority < 1 or priority > 100):
                raise ValueError(
                    f"Additional repository '{source_name}' priority must be "
                    "an integer from 1 through 100"
                )
            effective_priorities.add(priority)

            client_cert = (
                repo_entry.get("sslclientcert")
                or repo_entry.get("client_cert")
            )
            client_key = (
                repo_entry.get("sslclientkey")
                or repo_entry.get("client_key")
            )
            if bool(client_cert) != bool(client_key):
                raise ValueError(
                    f"Additional repository '{source_name}' must configure "
                    "sslclientcert and sslclientkey together"
                )

        if len(effective_policies) != 1:
            raise ValueError(
                f"Additional repositories for '{arch}' must use one effective "
                "Pulp policy; found " + ", ".join(sorted(effective_policies))
            )
        if len(effective_priorities) != 1:
            raise ValueError(
                f"Additional repositories for '{arch}' must use one effective "
                "DNF priority; found "
                + ", ".join(
                    str(value) for value in sorted(effective_priorities)
                )
            )

        active_architectures.append(arch)
        aggregate_priorities[aggregate_name] = next(
            iter(effective_priorities)
        )

    return active_architectures, aggregate_priorities


def create_aggregated_remote(repo_entry, repo_name, log):
    """
    Create or update a remote for an additional repo entry.

    Args:
        repo_entry (dict): Repository entry with name, url, policy, and optional SSL certs.
        repo_name (str): Pre-built aggregated repository name (used as prefix for remote name).
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, remote_name)
    """
    repo_name = validate_repository_id(repo_name)
    name = validate_repository_id(
        repo_entry.get("original_name") or repo_entry["name"]
    )
    url = validate_repository_url(repo_entry["url"])
    policy = _resolve_aggregated_remote_policy(repo_entry)
    remote_name = validate_repository_id(f"{repo_name}-source-{name}")

    log.info("Creating or updating aggregated remote '%s'.", remote_name)

    ca_cert = repo_entry.get("sslcacert") or repo_entry.get("ca_cert", "")
    client_key = (
        repo_entry.get("sslclientkey") or repo_entry.get("client_key", "")
    )
    client_cert = (
        repo_entry.get("sslclientcert") or repo_entry.get("client_cert", "")
    )

    remote_exists = show_rpm_remote(remote_name, log)
    if remote_exists is None:
        log.error("Unable to determine remote state: %s", remote_name)
        return False, remote_name

    action = "create" if not remote_exists else "update"
    command = build_rpm_remote_command(
        action,
        name=remote_name,
        url=url,
        policy=policy,
        ca_cert=f"@{ca_cert}" if ca_cert else None,
        client_cert=f"@{client_cert}" if client_cert else None,
        client_key=f"@{client_key}" if client_key else None,
    )

    result = execute_command(command, log)
    if not result:
        log.error(f"Failed to create/update remote: {remote_name}")
        return False, remote_name

    log.info(f"Remote '{remote_name}' created/updated successfully.")
    return True, remote_name


def sync_aggregated_repository(repo_name, remote_name, log):
    """
    Sync the aggregated repository with a specific remote.

    Args:
        repo_name (str): Name of the aggregated repository.
        remote_name (str): Name of the remote to sync from.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, remote_name)
    """
    repo_name = validate_repository_id(repo_name)
    remote_name = validate_repository_id(remote_name)
    log.info(f"Syncing repository '{repo_name}' with remote '{remote_name}'")

    command = pulp_rpm_commands["sync_repository"] % (
        repo_name, remote_name,
    )
    repository_href = _get_repository_href(repo_name, log)
    success, _, error_message = _execute_pulp_task(
        command,
        log,
        repo_name,
        repository_href=repository_href,
        require_task=True,
    )

    if not success:
        log.error(
            "Failed to sync repository '%s' with remote '%s': %s",
            repo_name, remote_name, error_message,
        )
        return False, remote_name

    log.info(f"Successfully synced repository '{repo_name}' with remote '{remote_name}'")
    return True, remote_name


def create_aggregated_publication(repo_name, log):
    """
    Create a publication for the aggregated repository.

    Args:
        repo_name (str): Name of the aggregated repository.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, publication_href or None)
    """
    log.info(f"Creating publication for aggregated repository: {repo_name}")

    try:
        repository_version_href = get_repository_latest_version_href(
            repo_name, log
        )
        if not repository_version_href:
            log.error(
                "Failed to determine latest version for aggregated repository %s",
                repo_name,
            )
            return False, None

        publication_href = get_latest_publication_href(
            repo_name, log, repository_version_href
        )
        if publication_href:
            log.info(
                "Publication already exists for aggregated repository version: %s",
                publication_href,
            )
            return True, publication_href

        version_number = int(
            repository_version_href.rstrip("/").rsplit("/", maxsplit=1)[-1]
        )
        command = pulp_rpm_commands["publish_repository_version"] % (
            repo_name, version_number
        )
        success, _, error_message = _execute_pulp_task(
            command, log, repo_name, require_task=False
        )
        if not success:
            log.error(
                "Failed to create publication for %s: %s",
                repo_name, error_message,
            )
            return False, None

        publication_href = get_latest_publication_href(
            repo_name, log, repository_version_href
        )
        if not publication_href:
            log.error(
                "Publication for %s was not visible after creation", repo_name
            )
            return False, None
        log.info("Publication created with href: %s", publication_href)
        return True, publication_href

    except Exception:
        log.error("Exception during publication creation")
        return False, None


def create_aggregated_distribution(repo_name, base_path, pub_href, log):
    """
    Create or update the distribution for the aggregated repository.

    Args:
        repo_name (str): Pre-built aggregated repository name.
        base_path (str): Pre-built base path for the distribution.
        pub_href (str): Publication href to associate with distribution.
        log (logging.Logger): Logger instance.

    Returns:
        tuple: (success, distribution_name)
    """
    dist_name = repo_name

    log.info(f"Creating/updating distribution '{dist_name}' with base_path '{base_path}'")

    # Validate pub_href matches expected Pulp href format (allowlist validation)
    validated_href = validate_pulp_href(pub_href) if pub_href else None

    distribution = get_distribution_details(dist_name, log)
    if distribution is None:
        return False, dist_name

    if distribution is False:
        create_cmd = pulp_rpm_commands["distribute_repository"] % (dist_name, base_path, repo_name)
        success, _, error_message = _execute_pulp_task(
            create_cmd, log, dist_name, require_task=False
        )
        if not success:
            log.error(
                "Failed to create distribution %s: %s",
                dist_name, error_message,
            )
            return False, dist_name
    elif distribution.get("base_path") != base_path:
        update_cmd = pulp_rpm_commands["update_distribution"] % (
            dist_name, base_path, repo_name
        )
        success, _, error_message = _execute_pulp_task(
            update_cmd, log, dist_name, require_task=False
        )
        if not success:
            log.error(
                "Failed to update distribution %s: %s",
                dist_name, error_message,
            )
            return False, dist_name

    if not validated_href:
        log.error("Publication HREF is required for distribution %s", dist_name)
        return False, dist_name

    update_command = (
        pulp_rpm_commands["update_distribution_publication"]
        % (dist_name, validated_href)
    )
    success, _, error_message = _execute_pulp_task(
        update_command, log, dist_name, require_task=False
    )
    if not success:
        log.error(
            "Failed to link distribution %s to publication: %s",
            dist_name, error_message,
        )
        return False, dist_name

    if check_distribution_exists(dist_name, log, validated_href) is not True:
        log.error("Distribution %s failed final publication validation", dist_name)
        return False, dist_name

    return True, dist_name


def manage_aggregated_repos(
        additional_repos_config, log, cluster_os_type,
        cluster_os_version, selected_architectures):
    """
    Manage aggregated repositories for additional_repos_* entries.
    This function handles the complete workflow:
    1. Reconcile the aggregated repository without deleting serving state
    2. Create or update remotes for each repo entry
    3. Sync each remote to the aggregated repository
    4. Create a publication for the completed repository version
    5. Create or update the distribution only after publication succeeds

    Args:
        additional_repos_config (dict): Dictionary with arch as key and list of repo configs as value.
        log (logging.Logger): Logger instance.
        cluster_os_type (str): The cluster OS type (e.g., 'rhel').
        cluster_os_version (str): The cluster OS version (e.g., '10.0').

    Returns:
        tuple: (success, error_message)
    """
    log.info("Starting management of aggregated repositories")

    for arch in selected_architectures:
        repos = additional_repos_config.get(arch, [])
        if not repos:
            log.info("No aggregated repositories configured for %s; skipping", arch)
            continue
        repo_name = build_repo_name(arch, cluster_os_type, cluster_os_version, AGGREGATED_REPO_SUFFIX)
        base_path = AGGREGATED_BASE_PATH_TEMPLATE.format(arch=arch, os_type=cluster_os_type, os_version=cluster_os_version, repo_name=repo_name)

        log.info(f"Processing aggregated repos for arch '{arch}': {len(repos)} repos")

        # Preserve the last-known-good repository/publication/distribution
        # while remotes and replacement content are reconciled. Deleting the
        # active chain here makes a transient upstream failure an outage.
        log.info(f"Step 1: Reconciling aggregated repository for {arch}")
        success, _ = create_aggregated_repository(repo_name, log)
        if not success:
            return False, f"Failed to create aggregated repository for {arch}"

        # Step 2 & 3: Create remotes and sync (only if there are repos)
        if repos:
            sync_failures = []

            for repo_entry in repos:
                # Create remote
                log.info(f"Step 2: Creating remote for '{repo_entry['name']}'")
                success, remote_name = create_aggregated_remote(repo_entry, repo_name, log)
                if not success:
                    return False, f"Failed to create remote for {repo_entry['name']}"

                # Sync to aggregated repo
                log.info(f"Step 3: Syncing remote '{remote_name}' to aggregated repo")
                success, _ = sync_aggregated_repository(repo_name, remote_name, log)
                if not success:
                    sync_failures.append(repo_entry['name'])

            # Check if all syncs succeeded
            if sync_failures:
                return False, f"Failed to sync repos for {arch}: {', '.join(sync_failures)}"

        # Step 4: Create a replacement publication. The current distribution
        # remains available if remote reconciliation or synchronization failed.
        log.info(f"Step 4: Creating publication for {arch}")
        success, pub_href = create_aggregated_publication(repo_name, log)
        if not success:
            return False, f"Failed to create publication for aggregated repo {arch}"

        # Step 5: Switch the distribution only after replacement publication
        # creation and verification have succeeded.
        log.info(f"Step 5: Creating/updating distribution for {arch}")
        success, _ = create_aggregated_distribution(repo_name, base_path, pub_href, log)
        if not success:
            return False, f"Failed to create distribution for aggregated repo {arch}"

        log.info(f"Successfully completed aggregated repo management for {arch}")

    log.info("Completed management of all aggregated repositories")
    return True, "success"


def _repository_version_number(version):
    """Return the numeric identifier from one Pulp repository version."""
    number = version.get("number")
    if number is not None:
        return int(number)
    href = str(version.get("pulp_href") or "").rstrip("/")
    if not href:
        raise ValueError("Repository version response has no number or HREF")
    return int(href.rsplit("/", maxsplit=1)[-1])


def _repository_version_number_from_href(version_href):
    """Return the numeric identifier from a validated version HREF."""
    normalized_href = validate_repository_version_href(version_href)
    return int(normalized_href.rstrip("/").rsplit("/", maxsplit=1)[-1])


def _content_package_count(summary):
    """Return the RPM package count from a Pulp content-summary object."""
    if not isinstance(summary, dict):
        return 0
    package_count = 0
    for content_type, value in summary.items():
        if str(content_type).rsplit(".", maxsplit=1)[-1] != "package":
            continue
        if isinstance(value, int):
            package_count += value
        elif isinstance(value, dict):
            package_count += int(value.get("count", 0))
    return package_count


def _repository_version_metrics(repo_name, version_number, log):
    """Return RPM package additions and removals for a repository version."""
    command = pulp_rpm_commands["show_repository_version"] % (
        repo_name, version_number,
    )
    result = _run_pulp_cli(command, log, repo_name=repo_name)
    if result is None or result.returncode != 0:
        raise RuntimeError("Unable to read synchronized repository version")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Pulp returned invalid repository-version data"
        ) from error
    content_summary = payload.get("content_summary", {})
    return (
        _content_package_count(
            payload.get(
                "added_content_summary", content_summary.get("added", {})
            )
        ),
        _content_package_count(
            payload.get(
                "removed_content_summary", content_summary.get("removed", {})
            )
        ),
    )


def _parse_pulp_list_page(result, object_label):
    """Return one validated Pulp list page from CLI JSON output."""
    try:
        payload = json.loads(result.stdout or "[]")
        items = payload.get("results", []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise ValueError("Pulp list response is not a list")
        return items
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise RuntimeError(
            f"Pulp returned invalid {object_label} data"
        ) from error


def _list_all_publications(repo_name, log):
    """Return every repository publication using bounded pagination."""
    repo_name = validate_repository_id(repo_name)
    publications = []
    offset = 0
    seen_pages = set()
    while True:
        command = build_rpm_publication_list_command(
            repo_name, limit=_PULP_LIST_PAGE_SIZE, offset=offset
        )
        result = _run_pulp_cli(command, log, repo_name=repo_name)
        if result is None or result.returncode != 0:
            raise RuntimeError("Unable to list repository publications")
        page = _parse_pulp_list_page(result, "publication")
        if not page:
            break
        page_identity = tuple(
            str(item.get("pulp_href") or item.get("pulp_created") or "")
            for item in page
        )
        if page_identity in seen_pages:
            raise RuntimeError("Pulp publication pagination did not advance")
        seen_pages.add(page_identity)
        publications.extend(page)
        if len(page) < _PULP_LIST_PAGE_SIZE:
            break
        offset += len(page)
    return publications


def _list_repository_versions(repo_name, log):
    """Return all repository-version numbers in ascending order."""
    repo_name = validate_repository_id(repo_name)
    versions = []
    offset = 0
    seen_pages = set()
    while True:
        command = build_rpm_repository_version_list_command(
            repo_name, limit=_PULP_LIST_PAGE_SIZE, offset=offset
        )
        result = _run_pulp_cli(command, log, repo_name=repo_name)
        if result is None or result.returncode != 0:
            raise RuntimeError("Unable to list repository versions")
        page = _parse_pulp_list_page(result, "repository-version")
        if not page:
            break
        page_identity = tuple(_repository_version_number(item) for item in page)
        if page_identity in seen_pages:
            raise RuntimeError(
                "Pulp repository-version pagination did not advance"
            )
        seen_pages.add(page_identity)
        versions.extend(page_identity)
        if len(page) < _PULP_LIST_PAGE_SIZE:
            break
        offset += len(page)
    return sorted(set(versions))


def _publication_repository_version_href(publication_href, repo_name, log):
    """Return the exact repository-version HREF owned by a publication."""
    publication_href = validate_pulp_href(publication_href)
    result = _run_pulp_cli(
        pulp_common_commands["show_href"] % publication_href,
        log,
        repo_name=repo_name,
    )
    if result is None or result.returncode != 0:
        raise RuntimeError("Unable to inspect the active publication")
    try:
        publication = json.loads(result.stdout)
        if not isinstance(publication, dict):
            raise ValueError("Publication response is not an object")
        version_href = _publication_version_href(publication)
        if not version_href:
            raise ValueError("Publication response has no repository version")
        return validate_repository_version_href(version_href)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise RuntimeError("Pulp returned invalid publication data") from error


def _distribution_served_state(repo_name, log):
    """Return the publication and repository version served by a distribution."""
    distribution = get_distribution_details(repo_name, log)
    if not isinstance(distribution, dict):
        raise RuntimeError("Catalog-referenced Pulp distribution is unavailable")
    publication_href = distribution.get("publication")
    if not publication_href:
        raise RuntimeError("Pulp distribution has no current publication")
    publication_href = validate_pulp_href(publication_href)
    version_href = _publication_repository_version_href(
        publication_href, repo_name, log
    )
    return publication_href, version_href


def _validate_served_repomd(repo_name, pulp_base_url, log):
    """Verify that the current distribution serves valid RPM metadata."""
    distribution = get_distribution_details(repo_name, log)
    if not isinstance(distribution, dict):
        return False, "Pulp distribution is unavailable"
    try:
        base_url = normalize_pulp_distribution_url(
            distribution.get("base_url"), pulp_base_url
        )
        metadata_url = f"{base_url.rstrip('/')}/repodata/repomd.xml"
        parsed_url = urlsplit(metadata_url)
        credentials_present = (
            parsed_url.username is not None
            or parsed_url.password is not None
        )
        if parsed_url.scheme != "https" or not parsed_url.hostname:
            return False, "Published metadata URL is not a secure HTTPS origin"
        if credentials_present or parsed_url.query or parsed_url.fragment:
            return False, "Published metadata URL is not a secure HTTPS origin"
        ca_bundle = os.environ.get("PULP_CA_BUNDLE") or PULP_SSL_CA_CERT
        if not ca_bundle or not os.path.isfile(ca_bundle):
            return False, "Pulp CA certificate is unavailable"
        with requests.get(
                metadata_url,
                allow_redirects=False,
                stream=True,
                timeout=60,
                verify=ca_bundle,
        ) as response:
            if 300 <= response.status_code < 400:
                return (
                    False,
                    "Published repomd.xml redirect is not permitted",
                )
            if response.status_code != 200:
                return False, "Published repomd.xml returned a non-success status"
            document = b""
            for chunk in response.iter_content(chunk_size=64 * 1024):
                document += chunk
                if len(document) > _MAX_REPOMD_BYTES:
                    return (
                        False,
                        "Published repomd.xml exceeds the validation limit",
                    )
        upper_document = document.upper()
        if b"<!DOCTYPE" in upper_document or b"<!ENTITY" in upper_document:
            return False, "Published repomd.xml contains forbidden declarations"
        if ElementTree is None:
            return False, "Secure XML parser is unavailable"
        root = ElementTree.fromstring(document)
        if root.tag.rsplit("}", maxsplit=1)[-1] != "repomd":
            return False, "Published metadata is not a repomd document"
        return True, "Published repomd.xml is valid"
    except requests.RequestException:
        _log(log, "error", repo_name, "Published repomd.xml request failed")
        return False, "Published repomd.xml request failed"
    except (OSError, ValueError):
        _log(log, "error", repo_name, "Published repomd.xml TLS validation failed")
        return False, "Published repomd.xml TLS validation failed"
    except _XML_PARSE_EXCEPTIONS:
        _log(log, "error", repo_name, "Published repomd.xml is invalid")
        return False, "Published repomd.xml is invalid"


def _switch_distribution_publication(repo_name, publication_href, log):
    """Point a distribution to a publication and verify the resulting state."""
    command = pulp_rpm_commands["update_distribution_publication"] % (
        repo_name, validate_pulp_href(publication_href),
    )
    success, _, error_message = _execute_pulp_task(
        command, log, repo_name, require_task=False
    )
    if not success:
        return False, error_message
    if check_distribution_exists(repo_name, log, publication_href) is not True:
        return False, "Distribution did not retain the requested publication"
    return True, "Distribution publication updated"


def _prune_superseded_repository_state(
        repo_name, current_publication, current_version, log):
    """Delete every publication/version superseded by the verified target."""
    publications_removed = 0
    for publication in _list_all_publications(repo_name, log):
        publication_href = publication.get("pulp_href")
        if not publication_href:
            raise RuntimeError("Publication response has no HREF")
        publication_href = validate_pulp_href(publication_href)
        if publication_href == current_publication:
            continue
        command = pulp_rpm_commands["delete_publication"] % publication_href
        success, _, _error_message = _execute_pulp_task(
            command, log, repo_name, require_task=False
        )
        if not success:
            raise RuntimeError("Unable to delete superseded publication")
        publications_removed += 1

    versions_removed = 0
    superseded_versions = [
        version for version in _list_repository_versions(repo_name, log)
        if version > 0 and version != current_version
    ]
    for version in sorted(superseded_versions, reverse=True):
        command = pulp_rpm_commands["repository_version_destroy"] % (
            repo_name, version,
        )
        success, _, _error_message = _execute_pulp_task(
            command, log, repo_name, require_task=False
        )
        if not success:
            raise RuntimeError("Unable to delete superseded repository version")
        versions_removed += 1
    return publications_removed, versions_removed


def _verify_exact_repository_state(
        repo_name, current_publication, current_version_href,
        pulp_base_url, log):
    """Verify distribution, publication, version and HTTPS metadata agreement."""
    publications = _list_all_publications(repo_name, log)
    publication_hrefs = [
        validate_pulp_href(publication.get("pulp_href"))
        for publication in publications
        if publication.get("pulp_href")
    ]
    if publication_hrefs != [current_publication]:
        raise RuntimeError("Superseded repository publications remain")

    current_version = _repository_version_number_from_href(
        current_version_href
    )
    nonzero_versions = [
        version for version in _list_repository_versions(repo_name, log)
        if version > 0
    ]
    if nonzero_versions != [current_version]:
        raise RuntimeError("Superseded repository versions remain")

    served_publication, served_version_href = _distribution_served_state(
        repo_name, log
    )
    if (
            served_publication != current_publication
            or served_version_href != current_version_href):
        raise RuntimeError("Distribution does not serve the verified version")

    metadata_valid, _metadata_error = _validate_served_repomd(
        repo_name, pulp_base_url, log
    )
    if not metadata_valid:
        raise RuntimeError("Published metadata failed final validation")


def _aggregate_repository_name(
        arch, cluster_os_type, cluster_os_version):
    """Return the stable public identity for one additional-repo aggregate."""
    return validate_repository_id(build_repo_name(
        arch,
        cluster_os_type,
        cluster_os_version,
        AGGREGATED_REPO_SUFFIX,
    ))


def _aggregate_source_repository_name(aggregate_name, repo_entry):
    """Return one private source repository/remote identity."""
    source_name = validate_repository_id(
        repo_entry.get("original_name") or repo_entry.get("name")
    )
    return validate_repository_id(f"{aggregate_name}-source-{source_name}")


def _list_repository_content_hrefs(repo_name, version_href, log):
    """Return the complete validated content set for one RPM repo version."""
    repo_name = validate_repository_id(repo_name)
    version = _repository_version_number_from_href(version_href)
    content_hrefs = set()
    offset = 0
    seen_pages = set()
    while True:
        command = build_rpm_repository_content_list_command(
            repo_name,
            version,
            limit=_PULP_LIST_PAGE_SIZE,
            offset=offset,
        )
        result = _run_pulp_cli(command, log, repo_name=repo_name)
        if result is None or result.returncode != 0:
            raise RuntimeError("Unable to list repository content")
        page = _parse_pulp_list_page(result, "repository-content")
        if not page:
            break
        page_hrefs = []
        for item in page:
            if not isinstance(item, dict) or not item.get("pulp_href"):
                raise RuntimeError("Pulp content response has no HREF")
            page_hrefs.append(validate_pulp_href(item["pulp_href"]))
        page_identity = tuple(page_hrefs)
        if page_identity in seen_pages:
            raise RuntimeError("Pulp content pagination did not advance")
        seen_pages.add(page_identity)
        content_hrefs.update(page_hrefs)
        if len(page) < _PULP_LIST_PAGE_SIZE:
            break
        offset += len(page)
    return content_hrefs


def _write_content_change_file(content_hrefs):
    """Write a private temporary Pulp content-change JSON file."""
    file_descriptor, file_path = tempfile.mkstemp(
        prefix="repo-manager-rpm-content-", suffix=".json"
    )
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                [{"pulp_href": href} for href in sorted(content_hrefs)],
                stream,
            )
    except Exception:
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        try:
            os.unlink(file_path)
        except OSError:
            pass
        raise
    return file_path


def _modify_aggregate_content(
        aggregate_name, base_version_href, add_hrefs, remove_hrefs, log):
    """Create one aggregate version containing the exact requested delta."""
    add_file = None
    remove_file = None
    try:
        if add_hrefs:
            add_file = _write_content_change_file(add_hrefs)
        if remove_hrefs:
            remove_file = _write_content_change_file(remove_hrefs)
        command = build_rpm_repository_content_modify_command(
            aggregate_name,
            _repository_version_number_from_href(base_version_href),
            add_content_file=add_file,
            remove_content_file=remove_file,
        )
        repository_href = _get_repository_href(aggregate_name, log)
        if not repository_href:
            raise RuntimeError("Aggregate repository HREF is unavailable")
        success, _, error_message = _execute_pulp_task(
            command,
            log,
            aggregate_name,
            repository_href=repository_href,
            require_task=True,
        )
        if not success:
            raise RuntimeError(
                error_message or "Aggregate content modification failed"
            )
    finally:
        for file_path in (add_file, remove_file):
            if file_path:
                try:
                    os.unlink(file_path)
                except OSError:
                    pass


def _list_owned_source_objects(aggregate_name, resource, log):
    """Return private RPM source objects owned by one aggregate."""
    prefix = f"{validate_repository_id(aggregate_name)}-source-"
    objects = []
    offset = 0
    seen_pages = set()
    while True:
        command = build_pulp_entity_command(
            "rpm",
            resource,
            "list",
            fields=("name",),
            limit=_PULP_LIST_PAGE_SIZE,
            offset=offset,
        )
        result = _run_pulp_cli(command, log, repo_name=aggregate_name)
        if result is None or result.returncode != 0:
            raise RuntimeError(
                f"Unable to list aggregate source {resource}s: "
                f"{_command_output(result) or 'no CLI response'}"
            )
        page = _parse_pulp_list_page(result, f"aggregate-source-{resource}")
        if not page:
            break
        names = tuple(str(item.get("name") or "") for item in page)
        if names in seen_pages:
            raise RuntimeError("Pulp source-object pagination did not advance")
        seen_pages.add(names)
        for item in page:
            name = item.get("name") if isinstance(item, dict) else None
            if name and str(name).startswith(prefix):
                objects.append(validate_repository_id(name))
        if len(page) < _PULP_LIST_PAGE_SIZE:
            break
        offset += len(page)
    return sorted(set(objects))


def _destroy_rpm_source_object(resource, name, log):
    """Destroy and verify one private aggregate source object."""
    name = validate_repository_id(name)
    command = build_pulp_entity_command(
        "rpm", resource, "destroy", name=name
    )
    success, _, error_message = _execute_pulp_task(
        command, log, name, require_task=False
    )
    if not success:
        raise RuntimeError(
            error_message or f"Unable to delete aggregate source {resource}"
        )
    state = _query_object_exists(
        build_pulp_entity_command("rpm", resource, "show", name=name),
        log,
        name,
    )
    if state is not False:
        raise RuntimeError(f"Aggregate source {resource} deletion is unverified")


def _prune_private_source_versions(repo_name, current_version_href, log):
    """Retain only the exact version used to compose the public aggregate."""
    current_version = _repository_version_number_from_href(
        current_version_href
    )
    for version in sorted(
            (
                value for value in _list_repository_versions(repo_name, log)
                if value > 0 and value != current_version
            ),
            reverse=True):
        success, _, error_message = _execute_pulp_task(
            pulp_rpm_commands["repository_version_destroy"] % (
                repo_name, version
            ),
            log,
            repo_name,
            require_task=False,
        )
        if not success:
            raise RuntimeError(
                error_message or "Unable to prune aggregate source version"
            )


def _cleanup_stale_aggregate_sources(
        aggregate_name, desired_source_names, log):
    """Delete private repositories before their remotes after public commit."""
    desired = set(desired_source_names)
    repositories = set(_list_owned_source_objects(
        aggregate_name, "repository", log
    ))
    remotes = set(_list_owned_source_objects(aggregate_name, "remote", log))
    for repository_name in sorted(repositories - desired):
        _destroy_rpm_source_object(
            "repository", repository_name, log
        )
    for remote_name in sorted(remotes - desired):
        _destroy_rpm_source_object("remote", remote_name, log)


def _validate_exact_aggregate_target(
        aggregate_name, repo_entries, pulp_base_url, log):
    """Validate one public aggregate and safely classify source state."""
    repository_href = _get_repository_href(aggregate_name, log)
    if not repository_href:
        raise RuntimeError(
            "Aggregate repository is unavailable; run the download workflow "
            "before repo_sync"
        )
    publication_href, version_href = _distribution_served_state(
        aggregate_name, log
    )
    if not version_href.startswith(f"{repository_href}versions/"):
        raise RuntimeError(
            "Aggregate distribution publication belongs to another repository"
        )
    if _repository_version_number_from_href(version_href) <= 0:
        raise RuntimeError("Aggregate distribution does not serve content")
    metadata_valid, metadata_error = _validate_served_repomd(
        aggregate_name, pulp_base_url, log
    )
    if not metadata_valid:
        raise RuntimeError(metadata_error)

    for repo_entry in repo_entries:
        validate_repository_url(repo_entry.get("url"))
        _resolve_aggregated_remote_policy(repo_entry)
        source_name = _aggregate_source_repository_name(
            aggregate_name, repo_entry
        )
        remote_exists, remote_state = _get_rpm_remote_state(source_name, log)
        if remote_exists is None:
            raise RuntimeError("Aggregate source remote state is unavailable")
        if remote_exists:
            try:
                validate_repository_url(remote_state.get("url"))
                validate_pulp_policy(remote_state.get("policy"))
            except (TypeError, ValueError) as error:
                raise RuntimeError(
                    "Aggregate source remote state is invalid"
                ) from error
        repository_exists = show_rpm_repository(source_name, log)
        if repository_exists is None:
            raise RuntimeError(
                "Aggregate source repository state is unavailable"
            )
    return publication_href, version_href


def preflight_exact_additional_repositories(
        additional_repos_config, selected_architectures, pulp_base_url, log,
        cluster_os_type, cluster_os_version):
    """Validate every URL-backed aggregate without mutating Pulp."""
    repositories = {}
    active_architectures = _selected_additional_architectures(
        additional_repos_config, selected_architectures
    )
    for index, arch in enumerate(active_architectures):
        repo_entries = (additional_repos_config or {}).get(arch) or []
        if not repo_entries:
            continue
        aggregate_name = _aggregate_repository_name(
            arch, cluster_os_type, cluster_os_version
        )
        try:
            _, version_href = _validate_exact_aggregate_target(
                aggregate_name, repo_entries, pulp_base_url, log
            )
            repositories[aggregate_name] = {
                "preflight_status": "success",
                "sync_status": "not_run",
                "cleanup_status": "not_run",
                "version_href": version_href,
            }
        except (RuntimeError, TypeError, ValueError) as error:
            repositories[aggregate_name] = {
                "preflight_status": "failed",
                "sync_status": "not_run",
                "cleanup_status": "not_run",
                "error": str(error),
            }
            for pending_arch in active_architectures[index + 1:]:
                pending_entries = (
                    additional_repos_config or {}
                ).get(pending_arch) or []
                if pending_entries:
                    pending_name = _aggregate_repository_name(
                        pending_arch, cluster_os_type, cluster_os_version
                    )
                    repositories[pending_name] = {
                        "preflight_status": "not_run",
                        "sync_status": "not_run",
                        "cleanup_status": "not_run",
                    }
            return False, repositories, str(error)
    return True, repositories, "Additional-repository preflight completed"


def _validate_exact_mirror_target(repo, pulp_base_url, log):
    """Validate one existing repository chain without mutating Pulp."""
    repo_name = _configured_repository_name(repo)
    repository_href = _get_repository_href(repo_name, log)
    if not repository_href:
        raise RuntimeError("Catalog-referenced Pulp repository is unavailable")

    remote_exists, remote_state = _get_rpm_remote_state(repo_name, log)
    if remote_exists is not True:
        raise RuntimeError("Catalog-referenced Pulp remote is unavailable")
    try:
        expected_url = validate_repository_url(repo.get("url"))
        current_url = validate_repository_url(remote_state.get("url"))
        expected_policy = validate_pulp_policy(repo.get("policy"))
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "Exact-mirror repository configuration is invalid"
        ) from error
    if current_url.rstrip("/") != expected_url.rstrip("/"):
        raise RuntimeError("Pulp remote URL does not match Repo Manager input")
    if remote_state.get("policy") != expected_policy:
        raise RuntimeError("Pulp remote policy does not match Repo Manager input")

    publication_href, version_href = _distribution_served_state(repo_name, log)
    if not version_href.startswith(f"{repository_href}versions/"):
        raise RuntimeError("Distribution publication belongs to another repository")
    if _repository_version_number_from_href(version_href) <= 0:
        raise RuntimeError("Pulp distribution does not serve synchronized content")

    metadata_valid, metadata_error = _validate_served_repomd(
        repo_name, pulp_base_url, log
    )
    if not metadata_valid:
        raise RuntimeError(metadata_error)
    return {
        "publication_href": publication_href,
        "version_href": version_href,
    }


def _exact_repository_names(rpm_config):
    """Return unique deterministic repository names or raise safely."""
    repository_names = [
        _configured_repository_name(repo) for repo in rpm_config
    ]
    if not repository_names:
        raise RuntimeError("No catalog-referenced RPM repositories")
    if len(repository_names) != len(set(repository_names)):
        raise RuntimeError("Duplicate catalog repository definitions")
    return repository_names


def preflight_exact_mirror_repositories(rpm_config, pulp_base_url, log):
    """Validate all exact-mirror targets in one context without mutation."""
    repositories = {}
    try:
        repository_names = _exact_repository_names(rpm_config)
    except RuntimeError as error:
        return False, repositories, str(error)
    for index, repo in enumerate(rpm_config):
        repo_name = repository_names[index]
        try:
            target = _validate_exact_mirror_target(repo, pulp_base_url, log)
            repositories[repo_name] = {
                "preflight_status": "success",
                "sync_status": "not_run",
                "cleanup_status": "not_run",
                "version_href": target["version_href"],
            }
        except RuntimeError as error:
            repositories[repo_name] = {
                "preflight_status": "failed",
                "sync_status": "not_run",
                "cleanup_status": "not_run",
                "error": str(error),
            }
            for pending_name in repository_names[index + 1:]:
                repositories[pending_name] = {
                    "preflight_status": "not_run",
                    "sync_status": "not_run",
                    "cleanup_status": "not_run",
                }
            return False, repositories, str(error)
    return True, repositories, "Exact-mirror preflight completed"


def _stored_repository_version_href(mirror_index_path, repo_name, log):
    """Return one validated persisted repository-version HREF when present."""
    mirror_data = load_mirror_index(mirror_index_path, log)
    state = mirror_data.get("MirrorIndex", {}).get(
        "repositories", {}
    ).get(repo_name, {})
    stored_href = state.get("version_href") if isinstance(state, dict) else None
    return (
        validate_repository_version_href(stored_href)
        if stored_href else None
    )


def _persist_exact_repository_checkpoint(
        mirror_index_path, rpm_config, repo_name, status, version_href,
        log, cluster_os_type, cluster_os_version,
        invalidate_packages=False):
    """Persist one exact checkpoint and optional package invalidation atomically."""
    return _persist_repository_checkpoints(
        mirror_index_path,
        rpm_config,
        {repo_name: status},
        log,
        version_href_by_repository=(
            {repo_name: version_href} if version_href is not None else {}
        ),
        clear_version_repositories=(
            {repo_name} if version_href is None else set()
        ),
        invalidate_package_repositories=(
            {repo_name} if invalidate_packages else set()
        ),
        cluster_os_type=cluster_os_type,
        cluster_os_version=cluster_os_version,
    )


def _exact_mirror_repository(
        repo, pulp_base_url, mirror_index_path,
        cluster_os_type, cluster_os_version, rpm_config, log):
    """Reconcile one repository with checkpoint-safe destructive ordering."""
    repo_name = _configured_repository_name(repo)
    status = {
        "sync_status": "failed",
        "old_version": None,
        "new_version": None,
        "packages_added": 0,
        "packages_removed": 0,
        "stale_packages_remaining": None,
        "publication_updated": False,
        "cleanup_status": "not_run",
    }
    stage = "preflight"
    old_publication = None
    old_version_href = None
    committed_version_href = None
    distribution_switched = False
    replacement_validated = False
    try:
        target = _validate_exact_mirror_target(repo, pulp_base_url, log)
        old_publication = target["publication_href"]
        old_version_href = target["version_href"]
        committed_version_href = old_version_href
        old_version = _repository_version_number_from_href(old_version_href)
        status["old_version"] = old_version

        stored_version_href = _stored_repository_version_href(
            mirror_index_path, repo_name, log
        )
        legacy_state_mismatch = (
            stored_version_href is not None
            and stored_version_href != old_version_href
        )
        stage = "initial_checkpoint"
        if not _persist_exact_repository_checkpoint(
                mirror_index_path, rpm_config, repo_name, "pending",
                old_version_href, log, cluster_os_type, cluster_os_version,
                invalidate_packages=legacy_state_mismatch):
            raise RuntimeError("Unable to persist initial exact-mirror checkpoint")

        baseline_latest_version = get_repo_version(repo_name, log)
        if baseline_latest_version is None:
            raise RuntimeError("Unable to read current repository version")

        stage = "synchronization"
        sync_result = sync_rpm_repository_with_monitoring(
            repo,
            log,
            resync_repos="all",
            sync_policy="mirror_content_only",
        )
        if not sync_result[0]:
            raise RuntimeError("Exact-mirror synchronization failed")
        status["sync_status"] = "success"

        new_version_href = get_repository_latest_version_href(repo_name, log)
        if not new_version_href:
            raise RuntimeError("Unable to read synchronized repository version")
        new_version = _repository_version_number_from_href(new_version_href)
        status["new_version"] = new_version
        if new_version == old_version:
            added, removed = 0, 0
        else:
            added, removed = _repository_version_metrics(
                repo_name, new_version, log
            )
        status["packages_added"] = added
        status["packages_removed"] = removed

        stage = "publication"
        publication_created, _ = create_publication(repo, log)
        if not publication_created:
            raise RuntimeError("Replacement publication could not be created")
        new_publication = get_latest_publication_href(
            repo_name, log, new_version_href
        )
        if not new_publication:
            raise RuntimeError("Replacement publication is unavailable")

        stage = "distribution_switch"
        if old_publication != new_publication:
            distribution_switched = True
            switch_ok, _switch_error = _switch_distribution_publication(
                repo_name, new_publication, log
            )
            if not switch_ok:
                raise RuntimeError("Distribution switch failed")
        status["publication_updated"] = distribution_switched

        stage = "replacement_validation"
        metadata_valid, _metadata_error = _validate_served_repomd(
            repo_name, pulp_base_url, log
        )
        if not metadata_valid:
            raise RuntimeError("Replacement publication validation failed")
        served_publication, served_version_href = _distribution_served_state(
            repo_name, log
        )
        if (
                served_publication != new_publication
                or served_version_href != new_version_href):
            raise RuntimeError("Distribution does not serve the replacement")
        replacement_validated = True
        committed_version_href = new_version_href

        repository_content_changed = (
            legacy_state_mismatch
            or new_version_href != old_version_href
            or new_version != baseline_latest_version
            or bool(added)
            or bool(removed)
        )
        stage = "replacement_checkpoint"
        if not _persist_exact_repository_checkpoint(
                mirror_index_path, rpm_config, repo_name, "pending",
                new_version_href, log, cluster_os_type, cluster_os_version,
                invalidate_packages=repository_content_changed):
            raise RuntimeError("Unable to persist replacement checkpoint")
        stage = "pruning"
        _prune_superseded_repository_state(
            repo_name, new_publication, new_version, log
        )

        stage = "final_validation"
        _verify_exact_repository_state(
            repo_name,
            new_publication,
            new_version_href,
            pulp_base_url,
            log,
        )

        stage = "ready_checkpoint"
        if not _persist_exact_repository_checkpoint(
                mirror_index_path, rpm_config, repo_name, "ready",
                new_version_href, log, cluster_os_type, cluster_os_version):
            raise RuntimeError("Unable to persist ready exact-mirror checkpoint")
        status["stale_packages_remaining"] = 0
        status["cleanup_status"] = "success"
        return True, status
    except (RuntimeError, TypeError, ValueError):
        _log(
            log, "error", repo_name,
            f"Exact-mirror reconciliation failed during {stage}",
        )
        if (
                distribution_switched
                and not replacement_validated
                and old_publication):
            rollback_ok, _rollback_error = _switch_distribution_publication(
                repo_name, old_publication, log
            )
            if rollback_ok:
                committed_version_href = old_version_href
            else:
                status["rollback_error"] = "Distribution rollback failed"
        active_version_resolved = False
        try:
            _active_publication, active_version_href = (
                _distribution_served_state(repo_name, log)
            )
            committed_version_href = active_version_href
            active_version_resolved = True
        except RuntimeError:
            pass
        if (
                distribution_switched
                and not replacement_validated
                and status.get("rollback_error")
                and not active_version_resolved):
            committed_version_href = None
        checkpoint_saved = _persist_exact_repository_checkpoint(
            mirror_index_path, rpm_config, repo_name, "failed",
            committed_version_href, log,
            cluster_os_type, cluster_os_version,
        )
        if not checkpoint_saved:
            _log(
                log, "error", repo_name,
                "Unable to persist failed exact-mirror checkpoint",
            )
        status["error"] = (
            f"Exact-mirror reconciliation failed during {stage}"
        )
        return False, status


def _sync_exact_aggregate_source(repo_entry, aggregate_name, log):
    """Exact-sync one URL into its private source repository."""
    source_name = _aggregate_source_repository_name(
        aggregate_name, repo_entry
    )
    repository_created, _ = create_aggregated_repository(source_name, log)
    if not repository_created:
        raise RuntimeError("Aggregate source repository could not be created")
    remote_created, remote_name = create_aggregated_remote(
        repo_entry, aggregate_name, log
    )
    if not remote_created or remote_name != source_name:
        raise RuntimeError("Aggregate source remote could not be reconciled")
    source_config = {
        "package": source_name,
        "name": source_name,
        "url": repo_entry.get("url"),
        "policy": _resolve_aggregated_remote_policy(repo_entry),
    }
    sync_result = sync_rpm_repository_with_monitoring(
        source_config,
        log,
        resync_repos="all",
        sync_policy="mirror_content_only",
    )
    if not sync_result[0]:
        raise RuntimeError("Aggregate source synchronization failed")
    version_href = get_repository_latest_version_href(source_name, log)
    if not version_href:
        raise RuntimeError("Aggregate source version is unavailable")
    return source_name, version_href


def _exact_aggregate_repository(
        arch, repo_entries, pulp_base_url, mirror_index_path,
        cluster_os_type, cluster_os_version, rpm_config, log):
    """Publish the exact union of private URL-backed source repositories."""
    aggregate_name = _aggregate_repository_name(
        arch, cluster_os_type, cluster_os_version
    )
    status = {
        "sync_status": "failed",
        "old_version": None,
        "new_version": None,
        "packages_added": 0,
        "packages_removed": 0,
        "content_added": 0,
        "content_removed": 0,
        "source_count": len(repo_entries),
        "publication_updated": False,
        "cleanup_status": "not_run",
    }
    stage = "preflight"
    old_publication = None
    old_version_href = None
    committed_version_href = None
    distribution_switched = False
    replacement_validated = False
    try:
        old_publication, old_version_href = _validate_exact_aggregate_target(
            aggregate_name, repo_entries, pulp_base_url, log
        )
        committed_version_href = old_version_href
        old_version = _repository_version_number_from_href(old_version_href)
        status["old_version"] = old_version

        stage = "initial_checkpoint"
        if not _persist_exact_repository_checkpoint(
                mirror_index_path, rpm_config, aggregate_name, "pending",
                old_version_href, log, cluster_os_type, cluster_os_version):
            raise RuntimeError("Unable to persist aggregate checkpoint")

        stage = "source_synchronization"
        desired_content = set()
        source_versions = {}
        desired_source_names = set()
        for repo_entry in repo_entries:
            source_name, source_version_href = _sync_exact_aggregate_source(
                repo_entry, aggregate_name, log
            )
            desired_source_names.add(source_name)
            source_versions[source_name] = source_version_href
            desired_content.update(_list_repository_content_hrefs(
                source_name, source_version_href, log
            ))

        stage = "content_reconciliation"
        current_content = _list_repository_content_hrefs(
            aggregate_name, old_version_href, log
        )
        add_hrefs = desired_content - current_content
        remove_hrefs = current_content - desired_content
        status["content_added"] = len(add_hrefs)
        status["content_removed"] = len(remove_hrefs)
        status["packages_added"] = sum(
            "/content/rpm/packages/" in href for href in add_hrefs
        )
        status["packages_removed"] = sum(
            "/content/rpm/packages/" in href for href in remove_hrefs
        )

        if add_hrefs or remove_hrefs:
            _modify_aggregate_content(
                aggregate_name,
                old_version_href,
                add_hrefs,
                remove_hrefs,
                log,
            )
            new_version_href = get_repository_latest_version_href(
                aggregate_name, log
            )
            if not new_version_href or new_version_href == old_version_href:
                raise RuntimeError("Aggregate replacement version is unavailable")
            replacement_content = _list_repository_content_hrefs(
                aggregate_name, new_version_href, log
            )
            if replacement_content != desired_content:
                raise RuntimeError("Aggregate replacement content is incomplete")
        else:
            new_version_href = old_version_href

        new_version = _repository_version_number_from_href(new_version_href)
        status["new_version"] = new_version
        status["sync_status"] = "success"

        stage = "publication"
        publication_created, new_publication = (
            create_aggregated_publication(aggregate_name, log)
        )
        if not publication_created or not new_publication:
            raise RuntimeError("Aggregate replacement publication failed")

        stage = "distribution_switch"
        if old_publication != new_publication:
            distribution_switched = True
            switch_ok, _switch_error = _switch_distribution_publication(
                aggregate_name, new_publication, log
            )
            if not switch_ok:
                raise RuntimeError("Aggregate distribution switch failed")
        status["publication_updated"] = distribution_switched

        stage = "replacement_validation"
        metadata_valid, _metadata_error = _validate_served_repomd(
            aggregate_name, pulp_base_url, log
        )
        if not metadata_valid:
            raise RuntimeError("Aggregate replacement metadata is invalid")
        served_publication, served_version_href = _distribution_served_state(
            aggregate_name, log
        )
        if (
                served_publication != new_publication
                or served_version_href != new_version_href):
            raise RuntimeError("Aggregate distribution serves another version")
        replacement_validated = True
        committed_version_href = new_version_href

        stage = "replacement_checkpoint"
        if not _persist_exact_repository_checkpoint(
                mirror_index_path, rpm_config, aggregate_name, "pending",
                new_version_href, log, cluster_os_type, cluster_os_version,
                invalidate_packages=new_version_href != old_version_href):
            raise RuntimeError("Unable to persist aggregate replacement state")

        stage = "pruning"
        _prune_superseded_repository_state(
            aggregate_name, new_publication, new_version, log
        )
        for source_name, source_version_href in source_versions.items():
            _prune_private_source_versions(
                source_name, source_version_href, log
            )
        _cleanup_stale_aggregate_sources(
            aggregate_name, desired_source_names, log
        )

        stage = "final_validation"
        _verify_exact_repository_state(
            aggregate_name,
            new_publication,
            new_version_href,
            pulp_base_url,
            log,
        )

        stage = "ready_checkpoint"
        if not _persist_exact_repository_checkpoint(
                mirror_index_path, rpm_config, aggregate_name, "ready",
                new_version_href, log, cluster_os_type, cluster_os_version):
            raise RuntimeError("Unable to persist ready aggregate checkpoint")
        status["stale_packages_remaining"] = 0
        status["cleanup_status"] = "success"
        return True, status
    except (OSError, RuntimeError, TypeError, ValueError):
        _log(
            log,
            "error",
            aggregate_name,
            f"Exact aggregate reconciliation failed during {stage}",
        )
        if (
                distribution_switched
                and not replacement_validated
                and old_publication):
            rollback_ok, _rollback_error = _switch_distribution_publication(
                aggregate_name, old_publication, log
            )
            if rollback_ok:
                committed_version_href = old_version_href
            else:
                status["rollback_error"] = "Distribution rollback failed"
        try:
            _active_publication, active_version_href = (
                _distribution_served_state(aggregate_name, log)
            )
            committed_version_href = active_version_href
        except RuntimeError:
            pass
        checkpoint_saved = _persist_exact_repository_checkpoint(
            mirror_index_path,
            rpm_config,
            aggregate_name,
            "failed",
            committed_version_href,
            log,
            cluster_os_type,
            cluster_os_version,
        )
        if not checkpoint_saved:
            _log(
                log,
                "error",
                aggregate_name,
                "Unable to persist failed aggregate checkpoint",
            )
        status["error"] = (
            f"Exact aggregate reconciliation failed during {stage}"
        )
        return False, status


def manage_exact_additional_repositories(
        additional_repos_config, selected_architectures, log, pulp_base_url,
        mirror_index_path, cluster_os_type, cluster_os_version, rpm_config,
        run_orphan_cleanup=False):
    """Reconcile public additional aggregates in deterministic order."""
    repositories = {}
    active_architectures = _selected_additional_architectures(
        additional_repos_config, selected_architectures
    )
    for index, arch in enumerate(active_architectures):
        repo_entries = (additional_repos_config or {}).get(arch) or []
        if not repo_entries:
            continue
        aggregate_name = _aggregate_repository_name(
            arch, cluster_os_type, cluster_os_version
        )
        success, repository_status = _exact_aggregate_repository(
            arch,
            repo_entries,
            pulp_base_url,
            mirror_index_path,
            cluster_os_type,
            cluster_os_version,
            rpm_config,
            log,
        )
        repositories[aggregate_name] = repository_status
        if not success:
            for pending_arch in active_architectures[index + 1:]:
                pending_entries = (
                    additional_repos_config or {}
                ).get(pending_arch) or []
                if pending_entries:
                    pending_name = _aggregate_repository_name(
                        pending_arch, cluster_os_type, cluster_os_version
                    )
                    repositories[pending_name] = {
                        "sync_status": "not_run",
                        "cleanup_status": "not_run",
                    }
            return (
                False,
                repositories,
                repository_status.get(
                    "error", "Exact aggregate reconciliation failed"
                ),
                "not_run",
            )

    if run_orphan_cleanup:
        success, _, _error_message = _execute_pulp_task(
            pulp_rpm_commands["orphan_cleanup"],
            log,
            "pulp_orphans",
            require_task=False,
        )
        if not success:
            return False, repositories, "Pulp orphan cleanup failed", "failed"
        return (
            True,
            repositories,
            "Exact aggregate reconciliation completed",
            "success",
        )
    return (
        True,
        repositories,
        "Exact aggregate reconciliation completed",
        "not_run",
    )


def manage_exact_mirror_repositories(
        rpm_config, log, pulp_base_url, mirror_index_path,
        cluster_os_type, cluster_os_version, run_orphan_cleanup=False):
    """Reconcile supplied repositories in deterministic order."""
    repositories = {}
    try:
        repository_names = _exact_repository_names(rpm_config)
    except RuntimeError as error:
        return False, repositories, str(error), "not_run"

    for index, repo in enumerate(rpm_config):
        repo_name = repository_names[index]
        success, repository_status = _exact_mirror_repository(
            repo,
            pulp_base_url,
            mirror_index_path,
            cluster_os_type,
            cluster_os_version,
            rpm_config,
            log,
        )
        repositories[repo_name] = repository_status
        if not success:
            for pending_name in repository_names[index + 1:]:
                repositories[pending_name] = {
                    "sync_status": "not_run",
                    "cleanup_status": "not_run",
                }
            return (
                False,
                repositories,
                repository_status.get(
                    "error", "Exact-mirror reconciliation failed"
                ),
                "not_run",
            )

    if run_orphan_cleanup:
        success, _, _error_message = _execute_pulp_task(
            pulp_rpm_commands["orphan_cleanup"],
            log,
            "pulp_orphans",
            require_task=False,
        )
        if not success:
            return (
                False,
                repositories,
                "Pulp orphan cleanup failed",
                "failed",
            )
        return (
            True,
            repositories,
            "Exact-mirror reconciliation completed",
            "success",
        )
    return (
        True,
        repositories,
        "Exact-mirror reconciliation completed",
        "not_run",
    )


def manage_rpm_repositories_multiprocess(
        rpm_config, log, cluster_os_type, cluster_os_version, sw_archs=None,
        resync_repos=None,
        continue_on_failure=True,
        thread_pool_size=RPM_THREAD_POOL_SIZE,
        pulp_base_url=None,
        repo_file_path=None,
        mirror_index_path=None,
        write_repo_file=True):
    """
    Manage RPM repositories using multiprocessing.

    Args:
        rpm_config (list): A list of dictionaries containing the configuration for each RPM repository.
        log (logging.Logger): Logger instance for logging the process and errors.
        cluster_os_type (str): The cluster OS type (for example, 'rhel').
        cluster_os_version (str): The cluster OS version (for example, '10.0').
        sw_archs (list, optional): List of architectures to process from catalog configuration.
                                   If provided, only repos matching these archs are processed.
        resync_repos (str/list, optional): Controls sync behavior:
            - None/empty: Skip already synced repos (default)
            - "all": Force resync all repos
            - list of repo names: Only sync specified repos
        thread_pool_size (int): Maximum worker processes used by every RPM stage.
        pulp_base_url (str): Trusted public Pulp HTTPS origin.
        repo_file_path (str): Destination path for the generated DNF file.
        mirror_index_path (str): Per-version mirror state used for sync recovery.
        write_repo_file (bool): Write the DNF file after regular repositories.
            Aggregate callers defer this until all additional sources succeed.
    Returns:
        tuple: (bool, str) indicating success and a message
    """
    # Accumulate all failures across stages with stage prefixes
    all_failures = []
    total_start_time = time.time()

    # Filter rpm_config by sw_archs if provided
    if sw_archs:
        log.info(f"Filtering repositories for architectures: {sw_archs}")
        rpm_config = [repo for repo in rpm_config if repo.get("sw_arch") in sw_archs]
        log.info(f"Filtered to {len(rpm_config)} repositories")

    if not rpm_config:
        log.info("No repositories to process after filtering")
        return True, "No repositories to process"

    configured_repository_names = {
        _configured_repository_name(repo) for repo in rpm_config
    }
    try:
        retry_repositories = _load_repository_retry_state(
            mirror_index_path, log
        ) & configured_repository_names
    except (OSError, ValueError):
        return False, "RPM repository recovery state is unavailable"
    if retry_repositories:
        log.info(
            "Retrying %d repository synchronization checkpoint(s): %s",
            len(retry_repositories), sorted(retry_repositories),
        )

    # The sequential catalog dispatcher uses an empty list when a targeted
    # resync belongs to another OS-version context. Do not reinterpret that as
    # the default "sync every stale repository" behavior.
    if (
            isinstance(resync_repos, list)
            and not resync_repos
            and not retry_repositories):
        log.info("No targeted repositories belong to this execution context")
        repositories_ready, readiness_failures = (
            validate_repository_readiness(rpm_config, log)
        )
        if not repositories_ready:
            return False, (
                "Repositories required by this context are incomplete: "
                + ", ".join(readiness_failures)
            )
        if write_repo_file:
            base_urls = get_base_urls(log, pulp_base_url)
            if not base_urls:
                return False, "Base URLs fetch failed — repo file not created."
            if not create_yum_repo_file(
                    base_urls, log,
                    repo_priorities=build_complete_repo_priority_map(
                        rpm_config,
                        repo_file_path,
                        cluster_os_type,
                        cluster_os_version,
                        sw_archs,
                        log,
                    ),
                    pulp_base_url=pulp_base_url,
                    repo_file_path=repo_file_path):
                return False, (
                    "Failed to atomically create the DNF repository file"
                )
        return True, "No targeted repositories for this execution context"

    # Validate resync_repos contains valid repository names
    is_valid, error_msg = validate_resync_repos(resync_repos, rpm_config, log)
    if not is_valid:
        return False, error_msg

    requested_repositories = _requested_repository_names(
        resync_repos, rpm_config
    )
    requested_or_recovery_repositories = (
        requested_repositories | retry_repositories
    )
    if not _persist_repository_checkpoints(
            mirror_index_path,
            rpm_config,
            {
                name: "pending"
                for name in requested_or_recovery_repositories
            },
            log):
        return False, "Failed to persist repository synchronization checkpoint"

    process = _effective_worker_count(thread_pool_size, len(rpm_config))
    log.info(f"Configured RPM worker processes = {thread_pool_size}")
    log.info(f"Effective processes for lightweight operations = {process}")

    # Calculate actual repos to process based on resync_repos
    # This determines the effective concurrency for sync/publish/distribute
    if resync_repos is None or resync_repos == "" or resync_repos == "all":
        repos_to_process_count = len(rpm_config)
    else:
        # Count repos that match resync_repos
        if isinstance(resync_repos, str):
            resync_list = [r.strip() for r in resync_repos.split(",")]
        else:
            resync_list = resync_repos
        repos_to_process_count = len(
            set(resync_list) | retry_repositories
        )

    log.info(f"Repos to actually process (based on resync_repos): {repos_to_process_count}")

    # One stability-oriented limit controls every stage. Cap resource-intensive
    # work by the number of repositories that can actually be processed.
    pulp_process = _effective_worker_count(thread_pool_size, repos_to_process_count)

    log.info(f"Actual pulp processes (capped by repo to process): {pulp_process}")
    log.info(f"Continue on failure: {continue_on_failure}")

    # Step 1: Concurrent repository creation
    log.info("Step 1: Starting concurrent RPM repository creation")
    with multiprocessing.Pool(processes=process) as pool:
        result = pool.map(partial(create_rpm_repository, log=log), rpm_config)

    # Step 1.5: Validate repository creation
    log.info("Step 1.5: Validating repository creation")
    failed_repos = [name for success, name in result if not success]
    if failed_repos:
        log.error(f"Failed to create {len(failed_repos)} repositories: {', '.join(failed_repos)}")
        all_failures.extend([f"create:{name}" for name in failed_repos])
        if not continue_on_failure:
            return False, f"Failed to create repositories: {', '.join(failed_repos)}"
        log.warning("Continuing despite repository creation failures (continue_on_failure=True)")
    else:
        log.info("All repositories created successfully")

    # Step 2: Concurrent remote creation
    log.info("Step 2: Starting concurrent RPM remote creation")
    with multiprocessing.Pool(processes=process) as pool:
        sync_result = pool.map(partial(create_rpm_remote, log=log), rpm_config)
    failed = [name for success, name, _ in sync_result if not success]
    if failed:
        log.error("Failed during creation of RPM remote for: %s", ", ".join(failed))
        return False, f"During creation of RPM remote for: {', '.join(failed)}"
    changed_remotes = {
        name for success, name, changed in sync_result
        if success and changed
    }

    forced_repositories = (
        changed_remotes | requested_or_recovery_repositories
    )
    if not _persist_repository_checkpoints(
            mirror_index_path,
            rpm_config,
            {name: "pending" for name in forced_repositories},
            log):
        return False, "Failed to persist repository synchronization checkpoint"

    # Step 3: Concurrent synchronization
    log.info("Step 3: Starting concurrent RPM repository synchronization")
    with multiprocessing.Pool(processes=pulp_process) as pool:
        sync_results = pool.map(partial(
            sync_rpm_repository_with_monitoring,
            log=log,
            resync_repos=resync_repos,
            force_sync_repos=forced_repositories,
        ), rpm_config)

    synchronization_checkpoints = {
        name: "pending"
        for success, name, actually_synced, _version_changed in sync_results
        if success and actually_synced
    }
    synchronization_checkpoints.update({
        name: "failed"
        for success, name, _actually_synced, _version_changed in sync_results
        if not success
    })
    if not _persist_repository_checkpoints(
            mirror_index_path,
            rpm_config,
            synchronization_checkpoints,
            log):
        return False, "Failed to persist repository synchronization result"

    sync_failed = [name for success, name, _, _ in sync_results if not success]
    if sync_failed:
        log.error("Failed during synchronization of RPM repository for: %s", ", ".join(sync_failed))
        all_failures.extend([f"sync:{name}" for name in sync_failed])
        if not continue_on_failure:
            return False, f"During synchronization of RPM repository for: {', '.join(sync_failed)}. Please refer to the troubleshooting guide for more information."
        log.warning("Continuing with remaining repositories (continue_on_failure=True)")
        # process_sync_results ignores failed sync results while still repairing
        # successful skipped repositories with incomplete publication state.

    # Process sync results and get repos for publication/distribution
    repos_for_pub_dist, should_skip, skip_message = process_sync_results(
        sync_results, rpm_config, resync_repos, log
    )

    # Only run publication/distribution if repos need it
    if not should_skip:
        # Step 4: Concurrent publication creation
        # Creates a replacement before the distribution target is changed, so
        # an older publication remains usable if this stage fails.
        log.info("Step 4: Starting concurrent RPM publication creation")
        log.info(f"Processing publication for {len(repos_for_pub_dist)} repos")
        publication_processes = _effective_worker_count(
            thread_pool_size, len(repos_for_pub_dist)
        )
        with multiprocessing.Pool(processes=publication_processes) as pool:
            result = pool.map(partial(create_publication, log=log), repos_for_pub_dist)

        pub_failed = [name for success, name in result if not success]
        if pub_failed:
            log.error("Failed during publication of RPM repository for: %s", ", ".join(pub_failed))
            all_failures.extend([f"publish:{name}" for name in pub_failed])
            if not continue_on_failure:
                return False, f"During publication of RPM repository for: {', '.join(pub_failed)}. Please refer to the troubleshooting guide for more information."
            log.warning("Continuing with remaining repositories (continue_on_failure=True)")
            # Remove failed repos from distribution processing
            repos_for_pub_dist = [
                repo for repo in repos_for_pub_dist
                if _configured_repository_name(repo) not in pub_failed
            ]
            log.info(f"Removed {len(pub_failed)} failed repos from distribution processing")

        # Step 5: Concurrent distribution creation/update
        log.info("Step 5: Starting concurrent RPM distribution creation/update")
        log.info(f"Processing distribution for {len(repos_for_pub_dist)} repos")
        distribution_processes = _effective_worker_count(
            thread_pool_size, len(repos_for_pub_dist)
        )
        with multiprocessing.Pool(processes=distribution_processes) as pool:
            result = pool.map(partial(
                create_distribution,
                log=log,
                cluster_os_type=cluster_os_type,
                cluster_os_version=cluster_os_version,
            ), repos_for_pub_dist)

        dist_failed = [name for success, name in result if not success]
        if dist_failed:
            log.error("Failed during distribution of RPM repository for: %s", ", ".join(dist_failed))
            all_failures.extend([f"dist:{name}" for name in dist_failed])
            if not continue_on_failure:
                return False, f"During distribution of RPM repository for: {', '.join(dist_failed)}"
            log.warning("Continuing despite distribution failures (continue_on_failure=True)")
    else:
        log.info(
            "Skipping publication/distribution steps: %s",
            skip_message,
        )

    # Artifact download commands must not run against incomplete Pulp state.
    # Check all repositories in the active context, including repositories not
    # selected for a targeted resync, because the following artifact phase can
    # consume any of them.
    repositories_ready, readiness_failures = validate_repository_readiness(
        rpm_config, log
    )
    if not repositories_ready:
        all_failures.extend([
            f"readiness:{failure}" for failure in readiness_failures
        ])

    # Keep the last-known-good pulp.repo untouched when this preparation run
    # failed. Publishing a successful subset would make DNF behavior depend on
    # which worker happened to finish before the failure.
    if all_failures:
        _log_summary(log, sync_results, all_failures, total_start_time)
        failure_summary = ", ".join(all_failures)
        return False, f"Repository preparation failed: {failure_summary}"

    # --- STEP 6: Always ensure pulp.repo exists ---
    # This handles the scenario where omnia_core upgrade deletes pulp.repo
    # and local_repo.yml runs again with already-synced repos.
    # Distributions must exist before we can fetch base_urls.
    if write_repo_file:
        log.info("Step 6: Ensuring pulp.repo file exists")
        base_urls = get_base_urls(log, pulp_base_url)
        if not base_urls:
            log.error("No base URLs retrieved from Pulp. Cannot create repo file.")
            return False, "Base URLs fetch failed — repo file not created."

        log.info(f"Fetched {len(base_urls)} base URLs from Pulp.")
        repo_file_created = create_yum_repo_file(
            base_urls, log,
            repo_priorities=build_complete_repo_priority_map(
                rpm_config,
                repo_file_path,
                cluster_os_type,
                cluster_os_version,
                sw_archs,
                log,
            ),
            pulp_base_url=pulp_base_url,
            repo_file_path=repo_file_path,
        )
        if not repo_file_created:
            return False, "Failed to atomically create the DNF repository file"
        log.info(
            "Successfully created/updated pulp.repo file with fetched base URLs."
        )

    if not _persist_repository_checkpoints(
            mirror_index_path,
            rpm_config,
            {name: "ready" for name in configured_repository_names},
            log):
        return False, "Failed to persist ready repository state"

    # Final summary
    _log_summary(log, sync_results, all_failures, total_start_time)

    return True, "All repositories processed successfully"


def write_complete_repo_file(
        rpm_config, aggregate_priorities, active_additional_architectures,
        cluster_os_type, cluster_os_version, pulp_base_url, repo_file_path,
        log):
    """Atomically publish DNF configuration after aggregate success."""
    distributions = get_base_urls(log, pulp_base_url)
    if not distributions:
        return False, "Base URLs fetch failed — repo file not created."

    legacy_names = {
        build_repo_name(
            arch, cluster_os_type, cluster_os_version,
            "repo_manager-additional",
        )
        for arch in active_additional_architectures
    }
    distributions = [
        distribution for distribution in distributions
        if distribution.get("name") not in legacy_names
    ]
    priorities = build_complete_repo_priority_map(
        rpm_config,
        repo_file_path,
        cluster_os_type,
        cluster_os_version,
        active_additional_architectures,
        log,
        extra_priorities=aggregate_priorities,
    )
    if not create_yum_repo_file(
            distributions, log, repo_priorities=priorities,
            pulp_base_url=pulp_base_url, repo_file_path=repo_file_path):
        return False, "Failed to atomically create the DNF repository file"
    return True, "DNF repository file includes additional repositories"


def main():
    """
    The main function of the module.

    This function sets up the argument specifications for the module and initializes the logger.
    It then retrieves the `local_config` and `log_dir` parameters from the module.

    The `local_config` parameter is used to replace single quotes with double quotes to make it valid JSON.
    The JSON string is then parsed and stored in the `rpm_config` variable.

    The `manage_rpm_repositories_multiprocess` function is called with the `rpm_config` and `log` as arguments.

    If `additional_repos_config` is provided, the `manage_aggregated_repos` function is called to handle
    the aggregated repositories feature.

    Finally, the function exits with a JSON response indicating that the RPM configuration has been processed.

    Parameters:
        None

    Returns:
        None
    """
    module_args = {
        "local_config": {"type": "list", "required": True, "no_log": True},
        "log_dir": {
            "type": "str", "required": False,
            "default": os.path.join(REPO_MANAGER_LOG_DIR, "thread_logs")
        },
        "additional_repos_config": {
            "type": "dict", "required": False, "default": None,
            "no_log": True,
        },
        "user_repos_config": {
            "type": "dict", "required": False, "default": None,
            "no_log": True,
        },
        "thread_pool_size": {"type": "int", "required": False, "default": None},
        "pulp_concurrency": {"type": "int", "required": False, "default": None},
        "sw_archs": {"type": "list", "required": False, "default": None},
        "resync_repos": {"type": "raw", "required": False, "default": None},
        "exact_mirror": {
            "type": "bool", "required": False, "default": False,
        },
        "exact_mirror_preflight": {
            "type": "bool", "required": False, "default": False,
        },
        "run_orphan_cleanup": {
            "type": "bool", "required": False, "default": False,
        },
        "cluster_os_type": {"type": "str", "required": True},
        "cluster_os_version": {"type": "str", "required": True},
        "pulp_base_url": {"type": "str", "required": True},
        "repo_file_path": {"type": "path", "required": True},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    # Get the local_config parameter from the module
    rpm_config = module.params["local_config"]
    log_dir = module.params["log_dir"]
    additional_repos_config = module.params["additional_repos_config"]
    user_repos_config = module.params["user_repos_config"]
    thread_pool_size = module.params["thread_pool_size"]
    pulp_concurrency = module.params["pulp_concurrency"]
    sw_archs = module.params["sw_archs"]
    resync_repos = module.params["resync_repos"]
    exact_mirror = module.params["exact_mirror"]
    exact_mirror_preflight = module.params["exact_mirror_preflight"]
    run_orphan_cleanup = module.params["run_orphan_cleanup"]
    cluster_os_type = module.params["cluster_os_type"]
    cluster_os_version = module.params["cluster_os_version"]
    pulp_base_url = module.params["pulp_base_url"]
    repo_file_path = module.params["repo_file_path"]

    log = setup_standard_logger(log_dir)
    standard_log_path = os.path.join(log_dir, "standard.log")
    mirror_index_path = os.path.join(
        log_dir, MIRROR_STATUS_DIR, MIRROR_INDEX_FILENAME
    )

    if exact_mirror_preflight and not exact_mirror:
        module.fail_json(
            msg="exact_mirror_preflight is valid only with exact_mirror"
        )
    if run_orphan_cleanup and not exact_mirror:
        module.fail_json(
            msg="run_orphan_cleanup is valid only with exact_mirror"
        )
    if exact_mirror_preflight and run_orphan_cleanup:
        module.fail_json(
            msg="Orphan cleanup cannot run during exact-mirror preflight"
        )

    # Convert user_repos_config to rpm_config format and merge
    if user_repos_config:
        log.info("Processing user_repos_config")
        for arch, repos in user_repos_config.items():
            for repo in repos:
                # Get policy and caching settings
                policy_str = repo.get("policy", "partial")
                caching = repo.get("caching", True)

                # Resolve policy using POLICY_CACHING_MAP
                resolved_policy = POLICY_CACHING_MAP.get((policy_str, caching), "on_demand")

                # Use normalized name if already present, otherwise normalize
                repo_name = repo["name"]
                original_name = repo.get("original_name", repo_name)

                # Check if already normalized (has expected prefix)
                expected_prefix = f"{arch}_{cluster_os_type}_{cluster_os_version}_"
                if repo_name.startswith(expected_prefix):
                    normalized_name = repo_name  # Already normalized
                else:
                    normalized_name = normalize_repo_name(repo_name, arch, cluster_os_type, cluster_os_version)

                # Convert user repo to rpm_config format
                user_repo_entry = {
                    "package": normalized_name,  # Use normalized name for compatibility with create_rpm_remote
                    "name": normalized_name,     # Use normalized name for other uses
                    "original_name": original_name,  # Keep original for reference
                    "url": repo["url"],
                    "gpgkey": repo.get("gpgkey", ""),
                    "policy": resolved_policy,  # Use resolved Pulp policy
                    "caching": caching,
                    "sslcacert": repo.get("sslcacert", ""),
                    "sslclientkey": repo.get("sslclientkey", ""),
                    "sslclientcert": repo.get("sslclientcert", ""),
                    "sw_arch": arch,
                    "os_type": cluster_os_type,
                    "os_version": cluster_os_version,
                    "version": "null",  # Set to "null" string to prevent _None suffix
                    "priority": repo.get("priority", 100)
                }
                rpm_config.append(user_repo_entry)
                log.info(f"Added user repo: {original_name} -> {normalized_name} for arch {arch} with policy: {resolved_policy}")

    try:
        active_additional_architectures, aggregate_priorities = (
            validate_additional_repo_contract(
                additional_repos_config,
                sw_archs,
                rpm_config,
                cluster_os_type,
                cluster_os_version,
            )
        )
    except (KeyError, TypeError, ValueError) as error:
        module.fail_json(
            changed=False,
            msg=f"Invalid additional_repos configuration: {error}",
        )

    if exact_mirror:
        if exact_mirror_preflight:
            regular_success, regular_repositories, regular_message = (
                preflight_exact_mirror_repositories(
                    rpm_config, pulp_base_url, log
                )
            )
            additional_success, additional_repositories, additional_message = (
                preflight_exact_additional_repositories(
                    additional_repos_config,
                    active_additional_architectures,
                    pulp_base_url,
                    log,
                    cluster_os_type,
                    cluster_os_version,
                )
            )
            repositories = dict(regular_repositories)
            repositories.update(additional_repositories)
            success = regular_success and additional_success
            message = (
                regular_message if not regular_success
                else additional_message if not additional_success
                else "Exact-mirror preflight completed"
            )
            preflight_result = {
                "repositories": repositories,
                "overall_status": "success" if success else "failed",
                "orphan_cleanup": "not_run",
            }
            if not success:
                preflight_result["error"] = message
                module.fail_json(
                    msg=message,
                    changed=False,
                    result=preflight_result,
                    repositories=repositories,
                )
            module.exit_json(changed=False, result=preflight_result)

        (
            regular_success,
            regular_repositories,
            regular_message,
            orphan_cleanup_status,
        ) = (
            manage_exact_mirror_repositories(
                rpm_config,
                log,
                pulp_base_url,
                mirror_index_path,
                cluster_os_type,
                cluster_os_version,
                run_orphan_cleanup=(
                    run_orphan_cleanup
                    and not active_additional_architectures
                ),
            )
        )
        repositories = dict(regular_repositories)
        success = regular_success
        message = regular_message
        if regular_success and active_additional_architectures:
            (
                additional_success,
                additional_repositories,
                additional_message,
                orphan_cleanup_status,
            ) = manage_exact_additional_repositories(
                additional_repos_config,
                active_additional_architectures,
                log,
                pulp_base_url,
                mirror_index_path,
                cluster_os_type,
                cluster_os_version,
                rpm_config,
                run_orphan_cleanup=run_orphan_cleanup,
            )
            repositories.update(additional_repositories)
            success = additional_success
            message = additional_message
        elif not regular_success:
            for arch in active_additional_architectures:
                aggregate_name = _aggregate_repository_name(
                    arch, cluster_os_type, cluster_os_version
                )
                repositories[aggregate_name] = {
                    "sync_status": "not_run",
                    "cleanup_status": "not_run",
                }
        exact_result = {
            "repositories": repositories,
            "overall_status": "success" if success else "failed",
            "orphan_cleanup": orphan_cleanup_status,
        }
        if not success:
            exact_result["error"] = message
            module.fail_json(
                msg=message,
                changed=True,
                result=exact_result,
                repositories=repositories,
            )
        module.exit_json(changed=True, result=exact_result)

    # ``pulp_concurrency`` remains a compatibility alias for direct callers.
    # The role passes ``thread_pool_size`` and therefore always takes priority.
    configured_thread_pool_size = thread_pool_size
    if configured_thread_pool_size is None and pulp_concurrency is not None:
        configured_thread_pool_size = pulp_concurrency
        log.warning(
            "pulp_concurrency is deprecated; use rpm_repo_config.thread_pool_size"
        )
    if configured_thread_pool_size is None:
        configured_thread_pool_size = RPM_THREAD_POOL_SIZE

    if not MIN_THREAD_POOL_SIZE <= configured_thread_pool_size <= MAX_THREAD_POOL_SIZE:
        module.fail_json(
            msg=(
                "thread_pool_size must be between "
                f"{MIN_THREAD_POOL_SIZE} and {MAX_THREAD_POOL_SIZE}"
            )
        )

    log.info(f"Configured RPM thread pool size: {configured_thread_pool_size}")

    start_time = datetime.now().strftime("%I:%M:%S %p")

    log.info(f"Start execution time: {start_time}")

    log.info(f"Architectures to process: {sw_archs}")
    log.info(f"Resync repos setting: {resync_repos}")
    # Call the function to manage RPM repositories
    result, output = manage_rpm_repositories_multiprocess(
        rpm_config, log, cluster_os_type, cluster_os_version, sw_archs,
        resync_repos,
        continue_on_failure=RPM_CONTINUE_ON_FAILURE,
        thread_pool_size=configured_thread_pool_size,
        pulp_base_url=pulp_base_url,
        repo_file_path=repo_file_path,
        mirror_index_path=mirror_index_path,
        write_repo_file=not bool(active_additional_architectures),
    )

    if result is False:
        module.fail_json(msg=f"Error {output}, check {standard_log_path}")

    # Handle only non-empty aggregate definitions. Missing or empty
    # additional_repos remains a complete no-op.
    if active_additional_architectures:
        log.info("Processing additional_repos aggregated repositories")
        result, output = manage_aggregated_repos(
            additional_repos_config, log, cluster_os_type,
            cluster_os_version, active_additional_architectures
        )
        if result is False:
            module.fail_json(msg=f"Error in aggregated repos: {output}, check {standard_log_path}")
        log.info("Successfully processed additional_repos aggregated repositories")

        result, output = write_complete_repo_file(
            rpm_config,
            aggregate_priorities,
            active_additional_architectures,
            cluster_os_type,
            cluster_os_version,
            pulp_base_url,
            repo_file_path,
            log,
        )
        if result is False:
            module.fail_json(
                msg=f"Error {output}, check {standard_log_path}"
            )

    module.exit_json(changed=True, result=output)


if __name__ == "__main__":
    main()
