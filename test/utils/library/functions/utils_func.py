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
import yaml
from typing import Dict, Any, List

from ..vars.common_vars import (
    CMDS,
    FUNCTIONAL_GROUPS,
    LOG_BUNDLE_PATTERN,
    METADATA_FILE,
    CUSTOM_ISO_PATTERN,
    KICKSTART_FILE,
    INSTALL_OS_STATUS_FILE,
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

        # Use a simple approach: find any tar.gz file and sort by modification time (newest first)
        cmd = f"find {output_dir} -type f -name '*.tar.gz' 2>/dev/null | xargs ls -t 2>/dev/null | head -1"
        result = host.run(cmd)

        if result.rc == 0 and result.stdout.strip():
            bundle_path = result.stdout.strip()
            return {
                "success": True,
                "bundle_path": bundle_path,
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

def validate_bundle_log_files(host, tar_path: str) -> Dict[str, Any]:
    """Validate log bundle contains log files from log_collector role based on input configuration.

    Args:
        host: Testinfra host object.
        tar_path: Path to the tar.gz file.

    Returns:
        dict: {
            "success": bool,
            "collected_files": list,
            "empty_files": list,
            "missing_files": list,
            "error": str
        }
    """
    try:
        # Extract bundle to temp directory
        temp_dir = "/tmp/log_bundle_verify"
        extract_cmd = f"rm -rf {temp_dir} && mkdir -p {temp_dir} && tar -xzf {tar_path} -C {temp_dir}"
        result = host.run(extract_cmd)

        if result.rc != 0:
            return {
                "success": False,
                "collected_files": [],
                "empty_files": [],
                "missing_files": [],
                "error": f"Failed to extract bundle: {result.stderr}",
            }

        # Read collect_pxe.yml to determine which groups have nodes
        # Use the standard input path
        input_path = "/opt/omnia/utils/input/project_default"
        collect_pxe_file = f"{input_path}/collect_pxe.yml"
        
        read_cmd = f"cat {collect_pxe_file}"
        result = host.run(read_cmd)
        
        if result.rc != 0:
            return {
                "success": False,
                "collected_files": [],
                "empty_files": [],
                "missing_files": [],
                "error": f"Failed to read collect_pxe.yml: {result.stderr}",
            }
        
        config_content = result.stdout
        
        # Parse YAML to check which groups have nodes
        try:
            config = yaml.safe_load(config_content)
        except:
            config = {}
        
        # Determine which groups have nodes based on input file
        has_k8s = False
        has_slurm = False
        
        if config:
            # Check K8s groups
            k8s_groups = ["service_kube_control_plane_x86_64", "service_kube_node_x86_64"]
            for group in k8s_groups:
                if group in config and config[group] and len(config[group]) > 0:
                    has_k8s = True
                    break
            
            # Check Slurm groups
            slurm_groups = ["slurm_control_node_x86_64", "slurm_node_x86_64", 
                           "login_node_x86_64", "login_compiler_node_aarch64"]
            for group in slurm_groups:
                if group in config and config[group] and len(config[group]) > 0:
                    has_slurm = True
                    break

        collected_files = []
        empty_files = []
        missing_files = []

        # Find all log files in k8s and slurm directories
        # First, check if the directories exist
        k8s_exists_cmd = f"test -d {temp_dir}/k8s && echo 'yes' || echo 'no'"
        k8s_result = host.run(k8s_exists_cmd)
        
        slurm_exists_cmd = f"test -d {temp_dir}/slurm && echo 'yes' || echo 'no'"
        slurm_result = host.run(slurm_exists_cmd)
        
        # Find all log files in k8s and slurm directories
        find_cmd = f"find {temp_dir} -type f -name '*.log' 2>/dev/null"
        result = host.run(find_cmd)

        if result.rc != 0:
            return {
                "success": False,
                "collected_files": [],
                "empty_files": [],
                "missing_files": [],
                "error": f"Failed to find log files: {result.stderr}",
            }

        found_files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        for found_file in found_files:
            if not found_file:
                continue

            # Check if file has content
            size_cmd = f"stat -c %s {found_file} 2>/dev/null || echo 0"
            size_result = host.run(size_cmd)
            file_size = int(size_result.stdout.strip()) if size_result.stdout.strip() else 0

            relative_path = found_file.replace(temp_dir + "/", "")
            if file_size > 0:
                collected_files.append(relative_path)
            else:
                empty_files.append(relative_path)

        # Add information about which groups were expected
        if has_k8s and k8s_result.stdout.strip() == "no":
            missing_files.append("k8s log files (expected but not found)")
        if has_slurm and slurm_result.stdout.strip() == "no":
            missing_files.append("slurm log files (expected but not found)")

        # Clean up temp directory
        host.run(f"rm -rf {temp_dir}")

        return {
            "success": True,
            "collected_files": collected_files,
            "empty_files": empty_files,
            "missing_files": missing_files,
            "error": "",
        }
    except Exception as exc:
        return {
            "success": False,
            "collected_files": [],
            "empty_files": [],
            "missing_files": [],
            "error": str(exc),
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


def validate_install_os_config(host, path: str) -> Dict[str, Any]:
    """Validate install_os_config.yml file structure.

    This config supports multiple execution modes, so we only enforce:
      - YAML is valid
      - key types are sane (where present)

    Args:
        host: Testinfra host object.
        path: Absolute path to install_os_config.yml.

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

    expected_types = {
        "kickstart_delivery_method": str,
        "kickstart_file": str,
        "kickstart_template": str,
        "rebuild_iso": bool,
        "force_reinstall": bool,
        "ssh_verify_enabled": bool,
        "ssh_verify_retries": int,
        "ssh_verify_delay": int,
    }

    errors = []
    for key, typ in expected_types.items():
        if key in data and data[key] is not None and not isinstance(data[key], typ):
            errors.append(f"{key} should be {typ.__name__}")

    return {
        "success": len(errors) == 0,
        "config": data,
        "error": "; ".join(errors),
    }


def validate_install_os_credentials(host, path: str) -> Dict[str, Any]:
    """Validate install_os_credentials.yml file structure.

    Args:
        host: Testinfra host object.
        path: Absolute path to install_os_credentials.yml.

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

    expected_fields = ["bmc_username", "bmc_password", "os_root_password"]
    missing = [f for f in expected_fields if not data.get(f)]

    if missing:
        return {
            "success": False,
            "credentials": data,
            "error": f"Missing or empty fields: {missing}",
        }

    return {
        "success": True,
        "credentials": data,
        "error": "",
    }


def find_custom_iso(host, output_dir: str) -> Dict[str, Any]:
    """Find custom ISO file in output directory.

    Pattern is based on the new utils/install_os behavior ("*-omnia.iso").

    Args:
        host: Testinfra host object.
        output_dir: Path to the output directory.

    Returns:
        dict: {"success": bool, "iso_path": str, "error": str}
    """
    try:
        cmd = CMDS["find_files"].format(path=output_dir, pattern="*.iso")
        result = host.run(cmd)

        if result.rc == 0 and result.stdout.strip():
            isos = [p for p in result.stdout.strip().split("\n") if p]
            # Prefer -omnia.iso output
            candidates = [p for p in isos if re.search(CUSTOM_ISO_PATTERN, p)]
            candidates = candidates or isos
            candidates.sort()
            return {
                "success": True,
                "iso_path": candidates[-1],
                "error": "",
            }

        return {
            "success": False,
            "iso_path": "",
            "error": f"No ISO found in output directory: {output_dir}",
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

    We avoid mounting ISOs in test automation (requires loop mount privileges).
    Instead, we attempt to use `isoinfo` if present.

    Args:
        host: Testinfra host object.
        iso_path: Path to the ISO file.

    Returns:
        dict: {"success": bool, "found": bool, "error": str}
    """
    try:
        which = host.run("command -v isoinfo 2>/dev/null")
        if which.rc != 0:
            return {
                "success": False,
                "found": False,
                "error": "isoinfo not available (install genisoimage/xorriso tools)",
            }

        cmd = f"isoinfo -i '{iso_path}' -R -f 2>/dev/null | grep -i '{KICKSTART_FILE}'"
        result = host.run(cmd)
        return {
            "success": True,
            "found": result.rc == 0,
            "error": "",
        }
    except Exception as exc:
        return {
            "success": False,
            "found": False,
            "error": str(exc),
        }
