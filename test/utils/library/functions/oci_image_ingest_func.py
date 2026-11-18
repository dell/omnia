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

# Production source paths (for invoking production validators)
SRC_UTILS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', '..', '..', 'src', 'utils',
)

from ..vars.common_vars import (
    CMDS,
    OCI_IMAGE_INGEST_CONFIG_FILE,
    OCI_IMAGE_INGEST_CREDENTIALS_FILE,
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
    ref = f"{endpoint}/{namespace}/{image}"
    cmd = f"regctl registry set {endpoint} --tls insecure 2>&1; regctl tag ls {ref} 2>&1"
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
    cmd = f"regctl registry set {endpoint} --tls insecure 2>&1; regctl manifest get {ref} --format '{{{{.GetDescriptor.Digest}}}}' 2>&1"
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
    cmd = (
        f"regctl registry set {endpoint} --tls insecure 2>&1; "
        f"regctl manifest get {ref} --platform linux/amd64 "
        f"--format '{{{{.GetDescriptor.Digest}}}}' 2>&1"
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


def run_production_validation(host, config_dict) -> Dict[str, Any]:
    """Invoke the production validate_oci_image_ingest_config.run_validation().

    Passes config_dict to the production Python validation module as a
    base64-encoded argument (no temporary file is created), validates it
    against the real JSON schema, and returns the result including any
    error messages.

    This ensures negative input tests exercise the actual production
    validation code path rather than recreating validation logic.
    """
    import base64
    import json as json_mod
    import yaml as yaml_mod

    encoded = base64.b64encode(
        yaml_mod.safe_dump(config_dict).encode("utf-8")
    ).decode("ascii")
    src_path = run_on_host(
        host, "realpath " + os.path.normpath(SRC_UTILS_PATH)
    ).stdout.strip()
    if not src_path:
        src_path = "/root/main/omnia/src/utils"
    script = (
        "import base64, json, sys, yaml; "
        f"sys.path.insert(0, '{src_path}/plugins/modules'); "
        "from validate_oci_image_ingest_config import run_validation; "
        f"c = yaml.safe_load(base64.b64decode('{encoded}')); "
        f"s = json.load(open('{src_path}/plugins/module_utils"
        "/input_validation/schema/oci_image_ingest_config.json')); "
        "e, n = run_validation(c, s); "
        "print(json.dumps(dict(errors=e, success=len(e) == 0)))"
    )
    result = run_on_host(host, f'python3 -c "{script}"')
    try:
        return json_mod.loads(result.stdout.strip())
    except (json_mod.JSONDecodeError, ValueError):
        return {"success": False, "errors": [f"Execution failed: {result.stdout.strip()}"]}


def run_pipeline_with_fault(host, config_override, timeout=300):
    """Run the OCI ingest pipeline with a modified config for fault injection.

    Backs up the real config, writes the override, runs the playbook,
    restores the original, and returns the playbook result.
    """
    config_path = get_oci_config_path(host)
    backup_path = config_path + ".fvt_backup"

    # Backup original config
    run_on_host(host, CMDS["copy_file"].format(src=config_path, dst=backup_path))
    try:
        import yaml as yaml_mod
        override_yaml = yaml_mod.dump(config_override, default_flow_style=False)
        run_on_host(
            host,
            f"cat > {config_path} << 'ENDOFCFG'\n{override_yaml}ENDOFCFG",
        )
        # Run the playbook (expect failure)
        from library.functions import run_playbook
        result = run_playbook(
            host,
            CMDS["playbook_utils_oci"],
            timeout=timeout,
        )
        return result
    finally:
        # Always restore original config
        run_on_host(host, CMDS["copy_file"].format(src=backup_path, dst=config_path))
        run_on_host(host, f"rm -f {backup_path}")
