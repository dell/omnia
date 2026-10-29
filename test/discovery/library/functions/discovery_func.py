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

from omnia_auto import (
    read_remote_env,
    resolve_domain_data_path,
    run_on_host,
)
from ..vars.common_vars import (
    build_cmd,
    DISCOVERY_CONFIG_FILE,
    NETWORK_SPEC_FILE,
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_DISCOVERY_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    PXE_MAPPING_PATTERN,
    PXE_MAPPING_SYMLINK,
    DISCOVERY_REPORT_PATTERN,
    ORCHESTRATOR_REQUIRED_COLUMNS,
    ORCHESTRATOR_OPTIONAL_COLUMNS,
    # Dynamic functional group support (Omnia 2.3)
    is_supported_functional_group,
    parse_functional_group,
)


def _get_input_path(host) -> str:
    """Return the discovery input path for the configured project.

    Reads OMNIA_DATA_PATH and OMNIA_PROJECT_NAME from the target host's
    environment to resolve the input directory dynamically.

    Args:
        host: Testinfra host object.

    Returns:
        Absolute path to the discovery input directory.
    """
    domain_data_path = resolve_domain_data_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        domain_data_path_var=ENV_DISCOVERY_DATA_PATH,
    )
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    return f"{domain_data_path}/input/{project}"


def _get_output_path(host) -> str:
    """Return the discovery output path for the configured project.

    Reads OMNIA_DATA_PATH and OMNIA_PROJECT_NAME from the target host's
    environment to resolve the output directory dynamically.

    Args:
        host: Testinfra host object.

    Returns:
        Absolute path to the discovery output directory.
    """
    domain_data_path = resolve_domain_data_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        domain_data_path_var=ENV_DISCOVERY_DATA_PATH,
    )
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    return f"{domain_data_path}/output/{project}"


