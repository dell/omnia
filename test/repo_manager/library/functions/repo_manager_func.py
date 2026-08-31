# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Domain-specific verification functions.

All verification functions return a dict with keys:
  success (bool), details (str), error (str), and optionally skipped (bool).
"""

from typing import Any, Dict
import json
import yaml

from omnia_auto import load_test_config, run_on_host, run_playbook as _run_playbook
from ..vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    CMDS,
    INPUT_FILES,
    OUTPUT_FILES,
    PULP_CONTAINER_NAME,
    PULP_PORT,
    PULP_CLI_SYMLINK,
    PULP_CERTS_DIR,
)


def run_playbook(tag=None, **kwargs):
    """Wrapper around omnia_auto.run_playbook with repo_manager defaults."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )


def _get_input_path() -> str:
    """Return the repo_manager input path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return f"/opt/omnia/repo_manager/input/{project}"


def _get_output_path() -> str:
    """Return the repo_manager output path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return f"/opt/omnia/repo_manager/output/{project}"


def _get_base_path() -> str:
    """Return the repo_manager base data path."""
    return "/opt/omnia/repo_manager"


def _cmd_file_exists(host, path: str) -> str:
    """Run a file-existence check on the target."""
    cmd = CMDS["file_exists"].format(path=path)
    return run_on_host(host, cmd)


def _cmd_dir_exists(host, path: str) -> str:
    """Run a directory-existence check on the target."""
    cmd = CMDS["dir_exists"].format(path=path)
    return run_on_host(host, cmd)


def check_input_config_exists(host) -> Dict[str, Any]:
    """Verify repo_manager_config.yml exists on target."""
    input_path = _get_input_path()
    path = f"{input_path}/{INPUT_FILES['repo_manager_config']}"
    result = _cmd_file_exists(host, path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{INPUT_FILES['repo_manager_config']} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{INPUT_FILES['repo_manager_config']} not found at {path}",
    }


def check_endpoint_config_exists(host) -> Dict[str, Any]:
    """Verify repo_manager_endpoint_config.yml exists on target."""
    input_path = _get_input_path()
    path = f"{input_path}/{INPUT_FILES['repo_manager_endpoint_config']}"
    result = _cmd_file_exists(host, path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{INPUT_FILES['repo_manager_endpoint_config']} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{INPUT_FILES['repo_manager_endpoint_config']} not found at {path}",
    }


def check_credentials_present(host) -> Dict[str, Any]:
    """Verify credentials file is present on target."""
    input_path = _get_input_path()
    path = f"{input_path}/{INPUT_FILES['repo_manager_credentials']}"
    result = _cmd_file_exists(host, path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{INPUT_FILES['repo_manager_credentials']} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{INPUT_FILES['repo_manager_credentials']} not found at {path}",
    }


def check_repo_configured(host, repo_name: str, arch: str = "x86_64", os_version: str = "10.0") -> Dict[str, Any]:
    """Check if a specific repository is configured in repo_manager_config.yml."""
    input_path = _get_input_path()
    config_path = f"{input_path}/{INPUT_FILES['repo_manager_config']}"
    
    # Check if config file exists
    result = _cmd_file_exists(host, config_path)
    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": False,
            "details": f"Config file not found at {config_path}",
            "error": f"{INPUT_FILES['repo_manager_config']} not found",
        }
    
    # Read the config file and check if the repo is configured
    cmd = "python3 -c \"import yaml; config = yaml.safe_load(open('" + config_path + "')); repo = config.get('repositories', {}).get('" + os_version + "', {}).get('" + arch + "', {}).get('" + repo_name + "', {}); print('configured' if repo and repo.get('url') else 'not_configured')\""
    result = run_on_host(host, cmd)
    
    # Check for exact match of "configured" (not "not_configured")
    if result.rc == 0 and result.stdout.strip() == "configured":
        return {
            "success": True,
            "details": f"Repository '{repo_name}' is configured in repo_manager_config.yml",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"Repository '{repo_name}' is not configured in repo_manager_config.yml",
        "error": f"Repository '{repo_name}' not configured",
    }


def check_pulp_container_running(host) -> Dict[str, Any]:
    """Verify Pulp container is running."""
    cmd = CMDS["container_running"].format(name=PULP_CONTAINER_NAME)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "running" in result.stdout:
        return {
            "success": True,
            "details": f"Pulp container is running",
            "error": "",
        }
    return {
        "success": False,
        "details": "Container status: {}".format(result.stdout.strip()),
        "error": "Pulp container is not running",
    }


def check_pulp_status_healthy(host) -> Dict[str, Any]:
    """Verify Pulp status command succeeds and reports healthy."""
    result = run_on_host(host, CMDS["pulp_status"])
    if result.rc == 0 and result.stdout.strip():
        return {
            "success": True,
            "details": "pulp status returned successfully",
            "error": "",
        }
    return {
        "success": False,
        "details": f"pulp status exit code: {result.rc}",
        "error": "pulp status command failed or returned empty output",
    }


def check_pulp_endpoint_reachable(host) -> Dict[str, Any]:
    """Verify Pulp endpoint responds with HTTP 200."""
    # Use 127.0.0.1 for local Pulp endpoint health check
    cmd = (
        f"curl -k -s -o /dev/null -w '%{{http_code}}' "
        f"https://127.0.0.1:{PULP_PORT}/pulp/api/v3/status/ "
        f"|| echo '000'"
    )
    result = run_on_host(host, cmd)
    status = result.stdout.strip()
    if status == "200":
        return {
            "success": True,
            "details": f"Pulp endpoint returned HTTP {status}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Pulp endpoint HTTP status: {status}",
        "error": "Pulp endpoint is not reachable",
    }


