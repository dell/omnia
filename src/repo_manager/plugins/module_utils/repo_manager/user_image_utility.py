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
"""Pulp remote handling for catalog-mapped configured registries."""

import json

from ansible.module_utils.repo_manager.container_repo_utils import extract_existing_tags
from ansible.module_utils.repo_manager.parse_and_download import execute_command
from ansible.module_utils.repo_manager.config import pulp_container_commands


def _append_registry_options(command, registry_context, clear_missing=False):
    """Append auth/TLS options and explicitly clear removed values on updates."""
    tls = registry_context.get("tls") or {}
    command.extend([
        "--tls-validation",
        "false" if tls.get("insecure", False) else "true",
    ])

    ca_path = tls.get("ca_path") or ""
    client_cert = tls.get("client_cert_path") or ""
    client_key = tls.get("client_key_path") or ""
    if ca_path:
        command.extend(["--ca-cert", f"@{ca_path}"])
    elif clear_missing:
        command.extend(["--ca-cert", ""])
    if client_cert:
        command.extend(["--client-cert", f"@{client_cert}"])
    elif clear_missing:
        command.extend(["--client-cert", ""])
    if client_key:
        command.extend(["--client-key", f"@{client_key}"])
    elif clear_missing:
        command.extend(["--client-key", ""])

    if registry_context.get("auth_type") == "basic":
        command.extend([
            "--username", registry_context["username"],
            "--password", registry_context["password"],
        ])
    elif clear_missing:
        command.extend(["--username", "", "--password", ""])
    return command


def _build_remote_command(
    action, remote_name, registry_context, image_path, policy_type, tags=None
):
    """Build a Pulp container remote create/update argv list."""
    command = [
        "pulp", "container", "remote", action,
        "--name", remote_name,
        "--url", registry_context["base_url"],
        "--upstream-name", image_path,
        "--policy", policy_type,
        "--exclude-tags", json.dumps(["*sha256*.sig"]),
    ]
    if tags is not None:
        command.extend(["--include-tags", json.dumps(tags)])
    return _append_registry_options(
        command, registry_context, clear_missing=(action == "update")
    )


def create_or_update_configured_remote(
    remote_name, registry_context, image_path, policy_type, logger, tag=None
):
    """Create or fully reconcile a configured-registry Pulp remote.

    Existing tags are retained and deduplicated. Authentication, URL, policy,
    and TLS options are reconciled even when the requested tag already exists.
    """
    remote_exists = execute_command(
        pulp_container_commands["show_container_remote"] % remote_name, logger
    )

    tags = None if tag is None else list(dict.fromkeys(
        extract_existing_tags(remote_name, logger) + [tag]
        if remote_exists else [tag]
    ))
    action = "update" if remote_exists else "create"
    command = _build_remote_command(
        action, remote_name, registry_context, image_path, policy_type, tags
    )
    result = execute_command(command, logger)
    if result is False or (
        isinstance(result, dict) and result.get("returncode", 1) != 0
    ):
        logger.error(
            "Failed to %s configured registry remote '%s' for registry '%s'.",
            action, remote_name, registry_context["name"]
        )
        return False

    logger.info(
        "Configured registry remote '%s' %sd successfully%s.",
        remote_name, action, f" with tags {tags}" if tags is not None else ""
    )
    return True
