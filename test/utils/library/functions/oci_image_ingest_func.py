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
OCI Image Ingest — Domain-Specific Verification Functions.

Provides verification functions for the OCI Image Ingest FVT tests
(ER-UTIL-001-registry-automation). Each function checks a specific
aspect of the registry automation pipeline and returns a standardized
result dict.
"""

import os
import re
from typing import Any, Dict, List, Optional

from omnia_auto import (
    load_test_config,
    run_on_host,
    read_remote_env,
)

from .host_func import resolve_target_source_root

from ..vars.common_vars import (
    CMDS,
    OCI_IMAGE_INGEST_CREDENTIALS_FILE,
    OCI_IMAGE_INGEST_CONFIG_FILE,
    OCI_BUILD_STATUS_FILE,
    OCI_IMAGE_BUILD_TYPE,
    OCI_ACCEPTED_BUILD_TYPES,
    OCI_S3_PATH_PATTERN,
    OCI_CREDENTIAL_FIELDS,
    OCI_PREREQUISITE_BINARIES,
    OCI_PREREQUISITE_FILES,
    OCI_SUPPORTED_REGISTRY_TYPES,
    OCI_SUPPORTED_OPERATIONS,
    OCI_WORKDIR_PATTERN,
    OCI_SAFE_CHAR_PATTERN,
    OCI_IMAGE_INGEST_TAG,
)


def _get_project_name(host) -> str:
    """Read the active project name from the target environment.

    Args:
        host: Testinfra host connection.

    Returns:
        Project name string, or 'default' if not set.
    """
    env_val = read_remote_env(host, "OMNIA_PROJECT_NAME")
    return env_val.strip() if env_val else "default"


def _get_data_path(host) -> str:
    """Read OMNIA_DATA_PATH from the target environment.

    Args:
        host: Testinfra host connection.

    Returns:
        Data path string, or empty string if not set.
    """
    env_val = read_remote_env(host, "OMNIA_DATA_PATH")
    return env_val.strip() if env_val else ""


def get_oci_config_path(host) -> str:
    """Build the full path to oci_image_ingest_config.yml on the target.

    Args:
        host: Testinfra host connection.

    Returns:
        Full path to the OCI image ingest config file.
    """
    data_path = _get_data_path(host)
    project = _get_project_name(host)
    return f"{data_path}/utils/input/{project}/{OCI_IMAGE_INGEST_CONFIG_FILE}"


def get_oci_credentials_path(host) -> str:
    """Build the full path to oci_image_ingest_credentials.yml on the target.

    Args:
        host: Testinfra host connection.

    Returns:
        Full path to the OCI image ingest credentials file.
    """
    data_path = _get_data_path(host)
    project = _get_project_name(host)
    return f"{data_path}/utils/input/{project}/{OCI_IMAGE_INGEST_CREDENTIALS_FILE}"


def get_oci_output_path(host) -> str:
    """Build the full path to the OCI image ingest output directory.

    Args:
        host: Testinfra host connection.

    Returns:
        Full path to the output directory.
    """
    data_path = _get_data_path(host)
    project = _get_project_name(host)
    return f"{data_path}/utils/output/{project}"


def get_oci_workdir_path(host) -> str:
    """Build the full path to the OCI image ingest working directory.

    Args:
        host: Testinfra host connection.

    Returns:
        Full path to the working directory.
    """
    data_path = _get_data_path(host)
    project = _get_project_name(host)
    return f"{data_path}/{OCI_WORKDIR_PATTERN.format(project=project)}"


def get_oci_log_path(host) -> str:
    """Build the full path to the OCI image ingest log directory.

    Args:
        host: Testinfra host connection.

    Returns:
        Full path to the log directory.
    """
    data_path = _get_data_path(host)
    project = _get_project_name(host)
    return f"{data_path}/utils/log/{project}"


def check_oci_config_exists(host) -> Dict[str, Any]:
    """Check if oci_image_ingest_config.yml exists on the target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, and error keys.
    """
    config_path = get_oci_config_path(host)
    cmd = CMDS["file_exists"].format(path=config_path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {"success": True, "details": f"Config exists: {config_path}", "error": ""}
    return {"success": False, "details": "", "error": f"Config not found: {config_path}"}


def validate_oci_config_structure(host) -> Dict[str, Any]:
    """Validate the YAML structure of oci_image_ingest_config.yml.

    Checks for required top-level keys (registries, image_mappings)
    and validates supported values for registry_type and operation.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, error, and parsed config data.
    """
    config_path = get_oci_config_path(host)
    cmd = (
        f"python3 -c \""
        f"import yaml, json, sys; "
        f"d = yaml.safe_load(open('{config_path}')); "
        f"print(json.dumps(d))\" 2>&1"
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": f"YAML parse failed: {result.stdout.strip()}",
            "config": None,
        }

    try:
        import json
        config = json.loads(result.stdout.strip())
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "success": False,
            "details": "",
            "error": f"JSON parse of remote output failed: {exc}",
            "config": None,
        }

    errors = []

    # Check required top-level keys
    if "registries" not in config:
        errors.append("Missing required key: registries")
    if "image_mappings" not in config:
        errors.append("Missing required key: image_mappings")

    # Validate registries
    for reg in config.get("registries", []):
        reg_type = reg.get("registry_type", "")
        if reg_type and reg_type not in OCI_SUPPORTED_REGISTRY_TYPES:
            errors.append(
                f"{reg_type} is not yet supported; supported: "
                f"{', '.join(OCI_SUPPORTED_REGISTRY_TYPES)}"
            )
        # Check for credential fields in config
        for field in OCI_CREDENTIAL_FIELDS:
            if field in reg:
                errors.append(
                    f"Credential field '{field}' found in config; "
                    f"credentials must be provided in {OCI_IMAGE_INGEST_CREDENTIALS_FILE}"
                )

    # Validate image_mappings
    for mapping in config.get("image_mappings", []):
        operation = mapping.get("operation", "")
        if operation and operation not in OCI_SUPPORTED_OPERATIONS:
            errors.append(
                f"{operation} is not yet supported; supported: "
                f"{', '.join(OCI_SUPPORTED_OPERATIONS)}"
            )
        func_group = mapping.get("functional_group", "")
        if func_group and not (
            func_group.endswith("_x86_64") or func_group.endswith("_aarch64")
        ):
            errors.append(
                f"functional_group '{func_group}' must end in _x86_64 or _aarch64"
            )
        if not mapping.get("image"):
            errors.append("image_mapping is missing required field: image")
        if not mapping.get("functional_group"):
            errors.append("image_mapping is missing required field: functional_group")

        # Check registry reference
        reg_name = mapping.get("registry_name", "")
        if reg_name:
            registry_names = [
                r.get("registry_name", "") for r in config.get("registries", [])
            ]
            if reg_name not in registry_names:
                errors.append(f"Unresolved registry reference: {reg_name}")

    if errors:
        return {
            "success": False,
            "details": "",
            "error": "; ".join(errors),
            "config": config,
        }

    return {
        "success": True,
        "details": f"Config valid with {len(config.get('registries', []))} registries, "
                   f"{len(config.get('image_mappings', []))} mappings",
        "error": "",
        "config": config,
    }


def check_oci_credentials_vault(host) -> Dict[str, Any]:
    """Verify the credentials file is Vault-encrypted with correct permissions.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, error, is_encrypted, and permissions keys.
    """
    cred_path = get_oci_credentials_path(host)

    # Check file exists
    exists_cmd = CMDS["file_exists"].format(path=cred_path)
    exists_result = run_on_host(host, exists_cmd)
    if exists_result.rc != 0 or "exists" not in exists_result.stdout:
        return {
            "success": False,
            "details": "",
            "error": f"Credentials file not found: {cred_path}",
            "is_encrypted": False,
            "permissions": "",
        }

    # Check Vault header
    header_cmd = CMDS["vault_check_header"].format(path=cred_path)
    header_result = run_on_host(host, header_cmd)
    is_encrypted = "$ANSIBLE_VAULT" in header_result.stdout

    # Check permissions
    perm_cmd = CMDS["file_permissions"].format(path=cred_path)
    perm_result = run_on_host(host, perm_cmd)
    permissions = perm_result.stdout.strip()

    success = is_encrypted and permissions == "600"
    details = (
        f"Vault-encrypted: {is_encrypted}, permissions: {permissions}"
    )
    error = ""
    if not is_encrypted:
        error = "Credentials file is not Vault-encrypted"
    elif permissions != "600":
        error = f"Permissions are {permissions}, expected 600"

    return {
        "success": success,
        "details": details,
        "error": error,
        "is_encrypted": is_encrypted,
        "permissions": permissions,
    }


def check_credential_leakage(host, credential_values: Optional[List[str]] = None) -> Dict[str, Any]:
    """Scan output paths for credential leakage.

    Scans build_status.yml, domain logs, and error output for any
    occurrence of credential values.

    Args:
        host: Testinfra host connection.
        credential_values: Optional list of credential strings to search for.
            If None, reads from test config.

    Returns:
        Dict with success, details, error, and leaked_locations keys.
    """
    output_path = get_oci_output_path(host)
    log_path = get_oci_log_path(host)
    leaked = []

    if not credential_values:
        config = load_test_config()
        credential_values = [
            v for v in [
                config.get("oci_registry_username", ""),
                config.get("oci_registry_password", ""),
            ] if v
        ]

    if not credential_values:
        return {
            "success": True,
            "details": "No credential values configured to scan",
            "error": "",
            "leaked_locations": [],
        }

    for cred_val in credential_values:
        for scan_path in [output_path, log_path]:
            cmd = CMDS["grep_credential_scan"].format(
                pattern=cred_val, path=scan_path
            )
            result = run_on_host(host, cmd)
            if result.rc == 0 and "clean" not in result.stdout:
                for line in result.stdout.strip().splitlines():
                    if line.strip():
                        leaked.append(line.strip())

    if leaked:
        return {
            "success": False,
            "details": "",
            "error": f"Credential leakage in {len(leaked)} location(s)",
            "leaked_locations": leaked,
        }

    return {
        "success": True,
        "details": "No credential leakage detected",
        "error": "",
        "leaked_locations": [],
    }


def check_oci_prerequisites(host) -> Dict[str, Any]:
    """Verify OCI image ingest prerequisites are installed.

    Checks for regctl, s3cmd, mksquashfs binaries and .s3cfg file.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, error, missing_binaries, and missing_files keys.
    """
    missing_binaries = []
    missing_files = []

    for binary in OCI_PREREQUISITE_BINARIES:
        cmd = CMDS["which_cmd"].format(binary=binary)
        result = run_on_host(host, cmd)
        if result.rc != 0 or not result.stdout.strip():
            missing_binaries.append(binary)

    home_dir = run_on_host(host, "echo $HOME").stdout.strip() or "/root"
    for filename in OCI_PREREQUISITE_FILES:
        path = f"{home_dir}/{filename}"
        cmd = CMDS["check_s3cfg"].format(path=path)
        result = run_on_host(host, cmd)
        if "missing" in result.stdout:
            missing_files.append(filename)

    all_missing = missing_binaries + missing_files
    if all_missing:
        return {
            "success": False,
            "details": "",
            "error": (
                f"Missing prerequisites: {', '.join(all_missing)}. "
                f"Run Image Build Manager with --tags prepare first"
            ),
            "missing_binaries": missing_binaries,
            "missing_files": missing_files,
        }

    return {
        "success": True,
        "details": f"All prerequisites present: {', '.join(OCI_PREREQUISITE_BINARIES)}",
        "error": "",
        "missing_binaries": [],
        "missing_files": [],
    }


def validate_build_status(host) -> Dict[str, Any]:
    """Validate the build_status.yml file structure and content.

    Checks for required fields: overall_status, image_build_type,
    s3_configurations, functional_group_images. Also verifies
    image_build_type is 'oci-image-ingest'.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, error, and status_data keys.
    """
    output_path = get_oci_output_path(host)
    find_cmd = CMDS["find_build_status"].format(path=output_path)
    find_result = run_on_host(host, find_cmd)

    if find_result.rc != 0 or not find_result.stdout.strip():
        return {
            "success": False,
            "details": "",
            "error": f"build_status.yml not found in {output_path}",
            "status_data": None,
        }

    status_path = find_result.stdout.strip()
    cmd = (
        f"python3 -c \""
        f"import yaml, json; "
        f"d = yaml.safe_load(open('{status_path}')); "
        f"print(json.dumps(d, default=str))\" 2>&1"
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": f"YAML parse failed: {result.stdout.strip()}",
            "status_data": None,
        }

    try:
        import json
        status = json.loads(result.stdout.strip())
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "success": False,
            "details": "",
            "error": f"JSON parse failed: {exc}",
            "status_data": None,
        }

    errors = []
    required_keys = ["overall_status", "image_build_type", "s3_configurations",
                     "functional_group_images"]
    for key in required_keys:
        if key not in status:
            errors.append(f"Missing required key: {key}")

    build_type = status.get("image_build_type", "")
    if build_type and build_type != OCI_IMAGE_BUILD_TYPE:
        errors.append(
            f"image_build_type is '{build_type}', expected '{OCI_IMAGE_BUILD_TYPE}'"
        )

    s3_config = status.get("s3_configurations", {})
    if s3_config:
        if "endpoint_url" not in s3_config:
            errors.append("s3_configurations missing endpoint_url")
        if not s3_config.get("bucket"):
            errors.append("s3_configurations missing bucket")

    if errors:
        return {
            "success": False,
            "details": "",
            "error": "; ".join(errors),
            "status_data": status,
        }

    return {
        "success": True,
        "details": (
            f"build_status.yml valid: overall_status={status.get('overall_status')}, "
            f"type={build_type}"
        ),
        "error": "",
        "status_data": status,
    }


def check_oci_sources_in_status(host) -> Dict[str, Any]:
    """Verify oci_sources section in build_status.yml.

    Checks for required provenance fields and confirms no credentials
    appear in the file.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, error, and sources keys.
    """
    status_result = validate_build_status(host)
    if not status_result["success"]:
        return {
            "success": False,
            "details": "",
            "error": f"Cannot check oci_sources: {status_result['error']}",
            "sources": [],
        }

    status = status_result["status_data"]
    sources = status.get("oci_sources", [])
    if not sources:
        return {
            "success": False,
            "details": "",
            "error": "oci_sources section is missing or empty",
            "sources": [],
        }

    required_source_fields = [
        "functional_group", "registry", "repository",
        "requested_reference", "digest", "platform",
        "kernel_version", "published_at", "artifacts",
    ]

    errors = []
    for idx, source in enumerate(sources):
        for field in required_source_fields:
            if field not in source:
                errors.append(f"oci_sources[{idx}] missing: {field}")

        # Check artifacts have size and sha256
        for artifact in source.get("artifacts", []):
            if "size_bytes" not in artifact:
                errors.append(f"artifact missing size_bytes")
            if "sha256" not in artifact:
                errors.append(f"artifact missing sha256")

    if errors:
        return {
            "success": False,
            "details": "",
            "error": "; ".join(errors),
            "sources": sources,
        }

    return {
        "success": True,
        "details": f"oci_sources valid with {len(sources)} entries",
        "error": "",
        "sources": sources,
    }


def check_s3_artifacts(host, functional_group: str, image_name: str,
                       release: str, bucket: str = "") -> Dict[str, Any]:
    """Verify artifacts exist in S3 at the expected paths.

    Args:
        host: Testinfra host connection.
        functional_group: The functional group name.
        image_name: The sanitized image name.
        release: The release prefix.
        bucket: S3 bucket name (read from build_status at runtime).

    Returns:
        Dict with success, details, error, and objects keys.
    """
    if not bucket:
        # Try to read bucket from build_status
        status_result = validate_build_status(host)
        if status_result["success"]:
            bucket = status_result["status_data"].get(
                "s3_configurations", {}
            ).get("bucket", "")
    prefix = f"{bucket}/{functional_group}/{image_name}-ingest/{release}/"
    cmd = CMDS["list_s3_objects"].format(bucket=bucket, prefix=f"{functional_group}/{image_name}-ingest/{release}/")
    result = run_on_host(host, cmd)

    if result.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to list S3 objects: {result.stdout.strip()}",
            "objects": [],
        }

    objects = [
        line.strip() for line in result.stdout.strip().splitlines() if line.strip()
    ]

    expected_patterns = ["vmlinuz-", "initramfs-", "rootfs.squashfs"]
    found = {p: False for p in expected_patterns}
    for obj in objects:
        for pattern in expected_patterns:
            if pattern in obj:
                found[pattern] = True

    missing = [p for p, v in found.items() if not v]
    if missing:
        return {
            "success": False,
            "details": f"Found {len(objects)} objects",
            "error": f"Missing artifacts in S3: {', '.join(missing)}",
            "objects": objects,
        }

    return {
        "success": True,
        "details": f"All 3 artifacts present at {prefix}",
        "error": "",
        "objects": objects,
    }


def check_oci_workdir_cleaned(host) -> Dict[str, Any]:
    """Verify the OCI image ingest working directory is cleaned up.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, and error keys.
    """
    workdir = get_oci_workdir_path(host)
    cmd = CMDS["dir_exists"].format(path=workdir)
    result = run_on_host(host, cmd)

    if result.rc == 0 and "exists" in result.stdout:
        # Dir exists, check if empty (exclude . / .. and total line)
        ls_cmd = CMDS["ls_dir"].format(path=workdir)
        ls_result = run_on_host(host, ls_cmd)
        lines = [
            l for l in ls_result.stdout.strip().splitlines()
            if l.strip()
            and not l.startswith("total")
            and not l.rstrip().endswith(" .")
            and not l.rstrip().endswith(" ..")
        ]
        if lines:
            return {
                "success": False,
                "details": f"Working directory contains {len(lines)} entries",
                "error": f"Working directory not cleaned: {workdir}",
            }

    return {
        "success": True,
        "details": f"Working directory clean: {workdir}",
        "error": "",
    }


def check_build_status_preserved(host, original_checksum: str) -> Dict[str, Any]:
    """Verify build_status.yml was not modified after a failed operation.

    Args:
        host: Testinfra host connection.
        original_checksum: SHA-256 checksum of the file before the operation.

    Returns:
        Dict with success, details, error, and current_checksum keys.
    """
    output_path = get_oci_output_path(host)
    find_cmd = CMDS["find_build_status"].format(path=output_path)
    find_result = run_on_host(host, find_cmd)

    if not find_result.stdout.strip():
        if not original_checksum:
            return {
                "success": True,
                "details": "No build_status.yml existed before or after",
                "error": "",
                "current_checksum": "",
            }
        return {
            "success": False,
            "details": "",
            "error": "build_status.yml was removed",
            "current_checksum": "",
        }

    status_path = find_result.stdout.strip()
    checksum_cmd = CMDS["sha256sum"].format(path=status_path)
    checksum_result = run_on_host(host, checksum_cmd)
    current_checksum = checksum_result.stdout.strip()

    if current_checksum == original_checksum:
        return {
            "success": True,
            "details": "build_status.yml unchanged",
            "error": "",
            "current_checksum": current_checksum,
        }

    return {
        "success": False,
        "details": "",
        "error": (
            f"build_status.yml was modified: "
            f"before={original_checksum}, after={current_checksum}"
        ),
        "current_checksum": current_checksum,
    }


def check_orchestrator_build_type(host, build_type: str) -> Dict[str, Any]:
    """Verify the Orchestrator accepts or rejects a given image_build_type.

    Args:
        host: Testinfra host connection.
        build_type: The image_build_type value to check.

    Returns:
        Dict with success, details, error, and accepted keys.
    """
    accepted = build_type in OCI_ACCEPTED_BUILD_TYPES

    if accepted:
        return {
            "success": True,
            "details": f"Build type '{build_type}' is accepted",
            "error": "",
            "accepted": True,
        }

    return {
        "success": True,
        "details": (
            f"Build type '{build_type}' correctly rejected. "
            f"Accepted: {', '.join(OCI_ACCEPTED_BUILD_TYPES)}"
        ),
        "error": "",
        "accepted": False,
    }


def sanitize_image_name(image_ref: str) -> str:
    """Sanitize an image reference for use in S3 paths.

    Replaces characters outside [A-Za-z0-9._-] with '-'.

    Args:
        image_ref: The image repository name or tag component.

    Returns:
        Sanitized string safe for S3 object keys.
    """
    return OCI_SAFE_CHAR_PATTERN.sub("-", image_ref)


def check_config_template_delivered(host) -> Dict[str, Any]:
    """Verify the config template was delivered to the project input directory.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, and error keys.
    """
    config_path = get_oci_config_path(host)
    cred_path = get_oci_credentials_path(host)

    # Config template should exist
    config_cmd = CMDS["file_exists"].format(path=config_path)
    config_result = run_on_host(host, config_cmd)
    config_exists = config_result.rc == 0 and "exists" in config_result.stdout

    # Credential file should NOT be shipped
    cred_cmd = CMDS["file_exists"].format(path=cred_path)
    cred_result = run_on_host(host, cred_cmd)
    cred_exists = cred_result.rc == 0 and "exists" in cred_result.stdout

    if not config_exists:
        return {
            "success": False,
            "details": "",
            "error": f"Config template not delivered: {config_path}",
        }

    details = f"Config template delivered: {config_path}"
    if cred_exists:
        details += " (WARNING: credential file also exists, but should be created by collection)"

    return {
        "success": True,
        "details": details,
        "error": "",
    }


def check_lock_file_status(host) -> Dict[str, Any]:
    """Check if the per-project run lock is held.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with success, details, error, and locked keys.
    """
    data_path = _get_data_path(host)
    project = _get_project_name(host)
    lock_path = f"{data_path}/utils/workdir/{project}/oci-image-ingest/.lock"

    cmd = CMDS["check_lock_file"].format(path=lock_path)
    result = run_on_host(host, cmd)
    locked = result.stdout.strip() == "locked"

    return {
        "success": True,
        "details": f"Lock status: {'locked' if locked else 'unlocked'}",
        "error": "",
        "locked": locked,
    }


# =============================================================================
# LIVE SYSTEM VERIFICATION HELPERS
# =============================================================================

def get_registry_info(host) -> Dict[str, Any]:
    """Extract registry endpoint and image repos from the OCI config.

    Returns:
        Dict with endpoint, namespace, images list, and raw config.
    """
    config_result = validate_oci_config_structure(host)
    config = config_result.get("config", {})
    if not config or not config.get("registries"):
        return {"success": False, "error": "No registries configured"}

    reg = config["registries"][0]
    endpoint = reg.get("endpoint", "")
    # Build endpoint from hostname/port if not present
    # regctl expects hostname:port without protocol
    if not endpoint:
        hostname = reg.get("registry_hostname", "")
        port = reg.get("registry_port", 443)
        endpoint = f"{hostname}:{port}"
    else:
        # Strip protocol if present (e.g., https://hostname:port -> hostname:port)
        if "://" in endpoint:
            endpoint = endpoint.split("://")[1]
    # Namespace can be per-registry or per-mapping
    namespace = reg.get("registry_namespace", "")
    if not namespace:
        for m in config.get("image_mappings", []):
            ns = m.get("namespace_name", "")
            if ns:
                namespace = ns
                break

    images = []
    for m in config.get("image_mappings", []):
        img = m.get("image", m.get("image_name", ""))
        # Parse tag from "image:tag" format
        if ":" in img:
            img_name, tag = img.rsplit(":", 1)
        else:
            img_name = img
            tag = m.get("tag", "")
        fg = m.get("functional_group", "")
        if img_name:
            images.append({
                "image_name": img_name,
                "tag": tag,
                "functional_group": fg,
                "full_ref": f"{endpoint}/{namespace}/{img_name}:{tag}" if tag else f"{endpoint}/{namespace}/{img_name}",
            })

    return {
        "success": True,
        "endpoint": endpoint,
        "namespace": namespace,
        "images": images,
        "config": config,
    }


def verify_registry_tag(host, endpoint: str, namespace: str,
                         image: str) -> Dict[str, Any]:
    """List tags for a registry image via regctl.

    Returns:
        Dict with success, tags list, and raw output.
    """
    # The endpoint must appear in both the regctl_cmd() call (for TLS/auth
    # config) and in the image reference (for registry routing).  Without
    # it in the ref, regctl defaults to docker.io.
    ref = f"{endpoint}/{namespace}/{image}"
    cmd = regctl_cmd(endpoint, f"tag ls {ref}")
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "tags": [],
            "error": result.stdout.strip(),
        }
    tags = [t.strip() for t in result.stdout.strip().splitlines() if t.strip()]
    return {"success": True, "tags": tags, "error": ""}


def verify_registry_digest(host, endpoint: str, namespace: str,
                            image: str, tag: str) -> Dict[str, Any]:
    """Get the digest for a specific image:tag via regctl.

    Returns:
        Dict with success, digest string, and platform.
    """
    ref = f"{endpoint}/{namespace}/{image}:{tag}"
    cmd = regctl_cmd(
        endpoint,
        f"manifest get {ref} --format '{{{{.GetDescriptor.Digest}}}}'",
    )
    result = run_on_host(host, cmd)
    # regctl may return non-zero due to auth warnings but still output the digest
    output = result.stdout.strip()
    # Extract the digest (sha256:...) from the output
    digest_match = re.search(r'sha256:[a-f0-9]+', output)
    if digest_match:
        return {
            "success": True,
            "digest": digest_match.group(0),
            "error": "",
        }
    return {"success": False, "digest": "", "error": output}


def verify_registry_platform(host, endpoint: str, namespace: str,
                              image: str, tag: str) -> Dict[str, Any]:
    """Get the platform for a specific image:tag via regctl.

    Returns:
        Dict with success and platform string (e.g. linux/amd64).
    """
    ref = f"{endpoint}/{namespace}/{image}:{tag}"
    cmd = regctl_cmd(
        endpoint,
        f"manifest get {ref} --platform linux/amd64 "
        f"--format '{{{{.GetDescriptor.Digest}}}}'",
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {"success": False, "platform": "", "error": result.stdout.strip()}
    return {"success": True, "platform": "linux/amd64", "error": ""}


def list_s3_objects_live(host, bucket: str,
                         prefix: str = "") -> Dict[str, Any]:
    """List S3 objects via s3cmd with sizes.

    Returns:
        Dict with success, objects list (each has path, size_str), count.
    """
    if prefix:
        cmd = f"s3cmd ls -r s3://{bucket}/{prefix} 2>&1"
    else:
        cmd = f"s3cmd ls -r s3://{bucket}/ 2>&1"
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False, "objects": [], "count": 0,
            "error": result.stdout.strip(),
        }
    objects = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("DIR"):
            continue
        parts = line.split()
        if len(parts) >= 4:
            size_str = parts[2]
            path = parts[3]
            objects.append({"path": path, "size_str": size_str})
    return {
        "success": True, "objects": objects,
        "count": len(objects), "error": "",
    }


def verify_s3_endpoint(host, endpoint: str) -> Dict[str, Any]:
    """Verify the S3 endpoint is reachable via curl.

    Returns:
        Dict with success, http_code, response_time.
    """
    cmd = (
        f"curl -s -o /dev/null -w '%{{http_code}} %{{time_total}}' "
        f"{endpoint} --connect-timeout 5 2>&1"
    )
    result = run_on_host(host, cmd)
    parts = result.stdout.strip().split()
    http_code = parts[0] if parts else "000"
    time_total = parts[1] if len(parts) > 1 else "0"
    reachable = http_code not in ("000", "")
    return {
        "success": reachable,
        "http_code": http_code,
        "response_time": time_total,
        "error": "" if reachable else f"Unreachable (code={http_code})",
    }


def check_disk_space(host, path: str) -> Dict[str, Any]:
    """Check available disk space at a path.

    Returns:
        Dict with available_bytes, total_bytes, used_pct.
    """
    cmd = f"df -B1 {path} 2>/dev/null | tail -1"
    result = run_on_host(host, cmd)
    parts = result.stdout.strip().split()
    if len(parts) < 4:
        return {"success": False, "available_bytes": 0, "error": "Cannot parse df"}
    try:
        available = int(parts[3])
        used_pct = parts[4] if len(parts) > 4 else "0%"
    except (ValueError, IndexError):
        return {"success": False, "available_bytes": 0, "error": "Cannot parse df"}
    return {
        "success": True,
        "available_bytes": available,
        "used_pct": used_pct,
        "error": "",
    }


def _collect_fg_entries(status: Dict[str, Any], arch: str) -> List[Dict[str, Any]]:
    """Flatten functional_group_images for one arch (nested or flat format)."""
    images = status.get("functional_group_images") or []
    blocks = [images] if isinstance(images, dict) else images
    nested = []
    for block in blocks:
        if isinstance(block, dict) and arch in block:
            val = block[arch]
            nested.extend(val if isinstance(val, list) else [val])
    if nested:
        return [e for e in nested if isinstance(e, dict)]
    return [e for e in blocks if isinstance(e, dict) and e.get("functional_group")]


def resolve_orchestrator_fg_entry(status: Dict[str, Any], fg_name: str) -> Dict[str, Any]:
    """Resolve a mapping functional group to a build_status entry.

    Mirrors the Orchestrator validate_image.yml lookup: exact match, then
    <prefix>_.*<arch>, then the same without the orchestrator-only '_first'.
    """
    arch_match = re.search(r"(x86_64|aarch64)$", fg_name)
    arch = arch_match.group(1) if arch_match else "x86_64"
    prefix = re.sub(r"_(x86_64|aarch64)$", "", fg_name)
    entries = _collect_fg_entries(status, arch)
    for entry in entries:
        if entry.get("functional_group") == fg_name:
            return entry
    prefixes = [prefix]
    if "_first" in prefix:
        prefixes.append(re.sub(r"_first(?=_rhel(_[0-9]+)+$|$)", "", prefix))
    for pfx in prefixes:
        pattern = re.compile(f"^{re.escape(pfx)}_.*{arch}$")
        for entry in entries:
            if pattern.search(entry.get("functional_group", "")):
                return entry
    return {}


def head_boot_artifact(host, url: str) -> str:
    """Anonymous HEAD on a boot artifact URL (as the OpenCHAMI Boot Service fetches it)."""
    cmd = (
        f"curl -skI -L --connect-timeout 15 --max-time 30 "
        f"-o /dev/null -w '%{{http_code}}' '{url}'"
    )
    return run_on_host(host, cmd).stdout.strip()[-3:]


def verify_orchestrator_boot_contract(
    host, status: Dict[str, Any], mapping_fgs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Verify the OCI ingest build_status.yml is consumable by the Orchestrator.

    Replicates the Orchestrator preconditions without running the playbook
    (configure_s3_access.yml + validate_image.yml):
      1. overall_status == success and image_build_type is accepted
      2. s3_configurations.endpoint_url / bucket present
      3. every oci_sources functional group, plus every functional group in
         the PXE mapping file, resolves to kernel/initrd/image paths that
         include the bucket
      4. each artifact URL answers HTTP 200 to an anonymous HEAD request

    Returns:
        Dict with success, details, error, and checked (artifact count).
    """
    errors: List[str] = []
    if status.get("overall_status") != "success":
        errors.append(f"overall_status is '{status.get('overall_status')}'")
    if status.get("image_build_type") not in OCI_ACCEPTED_BUILD_TYPES:
        errors.append(f"image_build_type '{status.get('image_build_type')}' not accepted")

    s3 = status.get("s3_configurations") or {}
    endpoint = str(s3.get("endpoint_url", "")).rstrip("/")
    bucket = s3.get("bucket", "")
    if not endpoint:
        errors.append("s3_configurations.endpoint_url missing")
    if not bucket:
        errors.append("s3_configurations.bucket missing")
    if errors:
        return {"success": False, "details": "", "error": "; ".join(errors), "checked": 0}

    fg_names = [s.get("functional_group", "") for s in status.get("oci_sources", [])]
    fg_names += [fg for fg in (mapping_fgs or []) if fg not in fg_names]
    checked = 0
    for fg in fg_names:
        entry = resolve_orchestrator_fg_entry(status, fg)
        if not entry:
            errors.append(f"{fg}: no matching functional_group_images entry")
            continue
        for name, key in (("kernel", "kernel"), ("initrd", "initrd"), ("rootfs", "image")):
            path = str(entry.get(key, "")).lstrip("/")
            if not path:
                errors.append(f"{fg}: {name} path missing")
                continue
            if not path.startswith(f"{bucket}/"):
                errors.append(f"{fg}: {name} path '{path}' not under bucket '{bucket}'")
            code = head_boot_artifact(host, f"{endpoint}/{path}")
            checked += 1
            if code != "200":
                errors.append(f"{fg}: {name} HEAD {endpoint}/{path} returned {code}")

    if errors:
        return {"success": False, "details": "", "error": "; ".join(errors), "checked": checked}
    return {
        "success": True,
        "details": f"{len(fg_names)} functional group(s), {checked} artifact(s) return 200 anonymously",
        "error": "",
        "checked": checked,
    }


