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
Utils Domain — Verification Functions.

Domain-specific functions for verifying log collector and PXE boot functionality.
"""

import json
import re
import tempfile
from typing import Dict, Any, List

from ..vars.common_vars import (
    CMDS,
    FUNCTIONAL_GROUPS,
    LOG_BUNDLE_PATTERN,
    METADATA_FILE,
    FAILED_NODES_FILE,
    ISO_OUTPUT_DIR,
    CUSTOM_ISO_PATTERN,
    KICKSTART_FILE,
)


def check_target_connectivity(host) -> Dict[str, Any]:
    """Check if target host is reachable via SSH.

    Args:
        host: Testinfra host object.

    Returns:
        dict: {"success": bool, "details": str, "error": str}
    """
    try:
        result = host.run(CMDS["echo_test"])
        if result.rc == 0 and "connectivity_ok" in result.stdout:
            return {
                "success": True,
                "details": "Target host is reachable",
                "error": "",
            }
        return {
            "success": False,
            "details": "",
            "error": f"Unexpected response: {result.stdout}",
        }
    except Exception as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }


def check_env_var(host, var_name: str) -> Dict[str, Any]:
    """Check if an environment variable is set on target.

    Args:
        host: Testinfra host object.
        var_name: Name of the environment variable.

    Returns:
        dict: {"success": bool, "value": str, "error": str}
    """
    try:
        # Try sourcing the env file first
        cmd = CMDS["source_env_file"].format(env_var=var_name)
        result = host.run(cmd)

        if result.rc == 0 and result.stdout.strip():
            return {
                "success": True,
                "value": result.stdout.strip(),
                "error": "",
            }

        # Fallback to direct env check
        cmd = CMDS["env_check"].format(env_var=var_name)
        result = host.run(cmd)

        if result.rc == 0 and result.stdout.strip():
            return {
                "success": True,
                "value": result.stdout.strip(),
                "error": "",
            }

        return {
            "success": False,
            "value": "",
            "error": f"Environment variable {var_name} is not set",
        }
    except Exception as exc:
        return {
            "success": False,
            "value": "",
            "error": str(exc),
        }


def check_file_exists(host, path: str) -> Dict[str, Any]:
    """Check if a file exists on target.

    Args:
        host: Testinfra host object.
        path: Absolute path to the file.

    Returns:
        dict: {"success": bool, "details": str, "error": str}
    """
    try:
        cmd = CMDS["file_exists"].format(path=path)
        result = host.run(cmd)

        if result.rc == 0 and "exists" in result.stdout:
            return {
                "success": True,
                "details": f"File exists: {path}",
                "error": "",
            }
        return {
            "success": False,
            "details": "",
            "error": f"File not found: {path}",
        }
    except Exception as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }


def check_dir_exists(host, path: str) -> Dict[str, Any]:
    """Check if a directory exists on target.

    Args:
        host: Testinfra host object.
        path: Absolute path to the directory.

    Returns:
        dict: {"success": bool, "details": str, "error": str}
    """
    try:
        cmd = CMDS["dir_exists"].format(path=path)
        result = host.run(cmd)

        if result.rc == 0 and "exists" in result.stdout:
            return {
                "success": True,
                "details": f"Directory exists: {path}",
                "error": "",
            }
        return {
            "success": False,
            "details": "",
            "error": f"Directory not found: {path}",
        }
    except Exception as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }


def read_remote_file(host, path: str) -> Dict[str, Any]:
    """Read contents of a file on target.

    Args:
        host: Testinfra host object.
        path: Absolute path to the file.

    Returns:
        dict: {"success": bool, "content": str, "error": str}
    """
    try:
        cmd = CMDS["cat_file"].format(path=path)
        result = host.run(cmd)

        if result.rc == 0:
            return {
                "success": True,
                "content": result.stdout,
                "error": "",
            }
        return {
            "success": False,
            "content": "",
            "error": f"Failed to read file: {path}",
        }
    except Exception as exc:
        return {
            "success": False,
            "content": "",
            "error": str(exc),
        }


def validate_yaml_file(host, path: str) -> Dict[str, Any]:
    """Validate that a file contains valid YAML.

    Args:
        host: Testinfra host object.
        path: Absolute path to the YAML file.

    Returns:
        dict: {"success": bool, "data": dict, "error": str}
    """
    try:
        file_result = read_remote_file(host, path)
        if not file_result["success"]:
            return {
                "success": False,
                "data": {},
                "error": file_result["error"],
            }

        import yaml
        data = yaml.safe_load(file_result["content"])

        if data is None:
            data = {}

        return {
            "success": True,
            "data": data,
            "error": "",
        }
    except yaml.YAMLError as exc:
        return {
            "success": False,
            "data": {},
            "error": f"Invalid YAML: {exc}",
        }
    except Exception as exc:
        return {
            "success": False,
            "data": {},
            "error": str(exc),
        }


def validate_collect_pxe_file(host, path: str) -> Dict[str, Any]:
    """Validate collect_pxe.yml file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to collect_pxe.yml.

    Returns:
        dict: {"success": bool, "groups": list, "invalid_groups": list, "error": str}
    """
    yaml_result = validate_yaml_file(host, path)
    if not yaml_result["success"]:
        return {
            "success": False,
            "groups": [],
            "invalid_groups": [],
            "error": yaml_result["error"],
        }

    data = yaml_result["data"]
    found_groups = []
    invalid_groups = []

    for key in data.keys():
        if key in FUNCTIONAL_GROUPS:
            found_groups.append(key)
        else:
            invalid_groups.append(key)

    return {
        "success": len(invalid_groups) == 0,
        "groups": found_groups,
        "invalid_groups": invalid_groups,
        "error": f"Invalid groups: {invalid_groups}" if invalid_groups else "",
    }


def find_log_bundle(host, output_dir: str) -> Dict[str, Any]:
    """Find log bundle tar.gz file in output directory.

    Args:
        host: Testinfra host object.
        output_dir: Path to the output directory.

    Returns:
        dict: {"success": bool, "bundle_path": str, "error": str}
    """
    try:
        # First check if output directory exists
        check_result = check_dir_exists(host, output_dir)
        if not check_result["success"]:
            return {
                "success": False,
                "bundle_path": "",
                "error": f"Output directory not found: {output_dir}",
            }

        # Debug: list directory contents
        ls_cmd = f"ls -la {output_dir}"
        ls_result = host.run(ls_cmd)

        # Use a simple approach: find any tar.gz file
        cmd = f"find {output_dir} -type f -name '*.tar.gz' 2>/dev/null"
        result = host.run(cmd)

        if result.rc == 0 and result.stdout.strip():
            bundles = result.stdout.strip().split("\n")
            if bundles:
                # Return the first bundle found
                return {
                    "success": True,
                    "bundle_path": bundles[0],
                    "error": "",
                }

        return {
            "success": False,
            "bundle_path": "",
            "error": f"No log bundle found in output directory: {output_dir}. Directory listing: {ls_result.stdout}",
        }
    except Exception as exc:
        return {
            "success": False,
            "bundle_path": "",
            "error": str(exc),
        }


def validate_metadata_file(host, path: str) -> Dict[str, Any]:
    """Validate metadata.json file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to metadata.json.

    Returns:
        dict: {"success": bool, "data": dict, "has_sha256": bool, "error": str}
    """
    try:
        file_result = read_remote_file(host, path)
        if not file_result["success"]:
            return {
                "success": False,
                "data": {},
                "has_sha256": False,
                "error": file_result["error"],
            }

        data = json.loads(file_result["content"])

        # Check for required fields (updated to match actual metadata structure)
        required_fields = ["bundle_name"]
        missing = [f for f in required_fields if f not in data]

        if missing:
            return {
                "success": False,
                "data": data,
                "has_sha256": "tar_sha256" in data,
                "error": f"Missing required fields: {missing}",
            }

        return {
            "success": True,
            "data": data,
            "has_sha256": "tar_sha256" in data,
            "error": "",
        }
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "data": {},
            "has_sha256": False,
            "error": f"Invalid JSON: {exc}",
        }
    except Exception as exc:
        return {
            "success": False,
            "data": {},
            "has_sha256": False,
            "error": str(exc),
        }


def validate_tar_contents(host, tar_path: str, expected_dirs: List[str]) -> Dict[str, Any]:
    """Validate tar.gz bundle contains expected directories.

    Args:
        host: Testinfra host object.
        tar_path: Path to the tar.gz file.
        expected_dirs: List of expected directory names.

    Returns:
        dict: {"success": bool, "found_dirs": list, "missing_dirs": list, "error": str}
    """
    try:
        cmd = CMDS["tar_list"].format(path=tar_path)
        result = host.run(cmd)

        if result.rc != 0:
            return {
                "success": False,
                "found_dirs": [],
                "missing_dirs": expected_dirs,
                "error": f"Failed to list tar contents: {result.stderr}",
            }

        contents = result.stdout.strip().split("\n")
        found_dirs = []
        missing_dirs = []

        for expected in expected_dirs:
            found = any(expected in line for line in contents)
            if found:
                found_dirs.append(expected)
            else:
                missing_dirs.append(expected)

        return {
            "success": len(missing_dirs) == 0,
            "found_dirs": found_dirs,
            "missing_dirs": missing_dirs,
            "error": f"Missing directories: {missing_dirs}" if missing_dirs else "",
        }
    except Exception as exc:
        return {
            "success": False,
            "found_dirs": [],
            "missing_dirs": expected_dirs,
            "error": str(exc),
        }


def validate_pxe_config(host, path: str) -> Dict[str, Any]:
    """Validate set_pxe_boot_config.yml file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to set_pxe_boot_config.yml.

    Returns:
        dict: {"success": bool, "config": dict, "error": str}
    """
    yaml_result = validate_yaml_file(host, path)
    if not yaml_result["success"]:
        return {
            "success": False,
            "config": {},
            "error": yaml_result["error"],
        }

    data = yaml_result["data"]

    # Check for expected fields (all have defaults, so just validate types)
    expected_fields = {
        "enable_phone_home": bool,
        "phone_home_pause_minutes": int,
        "phone_home_retries": int,
        "phone_home_delay": int,
        "restart_host": bool,
        "force_restart": bool,
    }

    errors = []
    for field, expected_type in expected_fields.items():
        if field in data and not isinstance(data[field], expected_type):
            errors.append(f"{field} should be {expected_type.__name__}")

    if errors:
        return {
            "success": False,
            "config": data,
            "error": "; ".join(errors),
        }

    return {
        "success": True,
        "config": data,
        "error": "",
    }


def validate_ini_inventory(host, path: str) -> Dict[str, Any]:
    """Validate INI inventory file format.

    Args:
        host: Testinfra host object.
        path: Absolute path to the INI file.

    Returns:
        dict: {"success": bool, "hosts": list, "error": str}
    """
    try:
        file_result = read_remote_file(host, path)
        if not file_result["success"]:
            return {
                "success": False,
                "hosts": [],
                "error": file_result["error"],
            }

        content = file_result["content"]
        lines = content.strip().split("\n")

        # Check for [bmc] section
        has_bmc_section = any(line.strip() == "[bmc]" for line in lines)
        if not has_bmc_section:
            return {
                "success": False,
                "hosts": [],
                "error": "Missing [bmc] section in inventory",
            }

        # Parse hosts
        hosts = []
        in_bmc_section = False
        for line in lines:
            line = line.strip()
            if line == "[bmc]":
                in_bmc_section = True
                continue
            if line.startswith("["):
                in_bmc_section = False
                continue
            if in_bmc_section and line and not line.startswith("#"):
                # Extract host IP (first word)
                parts = line.split()
                if parts:
                    hosts.append(parts[0])

        if not hosts:
            return {
                "success": False,
                "hosts": [],
                "error": "No hosts found in [bmc] section",
            }

        return {
            "success": True,
            "hosts": hosts,
            "error": "",
        }
    except Exception as exc:
        return {
            "success": False,
            "hosts": [],
            "error": str(exc),
        }


def validate_failed_nodes_json(host, path: str) -> Dict[str, Any]:
    """Validate failed_nodes.json file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to failed_nodes.json.

    Returns:
        dict: {"success": bool, "data": dict, "error": str}
    """
    try:
        file_result = read_remote_file(host, path)
        if not file_result["success"]:
            return {
                "success": False,
                "data": {},
                "error": file_result["error"],
            }

        data = json.loads(file_result["content"])

        # Check for required fields
        required_fields = ["timestamp", "total_nodes", "failure_count", "success_count"]
        missing = [f for f in required_fields if f not in data]

        if missing:
            return {
                "success": False,
                "data": data,
                "error": f"Missing required fields: {missing}",
            }

        return {
            "success": True,
            "data": data,
            "error": "",
        }
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "data": {},
            "error": f"Invalid JSON: {exc}",
        }
    except Exception as exc:
        return {
            "success": False,
            "data": {},
            "error": str(exc),
        }


def get_hostname(host) -> Dict[str, Any]:
    """Get hostname from target.

    Args:
        host: Testinfra host object.

    Returns:
        dict: {"success": bool, "hostname": str, "domain": str, "error": str}
    """
    try:
        hostname_result = host.run(CMDS["hostname_short"])
        domain_result = host.run(CMDS["hostname_domain"])

        hostname = hostname_result.stdout.strip() if hostname_result.rc == 0 else ""
        domain = domain_result.stdout.strip() if domain_result.rc == 0 else ""

        return {
            "success": bool(hostname),
            "hostname": hostname,
            "domain": domain,
            "error": "" if hostname else "Failed to get hostname",
        }
    except Exception as exc:
        return {
            "success": False,
            "hostname": "",
            "domain": "",
            "error": str(exc),
        }


def check_admin_ip_assigned(host, admin_ip: str) -> Dict[str, Any]:
    """Check if admin IP is assigned to a network interface.

    Args:
        host: Testinfra host object.
        admin_ip: The admin IP address to check.

    Returns:
        dict: {"success": bool, "interface": str, "error": str}
    """
    try:
        result = host.run(CMDS["hostname_ip"])
        if result.rc != 0:
            return {
                "success": False,
                "interface": "",
                "error": "Failed to get IP addresses",
            }

        ips = result.stdout.strip().split()
        if admin_ip in ips:
            return {
                "success": True,
                "interface": "detected",
                "error": "",
            }

        return {
            "success": False,
            "interface": "",
            "error": f"Admin IP {admin_ip} not assigned to any interface",
        }
    except Exception as exc:
        return {
            "success": False,
            "interface": "",
            "error": str(exc),
        }


def validate_iso_config(host, path: str) -> Dict[str, Any]:
    """Validate iso_config.yml file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to iso_config.yml.

    Returns:
        dict: {"success": bool, "config": dict, "error": str}
    """
    yaml_result = validate_yaml_file(host, path)
    if not yaml_result["success"]:
        return {
            "success": False,
            "config": {},
            "error": yaml_result["error"],
        }

    data = yaml_result["data"]

    # Check for expected fields
    expected_fields = [
        "iso_source_path",
        "iso_nfs_share",
        "ks_ssh_public_key",
        "ks_hostname",
        "ks_static_ip",
    ]

    errors = []
    for field in expected_fields:
        if field not in data or not data[field]:
            errors.append(f"{field} is missing or empty")

    if errors:
        return {
            "success": False,
            "config": data,
            "error": "; ".join(errors),
        }

    return {
        "success": True,
        "config": data,
        "error": "",
    }


def validate_os_install_credentials(host, path: str) -> Dict[str, Any]:
    """Validate os_install_credentials.yml file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to os_install_credentials.yml.

    Returns:
        dict: {"success": bool, "credentials": dict, "error": str}
    """
    yaml_result = validate_yaml_file(host, path)
    if not yaml_result["success"]:
        return {
            "success": False,
            "credentials": {},
            "error": yaml_result["error"],
        }

    data = yaml_result["data"]

    # Check for expected fields
    expected_fields = ["bmc_username", "bmc_password", "os_root_password"]

    errors = []
    for field in expected_fields:
        if field not in data or not data[field]:
            errors.append(f"{field} is missing or empty")

    if errors:
        return {
            "success": False,
            "credentials": data,
            "error": "; ".join(errors),
        }

    return {
        "success": True,
        "credentials": data,
        "error": "",
    }


def find_custom_iso(host, output_dir: str) -> Dict[str, Any]:
    """Find custom ISO file in output directory.

    Args:
        host: Testinfra host object.
        output_dir: Path to the output directory.

    Returns:
        dict: {"success": bool, "iso_path": str, "error": str}
    """
    try:
        cmd = CMDS["find_files"].format(path=output_dir, pattern="omnia_custom_*.iso")
        result = host.run(cmd)

        if result.rc == 0 and result.stdout.strip():
            isos = result.stdout.strip().split("\n")
            if isos:
                # Return the most recent ISO (last in sorted list)
                isos.sort()
                return {
                    "success": True,
                    "iso_path": isos[-1],
                    "error": "",
                }

        return {
            "success": False,
            "iso_path": "",
            "error": "No custom ISO found in output directory",
        }
    except Exception as exc:
        return {
            "success": False,
            "iso_path": "",
            "error": str(exc),
        }


def verify_iso_checksum(host, iso_path: str, expected_checksum: str) -> Dict[str, Any]:
    """Verify ISO checksum matches expected value.

    Args:
        host: Testinfra host object.
        iso_path: Path to the ISO file.
        expected_checksum: Expected SHA-256 checksum.

    Returns:
        dict: {"success": bool, "actual_checksum": str, "error": str}
    """
    try:
        cmd = f"sha256sum {iso_path} 2>/dev/null"
        result = host.run(cmd)

        if result.rc != 0:
            return {
                "success": False,
                "actual_checksum": "",
                "error": f"Failed to calculate checksum: {result.stderr}",
            }

        actual_checksum = result.stdout.strip().split()[0] if result.stdout.strip() else ""

        if actual_checksum == expected_checksum:
            return {
                "success": True,
                "actual_checksum": actual_checksum,
                "error": "",
            }

        return {
            "success": False,
            "actual_checksum": actual_checksum,
            "error": f"Checksum mismatch",
        }
    except Exception as exc:
        return {
            "success": False,
            "actual_checksum": "",
            "error": str(exc),
        }


def verify_kickstart_in_iso(host, iso_path: str) -> Dict[str, Any]:
    """Verify Kickstart configuration is injected into ISO.

    Args:
        host: Testinfra host object.
        iso_path: Path to the ISO file.

    Returns:
        dict: {"success": bool, "found": bool, "error": str}
    """
    try:
        # Mount ISO temporarily and check for kickstart file
        mount_point = tempfile.mkdtemp(prefix="iso_verify_")  # nosec B108
        mkdir_cmd = CMDS["mkdir_p"].format(path=mount_point)
        host.run(mkdir_cmd)

        mount_cmd = f"mount -o ro {iso_path} {mount_point} 2>/dev/null"
        mount_result = host.run(mount_cmd)

        if mount_result.rc != 0:
            return {
                "success": False,
                "found": False,
                "error": f"Failed to mount ISO: {mount_result.stderr}",
            }

        # Check for kickstart file
        ks_path = f"{mount_point}/{KICKSTART_FILE}"
        ks_result = host.run(CMDS["file_exists"].format(path=ks_path))

        # Unmount
        umount_cmd = CMDS["umount"].format(flags="", path=mount_point)
        host.run(umount_cmd)

        # Clean up temp directory
        rm_cmd = CMDS["rm_dir"].format(path=mount_point)
        host.run(rm_cmd)

        if ks_result.rc == 0 and "exists" in ks_result.stdout:
            return {
                "success": True,
                "found": True,
                "error": "",
            }

        return {
            "success": True,
            "found": False,
            "error": "",
        }
    except Exception as exc:
        return {
            "success": False,
            "found": False,
            "error": str(exc),
        }
