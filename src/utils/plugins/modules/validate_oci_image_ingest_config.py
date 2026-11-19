#!/usr/bin/python
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
# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-CONFIG-001.5, CG-CRYPTO-001.6
# ****

"""Validate oci_image_ingest_config.yml (JSON Schema plus semantic checks)."""

from __future__ import annotations

import json
import os
from typing import Any

import yaml
from ansible.module_utils.basic import AnsibleModule

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover
    HAS_JSONSCHEMA = False

DOCUMENTATION = r"""
---
module: validate_oci_image_ingest_config
short_description: Validate the OCI image ingest input file
description:
  - Validates oci_image_ingest_config.yml against its JSON Schema.
  - Rejects credential keys without echoing their values.
  - Rejects unsupported registry types and operations with a "not yet supported" message.
  - Verifies that every image mapping references a defined registry.
options:
  config_path:
    description: Path to oci_image_ingest_config.yml.
    type: path
    required: true
  schema_path:
    description: Path to the JSON Schema file.
    type: path
    required: true
"""

CREDENTIAL_KEYS = {
    "username", "password", "token", "auth", "credentials", "secret",
    "registry_username", "registry_password", "registry_token", "api_key",
}
SUPPORTED = {"registry_type": ["harbor"], "operation": ["repo_to_bucket"]}
CREDENTIAL_MSG = ("credentials must be provided in oci_image_ingest_credentials.yml "
                  "(found credential key(s): {keys})")
DEFAULT_PORTS = {"https": 443, "http": 80}


def find_credential_keys(config: dict) -> list[str]:
    """Return credential-like key names found in registries and mappings (never values)."""
    found = set()
    for section in ("registries", "image_mappings"):
        for entry in config.get(section) or []:
            if isinstance(entry, dict):
                found.update(k for k in entry if str(k).lower() in CREDENTIAL_KEYS)
    found.update(k for k in config if str(k).lower() in CREDENTIAL_KEYS)
    return sorted(found)


def format_schema_error(err: Any) -> str:
    """Convert a jsonschema error into an actionable message."""
    path = "/".join(str(p) for p in err.absolute_path) or "<root>"
    field = str(err.absolute_path[-1]) if err.absolute_path else ""
    if err.validator == "enum" and field in SUPPORTED:
        supported = ", ".join(SUPPORTED[field])
        return f"{path}: {err.instance} is not yet supported; supported: {supported}"
    if err.validator == "required":
        return f"{path}: {err.message}"
    if field == "functional_group":
        return (f"{path}: functional_group must end in _x86_64 or _aarch64 "
                "(for example slurm_node_rhel_10_2_x86_64)")
    if field == "image":
        return f"{path}: image must be <repository>:<tag> or <repository>@sha256:<64 hex digest>"
    return f"{path}: {err.message}"


def semantic_errors(config: dict) -> list[str]:
    """Cross-reference checks that JSON Schema cannot express."""
    errors = []
    names = [r["registry_name"] for r in config["registries"]]
    for dup in sorted({n for n in names if names.count(n) > 1}):
        errors.append(f"registries: duplicate registry_name '{dup}'")
    maps = [m["mapping_name"] for m in config["image_mappings"]]
    for dup in sorted({n for n in maps if maps.count(n) > 1}):
        errors.append(f"image_mappings: duplicate mapping_name '{dup}'")
    for mapping in config["image_mappings"]:
        if mapping["registry_name"] not in names:
            errors.append(f"image_mappings[{mapping['mapping_name']}]: registry_name "
                          f"'{mapping['registry_name']}' is not defined in registries")
    return errors


def run_validation(config: Any, schema: dict) -> tuple[list[str], dict]:
    """Return (errors, normalized config)."""
    if not isinstance(config, dict):
        return ["oci_image_ingest_config.yml must be a YAML mapping with registries "
                "and image_mappings"], {}
    cred_keys = find_credential_keys(config)
    if cred_keys:
        return [CREDENTIAL_MSG.format(keys=", ".join(cred_keys))], {}
    validator = jsonschema.Draft7Validator(schema)
    found = sorted(validator.iter_errors(config), key=lambda e: list(map(str, e.absolute_path)))
    errors = [format_schema_error(e) for e in found]
    if errors:
        return errors, {}
    errors = semantic_errors(config)
    if errors:
        return errors, {}
    normalized = {"registries": [], "image_mappings": config["image_mappings"]}
    for reg in config["registries"]:
        reg = dict(reg)
        reg.setdefault("registry_port", DEFAULT_PORTS[reg["registry_protocol"]])
        normalized["registries"].append(reg)
    return [], normalized


def main() -> None:
    """Module entry point."""
    module = AnsibleModule(
        argument_spec={"config_path": {"type": "path", "required": True},
                       "schema_path": {"type": "path", "required": True}},
        supports_check_mode=True,
    )
    if not HAS_JSONSCHEMA:
        module.fail_json(msg="python jsonschema library is required")
    for key in ("config_path", "schema_path"):
        if not os.path.isfile(module.params[key]):
            module.fail_json(msg=f"{key} not found: {module.params[key]}")
    try:
        with open(module.params["config_path"], encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        with open(module.params["schema_path"], encoding="utf-8") as handle:
            schema = json.load(handle)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        module.fail_json(msg=f"Failed to parse input: {type(exc).__name__}")
    errors, normalized = run_validation(config, schema)
    if errors:
        module.fail_json(msg="oci_image_ingest_config.yml validation failed", errors=errors)
    module.exit_json(changed=False, msg="oci_image_ingest_config.yml is valid", config=normalized)


if __name__ == "__main__":
    main()
