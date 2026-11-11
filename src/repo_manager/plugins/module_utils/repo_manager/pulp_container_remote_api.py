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
"""CA-verified Pulp container-remote mutations that keep secrets off argv."""

import base64
import binascii
import re
import time

from ansible.module_utils.repo_manager.common_functions import load_pulp_config
from ansible.module_utils.repo_manager.config import CLI_FILE_PATH
from ansible.module_utils.repo_manager.rest_client import RestClient
from ansible.module_utils.repo_manager.secure_path import read_secure_text_file
from ansible.module_utils.repo_manager.security_utils import (
    validate_container_policy,
    validate_container_reference,
    validate_container_tag,
    validate_repository_id,
    validate_repository_url,
)


_CONTAINER_REMOTE_COLLECTION = "/pulp/api/v3/remotes/container/container/"
_CONTAINER_REMOTE_HREF = re.compile(
    r"^/pulp/api/v3/remotes/container/container/"
    r"[0-9A-Fa-f-]{32,36}/$"
)
_PULP_TASK_HREF = re.compile(
    r"^/pulp/api/v3/tasks/[0-9A-Fa-f-]{32,36}/$"
)
_REMOTE_UPDATE_TIMEOUT_SECONDS = 300
_TASK_POLL_INTERVAL_SECONDS = 1


def _pulp_rest_client():
    """Load Pulp administration credentials into memory, never process argv."""
    config = load_pulp_config(CLI_FILE_PATH)
    encoded_password = config.get("password", "")
    try:
        password = base64.b64decode(
            encoded_password.encode("ascii"), validate=True
        ).decode("utf-8")
    except (binascii.Error, UnicodeError, ValueError) as error:
        raise RuntimeError("Pulp client credentials are invalid") from error
    if not config.get("username") or not password or not config.get("base_url"):
        raise RuntimeError("Pulp client credentials are incomplete")
    return RestClient(config["base_url"], config["username"], password)


def _optional_tls_content(path):
    """Return certificate/key content from one trusted file path."""
    if not path:
        return None
    content = read_secure_text_file(
        str(path), require_trusted_owner=False
    )
    if len(content.encode("utf-8")) > 1024 * 1024:
        raise ValueError("Registry TLS material exceeds the allowed size")
    return content


def _validated_remote_href(remote_href):
    """Return one exact container-remote HREF or reject it."""
    if not isinstance(remote_href, str) or not _CONTAINER_REMOTE_HREF.fullmatch(
            remote_href):
        raise ValueError("Pulp container remote href is invalid")
    return remote_href


def _wait_for_remote_update(client, task_href, logger):
    """Wait for one asynchronous Pulp remote-update task to complete."""
    if not isinstance(task_href, str) or not _PULP_TASK_HREF.fullmatch(
            task_href):
        logger.error("Pulp container remote update returned an invalid task href.")
        return False

    deadline = time.monotonic() + _REMOTE_UPDATE_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        task = client.get(task_href)
        if not isinstance(task, dict):
            logger.error("Unable to read Pulp container remote update task state.")
            return False

        state = task.get("state")
        if state == "completed":
            return True
        if state in {"failed", "canceled", "canceling"}:
            logger.error(
                "Pulp container remote update task ended in state '%s'.",
                state,
            )
            return False
        if state not in {"waiting", "running"}:
            logger.error(
                "Pulp container remote update returned unexpected state '%s'.",
                state,
            )
            return False
        time.sleep(_TASK_POLL_INTERVAL_SECONDS)

    logger.error("Timed out waiting for Pulp container remote update task.")
    return False


def reconcile_authenticated_container_remote(
        action, *, name, url, upstream_name, policy, include_tags,
        username, password, logger, remote_href=None, tls=None):
    """Create or update an authenticated remote over verified Pulp HTTPS."""
    try:
        if action not in {"create", "update"}:
            raise ValueError("Unsupported container remote action")
        name = validate_repository_id(name)
        url = validate_repository_url(url)
        upstream_name = validate_container_reference(upstream_name)
        policy = validate_container_policy(policy)
        tags = [validate_container_tag(tag) for tag in include_tags or ()]
        if (
                not isinstance(username, str)
                or not username
                or not isinstance(password, str)
                or not password
        ):
            raise ValueError("Container registry credentials are incomplete")

        tls = tls or {}
        payload = {
            "name": name,
            "url": url,
            "upstream_name": upstream_name,
            "policy": policy,
            "include_tags": tags,
            "exclude_tags": ["*sha256*.sig"],
            "username": str(username),
            "password": str(password),
            "tls_validation": not bool(tls.get("insecure", False)),
            "ca_cert": _optional_tls_content(tls.get("ca_path")),
            "client_cert": _optional_tls_content(tls.get("client_cert_path")),
            "client_key": _optional_tls_content(tls.get("client_key_path")),
        }
        client = _pulp_rest_client()
        if action == "create":
            result = client.request_json(
                "POST",
                _CONTAINER_REMOTE_COLLECTION,
                payload,
                expected_statuses=(201,),
            )
        else:
            result = client.request_json(
                "PATCH",
                _validated_remote_href(remote_href),
                payload,
                expected_statuses=(200, 202),
            )
        if result is None:
            logger.error(
                "Pulp rejected authenticated container remote %s for '%s'.",
                action, name,
            )
            return False
        if action == "update" and result.get("task"):
            return _wait_for_remote_update(client, result["task"], logger)
        return True
    except (OSError, RuntimeError, TypeError, UnicodeError, ValueError):
        logger.error(
            "Authenticated container remote %s failed for '%s'.",
            action, name,
        )
        return False