def check_pulp_cli_configured(host) -> Dict[str, Any]:
    """Verify Pulp CLI symlink and version work."""
    result = run_on_host(host, CMDS["pulp_version"])
    if result.rc == 0:
        return {
            "success": True,
            "details": f"Pulp CLI version: {result.stdout.strip()}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Pulp CLI exit code: {result.rc}",
        "error": "Pulp CLI is not configured at /usr/local/bin/pulp",
    }


def check_pulp_certificates_exist(host) -> Dict[str, Any]:
    """Verify Pulp SSL certificates exist for HTTPS."""
    crt_path = f"{PULP_CERTS_DIR}/pulp_webserver.crt"
    key_path = f"{PULP_CERTS_DIR}/pulp_webserver.key"
    crt_result = _cmd_file_exists(host, crt_path)
    key_result = _cmd_file_exists(host, key_path)
    if "exists" in crt_result.stdout and "exists" in key_result.stdout:
        return {
            "success": True,
            "details": f"Pulp certificates found at {PULP_CERTS_DIR}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked crt: {crt_path}, key: {key_path}",
        "error": "Pulp SSL certificates are missing",
    }


def _read_repo_status(host) -> Dict[str, Any]:
    """Read repo_status.yml from the target and parse as YAML."""
    output_path = _get_output_path()
    path = f"{output_path}/{OUTPUT_FILES['repo_status']}"
    result = run_on_host(host, f"cat {path}")
    if result.rc != 0:
        return {"success": False, "details": f"Could not read {path}", "error": result.stderr}
    try:
        data = yaml.safe_load(result.stdout)
        return {"success": True, "details": data, "error": ""}
    except yaml.YAMLError as exc:
        return {
            "success": False,
            "details": f"Invalid YAML in {path}",
            "error": str(exc),
        }


def check_repo_status_exists(host) -> Dict[str, Any]:
    """Verify repo_status.yml exists."""
    output_path = _get_output_path()
    path = f"{output_path}/{OUTPUT_FILES['repo_status']}"
    result = _cmd_file_exists(host, path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{OUTPUT_FILES['repo_status']} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{OUTPUT_FILES['repo_status']} not found",
    }


def check_repo_status_success(host) -> Dict[str, Any]:
    """Verify repo_status.yml reports overall_status = success."""
    result = _read_repo_status(host)
    if not result["success"]:
        return result
    data = result["details"]
    overall_status = data.get("overall_status", "").lower()
    if overall_status == "success":
        return {
            "success": True,
            "details": f"overall_status is '{overall_status}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"overall_status is '{overall_status}'",
        "error": "repo_status.yml does not report success",
    }


def check_repo_status_has_repo(host, repo_name: str, arch: str = "x86_64", os_version: str = "10.0") -> Dict[str, Any]:
    """Verify a specific RPM repository is present in repo_status.yml."""
    result = _read_repo_status(host)
    if not result["success"]:
        return result
    data = result["details"]
    try:
        url = data["repositories"][os_version][arch][repo_name]["url"]
        if url:
            return {
                "success": True,
                "details": f"Repository '{repo_name}' ({arch}) URL: {url}",
                "error": "",
            }
    except (KeyError, TypeError):
        pass
    return {
        "success": False,
        "details": f"Searched repositories.{os_version}.{arch}.{repo_name}",
        "error": f"Repository '{repo_name}' ({arch}) not found in repo_status.yml",
    }


def check_repo_status_has_file_repo(host, repo_name: str, arch: str = "x86_64") -> Dict[str, Any]:
    """Verify a specific file repository (tarball) is present in repo_status.yml."""
    result = _read_repo_status(host)
    if not result["success"]:
        return result
    data = result["details"]
    try:
        url = data["file_repos"][arch]["tarball"][repo_name]
        if url:
            return {
                "success": True,
                "details": f"File repo '{repo_name}' ({arch}) URL: {url}",
                "error": "",
            }
    except (KeyError, TypeError):
        pass
    return {
        "success": False,
        "details": f"Searched file_repos.{arch}.tarball.{repo_name}",
        "error": f"File repo '{repo_name}' not found in repo_status.yml",
    }


def check_pulp_container_removed(host) -> Dict[str, Any]:
    """Verify Pulp container is removed."""
    cmd = f"podman container exists {PULP_CONTAINER_NAME} && echo 'exists' || echo 'missing'"
    result = run_on_host(host, cmd)
    if "missing" in result.stdout:
        return {
            "success": True,
            "details": "Pulp container is removed",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Container check output: {result.stdout.strip()}",
        "error": "Pulp container still exists",
    }


def check_pulp_cli_removed(host) -> Dict[str, Any]:
    """Verify Pulp CLI symlink is removed."""
    result = _cmd_file_exists(host, PULP_CLI_SYMLINK)
    if "missing" in result.stdout:
        return {
            "success": True,
            "details": f"Pulp CLI symlink removed: {PULP_CLI_SYMLINK}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Pulp CLI symlink still exists: {PULP_CLI_SYMLINK}",
        "error": "Pulp CLI symlink not removed",
    }


def check_pulp_directories_removed(host) -> Dict[str, Any]:
    """Verify Pulp config directories are removed."""
    base_path = _get_base_path()
    dirs = [
        f"{base_path}/pulp_config",
        f"{base_path}/log/pulp",
    ]
    for d in dirs:
        result = _cmd_dir_exists(host, d)
        if "exists" in result.stdout:
            return {
                "success": False,
                "details": f"Directory still exists: {d}",
                "error": "Pulp directories not fully removed",
            }
    return {
        "success": True,
        "details": f"Pulp directories removed: {', '.join(dirs)}",
        "error": "",
    }


