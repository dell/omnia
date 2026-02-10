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
import subprocess
from typing import Dict, List, Any, Tuple

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.config import (
    CLEANUP_BASE_PATH_DEFAULT,
    CLEANUP_STATUS_FILE_PATH_DEFAULT,
    pulp_rpm_commands,
    pulp_container_commands,
    pulp_file_commands,
    pulp_python_commands,
    ARCH_SUFFIXES
)


# =============================================================================
# PRETTY TABLE FORMATTING
# =============================================================================

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

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
            #f" {colored_status}{status_padding} ",
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
        return False, f"Invalid format '{image_name}'. Must include registry (e.g., registry.k8s.io/pause, docker.io/library/busybox)"

    # Must have a registry part (contains '.' or is a known registry)
    parts = image_name.split('/')
    registry = parts[0]

    # Check if registry looks valid (contains dot or is localhost)
    if '.' not in registry and registry != 'localhost' and ':' not in registry:
        return False, f"Invalid registry '{registry}' in '{image_name}'. Registry must be a domain (e.g., docker.io, registry.k8s.io)"

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

def detect_file_type(name: str) -> str:
    """Detect artifact type from name."""
    # Pip module: contains == (e.g., cffi==1.17.1)
    if '==' in name:
        return "pip_module"
    # Ansible Galaxy collection: contains . but no / or == (e.g., community.general, ansible.posix)
    if '.' in name and '/' not in name and '==' not in name and any(x in name.lower() for x in ['ansible', 'community', 'galaxy']):
        return "ansible_galaxy_collection"
    if name.startswith('ansible_galaxy_collection'):
        return "ansible_galaxy_collection"
    if any(x in name.lower() for x in ['chart', 'tar', 'tgz', 'helm', 'bundle']):
        return "tarball"
    if any(x in name.lower() for x in ['git', 'repo', 'source', 'scm']):
        return "git"
    if any(x in name.lower() for x in ['manifest', 'calico', 'yml', 'yaml']):
        return "manifest"
    return "file"


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
        for status_file in glob.glob(f"{base_path}/x86_64/*/status.csv"):
            with open(status_file, 'r', encoding='utf-8') as f:
                if name in f.read():
                    return True
        return False
    except Exception:
        return False

def get_all_repositories(logger) -> List[str]:
    """Get all RPM repository names from Pulp."""
    cmd = pulp_rpm_commands["list_repositories"]
    result = run_cmd(cmd, logger)
    if result["rc"] != 0:
        logger.error(f"Failed to list repositories: {result['stderr']}")
        return []
    repos = safe_json_parse(result["stdout"])
    return [r.get('name', '') for r in repos if r.get('name')]


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
    """
    result = {"name": user_input, "type": "container", "status": "Failed", "message": ""}

    # Validate format
    is_valid, error_msg = validate_container_format(user_input)
    if not is_valid:
        result["message"] = error_msg
        return result

    # Convert to Pulp naming convention
    pulp_name = convert_to_pulp_container_name(user_input)

    # Check existence
    if not container_exists(pulp_name, logger):
        result["message"] = f"Container not found in Pulp (looked for: {pulp_name})"
        return result

    try:
        # Delete distributions
        dist_list = run_cmd(pulp_container_commands["list_distributions"], logger)
        if dist_list["rc"] == 0:
            dists = safe_json_parse(dist_list["stdout"])
            for d in dists:
                if d.get('name', '') == pulp_name:
                    run_cmd(pulp_container_commands["delete_distribution"] % d.get('name', ''), logger)

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


def file_exists_in_pulp(name: str, logger) -> Tuple[bool, str, str]:
    """Check if file content exists in Pulp file repository.
    
    Returns:
        Tuple of (exists, repo_name, content_href)
    """
    try:
        # List file repositories and search for the content
        repo_list = run_cmd(pulp_file_commands["list_repositories"], logger)
        if repo_list["rc"] != 0:
            return False, "", ""

        repos = safe_json_parse(repo_list["stdout"])
        for repo in repos:
            repo_name = repo.get('name', '')
            # Check if this repo contains our file
            content_list = run_cmd(
                f"pulp file content list --repository {repo_name} --relative-path '{name}'",
                logger
            )
            if content_list["rc"] == 0:
                contents = safe_json_parse(content_list["stdout"])
                if contents:
                    return True, repo_name, contents[0].get('pulp_href', '')

        return False, "", ""
    except (OSError, ValueError):
        return False, "", ""


def delete_file_from_pulp(name: str, repo_name: str, content_href: str, logger) -> Tuple[bool, str]:
    """Delete file content from Pulp.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        messages = []

        # 1. Remove content from repository
        if content_href:
            remove_result = run_cmd(
                f"pulp file repository content remove --repository {repo_name} --href {content_href}",
                logger
            )
            if remove_result["rc"] == 0:
                messages.append("Content removed from repository")
            else:
                # Try alternative: modify repository to remove content
                run_cmd(
                    f"pulp file repository content modify --repository {repo_name} --remove-content '[{{\"pulp_href\": \"{content_href}\"}}]'",
                    logger
                )

        # 2. Delete distribution if exists
        dist_result = run_cmd(pulp_file_commands["list_distributions"], logger)
        if dist_result["rc"] == 0:
            dists = safe_json_parse(dist_result["stdout"])
            for d in dists:
                if d.get('name', '') == name or name in d.get('name', ''):
                    run_cmd(pulp_file_commands["delete_distribution"] % d.get('name', ''), logger)
                    messages.append("Distribution deleted")

        # 3. Try to delete the file repository if it's named after the artifact
        repo_del = run_cmd(pulp_file_commands["delete_repository"] % name, logger)
        if repo_del["rc"] == 0:
            messages.append("Repository deleted")

        return True, "; ".join(messages) if messages else "Removed from Pulp"

    except Exception as e:
        return False, f"Pulp deletion error: {str(e)}"


