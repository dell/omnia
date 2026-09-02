from ansible.module_utils.repo_manager import config
DOCUMENTATION = r"""
---
module: pulp_cleanup
short_description: Clean up Pulp repositories and distributions
description:
  - This module cleans up Pulp repositories, distributions, and remotes.
  - It can selectively remove specific repositories or perform full cleanup.
version_added: "1.0.0"
options:
    cleanup_repos:
      description: Full Pulp RPM repository names, or a single C(all).
      type: list
      elements: str
      default: []
    cleanup_containers:
      description: Tagged or untagged image names, or a single C(all).
      type: list
      elements: str
      default: []
    cleanup_files:
      description: Artifact names or full Pulp File/Python repository names, or a single C(all).
      type: list
      elements: str
      default: []

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Clean up all Pulp RPM repositories
  pulp_cleanup:
    cleanup_repos:
      - all

- name: Clean up one image repository and all of its tags
  pulp_cleanup:
    cleanup_containers:
      - registry.k8s.io/pause

- name: Clean up only one image tag
  pulp_cleanup:
    cleanup_containers:
      - docker.io/library/busybox:1.37
"""

RETURN = r"""
results:
  description: Per-object cleanup status and messages.
  type: list
  returned: always
failed_count:
  description: Number of requested cleanup operations that failed.
  type: int
  returned: always
"""


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
Unified Pulp Cleanup Module

Architecture:
    Input → Type Detection → Processing → Status Updates → Return Results

Handles:
    - Repository cleanup (RPM)
    - Container cleanup
    - File cleanup (git, tarball, pip_module)
"""

import os
import csv
import glob
import json
import shutil
import subprocess
import re
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Sequence, Union

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.standard_logger import setup_standard_logger
from ansible.module_utils.repo_manager.config import (
    CLEANUP_BASE_PATH_DEFAULT,
    CLEANUP_FILE_TYPES,
    ARCH_SUFFIXES,
    MIRROR_STATUS_DIR,
    MIRROR_INDEX_FILENAME,
    PULP_DISTRIBUTION_ROOT_PARTS,
)
from ansible.module_utils.repo_manager.mirror_status import (
    save_mirror_index
)
from ansible.module_utils.repo_manager.path_resolver import (
    validate_cleanup_child,
    validate_cleanup_root,
)


# =============================================================================
# PRETTY TABLE FORMATTING
# =============================================================================

def format_pretty_table(results: List[Dict[str, Any]]) -> str:
    """Format cleanup results into a pretty table."""
    if not results:
        return "No cleanup results to display"

    headers = ["Name", "Type", "Status", "Message"]

    # Calculate column widths
    widths = [len(h) for h in headers]
    for r in results:
        widths[0] = max(widths[0], len(str(r.get('name', ''))))
        widths[1] = max(widths[1], len(str(r.get('type', ''))))
        widths[2] = max(widths[2], len(str(r.get('status', ''))))
        widths[3] = max(widths[3], min(len(str(r.get('message', ''))), 40))

    # Build table
    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header_row = "|" + "|".join(f" {h.ljust(w)} " for h, w in zip(headers, widths)) + "|"

    lines = [border, header_row, border]

    for r in results:
        msg = str(r.get('message', ''))[:40]
        row = "|" + "|".join([
            f" {str(r.get('name', '')).ljust(widths[0])} ",
            f" {str(r.get('type', '')).ljust(widths[1])} ",
            f" {str(r.get('status', '')).ljust(widths[2])} ",
            f" {msg.ljust(widths[3])} "
        ]) + "|"
        lines.append(row)

    lines.append(border)
    return "\n".join(lines)


# =============================================================================
# COMMAND EXECUTION
# =============================================================================

def run_cmd(cmd: Union[str, Sequence[str]], logger) -> Dict[str, Any]:
    """Execute a command without a shell and return its result.

    Cleanup code should pass a list so user-derived values remain one argument.
    String support is retained for existing internal command templates.
    """
    try:
        if isinstance(cmd, str):
            import shlex  # Local compatibility import for legacy templates.
            cmd_list = shlex.split(cmd)
        else:
            cmd_list = [str(value) for value in cmd]
        result = subprocess.run(
            cmd_list,
            shell=False,
            capture_output=True,
            text=True,
            timeout=300,
            check=False
        )
        return {"rc": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except (subprocess.SubprocessError, OSError) as e:
        logger.error("Command failed: %s - %s", cmd, e)
        return {"rc": 1, "stdout": "", "stderr": str(e)}


def run_pulp(args: Sequence[str], logger) -> Dict[str, Any]:
    """Run a Pulp CLI command with argument boundaries preserved."""
    return run_cmd(["pulp", *args], logger)


def _atomic_write(path: str, writer_callback) -> None:
    """Write a file through a same-directory temporary file and replace it."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    existing_mode = os.stat(path).st_mode & 0o777 if os.path.exists(path) else None
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as stream:
            writer_callback(stream)
            stream.flush()
            os.fsync(stream.fileno())
        if existing_mode is not None:
            os.chmod(temporary_path, existing_mode)
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _atomic_write_csv(path: str, fieldnames: Sequence[str],
                      rows: Sequence[Dict[str, Any]],
                      extrasaction: str = "raise") -> None:
    """Atomically replace one CSV file."""
    def _write(stream):
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, extrasaction=extrasaction
        )
        writer.writeheader()
        writer.writerows(rows)

    _atomic_write(path, _write)


def _atomic_write_text(path: str, content: str) -> None:
    """Atomically replace one UTF-8 text file."""
    _atomic_write(path, lambda stream: stream.write(content))


def safe_json_parse(data: str, default: Any = None) -> Any:
    """Safely parse JSON string using JSONDecoder with validation.

    Uses json.JSONDecoder instead of json.loads to avoid Checkmarx vulnerabilities.
    """
    if not data or not isinstance(data, str):
        return default if default is not None else []

    decoder = json.JSONDecoder()
    stripped = data.strip()
    candidates = [index for index in (stripped.find("["), stripped.find("{")) if index >= 0]
    for start in sorted(candidates):
        try:
            parsed, _ = decoder.raw_decode(stripped[start:])
            return parsed
        except (ValueError, TypeError):
            continue
    return default if default is not None else []


def _validate_pulp_name(value: str, label: str = "Pulp name") -> Tuple[bool, str]:
    """Validate a generated Pulp object name before using it in a command."""
    if not isinstance(value, str) or not value.strip():
        return False, f"{label} cannot be empty"
    if value != value.strip() or value.startswith("-"):
        return False, f"Invalid {label.lower()}: {value!r}"
    if any(char.isspace() or ord(char) < 32 for char in value):
        return False, f"Invalid {label.lower()}: whitespace/control characters are not allowed"
    if "/" in value or "\\" in value or value in (".", ".."):
        return False, f"Invalid {label.lower()}: path separators are not allowed"
    return True, ""


def _validate_artifact_name(value: str) -> Tuple[bool, str]:
    """Validate a catalog artifact name used for local content cleanup."""
    valid, message = _validate_pulp_name(value, "artifact name")
    if not valid:
        return valid, message
    return True, ""


# =============================================================================
# CONTAINER IMAGE VALIDATION & CONVERSION
# =============================================================================