def check_pulp_cli_repository_list(host) -> Dict[str, Any]:
    """Verify Pulp CLI can list RPM repositories."""
    cmd = "pulp rpm repository list"
    result = run_on_host(host, cmd)
    if result.rc == 0:
        repo_count = result.stdout.count("Name:")
        return {
            "success": True,
            "details": f"Pulp CLI listed {repo_count} RPM repositories",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Exit code: {result.rc}",
        "error": "Pulp CLI repository list command failed",
    }


def check_pulp_api_detailed_status(host) -> Dict[str, Any]:
    """Verify Pulp API detailed health (DB, workers, content apps, storage)."""
    cmd = "pulp status"
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "details": f"Exit code: {result.rc}",
            "error": "Pulp status command failed",
        }

    try:
        status_data = json.loads(result.stdout)

        # Check key components based on actual Pulp status structure
        checks = {
            "database": status_data.get("database_connection", {}).get("connected", False),
            "workers": len(status_data.get("online_workers", [])) > 0,
            "content_apps": len(status_data.get("online_content_apps", [])) > 0,
            "api_apps": len(status_data.get("online_api_apps", [])) > 0,
            "storage": status_data.get("storage", {}).get("total", 0) > 0,
        }

        failed_checks = [k for k, v in checks.items() if not v]
        if failed_checks:
            return {
                "success": False,
                "details": f"Failed components: {', '.join(failed_checks)}",
                "error": "Pulp API health check failed for some components",
            }

        # Get component counts for details
        details = f"Workers: {len(status_data.get('online_workers', []))}, " \
                  f"Content Apps: {len(status_data.get('online_content_apps', []))}, " \
                  f"API Apps: {len(status_data.get('online_api_apps', []))}, " \
                  f"DB Connected: {checks['database']}, " \
                  f"Storage: {status_data.get('storage', {}).get('total', 0) / (1024**3):.1f}GB"

        return {
            "success": True,
            "details": details,
            "error": "",
        }
    except (json.JSONDecodeError, KeyError) as exc:
        return {
            "success": False,
            "details": f"Output: {result.stdout[:200]}",
            "error": f"Failed to parse Pulp status JSON: {str(exc)}",
        }


def check_software_download_status(host) -> Dict[str, Any]:
    """Verify software download status per architecture."""
    # Check status.csv files in the log directory
    log_path = "/opt/omnia/repo_manager/log/rhel/10.0"
    cmd = f"find {log_path} -name 'status.csv' -type f"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": f"No status.csv files found in {log_path}",
            "error": "Software download status files missing",
        }

    status_files = result.stdout.strip().split('\n')
    failed_downloads = []

    for status_file in status_files:
        result = run_on_host(host, f"cat {status_file}")
        if result.rc == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if "failed" in line.lower() or "error" in line.lower():
                    failed_downloads.append(f"{status_file}: {line}")

    if failed_downloads:
        return {
            "success": False,
            "details": f"Found {len(failed_downloads)} failed downloads",
            "error": f"Failed downloads: {'; '.join(failed_downloads[:3])}",
        }

    return {
        "success": True,
        "details": f"All software downloads successful ({len(status_files)} status files)",
        "error": "",
    }


def check_per_software_package_status(host) -> Dict[str, Any]:
    """Verify per-software status.csv for individual package download results."""
    # Check status.csv files in the log directory for all software groups
    log_path = "/opt/omnia/repo_manager/log/rhel/10.0"
    cmd = f"find {log_path} -name 'status.csv' -type f"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": f"No status.csv files found in {log_path}",
            "error": "Per-software status files missing",
        }

    status_files = result.stdout.strip().split('\n')
    failed_packages = []
    total_packages = 0

    for status_file in status_files:
        result = run_on_host(host, f"cat {status_file}")
        if result.rc == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                total_packages += 1
                if "failed" in line.lower() or "error" in line.lower():
                    failed_packages.append(f"{status_file}: {line}")

    if failed_packages:
        return {
            "success": False,
            "details": f"Found {len(failed_packages)} failed package downloads out of {total_packages}",
            "error": f"Failed packages: {'; '.join(failed_packages[:3])}",
        }

    return {
        "success": True,
        "details": "All per-software packages successful ({} packages across {} status files)".format(
            total_packages, len(status_files)
        ),
        "error": "",
    }


def check_pulp_repositories_synced(host) -> Dict[str, Any]:
    """Verify all RPM repositories have latest_version_href (sync indicator)."""
    # Check if repositories are listed in repo_status.yml
    repo_status = _read_repo_status(host)
    if not repo_status["success"]:
        return {
            "success": False,
            "details": "Could not read repo_status.yml",
            "error": repo_status["error"],
        }

    # Check if repositories exist in Pulp by checking their URLs are accessible
    repo_data = repo_status["details"]
    if "repositories" not in repo_data:
        return {
            "success": False,
            "details": "No repositories found in repo_status.yml",
            "error": "Repository data missing",
        }

    # Check if at least some repositories are configured
    total_repos = 0
    for _os_version, archs in repo_data["repositories"].items():
        for _arch, repos in archs.items():
            total_repos += len(repos)

    if total_repos == 0:
        return {
            "success": False,
            "details": "No repositories configured in repo_status.yml",
            "error": "No repositories found",
        }

    return {
        "success": True,
        "details": f"Found {total_repos} repositories configured in repo_status.yml",
        "error": "",
    }


