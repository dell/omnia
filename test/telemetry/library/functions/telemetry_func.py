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
Telemetry — Domain-Specific Verification Functions.

Functions for verifying telemetry-specific resources and config.
"""

import yaml

from omnia_auto import (
    load_test_config,
    run_on_host,
)

from library.vars.common_vars import (
    CMDS,
    DEFAULT_OMNIA_DATA_PATH,
    DEFAULT_PROJECT_NAME,
    DOMAIN_NAME,
    INPUT_FILES,
)


def get_telemetry_input_path(host):
    """Resolve the telemetry input directory on the target host.

    Resolves: $OMNIA_DATA_PATH/telemetry/input/$OMNIA_PROJECT_NAME/

    Args:
        host: testinfra host connection to kube_vip.

    Returns:
        str: Absolute path to telemetry input directory.
    """
    config = load_test_config()
    project = config.get("project_name", DEFAULT_PROJECT_NAME)
    omnia_data_path = config.get("omnia_data_path", DEFAULT_OMNIA_DATA_PATH)
    return f"{omnia_data_path}/{DOMAIN_NAME}/input/{project}"


def verify_input_file_exists(host, filename):
    """Check if a telemetry input file exists on the target.

    Args:
        host: testinfra host connection to kube_vip.
        filename: Input file name (e.g. telemetry_config.yml).

    Returns:
        dict with keys: success (bool), path (str), error (str|None)
    """
    input_path = get_telemetry_input_path(host)
    file_path = f"{input_path}/{filename}"
    cmd = CMDS["file_exists"].format(path=file_path)
    result = run_on_host(host, cmd)
    exists = result.rc == 0 and "exists" in result.stdout

    return {
        "success": exists,
        "path": file_path,
        "error": None if exists else f"File not found: {file_path}",
    }


def verify_all_input_files_exist(host):
    """Check all 3 telemetry input files exist on target.

    Returns:
        dict with keys: success, results (per-file), missing (list)
    """
    results = []
    missing = []
    for filename in INPUT_FILES:
        result = verify_input_file_exists(host, filename)
        results.append({"filename": filename, **result})
        if not result["success"]:
            missing.append(filename)

    return {
        "success": len(missing) == 0,
        "results": results,
        "missing": missing,
    }


def load_telemetry_config_from_target(host):
    """Read and parse telemetry_config.yml from target host.

    Args:
        host: testinfra host connection to kube_vip.

    Returns:
        dict: Parsed YAML content, or empty dict on failure.
    """
    input_path = get_telemetry_input_path(host)
    file_path = f"{input_path}/telemetry_config.yml"
    cmd = CMDS["cat_file"].format(path=file_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {}
    try:
        return yaml.safe_load(result.stdout) or {}
    except yaml.YAMLError:
        return {}


def get_kube_vip_from_config(host):
    """Extract kube_vip value from telemetry_config.yml on target.

    Args:
        host: testinfra host connection to kube_vip.

    Returns:
        str: kube_vip IP address, or empty string if not set.
    """
    config = load_telemetry_config_from_target(host)
    return config.get("kube_vip", "")


def is_source_enabled(host, source_name):
    """Check if a telemetry source is enabled.

    Args:
        host: testinfra host connection to kube_vip.
        source_name: Source name (e.g. 'idrac', 'ldms').

    Returns:
        bool: True if source has metrics_enabled: true.
    """
    config = load_telemetry_config_from_target(host)
    sources = config.get("telemetry_sources", {})
    source = sources.get(source_name, {})
    return source.get("metrics_enabled", False)


def is_sink_enabled(host, sink_name):
    """Check if a telemetry sink is enabled.

    Sinks are considered enabled if any source targets them.

    Args:
        host: testinfra host connection to kube_vip.
        sink_name: Sink name (e.g. 'victoria_metrics', 'kafka').

    Returns:
        bool: True if at least one source targets this sink.
    """
    config = load_telemetry_config_from_target(host)
    sinks = config.get("telemetry_sinks", {})
    sink = sinks.get(sink_name, {})
    return sink.get("enabled", False)