def validate_container_format(image_name: str) -> Tuple[bool, str]:
    """Validate container image format.

    User must provide format: registry/image (e.g., registry.k8s.io/pause)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(image_name, str) or not image_name:
        return False, "Container image name cannot be empty"

    if image_name != image_name.strip() or image_name.startswith("-"):
        return False, f"Invalid container image name: {image_name!r}"
    if any(char.isspace() or ord(char) < 32 for char in image_name):
        return False, "Container image name cannot contain whitespace or control characters"
    if "\\" in image_name:
        return False, "Container image name cannot contain backslash path separators"
    if "@" in image_name:
        return False, (
            "Container cleanup does not accept image digests; provide an image "
            "repository with an optional tag"
        )

    # Must contain at least one '/' to indicate registry/image format
    if '/' not in image_name:
        return False, (
            f"Invalid format '{image_name}'. Must include registry "
            "(e.g., registry.k8s.io/pause, docker.io/library/busybox)"
        )

    # Must have a registry part (contains '.' or is a known registry)
    parts = image_name.split('/')
    if any(part in ("", ".", "..") for part in parts):
        return False, f"Invalid container image path: {image_name!r}"
    registry = parts[0]

    # Check if registry looks valid (contains dot or is localhost)
    if '.' not in registry and registry != 'localhost' and ':' not in registry:
        return False, (
            f"Invalid registry '{registry}' in '{image_name}'. "
            "Registry must be a domain (e.g., docker.io, registry.k8s.io)"
        )

    _, tag = split_container_reference(image_name)
    if ":" in parts[-1] and not tag:
        return False, "Container image tag cannot be empty"
    if tag and not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
        return False, f"Invalid container image tag: {tag!r}"

    return True, ""


def convert_to_pulp_container_name(image_name: str) -> str:
    """Convert user-provided image name to Pulp repository name.

    Examples:
        registry.k8s.io/pause -> container_repo_registry.k8s.io_pause
        docker.io/library/busybox -> container_repo_docker.io_library_busybox
        ghcr.io/kube-vip/kube-vip -> container_repo_ghcr.io_kube-vip_kube-vip
    """
    # Replace '/' with '_' and prepend 'container_repo_'
    normalized = image_name.replace('/', '_').replace(':', '_')
    return f"container_repo_{normalized}"


def split_container_reference(image_reference: str) -> Tuple[str, Optional[str]]:
    """Split a container reference without treating a registry port as a tag."""
    untagged = image_reference.split("@", 1)[0]
    last_slash = untagged.rfind("/")
    last_colon = untagged.rfind(":")
    if last_colon > last_slash:
        return untagged[:last_colon], untagged[last_colon + 1:] or None
    return untagged, None


def container_repo_name_for_reference(image_reference: str) -> str:
    """Return the repository-level Pulp name for a possibly tagged image."""
    untagged, _ = split_container_reference(image_reference)
    return convert_to_pulp_container_name(untagged)


def rpm_repository_context(
        repository_name: str
) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """Return architecture, OS, version and logical repository name."""
    for arch in ARCH_SUFFIXES:
        prefix = f"{arch}_"
        if repository_name.startswith(prefix):
            remainder = repository_name[len(prefix):]
            match = re.match(
                r"^(?P<os_type>[^_]+)_"
                r"(?P<os_version>[0-9]+(?:\.[0-9]+)*)_"
                r"(?P<repo_name>.+)$",
                remainder,
            )
            if match:
                return (
                    arch,
                    match.group("os_type"),
                    match.group("os_version"),
                    match.group("repo_name"),
                )
            return arch, None, None, repository_name
    return None, None, None, repository_name


def rpm_repository_identity(repository_name: str) -> Tuple[Optional[str], str]:
    """Return architecture and catalog repository name from a Pulp name.

    Current Pulp repositories use ``<arch>_<os>_<version>_<repo>`` while
    mirror-index entries retain the catalog's logical ``repo`` value. Legacy
    repositories without that prefix remain supported.
    """
    arch, _os_type, _os_version, repo_name = rpm_repository_context(
        repository_name
    )
    return arch, repo_name


# =============================================================================
# TYPE DETECTION
# =============================================================================



def detect_file_types(name: str, base_path: str) -> List[str]:
    """Return every exact local artifact type containing ``name``."""
    detected = []
    for file_type in CLEANUP_FILE_TYPES:
        pattern = os.path.join(base_path, "*", "*", "*", file_type, name)
        if glob.glob(pattern):
            detected.append(file_type)
    return detected


def detect_status_file_types(name: str, base_path: str) -> List[str]:
    """Return exact file artifact types retained only in status files."""
    detected = set()
    for arch in ARCH_SUFFIXES:
        for status_file in glob.glob(
                f"{base_path}/*/*/{arch}/*/status.csv"):
            with open(status_file, "r", encoding="utf-8") as stream:
                for row in csv.DictReader(stream):
                    if (
                        row.get("name") == name
                        and row.get("type") in CLEANUP_FILE_TYPES
                    ):
                        detected.add(row["type"])
    return sorted(detected)

# =============================================================================
# EXISTENCE CHECKS
# =============================================================================


def _is_not_found(result: Dict[str, Any]) -> bool:
    """Return whether a failed Pulp command represents an absent object."""
    message = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    return any(marker in message for marker in (
        "not found", "does not exist", "could not find", "matches the given query", "404"
    ))


def _pulp_object_exists(plugin: str, resource: str, name: str, logger,
                        reference_option: str = "--name") -> Optional[bool]:
    """Return True/False for object presence, or None for an operational error."""
    result = run_pulp(
        [plugin, resource, "show", reference_option, name], logger
    )
    if result["rc"] == 0:
        return True
    if _is_not_found(result):
        return False
    logger.error(
        "Unable to query Pulp %s %s %s: %s",
        plugin, resource, name, result.get("stderr", "")
    )
    return None


def _list_pulp_objects(plugin: str, resource: str, logger,
                       filters: Optional[Sequence[str]] = None,
                       fields: Optional[Sequence[str]] = None) -> Optional[List[Dict[str, Any]]]:
    """Return every Pulp object using deterministic CLI pagination."""
    page_size = 1000
    offset = 0
    objects = []
    filters = list(filters or [])
    fields = list(fields or [])

    while True:
        args = [
            plugin, resource, "list", *filters,
            "--limit", str(page_size), "--offset", str(offset),
        ]
        for field in fields:
            args.extend(["--field", field])
        result = run_pulp(args, logger)
        if result["rc"] != 0:
            logger.error(
                "Failed to list Pulp %s %s objects: %s",
                plugin, resource, result.get("stderr", "")
            )
            return None

        page = safe_json_parse(result["stdout"], default={})
        if not isinstance(page, list):
            logger.error(
                "Pulp %s %s list returned non-JSON output: %s",
                plugin, resource, result.get("stdout", "")[:200]
            )
            return None
        objects.extend(item for item in page if isinstance(item, dict))
        if len(page) < page_size:
            break
        offset += page_size

    return objects


def _delete_named_object(plugin: str, resource: str, name: str, logger,
                         required: bool = True) -> Tuple[bool, str]:
    """Delete and verify one name-addressable Pulp object."""
    exists = _pulp_object_exists(plugin, resource, name, logger)
    if exists is None:
        return False, f"Unable to check {plugin} {resource} '{name}'"
    if not exists:
        return True, f"{resource} already absent"

    result = run_pulp([plugin, resource, "destroy", "--name", name], logger)
    if result["rc"] != 0:
        level = "required" if required else "optional"
        return False, (
            f"Failed to delete {level} {plugin} {resource} '{name}': "
            f"{result.get('stderr', '').strip()}"
        )
    remaining = _pulp_object_exists(plugin, resource, name, logger)
    if remaining is not False:
        return False, f"Pulp {plugin} {resource} '{name}' still exists after deletion"
    return True, f"{resource} deleted"


def _delete_href_object(plugin: str, resource: str, href: str, logger) -> Tuple[bool, str]:
    """Delete one href-addressable Pulp object and verify it is absent."""
    if not isinstance(href, str) or not href.startswith("/pulp/api/"):
        return False, f"Invalid Pulp {resource} href: {href!r}"
    result = run_pulp([plugin, resource, "destroy", "--href", href], logger)
    if result["rc"] != 0 and not _is_not_found(result):
        return False, (
            f"Failed to delete {plugin} {resource} '{href}': "
            f"{result.get('stderr', '').strip()}"
        )
    remaining = _pulp_object_exists(
        plugin, resource, href, logger, reference_option="--href"
    )
    if remaining is not False:
        return False, f"Pulp {plugin} {resource} '{href}' still exists after deletion"
    return True, f"{resource} deleted"


def repo_exists(name: str, logger) -> Optional[bool]:
    """Check if an RPM repository exists without masking endpoint errors."""
    return _pulp_object_exists("rpm", "repository", name, logger)


def container_exists(name: str, logger) -> Optional[bool]:
    """Check if a container repository exists without masking endpoint errors."""
    return _pulp_object_exists("container", "repository", name, logger)


def _list_container_repository_tags(repository_name: str, logger) -> Optional[List[Dict[str, Any]]]:
    """Return all tags in the latest version of one container repository."""
    page_size = 1000
    offset = 0
    tags = []
    while True:
        result = run_pulp([
            "container", "repository", "content", "-t", "tag", "list",
            "--repository", repository_name,
            "--limit", str(page_size), "--offset", str(offset),
        ], logger)
        if result["rc"] != 0:
            logger.error(
                "Failed to list tags for container repository %s: %s",
                repository_name, result.get("stderr", "")
            )
            return None
        page = safe_json_parse(result["stdout"], default={})
        if not isinstance(page, list):
            logger.error(
                "Container tag list returned non-JSON output for %s: %s",
                repository_name, result.get("stdout", "")[:200]
            )
            return None
        tags.extend(item for item in page if isinstance(item, dict))
        if len(page) < page_size:
            break
        offset += page_size
    return tags


def _cleanup_container_tag(repository_name: str, tag: str,
                           logger) -> Tuple[bool, str]:
    """Remove exactly one tag while preserving its repository and distribution."""
    repository_present = container_exists(repository_name, logger)
    if repository_present is None:
        return False, f"Unable to query container repository '{repository_name}'"
    if not repository_present:
        return True, "container tag already absent (repository does not exist)"

    distribution_present = _pulp_object_exists(
        "container", "distribution", repository_name, logger
    )
    if distribution_present is None:
        return False, f"Unable to query container distribution '{repository_name}'"

    tags_before = _list_container_repository_tags(repository_name, logger)
    if tags_before is None:
        return False, f"Unable to list tags in container repository '{repository_name}'"
    names_before = sorted(item.get("name", "") for item in tags_before)
    matching_tags = [item for item in tags_before if item.get("name") == tag]
    if not matching_tags:
        return True, "container tag already absent"
    if len(matching_tags) != 1:
        return False, (
            f"Expected one exact tag '{tag}' in '{repository_name}', "
            f"found {len(matching_tags)}"
        )

    untag_result = run_pulp([
        "container", "repository", "untag",
        "--name", repository_name, "--tag", tag,
    ], logger)
    if untag_result["rc"] != 0:
        return False, (
            f"Failed to remove container tag '{tag}' from '{repository_name}': "
            f"{untag_result.get('stderr', '').strip()}"
        )

    tags_after = _list_container_repository_tags(repository_name, logger)
    if tags_after is None:
        return False, f"Unable to verify tag removal from '{repository_name}'"
    names_after = sorted(item.get("name", "") for item in tags_after)
    expected_names = sorted(name for name in names_before if name != tag)
    if names_after != expected_names:
        return False, (
            "Container tags do not match the expected state after cleanup: "
            f"expected {expected_names}, found {names_after}"
        )

    repository_after = container_exists(repository_name, logger)
    distribution_after = _pulp_object_exists(
        "container", "distribution", repository_name, logger
    )
    if repository_after is not True:
        return False, "Container repository was not preserved after tag cleanup"
    if distribution_after is None or distribution_after != distribution_present:
        return False, "Container distribution state changed during tag cleanup"
    return True, f"container tag '{tag}' removed; repository preserved"


def file_exists_in_status(name: str, base_path: str, logger,
                          arch: Optional[str] = None,
                          os_type: Optional[str] = None,
                          os_version: Optional[str] = None) -> bool:
    """Check if file artifact exists in status files."""
    try:
        arches = [arch] if arch else ARCH_SUFFIXES
        for current_arch in arches:
            status_pattern = (
                f"{base_path}/{os_type}/{os_version}/"
                f"{current_arch}/*/status.csv"
                if os_type and os_version
                else f"{base_path}/*/*/{current_arch}/*/status.csv"
            )
            for status_file in glob.glob(status_pattern):
                with open(status_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    if any(row.get("name", "") == name for row in reader):
                        return True
        return False
    except OSError as error:
        logger.error("Failed to inspect status files for %s: %s", name, error)
        raise


def get_all_repositories(logger) -> List[str]:
    """Get all RPM repository names from Pulp."""
    repos = _list_pulp_objects("rpm", "repository", logger, fields=["name"])
    return None if repos is None else [item["name"] for item in repos if item.get("name")]


def get_all_containers(logger) -> List[str]:
    """Get all container repository names from Pulp."""
    repos = _list_pulp_objects("container", "repository", logger, fields=["name"])
    return None if repos is None else [item["name"] for item in repos if item.get("name")]


def get_all_file_repositories(logger) -> List[str]:
    """Get all file repository names from Pulp."""
    repos = _list_pulp_objects("file", "repository", logger, fields=["name"])
    return None if repos is None else [item["name"] for item in repos if item.get("name")]


def get_all_python_repositories(logger) -> List[str]:
    """Get all Python repository names from Pulp."""
    repos = _list_pulp_objects("python", "repository", logger, fields=["name"])
    return None if repos is None else [item["name"] for item in repos if item.get("name")]


# =============================================================================
# CLEANUP FUNCTIONS
# =============================================================================

def _delete_publications(plugin: str, repository_name: str, logger) -> Tuple[bool, List[str]]:
    """Delete all publications associated with one repository."""
    publications = _list_pulp_objects(
        plugin,
        "publication",
        logger,
        filters=["--repository", repository_name],
        fields=["pulp_href"],
    )
    if publications is None:
        return False, [f"Unable to list {plugin} publications"]

    messages = []
    for publication in publications:
        href = publication.get("pulp_href", "")
        success, message = _delete_href_object(
            plugin, "publication", href, logger
        )
        messages.append(message)
        if not success:
            return False, messages
    if not publications:
        messages.append("publications already absent")
    return True, messages


def _cleanup_uploaded_repository(plugin: str, repository_name: str,
                                 logger) -> Tuple[bool, List[str]]:
    """Delete a File/Python distribution, publications and repository."""
    valid, validation_message = _validate_pulp_name(
        repository_name, f"{plugin} repository name"
    )
    if not valid:
        return False, [validation_message]

    repository_present = _pulp_object_exists(
        plugin, "repository", repository_name, logger
    )
    if repository_present is None:
        return False, [f"Unable to query {plugin} repository '{repository_name}'"]

    messages = []
    ok, message = _delete_named_object(
        plugin, "distribution", repository_name, logger
    )
    messages.append(message)
    if not ok:
        return False, messages

    if repository_present:
        ok, publication_messages = _delete_publications(
            plugin, repository_name, logger
        )
        messages.extend(publication_messages)
        if not ok:
            return False, messages
    else:
        messages.append("repository already absent")

    ok, message = _delete_named_object(
        plugin, "repository", repository_name, logger
    )
    messages.append(message)
    return ok, messages


def cleanup_repository(name: str, base_path: str, repo_store_path: str,
                       logger) -> Dict[str, Any]:
    """Cleanup a single RPM repository."""
    result = {"name": name, "type": "repository", "status": "Failed", "message": ""}
    valid, validation_message = _validate_pulp_name(name, "RPM repository name")
    if not valid:
        result["message"] = validation_message
        return result

    try:
        repository_present = repo_exists(name, logger)
        if repository_present is None:
            result["message"] = "Unable to query RPM repository; Pulp may be unavailable"
            return result

        messages = []
        ok, message = _delete_named_object("rpm", "distribution", name, logger)
        messages.append(message)
        if not ok:
            result["message"] = "; ".join(messages)
            return result

        if repository_present:
            ok, publication_messages = _delete_publications("rpm", name, logger)
            messages.extend(publication_messages)
            if not ok:
                result["message"] = "; ".join(messages)
                return result
        else:
            messages.append("repository already absent")

        ok, message = _delete_named_object(
            "rpm", "remote", name, logger, required=False
        )
        messages.append(message)
        if not ok:
            result["message"] = "; ".join(messages)
            return result

        ok, message = _delete_named_object("rpm", "repository", name, logger)
        messages.append(message)
        if not ok:
            result["message"] = "; ".join(messages)
            return result
        result["pulp_absent"] = True

        rpm_file_artifacts = find_rpm_file_artifacts(name, base_path, logger)
        affected = remove_rpms_from_repository(name, base_path, logger)
        mark_software_partial(affected, base_path, logger, 'repository')
        filesystem_failures = []
        _repo_arch, repo_os, repo_version, _repo_name = (
            rpm_repository_context(name)
        )
        for arch, artifact_name in rpm_file_artifacts:
            fs_result = cleanup_content_directory(
                artifact_name, "rpm_file", repo_store_path, logger, arch=arch,
                os_type=repo_os, os_version=repo_version
            )
            if fs_result["status"] == "Success":
                messages.append(fs_result["message"])
            elif not fs_result["message"].startswith((
                    "No filesystem content found", "Content store path not found")):
                filesystem_failures.append(fs_result["message"])

        if filesystem_failures:
            messages.extend(filesystem_failures)
            result["message"] = "; ".join(messages)
            return result

        result["status"] = "Success"
        result["message"] = "; ".join(messages)

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


def cleanup_container(user_input: str, base_path: str, logger) -> Dict[str, Any]:
    """Cleanup one container tag or a complete container repository.

    Args:
        user_input: User-provided image name (e.g., registry.k8s.io/pause)
                    or Pulp repository name (e.g., container_repo_registry.k8s.io_pause)
                    when called from cleanup_containers=all
    """
    result = {"name": user_input, "type": "container", "status": "Failed", "message": ""}
    tag = None

    # Check if input is already a Pulp repository name (from get_all_containers)
    if user_input.startswith('container_repo_'):
        valid, validation_message = _validate_pulp_name(
            user_input, "container repository name"
        )
        if not valid:
            result["message"] = validation_message
            return result
        pulp_name = user_input
        repo_suffix = user_input[len('container_repo_'):]
    else:
        # Validate format
        is_valid, error_msg = validate_container_format(user_input)
        if not is_valid:
            result["message"] = error_msg
            return result

        # Tagged input removes only that tag; untagged input removes the repository.
        _, tag = split_container_reference(user_input)
        pulp_name = container_repo_name_for_reference(user_input)
        repo_suffix = pulp_name[len('container_repo_'):]

    try:
        if tag:
            ok, message = _cleanup_container_tag(pulp_name, tag, logger)
            if not ok:
                result["message"] = message
                return result
            affected = remove_from_status_files(
                user_input, 'image', base_path, logger
            )
            mark_software_partial(affected, base_path, logger, 'image')
            result["status"] = "Success"
            result["message"] = message
            result["pulp_repo_name"] = pulp_name
            return result

        repository_present = container_exists(pulp_name, logger)
        if repository_present is None:
            result["message"] = "Unable to query container repository; Pulp may be unavailable"
            return result

        messages = []
        ok, message = _delete_named_object(
            "container", "distribution", pulp_name, logger
        )
        messages.append(message)
        if not ok:
            result["message"] = "; ".join(messages)
            return result

        # Current public and configured-registry downloads both use remote_.
        # user_remote_ is retained as an exact legacy name, never as a suffix match.
        remote_candidates = [
            f"remote_{repo_suffix}",
            f"user_remote_{repo_suffix}",
        ]
        for remote_name in remote_candidates:
            ok, message = _delete_named_object(
                "container", "remote", remote_name, logger, required=False
            )
            messages.append(message)
            if not ok:
                result["message"] = "; ".join(messages)
                return result

        ok, message = _delete_named_object(
            "container", "repository", pulp_name, logger
        )
        messages.append(message)
        if not ok:
            result["message"] = "; ".join(messages)
            return result
        result["pulp_absent"] = True

        # A container repository contains every synchronized tag for the image.
        # For explicit image input, remove all tag rows across both architectures.
        if not user_input.startswith('container_repo_'):
            affected = remove_from_status_files(user_input, 'image', base_path, logger)
        else:
            affected = remove_container_repo_from_status_files(
                pulp_name, base_path, logger
            )
        mark_software_partial(affected, base_path, logger, 'image')

        result["status"] = "Success"
        result["message"] = "; ".join(messages)
        result["pulp_repo_name"] = pulp_name

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


def cleanup_pip_module(name: str, base_path: str, repo_store_path: str, logger,
                       pulp_repo_name: str = None,
                       arch: Optional[str] = None,
                       os_type: Optional[str] = None,
                       os_version: Optional[str] = None) -> Dict[str, Any]:
    """Cleanup a pip module from Pulp Python repository.

    Pip modules are stored as: pip_module<package_name>==<version>
    e.g., pip_modulecffi==1.17.1

    Args:
        name: Content name (e.g., 'cffi==1.17.1') used for status files and filesystem
        base_path: Base path for status files
        repo_store_path: Root store path for filesystem cleanup
        logger: Logger instance
        pulp_repo_name: Optional Pulp repo name override (from cleanup_files=all).
                        If None, derived from name.
    """
    result = {"name": name, "type": "pip_module", "status": "Failed", "message": ""}
    messages = []
    pulp_clean = pulp_repo_name is None
    status_removed = False
    content_removed = False

    try:
        valid, validation_message = _validate_artifact_name(name)
        if not valid:
            result["message"] = validation_message
            return result

        if pulp_repo_name:
            pulp_clean, pulp_messages = _cleanup_uploaded_repository(
                "python", pulp_repo_name, logger
            )
            messages.extend(pulp_messages)
            if not pulp_clean:
                result["message"] = "; ".join(messages)
                return result
            result["pulp_absent"] = True
        else:
            messages.append("No matching Python repository; local state cleanup only")

        # Update status files
        if file_exists_in_status(
                name, base_path, logger, arch=arch,
                os_type=os_type, os_version=os_version):
            affected = remove_from_status_files(
                name, 'pip_module', base_path, logger, arch=arch,
                os_type=os_type, os_version=os_version
            )
            if affected:
                status_removed = True
                messages.append("Status files updated")
                mark_software_partial(affected, base_path, logger, 'pip_module')

        # Clean up uploaded content from filesystem
        fs_result = cleanup_content_directory(
            name, 'pip_module', repo_store_path, logger, arch=arch,
            os_type=os_type, os_version=os_version
        )
        if fs_result["status"] == "Success":
            content_removed = True
            messages.append(fs_result["message"])
        elif fs_result["message"].startswith("Filesystem cleanup error"):
            messages.append(fs_result["message"])
            result["message"] = "; ".join(messages)
            return result

        if pulp_clean or status_removed or content_removed:
            result["status"] = "Success"
            result["message"] = "; ".join(messages) if messages else "Cleaned up"
        else:
            result["message"] = f"pip_module '{name}' not found in Pulp or filesystem"

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result




def cleanup_file_repository(name: str, file_type: str, base_path: str,
                            repo_store_path: str, logger,
                            pulp_repo_name: str = None,
                            arch: Optional[str] = None,
                            os_type: Optional[str] = None,
                            os_version: Optional[str] = None) -> Dict[str, Any]:
    """Cleanup artifact from Pulp File repository.

    Handles: tarball, git, manifest, ansible_galaxy_collection
    All use 'pulp file' repository type with type-specific naming conventions.

    Args:
        name: Content name (e.g., 'calico-v3.30.3') used for status files and filesystem
        file_type: Artifact type (e.g., 'manifest', 'tarball')
        base_path: Base path for status files
        repo_store_path: Root store path for filesystem cleanup
        logger: Logger instance
        pulp_repo_name: Optional Pulp repo name override (from cleanup_files=all).
                        If None, derived from name + file_type.
    """
    result = {"name": name, "type": file_type, "status": "Failed", "message": ""}
    messages = []
    pulp_clean = pulp_repo_name is None
    status_removed = False
    content_removed = False

    try:
        valid, validation_message = _validate_artifact_name(name)
        if not valid:
            result["message"] = validation_message
            return result

        if file_type not in CLEANUP_FILE_TYPES or file_type == "pip_module":
            result["message"] = f"Unsupported Pulp File cleanup type: {file_type!r}"
            return result

        if pulp_repo_name:
            pulp_clean, pulp_messages = _cleanup_uploaded_repository(
                "file", pulp_repo_name, logger
            )
            messages.extend(pulp_messages)
            if not pulp_clean:
                result["message"] = "; ".join(messages)
                return result
            result["pulp_absent"] = True
        else:
            messages.append("No matching File repository; local state cleanup only")

        # Update status files
        if file_exists_in_status(
                name, base_path, logger, arch=arch,
                os_type=os_type, os_version=os_version):
            affected = remove_from_status_files(
                name, file_type, base_path, logger, arch=arch,
                os_type=os_type, os_version=os_version
            )
            if affected:
                status_removed = True
                messages.append("Status files updated")
                mark_software_partial(affected, base_path, logger, file_type)

        # Clean up uploaded content from filesystem
        fs_result = cleanup_content_directory(
            name, file_type, repo_store_path, logger, arch=arch,
            os_type=os_type, os_version=os_version
        )
        if fs_result["status"] == "Success":
            content_removed = True
            messages.append(fs_result["message"])
        elif fs_result["message"].startswith("Filesystem cleanup error"):
            messages.append(fs_result["message"])
            result["message"] = "; ".join(messages)
            return result

        # Determine overall result
        if pulp_clean or status_removed or content_removed:
            result["status"] = "Success"
            result["message"] = "; ".join(messages) if messages else "Cleaned up"
        else:
            result["message"] = f"{file_type} '{name}' not found in Pulp, status files, or filesystem"

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


def parse_pulp_file_repo_context(
        repo_name: str
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], str]:
    """Return architecture, OS, version, type and content from a Pulp name."""
    for arch in ARCH_SUFFIXES:
        prefix = f"{arch}_"
        if not repo_name.startswith(prefix):
            continue
        remainder = repo_name[len(prefix):]
        os_match = re.match(r'^([a-z]+)_(\d+(?:\.\d+)*)_', remainder)
        os_type = os_match.group(1) if os_match else None
        os_version = os_match.group(2) if os_match else None
        typed_remainder = remainder[os_match.end():] if os_match else remainder
        for file_type in sorted(CLEANUP_FILE_TYPES, key=len, reverse=True):
            if typed_remainder.startswith(file_type):
                return (
                    arch, os_type, os_version, file_type,
                    typed_remainder[len(file_type):],
                )
        return arch, os_type, os_version, None, typed_remainder
    return None, None, None, None, repo_name


def parse_pulp_file_repo_name(repo_name: str) -> Tuple[str, str, str]:
    """Parse a Pulp file/python repository name into components.

    Pulp repo names follow the format:
        {arch}_{os_type}_{os_version}_{type}{content_name}
    e.g.:
        x86_64_rhel_10.0_manifestcalico-v3.30.3 -> ('x86_64', 'manifest', 'calico-v3.30.3')
        x86_64_rhel_10.0_pip_modulecffi==1.17.1 -> ('x86_64', 'pip_module', 'cffi==1.17.1')
        aarch64_rhel_10.0_isocuda-run            -> ('aarch64', 'iso', 'cuda-run')

    Also supports legacy format without os_type/version for backward compatibility:
        x86_64_manifestcalico-v3.30.3 -> ('x86_64', 'manifest', 'calico-v3.30.3')

    Returns:
        Tuple of (arch, file_type, content_name).
        Returns (None, None, repo_name) if parsing fails.
    """
    arch, _os_type, _os_version, file_type, content_name = (
        parse_pulp_file_repo_context(repo_name)
    )
    return arch, file_type, content_name


def expand_cleanup_file_requests(requested_names: List[str],
                                 repository_names: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Resolve bare artifact names to exact Pulp repositories across architectures.

    A full Pulp repository name remains architecture-specific. A bare artifact
    name expands to all exact parsed matches. Ambiguous matches across multiple
    artifact types are rejected rather than selecting the first substring hit.
    """
    expanded = []
    errors = []
    known_repositories = list(dict.fromkeys(repository_names))

    for requested in requested_names:
        if requested in known_repositories:
            expanded.append(requested)
            continue

        requested_arch, requested_type, _ = parse_pulp_file_repo_name(requested)
        if requested_arch and requested_type:
            # Preserve an exact, already-qualified request even when Pulp no
            # longer contains it so stale local tracking can converge safely.
            expanded.append(requested)
            continue

        valid, validation_message = _validate_artifact_name(requested)
        if not valid:
            errors.append({
                "name": requested,
                "type": "file",
                "status": "Failed",
                "message": validation_message,
            })
            continue

        matches = []
        matched_types = set()
        for repository_name in known_repositories:
            _arch, file_type, content_name = parse_pulp_file_repo_name(repository_name)
            if file_type and content_name == requested:
                matches.append(repository_name)
                matched_types.add(file_type)

        if len(matched_types) > 1:
            errors.append({
                "name": requested,
                "type": "file",
                "status": "Failed",
                "message": (
                    "Artifact name is ambiguous across types "
                    f"{sorted(matched_types)}; provide the full Pulp repository name"
                ),
            })
            continue
        expanded.extend(matches or [requested])

    return list(dict.fromkeys(expanded)), errors


