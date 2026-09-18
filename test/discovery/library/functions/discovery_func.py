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
Discovery — Domain-Specific Verification Functions

All verification functions return a dict with keys:
  success (bool), details (str), error (str), and optionally skipped (bool).
"""

from typing import Any, Dict

from omnia_auto import load_test_config, run_on_host
from ..vars.common_vars import (
    CMDS,
    DISCOVERY_CONFIG_FILE,
    NETWORK_SPEC_FILE,
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    INPUT_PATH_TEMPLATE,
    OUTPUT_PATH_TEMPLATE,
    PXE_MAPPING_PATTERN,
    PXE_MAPPING_SYMLINK,
    DISCOVERY_REPORT_PATTERN,
)


def _get_input_path() -> str:
    """Return the discovery input path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return INPUT_PATH_TEMPLATE.format(project=project)


def _get_output_path() -> str:
    """Return the discovery output path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return OUTPUT_PATH_TEMPLATE.format(project=project)


def check_input_config_exists(host) -> Dict[str, Any]:
    """Verify discovery_config.yml exists on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path()
    path = f"{input_path}/{DISCOVERY_CONFIG_FILE}"
    cmd = CMDS["file_exists"].format(path=path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{DISCOVERY_CONFIG_FILE} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{DISCOVERY_CONFIG_FILE} not found at {path}",
    }


def check_network_spec_exists(host) -> Dict[str, Any]:
    """Verify network_spec.yml exists on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path()
    path = f"{input_path}/{NETWORK_SPEC_FILE}"
    cmd = CMDS["file_exists"].format(path=path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{NETWORK_SPEC_FILE} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{NETWORK_SPEC_FILE} not found at {path}",
    }


def check_credentials_present(host) -> Dict[str, Any]:
    """Verify credentials file is present on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path()
    cred_path = f"{input_path}/{CREDENTIALS_FILE_NAME}"
    cmd = CMDS["file_exists"].format(path=cred_path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{CREDENTIALS_FILE_NAME} found at {cred_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {cred_path}",
        "error": f"{CREDENTIALS_FILE_NAME} not found at {cred_path}",
    }


def check_output_dir_exists(host) -> Dict[str, Any]:
    """Verify discovery output directory exists.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    cmd = CMDS["dir_exists"].format(path=output_path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"Output directory exists: {output_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {output_path}",
        "error": f"Output directory not found: {output_path}",
    }


def check_pxe_mapping_created(host) -> Dict[str, Any]:
    """Verify bmc_pxe_mapping_file CSV was created in output directory.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    cmd = CMDS["find_csv"].format(
        path=output_path, pattern=PXE_MAPPING_PATTERN
    )
    result = run_on_host(host, cmd)
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    if files:
        return {
            "success": True,
            "details": f"Found {len(files)} PXE mapping file(s): {files[-1]}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Searched: {output_path}/{PXE_MAPPING_PATTERN}",
        "error": "No PXE mapping files found",
    }


def check_pxe_mapping_columns(host) -> Dict[str, Any]:
    """Verify PXE mapping CSV has required columns.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    symlink_path = f"{output_path}/{PXE_MAPPING_SYMLINK}"
    cmd = CMDS["csv_header"].format(path=symlink_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "details": f"Could not read header from {symlink_path}",
            "error": "PXE mapping file not readable",
        }

    header = result.stdout.strip()
    required_columns = [
        "FUNCTIONAL_GROUP_NAME", "SERVICE_TAG", "HOSTNAME",
        "ADMIN_MAC", "ADMIN_IP", "BMC_IP",
    ]
    missing = [c for c in required_columns if c not in header]
    if missing:
        return {
            "success": False,
            "details": f"Header: {header}",
            "error": f"Missing columns: {', '.join(missing)}",
        }
    return {
        "success": True,
        "details": f"All required columns present",
        "error": "",
    }


def check_pxe_mapping_has_rows(host) -> Dict[str, Any]:
    """Verify PXE mapping CSV contains data rows.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    symlink_path = f"{output_path}/{PXE_MAPPING_SYMLINK}"
    cmd = CMDS["csv_line_count"].format(path=symlink_path)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "details": f"Could not count lines in {symlink_path}",
            "error": "PXE mapping file not readable",
        }

    line_count = int(result.stdout.strip())
    data_rows = line_count - 1  # subtract header
    if data_rows > 0:
        return {
            "success": True,
            "details": f"{data_rows} data rows found",
            "error": "",
        }
    return {
        "success": False,
        "details": f"File has {line_count} total lines (header only)",
        "error": "PXE mapping file has no data rows",
    }