def check_input_config_exists(host) -> Dict[str, Any]:
    """Verify discovery_config.yml exists on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path(host)
    path = f"{input_path}/{DISCOVERY_CONFIG_FILE}"
    cmd = build_cmd("file_exists", path=path)
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
    input_path = _get_input_path(host)
    path = f"{input_path}/{NETWORK_SPEC_FILE}"
    cmd = build_cmd("file_exists", path=path)
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
    input_path = _get_input_path(host)
    cred_path = f"{input_path}/{CREDENTIALS_FILE_NAME}"
    cmd = build_cmd("file_exists", path=cred_path)
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
    output_path = _get_output_path(host)
    cmd = build_cmd("dir_exists", path=output_path)
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
    output_path = _get_output_path(host)
    cmd = build_cmd(
        "find_csv", path=output_path, pattern=PXE_MAPPING_PATTERN
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
    output_path = _get_output_path(host)
    symlink_path = f"{output_path}/{PXE_MAPPING_SYMLINK}"
    cmd = build_cmd("csv_header", path=symlink_path)
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
    output_path = _get_output_path(host)
    symlink_path = f"{output_path}/{PXE_MAPPING_SYMLINK}"
    cmd = build_cmd("csv_line_count", path=symlink_path)
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
    output_path = _get_output_path(host)
    cmd = build_cmd(
        "find_csv", path=output_path, pattern=DISCOVERY_REPORT_PATTERN
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
    output_path = _get_output_path(host)
    symlink_path = f"{output_path}/{PXE_MAPPING_SYMLINK}"
    cmd = build_cmd("readlink", path=symlink_path)
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
    cmd = build_cmd("dir_exists", path=clone_path)
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
    output_path = _get_output_path(host)
    cmd = build_cmd("dir_exists", path=output_path)
    result = run_on_host(host, cmd)
    
    # Directory should not exist or should be empty
    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": True,
            "details": f"Output directory removed: {output_path}",
            "error": "",
        }
    
    # If directory exists, check if it's empty
    cmd = build_cmd("ls_files", path=output_path)
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
    input_path = _get_input_path(host)
    cred_path = f"{input_path}/{CREDENTIALS_FILE_NAME}"
    cmd = build_cmd("file_exists", path=cred_path)
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
    output_path = _get_output_path(host)
    cmd = build_cmd(
        "find_csv", path=output_path, pattern=PXE_MAPPING_PATTERN
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
    output_path = _get_output_path(host)
    cmd = build_cmd(
        "find_csv", path=output_path, pattern=DISCOVERY_REPORT_PATTERN
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
    output_path = _get_output_path(host)
    cmd = build_cmd("find_csv", path=output_path, pattern="discovery_status.yml"
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
    input_path = _get_input_path(host)
    cred_path = f"{input_path}/{CREDENTIALS_FILE_NAME}"
    cmd = build_cmd("file_exists", path=cred_path)
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


# =============================================================================
# PXE Mapping Validation Functions (V007-V009, V014)
# =============================================================================


def _read_pxe_mapping_raw(host) -> Dict[str, Any]:
    """Read PXE mapping CSV and return headers and rows.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, headers (list), rows (list of lists), error.
    """
    result = {
        "success": False,
        "headers": [],
        "rows": [],
        "error": "",
    }

    output_path = _get_output_path(host)
    symlink_path = f"{output_path}/{PXE_MAPPING_SYMLINK}"

    # Read entire CSV file
    cmd = build_cmd("cat_file", path=symlink_path)
    cmd_result = run_on_host(host, cmd)

    if cmd_result.rc != 0 or not cmd_result.stdout.strip():
        result["error"] = f"Could not read PXE mapping file: {symlink_path}"
        return result

    lines = cmd_result.stdout.strip().split("\n")
    if not lines:
        result["error"] = "PXE mapping file is empty"
        return result

    result["headers"] = [h.strip() for h in lines[0].split(",")]

    for line in lines[1:]:
        if line.strip():
            result["rows"].append([v.strip() for v in line.split(",")])

    result["success"] = True
    return result


def _get_network_spec_subnets(host) -> Dict[str, Any]:
    """Get admin and IB subnets from network_spec.yml.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, admin_subnet, ib_subnet, error.
    """
    result = {
        "success": False,
        "admin_subnet": "",
        "ib_subnet": "",
        "error": "",
    }

    input_path = _get_input_path(host)
    path = f"{input_path}/{NETWORK_SPEC_FILE}"

    # Read and parse network_spec.yml
    cmd = build_cmd("cat_file", path=path)
    cmd_result = run_on_host(host, cmd)

    if cmd_result.rc != 0 or not cmd_result.stdout.strip():
        result["error"] = f"Could not read network_spec.yml: {path}"
        return result

    try:
        import yaml
        config = yaml.safe_load(cmd_result.stdout)
    except Exception as e:
        result["error"] = f"Failed to parse network_spec.yml: {e}"
        return result

    networks = config.get("Networks", [])
    for net in networks:
        if "admin_network" in net:
            result["admin_subnet"] = net["admin_network"].get("subnet", "")
        if "ib_network" in net:
            result["ib_subnet"] = net["ib_network"].get("subnet", "")

    result["success"] = True
    return result


def check_functional_groups_supported(host) -> Dict[str, Any]:
    """Verify all functional groups in PXE mapping are Omnia-supported.

    In Omnia 2.3, ALL functional groups MUST follow the pattern:
        <any_prefix>_rhel_<major>_<minor>_<arch>

    The prefix can be ANY string. The mandatory suffix is:
        _rhel_<major>_<minor>_(x86_64|aarch64)

    Valid examples:
        slurm_control_node_rhel_10_2_x86_64   ✅
        slurm_node_rhel_10_2_x86_64           ✅
        os_rhel_10_2_x86_64                   ✅
        sujal_rhel_10_0_x86_64                ✅ (custom prefix allowed)
        my_custom_group_rhel_9_4_aarch64      ✅ (any prefix allowed)

    Invalid examples:
        slurm_node_rocky_9_4_aarch64          ❌ (only rhel supported)
        slurm_node_x86_64                     ❌ (missing _rhel_<version>_)
        slurm_node                            ❌ (missing _rhel_<version>_<arch>)

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, supported_groups, unsupported_groups,
                       parsed_groups, details, error.
    """
    result = {
        "success": False,
        "supported_groups": [],
        "unsupported_groups": [],
        "parsed_groups": [],  # List of parsed group details
        "details": "",
        "error": "",
    }

    mapping = _read_pxe_mapping_raw(host)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result

    try:
        fg_idx = mapping["headers"].index("FUNCTIONAL_GROUP_NAME")
    except ValueError:
        result["error"] = "FUNCTIONAL_GROUP_NAME column not found"
        return result

    found_groups = set()
    for row in mapping["rows"]:
        if len(row) > fg_idx and row[fg_idx]:
            found_groups.add(row[fg_idx])

    # Validate each group against the Omnia 2.3 pattern
    # Pattern: <prefix>_<os>_<major>_<minor>_<arch>
    for group in found_groups:
        if is_supported_functional_group(group):
            result["supported_groups"].append(group)
            # Parse and store group details
            parsed = parse_functional_group(group)
            result["parsed_groups"].append({
                "name": group,
                "prefix": parsed["prefix"],
                "os_type": parsed["os_type"],
                "os_version": f"{parsed['os_major']}.{parsed['os_minor']}",
                "arch": parsed["arch"],
            })
        else:
            result["unsupported_groups"].append(group)

    # Sort all lists
    result["supported_groups"] = sorted(result["supported_groups"])
    result["unsupported_groups"] = sorted(result["unsupported_groups"])

    if result["unsupported_groups"]:
        result["details"] = (
            f"Found {len(result['unsupported_groups'])} unsupported groups: "
            f"{', '.join(result['unsupported_groups'])}. "
            f"All groups must follow pattern: <prefix>_<os>_<major>_<minor>_<arch> "
            f"(e.g., slurm_node_rhel_10_2_x86_64)"
        )
        result["error"] = result["details"]
    else:
        result["success"] = True
        result["details"] = (
            f"All {len(result['supported_groups'])} functional groups are valid"
        )

    return result


def check_ip_correlation(host) -> Dict[str, Any]:
    """Verify ADMIN_IP and IB_IPV4 correlation with BMC_IP based on network_spec.yml.

    IP correlation logic from discovery:
    - ADMIN_IP = admin_subnet[0:2] + bmc_ip[2:4]
    - IB_IPV4 = ib_subnet[0:2] + bmc_ip[2:4]

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, valid_count, invalid_rows, details, error.
    """
    result = {
        "success": False,
        "valid_count": 0,
        "invalid_rows": [],
        "details": "",
        "error": "",
    }

    # Get subnets from network_spec.yml
    subnets = _get_network_spec_subnets(host)
    if not subnets["success"]:
        result["error"] = subnets["error"]
        return result

    admin_subnet = subnets["admin_subnet"]
    ib_subnet = subnets["ib_subnet"]

    if not admin_subnet:
        result["error"] = "admin_subnet not found in network_spec.yml"
        return result

    mapping = _read_pxe_mapping_raw(host)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result

    headers = mapping["headers"]
    try:
        admin_ip_idx = headers.index("ADMIN_IP")
        bmc_ip_idx = headers.index("BMC_IP")
        hostname_idx = headers.index("HOSTNAME")
        ib_ip_idx = headers.index("IB_IPV4") if "IB_IPV4" in headers else (
            headers.index("IB_IP") if "IB_IP" in headers else -1
        )
    except ValueError as e:
        result["error"] = f"Required column not found: {e}"
        return result

    admin_octets = admin_subnet.split(".")
    ib_octets = ib_subnet.split(".") if ib_subnet else []

    for row in mapping["rows"]:
        if len(row) <= max(admin_ip_idx, bmc_ip_idx, hostname_idx):
            continue

        admin_ip = row[admin_ip_idx]
        bmc_ip = row[bmc_ip_idx]
        hostname = row[hostname_idx]
        ib_ip = row[ib_ip_idx] if ib_ip_idx >= 0 and len(row) > ib_ip_idx else ""

        if not admin_ip or not bmc_ip:
            continue

        bmc_parts = bmc_ip.split(".")
        admin_parts = admin_ip.split(".")

        if len(bmc_parts) != 4 or len(admin_parts) != 4:
            result["invalid_rows"].append({
                "hostname": hostname,
                "admin_ip": admin_ip,
                "bmc_ip": bmc_ip,
                "reason": "Invalid IP format",
            })
            continue

        # Expected ADMIN_IP: admin_subnet[0:2] + bmc_ip[2:4]
        expected_admin = (
            f"{admin_octets[0]}.{admin_octets[1]}."
            f"{bmc_parts[2]}.{bmc_parts[3]}"
        )

        if admin_ip != expected_admin:
            result["invalid_rows"].append({
                "hostname": hostname,
                "admin_ip": admin_ip,
                "bmc_ip": bmc_ip,
                "expected_admin_ip": expected_admin,
                "reason": f"ADMIN_IP mismatch: expected {expected_admin}",
            })
            continue

        # Check IB_IPV4 if present and ib_subnet configured
        if ib_ip and ib_octets and len(ib_octets) == 4:
            ib_parts = ib_ip.split(".")
            expected_ib = (
                f"{ib_octets[0]}.{ib_octets[1]}."
                f"{bmc_parts[2]}.{bmc_parts[3]}"
            )
            if ib_ip != expected_ib:
                result["invalid_rows"].append({
                    "hostname": hostname,
                    "ib_ip": ib_ip,
                    "bmc_ip": bmc_ip,
                    "expected_ib_ip": expected_ib,
                    "reason": f"IB_IPV4 mismatch: expected {expected_ib}",
                })
                continue

        result["valid_count"] += 1

    if result["invalid_rows"]:
        result["details"] = (
            f"{len(result['invalid_rows'])} rows have IP correlation issues"
        )
        result["error"] = result["details"]
    else:
        result["success"] = True
        result["details"] = (
            f"All {result['valid_count']} rows have valid IP correlation"
        )

    return result


def check_parent_service_tag(host) -> Dict[str, Any]:
    """Verify PARENT_SERVICE_TAG values in PXE mapping (if present).

    In Omnia 2.3, PARENT_SERVICE_TAG is NOT mandatory for any functional group.
    However, if the column exists and has values, we validate that:
    1. The referenced SERVICE_TAG exists in the PXE mapping
    2. The format is valid (non-empty string)

    If PARENT_SERVICE_TAG column is not present, the test is SKIPPED (success).

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, skipped, valid_count, invalid_rows, details, error.
    """
    result = {
        "success": False,
        "skipped": False,
        "valid_count": 0,
        "rows_with_parent": 0,
        "invalid_rows": [],
        "details": "",
        "error": "",
    }

    mapping = _read_pxe_mapping_raw(host)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result

    headers = mapping["headers"]

    # PARENT_SERVICE_TAG is optional - if not present, skip this test
    if "PARENT_SERVICE_TAG" not in headers:
        result["success"] = True
        result["skipped"] = True
        result["details"] = "PARENT_SERVICE_TAG column not present - skipped"
        return result

    try:
        st_idx = headers.index("SERVICE_TAG")
        pst_idx = headers.index("PARENT_SERVICE_TAG")
        hostname_idx = headers.index("HOSTNAME")
        fg_idx = headers.index("FUNCTIONAL_GROUP_NAME") if "FUNCTIONAL_GROUP_NAME" in headers else -1
    except ValueError as e:
        result["error"] = f"Required column not found: {e}"
        return result

    # Build set of all valid service tags in the PXE mapping
    all_service_tags = set()
    for row in mapping["rows"]:
        if len(row) > st_idx and row[st_idx]:
            all_service_tags.add(row[st_idx])

    # Validate PARENT_SERVICE_TAG values
    for row in mapping["rows"]:
        if len(row) <= max(st_idx, pst_idx, hostname_idx):
            continue

        service_tag = row[st_idx]
        parent_tag = row[pst_idx]
        hostname = row[hostname_idx]
        fg = row[fg_idx] if fg_idx >= 0 and len(row) > fg_idx else ""

        # If PARENT_SERVICE_TAG is empty, it's valid (not mandatory)
        if not parent_tag:
            result["valid_count"] += 1
            continue

        # If PARENT_SERVICE_TAG has a value, validate it
        result["rows_with_parent"] += 1

        if parent_tag not in all_service_tags:
            result["invalid_rows"].append({
                "hostname": hostname,
                "functional_group": fg,
                "service_tag": service_tag,
                "parent_service_tag": parent_tag,
                "reason": f"PARENT_SERVICE_TAG '{parent_tag}' not found in PXE mapping",
            })
        else:
            result["valid_count"] += 1

    if result["invalid_rows"]:
        result["details"] = (
            f"{len(result['invalid_rows'])} rows have invalid PARENT_SERVICE_TAG references"
        )
        result["error"] = result["details"]
    else:
        result["success"] = True
        if result["rows_with_parent"] > 0:
            result["details"] = (
                f"Validated {result['rows_with_parent']} rows with PARENT_SERVICE_TAG, "
                f"{result['valid_count']} total rows valid"
            )
        else:
            result["details"] = (
                f"PARENT_SERVICE_TAG column present but no values set - "
                f"{result['valid_count']} rows valid"
            )

    return result


def check_pxe_mapping_orchestrator_contract(host) -> Dict[str, Any]:
    """Verify PXE mapping CSV format matches Orchestrator expectations.

    This is a contract test that ensures the PXE mapping CSV can be
    consumed by the Orchestrator domain without parsing errors.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, required_columns, optional_columns,
                       missing_required, details, error.
    """
    result = {
        "success": False,
        "required_columns": [],
        "optional_columns": [],
        "missing_required": [],
        "details": "",
        "error": "",
    }

    mapping = _read_pxe_mapping_raw(host)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result

    file_headers = set(mapping["headers"])
    required_set = set(ORCHESTRATOR_REQUIRED_COLUMNS)
    optional_set = set(ORCHESTRATOR_OPTIONAL_COLUMNS)

    result["required_columns"] = sorted(list(file_headers & required_set))
    result["optional_columns"] = sorted(list(file_headers & optional_set))
    result["missing_required"] = sorted(list(required_set - file_headers))

    if result["missing_required"]:
        result["details"] = (
            f"Missing required columns for Orchestrator: "
            f"{', '.join(result['missing_required'])}"
        )
        result["error"] = result["details"]
    else:
        # Verify data integrity - check for empty required fields
        empty_field_errors = []
        for row_idx, row in enumerate(mapping["rows"], start=2):
            for col in ORCHESTRATOR_REQUIRED_COLUMNS:
                if col in mapping["headers"]:
                    col_idx = mapping["headers"].index(col)
                    if len(row) > col_idx and not row[col_idx]:
                        empty_field_errors.append(
                            f"Row {row_idx}: empty {col}"
                        )

        if empty_field_errors and len(empty_field_errors) <= 5:
            result["details"] = (
                f"Empty required fields: {'; '.join(empty_field_errors)}"
            )
            result["error"] = result["details"]
        elif empty_field_errors:
            result["details"] = (
                f"{len(empty_field_errors)} rows have empty required fields"
            )
            result["error"] = result["details"]
        else:
            result["success"] = True
            result["details"] = (
                f"Orchestrator contract satisfied: "
                f"{len(result['required_columns'])} required columns, "
                f"{len(result['optional_columns'])} optional columns present"
            )

    return result