def cleanup_file(name: str, base_path: str, repo_store_path: str, logger) -> Dict[str, Any]:
    """Cleanup a file artifact.

    Routes to appropriate handler:
    - pip_module: Pulp Python repository
    - tarball, git, manifest, ansible_galaxy_collection: Pulp File repository

    When called from cleanup_files=all, names are Pulp repo names like
    'x86_64_manifestcalico-v3.30.3'. These are parsed to extract the type
    and content name for correct routing, status updates, and filesystem cleanup.
    """
    # Try parsing as a Pulp repo name (from cleanup_files=all)
    arch, os_type, os_version, parsed_type, content_name = (
        parse_pulp_file_repo_context(name)
    )

    if parsed_type:
        # Name is a Pulp repo name — use parsed type and content name
        file_type = parsed_type
        pulp_name = name
        artifact_name = content_name
        logger.info(f"Parsed Pulp repo name: arch={arch}, type={file_type}, content={artifact_name}")
    else:
        # Name is a user-provided content name. Exact Pulp matching has already
        # been attempted, so only local state remains to be resolved here.
        local_root = os.path.join(
            repo_store_path, *PULP_DISTRIBUTION_ROOT_PARTS
        )
        detected_types = sorted(set(
            detect_file_types(name, local_root)
            + detect_status_file_types(name, base_path)
        ))
        if len(detected_types) > 1:
            return {
                "name": name,
                "type": "file",
                "status": "Failed",
                "message": (
                    "Artifact name is ambiguous across local types "
                    f"{detected_types}; provide the full Pulp repository name"
                ),
            }
        file_type = detected_types[0] if detected_types else None
        pulp_name = None
        artifact_name = name

    if not file_type:
        return {
            "name": artifact_name,
            "type": "file",
            "status": "Failed",
            "message": "Artifact not found in Pulp or the local content store",
        }

    # Handle pip modules separately - they use Python repositories
    if file_type == "pip_module":
        result = cleanup_pip_module(
            artifact_name, base_path, repo_store_path, logger,
            pulp_repo_name=pulp_name, arch=arch,
            os_type=os_type, os_version=os_version
        )
    else:
        result = cleanup_file_repository(
            artifact_name, file_type, base_path, repo_store_path, logger,
            pulp_repo_name=pulp_name, arch=arch,
            os_type=os_type, os_version=os_version
        )

    if arch:
        result["arch"] = arch
    if pulp_name:
        result["pulp_repo_name"] = pulp_name
    if os_type and os_version:
        result["os_type"] = os_type
        result["os_version"] = os_version
    return result