def list_release_objects(host, bucket: str, status_data: Dict[str, Any],
                         functional_group: str) -> Dict[str, Any]:
    """List the S3 objects of the release that build_status.yml names.

    The functional-group prefix also holds Image Build Manager releases, so
    the listing is scoped to ``dirname(kernel)`` of the group's entry in
    ``functional_group_images`` (``<bucket>/<group>/<image>-ingest/<release>/``,
    bucket stripped).
    """
    arch_match = re.search(r"(x86_64|aarch64)$", functional_group)
    arch = arch_match.group(1) if arch_match else "x86_64"
    for entry in _collect_fg_entries(status_data, arch):
        if entry.get("functional_group") == functional_group:
            prefix = os.path.dirname(entry.get("kernel", ""))
            if prefix.startswith(bucket + "/"):
                prefix = prefix[len(bucket) + 1:]
            if prefix:
                return list_s3_objects_live(host, bucket, prefix + "/")
    return {
        "success": False, "objects": [], "count": 0,
        "error": f"No functional_group_images entry for {functional_group}",
    }


def get_oci_src_utils_path(host) -> str:
    """Return <source_root>/src/utils on the execution target.

    The source root follows the other domains: the local checkout in local
    mode, ``clone_path`` from test_config.yml in remote mode.

    Raises:
        FileNotFoundError: If the utils source directory is missing.
    """
    src_path = os.path.join(resolve_target_source_root(), "src", "utils")
    if run_on_host(host, f"test -d {src_path}").rc != 0:
        raise FileNotFoundError(
            f"Omnia utils source not found on target: {src_path}"
        )
    return src_path