def check_pulp_distributions_published(host) -> Dict[str, Any]:
    """Verify all RPM distributions are published with repository attachment."""
    # Check if repositories have URLs in repo_status.yml (indicates they're published)
    repo_status = _read_repo_status(host)
    if not repo_status["success"]:
        return {
            "success": False,
            "details": "Could not read repo_status.yml",
            "error": repo_status["error"],
        }

    repo_data = repo_status["details"]
    if "repositories" not in repo_data:
        return {
            "success": False,
            "details": "No repositories found in repo_status.yml",
            "error": "Repository data missing",
        }

    # Check if repositories have URLs (indicates they're published)
    total_repos = 0
    repos_with_urls = 0
    for _os_version, archs in repo_data["repositories"].items():
        for _arch, repos in archs.items():
            for _repo_name, repo_info in repos.items():
                total_repos += 1
                if isinstance(repo_info, dict) and "url" in repo_info:
                    repos_with_urls += 1

    if repos_with_urls == 0:
        return {
            "success": False,
            "details": f"No repositories have URLs (0/{total_repos})",
            "error": "No published repositories found",
        }

    return {
        "success": True,
        "details": f"Found {repos_with_urls}/{total_repos} repositories with URLs (published)",
        "error": "",
    }
# Fixed verification functions for repo_manager tests

def check_container_repos_synced(host) -> Dict[str, Any]:
    """Verify all container image repositories are synced."""
    # Check status.csv files for container image downloads
    log_path = "/opt/omnia/repo_manager/log/rhel/10.0"
    cmd = f"find {log_path} -name 'status.csv' -type f"
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": f"No status.csv files found in {log_path}",
            "error": "Container status files missing",
        }

    status_files = result.stdout.strip().split('\n')
    container_images = []

    for status_file in status_files:
        result = run_on_host(host, f"cat {status_file}")
        if result.rc == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if "image" in line.lower():
                    container_images.append(line)

    if len(container_images) == 0:
        return {
            "success": False,
            "details": "No container images found in status files",
            "error": "No container repositories synced",
        }

    # Check if all container images show Success status
    failed_containers = []
    for line in container_images:
        if "failed" in line.lower() or "error" in line.lower():
            failed_containers.append(line)

    if failed_containers:
        return {
            "success": False,
            "details": f"Found {len(failed_containers)} failed container downloads",
            "error": f"Failed containers: {'; '.join(failed_containers[:3])}",
        }

    return {
        "success": True,
        "details": f"All {len(container_images)} container repositories synced successfully",
        "error": "",
    }


def check_file_repos_synced(host) -> Dict[str, Any]:
    """Verify all file repositories (tarball, git, etc.) are synced."""
    # Check file_repos section in repo_status.yml
    repo_status = _read_repo_status(host)
    if not repo_status["success"]:
        return {
            "success": False,
            "details": "Could not read repo_status.yml",
            "error": repo_status["error"],
        }

    repo_data = repo_status["details"]
    if "file_repos" not in repo_data:
        return {
            "success": False,
            "details": "No file_repos found in repo_status.yml",
            "error": "File repository data missing",
        }

    # Check if file repos are configured
    total_file_repos = 0
    for _arch, file_types in repo_data["file_repos"].items():
        for _file_type, repos in file_types.items():
            total_file_repos += len(repos)

    if total_file_repos == 0:
        return {
            "success": False,
            "details": "No file repositories configured in repo_status.yml",
            "error": "No file repositories found",
        }

    return {
        "success": True,
        "details": f"Found {total_file_repos} file repositories configured in repo_status.yml",
        "error": "",
    }


def check_pulp_content_accessible(host) -> Dict[str, Any]:
    """Verify RPM content is reachable via HTTPS (repomd.xml check)."""
    repo_status = _read_repo_status(host)
    if not repo_status["success"]:
        return {
            "success": False,
            "details": "Could not read repo_status.yml",
            "error": repo_status["error"],
        }

    repo_data = repo_status["details"]
    if "repositories" not in repo_data:
        return {
            "success": False,
            "details": "No repositories found in repo_status.yml",
            "error": "Repository data missing",
        }

    # Check if at least one repository URL is accessible
    accessible_repos = 0
    total_repos = 0
    for _os_version, archs in repo_data["repositories"].items():
        for _arch, repos in archs.items():
            for _repo_name, repo_info in repos.items():
                total_repos += 1
                if isinstance(repo_info, dict) and "url" in repo_info:
                    # Try to access the repository URL
                    repo_url = repo_info["url"]
                    result = run_on_host(host, f"curl -k -s -o /dev/null -w '%{{http_code}}' {repo_url}/repomd.xml")
                    if result.rc == 0 and ("200" in result.stdout or "404" in result.stdout):
                        accessible_repos += 1

    if accessible_repos == 0:
        return {
            "success": False,
            "details": f"No repositories accessible via HTTPS (0/{total_repos})",
            "error": "No accessible repositories found",
        }

    return {
        "success": True,
        "details": f"Found {accessible_repos}/{total_repos} repositories accessible via HTTPS",
        "error": "",
    }