# =============================================================================
# FILESYSTEM CONTENT CLEANUP
# =============================================================================

def cleanup_content_directory(content_name: str, content_type: str,
                              repo_store_path: str, logger,
                              arch: Optional[str] = None,
                              os_type: Optional[str] = None,
                              os_version: Optional[str] = None) -> Dict[str, Any]:
    """Remove uploaded content directory from the filesystem.

    Builds the content path from the configured distribution root, matching
    download_common.py.

    This mirrors how remove_from_status_files iterates over ARCH_SUFFIXES to
    clean status.csv entries.

    Args:
        content_name: Name of the content item (e.g., 'helm-v3.19.0-amd64')
        content_type: Directory category (tarball, git, pip_module, manifest,
                      ansible_galaxy_collection, rpm_file)
        repo_store_path: Root store path (e.g., config.REPO_MANAGER_BASE_DIR)
        logger: Logger instance

    Returns:
        Dict with name, type, status, and message keys
    """
    result = {"name": content_name, "type": f"filesystem_{content_type}",
              "status": "Failed", "message": ""}
    removed_dirs = []

    valid, validation_message = _validate_artifact_name(content_name)
    if not valid:
        result["message"] = validation_message
        return result

    allowed_types = set(CLEANUP_FILE_TYPES) | {"rpm_file"}
    if content_type is not None and content_type not in allowed_types:
        result["message"] = f"Unsupported cleanup content type: {content_type!r}"
        return result
    if arch is not None and arch not in ARCH_SUFFIXES:
        result["message"] = f"Unsupported cleanup architecture: {arch!r}"
        return result

    cluster_path = os.path.join(
        repo_store_path, *PULP_DISTRIBUTION_ROOT_PARTS
    )
    if not os.path.exists(cluster_path):
        result["message"] = f"Content store path not found: {cluster_path}"
        logger.warning(result["message"])
        return result

    # If content_type is None (e.g., from cleanup_files=all when detect_file_type fails),
    # search all known type directories to find and delete the content
    types_to_search = [content_type] if content_type else CLEANUP_FILE_TYPES

    try:
        arches = [arch] if arch else ARCH_SUFFIXES
        for current_arch in arches:
            # Walk version directories (e.g., rhel/10.0)
            arch_path = validate_cleanup_child(cluster_path, current_arch)
            if not os.path.isdir(arch_path):
                continue

            candidate_pattern = (
                os.path.join(arch_path, os_type, os_version, "")
                if os_type and os_version
                else f"{arch_path}/*/*/"
            )
            for candidate_dir in glob.glob(candidate_pattern):
                relative_parts = os.path.relpath(
                    candidate_dir, arch_path
                ).strip(os.sep).split(os.sep)
                version_dir = validate_cleanup_child(arch_path, *relative_parts)
                for search_type in types_to_search:
                    content_dir = validate_cleanup_child(
                        version_dir, search_type, content_name
                    )
                    if os.path.exists(content_dir):
                        logger.info(f"Removing content directory: {content_dir}")
                        if os.path.islink(content_dir):
                            os.unlink(content_dir)
                        elif os.path.isdir(content_dir):
                            shutil.rmtree(content_dir)
                        else:
                            os.remove(content_dir)
                        removed_dirs.append(content_dir)
                        # Remove parent type directory if now empty
                        type_dir = validate_cleanup_child(version_dir, search_type)
                        if os.path.isdir(type_dir) and not os.listdir(type_dir):
                            os.rmdir(type_dir)
                            logger.info(f"Removed empty directory: {type_dir}")

        if removed_dirs:
            result["status"] = "Success"
            result["message"] = f"Removed content: {', '.join(removed_dirs)}"
        else:
            result["message"] = (f"No filesystem content found for "
                                 f"'{content_name}' under {types_to_search}")
            logger.info(result["message"])

    except Exception as e:
        result["message"] = f"Filesystem cleanup error: {str(e)}"
        logger.error(f"Failed to cleanup content {content_name}: {e}")

    return result