def regctl_cmd(endpoint: str, args: str, user: Optional[str] = None,
               password: Optional[str] = None) -> str:
    """Build a regctl command that uses a private, session-scoped config.

    The config (0600, in a 0700 mktemp directory) is passed through
    REGCTL_CONFIG and removed afterwards, mirroring the production
    validate_registry_connection role.  The operator's global
    ~/.regctl/config.json is never read or written.  Credentials, when
    given, live only in that file and never appear in regctl's arguments.
    """
    import base64
    import json as json_mod

    entry = {"hostname": endpoint, "tls": "insecure"}
    if user:
        entry.update({"user": user, "pass": password})
    encoded = base64.b64encode(
        json_mod.dumps({"hosts": {endpoint: entry}}).encode("utf-8")
    ).decode("ascii")
    return (
        "umask 077; d=$(mktemp -d); "
        f"echo {encoded} | base64 -d > \"$d/regctl.json\"; "
        f"REGCTL_CONFIG=\"$d/regctl.json\" regctl {args} 2>&1; rc=$?; "
        "rm -rf \"$d\"; exit $rc"
    )


def registry_v2_auth_cmd(endpoint: str, user: Optional[str] = None,
                         password: Optional[str] = None,
                         vault_dir: Optional[str] = None) -> str:
    """Build a Registry V2 ``/v2/`` auth probe that prints the HTTP code.

    This is the call the production validate_registry_connection role uses
    to authenticate.  Credentials are read by curl from a private mktemp
    config file, never from its arguments.  Pass ``user``/``password`` for a
    literal pair, or ``vault_dir`` to decrypt the stored OCI credentials on
    the host (ansible-vault, output piped straight into the config file).
    """
    import base64
    import json as json_mod

    head = (
        "insecure\nsilent\nconnect-timeout = 10\noutput = \"/dev/null\"\n"
        f"url = \"https://{endpoint}/v2/\"\n"
        "write-out = \"%{http_code}\"\n"
    )
    esc = lambda v: json_mod.dumps(v)[1:-1]
    if vault_dir:
        creds = f"{vault_dir}/{OCI_IMAGE_INGEST_CREDENTIALS_FILE}"
        key = f"{vault_dir}/.oci_image_ingest_credentials_key"
        user_line = (
            f"ansible-vault view --vault-password-file {key} {creds} | "
            "python3 -c 'import sys,yaml,json; c=yaml.safe_load(sys.stdin); "
            "print(\"user = \" + json.dumps(c[\"registry_username\"] + \":\" "
            "+ c[\"registry_password\"]))' >> \"$d/curl.cfg\"; "
        )
    else:
        line = f'user = "{esc(user)}:{esc(password)}"\n'
        user_line = (
            f"echo {base64.b64encode(line.encode()).decode()} | base64 -d "
            ">> \"$d/curl.cfg\"; "
        )
    return (
        "umask 077; d=$(mktemp -d); "
        f"echo {base64.b64encode(head.encode()).decode()} | base64 -d "
        "> \"$d/curl.cfg\"; " + user_line +
        "curl -K \"$d/curl.cfg\" 2>&1; rc=$?; rm -rf \"$d\"; exit $rc"
    )


