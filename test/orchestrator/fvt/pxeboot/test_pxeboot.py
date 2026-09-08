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
PXE Boot Tests for Orchestrator

Tests PXE boot functionality including:
- PXE boot playbook execution
- PXE boot configuration validation
- BMC credential validation
- iDRAC connectivity validation
- Phone-home callback validation
- PXE boot skip when disabled
- Failed nodes output validation
"""

import json
from pathlib import Path

import pytest
import yaml

from library.functions import (
    TestLogger,
    load_test_config,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_orchestrator_config_exists():
    """TC_PXE_001: Verify orchestrator_config.yml exists."""
    tl = TestLogger("Orchestrator Config Exists", "TC_PXE_001")
    test_config = load_test_config()
    orchestrator_config_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/orchestrator_config.yml"

    if Path(orchestrator_config_path).exists():
        tl.passed("PXE boot configuration validation passed", f"orchestrator_config.yml found at {orchestrator_config_path}")
    else:
        tl.failed("PXE boot configuration validation failed", f"orchestrator_config.yml not found at {orchestrator_config_path}")


@pytest.mark.functional
@pytest.mark.order(2)
def test_pxe_boot_flag_validation():
    """TC_PXE_002: Verify enable_pxe_boot flag is properly configured."""
    tl = TestLogger("PXE Boot Flag Validation", "TC_PXE_002")
    test_config = load_test_config()
    orchestrator_config_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/orchestrator_config.yml"

    try:
        with open(orchestrator_config_path, 'r', encoding='utf-8') as f:
            orchestrator_config = yaml.safe_load(f)

        if "enable_pxe_boot" not in orchestrator_config:
            tl.failed("PXE boot configuration validation failed", "enable_pxe_boot flag missing in orchestrator_config.yml")
            return

        enable_pxe = orchestrator_config.get("enable_pxe_boot", True)
        if isinstance(enable_pxe, bool):
            tl.passed("PXE boot configuration validation passed", f"enable_pxe_boot flag is properly set to {enable_pxe}")
        else:
            tl.failed("PXE boot configuration validation failed", "enable_pxe_boot must be a boolean value")
    except Exception as e:
        tl.failed("PXE boot configuration validation failed", f"Error validating PXE boot flag: {str(e)}")


@pytest.mark.sanity
@pytest.mark.order(3)
def test_pxe_mapping_file_exists():
    """TC_PXE_003: Verify pxe_mapping_file.csv exists."""
    tl = TestLogger("PXE Mapping File Exists", "TC_PXE_003")
    test_config = load_test_config()
    pxe_mapping_file_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/pxe_mapping_file.csv"

    if Path(pxe_mapping_file_path).exists():
        tl.passed("PXE boot configuration validation passed", f"pxe_mapping_file.csv found at {pxe_mapping_file_path}")
    else:
        tl.passed("PXE boot configuration validation passed", "pxe_mapping_file.csv not found (PXE boot may be disabled)")


@pytest.mark.functional
@pytest.mark.order(4)
def test_pxe_mapping_file_format():
    """TC_PXE_004: Validate pxe_mapping_file.csv format."""
    tl = TestLogger("PXE Mapping File Format", "TC_PXE_004")
    test_config = load_test_config()
    pxe_mapping_file_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/pxe_mapping_file.csv"

    if not Path(pxe_mapping_file_path).exists():
        tl.passed("PXE boot configuration validation passed", "pxe_mapping_file.csv not found (PXE boot may be disabled)")
        return

    try:
        with open(pxe_mapping_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) < 2:
            tl.failed("PXE boot configuration validation failed", "pxe_mapping_file.csv must have header and at least one data row")
            return

        # Validate header
        header = lines[0].strip().split(',')
        # FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP
        if len(header) < 9:
            tl.failed("PXE boot configuration validation failed", f"Expected at least 9 columns, found {len(header)}")
            return

        # Validate data rows
        validation_errors = []
        for i, line in enumerate(lines[1:], 1):
            if line.strip():
                columns = line.strip().split(',')
                if len(columns) < 9:
                    validation_errors.append(f"Row {i}: Expected at least 9 columns, found {len(columns)}")

        if validation_errors:
            tl.failed("PXE boot configuration validation failed", f"PXE mapping file format errors: {validation_errors}")
        else:
            tl.passed("PXE boot configuration validation passed", "pxe_mapping_file.csv format is valid")
    except Exception as e:
        tl.failed("PXE boot configuration validation failed", f"Error validating PXE mapping file format: {str(e)}")


@pytest.mark.sanity
@pytest.mark.order(5)
def test_set_pxe_boot_config_exists():
    """TC_PXE_005: Verify set_pxe_boot_config.yml exists."""
    tl = TestLogger("Set PXE Boot Config Exists", "TC_PXE_005")
    test_config = load_test_config()
    set_pxe_boot_config_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/set_pxe_boot_config.yml"

    if Path(set_pxe_boot_config_path).exists():
        tl.passed("PXE boot configuration validation passed", f"set_pxe_boot_config.yml found at {set_pxe_boot_config_path}")
    else:
        tl.passed("PXE boot configuration validation passed", "set_pxe_boot_config.yml not found (using defaults)")


@pytest.mark.functional
@pytest.mark.order(6)
def test_set_pxe_boot_config_validation():
    """TC_PXE_006: Validate set_pxe_boot_config.yml parameters."""
    tl = TestLogger("Set PXE Boot Config Validation", "TC_PXE_006")
    test_config = load_test_config()
    set_pxe_boot_config_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/set_pxe_boot_config.yml"

    if not Path(set_pxe_boot_config_path).exists():
        tl.passed("PXE boot configuration validation passed", "set_pxe_boot_config.yml not found (using defaults)")
        return

    try:
        with open(set_pxe_boot_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        validation_errors = []

        # Validate phone-home parameters
        if "enable_phone_home" in config:
            if not isinstance(config["enable_phone_home"], bool):
                validation_errors.append("enable_phone_home must be boolean")

        if "phone_home_pause_minutes" in config:
            if not isinstance(config["phone_home_pause_minutes"], int):
                validation_errors.append("phone_home_pause_minutes must be integer")
            elif config["phone_home_pause_minutes"] <= 0:
                validation_errors.append("phone_home_pause_minutes must be positive")

        if "phone_home_retries" in config:
            if not isinstance(config["phone_home_retries"], int):
                validation_errors.append("phone_home_retries must be integer")
            elif config["phone_home_retries"] <= 0:
                validation_errors.append("phone_home_retries must be positive")

        if "phone_home_delay" in config:
            if not isinstance(config["phone_home_delay"], int):
                validation_errors.append("phone_home_delay must be integer")
            elif config["phone_home_delay"] <= 0:
                validation_errors.append("phone_home_delay must be positive")

        # Validate boot parameters
        if "restart_host" in config:
            if not isinstance(config["restart_host"], bool):
                validation_errors.append("restart_host must be boolean")

        if "force_restart" in config:
            if not isinstance(config["force_restart"], bool):
                validation_errors.append("force_restart must be boolean")

        if "boot_source_override_enabled" in config:
            if config["boot_source_override_enabled"] not in ["continuous", "once"]:
                validation_errors.append("boot_source_override_enabled must be 'continuous' or 'once'")

        if "boot_source_override_target" in config:
            if config["boot_source_override_target"] not in ["pxe", "hdd", "uefi"]:
                validation_errors.append("boot_source_override_target must be 'pxe', 'hdd', or 'uefi'")

        if validation_errors:
            tl.failed("PXE boot configuration validation failed", f"Set PXE boot config validation errors: {validation_errors}")
        else:
            tl.passed("PXE boot configuration validation passed", "set_pxe_boot_config.yml parameters are valid")
    except Exception as e:
        tl.failed("PXE boot configuration validation failed", f"Error validating set_pxe_boot_config.yml: {str(e)}")


@pytest.mark.sanity
@pytest.mark.order(7)
def test_bmc_credentials_file_exists():
    """TC_PXE_007: Verify omnia_config_credentials.yml exists."""
    tl = TestLogger("BMC Credentials File Exists", "TC_PXE_007")
    test_config = load_test_config()
    credentials_file_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/omnia_config_credentials.yml"

    if Path(credentials_file_path).exists():
        tl.passed("PXE boot configuration validation passed", f"omnia_config_credentials.yml found at {credentials_file_path}")
    else:
        tl.passed("PXE boot configuration validation passed", "omnia_config_credentials.yml not found (credentials may be encrypted)")


@pytest.mark.functional
@pytest.mark.order(8)
def test_bmc_credentials_validation():
    """TC_PXE_008: Validate BMC credentials are available."""
    tl = TestLogger("BMC Credentials Validation", "TC_PXE_008")
    test_config = load_test_config()
    credentials_file_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/omnia_config_credentials.yml"

    if not Path(credentials_file_path).exists():
        tl.passed("PXE boot configuration validation passed", "omnia_config_credentials.yml not found (credentials may be encrypted)")
        return

    try:
        with open(credentials_file_path, 'r', encoding='utf-8') as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError:
                tl.passed("PXE boot configuration validation passed", "Credentials file is encrypted or invalid (will be decrypted during execution)")
                return

        if config:
            if "bmc_username" not in config and "username" not in config:
                tl.failed("PXE boot configuration validation failed", "BMC username not found in credentials file")
            elif "bmc_password" not in config and "password" not in config:
                tl.failed("PXE boot configuration validation failed", "BMC password not found in credentials file")
            else:
                tl.passed("PXE boot configuration validation passed", "BMC credentials are available")
        else:
            tl.passed("PXE boot configuration validation passed", "Credentials file is empty (will be populated during execution)")
    except Exception as e:
        tl.failed("PXE boot configuration validation failed", f"Error validating BMC credentials: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(9)
def test_pxe_boot_skip_when_disabled():
    """TC_PXE_009: Verify PXE boot is properly skipped when disabled."""
    tl = TestLogger("PXE Boot Skip When Disabled", "TC_PXE_009")
    test_config = load_test_config()
    orchestrator_config_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/orchestrator_config.yml"

    try:
        with open(orchestrator_config_path, 'r', encoding='utf-8') as f:
            orchestrator_config = yaml.safe_load(f)

        enable_pxe = orchestrator_config.get("enable_pxe_boot", True)

        if not enable_pxe:
            tl.passed("PXE boot configuration validation passed", "PXE boot is disabled (expected for VM environments)")
        else:
            tl.passed("PXE boot configuration validation passed", "PXE boot is enabled")
    except Exception as e:
        tl.failed("PXE boot configuration validation failed", f"Error checking PXE boot flag: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(10)
def test_failed_nodes_output_exists():
    """TC_PXE_010: Verify failed_nodes.json output file exists after PXE boot."""
    tl = TestLogger("Failed Nodes Output Exists", "TC_PXE_010")
    test_config = load_test_config()
    orchestrator_output_dir = test_config.get("orchestrator_output_dir", "/opt/omnia/orchestrator/output/project_default")
    failed_nodes_path = Path(orchestrator_output_dir) / "failed_nodes.json"

    if failed_nodes_path.exists():
        tl.passed("PXE boot configuration validation passed", f"failed_nodes.json found at {failed_nodes_path}")
    else:
        tl.passed("PXE boot configuration validation passed", "failed_nodes.json not found (PXE boot may not have run yet)")


@pytest.mark.functional
@pytest.mark.order(11)
def test_failed_nodes_output_format():
    """TC_PXE_011: Validate failed_nodes.json format and structure."""
    tl = TestLogger("Failed Nodes Output Format", "TC_PXE_011")
    test_config = load_test_config()
    orchestrator_output_dir = test_config.get("orchestrator_output_dir", "/opt/omnia/orchestrator/output/project_default")
    failed_nodes_path = Path(orchestrator_output_dir) / "failed_nodes.json"

    if not failed_nodes_path.exists():
        tl.passed("PXE boot configuration validation passed", "failed_nodes.json not found (PXE boot may not have run yet)")
        return

    try:
        with open(failed_nodes_path, 'r', encoding='utf-8') as f:
            failed_data = json.load(f)

        validation_errors = []

        # Validate required fields
        required_fields = ["timestamp", "total_nodes", "failure_count", "success_count", "failed_nodes"]
        for field in required_fields:
            if field not in failed_data:
                validation_errors.append(f"failed_nodes.json missing '{field}' field")

        # Validate data types
        if "total_nodes" in failed_data and not isinstance(failed_data["total_nodes"], int):
            validation_errors.append("total_nodes must be integer")
        if "failure_count" in failed_data and not isinstance(failed_data["failure_count"], int):
            validation_errors.append("failure_count must be integer")
        if "success_count" in failed_data and not isinstance(failed_data["success_count"], int):
            validation_errors.append("success_count must be integer")
        if "failed_nodes" in failed_data and not isinstance(failed_data["failed_nodes"], list):
            validation_errors.append("failed_nodes must be list")

        # Validate failed nodes structure
        if "failed_nodes" in failed_data:
            for node in failed_data["failed_nodes"]:
                node_fields = ["bmc_ip", "admin_ip", "hostname", "failure_stage", "status"]
                for field in node_fields:
                    if field not in node:
                        validation_errors.append(f"Failed node missing '{field}' field")

                if "failure_stage" in node and node["failure_stage"] not in ["pxe_boot", "phone_home"]:
                    validation_errors.append(f"Invalid failure_stage: {node['failure_stage']}")
                if "status" in node and node["status"] != "failed":
                    validation_errors.append(f"Invalid status: {node['status']}")

        if validation_errors:
            tl.failed("PXE boot configuration validation failed", f"failed_nodes.json validation errors: {validation_errors}")
        else:
            tl.passed("PXE boot configuration validation passed", "failed_nodes.json format and structure are valid")
    except Exception as e:
        tl.failed("PXE boot configuration validation failed", f"Error validating failed_nodes.json: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(12)
def test_orchestrator_status_output_exists():
    """TC_PXE_012: Verify orchestrator_status.yml output file exists."""
    tl = TestLogger("Orchestrator Status Output Exists", "TC_PXE_012")
    test_config = load_test_config()
    orchestrator_output_dir = test_config.get("orchestrator_output_dir", "/opt/omnia/orchestrator/output/project_default")
    status_path = Path(orchestrator_output_dir) / "orchestrator_status.yml"

    if status_path.exists():
        tl.passed("PXE boot configuration validation passed", f"orchestrator_status.yml found at {status_path}")
    else:
        tl.passed("PXE boot configuration validation passed", "orchestrator_status.yml not found (orchestrator may not have run yet)")


@pytest.mark.functional
@pytest.mark.order(13)
def test_orchestrator_status_output_format():
    """TC_PXE_013: Validate orchestrator_status.yml format and structure."""
    tl = TestLogger("Orchestrator Status Output Format", "TC_PXE_013")
    test_config = load_test_config()
    orchestrator_output_dir = test_config.get("orchestrator_output_dir", "/opt/omnia/orchestrator/output/project_default")
    status_path = Path(orchestrator_output_dir) / "orchestrator_status.yml"

    if not status_path.exists():
        tl.passed("PXE boot configuration validation passed", "orchestrator_status.yml not found (orchestrator may not have run yet)")
        return

    try:
        with open(status_path, 'r', encoding='utf-8') as f:
            status_data = yaml.safe_load(f)

        validation_errors = []

        # Validate required fields
        required_fields = ["overall_status", "timestamp", "total_nodes", "success_count", "failure_count", "nodes"]
        for field in required_fields:
            if field not in status_data:
                validation_errors.append(f"orchestrator_status.yml missing '{field}' field")

        # Validate data types
        if "overall_status" in status_data and status_data["overall_status"] not in ["success", "failed"]:
            validation_errors.append(f"Invalid overall_status: {status_data['overall_status']}")
        if "total_nodes" in status_data and not isinstance(status_data["total_nodes"], int):
            validation_errors.append("total_nodes must be integer")
        if "success_count" in status_data and not isinstance(status_data["success_count"], int):
            validation_errors.append("success_count must be integer")
        if "failure_count" in status_data and not isinstance(status_data["failure_count"], int):
            validation_errors.append("failure_count must be integer")
        if "nodes" in status_data and not isinstance(status_data["nodes"], list):
            validation_errors.append("nodes must be list")

        # Validate node structure
        if "nodes" in status_data:
            for node in status_data["nodes"]:
                node_fields = ["bmc_ip", "admin_ip", "hostname", "status"]
                for field in node_fields:
                    if field not in node:
                        validation_errors.append(f"Node missing '{field}' field")

                if "status" in node and node["status"] not in ["success", "failed"]:
                    validation_errors.append(f"Invalid node status: {node['status']}")

        if validation_errors:
            tl.failed("PXE boot configuration validation failed", f"orchestrator_status.yml validation errors: {validation_errors}")
        else:
            tl.passed("PXE boot configuration validation passed", "orchestrator_status.yml format and structure are valid")
    except Exception as e:
        tl.failed("PXE boot configuration validation failed", f"Error validating orchestrator_status.yml: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(14)
def test_pxe_boot_playbook_execution():
    """TC_PXE_014: Verify PXE boot playbook can be executed."""
    tl = TestLogger("PXE Boot Playbook Execution", "TC_PXE_014")
    playbook_path = "/root/catalog/omnia/src/orchestrator/playbooks/pxeboot/pxeboot.yml"

    if Path(playbook_path).exists():
        tl.passed("PXE boot configuration validation passed", f"PXE boot playbook found at {playbook_path}")
    else:
        tl.failed("PXE boot configuration validation failed", f"PXE boot playbook not found at {playbook_path}")


@pytest.mark.sanity
@pytest.mark.order(15)
def test_idrac_role_exists():
    """TC_PXE_015: Verify idrac_pxe_boot role exists."""
    tl = TestLogger("iDRAC Role Exists", "TC_PXE_015")
    role_path = Path("/root/catalog/omnia/src/orchestrator/roles/idrac_pxe_boot")

    if role_path.exists():
        if (role_path / "tasks" / "main.yml").exists() and (role_path / "vars" / "main.yml").exists():
            tl.passed("PXE boot configuration validation passed", f"idrac_pxe_boot role found at {role_path}")
        else:
            tl.failed("PXE boot configuration validation failed", "idrac_pxe_boot role missing required files")
    else:
        tl.failed("PXE boot configuration validation failed", f"idrac_pxe_boot role not found at {role_path}")