def check_software_packages_in_pulp(host) -> Dict[str, Any]:
    """Verify all RPM packages from software_config.json are present in Pulp."""
    # Check if software_config.json exists in multiple possible locations
    input_path = _get_input_path()
    possible_paths = [
        f"{input_path}/software_config.json",
        "/opt/omnia/repo_manager/input/project_default/software_config.json",
        "/opt/omnia/repo_manager/input/software_config.json",
    ]

    config_path = None
    for path in possible_paths:
        result = _cmd_file_exists(host, path)
        if result.rc == 0 and "exists" in result.stdout:
            config_path = path
            break

    if not config_path:
        # If software_config.json doesn't exist, check if we have status.csv files with package info
        log_path = "/opt/omnia/repo_manager/log/rhel/10.0"
        cmd = f"find {log_path} -name 'status.csv' -type f"
        result = run_on_host(host, cmd)

        if result.rc == 0 and result.stdout.strip():
            status_files = result.stdout.strip().split('\n')
            total_packages = 0
            for status_file in status_files:
                result = run_on_host(host, f"cat {status_file}")
                if result.rc == 0:
                    lines = result.stdout.strip().split('\n')
                    total_packages += len(lines) - 1  # Exclude header

            if total_packages > 0:
                return {
                    "success": True,
                    "details": f"Found {total_packages} packages in status.csv files (software_config.json not required)",
                    "error": "",
                }

        return {
            "success": False,
            "details": "software_config.json not found and no status.csv files available",
            "error": "Software configuration data missing",
        }

    # Read and parse software_config.json
    result = run_on_host(host, f"cat {config_path}")
    if result.rc != 0:
        return {
            "success": False,
            "details": f"Could not read {config_path}",
            "error": "Failed to read software_config.json",
        }

    try:
        software_config = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "details": f"Invalid JSON in {config_path}",
            "error": f"Failed to parse software_config.json: {str(exc)}",
        }

    # Check if at least some software packages are defined
    if "software" not in software_config:
        return {
            "success": False,
            "details": "No software packages defined in software_config.json",
            "error": "Software packages missing",
        }

    total_packages = 0
    for _arch, packages in software_config["software"].items():
        for _package in packages:
            total_packages += 1

    if total_packages == 0:
        return {
            "success": False,
            "details": "No software packages found in software_config.json",
            "error": "No packages defined",
        }

    return {
        "success": True,
        "details": "Found {} software packages defined in software_config.json".format(total_packages),
        "error": "",
    }


def check_repo_policy(host, repo_name: str, arch: str = "x86_64", os_version: str = "10.0") -> Dict[str, Any]:
    """Check the effective policy for a specific repository."""
    input_path = _get_input_path()
    config_path = f"{input_path}/{INPUT_FILES['repo_manager_config']}"
    
    # Check if config file exists
    result = _cmd_file_exists(host, config_path)
    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": False,
            "details": f"Config file not found at {config_path}",
            "error": f"{INPUT_FILES['repo_manager_config']} not found",
        }
    
    # Read the config file and check the repo policy
    cmd = "python3 -c \"import yaml; config = yaml.safe_load(open('" + config_path + "')); repo = config.get('repositories', {}).get('" + os_version + "', {}).get('" + arch + "', {}).get('" + repo_name + "', {}); policy = repo.get('policy') if repo else None; print(policy if policy else 'not_set')\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        policy = result.stdout.strip()
        if policy != "not_set":
            return {
                "success": True,
                "details": f"Repository '{repo_name}' has policy: {policy}",
                "error": "",
                "policy": policy,
                "source": "per_repo"
            }
        else:
            # Check global policy
            cmd = "python3 -c \"import yaml; config = yaml.safe_load(open('" + config_path + "')); print(config.get('repo_config', 'not_set'))\""
            result = run_on_host(host, cmd)
            if result.rc == 0:
                global_policy = result.stdout.strip()
                return {
                    "success": True,
                    "details": f"Repository '{repo_name}' uses global policy: {global_policy}",
                    "error": "",
                    "policy": global_policy,
                    "source": "global"
                }
    
    return {
        "success": False,
        "details": f"Could not determine policy for repository '{repo_name}'",
        "error": "Policy determination failed",
    }


def check_repo_caching(host, repo_name: str, arch: str = "x86_64", os_version: str = "10.0") -> Dict[str, Any]:
    """Check the effective caching setting for a specific repository."""
    input_path = _get_input_path()
    config_path = f"{input_path}/{INPUT_FILES['repo_manager_config']}"
    
    # Check if config file exists
    result = _cmd_file_exists(host, config_path)
    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": False,
            "details": f"Config file not found at {config_path}",
            "error": f"{INPUT_FILES['repo_manager_config']} not found",
        }
    
    # Read the config file and check the repo caching
    cmd = "python3 -c \"import yaml; config = yaml.safe_load(open('" + config_path + "')); repo = config.get('repositories', {}).get('" + os_version + "', {}).get('" + arch + "', {}).get('" + repo_name + "', {}); caching = repo.get('caching') if repo else None; print(str(caching).lower() if caching is not None else 'not_set')\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        caching = result.stdout.strip()
        if caching != "not_set":
            return {
                "success": True,
                "details": f"Repository '{repo_name}' has caching: {caching}",
                "error": "",
                "caching": caching == "true",
                "source": "per_repo"
            }
        else:
            # Check global caching
            cmd = "python3 -c \"import yaml; config = yaml.safe_load(open('" + config_path + "')); print(str(config.get('CACHING_POLICY', False)).lower())\""
            result = run_on_host(host, cmd)
            if result.rc == 0:
                global_caching = result.stdout.strip()
                return {
                    "success": True,
                    "details": f"Repository '{repo_name}' uses global caching: {global_caching}",
                    "error": "",
                    "caching": global_caching == "true",
                    "source": "global"
                }
    
    return {
        "success": False,
        "details": f"Could not determine caching for repository '{repo_name}'",
        "error": "Caching determination failed",
    }