def run_production_validation(host, config_dict) -> Dict[str, Any]:
    """Invoke the production validate_config() and normalize() API.

    Calls the upstream production entry points exposed by
    src/utils/plugins/modules/validate_oci_image_ingest_config.py:
        validate_config(config, schema_def, logger) -> list[str]
        normalize(config) -> dict

    The configuration is passed as a base64-encoded YAML string (no
    temporary file is created).  A lightweight ``ansible.module_utils``
    namespace shim is constructed so the production module's
    ``from ansible.module_utils.*`` imports resolve to the real
    ``plugins/module_utils/`` tree without requiring a full Ansible
    collection loader.  A no-op ValidationLogger is constructed via the
    production ``create_logger('', 'fvt')``.

    This ensures negative input tests exercise the actual production
    validation code path rather than recreating validation logic.
    """
    import base64
    import json as json_mod
    import yaml as yaml_mod

    encoded = base64.b64encode(
        yaml_mod.safe_dump(config_dict).encode("utf-8")
    ).decode("ascii")
    src_path = get_oci_src_utils_path(host)
    mu_path = f"{src_path}/plugins/module_utils"
    schema_path = (f"{mu_path}/input_validation/schema"
                   "/oci_image_ingest_config.json")
    script = (
        "import sys, types, base64, json, yaml; "
        # Shim ansible.module_utils → real plugins/module_utils tree
        f"mu='{mu_path}'; sys.path.insert(0, mu); "
        "a=types.ModuleType('ansible'); a.__path__=[]; "
        "amu=types.ModuleType('ansible.module_utils'); amu.__path__=[mu]; "
        "ab=types.ModuleType('ansible.module_utils.basic'); "
        "ab.AnsibleModule=type('AnsibleModule',(),{}); "
        "a.module_utils=amu; amu.basic=ab; "
        "sys.modules.update({'ansible':a,"
        "'ansible.module_utils':amu,'ansible.module_utils.basic':ab}); "
        # Import the real production module
        f"sys.path.insert(0, '{src_path}/plugins/modules'); "
        "from validate_oci_image_ingest_config import validate_config, normalize; "
        "from input_validation.core.utils import create_logger; "
        # Run validation
        f"c=yaml.safe_load(base64.b64decode('{encoded}')); "
        f"s=json.load(open('{schema_path}')); "
        "lg=create_logger('','fvt'); "
        "e=validate_config(c,s,lg); "
        "print(json.dumps(dict(errors=e, success=len(e)==0)))"
    )
    result = run_on_host(host, f'python3 -c "{script}"')
    try:
        return json_mod.loads(result.stdout.strip())
    except (json_mod.JSONDecodeError, ValueError):
        return {"success": False, "errors": [f"Execution failed: {result.stdout.strip()}"]}


