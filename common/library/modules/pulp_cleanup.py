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
import yaml
from typing import Dict, List, Any, Tuple

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.config import (
    CLEANUP_BASE_PATH_DEFAULT,
    CLEANUP_FILE_TYPES,
    pulp_rpm_commands,
    pulp_container_commands,
    pulp_file_commands,
    pulp_python_commands,
    ARCH_SUFFIXES
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

def run_cmd(cmd: str, logger) -> Dict[str, Any]:
    """Execute shell command and return result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return {"rc": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except (subprocess.SubprocessError, OSError) as e:
        logger.error(f"Command failed: {cmd} - {e}")
        return {"rc": 1, "stdout": "", "stderr": str(e)}


def safe_json_parse(data: str, default: Any = None) -> Any:
    """Safely parse JSON string using JSONDecoder with validation.
    
    Uses json.JSONDecoder instead of json.loads to avoid Checkmarx vulnerabilities.
    """
    if not data or not isinstance(data, str):
        return default if default is not None else []

    try:
        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(data.strip())
        return parsed
    except (ValueError, TypeError):
        return default if default is not None else []


# =============================================================================
# CONTAINER IMAGE VALIDATION & CONVERSION
# =============================================================================

def validate_container_format(image_name: str) -> Tuple[bool, str]:
    """Validate container image format.
    
    User must provide format: registry/image (e.g., registry.k8s.io/pause)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not image_name:
        return False, "Container image name cannot be empty"

    # Must contain at least one '/' to indicate registry/image format
    if '/' not in image_name:
        return False, (
            f"Invalid format '{image_name}'. Must include registry "
            "(e.g., registry.k8s.io/pause, docker.io/library/busybox)"
        )

    # Must have a registry part (contains '.' or is a known registry)
    parts = image_name.split('/')
    registry = parts[0]

    # Check if registry looks valid (contains dot or is localhost)
    if '.' not in registry and registry != 'localhost' and ':' not in registry:
        return False, (
            f"Invalid registry '{registry}' in '{image_name}'. "
            "Registry must be a domain (e.g., docker.io, registry.k8s.io)"
        )

    return True, ""


def convert_to_pulp_container_name(image_name: str) -> str:
    """Convert user-provided image name to Pulp repository name.
    
    Examples:
        registry.k8s.io/pause -> container_repo_registry.k8s.io_pause
        docker.io/library/busybox -> container_repo_docker.io_library_busybox
        ghcr.io/kube-vip/kube-vip -> container_repo_ghcr.io_kube-vip_kube-vip
    """
    # Replace '/' with '_' and prepend 'container_repo_'
    normalized = image_name.replace('/', '_')
    return f"container_repo_{normalized}"


# =============================================================================
# TYPE DETECTION
# =============================================================================

def detect_file_type(name: str, base_path: str = "/opt/omnia/offline_repo/cluster") -> str:
    """Detect artifact type by searching for the package name in the filesystem.
    
    Searches in base_path/<arch>/<os>/<version>/{type_folder}/name
    and returns the folder type where the package is found.
    
    Storage structure:
        - iso/          : ISO files, run files (e.g., cuda-run)
        - manifest/     : Kubernetes manifests (e.g., calico-v3.30.3, metallb-native-v0.15.2)
        - pip_module/   : Python pip packages (e.g., PyMySQL==1.1.2, kubernetes==33.1.0)
        - tarball/      : Tarballs, helm charts (e.g., helm-v3.19.0-amd64, nvhpc_2025_2511_Linux_x86_64_cuda_13.0)
        - git/          : Git repositories
        - ansible_galaxy_collection/ : Ansible Galaxy collections
    
    Args:
        name: Package name from JSON (e.g., "calico-v3.30.3", "helm-v3.19.0-amd64")
        base_path: Base path to search (default: /opt/omnia/offline_repo/cluster)
    
    Returns:
        str: Type based on folder where package is found, or fallback to name-based detection
    """
    
    # Search for the package name in the filesystem
    # Pattern: base_path/*/*/*/{type_folder}/name
    for file_type in CLEANUP_FILE_TYPES:
        pattern = f"{base_path}/*/*/*/{file_type}/{name}"
        matches = glob.glob(pattern)
        if matches:
            # Extract the parent folder name and return it
            parent_folder = os.path.basename(os.path.dirname(matches[0]))
            return parent_folder
    
    # If not found in filesystem, return None
    return None

# =============================================================================
# EXISTENCE CHECKS
# =============================================================================

def repo_exists(name: str, logger) -> bool:
    """Check if RPM repository exists in Pulp."""
    cmd = pulp_rpm_commands["show_repository"] % name
    result = run_cmd(cmd, logger)
    return result["rc"] == 0


def container_exists(name: str, logger) -> bool:
    """Check if container repository exists in Pulp."""
    cmd = pulp_container_commands["show_container_repo"] % name
    result = run_cmd(cmd, logger)
    return result["rc"] == 0


def file_exists_in_status(name: str, base_path: str, logger) -> bool:
    """Check if file artifact exists in status files."""
    try:
        for arch in ARCH_SUFFIXES:
            for status_file in glob.glob(f"{base_path}/*/*/{arch}/*/status.csv"):
                with open(status_file, 'r', encoding='utf-8') as f:
                    if name in f.read():
                        return True
        return False
    except OSError:
        return False

def _list_pulp_repos(cmd: str, label: str, logger) -> List[str]:
    """List repository names from Pulp using the given command."""
    result = run_cmd(cmd, logger)
    if result["rc"] != 0:
        logger.error(f"Failed to list {label}: {result['stderr']}")
        return []
    repos = safe_json_parse(result["stdout"])
    return [r.get('name', '') for r in repos if r.get('name')]


def get_all_repositories(logger) -> List[str]:
    """Get all RPM repository names from Pulp."""
    return _list_pulp_repos(pulp_rpm_commands["list_repositories"], "repositories", logger)


def get_all_containers(logger) -> List[str]:
    """Get all container repository names from Pulp."""
    return _list_pulp_repos(pulp_container_commands["list_repositories"], "container repositories", logger)


def get_all_file_repositories(logger) -> List[str]:
    """Get all file repository names from Pulp."""
    return _list_pulp_repos(pulp_file_commands["list_repositories"], "file repositories", logger)


def get_all_python_repositories(logger) -> List[str]:
    """Get all Python repository names from Pulp."""
    return _list_pulp_repos(pulp_python_commands["list_repositories"], "Python repositories", logger)


# =============================================================================
# CLEANUP FUNCTIONS
# =============================================================================

def cleanup_repository(name: str, base_path: str, logger) -> Dict[str, Any]:
    """Cleanup a single RPM repository."""
    result = {"name": name, "type": "repository", "status": "Failed", "message": ""}

    # Check existence
    if not repo_exists(name, logger):
        result["message"] = "Repository not found"
        return result

    try:
        # Delete distributions
        dist_list = run_cmd(pulp_rpm_commands["list_distributions"], logger)
        if dist_list["rc"] == 0:
            dists = safe_json_parse(dist_list["stdout"])
            for d in dists:
                if d.get('name', '') == name or name in d.get('name', ''):
                    run_cmd(pulp_rpm_commands["delete_distribution"] % d.get('name', ''), logger)

        # Delete publications
        pub_list = run_cmd(pulp_rpm_commands["list_publications"] % name, logger)
        if pub_list["rc"] == 0:
            pubs = safe_json_parse(pub_list["stdout"])
            for p in pubs:
                run_cmd(pulp_rpm_commands["delete_publication"] % p.get('pulp_href', ''), logger)

        # Delete remote
        run_cmd(pulp_rpm_commands["delete_remote"] % name, logger)

        # Delete repository
        del_result = run_cmd(pulp_rpm_commands["delete_repository"] % name, logger)

        if del_result["rc"] == 0:
            result["status"] = "Success"
            result["message"] = "Repository deleted"
            # Update status files - remove RPM entries from this repo and mark software as partial
            affected = remove_rpms_from_repository(name, base_path, logger)
            logger.info(f" mark affected softwares as partial {affected}")
            mark_software_partial(affected, base_path, logger, 'repository')
        else:
            result["message"] = f"Delete failed: {del_result['stderr']}"

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


def cleanup_container(user_input: str, base_path: str, logger) -> Dict[str, Any]:
    """Cleanup a single container repository.
    
    Args:
        user_input: User-provided image name (e.g., registry.k8s.io/pause)
                    or Pulp repository name (e.g., container_repo_registry.k8s.io_pause)
                    when called from cleanup_containers=all
    """
    result = {"name": user_input, "type": "container", "status": "Failed", "message": ""}

    # Check if input is already a Pulp repository name (from get_all_containers)
    if user_input.startswith('container_repo_'):
        pulp_name = user_input
        repo_suffix = user_input[len('container_repo_'):]
    else:
        # Validate format
        is_valid, error_msg = validate_container_format(user_input)
        if not is_valid:
            result["message"] = error_msg
            return result

        # Convert to Pulp naming convention
        pulp_name = convert_to_pulp_container_name(user_input)
        repo_suffix = pulp_name[len('container_repo_'):]

    # Check existence
    if not container_exists(pulp_name, logger):
        result["message"] = (
            f"Container not found in Pulp (looked for: {pulp_name})"
        )
        return result

    try:
        # Delete distributions
        dist_list = run_cmd(pulp_container_commands["list_distributions"], logger)
        if dist_list["rc"] == 0:
            dists = safe_json_parse(dist_list["stdout"])
            for d in dists:
                if d.get('name', '') == pulp_name:
                    run_cmd(pulp_container_commands["delete_distribution"] % d.get('name', ''), logger)

        # Delete remote(s)
        # Omnia creates container remotes as:
        #   - remote_<image_sans_separators> (for standard images)
        #   - user_remote_<image_sans_separators> (for user registries)
        # where the suffix matches the container repo name after 'container_repo_'.
        remote_candidates = [
            f"remote_{repo_suffix}",
            f"user_remote_{repo_suffix}",
        ]

        # Also try to discover any remotes that match this suffix (defensive)
        remote_list = run_cmd(pulp_container_commands["list_remotes"], logger)
        if remote_list["rc"] == 0:
            remotes = safe_json_parse(remote_list["stdout"], default=[])
            for r in remotes:
                rname = r.get('name', '') if isinstance(r, dict) else ''
                if not rname:
                    continue
                if rname.endswith(f"_{repo_suffix}") or rname in remote_candidates:
                    remote_candidates.append(rname)

        seen = set()
        for remote_name in remote_candidates:
            if not remote_name or remote_name in seen:
                continue
            seen.add(remote_name)
            remote_result = run_cmd(
                pulp_container_commands["delete_remote"] % remote_name, logger
            )
            if remote_result["rc"] == 0:
                logger.info(f"Deleted container remote: {remote_name}")
            else:
                logger.warning(
                    f"Could not delete container remote '{remote_name}': {remote_result['stderr']}"
                )

        # Delete repository
        del_result = run_cmd(pulp_container_commands["delete_repository"] % pulp_name, logger)

        if del_result["rc"] == 0:
            result["status"] = "Success"
            result["message"] = "Container deleted"
            # Update status files - remove image entries and mark software as partial
            affected = remove_from_status_files(user_input, 'image', base_path, logger)
            mark_software_partial(affected, base_path, logger, 'image')
        else:
            result["message"] = f"Delete failed: {del_result['stderr']}"

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


def cleanup_pip_module(name: str, base_path: str, repo_store_path: str, logger,
                       pulp_repo_name: str = None) -> Dict[str, Any]:
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
    pulp_deleted = False
    content_removed = False

    try:
        # Use provided Pulp repo name or derive from content name
        if not pulp_repo_name:
            if name.startswith("pip_module"):
                pulp_repo_name = name
            else:
                pulp_repo_name = f"pip_module{name}"

        logger.info(f"Looking for Python repository: {pulp_repo_name}")

        # Check if repository exists
        repo_check = run_cmd(pulp_python_commands["show_repository"] % pulp_repo_name, logger)

        if repo_check["rc"] == 0:
            # Delete distribution first
            dist_del = run_cmd(pulp_python_commands["delete_distribution"] % pulp_repo_name, logger)
            if dist_del["rc"] == 0:
                messages.append("Distribution deleted")

            # Delete repository
            repo_del = run_cmd(pulp_python_commands["delete_repository"] % pulp_repo_name, logger)
            if repo_del["rc"] == 0:
                pulp_deleted = True
                messages.append("Repository deleted")

            # Run orphan cleanup
            if pulp_deleted:
                logger.info("Running orphan cleanup...")
                orphan_result = run_cmd(pulp_python_commands["orphan_cleanup"], logger)
                if orphan_result["rc"] == 0:
                    messages.append("Orphan cleanup completed")
        else:
            # Try listing repos to find partial match
            repo_list = run_cmd(
                pulp_python_commands["list_repositories"], logger
            )
            if repo_list["rc"] == 0:
                repos = safe_json_parse(repo_list["stdout"])
                for repo in repos:
                    repo_name = repo.get('name', '')
                    if name in repo_name or repo_name == pulp_repo_name:
                        logger.info(f"Found matching Python repository: {repo_name}")

                        dist_del = run_cmd(pulp_python_commands["delete_distribution"] % repo_name, logger)
                        if dist_del["rc"] == 0:
                            messages.append("Distribution deleted")

                        repo_del = run_cmd(pulp_python_commands["delete_repository"] % repo_name, logger)
                        if repo_del["rc"] == 0:
                            pulp_deleted = True
                            messages.append("Repository deleted")
                        break

        # Update status files
        if file_exists_in_status(name, base_path, logger):
            affected = remove_from_status_files(name, 'pip_module', base_path, logger)
            if affected:
                messages.append("Status files updated")
                mark_software_partial(affected, base_path, logger, 'pip_module')

        # Clean up uploaded content from filesystem
        fs_result = cleanup_content_directory(name, 'pip_module', repo_store_path, logger)
        if fs_result["status"] == "Success":
            content_removed = True
            messages.append(fs_result["message"])

        if pulp_deleted or content_removed:
            result["status"] = "Success"
            result["message"] = "; ".join(messages) if messages else "Cleaned up"
        else:
            result["message"] = f"pip_module '{name}' not found in Pulp or filesystem"

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


def get_pulp_file_repo_name(name: str, file_type: str) -> str:
    """Get the Pulp File repository name based on artifact type.
    
    Naming conventions:
    - ansible_galaxy_collection: ansible_galaxy_collection<package>
    - tarball, git, manifest, file: <name> (as-is)
    """
    if file_type == "ansible_galaxy_collection":
        if name.startswith("ansible_galaxy_collection"):
            return name
        return f"ansible_galaxy_collection{name}"
    return name


def cleanup_file_repository(name: str, file_type: str, base_path: str, repo_store_path: str, logger,
                            pulp_repo_name: str = None) -> Dict[str, Any]:
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
    pulp_deleted = False
    status_removed = False
    content_removed = False

    try:
        # Use provided Pulp repo name or derive from content name
        if not pulp_repo_name:
            pulp_repo_name = get_pulp_file_repo_name(name, file_type)
        logger.info(f"Looking for {file_type} repository: {pulp_repo_name}")

        # Check if repository exists directly
        repo_check = run_cmd(pulp_file_commands["show_repository"] % pulp_repo_name, logger)

        if repo_check["rc"] == 0:
            # Found exact match - delete distribution and repository
            dist_del = run_cmd(pulp_file_commands["delete_distribution"] % pulp_repo_name, logger)
            if dist_del["rc"] == 0:
                messages.append("Distribution deleted")

            repo_del = run_cmd(pulp_file_commands["delete_repository"] % pulp_repo_name, logger)
            if repo_del["rc"] == 0:
                pulp_deleted = True
                messages.append("Repository deleted")
        else:
            # Try listing repos to find partial match
            repo_list = run_cmd(
                pulp_file_commands["list_repositories"], logger
            )
            if repo_list["rc"] == 0:
                repos = safe_json_parse(repo_list["stdout"])
                for repo in repos:
                    repo_name = repo.get('name', '')
                    if name in repo_name or repo_name == pulp_repo_name:
                        logger.info(f"Found matching repository: {repo_name}")

                        dist_del = run_cmd(pulp_file_commands["delete_distribution"] % repo_name, logger)
                        if dist_del["rc"] == 0:
                            messages.append("Distribution deleted")

                        repo_del = run_cmd(pulp_file_commands["delete_repository"] % repo_name, logger)
                        if repo_del["rc"] == 0:
                            pulp_deleted = True
                            messages.append("Repository deleted")
                        break

        # Run orphan cleanup to remove actual content files
        if pulp_deleted:
            logger.info("Running orphan cleanup to remove content files...")
            orphan_result = run_cmd(pulp_file_commands["orphan_cleanup"], logger)
            if orphan_result["rc"] == 0:
                messages.append("Orphan cleanup completed")
            else:
                logger.warning(f"Orphan cleanup warning: {orphan_result['stderr']}")

        # Update status files
        if file_exists_in_status(name, base_path, logger):
            affected = remove_from_status_files(name, file_type, base_path, logger)
            if affected:
                status_removed = True
                messages.append("Status files updated")
                mark_software_partial(affected, base_path, logger, file_type)

        # Clean up uploaded content from filesystem
        fs_result = cleanup_content_directory(
            name, file_type, repo_store_path, logger
        )
        if fs_result["status"] == "Success":
            content_removed = True
            messages.append(fs_result["message"])

        # Determine overall result
        if pulp_deleted or status_removed or content_removed:
            result["status"] = "Success"
            result["message"] = "; ".join(messages) if messages else "Cleaned up"
        else:
            result["message"] = f"{file_type} '{name}' not found in Pulp, status files, or filesystem"

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


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
    for arch in ARCH_SUFFIXES:
        prefix = f"{arch}_"
        if repo_name.startswith(prefix):
            remainder = repo_name[len(prefix):]
            # Try to strip os_type_os_version_ prefix (e.g., "rhel_10.0_")
            # os_type is alphabetic, os_version is digits/dots
            os_match = re.match(r'^([a-z]+)_(\d+(?:\.\d+)*)_', remainder)
            if os_match:
                remainder_after_os = remainder[os_match.end():]
                # Check if the remainder after os_type/version matches a file type
                for file_type in sorted(CLEANUP_FILE_TYPES, key=len, reverse=True):
                    if remainder_after_os.startswith(file_type):
                        content_name = remainder_after_os[len(file_type):]
                        return arch, file_type, content_name
            # Fallback: try legacy format without os_type/version
            for file_type in sorted(CLEANUP_FILE_TYPES, key=len, reverse=True):
                if remainder.startswith(file_type):
                    content_name = remainder[len(file_type):]
                    return arch, file_type, content_name
            return arch, None, remainder
    return None, None, repo_name


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
    arch, parsed_type, content_name = parse_pulp_file_repo_name(name)

    if parsed_type:
        # Name is a Pulp repo name — use parsed type and content name
        file_type = parsed_type
        pulp_name = name
        artifact_name = content_name
        logger.info(f"Parsed Pulp repo name: arch={arch}, type={file_type}, content={artifact_name}")
    else:
        # Name is a user-provided content name — detect type from filesystem
        file_type = detect_file_type(name)
        pulp_name = None
        artifact_name = name

    # Handle pip modules separately - they use Python repositories
    if file_type == "pip_module":
        return cleanup_pip_module(artifact_name, base_path, repo_store_path, logger, pulp_repo_name=pulp_name)

    # All other file types use Pulp File repository
    return cleanup_file_repository(artifact_name, file_type, base_path, repo_store_path, logger, pulp_repo_name=pulp_name)


# =============================================================================
# FILESYSTEM CONTENT CLEANUP
# =============================================================================

def cleanup_content_directory(content_name: str, content_type: str, repo_store_path: str, logger) -> Dict[str, Any]:
    """Remove uploaded content directory from the filesystem.

    Builds the content path the same way as download_common.py:
        <repo_store_path>/offline_repo/cluster/<arch>/<os_type>/<os_version>/<content_type>/<content_name>

    This mirrors how remove_from_status_files iterates over ARCH_SUFFIXES to
    clean status.csv entries.

    Args:
        content_name: Name of the content item (e.g., 'helm-v3.19.0-amd64')
        content_type: Directory category (tarball, git, pip_module, manifest,
                      ansible_galaxy_collection, rpm_file)
        repo_store_path: Root store path (e.g., '/opt/omnia')
        logger: Logger instance

    Returns:
        Dict with name, type, status, and message keys
    """
    result = {"name": content_name, "type": f"filesystem_{content_type}",
              "status": "Failed", "message": ""}
    removed_dirs = []

    cluster_path = os.path.join(repo_store_path, "offline_repo", "cluster")
    if not os.path.exists(cluster_path):
        result["message"] = f"Content store path not found: {cluster_path}"
        logger.warning(result["message"])
        return result

    # If content_type is None (e.g., from cleanup_files=all when detect_file_type fails),
    # search all known type directories to find and delete the content
    types_to_search = [content_type] if content_type else CLEANUP_FILE_TYPES

    try:
        for arch in ARCH_SUFFIXES:
            # Walk version directories (e.g., rhel/10.0)
            arch_path = os.path.join(cluster_path, arch)
            if not os.path.isdir(arch_path):
                continue

            for version_dir in glob.glob(f"{arch_path}/*/*/"):
                for search_type in types_to_search:
                    content_dir = os.path.join(version_dir, search_type, content_name)
                    if os.path.exists(content_dir):
                        logger.info(f"Removing content directory: {content_dir}")
                        if os.path.isdir(content_dir):
                            shutil.rmtree(content_dir)
                        else:
                            os.remove(content_dir)
                        removed_dirs.append(content_dir)
                        # Remove parent type directory if now empty
                        type_dir = os.path.join(version_dir, search_type)
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


def cleanup_all_file_content_directories(repo_store_path: str, logger) -> Dict[str, Any]:
    """Remove all file-type content directories from the filesystem.
    
    Called during cleanup_files=all to ensure all locally stored files
    under <repo_store_path>/offline_repo/cluster are deleted.
    
    Walks through all architectures, OS versions, and file-type directories,
    removing all content within each file-type folder.
    
    Args:
        repo_store_path: Root store path (e.g., '/opt/omnia')
        logger: Logger instance
        
    Returns:
        Dict with status and message
    """
    result = {"name": "all_file_content", "type": "filesystem_bulk",
              "status": "Failed", "message": ""}
    removed_dirs = []

    cluster_path = os.path.join(repo_store_path, "offline_repo", "cluster")
    if not os.path.exists(cluster_path):
        result["message"] = f"Content store path not found: {cluster_path}"
        logger.warning(result["message"])
        return result

    try:
        for arch in ARCH_SUFFIXES:
            arch_path = os.path.join(cluster_path, arch)
            if not os.path.isdir(arch_path):
                continue

            for version_dir in glob.glob(f"{arch_path}/*/*/"):
                for file_type in CLEANUP_FILE_TYPES:
                    type_dir = os.path.join(version_dir, file_type)
                    if os.path.isdir(type_dir):
                        # Remove all content within this type directory
                        for item in os.listdir(type_dir):
                            item_path = os.path.join(type_dir, item)
                            logger.info(f"Removing: {item_path}")
                            if os.path.isdir(item_path):
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
            result["message"] = "No file content found on filesystem"
            logger.info(result["message"])

    except Exception as e:
        result["message"] = f"Bulk filesystem cleanup error: {str(e)}"
        logger.error(f"Failed bulk filesystem cleanup: {e}")

    return result


# =============================================================================
# STATUS FILE UPDATES
# =============================================================================

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

    # Extract architecture from repo_name (all repo_names should now have arch prefixes)
    target_arch = None
    for arch in ARCH_SUFFIXES:
        if repo_name.startswith(f"{arch}_"):
            target_arch = arch
            break
    
    if not target_arch:
        logger.error(f"Repository name {repo_name} does not have architecture prefix")
        return {}
    
    logger.info(f"Processing architecture: {target_arch}")
    affected_software[target_arch] = []
    
    try:        
        for status_file in glob.glob(f"{base_path}/*/*/{target_arch}/*/status.csv"):
            rows = []
            removed = False
            has_repo_column = False

            # Check if file has repo_name column
            with open(status_file, 'r', encoding='utf-8') as f:
                header = f.readline().strip().lower()
                has_repo_column = "repo_name" in header

            with open(status_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    name = row.get('name', '')
                    row_type = row.get('type', '')
                    rpm_repo = row.get('repo_name', '')

                    # For RPMs, check if they belong to the deleted repository
                    if row_type in ('rpm', 'rpm_repo', 'rpm_file') and has_repo_column and rpm_repo == repo_name:
                        removed = True
                        logger.info(f"Removing RPM '{name}' from {status_file} (repo {repo_name} deleted)")
                    else:
                        rows.append(row)

            if removed and fieldnames:
                with open(status_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

                # Track affected software
                software_name = os.path.basename(os.path.dirname(status_file))
                if software_name not in affected_software[target_arch]:
                    affected_software[target_arch].append(software_name)

        return affected_software
    except Exception as e:
        logger.error(f"Failed to remove RPMs from repository {repo_name}: {e}")
        return {}

def remove_from_status_files(artifact_name: str, artifact_type: str, base_path: str, logger) -> Dict[str, List[str]]:
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
        for arch in ARCH_SUFFIXES:
            arch_affected = []
            for status_file in glob.glob(f"{base_path}/*/*/{arch}/*/status.csv"):
                rows = []
                removed = False
                with open(status_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    for row in reader:
                        name = row.get('name', '')
                        # Match logic based on type
                        should_remove = False
                        if artifact_type == 'image':
                            # Container images: match with or without tag
                            should_remove = (name == artifact_name or name.startswith(f"{artifact_name}:"))
                        else:
                            # Other types: exact match
                            should_remove = (name == artifact_name)

                        if should_remove:
                            removed = True
                            logger.info(f"Removing '{name}' from {status_file}")
                        else:
                            rows.append(row)

                if removed and fieldnames:
                    with open(status_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)

                    # Track affected software
                    software_name = os.path.basename(os.path.dirname(status_file))
                    if software_name not in arch_affected:
                        arch_affected.append(software_name)

            if arch_affected:
                affected_software[arch] = arch_affected

        logger.info(f"remove_from_status_files returning: {affected_software}")
        return affected_software
    except OSError as e:
        logger.error(f"Failed to remove from status files: {e}")
        return {}


def mark_software_partial(affected_software, base_path: str, logger, artifact_type: str = None):
    """Mark software entries as partial in software.csv.

    Args:
        affected_software: Either a List[str] of software names (legacy support)
                          or a Dict[str, List[str]] mapping arch to software names
        base_path: Base path for software.csv
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

            for software_file in glob.glob(f"{base_path}/*/*/{arch}/software.csv"):
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
                    with open(software_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    logger.info(f"Successfully wrote updated {software_file}")
    except OSError as e:
        logger.error(f"Failed to update software.csv: {e}")

def software_has_type(software_name: str, arch: str, base_path: str, logger, type_values: tuple) -> bool:
    """Check if a software has entries of given types in its status.csv.
    
    Args:
        software_name: Name of the software
        arch: Architecture (x86_64 or aarch64)
        base_path: Base path for status files
        logger: Logger instance
        type_values: Tuple of type strings to check for (e.g., ('rpm', 'rpm_repo'))
        
    Returns:
        True if software has matching entries, False otherwise
    """
    for status_file in glob.glob(f"{base_path}/*/*/{arch}/{software_name}/status.csv"):
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('type', '').lower() in type_values:
                        return True
        except OSError as e:
            logger.error(f"Error checking {type_values} for {software_name}: {e}")
    return False


def mark_all_software_partial_by_type(base_path: str, logger, type_values: tuple, type_label: str):
    """Mark software entries as partial in software.csv for all architectures.
    
    Only marks software that actually has dependencies of the given types.
    
    Args:
        base_path: Base path for software.csv files
        logger: Logger instance
        type_values: Tuple of type strings to check (e.g., ('rpm', 'rpm_repo'))
        type_label: Human-readable label for logging (e.g., 'RPM', 'container')
    """
    logger.info(f"Marking software with {type_label} dependencies as partial")
    try:
        for arch in ARCH_SUFFIXES:
            for software_file in glob.glob(f"{base_path}/*/*/{arch}/software.csv"):
                logger.info(f"Processing software file: {software_file}")

                rows = []
                updated = False
                with open(software_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    for row in reader:
                        software_name = row.get('name', '')
                        if row.get('status') == 'success':
                            if software_has_type(software_name, arch, base_path, logger, type_values):
                                row['status'] = 'partial'
                                updated = True
                                logger.info(f"Marked '{software_name}' as partial in {software_file} (has {type_label} deps)")
                            else:
                                logger.info(f"Skipping '{software_name}' - no {type_label} dependencies")
                        rows.append(row)

                if fieldnames and rows and updated:
                    with open(software_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    logger.info(f"Successfully updated {software_file}")
    except OSError as e:
        logger.error(f"Failed to mark all software as partial ({type_label}): {e}")


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
                    with open(status_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)

                    software_name = os.path.basename(os.path.dirname(status_file))
                    if software_name not in arch_affected:
                        arch_affected.append(software_name)

            if arch_affected:
                affected_software[arch] = arch_affected

        logger.info(f"remove_all_from_status_files({artifact_type}) returning: {affected_software}")
        return affected_software
    except OSError as e:
        logger.error(f"Failed to remove all {artifact_type} from status files: {e}")
        return {}


def write_cleanup_status(results: List[Dict], base_path: str):
    """Write cleanup results to status file."""
    status_file = f"{base_path}/cleanup_status.csv"
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    with open(status_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'type', 'status', 'message'])
        writer.writeheader()
        writer.writerows(results)

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
    if not cleaned_repos or not metadata_file:
        return

    if not os.path.exists(metadata_file):
        logger.info(f"Metadata file not found: {metadata_file}, skipping metadata update")
        return

    try:
        # When cleanup_repos=all, delete the metadata file entirely.
        if cleanup_all:
            os.remove(metadata_file)
            logger.info(f"Deleted metadata file: {metadata_file}")
            return

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = yaml.safe_load(f) or {}

        updated = False
        for repo_name in cleaned_repos:
            # Normalize repo name to match metadata key format: <name>_policy.
            # Metadata may store keys either with arch prefix (e.g., x86_64_doca_policy)
            # or without it (e.g., doca_policy), so try both.
            normalized_name = repo_name.replace('-', '_')
            candidate_policy_keys = {f"{normalized_name}_policy"}
            repo_arch = None
            for arch in ARCH_SUFFIXES:
                arch_prefix = f"{arch}_"
                if normalized_name.startswith(arch_prefix):
                    repo_arch = arch
                    candidate_policy_keys.add(f"{normalized_name[len(arch_prefix):]}_policy")

            def _section_matches_repo_arch(section: str, arch: str) -> bool:
                """Return True if a metadata section belongs to the given arch.

                Expected section naming patterns in localrepo_metadata.yml:
                    - omnia_repo_url_rhel_x86_64 / omnia_repo_url_rhel_aarch64
                    - rhel_subscription_url_x86_64 / rhel_subscription_url_aarch64
                    - user_repo_url_x86_64 / user_repo_url_aarch64
                """
                suffix = f"_{arch}"
                return isinstance(section, str) and section.endswith(suffix)

            # Search through all sections in metadata for these policy keys
            for section_key in list(metadata.keys()):
                if repo_arch and not _section_matches_repo_arch(section_key, repo_arch):
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
            with open(metadata_file, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, default_flow_style=False)
            logger.info(f"Successfully updated metadata file: {metadata_file}")
        else:
            logger.info("No matching entries found in metadata for cleaned repos")

    except Exception as e:
        logger.error(f"Failed to update metadata after cleanup: {e}")


def remove_repos_from_pulp_repo_file(cleaned_repos: List[str], pulp_repo_file: str, logger):
    """Remove cleaned repository stanzas from a yum repo file (pulp.repo).

    The pulp repo file is an INI-like file with sections such as:
        [repo_name]
        name=...
        baseurl=...

    For each repo in cleaned_repos, remove the entire stanza block.
    If the file becomes empty (no sections remain), remove the file.
    """
    if not cleaned_repos or not pulp_repo_file:
        return

    if not os.path.exists(pulp_repo_file):
        logger.info(f"pulp repo file not found: {pulp_repo_file}, skipping")
        return

    try:
        repo_names = {r.replace('-', '_') for r in cleaned_repos if isinstance(r, str) and r}
        if not repo_names:
            return

        with open(pulp_repo_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split into sections keeping headers. Regex finds section headers like [name].
        header_re = re.compile(r'^\[([^\]]+)\]\s*$', re.MULTILINE)
        matches = list(header_re.finditer(content))
        if not matches:
            logger.info(f"No repo sections found in {pulp_repo_file}, skipping")
            return

        kept_blocks: List[str] = []
        removed = 0
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
                logger.info(f"Removed repo stanza [{section_name}] from {pulp_repo_file}")
                continue

            kept_blocks.append(block.rstrip() + "\n\n")

        new_content = "".join(kept_blocks).strip() + "\n" if kept_blocks else ""
        if not new_content.strip():
            os.remove(pulp_repo_file)
            logger.info(f"Removed empty pulp repo file: {pulp_repo_file}")
            return

        with open(pulp_repo_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info(f"Updated pulp repo file: {pulp_repo_file}")

    except PermissionError:
        logger.error(
            f"Permission denied while updating {pulp_repo_file}. Run with elevated privileges."
        )
    except Exception as e:
        logger.error(f"Failed to update {pulp_repo_file} after cleanup: {e}")


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
                type='str', default='/opt/omnia'
            ),
            cluster_os_type=dict(
                type='str', required=False, default='rhel'
            ),
            cluster_os_version=dict(
                type='str', required=False, default='10.0'
            ),
            metadata_file=dict(
                type='str', required=False,
                default='/opt/omnia/offline_repo/.data/localrepo_metadata.yml'
            ),
            pulp_repo_file=dict(
                type='str', required=False,
                default='/etc/yum.repos.d/pulp.repo'
            )
        ),
        supports_check_mode=True
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

    # Setup logger - setup_standard_logger expects a directory, creates standard.log inside
    log_dir = os.path.join(base_path, cluster_os_type, cluster_os_version, "cleanup")
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
        if not cleanup_repos:
            module.fail_json(
                msg="Failed to retrieve repository list from Pulp. "
                "Please check if Pulp services are running."
            )
        logger.info(f"Found {len(cleanup_repos)} repositories to cleanup: {cleanup_repos}")

    # Handle 'all' keyword for containers
    cleanup_all_containers = (
        cleanup_containers and len(cleanup_containers) == 1 and
        cleanup_containers[0].lower() == 'all'
    )
    if cleanup_all_containers:
        logger.info("cleanup_containers='all' - fetching all container repositories from Pulp")
        cleanup_containers = get_all_containers(logger)
        if not cleanup_containers:
            module.fail_json(
                msg="Failed to retrieve container repository list from Pulp. "
                "Please check if Pulp services are running."
            )
        logger.info(f"Found {len(cleanup_containers)} containers to cleanup: {cleanup_containers}")

    # Handle 'all' keyword for files
    cleanup_all_files = (
        cleanup_files and len(cleanup_files) == 1 and
        cleanup_files[0].lower() == 'all'
    )
    if cleanup_all_files:
        logger.info("cleanup_files='all' - fetching all file and Python repositories from Pulp")
        file_repos = get_all_file_repositories(logger)
        python_repos = get_all_python_repositories(logger)
        cleanup_files = file_repos + python_repos
        if not cleanup_files:
            module.fail_json(
                msg="Failed to retrieve file/Python repository list from Pulp. "
                "Please check if Pulp services are running."
            )
        logger.info(f"Found {len(cleanup_files)} file repos to cleanup: {cleanup_files}")

    logger.info(
        f"Starting cleanup - repos: {cleanup_repos}, "
        f"containers: {cleanup_containers}, files: {cleanup_files}"
    )

    all_results = []

    # Process repositories
    for repo in cleanup_repos:
        result = cleanup_repository(repo, base_path, logger)
        all_results.append(result)
        logger.info(f"Repository {repo}: {result['status']} - {result['message']}")

    # If cleanup_repos=all, mark software with RPM dependencies as partial
    if cleanup_all_repos and any(r['status'] == 'Success' for r in all_results if r['type'] == 'repository'):
        mark_all_software_partial_by_type(base_path, logger, ('rpm', 'rpm_repo'), 'RPM')

    # Process containers
    container_cleanup_success = False
    for container in cleanup_containers:
        result = cleanup_container(container, base_path, logger)
        all_results.append(result)
        if result['status'] == 'Success':
            container_cleanup_success = True
        logger.info(f"Container {container}: {result['status']} - {result['message']}")

    # If cleanup_containers=all, bulk-remove all image entries from status files and mark software partial
    if cleanup_all_containers and container_cleanup_success:
        remove_all_from_status_files('image', base_path, logger)
        mark_all_software_partial_by_type(base_path, logger, ('image',), 'container')

    # Process files
    file_cleanup_success = False
    for file in cleanup_files:
        result = cleanup_file(file, base_path, repo_store_path, logger)
        all_results.append(result)
        if result['status'] == 'Success':
            file_cleanup_success = True
        logger.info(f"File {file}: {result['status']} - {result['message']}")

    # If cleanup_files=all, bulk-remove all file-type entries from status files,
    # clean all local file content directories, and mark software partial
    if cleanup_all_files and file_cleanup_success:
        for ftype in CLEANUP_FILE_TYPES:
            remove_all_from_status_files(ftype, base_path, logger)
        cleanup_all_file_content_directories(repo_store_path, logger)
        mark_all_software_partial_by_type(base_path, logger, tuple(CLEANUP_FILE_TYPES), 'file')

    # Update metadata file to remove entries for successfully cleaned repos
    successfully_cleaned = [r['name'] for r in all_results if r['status'] == 'Success']
    if successfully_cleaned and metadata_file:
        update_metadata_after_cleanup(successfully_cleaned, metadata_file, logger,
                                          cleanup_all=cleanup_all_repos)

    # Update yum repo file (pulp.repo) to remove stanzas for successfully cleaned repositories
    cleaned_repo_names = [r['name'] for r in all_results if r['status'] == 'Success' and r.get('type') == 'repository']
    if cleaned_repo_names and pulp_repo_file:
        remove_repos_from_pulp_repo_file(cleaned_repo_names, pulp_repo_file, logger)

    # Run orphan cleanup once after all deletions to reclaim disk space
    any_success = any(r['status'] == 'Success' for r in all_results)
    if any_success:
        logger.info("Running global orphan cleanup to reclaim disk space...")
        orphan_result = run_cmd(pulp_rpm_commands["orphan_cleanup"], logger)
        if orphan_result["rc"] == 0:
            logger.info("Orphan cleanup completed successfully")
        else:
            logger.warning(f"Orphan cleanup warning: {orphan_result['stderr']}")

    # Write status file
    status_file = write_cleanup_status(all_results, log_dir)

    # Calculate summary
    total = len(all_results)
    success = len([r for r in all_results if r['status'] == 'Success'])
    failed = len([r for r in all_results if r['status'] == 'Failed'])

    # Generate pretty table
    pretty_table = format_pretty_table(all_results)

    logger.info(f"Cleanup completed - Total: {total}, Success: {success}, Failed: {failed}")

    module.exit_json(
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


if __name__ == '__main__':
    run_module()