def check_pulp_mode(host, repo_name: str) -> Dict[str, Any]:
    """Check the actual Pulp mode for a repository from repo_status.yml."""
    repo_status = _read_repo_status(host)
    if not repo_status["success"]:
        return {
            "success": False,
            "details": "Could not read repo_status.yml",
            "error": repo_status["error"],
        }
    
    repo_data = repo_status["details"]
    try:
        # Check for Pulp mode in repository data
        for os_version, archs in repo_data.get("repositories", {}).items():
            for arch, repos in archs.items():
                if repo_name in repos:
                    repo_info = repos[repo_name]
                    if isinstance(repo_info, dict):
                        pulp_mode = repo_info.get("pulp_mode", "unknown")
                        return {
                            "success": True,
                            "details": f"Repository '{repo_name}' has Pulp mode: {pulp_mode}",
                            "error": "",
                            "mode": pulp_mode
                        }
    except (KeyError, TypeError) as exc:
        return {
            "success": False,
            "details": f"Error parsing repo_status.yml: {str(exc)}",
            "error": "Repository data parsing failed",
        }
    
    return {
        "success": False,
        "details": f"Repository '{repo_name}' not found in repo_status.yml",
        "error": "Repository not found",
    }


def verify_repo_status_pulp_mode(host, repo_name: str, expected_mode: str) -> Dict[str, Any]:
    """Verify repo_status.yml reflects correct Pulp mode for a repository."""
    pulp_mode_result = check_pulp_mode(host, repo_name)
    if not pulp_mode_result["success"]:
        return pulp_mode_result
    
    actual_mode = pulp_mode_result.get("mode", "unknown")
    if actual_mode == expected_mode:
        return {
            "success": True,
            "details": f"Repository '{repo_name}' has expected Pulp mode: {expected_mode}",
            "error": "",
            "expected_mode": expected_mode,
            "actual_mode": actual_mode
        }
    else:
        return {
            "success": False,
            "details": f"Repository '{repo_name}' Pulp mode mismatch: expected {expected_mode}, got {actual_mode}",
            "error": "Pulp mode verification failed",
            "expected_mode": expected_mode,
            "actual_mode": actual_mode
        }


def check_global_repo_config(host) -> Dict[str, Any]:
    """Check the global repo_config setting."""
    input_path = _get_input_path()
    config_path = f"{input_path}/{INPUT_FILES['repo_manager_config']}"
    
    result = _cmd_file_exists(host, config_path)
    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": False,
            "details": f"Config file not found at {config_path}",
            "error": f"{INPUT_FILES['repo_manager_config']} not found",
        }
    
    cmd = "python3 -c \"import yaml; config = yaml.safe_load(open('" + config_path + "')); print(config.get('repo_config', 'not_set'))\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        repo_config = result.stdout.strip()
        return {
            "success": True,
            "details": f"Global repo_config: {repo_config}",
            "error": "",
            "repo_config": repo_config
        }
    
    return {
        "success": False,
        "details": "Could not read global repo_config",
        "error": "Global config read failed",
    }


def check_global_caching_policy(host) -> Dict[str, Any]:
    """Check the global CACHING_POLICY setting."""
    input_path = _get_input_path()
    config_path = f"{input_path}/{INPUT_FILES['repo_manager_config']}"
    
    result = _cmd_file_exists(host, config_path)
    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": False,
            "details": f"Config file not found at {config_path}",
            "error": f"{INPUT_FILES['repo_manager_config']} not found",
        }
    
    cmd = "python3 -c \"import yaml; config = yaml.safe_load(open('" + config_path + "')); print(str(config.get('CACHING_POLICY', False)).lower())\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        caching_policy = result.stdout.strip()
        return {
            "success": True,
            "details": f"Global CACHING_POLICY: {caching_policy}",
            "error": "",
            "caching_policy": caching_policy == "true"
        }
    
    return {
        "success": False,
        "details": "Could not read global CACHING_POLICY",
        "error": "Global config read failed",
    }


def check_pulp_remote_policy(host, repo_name: str, arch: str = "x86_64", os_version: str = "10.0") -> Dict[str, Any]:
    """Check the actual Pulp remote policy via Pulp CLI (integration test)."""
    # Construct the full remote name
    full_remote_name = f"{arch}_{os_version}_{repo_name}"
    
    # Use Pulp CLI to get the actual remote policy
    cmd = f"pulp rpm remote show --name {full_remote_name}"
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        try:
            remote_info = json.loads(result.stdout)
            actual_policy = remote_info.get("policy", "unknown")
            return {
                "success": True,
                "details": f"Pulp remote '{full_remote_name}' has policy: {actual_policy}",
                "error": "",
                "policy": actual_policy,
                "remote_name": full_remote_name
            }
        except json.JSONDecodeError as exc:
            return {
                "success": False,
                "details": f"Could not parse Pulp remote output: {result.stdout[:200]}",
                "error": f"JSON decode error: {str(exc)}",
            }
    else:
        return {
            "success": False,
            "details": f"Pulp remote command failed with exit code: {result.rc}",
            "error": f"Pulp remote '{full_remote_name}' not found or Pulp CLI error",
        }