def get_build_status_checksum(host) -> str:
    """Return the SHA-256 checksum of build_status.yml, or '' if absent."""
    output_path = get_oci_output_path(host)
    find_cmd = CMDS["find_build_status"].format(path=output_path)
    find_result = run_on_host(host, find_cmd)
    status_path = find_result.stdout.strip()
    if not status_path:
        return ""
    checksum_result = run_on_host(host, CMDS["sha256sum"].format(path=status_path))
    return checksum_result.stdout.strip()


def run_pipeline_with_fault(host, config_override, timeout=900):
    """Run the OCI ingest pipeline with a modified input config.

    Backs up the real config, writes the override, runs the production
    playbook (utils.yml --tags oci_image_ingest), restores the original
    config in ``finally`` and returns the run_playbook result dict.
    """
    import yaml as yaml_mod
    from library.functions import run_playbook
    from ..vars.common_vars import PLAYBOOK_UTILS

    config_path = get_oci_config_path(host)
    backup_path = config_path + ".fvt_backup"
    run_on_host(host, CMDS["copy_file"].format(src=config_path, dst=backup_path))
    try:
        override_yaml = yaml_mod.dump(config_override, default_flow_style=False)
        run_on_host(host, f"cat > {config_path} << 'ENDOFCFG'\n{override_yaml}ENDOFCFG")
        return run_playbook(playbook=PLAYBOOK_UTILS, tag=OCI_IMAGE_INGEST_TAG, timeout=timeout)
    finally:
        run_on_host(host, CMDS["copy_file"].format(src=backup_path, dst=config_path))
        run_on_host(host, f"rm -f {backup_path}")


