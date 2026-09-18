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

from ansible.module_utils.repo_manager.container_repo_utils import extract_existing_tags
from ansible.module_utils.repo_manager.parse_and_download import execute_command
from ansible.module_utils.repo_manager.pulp_commands import (
    build_container_remote_command,
    pulp_container_commands,
)
from ansible.module_utils.repo_manager.security_utils import (
    validate_container_policy,
    validate_container_reference,
    validate_container_tag,
    validate_repository_id,
    validate_repository_url,
)


def _build_remote_command(
    action, remote_name, registry_context, image_path, policy_type, tags=None
):
    """Build a Pulp container remote create/update argv list."""
    remote_name = validate_repository_id(remote_name)
    image_path = validate_container_reference(image_path)
    policy_type = validate_container_policy(policy_type)
    base_url = validate_repository_url(registry_context["base_url"])
    if tags is not None:
        tags = [validate_container_tag(tag) for tag in tags]
    tls = registry_context.get("tls") or {}
    uses_basic_auth = registry_context.get("auth_type") == "basic"
    return build_container_remote_command(
        action,
        name=remote_name,
        url=base_url,
        upstream_name=image_path,
        policy=policy_type,
        include_tags=tags,
        username=registry_context.get("username") if uses_basic_auth else None,
        password=registry_context.get("password") if uses_basic_auth else None,
        tls_validation=not tls.get("insecure", False),
        ca_cert=f"@{tls['ca_path']}" if tls.get("ca_path") else None,
        client_cert=(
            f"@{tls['client_cert_path']}"
            if tls.get("client_cert_path") else None
        ),
        client_key=(
            f"@{tls['client_key_path']}"
            if tls.get("client_key_path") else None
        ),
        clear_missing=(action == "update"),
    )


def create_or_update_configured_remote(
    remote_name, registry_context, image_path, policy_type, logger, tag=None
):
    """Create or fully reconcile a configured-registry Pulp remote.

    Existing tags are retained and deduplicated. Authentication, URL, policy,
    and TLS options are reconciled even when the requested tag already exists.
    """
    remote_name = validate_repository_id(remote_name)
    image_path = validate_container_reference(image_path)
    policy_type = validate_container_policy(policy_type)
    if tag is not None:
        tag = validate_container_tag(tag)
    remote_exists = execute_command(
        pulp_container_commands["show_remote"] % remote_name, logger
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