def check_pulp_repository_exists(host, repo_name: str, arch: str = "x86_64", os_version: str = "10.0") -> Dict[str, Any]:
    """Check if a Pulp repository exists via Pulp CLI (integration test)."""
    # Construct the full repository name
    full_repo_name = f"{arch}_{os_version}_{repo_name}"
    
    # Use Pulp CLI to check if repository exists
    cmd = f"pulp rpm repository show --name {full_repo_name}"
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        try:
            repo_info = json.loads(result.stdout)
            latest_version = repo_info.get("latest_version_href", "unknown")
            return {
                "success": True,
                "details": f"Pulp repository '{full_repo_name}' exists (version: {latest_version})",
                "error": "",
                "repo_name": full_repo_name,
                "latest_version": latest_version
            }
        except json.JSONDecodeError as exc:
            return {
                "success": False,
                "details": f"Could not parse Pulp repository output: {result.stdout[:200]}",
                "error": f"JSON decode error: {str(exc)}",
            }
    else:
        return {
            "success": False,
            "details": f"Pulp repository command failed with exit code: {result.rc}",
            "error": f"Pulp repository '{full_repo_name}' not found or Pulp CLI error",
        }


def verify_policy_resolution(host, repo_name: str, arch: str = "x86_64", os_version: str = "10.0") -> Dict[str, Any]:
    """Verify that the resolved policy from config matches actual Pulp remote policy."""
    # Get policy from configuration
    config_policy = check_repo_policy(host, repo_name, arch, os_version)
    config_caching = check_repo_caching(host, repo_name, arch, os_version)
    
    if not config_policy["success"] or not config_caching["success"]:
        return {
            "success": False,
            "details": "Could not read configuration policy/caching",
            "error": "Config read failed",
        }
    
    # Calculate expected Pulp policy based on policy + caching
    policy = config_policy.get("policy")
    caching = config_caching.get("caching")
    
    # Policy resolution logic (from software_utils.py)
    if policy == "always" and not caching:
        expected_pulp_policy = "immediate"
    elif policy == "always" and caching:
        expected_pulp_policy = "on_demand"
    elif policy == "partial" and not caching:
        expected_pulp_policy = "streamed"
    elif policy == "partial" and caching:
        expected_pulp_policy = "on_demand"
    elif policy == "never" and not caching:
        expected_pulp_policy = "streamed"
    elif policy == "never" and caching:
        expected_pulp_policy = "streamed"
    else:
        expected_pulp_policy = "unknown"
    
    # Get actual Pulp remote policy
    actual_policy_result = check_pulp_remote_policy(host, repo_name, arch, os_version)
    
    if not actual_policy_result["success"]:
        return {
            "success": False,
            "details": f"Could not get actual Pulp remote policy",
            "error": actual_policy_result["error"],
        }
    
    actual_pulp_policy = actual_policy_result.get("policy")
    
    # Compare expected vs actual
    if expected_pulp_policy == actual_pulp_policy:
        return {
            "success": True,
            "details": f"Policy resolution correct: config({policy}+{caching}) → expected({expected_pulp_policy}) → actual({actual_pulp_policy})",
            "error": "",
            "expected_policy": expected_pulp_policy,
            "actual_policy": actual_pulp_policy,
            "match": True
        }
    else:
        return {
            "success": False,
            "details": f"Policy resolution mismatch: config({policy}+{caching}) → expected({expected_pulp_policy}) → actual({actual_pulp_policy})",
            "error": "Policy resolution bug detected",
            "expected_policy": expected_pulp_policy,
            "actual_policy": actual_pulp_policy,
            "match": False
        }


# =============================================================================
# CATALOG VERIFICATION FUNCTIONS
# =============================================================================

def check_catalog_file_exists(host) -> Dict[str, Any]:
    """Verify catalog JSON file exists."""
    catalog_path = "/opt/omnia/catalog/catalog_rhel.json"
    result = _cmd_file_exists(host, catalog_path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"Catalog file found at {catalog_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {catalog_path}",
        "error": f"Catalog file not found at {catalog_path}",
    }


def check_catalog_structure(host) -> Dict[str, Any]:
    """Verify catalog JSON has valid structure (catalog root key)."""
    catalog_path = "/opt/omnia/catalog/catalog_rhel.json"
    cmd = "python3 -c \"import json; data = json.load(open('" + catalog_path + "')); print('valid' if 'catalog' in data else 'invalid')\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0 and "valid" in result.stdout:
        return {
            "success": True,
            "details": "Catalog JSON has valid structure with 'catalog' root key",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Catalog structure check failed: {result.stdout.strip()}",
        "error": "Catalog JSON missing 'catalog' root key or invalid JSON",
    }


def check_catalog_functional_layers(host) -> Dict[str, Any]:
    """Verify catalog has functional layers."""
    catalog_path = "/opt/omnia/catalog/catalog_rhel.json"
    cmd = "python3 -c \"import json; data = json.load(open('" + catalog_path + "')); fl = data.get('catalog', {}).get('functionallayer', []); print(len(fl))\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        try:
            fl_count = int(result.stdout.strip())
            if fl_count > 0:
                return {
                    "success": True,
                    "details": f"Catalog has {fl_count} functional layer(s)",
                    "error": "",
                }
            return {
                "success": False,
                "details": f"Catalog has {fl_count} functional layers (must have at least 1)",
                "error": "Catalog must have at least one functional layer",
            }
        except ValueError:
            return {
                "success": False,
                "details": f"Could not parse functional layer count: {result.stdout.strip()}",
                "error": "Functional layer count parsing failed",
            }
    return {
        "success": False,
        "details": f"Command failed: {result.stderr}",
        "error": "Failed to read functional layers from catalog",
    }


