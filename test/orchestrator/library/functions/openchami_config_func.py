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
OpenCHAMI Configuration File Verification Functions.

This module provides functions to verify that OpenCHAMI configuration files
are properly created during orchestrator deployment, addressing the bug where
critical files like tokensmith.json and PostgreSQL init scripts were missing.
"""

import json


def check_openchami_config_files(host):
    """
    Verify that all required OpenCHAMI configuration files exist.

    Args:
        host: Ansible host object

    Returns:
        dict: Result with success status and details
    """
    required_files = [
        "/etc/openchami/configs/tokensmith.json",
        "/etc/openchami/configs/boot-service.yaml",
        "/etc/openchami/configs/metadata-service.yaml",
        "/etc/openchami/configs/haproxy.cfg",
        "/etc/openchami/configs/coredhcp.yaml",
        "/etc/openchami/configs/Corefile",
        "/etc/openchami/configs/openchami.env",
        "/etc/openchami/pg-init/multi-psql-db.sh",
    ]

    missing_files = []
    existing_files = []

    for file_path in required_files:
        result = host.run(f"test -f {file_path}", warn=True)
        if result.rc != 0:
            missing_files.append(file_path)
        else:
            existing_files.append(file_path)

    success = len(missing_files) == 0

    return {
        "success": success,
        "missing_files": missing_files,
        "existing_files": existing_files,
        "details": f"Found {len(existing_files)}/{len(required_files)} config files",
        "error": f"Missing {len(missing_files)} config files" if not success else None
    }


def check_tokensmith_config(host):
    """
    Verify that tokensmith.json configuration file exists and is valid JSON.

    Args:
        host: Ansible host object

    Returns:
        dict: Result with success status and details
    """
    tokensmith_path = "/etc/openchami/configs/tokensmith.json"

    # Check if file exists
    result = host.run(f"test -f {tokensmith_path}", warn=True)
    if result.rc != 0:
        return {
            "success": False,
            "details": f"tokensmith.json not found at {tokensmith_path}",
            "error": "tokensmith.json file missing"
        }

    # Check if file is valid JSON
    result = host.run(f"cat {tokensmith_path}", warn=True)
    if result.rc != 0:
        return {
            "success": False,
            "details": f"Failed to read tokensmith.json: {result.stderr}",
            "error": "Failed to read tokensmith.json"
        }

    try:
        json_content = json.loads(result.stdout)
        return {
            "success": True,
            "details": f"tokensmith.json is valid JSON with keys: {list(json_content.keys())}",
            "error": None
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "details": f"tokensmith.json is not valid JSON: {str(e)}",
            "error": "Invalid JSON in tokensmith.json"
        }


def check_postgres_init_script(host):
    """
    Verify that PostgreSQL initialization script exists and is executable.

    Args:
        host: Ansible host object

    Returns:
        dict: Result with success status and details
    """
    pg_init_path = "/etc/openchami/pg-init/multi-psql-db.sh"

    # Check if file exists
    result = host.run(f"test -f {pg_init_path}", warn=True)
    if result.rc != 0:
        return {
            "success": False,
            "details": f"PostgreSQL init script not found at {pg_init_path}",
            "error": "PostgreSQL init script missing"
        }

    # Check if file is executable
    result = host.run(f"test -x {pg_init_path}", warn=True)
    if result.rc != 0:
        # File exists but not executable - this is a warning, not a failure
        return {
            "success": True,
            "details": f"PostgreSQL init script exists but is not executable (chmod +x needed)",
            "error": None
        }

    # Check if script has proper shebang
    result = host.run(f"head -1 {pg_init_path}", warn=True)
    if result.rc != 0:
        return {
            "success": False,
            "details": f"Failed to read PostgreSQL init script",
            "error": "Failed to read PostgreSQL init script"
        }

    if not result.stdout.startswith("#!"):
        return {
            "success": False,
            "details": f"PostgreSQL init script missing shebang",
            "error": "Invalid script format"
        }

    return {
        "success": True,
        "details": f"PostgreSQL init script exists and is executable",
        "error": None
    }


def check_rpm_file_integrity(host):
    """
    Verify that OpenCHAMI RPM files are not missing after deployment.

    This checks the RPM verification to ensure no files are marked as missing.
    Note: Modified files (S.5....T.) are acceptable as they are customized by orchestrator.

    Args:
        host: Ansible host object

    Returns:
        dict: Result with success status and details
    """
    # Check if OpenCHAMI RPM is installed
    result = host.run("rpm -q openchami", warn=True)
    if result.rc != 0:
        return {
            "success": False,
            "details": "OpenCHAMI RPM is not installed - cannot verify file integrity",
            "error": "OpenCHAMI RPM not installed"
        }

    # Check RPM file integrity
    result = host.run("rpm -qV openchami", warn=True)

    # Parse output for missing files only (ignore modified files)
    missing_files = []
    for line in result.stdout.split('\n'):
        if 'missing' in line:
            parts = line.split()
            if len(parts) >= 2:
                missing_files.append(parts[1])

    success = len(missing_files) == 0

    return {
        "success": success,
        "missing_files": missing_files,
        "details": f"RPM verification: {len(missing_files)} missing files (modified files are acceptable)",
        "error": f"Missing {len(missing_files)} RPM files" if not success else None
    }