def cleanup_pip_module(name: str, base_path: str, logger) -> Dict[str, Any]:
    """Cleanup a pip module from Pulp Python repository.
    
    Pip modules are stored as: pip_module<package_name>==<version>
    e.g., pip_modulecffi==1.17.1
    """
    result = {"name": name, "type": "pip_module", "status": "Failed", "message": ""}
    messages = []
    pulp_deleted = False

    try:
        # Pulp Python repo name format: pip_module<name>
        # User input could be "cffi==1.17.1" or "pip_modulecffi==1.17.1"
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
            repo_list = run_cmd(pulp_python_commands["list_repositories"], logger)
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

        if pulp_deleted:
            result["status"] = "Success"
            result["message"] = "; ".join(messages) if messages else "Cleaned up"
        else:
            result["message"] = f"pip_module '{name}' not found in Pulp"

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


def cleanup_file_repository(name: str, file_type: str, base_path: str, logger) -> Dict[str, Any]:
    """Cleanup artifact from Pulp File repository.
    
    Handles: tarball, git, manifest, ansible_galaxy_collection
    All use 'pulp file' repository type with type-specific naming conventions.
    """
    result = {"name": name, "type": file_type, "status": "Failed", "message": ""}
    messages = []
    pulp_deleted = False
    status_removed = False

    try:
        # Get the expected Pulp repository name
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
            repo_list = run_cmd(pulp_file_commands["list_repositories"], logger)
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

        # Determine overall result
        if pulp_deleted or status_removed:
            result["status"] = "Success"
            result["message"] = "; ".join(messages) if messages else "Cleaned up"
        else:
            result["message"] = f"{file_type} '{name}' not found in Pulp or status files"

    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


def cleanup_file(name: str, base_path: str, logger) -> Dict[str, Any]:
    """Cleanup a file artifact.
    
    Routes to appropriate handler:
    - pip_module: Pulp Python repository
    - tarball, git, manifest, ansible_galaxy_collection: Pulp File repository
    """
    file_type = detect_file_type(name)

    # Handle pip modules separately - they use Python repositories
    if file_type == "pip_module":
        return cleanup_pip_module(name, base_path, logger)

    # All other file types use Pulp File repository
    return cleanup_file_repository(name, file_type, base_path, logger)


# =============================================================================
# STATUS FILE UPDATES
# =============================================================================