# =============================================================================
# CONTROLLED FAULT INJECTION AGAINST THE PRODUCTION PIPELINE
# =============================================================================
# Each scenario runs the real playbook. Faults are injected without touching
# production state: a scratch S3 bucket keeps the real release untouched, and
# command shims (df, mksquashfs, s3cmd) are placed first on PATH of the
# playbook process only, in a private temp directory removed afterwards.

_FAULT_RUN_CACHE: Dict[str, Dict[str, Any]] = {}

_S3_BAD_CFG = (
    "[default]\nhost_base = 127.0.0.1:1\nhost_bucket = 127.0.0.1:1\n"
    "use_https = False\naccess_key = fvt\nsecret_key = fvt\nmax_retries = 0\n"
)


def _shim_bodies(real_s3cmd: str, bad_cfg: str) -> Dict[str, str]:
    """Shell bodies of the fault shims, keyed by scenario."""
    return {
        "storage": {"df": (
            'for a in "$@"; do case "$a" in --output=avail) '
            "printf 'Avail\\n1024\\n'; exit 0;; esac; done\nexec /usr/bin/df \"$@\"\n")},
        "mksquashfs": {"mksquashfs": (
            'echo partial > "$2"\n'
            'echo "FATAL ERROR: injected mksquashfs failure" >&2\nexit 1\n')},
        "s3_unreachable": {"s3cmd": f'exec {real_s3cmd} -c {bad_cfg} "$@"\n'},
        "s3_partial": {"s3cmd": (
            'if [ "$1" = put ]; then for a in "$@"; do case "$a" in */rootfs.squashfs) '
            'echo "ERROR: injected upload failure" >&2; exit 12;; esac; done; fi\n'
            f'exec {real_s3cmd} "$@"\n')},
    }