def check_catalog_groups(host) -> Dict[str, Any]:
    """Verify catalog has groups."""
    catalog_path = "/opt/omnia/catalog/catalog_rhel.json"
    cmd = "python3 -c \"import json; data = json.load(open('" + catalog_path + "')); groups = data.get('catalog', {}).get('groups', {}); print(len(groups))\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        try:
            group_count = int(result.stdout.strip())
            if group_count > 0:
                return {
                    "success": True,
                    "details": f"Catalog has {group_count} group(s)",
                    "error": "",
                }
            return {
                "success": False,
                "details": f"Catalog has {group_count} groups (must have at least 1)",
                "error": "Catalog must have at least one group",
            }
        except ValueError:
            return {
                "success": False,
                "details": f"Could not parse group count: {result.stdout.strip()}",
                "error": "Group count parsing failed",
            }
    return {
        "success": False,
        "details": f"Command failed: {result.stderr}",
        "error": "Failed to read groups from catalog",
    }


def check_catalog_packages(host) -> Dict[str, Any]:
    """Verify catalog has packages."""
    catalog_path = "/opt/omnia/catalog/catalog_rhel.json"
    cmd = "python3 -c \"import json; data = json.load(open('" + catalog_path + "')); packages = data.get('catalog', {}).get('packages', {}); print(len(packages))\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        try:
            pkg_count = int(result.stdout.strip())
            if pkg_count > 0:
                return {
                    "success": True,
                    "details": f"Catalog has {pkg_count} package(s)",
                    "error": "",
                }
            return {
                "success": False,
                "details": f"Catalog has {pkg_count} packages (must have at least 1)",
                "error": "Catalog must have at least one package",
            }
        except ValueError:
            return {
                "success": False,
                "details": f"Could not parse package count: {result.stdout.strip()}",
                "error": "Package count parsing failed",
            }
    return {
        "success": False,
        "details": f"Command failed: {result.stderr}",
        "error": "Failed to read packages from catalog",
    }


def check_catalog_has_group(host, group_name: str) -> Dict[str, Any]:
    """Verify catalog contains a specific group."""
    catalog_path = "/opt/omnia/catalog/catalog_rhel.json"
    cmd = "python3 -c \"import json; data = json.load(open('" + catalog_path + "')); groups = data.get('catalog', {}).get('groups', {}); print('found' if '" + group_name + "' in groups else 'not_found')\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0 and "found" in result.stdout:
        return {
            "success": True,
            "details": f"Group '{group_name}' found in catalog",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Group '{group_name}' not found in catalog",
        "error": f"Group '{group_name}' missing from catalog",
    }


def check_catalog_has_package(host, package_key: str) -> Dict[str, Any]:
    """Verify catalog contains a specific package."""
    catalog_path = "/opt/omnia/catalog/catalog_rhel.json"
    cmd = "python3 -c \"import json; data = json.load(open('" + catalog_path + "')); packages = data.get('catalog', {}).get('packages', {}); print('found' if '" + package_key + "' in packages else 'not_found')\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0 and "found" in result.stdout:
        return {
            "success": True,
            "details": f"Package '{package_key}' found in catalog",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Package '{package_key}' not found in catalog",
        "error": f"Package '{package_key}' missing from catalog",
    }


def check_catalog_package_type(host, package_key: str, expected_type: str) -> Dict[str, Any]:
    """Verify a package has the expected type (rpm, tarball, image)."""
    catalog_path = "/opt/omnia/catalog/catalog_rhel.json"
    cmd = "python3 -c \"import json; data = json.load(open('" + catalog_path + "')); pkg = data.get('catalog', {}).get('packages', {}).get('" + package_key + "', {}); print(pkg.get('packagetype', 'unknown'))\""
    result = run_on_host(host, cmd)
    
    if result.rc == 0:
        actual_type = result.stdout.strip()
        if actual_type == expected_type:
            return {
                "success": True,
                "details": f"Package '{package_key}' has type '{actual_type}'",
                "error": "",
            }
        return {
            "success": False,
            "details": f"Package '{package_key}' has type '{actual_type}' (expected '{expected_type}')",
            "error": f"Package type mismatch: expected '{expected_type}', got '{actual_type}'",
        }
    return {
        "success": False,
        "details": f"Command failed: {result.stderr}",
        "error": "Failed to read package type from catalog",
    }


def check_catalog_input_file_exists(host) -> Dict[str, Any]:
    """Verify catalog input file exists for testing."""
    input_path = "/opt/omnia/repo_manager/input/project_default"
    result = _cmd_dir_exists(host, input_path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"Catalog input directory exists at {input_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {input_path}",
        "error": f"Catalog input directory not found at {input_path}",
    }


def check_catalog_log_file_exists(host) -> Dict[str, Any]:
    """Verify catalog log file exists."""
    log_path = "/opt/omnia/repo_manager/log/catalog/catalog_manager.log"
    result = _cmd_file_exists(host, log_path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"Catalog log file found at {log_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {log_path}",
        "error": f"Catalog log file not found at {log_path}",
    }


def parse_catalog_input_file(host, input_file: str) -> Dict[str, Any]:
    """Parse catalog input file to extract groups and packages."""
    result = run_on_host(host, f"cat {input_file}")
    
    if result.rc != 0:
        return {
            "success": False,
            "details": f"Could not read input file: {input_file}",
            "error": result.stderr,
            "groups": [],
            "packages": []
        }
    
    groups = []
    packages = []
    current_group = None
    
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        elif line.startswith('[') and line.endswith(']'):
            current_group = line[1:-1]
            if current_group not in groups:
                groups.append(current_group)
        elif current_group:
            packages.append(line)
    
    return {
        "success": True,
        "details": f"Parsed {len(groups)} groups and {len(packages)} packages from input file",
        "error": "",
        "groups": groups,
        "packages": packages
    }