def remove_rpms_from_repository(repo_name: str, base_path: str, logger) -> List[str]:
    """Remove RPMs that belong to a specific repository from status files.
    
    Uses the repo_name column in status.csv to accurately identify RPMs from the repository.
    
    Args:
        repo_name: Repository name (e.g., 'x86_64_appstream')
        base_path: Base path for status files
        logger: Logger instance
        
    Returns:
        List of software names that were affected
    """
    affected_software = []
    logger.info(f"Removing RPMs from status.csv for repository: {repo_name}")
    try:
        for arch in ARCH_SUFFIXES:
            for status_file in glob.glob(f"{base_path}/{arch}/*/status.csv"):
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

                        logger.info(f"Processing row: {row}")
                        # For RPMs, check if they belong to the deleted repository
                        if row_type == 'rpm':
                            if has_repo_column and rpm_repo == repo_name:
                                removed = True
                                logger.info(f"Removing RPM '{name}' from {status_file} (repo {repo_name} deleted)")
                            else:
                                rows.append(row)
                        else:
                            rows.append(row)

                if removed and fieldnames:
                    with open(status_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)

                    # Track affected software
                    software_name = os.path.basename(os.path.dirname(status_file))
                    if software_name not in affected_software:
                        affected_software.append(software_name)

        return affected_software
    except Exception as e:
        logger.error(f"Failed to remove RPMs from repository {repo_name}: {e}")
        return []