def _read_log(host) -> List[str]:
    log_file = f"{get_oci_log_path(host)}/oci_image_ingest.log"
    return run_on_host(host, f"cat {log_file} 2>/dev/null").stdout.splitlines()


def release_snapshot(host, status_data: Dict[str, Any]) -> Dict[str, Any]:
    """Checksum of build_status.yml plus the S3 objects of every named release."""
    bucket = (status_data.get("s3_configurations") or {}).get("bucket", "")
    releases = {}
    for src in status_data.get("oci_sources", []):
        fg = src.get("functional_group", "")
        listing = list_release_objects(host, bucket, status_data, fg)
        releases[fg] = sorted(o["path"] for o in listing.get("objects", []))
    return {"status_checksum": get_build_status_checksum(host), "releases": releases}


def run_fault_scenario(host, name: str, timeout: int = 1800) -> Dict[str, Any]:
    """Run one fault scenario through the production playbook (cached per session).

    Scenarios: storage, mksquashfs, s3_unreachable, s3_partial, registry_unreachable.

    Returns a dict with: skipped (reason or ''), result (run_playbook dict),
    output (whitespace-normalised playbook output), log (ingest log lines written
    during the run), before/after (release_snapshot), scratch_objects (objects left
    in the scratch bucket), workdir_clean, lock_held, elapsed.
    """
    if name in _FAULT_RUN_CACHE:
        return _FAULT_RUN_CACHE[name]
    import shutil
    import tempfile
    import time
    import uuid
    from omnia_auto import is_local_execution
    from library.functions import run_playbook
    from ..vars.common_vars import PLAYBOOK_UTILS

    out: Dict[str, Any] = {"skipped": ""}
    if name != "registry_unreachable" and not is_local_execution():
        out["skipped"] = "command-shim fault injection needs local execution mode"
        _FAULT_RUN_CACHE[name] = out
        return out
    status = validate_build_status(host)
    if not status["success"]:
        out["skipped"] = f"no build_status.yml: {status['error']}"
        return out
    status_data = status["status_data"]
    out["before"] = release_snapshot(host, status_data)
    log_before = len(_read_log(host))

    scratch = ""
    shim_dir = tempfile.mkdtemp(prefix="fvt_shim_")
    old_path = os.environ.get("PATH", "")
    started = time.time()
    try:
        if name in ("storage", "mksquashfs", "s3_partial"):
            scratch = f"fvt-oci-{uuid.uuid4().hex[:12]}"
            mb = run_on_host(host, f"s3cmd mb s3://{scratch}")
            assert mb.rc == 0, f"cannot create scratch bucket: {mb.stderr}"
        if name == "registry_unreachable":
            cfg = validate_oci_config_structure(host)["config"]
            import copy
            bad = copy.deepcopy(cfg)
            bad["registries"][0]["registry_hostname"] = "192.0.2.1"
            out["result"] = run_pipeline_with_fault(host, bad, timeout=timeout)
        else:
            bad_cfg = os.path.join(shim_dir, "bad.s3cfg")
            with open(bad_cfg, "w", encoding="utf-8") as fh:
                fh.write(_S3_BAD_CFG)
            os.chmod(bad_cfg, 0o600)
            real_s3cmd = shutil.which("s3cmd") or "s3cmd"
            for sname, body in _shim_bodies(real_s3cmd, bad_cfg)[name].items():
                path = os.path.join(shim_dir, sname)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("#!/bin/bash\n" + body)
                os.chmod(path, 0o700)
            os.environ["PATH"] = shim_dir + os.pathsep + old_path
            extra = {"oci_ingest_bucket": scratch} if scratch else {}
            out["result"] = run_playbook(
                playbook=PLAYBOOK_UTILS, tag=OCI_IMAGE_INGEST_TAG,
                extra_vars=extra, timeout=timeout)
        if scratch:
            out["scratch_objects"] = [
                l for l in run_on_host(host, f"s3cmd ls -r s3://{scratch}/").stdout.splitlines()
                if l.strip()]
    finally:
        os.environ["PATH"] = old_path
        shutil.rmtree(shim_dir, ignore_errors=True)
        if scratch:
            run_on_host(host, f"s3cmd rb --recursive --force s3://{scratch}")
    out["elapsed"] = time.time() - started
    res = out["result"]
    out["output"] = re.sub(r"\s+", " ", f"{res.get('output', '')} {res.get('error', '')}")
    out["log"] = _read_log(host)[log_before:]
    out["after"] = release_snapshot(host, status_data)
    out["workdir_clean"] = check_oci_workdir_cleaned(host)["success"]
    out["lock_held"] = check_lock_file_status(host)["locked"]
    _FAULT_RUN_CACHE[name] = out
    return out


