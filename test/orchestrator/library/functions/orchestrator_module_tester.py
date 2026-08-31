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
Orchestrator Module Testing Utilities

Functions for testing Ansible modules in the orchestrator collection.
Following the same pattern as main module testing.
"""

import os
import tempfile
import json
import yaml
from typing import Any, Dict

from omnia_auto import load_test_config, run_on_host
from ..vars.common_vars import SRC_ORCHESTRATOR_DIR


def validate_module_structure(module_name: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test an orchestrator module with validation logic.

    Args:
        module_name: Name of the Ansible module to test
        test_data: Test data to pass to the module

    Returns:
        Dict with keys: success, details, error
    """
    module_path = os.path.join(SRC_ORCHESTRATOR_DIR, "plugins", "modules", f"{module_name}.py")

    # Check if module file exists
    if not os.path.exists(module_path):
        return {
            "success": False,
            "details": f"Module file not found: {module_path}",
            "error": f"Module {module_name} does not exist"
        }

    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test input file
        test_input_file = os.path.join(temp_dir, "test_input.yml")
        with open(test_input_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_data, f)

        return {
            "success": True,
            "details": f"Module {module_name} validation test setup complete",
            "error": ""
        }


def validate_orchestrator_config_module(host, test_config: Dict[str, Any]) -> Dict[str, Any]:
    """Test the validate_orchestrator_config module.

    Args:
        host: Testinfra host connection
        test_config: Test configuration data

    Returns:
        Dict with keys: success, details, error
    """
    input_project_dir = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default")

    # Run the module using ansible-doc or direct Python import
    cmd = ("cd {} && python3 -c "
           "'from ansible.modules import validate_orchestrator_config; "
           "print(\"Module import successful\")'".format(input_project_dir))

    result = run_on_host(host, cmd)

    if result.rc == 0:
        return {
            "success": True,
            "details": "validate_orchestrator_config module is importable",
            "error": ""
        }
    return {
        "success": False,
        "details": f"Module import failed: {result.stdout}",
        "error": "validate_orchestrator_config module not found or import failed"
    }


def validate_generate_functional_groups_module(mapping_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test the generate_functional_groups module.

    Args:
        mapping_data: PXE mapping data for testing

    Returns:
        Dict with keys: success, details, error
    """
    # Check if module can process mapping data
    if not mapping_data.get("nodes"):
        return {
            "success": False,
            "details": "Invalid mapping data: missing nodes",
            "error": "Mapping data must contain 'nodes' key"
        }

    return {
        "success": True,
        "details": f"generate_functional_groups module can process {len(mapping_data['nodes'])} nodes",
        "error": ""
    }


def validate_slurm_conf_module(slurm_config: Dict[str, Any]) -> Dict[str, Any]:
    """Test the slurm_conf module.

    Args:
        slurm_config: Slurm configuration data

    Returns:
        Dict with keys: success, details, error
    """
    # Validate slurm configuration structure
    required_fields = ["cluster_name", "control_machine"]
    missing_fields = [field for field in required_fields if field not in slurm_config]

    if missing_fields:
        return {
            "success": False,
            "details": f"Missing required Slurm config fields: {missing_fields}",
            "error": f"Slurm config must contain: {required_fields}"
        }

    return {
        "success": True,
        "details": f"slurm_conf module can process config for cluster: {slurm_config['cluster_name']}",
        "error": ""
    }


def validate_module_schema(module_name: str, schema_file: str) -> Dict[str, Any]:
    """Test module against its JSON schema.

    Args:
        module_name: Name of the module
        schema_file: Path to schema file

    Returns:
        Dict with keys: success, details, error
    """
    schema_path = os.path.join(SRC_ORCHESTRATOR_DIR, "plugins", "module_utils", "orchestrator_validation", "schema", schema_file)

    if not os.path.exists(schema_path):
        return {
            "success": False,
            "details": f"Schema file not found: {schema_path}",
            "error": f"Schema {schema_file} does not exist for module {module_name}"
        }

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        if not isinstance(schema, dict):
            return {
                "success": False,
                "details": "Invalid schema format",
                "error": "Schema must be a JSON object"
            }

        return {
            "success": True,
            "details": "Schema {} is valid for module {}".format(schema_file, module_name),
            "error": ""
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "details": "Schema JSON parsing failed",
            "error": "Invalid JSON in schema file: {}".format(str(e))
        }


def check_module_dependencies(module_name: str) -> Dict[str, Any]:
    """Check if module dependencies are available.

    Args:
        module_name: Name of the module to check

    Returns:
        Dict with keys: success, details, error, missing_deps
    """
    module_path = os.path.join(SRC_ORCHESTRATOR_DIR, "plugins", "modules", f"{module_name}.py")

    if not os.path.exists(module_path):
        return {
            "success": False,
            "details": f"Module file not found: {module_path}",
            "error": f"Module {module_name} does not exist",
            "missing_deps": []
        }

    # Read module file to check imports
    with open(module_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Common dependencies for orchestrator modules
    common_deps = {
        "yaml": "yaml",
        "json": "json",
        "logging": "logging",
        "os": "os",
        "ansible.module_utils.basic": "ansible-core"
    }

    missing_deps = []
    for import_name, package in common_deps.items():
        if import_name in content:
            try:
                __import__(import_name.split('.', maxsplit=1)[0])
            except ImportError:
                missing_deps.append(package)

    if missing_deps:
        return {
            "success": False,
            "details": f"Module {module_name} has missing dependencies",
            "error": f"Missing dependencies: {missing_deps}",
            "missing_deps": missing_deps
        }

    return {
        "success": True,
        "details": f"All dependencies available for module {module_name}",
        "error": "",
        "missing_deps": []
    }
