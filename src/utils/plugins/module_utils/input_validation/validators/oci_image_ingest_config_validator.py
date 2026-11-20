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
"""
OCI image ingest configuration validator.

Validates oci_image_ingest_config.yml for:
- Credential-like keys (credentials belong in oci_image_ingest_credentials.yml)
- Duplicate registry, mapping and functional group names
- Mappings that reference an undefined registry
- Registry hostnames that carry a port
"""
from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    utils_messages as msg,
)

CREDENTIAL_KEYS = {
    "username", "password", "token", "auth", "credentials", "secret",
    "registry_username", "registry_password", "registry_token", "api_key",
}
SUPPORTED = {"registry_type": ["harbor"], "operation": ["repo_to_bucket"]}


def credential_key_errors(config_data):
    """Return an error list naming credential-like keys (never their values)."""
    found = set()
    for section in ("registries", "image_mappings"):
        for entry in config_data.get(section) or []:
            if isinstance(entry, dict):
                found.update(k for k in entry if str(k).lower() in CREDENTIAL_KEYS)
    found.update(k for k in config_data if str(k).lower() in CREDENTIAL_KEYS)
    if not found:
        return []
    return [msg.OCI_CREDENTIAL_KEYS_MSG.format(keys=", ".join(sorted(found)))]


def format_schema_error(err):
    """Convert a jsonschema error into an actionable message (L1 formatter)."""
    path = "/".join(str(p) for p in err.absolute_path) or "<root>"
    field = str(err.absolute_path[-1]) if err.absolute_path else ""
    if err.validator == "minItems" and field == "registries":
        return msg.OCI_REGISTRIES_EMPTY_MSG
    if err.validator == "minItems" and field == "image_mappings":
        return msg.OCI_MAPPINGS_EMPTY_MSG
    if err.validator == "enum" and field in SUPPORTED:
        return msg.oci_unsupported_value_msg(path, err.instance, ", ".join(SUPPORTED[field]))
    if err.validator == "required":
        return f"{path}: {err.message}"
    if field == "registry_hostname":
        return f"{path}: {msg.OCI_HOSTNAME_FORMAT_MSG}"
    if field == "functional_group":
        return f"{path}: {msg.OCI_FUNCTIONAL_GROUP_ARCH_MSG}"
    if field == "image":
        return f"{path}: {msg.OCI_IMAGE_FORMAT_MSG}"
    return f"{path}: {err.message}"


def _duplicates(values):
    return sorted({v for v in values if values.count(v) > 1})


def _validate_unique_names(config_data, errors, logger=None):
    """Registry names, mapping names and functional groups must be unique."""
    checks = (
        ("registries", "registry_name"),
        ("image_mappings", "mapping_name"),
        ("image_mappings", "functional_group"),
    )
    for section, key in checks:
        values = [e[key] for e in config_data[section]]
        for dup in _duplicates(values):
            _add(errors, msg.oci_duplicate_msg(section, key, dup), logger)


def _validate_registry_references(config_data, errors, logger=None):
    names = {r["registry_name"] for r in config_data["registries"]}
    for mapping in config_data["image_mappings"]:
        if mapping["registry_name"] not in names:
            _add(errors, msg.oci_unknown_registry_msg(
                mapping["mapping_name"], mapping["registry_name"]), logger)


def _validate_hostnames(config_data, errors, logger=None):
    for registry in config_data["registries"]:
        if ":" in registry["registry_hostname"]:
            _add(errors, msg.OCI_HOSTNAME_PORT_MSG.format(name=registry["registry_name"]), logger)


def _add(errors, error, logger=None):
    errors.append(error)
    if logger:
        logger.error(error)


def validate(config_data, logger=None):
    """
    Run all L2 validation rules on oci_image_ingest_config.yml data.

    Expects data that already passed the JSON schema (L1).

    Args:
        config_data (dict): Parsed oci_image_ingest_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    _validate_unique_names(config_data, errors, logger)
    _validate_registry_references(config_data, errors, logger)
    _validate_hostnames(config_data, errors, logger)
    return errors