def check_fault_run(run: Dict[str, Any], phase: str, expect: List[str],
                    forbid: Optional[List[str]] = None) -> List[str]:
    """Common safe-failure assertions; returns a list of violated expectations."""
    errors: List[str] = []
    result = run["result"]
    text = run["output"] + " " + " ".join(run["log"])
    if result.get("success") or result.get("rc") == 0:
        errors.append("pipeline did not fail")
    if f"(phase: {phase})" not in text:
        errors.append(f"failure not attributed to '(phase: {phase})'")
    errors += [f"missing '{e}' in output/log" for e in expect if e not in text]
    errors += [f"unexpected '{f}' in output" for f in (forbid or []) if f in run["output"]]
    if run["before"] != run["after"]:
        errors.append("build_status.yml or the published release changed")
    if not run["workdir_clean"]:
        errors.append("working directory not cleaned")
    if run["lock_held"]:
        errors.append("project lock not released")
    if not any(" - ERROR - " in l and "run failed" in l for l in run["log"]):
        errors.append("failure not written to the ingest log")
    if run.get("scratch_objects"):
        errors.append(f"objects left in scratch bucket: {run['scratch_objects']}")
    return errors


def credentials_leaked_in(host, text: str) -> bool:
    """True when a stored registry username/password value appears in ``text``.

    The values are decrypted on the host and fed to ``grep -F -f`` through
    process substitution; they never enter this process or a command line.

    Guards against blank patterns: empty or whitespace-only credential
    values are filtered out before grep, and at least one non-blank
    pattern must be present.  If ansible-vault fails or the YAML is
    unparsable, the function raises instead of silently returning False.
    """
    import base64
    cred_path = get_oci_credentials_path(host)
    key = os.path.join(os.path.dirname(cred_path), ".oci_image_ingest_credentials_key")
    encoded = base64.b64encode(text.encode()).decode()
    cmd = (
        "umask 077; f=$(mktemp); "
        f"echo {encoded} | base64 -d > \"$f\"; "
        "patterns=$(ansible-vault view --vault-password-file "
        f"{key} {cred_path} | python3 -c '"
        "import sys,yaml; c=yaml.safe_load(sys.stdin) or {}; "
        "vals=[v for v in (c.get(\"registry_username\"), c.get(\"registry_password\")) "
        "if v and str(v).strip()]; "
        "assert vals, \"No non-blank credentials found\"; "
        "[print(str(v).strip()) for v in vals]"
        "'); rc=$?; "
        "if [ $rc -ne 0 ]; then rm -f \"$f\"; echo ERROR; exit 1; fi; "
        "if grep -qF -f <(echo \"$patterns\") \"$f\"; "
        "then echo LEAK; else echo CLEAN; fi; rm -f \"$f\""
    )
    result = run_on_host(host, f"bash -c {shlex_quote(cmd)}")
    if "ERROR" in result.stdout or (result.rc != 0 and "LEAK" not in result.stdout
                                     and "CLEAN" not in result.stdout):
        raise RuntimeError(
            f"credentials_leaked_in: vault decrypt or credential extraction failed: "
            f"{result.stdout.strip()}"
        )
    return "LEAK" in result.stdout


def shlex_quote(value: str) -> str:
    import shlex
    return shlex.quote(value)


def latest_completed_run(host) -> List[str]:
    """Ingest log lines of the most recent run that wrote build_status.yml."""
    lines = _read_log(host)
    starts = [i for i, l in enumerate(lines) if "run started:" in l] + [len(lines)]
    for lo, hi in reversed(list(zip(starts, starts[1:]))):
        if any("build_status.yml written" in l for l in lines[lo:hi]):
            return lines[lo:hi]
    return []