def check_discovery_report_created(host) -> Dict[str, Any]:
    """Verify bmc_discovery_report CSV was created.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    cmd = CMDS["find_csv"].format(
        path=output_path, pattern=DISCOVERY_REPORT_PATTERN
    )
    result = run_on_host(host, cmd)
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    if files:
        return {
            "success": True,
            "details": f"Found {len(files)} discovery report(s): {files[-1]}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Searched: {output_path}/{DISCOVERY_REPORT_PATTERN}",
        "error": "No discovery report files found",
    }


def check_pxe_mapping_symlink(host) -> Dict[str, Any]:
    """Verify bmc_pxe_mapping_file.csv symlink exists and points to a file.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    symlink_path = f"{output_path}/{PXE_MAPPING_SYMLINK}"
    cmd = CMDS["readlink"].format(path=symlink_path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and result.stdout.strip():
        target = result.stdout.strip()
        return {
            "success": True,
            "details": f"Symlink -> {target}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked: {symlink_path}",
        "error": "Symlink not found or broken",
    }


def check_clone_status(host) -> Dict[str, Any]:
    """Verify repository is cloned on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")
    cmd = CMDS["dir_exists"].format(path=clone_path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"Repository found at {clone_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked: {clone_path}",
        "error": f"Repository not found at {clone_path}",
    }


def check_output_dir_removed(host) -> Dict[str, Any]:
    """Verify discovery output directory is empty after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    cmd = CMDS["dir_exists"].format(path=output_path)
    result = run_on_host(host, cmd)
    
    # Directory should not exist or should be empty
    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": True,
            "details": f"Output directory removed: {output_path}",
            "error": "",
        }
    
    # If directory exists, check if it's empty
    cmd = CMDS["ls_files"].format(path=output_path)
    result = run_on_host(host, cmd)
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    
    if not files:
        return {
            "success": True,
            "details": f"Output directory exists but is empty: {output_path}",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"Found {len(files)} remaining files/directories",
        "error": f"Output directory not empty: {output_path}",
    }


def check_credentials_removed(host) -> Dict[str, Any]:
    """Verify discovery credentials file is removed after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path()
    cred_path = f"{input_path}/{CREDENTIALS_FILE_NAME}"
    cmd = CMDS["file_exists"].format(path=cred_path)
    result = run_on_host(host, cmd)
    
    # Credentials file should not exist after cleanup
    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": True,
            "details": f"Credentials file removed: {cred_path}",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"Credentials file still exists: {cred_path}",
        "error": "Credentials file not removed during cleanup",
    }


def check_pxe_mapping_files_removed(host) -> Dict[str, Any]:
    """Verify PXE mapping CSV files are removed after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    cmd = CMDS["find_csv"].format(
        path=output_path, pattern=PXE_MAPPING_PATTERN
    )
    result = run_on_host(host, cmd)
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    
    if not files:
        return {
            "success": True,
            "details": f"No PXE mapping files found (cleanup successful)",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"Found {len(files)} remaining PXE mapping file(s)",
        "error": "PXE mapping files not removed during cleanup",
    }


def check_discovery_report_files_removed(host) -> Dict[str, Any]:
    """Verify discovery report CSV files are removed after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    cmd = CMDS["find_csv"].format(
        path=output_path, pattern=DISCOVERY_REPORT_PATTERN
    )
    result = run_on_host(host, cmd)
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    
    if not files:
        return {
            "success": True,
            "details": f"No discovery report files found (cleanup successful)",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"Found {len(files)} remaining discovery report file(s)",
        "error": "Discovery report files not removed during cleanup",
    }


def check_status_files_removed(host) -> Dict[str, Any]:
    """Verify discovery status files are removed after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    output_path = _get_output_path()
    cmd = CMDS["find_csv"].format(
        path=output_path, pattern="discovery_status.yml"
    )
    result = run_on_host(host, cmd)
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    
    if not files:
        return {
            "success": True,
            "details": f"No discovery status files found (cleanup successful)",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"Found {len(files)} remaining discovery status file(s)",
        "error": "Discovery status files not removed during cleanup",
    }


def check_credentials_preserved(host) -> Dict[str, Any]:
    """Verify discovery credentials file is preserved when cleanup_credentials=false.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path()
    cred_path = f"{input_path}/{CREDENTIALS_FILE_NAME}"
    cmd = CMDS["file_exists"].format(path=cred_path)
    result = run_on_host(host, cmd)
    
    # Credentials file should exist when preserved
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"Credentials file preserved: {cred_path}",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"Credentials file not found: {cred_path}",
        "error": "Credentials file was removed when it should have been preserved",
    }


def check_log_files_removed(host) -> Dict[str, Any]:
    """Verify discovery log files are removed after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    log_dir = f"/var/log/omnia/discovery"
    
    # Check for log files
    cmd = f"find {log_dir} -name '*.log' -type f 2>/dev/null"
    result = run_on_host(host, cmd)
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    
    if not files:
        return {
            "success": True,
            "details": f"No log files found in {log_dir} (cleanup successful)",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"Found {len(files)} remaining log file(s) in {log_dir}",
        "error": "Log files not removed during cleanup",
    }


def check_log_files_preserved(host) -> Dict[str, Any]:
    """Verify discovery log files are preserved when cleanup_logs=false.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    log_dir = f"/var/log/omnia/discovery"
    
    # Check for log files
    cmd = f"find {log_dir} -name '*.log' -type f 2>/dev/null"
    result = run_on_host(host, cmd)
    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    
    # Log files should exist when preserved
    if files:
        return {
            "success": True,
            "details": f"Log files preserved: {len(files)} file(s) in {log_dir}",
            "error": "",
        }
    
    return {
        "success": False,
        "details": f"No log files found in {log_dir}",
        "error": "Log files were removed when they should have been preserved",
    }