def cleanup_all_file_content_directories(repo_store_path: str, logger,
                                         content_types: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Remove all file-type content directories from the filesystem.

    Called during cleanup_files=all to ensure all locally stored files
    under the configured distribution root are deleted.

    Walks through all architectures, OS versions, and file-type directories,
    removing all content within each file-type folder.

    Args:
        repo_store_path: Root store path (e.g., config.REPO_MANAGER_BASE_DIR)
        logger: Logger instance
        content_types: Optional subset of supported content directories. The
                       default is every File/Python artifact type.

    Returns:
        Dict with status and message
    """
    types_to_remove = list(content_types or CLEANUP_FILE_TYPES)
    allowed_types = set(CLEANUP_FILE_TYPES) | {"rpm_file"}
    unsupported_types = sorted(set(types_to_remove) - allowed_types)
    result = {"name": "all_file_content", "type": "filesystem_bulk",
              "status": "Failed", "message": ""}
    removed_dirs = []

    if unsupported_types:
        result["message"] = f"Unsupported bulk content types: {unsupported_types}"
        return result

    cluster_path = os.path.join(
        repo_store_path, *PULP_DISTRIBUTION_ROOT_PARTS
    )
    if not os.path.exists(cluster_path):
        result["status"] = "Success"
        result["message"] = f"Content store already absent: {cluster_path}"
        logger.info(result["message"])
        return result

    try:
        for arch in ARCH_SUFFIXES:
            arch_path = validate_cleanup_child(cluster_path, arch)
            if not os.path.isdir(arch_path):
                continue

            for candidate_dir in glob.glob(f"{arch_path}/*/*/"):
                relative_parts = os.path.relpath(
                    candidate_dir, arch_path
                ).strip(os.sep).split(os.sep)
                version_dir = validate_cleanup_child(arch_path, *relative_parts)
                for file_type in types_to_remove:
                    type_dir = validate_cleanup_child(version_dir, file_type)
                    if os.path.islink(type_dir):
                        os.unlink(type_dir)
                        removed_dirs.append(type_dir)
                        logger.info(f"Removed content-directory symlink: {type_dir}")
                        continue
                    if os.path.isdir(type_dir):
                        # Remove all content within this type directory
                        for item in os.listdir(type_dir):
                            item_path = validate_cleanup_child(type_dir, item)
                            logger.info(f"Removing: {item_path}")
                            if os.path.islink(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                            removed_dirs.append(item_path)
                        # Remove the empty type directory itself
                        if not os.listdir(type_dir):
                            os.rmdir(type_dir)
                            logger.info(f"Removed empty directory: {type_dir}")

        if removed_dirs:
            result["status"] = "Success"
            result["message"] = f"Removed {len(removed_dirs)} content items from filesystem"
            logger.info(result["message"])
        else:
            result["status"] = "Success"
            result["message"] = "Requested filesystem content already absent"
            logger.info(result["message"])

    except Exception as e:
        result["message"] = f"Bulk filesystem cleanup error: {str(e)}"
        logger.error(f"Failed bulk filesystem cleanup: {e}")

    return result


# =============================================================================
# MIRROR INDEX UPDATES
# =============================================================================

def _get_mirror_index_path(base_path: str, cluster_os_type: str, cluster_os_version: str) -> str:
    """Construct the path to pulp_mirror_index.json.

    Path: {base_path}/{os_type}/{os_version}/mirror_status/pulp_mirror_index.json
    """
    return os.path.join(base_path, cluster_os_type, cluster_os_version,
                        MIRROR_STATUS_DIR, MIRROR_INDEX_FILENAME)


def remove_from_mirror_index(base_path: str, cluster_os_type: str, cluster_os_version: str,
                             logger, match_fn=None, remove_all: bool = False,
                             all_versions: bool = False) -> int:
    """Remove entries from pulp_mirror_index.json that match the given criteria.

    Args:
        base_path: Base log path (e.g., $OMNIA_DATA_PATH/log/repo_manager)
        cluster_os_type: OS type (e.g., 'rhel')
        cluster_os_version: OS version (e.g., '10.0')
        logger: Logger instance
        match_fn: Callable(identity_key, entry) -> bool.
                  Returns True for entries that should be removed.
        remove_all: If True, remove ALL entries (used by cleanup_repos=all etc.)

    Returns:
        int: Number of entries removed
    """
    if all_versions:
        mirror_index_paths = sorted(glob.glob(os.path.join(
            base_path, cluster_os_type, "*", MIRROR_STATUS_DIR,
            MIRROR_INDEX_FILENAME
        )))
        return sum(
            remove_from_mirror_index(
                base_path, cluster_os_type,
                Path(index_path).parents[1].name, logger,
                match_fn=match_fn, remove_all=remove_all
            )
            for index_path in mirror_index_paths
        )

    mirror_index_path = _get_mirror_index_path(
        base_path, cluster_os_type, cluster_os_version
    )

    if not os.path.isfile(mirror_index_path):
        logger.info("Mirror index not found at %s, nothing to update", mirror_index_path)
        return 0

    try:
        with open(mirror_index_path, "r", encoding="utf-8") as stream:
            mirror_data = json.load(stream)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise RuntimeError(
            f"Cannot safely update mirror index {mirror_index_path}: {error}"
        ) from error

    mirror_root = mirror_data.get("MirrorIndex")
    packages = mirror_root.get("packages") if isinstance(mirror_root, dict) else None
    if not isinstance(packages, dict):
        raise RuntimeError(
            f"Cannot safely update malformed mirror index {mirror_index_path}"
        )

    if not packages:
        logger.info("Mirror index has no packages, nothing to remove")
        return 0

    if remove_all:
        removed_count = len(packages)
        mirror_data["MirrorIndex"]["packages"] = {}
        logger.info("Removed all %d entries from mirror index", removed_count)
    else:
        keys_to_remove = [
            identity_key for identity_key, entry in packages.items()
            if match_fn and match_fn(identity_key, entry)
        ]
        removed_count = len(keys_to_remove)
        for key in keys_to_remove:
            del packages[key]
            logger.info("Removed '%s' from mirror index", key)

    if removed_count > 0:
        save_mirror_index(mirror_index_path, mirror_data, logger)
        logger.info("Saved mirror index after removing %d entries", removed_count)

    return removed_count


def remove_repo_from_mirror_index(repo_name: str, base_path: str,
                                  cluster_os_type: str, cluster_os_version: str,
                                  logger) -> int:
    """Remove all mirror index entries whose repo_name matches the deleted repository.

    Args:
        repo_name: Repository name (e.g., 'x86_64_rhel_10.0_appstream')
        base_path: Base log path
        cluster_os_type: OS type
        cluster_os_version: OS version
        logger: Logger instance

    Returns:
        int: Number of entries removed
    """
    repo_arch, catalog_repo_name = rpm_repository_identity(repo_name)

    def match_by_repo(_identity_key, entry):
        entry_repo_name = entry.get("repo_name", "")
        return (
            entry_repo_name in (repo_name, catalog_repo_name)
            and (not repo_arch or entry.get("arch") in ("", repo_arch))
        )

    _repo_arch, _repo_os, parsed_version, _repo_name = rpm_repository_context(
        repo_name
    )
    repository_version = parsed_version or cluster_os_version
    removed = remove_from_mirror_index(
        base_path, cluster_os_type, repository_version, logger,
        match_fn=match_by_repo
    )
    logger.info("Removed %d packages from mirror index for repo '%s'", removed, repo_name)
    return removed


def remove_artifact_from_mirror_index(artifact_name: str, artifact_type: str,
                                      base_path: str, cluster_os_type: str,
                                      cluster_os_version: str, logger,
                                      arch: Optional[str] = None,
                                      os_version: Optional[str] = None) -> int:
    """Remove a specific artifact entry from pulp_mirror_index.json.

    For containers, matches with or without tag.
    For other types, uses exact name match.

    Args:
        artifact_name: Name of the artifact
        artifact_type: Type (image, tarball, git, pip_module, etc.)
        base_path: Base log path
        cluster_os_type: OS type
        cluster_os_version: OS version
        logger: Logger instance

    Returns:
        int: Number of entries removed
    """
    def match_artifact(_identity_key, entry):
        if entry.get("type") != artifact_type:
            return False
        if arch and entry.get("arch") != arch:
            return False
        package_name = entry.get("package_name", "")
        if artifact_type == 'image':
            version = entry.get("version", "")
            tagged_name = f"{package_name}:{version}" if version else package_name
            return artifact_name in (package_name, tagged_name)
        return package_name == artifact_name

    removed = remove_from_mirror_index(
        base_path, cluster_os_type,
        os_version or cluster_os_version, logger,
        match_fn=match_artifact, all_versions=os_version is None
    )
    logger.info("Removed %d entries from mirror index for %s '%s'",
                removed, artifact_type, artifact_name)
    return removed


def remove_container_repo_from_mirror_index(pulp_repo_name: str, base_path: str,
                                            cluster_os_type: str,
                                            cluster_os_version: str,
                                            logger) -> int:
    """Remove every tag/architecture identity stored in one container repo."""
    def match_container_repo(_identity_key, entry):
        return (
            entry.get("type") == "image"
            and container_repo_name_for_reference(
                entry.get("package_name", "")
            ) == pulp_repo_name
        )

    return remove_from_mirror_index(
        base_path, cluster_os_type, cluster_os_version, logger,
        match_fn=match_container_repo, all_versions=True
    )


def remove_all_type_from_mirror_index(artifact_type: str, base_path: str,
                                      cluster_os_type: str, cluster_os_version: str,
                                      logger) -> int:
    """Remove all mirror index entries of a given type.

    Args:
        artifact_type: Type to remove (e.g., 'rpm', 'image', 'tarball')
        base_path: Base log path
        cluster_os_type: OS type
        cluster_os_version: OS version
        logger: Logger instance

    Returns:
        int: Number of entries removed
    """
    def match_by_type(pkg_name, entry):
        return entry.get("type", "") == artifact_type

    removed = remove_from_mirror_index(
        base_path, cluster_os_type, cluster_os_version, logger,
        match_fn=match_by_type, all_versions=True
    )
    logger.info("Removed %d '%s' entries from mirror index", removed, artifact_type)
    return removed


# =============================================================================
# STATUS FILE UPDATES
# =============================================================================

def find_rpm_file_artifacts(repo_name: str, base_path: str,
                            logger) -> List[Tuple[str, str]]:
    """Return architecture/name pairs for rpm_file rows owned by a repository."""
    artifacts = []
    repo_arch, repo_os, repo_version, catalog_repo_name = (
        rpm_repository_context(repo_name)
    )
    try:
        for arch in ARCH_SUFFIXES:
            if repo_arch and arch != repo_arch:
                continue
            status_pattern = (
                f"{base_path}/{repo_os}/{repo_version}/{arch}/*/status.csv"
                if repo_os and repo_version
                else f"{base_path}/*/*/{arch}/*/status.csv"
            )
            for status_file in glob.glob(status_pattern):
                with open(status_file, 'r', encoding='utf-8') as stream:
                    for row in csv.DictReader(stream):
                        if (
                            row.get("type", "") == "rpm_file"
                            and row.get("repo_name", "")
                            in (repo_name, catalog_repo_name)
                            and row.get("name", "")
                        ):
                            artifacts.append((arch, row["name"]))
    except OSError as error:
        logger.error("Failed to inspect rpm_file status for %s: %s", repo_name, error)
        raise
    return list(dict.fromkeys(artifacts))


def remove_rpms_from_repository(repo_name: str, base_path: str, logger) -> Dict[str, List[str]]:
    """Remove RPMs that belong to a specific repository from status files.

    Uses the repo_name column in status.csv to accurately identify RPMs from the repository.

    Args:
        repo_name: Repository name (e.g., 'x86_64_rhel_10.0_appstream', 'aarch64_rhel_10.0_epel')
        base_path: Base path for status files
        logger: Logger instance

    Returns:
        Dict mapping architecture to list of affected software names
    """
    affected_software = {}
    logger.info(f"Removing RPMs from status.csv for repository: {repo_name}")

    # Current names select one architecture; legacy unprefixed names select all.
    target_arch, repo_os, repo_version, catalog_repo_name = (
        rpm_repository_context(repo_name)
    )
    target_arches = [target_arch] if target_arch else ARCH_SUFFIXES

    try:
        for current_arch in target_arches:
            logger.info(f"Processing architecture: {current_arch}")
            arch_affected = []
            status_pattern = (
                f"{base_path}/{repo_os}/{repo_version}/"
                f"{current_arch}/*/status.csv"
                if repo_os and repo_version
                else f"{base_path}/*/*/{current_arch}/*/status.csv"
            )
            for status_file in glob.glob(status_pattern):
                rows = []
                removed = False

                with open(status_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    has_repo_column = bool(
                        fieldnames and "repo_name" in fieldnames
                    )
                    for row in reader:
                        name = row.get('name', '')
                        row_type = row.get('type', '')
                        rpm_repo = row.get('repo_name', '')

                        if (
                            row_type in ('rpm', 'rpm_repo', 'rpm_file')
                            and has_repo_column
                            and rpm_repo in (repo_name, catalog_repo_name)
                        ):
                            removed = True
                            logger.info(
                                f"Removing RPM '{name}' from {status_file} "
                                f"(repo {repo_name} deleted)"
                            )
                        else:
                            rows.append(row)

                if removed and fieldnames:
                    _atomic_write_csv(status_file, fieldnames, rows)
                    software_name = os.path.basename(
                        os.path.dirname(status_file)
                    )
                    if software_name not in arch_affected:
                        arch_affected.append(software_name)
            if arch_affected:
                affected_software[current_arch] = arch_affected

        return affected_software
    except Exception as e:
        logger.error(f"Failed to remove RPMs from repository {repo_name}: {e}")
        raise


def remove_from_status_files(artifact_name: str, artifact_type: str,
                             base_path: str, logger,
                             arch: Optional[str] = None,
                             os_type: Optional[str] = None,
                             os_version: Optional[str] = None) -> Dict[str, List[str]]:
    """Remove artifact entries from status.csv files and return affected software names.

    Removes entries so they are re-downloaded on next local_repo run
    (local_repo processes packages that are Failed or not present in status.csv).

    Args:
        artifact_name: Name of the artifact to remove
        artifact_type: Type of artifact (git, tarball, pip_module, image)
        base_path: Base path for status files
        logger: Logger instance

    Returns:
        Dict mapping architecture to list of affected software names
    """
    affected_software = {}
    try:
        arches = [arch] if arch else ARCH_SUFFIXES
        for current_arch in arches:
            arch_affected = []
            status_pattern = (
                f"{base_path}/{os_type}/{os_version}/"
                f"{current_arch}/*/status.csv"
                if os_type and os_version
                else f"{base_path}/*/*/{current_arch}/*/status.csv"
            )
            for status_file in glob.glob(status_pattern):
                rows = []
                removed = False
                with open(status_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    for row in reader:
                        name = row.get('name', '')
                        row_type = row.get('type', '')
                        # Match logic based on type
                        should_remove = False
                        if artifact_type == 'image':
                            # Container images: match with or without tag
                            should_remove = (
                                row_type == artifact_type
                                and (name == artifact_name or name.startswith(f"{artifact_name}:"))
                            )
                        else:
                            # Other types: exact match
                            should_remove = (
                                row_type == artifact_type and name == artifact_name
                            )

                        if should_remove:
                            removed = True
                            logger.info(f"Removing '{name}' from {status_file}")
                        else:
                            rows.append(row)

                if removed and fieldnames:
                    _atomic_write_csv(status_file, fieldnames, rows)

                    # Track affected software
                    software_name = os.path.basename(os.path.dirname(status_file))
                    if software_name not in arch_affected:
                        arch_affected.append(software_name)

            if arch_affected:
                affected_software[current_arch] = arch_affected

        logger.info(f"remove_from_status_files returning: {affected_software}")
        return affected_software
    except OSError as e:
        logger.error(f"Failed to remove from status files: {e}")
        raise


def remove_container_repo_from_status_files(pulp_repo_name: str, base_path: str,
                                            logger) -> Dict[str, List[str]]:
    """Remove all status rows whose image belongs to one Pulp repository."""
    affected_software = {}
    try:
        for arch in ARCH_SUFFIXES:
            arch_affected = []
            for status_file in glob.glob(
                    f"{base_path}/*/*/{arch}/*/status.csv"):
                with open(status_file, 'r', encoding='utf-8') as stream:
                    reader = csv.DictReader(stream)
                    fieldnames = reader.fieldnames
                    rows = []
                    removed = False
                    for row in reader:
                        should_remove = (
                            row.get("type") == "image"
                            and container_repo_name_for_reference(
                                row.get("name", "")
                            ) == pulp_repo_name
                        )
                        if should_remove:
                            removed = True
                        else:
                            rows.append(row)
                if removed and fieldnames:
                    _atomic_write_csv(status_file, fieldnames, rows)
                    software_name = os.path.basename(os.path.dirname(status_file))
                    if software_name not in arch_affected:
                        arch_affected.append(software_name)
            if arch_affected:
                affected_software[arch] = arch_affected
        return affected_software
    except OSError as error:
        logger.error(
            "Failed to remove container status for %s: %s",
            pulp_repo_name, error
        )
        raise


def mark_software_partial(affected_software, base_path: str, logger, artifact_type: str = None):
    """Mark software entries as partial in groups_status.csv.

    Args:
        affected_software: Either a List[str] of software names (legacy support)
                          or a Dict[str, List[str]] mapping arch to software names
        base_path: Base path for groups_status.csv
        logger: Logger instance
        artifact_type: Type of artifact being removed (for logging purposes)
    """
    logger.info(f"mark_software_partial called with affected_software: {affected_software}")
    if not affected_software:
        logger.info("No affected software to mark as partial")
        return

    # Normalize input: convert to arch_software_map if needed
    if isinstance(affected_software, list):
        logger.warning("Received list input to mark_software_partial, applying to all architectures (legacy behavior)")
        arch_software_map = {arch: affected_software for arch in ARCH_SUFFIXES}
    else:
        arch_software_map = affected_software

    try:
        for arch, software_names in arch_software_map.items():
            if not software_names:
                continue

            for software_file in glob.glob(f"{base_path}/*/*/{arch}/groups_status.csv"):
                logger.info(f"Looking for software file: {software_file}")

                rows = []
                updated = False
                with open(software_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    for row in reader:
                        if row.get('name') in software_names:
                            row['status'] = 'partial'
                            updated = True
                            logger.info(f"Marked '{row.get('name')}' as partial in {software_file} ({artifact_type} cleanup)")
                        rows.append(row)

                if fieldnames and rows and updated:
                    _atomic_write_csv(software_file, fieldnames, rows)
                    logger.info(f"Successfully wrote updated {software_file}")
    except OSError as e:
        logger.error(f"Failed to update groups_status.csv: {e}")
        raise






def remove_all_from_status_files(artifact_type: str, base_path: str, logger) -> Dict[str, List[str]]:
    """Remove all entries of a given type from status.csv files.

    Used by cleanup_containers=all and cleanup_files=all to bulk-remove
    all entries of a specific artifact type from all status.csv files.
    Removed entries will be re-downloaded on next local_repo run.

    Args:
        artifact_type: Type of artifact to remove (e.g., 'image', 'tarball', 'git', 'pip_module')
        base_path: Base path for status files
        logger: Logger instance

    Returns:
        Dict mapping architecture to list of affected software names
    """
    affected_software = {}
    try:
        for arch in ARCH_SUFFIXES:
            arch_affected = []
            for status_file in glob.glob(f"{base_path}/*/*/{arch}/*/status.csv"):
                rows = []
                removed = False
                with open(status_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    for row in reader:
                        if row.get('type', '') == artifact_type:
                            removed = True
                            logger.info(f"Removing '{row.get('name', '')}' ({artifact_type}) from {status_file}")
                        else:
                            rows.append(row)

                if removed and fieldnames:
                    _atomic_write_csv(status_file, fieldnames, rows)

                    software_name = os.path.basename(os.path.dirname(status_file))
                    if software_name not in arch_affected:
                        arch_affected.append(software_name)

            if arch_affected:
                affected_software[arch] = arch_affected

        logger.info(f"remove_all_from_status_files({artifact_type}) returning: {affected_software}")
        return affected_software
    except OSError as e:
        logger.error(f"Failed to remove all {artifact_type} from status files: {e}")
        raise


def write_cleanup_status(results: List[Dict], base_path: str):
    """Write cleanup results to status file."""
    status_file = f"{base_path}/cleanup_status.csv"
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    _atomic_write_csv(
        status_file,
        ['name', 'type', 'status', 'message'],
        results,
        extrasaction="ignore",
    )

    return status_file


def update_metadata_after_cleanup(cleaned_repos: List[str], metadata_file: str, logger,
                                  cleanup_all: bool = False):
    """Remove cleaned-up repository entries from localrepo_metadata.yml.

    For each successfully cleaned repo, find and remove its policy entry
    from the metadata file. Repo names in metadata are normalized
    (hyphens replaced with underscores, suffixed with _policy).

    When cleanup_all is True (i.e. cleanup_repos=all), the entire metadata
    file is deleted.

    Args:
        cleaned_repos: List of repo names that were successfully deleted
        metadata_file: Path to localrepo_metadata.yml
        logger: Logger instance
        cleanup_all: If True, delete the entire metadata file
    """
    if not metadata_file or (not cleaned_repos and not cleanup_all):
        return True

    if not os.path.exists(metadata_file):
        logger.info(f"Metadata file not found: {metadata_file}, skipping metadata update")
        return True

    try:
        # When cleanup_repos=all, delete the metadata file entirely.
        if cleanup_all:
            os.remove(metadata_file)
            logger.info(f"Deleted metadata file: {metadata_file}")
            return True

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = yaml.safe_load(f) or {}

        updated = False
        for repo_name in cleaned_repos:
            # Normalize repo name to match metadata key format: <name>_policy.
            # Metadata may store keys either with arch prefix (e.g., x86_64_doca_policy)
            # or without it (e.g., doca_policy), so try both.
            normalized_name = repo_name.replace('-', '_')
            candidate_policy_keys = {f"{normalized_name}_policy"}
            repo_arch, catalog_repo_name = rpm_repository_identity(repo_name)
            _arch, _os_type, repo_version, _name = rpm_repository_context(
                repo_name
            )
            candidate_policy_keys.add(
                f"{catalog_repo_name.replace('-', '_')}_policy"
            )

            def _section_matches_repo_context(
                    section: str, arch: str, version: Optional[str]) -> bool:
                """Return whether a metadata section belongs to the repo context.

                Repository names sourced from repositories.{version}.{arch} structure.
                Flat repos: baseos, appstream, epel, cuda, etc.
                Nested repos: entries under user_repos and additional_repos.
                """
                if not isinstance(section, str):
                    return False
                suffix = f"_{version}_{arch}" if version else f"_{arch}"
                return section.endswith(suffix)

            # Search through all sections in metadata for these policy keys
            for section_key in list(metadata.keys()):
                if repo_arch and not _section_matches_repo_context(
                        section_key, repo_arch, repo_version):
                    continue
                if not isinstance(metadata.get(section_key), dict):
                    continue
                for policy_key in list(candidate_policy_keys):
                    if policy_key in metadata[section_key]:
                        del metadata[section_key][policy_key]
                        updated = True
                        logger.info(
                            f"Removed '{policy_key}' from metadata section '{section_key}'"
                        )
                # Remove the section if it's now empty
                if section_key in metadata and isinstance(metadata[section_key], dict) and not metadata[section_key]:
                    del metadata[section_key]
                    logger.info(f"Removed empty metadata section '{section_key}'")

        if updated:
            _atomic_write_text(
                metadata_file,
                yaml.safe_dump(metadata, default_flow_style=False),
            )
            logger.info(f"Successfully updated metadata file: {metadata_file}")
        else:
            logger.info("No matching entries found in metadata for cleaned repos")
        return True

    except Exception as e:
        logger.error(f"Failed to update metadata after cleanup: {e}")
        return False


def remove_repos_from_pulp_repo_file(cleaned_repos: List[str], pulp_repo_file: str,
                                     logger, cleanup_all: bool = False):
    """Remove cleaned repository stanzas from a yum repo file (pulp.repo).

    The pulp repo file is an INI-like file with sections such as:
        [repo_name]
        name=...
        baseurl=...

    For each repo in cleaned_repos, remove the entire stanza block.
    If the file becomes empty (no sections remain), remove the file.
    """
    if not pulp_repo_file or (not cleaned_repos and not cleanup_all):
        return True

    if not os.path.exists(pulp_repo_file):
        logger.info(f"pulp repo file not found: {pulp_repo_file}, skipping")
        return True

    try:
        if cleanup_all:
            os.remove(pulp_repo_file)
            logger.info(f"Removed Pulp repo file after complete RPM cleanup: {pulp_repo_file}")
            return True

        repo_names = {r.replace('-', '_') for r in cleaned_repos if isinstance(r, str) and r}
        if not repo_names:
            return True

        with open(pulp_repo_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split into sections keeping headers. Regex finds section headers like [name].
        header_re = re.compile(r'^\[([^\]]+)\]\s*$', re.MULTILINE)
        matches = list(header_re.finditer(content))
        if not matches:
            logger.info(f"No repo sections found in {pulp_repo_file}, skipping")
            return True

        kept_blocks: List[str] = []
        removed = 0
        found_normalized = set()
        for idx, m in enumerate(matches):
            section_name = m.group(1).strip()
            start = m.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
            block = content[start:end]

            # Section names in pulp.repo are expected to match Pulp distribution names.
            # Compare normalized (hyphens -> underscores) for safety.
            normalized_section = section_name.replace('-', '_')
            if normalized_section in repo_names:
                removed += 1
                found_normalized.add(normalized_section)
                logger.info(f"Removed repo stanza [{section_name}] from {pulp_repo_file}")
                continue

            kept_blocks.append(block.rstrip() + "\n\n")

        # Log repos that were cleaned but had no stanza in pulp.repo
        missing = repo_names - found_normalized
        for m_name in sorted(missing):
            logger.info(f"No stanza found for [{m_name}] in {pulp_repo_file} (repo had no distribution)")

        new_content = "".join(kept_blocks).strip() + "\n" if kept_blocks else ""
        if not new_content.strip():
            os.remove(pulp_repo_file)
            logger.info(f"Removed empty pulp repo file: {pulp_repo_file}")
            return True

        _atomic_write_text(pulp_repo_file, new_content)
        logger.info(f"Updated pulp repo file: {pulp_repo_file}")
        return True

    except PermissionError:
        logger.error(
            f"Permission denied while updating {pulp_repo_file}. Run with elevated privileges."
        )
        return False
    except Exception as e:
        logger.error(f"Failed to update {pulp_repo_file} after cleanup: {e}")
        return False


# =============================================================================
# MAIN MODULE
# =============================================================================

def run_module():
    """Main module execution."""
    module = AnsibleModule(
        argument_spec=dict(
            cleanup_repos=dict(type='list', elements='str', default=[]),
            cleanup_containers=dict(type='list', elements='str', default=[]),
            cleanup_files=dict(type='list', elements='str', default=[]),
            base_path=dict(
                type='str', default=CLEANUP_BASE_PATH_DEFAULT
            ),
            repo_store_path=dict(
                type='str', default=config.REPO_MANAGER_RUNTIME_DIR
            ),
            cluster_os_type=dict(
                type='str', required=True
            ),
            cluster_os_version=dict(
                type='str', required=True
            ),
            metadata_file=dict(
                type='str', required=False,
                default=os.path.join(config.REPO_MANAGER_OFFLINE_REPO_DIR, ".data", "localrepo_metadata.yml")
            ),
            pulp_repo_file=dict(
                type='str', required=False,
                default='/etc/yum.repos.d/pulp.repo'
            )
        ),
        # Destructive cleanup is intentionally skipped by Ansible check mode.
        # Claiming check-mode support without a complete dry-run path caused
        # real deletions during ``--check``.
        supports_check_mode=False
    )

    cleanup_repos = module.params['cleanup_repos']
    cleanup_containers = module.params['cleanup_containers']
    cleanup_files = module.params['cleanup_files']
    base_path = module.params['base_path']
    repo_store_path = module.params['repo_store_path']
    cluster_os_type = module.params['cluster_os_type']
    cluster_os_version = module.params['cluster_os_version']
    metadata_file = module.params['metadata_file']
    pulp_repo_file = module.params['pulp_repo_file']

    try:
        base_path = validate_cleanup_root(
            base_path, source_root=config.REPO_MANAGER_BASE_DIR
        )
        repo_store_path = validate_cleanup_root(
            repo_store_path, source_root=config.REPO_MANAGER_BASE_DIR
        )
        log_dir = validate_cleanup_child(
            base_path, cluster_os_type, cluster_os_version, "cleanup"
        )
    except ValueError as error:
        module.fail_json(msg=str(error))

    # Setup logger - setup_standard_logger expects a directory, creates standard.log inside
    os.makedirs(log_dir, exist_ok=True)
    logger = setup_standard_logger(log_dir)

    # Handle 'all' keyword for repositories
    cleanup_all_repos = (
        cleanup_repos and len(cleanup_repos) == 1 and
        cleanup_repos[0].lower() == 'all'
    )
    if cleanup_all_repos:
        logger.info("cleanup_repos='all' - fetching all repositories from Pulp")
        cleanup_repos = get_all_repositories(logger)
        if cleanup_repos is None:
            module.fail_json(
                msg="Failed to retrieve repository list from Pulp. "
                "Please check if Pulp services are running."
            )
        if not cleanup_repos:
            logger.info("No RPM repositories found in Pulp - nothing to cleanup")
        else:
            logger.info(f"Found {len(cleanup_repos)} repositories to cleanup: {cleanup_repos}")

    # Handle 'all' keyword for containers
    cleanup_all_containers = (
        cleanup_containers and len(cleanup_containers) == 1 and
        cleanup_containers[0].lower() == 'all'
    )
    if cleanup_all_containers:
        logger.info("cleanup_containers='all' - fetching all container repositories from Pulp")
        cleanup_containers = get_all_containers(logger)
        if cleanup_containers is None:
            module.fail_json(
                msg="Failed to retrieve container repository list from Pulp. "
                "Please check if Pulp services are running."
            )
        if not cleanup_containers:
            logger.info("No container repositories found in Pulp - nothing to cleanup")
        else:
            logger.info(f"Found {len(cleanup_containers)} containers to cleanup: {cleanup_containers}")

    resolution_errors = []

    # Handle file/Python cleanup and resolve bare names to exact repository
    # identities. This removes the previous substring/first-match behavior.
    cleanup_all_files = (
        cleanup_files and len(cleanup_files) == 1 and
        cleanup_files[0].lower() == 'all'
    )
    if cleanup_files:
        logger.info("Fetching File and Python repositories from Pulp")
        file_repos = get_all_file_repositories(logger)
        python_repos = get_all_python_repositories(logger)
        if file_repos is None or python_repos is None:
            module.fail_json(
                msg="Failed to retrieve file/Python repository list from Pulp. "
                "Please check if Pulp services are running."
            )
        known_file_repositories = file_repos + python_repos
        if cleanup_all_files:
            cleanup_files = known_file_repositories
        else:
            cleanup_files, resolution_errors = expand_cleanup_file_requests(
                cleanup_files, known_file_repositories
            )
        if not cleanup_files:
            logger.info("No file/Python repositories found in Pulp - nothing to cleanup")
        else:
            logger.info(f"Found {len(cleanup_files)} file repos to cleanup: {cleanup_files}")

    logger.info(
        f"Starting cleanup - repos: {cleanup_repos}, "
        f"containers: {cleanup_containers}, files: {cleanup_files}"
    )

    all_results = list(resolution_errors)

    # Process repositories
    repo_results = []
    for repo in cleanup_repos:
        result = cleanup_repository(repo, base_path, repo_store_path, logger)
        all_results.append(result)
        repo_results.append(result)
        if result['status'] == 'Success' or result.get('pulp_absent'):
            try:
                removed = remove_repo_from_mirror_index(
                    repo, base_path, cluster_os_type, cluster_os_version, logger)
                logger.info(f"Removed {removed} entries from pulp_mirror_index.json for repo '{repo}'")
            except Exception as error:
                all_results.append({
                    "name": repo,
                    "type": "local_state",
                    "status": "Failed",
                    "message": f"Pulp repository was removed but mirror tracking could not be updated: {error}",
                })
        logger.info(f"Repository {repo}: {result['status']} - {result['message']}")

    repo_all_complete = (
        cleanup_all_repos
        and all(item['status'] == 'Success' for item in repo_results)
    )
    if repo_all_complete:
        try:
            affected_by_arch: Dict[str, List[str]] = {}
            for rpm_type in ('rpm', 'rpm_repo', 'rpm_file'):
                affected = remove_all_from_status_files(
                    rpm_type, base_path, logger
                )
                for arch, software_names in affected.items():
                    affected_by_arch.setdefault(arch, [])
                    affected_by_arch[arch].extend(
                        name for name in software_names
                        if name not in affected_by_arch[arch]
                    )
            mark_software_partial(
                affected_by_arch, base_path, logger, 'repository'
            )
            for rpm_type in ('rpm', 'rpm_repo', 'rpm_file'):
                remove_all_type_from_mirror_index(
                    rpm_type, base_path, cluster_os_type,
                    cluster_os_version, logger
                )
            rpm_fs_result = cleanup_all_file_content_directories(
                repo_store_path, logger, content_types=('rpm_file',)
            )
            if rpm_fs_result['status'] != 'Success':
                raise RuntimeError(rpm_fs_result['message'])
        except Exception as error:
            all_results.append({
                "name": "all_rpm_state",
                "type": "local_state",
                "status": "Failed",
                "message": f"All Pulp RPM repositories were removed but local state cleanup failed: {error}",
            })

    # Process containers
    container_results = []
    for container in cleanup_containers:
        result = cleanup_container(container, base_path, logger)
        all_results.append(result)
        container_results.append(result)
        if result['status'] == 'Success' or result.get('pulp_absent'):
            try:
                if container.startswith("container_repo_"):
                    remove_container_repo_from_mirror_index(
                        container, base_path, cluster_os_type,
                        cluster_os_version, logger
                    )
                else:
                    remove_artifact_from_mirror_index(
                        container, 'image', base_path, cluster_os_type,
                        cluster_os_version, logger)
            except Exception as error:
                all_results.append({
                    "name": container,
                    "type": "local_state",
                    "status": "Failed",
                    "message": f"Pulp container was removed but mirror tracking could not be updated: {error}",
                })
        logger.info(f"Container {container}: {result['status']} - {result['message']}")

    # Bulk state cleanup is safe only after every discovered Pulp object was
    # verified absent. all([]) is intentional when Pulp contains no objects.
    container_all_complete = (
        cleanup_all_containers
        and all(item['status'] == 'Success' for item in container_results)
    )
    if container_all_complete:
        try:
            affected = remove_all_from_status_files('image', base_path, logger)
            mark_software_partial(affected, base_path, logger, 'container')
            remove_all_type_from_mirror_index(
                'image', base_path, cluster_os_type, cluster_os_version, logger)
        except Exception as error:
            all_results.append({
                "name": "all_container_state",
                "type": "local_state",
                "status": "Failed",
                "message": f"All Pulp containers were removed but local state cleanup failed: {error}",
            })

    # Process files
    file_results = []
    for file in cleanup_files:
        result = cleanup_file(file, base_path, repo_store_path, logger)
        all_results.append(result)
        file_results.append(result)
        if result['status'] == 'Success' or result.get('pulp_absent'):
            try:
                file_type = result.get('type', 'file')
                remove_artifact_from_mirror_index(
                    result['name'], file_type, base_path, cluster_os_type,
                    cluster_os_version, logger, arch=result.get('arch'),
                    os_version=result.get('os_version'))
            except Exception as error:
                all_results.append({
                    "name": result['name'],
                    "type": "local_state",
                    "status": "Failed",
                    "message": f"Pulp file repository was removed but mirror tracking could not be updated: {error}",
                })
        logger.info(f"File {file}: {result['status']} - {result['message']}")

    # If cleanup_files=all, bulk-remove all file-type entries from status files,
    # clean all local file content directories, and mark software partial
    file_all_complete = (
        cleanup_all_files
        and all(item['status'] == 'Success' for item in file_results)
    )
    if file_all_complete:
        try:
            affected_by_arch: Dict[str, List[str]] = {}
            for ftype in CLEANUP_FILE_TYPES:
                affected = remove_all_from_status_files(
                    ftype, base_path, logger
                )
                for arch, software_names in affected.items():
                    affected_by_arch.setdefault(arch, [])
                    affected_by_arch[arch].extend(
                        name for name in software_names
                        if name not in affected_by_arch[arch]
                    )
            mark_software_partial(
                affected_by_arch, base_path, logger, 'file'
            )
            for ftype in CLEANUP_FILE_TYPES:
                remove_all_type_from_mirror_index(
                    ftype, base_path, cluster_os_type, cluster_os_version, logger)
            file_fs_result = cleanup_all_file_content_directories(
                repo_store_path, logger
            )
            if file_fs_result['status'] != 'Success':
                raise RuntimeError(file_fs_result['message'])
        except Exception as error:
            all_results.append({
                "name": "all_file_state",
                "type": "local_state",
                "status": "Failed",
                "message": f"All Pulp file repositories were removed but local state cleanup failed: {error}",
            })

    # Update metadata file to remove entries for successfully cleaned repos
    cleaned_repo_names = [
        result['name'] for result in all_results
        if result.get('type') == 'repository'
        and (result['status'] == 'Success' or result.get('pulp_absent'))
    ]
    all_requested_repos_clean = repo_all_complete
    if (cleaned_repo_names or all_requested_repos_clean) and metadata_file:
        metadata_updated = update_metadata_after_cleanup(
            cleaned_repo_names, metadata_file, logger,
            cleanup_all=all_requested_repos_clean
        )
        if not metadata_updated:
            all_results.append({
                "name": metadata_file,
                "type": "local_state",
                "status": "Failed",
                "message": "Pulp objects were removed but repository metadata could not be updated",
            })

    # Update yum repo file (pulp.repo) to remove stanzas for successfully cleaned repositories
    if (cleaned_repo_names or all_requested_repos_clean) and pulp_repo_file:
        repo_file_updated = remove_repos_from_pulp_repo_file(
            cleaned_repo_names, pulp_repo_file, logger,
            cleanup_all=all_requested_repos_clean
        )
        if not repo_file_updated:
            all_results.append({
                "name": pulp_repo_file,
                "type": "local_state",
                "status": "Failed",
                "message": "Pulp objects were removed but pulp.repo could not be updated",
            })

    # Run orphan cleanup once after all deletions to reclaim disk space
    any_success = any(
        result['status'] == 'Success' or result.get('pulp_absent')
        for result in all_results
    )
    if any_success:
        logger.info("Running global orphan cleanup to reclaim disk space...")
        orphan_result = run_pulp(
            ["orphan", "cleanup", "--protection-time", "0"], logger
        )
        if orphan_result["rc"] == 0:
            logger.info("Orphan cleanup completed successfully")
        else:
            orphan_failure = {
                "name": "pulp_orphans",
                "type": "orphan_cleanup",
                "status": "Failed",
                "message": (
                    "Logical objects were deleted, but orphan cleanup failed: "
                    f"{orphan_result.get('stderr', '').strip()}"
                ),
            }
            all_results.append(orphan_failure)
            logger.error(orphan_failure["message"])

    # Write status file
    status_file = write_cleanup_status(all_results, log_dir)

    # Calculate summary
    total = len(all_results)
    success = len([r for r in all_results if r['status'] == 'Success'])
    failed = len([r for r in all_results if r['status'] == 'Failed'])

    # Generate pretty table
    pretty_table = format_pretty_table(all_results)

    logger.info(f"Cleanup completed - Total: {total}, Success: {success}, Failed: {failed}")

    response = dict(
        changed=success > 0,
        results=all_results,
        total=total,
        success_count=success,
        failed_count=failed,
        summary=f"Total: {total}, Success: {success}, Failed: {failed}",
        pretty_table=pretty_table,
        pretty_table_lines=pretty_table.split('\n'),
        status_file=status_file
    )
    if failed:
        module.fail_json(msg=response["summary"], **response)
    module.exit_json(**response)


if __name__ == '__main__':
    run_module()