def remove_from_status_files(artifact_name: str, artifact_type: str, base_path: str, logger) -> Dict[str, List[str]]:
    """Remove artifact from status.csv files and return affected software names by architecture.
    
    Args:
        artifact_name: Name of the artifact to remove
        artifact_type: Type of artifact (git, tarball, pip_module)
        base_path: Base path for status files
        logger: Logger instance
        
    Returns:
        Dict mapping architecture to list of affected software names
    """
    affected_software = {}
    try:
        for arch in ARCH_SUFFIXES:
            arch_affected = []
            for status_file in glob.glob(f"{base_path}/{arch}/*/status.csv"):
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
        affected_software: Either a List[str] of software names (from remove_rpms_from_repository)
                          or a Dict[str, List[str]] mapping arch to software names (from remove_from_status_files)
        base_path: Base path for software.csv
        logger: Logger instance
        artifact_type: Type of artifact being removed (for logging purposes)
    """
    logger.info(f"mark_software_partial called with affected_software: {affected_software}")
    if not affected_software:
        logger.info("No affected software to mark as partial")
        return

    # Normalize input: if a flat list is passed, apply to all architectures
    if isinstance(affected_software, list):
        arch_software_map = {arch: affected_software for arch in ARCH_SUFFIXES}
    else:
        arch_software_map = affected_software

    try:
        for arch, software_names in arch_software_map.items():
            if not software_names:
                continue

            software_file = f"{base_path}/{arch}/software.csv"
            logger.info(f"Looking for software file: {software_file}")
            if not os.path.exists(software_file):
                logger.warning(f"Software file not found: {software_file}")
                continue

            rows = []
            updated = False
            with open(software_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row.get('name') in software_names:
                        row['status'] = 'partial'
                        updated = True
                        logger.info(f"Marked '{row.get('name')}' as partial in {arch}/software.csv ({artifact_type} cleanup)")
                    rows.append(row)

            if fieldnames and rows and updated:
                with open(software_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                logger.info(f"Successfully wrote updated software.csv for {arch}")
    except OSError as e:
        logger.error(f"Failed to update software.csv: {e}")

def software_has_rpms(software_name: str, arch: str, base_path: str, logger) -> bool:
    """Check if a software has any RPM dependencies in its status.csv.
    
    Args:
        software_name: Name of the software
        arch: Architecture (x86_64 or aarch64)
        base_path: Base path for status files
        logger: Logger instance
        
    Returns:
        True if software has RPM entries, False otherwise
    """
    status_file = f"{base_path}/{arch}/{software_name}/status.csv"
    if not os.path.exists(status_file):
        return False

    try:
        with open(status_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('type', '').lower() == 'rpm':
                    return True
        return False
    except OSError as e:
        logger.error(f"Error checking RPMs for {software_name}: {e}")
        return False


def mark_all_software_partial(base_path: str, logger):
    """Mark software entries as partial in software.csv for all architectures.
    
    This is called when cleanup_repos=all to mark software as partial
    since all RPM repositories are being deleted.
    Only marks software that actually has RPM dependencies.
    
    Args:
        base_path: Base path for software.csv files
        logger: Logger instance
    """
    logger.info("Marking software with RPM dependencies as partial (cleanup_repos=all)")
    try:
        for arch in ARCH_SUFFIXES:
            software_file = f"{base_path}/{arch}/software.csv"
            logger.info(f"Processing software file: {software_file}")

            if not os.path.exists(software_file):
                logger.info(f"Software file not found: {software_file}")
                continue

            rows = []
            updated = False
            with open(software_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    software_name = row.get('name', '')
                    if row.get('status') == 'success':
                        # Only mark as partial if software has RPM dependencies
                        if software_has_rpms(software_name, arch, base_path, logger):
                            row['status'] = 'partial'
                            updated = True
                            logger.info(f"Marked '{software_name}' as partial in {arch}/software.csv (has RPM deps)")
                        else:
                            logger.info(f"Skipping '{software_name}' - no RPM dependencies")
                    rows.append(row)

            if fieldnames and rows and updated:
                with open(software_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                logger.info(f"Successfully updated {software_file}")
    except OSError as e:
        logger.error(f"Failed to mark all software as partial: {e}")

def write_cleanup_status(results: List[Dict], base_path: str):
    """Write cleanup results to status file."""
    status_file = f"{base_path}/cleanup_status.csv"
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    with open(status_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'type', 'status', 'message'])
        writer.writeheader()
        writer.writerows(results)

    return status_file


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
            base_path=dict(type='str', default=CLEANUP_BASE_PATH_DEFAULT)
        ),
        supports_check_mode=True
    )

    cleanup_repos = module.params['cleanup_repos']
    cleanup_containers = module.params['cleanup_containers']
    cleanup_files = module.params['cleanup_files']
    base_path = module.params['base_path']

    # Setup logger - setup_standard_logger expects a directory, creates standard.log inside
    log_dir = os.path.join(base_path, "cleanup")
    os.makedirs(base_path, exist_ok=True)
    logger = setup_standard_logger(log_dir)

    # Handle 'all' keyword for repositories only
    cleanup_all_repos = cleanup_repos and len(cleanup_repos) == 1 and cleanup_repos[0].lower() == 'all'
    #if cleanup_repos and len(cleanup_repos) == 1 and cleanup_repos[0].lower() == 'all':
    if cleanup_all_repos:
        logger.info("cleanup_repos='all' - fetching all repositories from Pulp")
        cleanup_repos = get_all_repositories(logger)
        if not cleanup_repos:
            module.fail_json(msg="Failed to retrieve repository list from Pulp. Please check if Pulp services are running.")
        logger.info(f"Found {len(cleanup_repos)} repositories to cleanup: {cleanup_repos}")

    logger.info(f"Starting cleanup - repos: {cleanup_repos}, containers: {cleanup_containers}, files: {cleanup_files}")

    all_results = []

    # Process repositories
    for repo in cleanup_repos:
        result = cleanup_repository(repo, base_path, logger)
        all_results.append(result)
        logger.info(f"Repository {repo}: {result['status']} - {result['message']}")

    # If cleanup_repos=all, mark software with RPM dependencies as partial
    if cleanup_all_repos and any(r['status'] == 'Success' for r in all_results if r['type'] == 'repository'):
        mark_all_software_partial(base_path, logger)

    # Process containers
    for container in cleanup_containers:
        result = cleanup_container(container, base_path, logger)
        all_results.append(result)
        logger.info(f"Container {container}: {result['status']} - {result['message']}")

    # Process files
    for file in cleanup_files:
        result = cleanup_file(file, base_path, logger)
        all_results.append(result)
        logger.info(f"File {file}: {result['status']} - {result['message']}")

    # Write status file
    status_file = write_cleanup_status(all_results, base_path)

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
