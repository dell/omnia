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
Orchestrator validation engine — runs L1 (schema) and L2 (logic) validation.

Provides the central ``run_validation()`` dispatcher that loads config files,
applies JSON schema checks, then runs semantic validators.
"""

import csv
import ipaddress
import json
import os

import yaml

from ..messages.orchestrator_messages import VALIDATOR_EXCEPTION_MSG


# ── Utility helpers ──────────────────────────────────────────────────────────

def read_csv_rows(path):
    """Read CSV file, return (header, rows) with stripped values."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip().upper() for h in next(reader)]
        rows = []
        for row in reader:
            rows.append([c.strip() for c in row])
    return header, rows


def col_index(header, name):
    """Return column index for *name* or -1 if not found."""
    name_upper = name.upper()
    for i, h in enumerate(header):
        if h == name_upper:
            return i
    return -1


def is_valid_ipv4(addr):
    """Quick check for valid IPv4 address."""
    try:
        ip = ipaddress.ip_address(addr)
        return ip.version == 4
    except ValueError:
        return False


def ip_in_subnet(ip_str, network_str, prefix_len):
    """Check if an IP is in a given subnet."""
    try:
        network = ipaddress.ip_network(f"{network_str}/{prefix_len}", strict=False)
        return ipaddress.ip_address(ip_str) in network
    except ValueError:
        return False


def load_yaml_file(path):
    """Safely load a YAML file, return parsed data or None."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, IOError, OSError):
        return None


def load_json_schema(schema_path):
    """Load a JSON schema file, return parsed data or None."""
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None


def run_validation(config_file, config_data, validators, logger=None):
    """
    Run a list of validator functions against config data.

    Args:
        config_file (str): Name of the config file being validated.
        config_data (dict): Parsed configuration data.
        validators (list): List of callables with signature (data, errors, logger).
        logger: Optional logger instance.

    Returns:
        list: Collected error message strings (empty if valid).
    """
    errors = []
    for validator_fn in validators:
        try:
            validator_fn(config_data, errors, logger)
        except Exception as e:
            msg = VALIDATOR_EXCEPTION_MSG.format(config_file, validator_fn.__name__, e)
            errors.append(msg)
            if logger:
                logger.error(errors[-1])
    return errors
