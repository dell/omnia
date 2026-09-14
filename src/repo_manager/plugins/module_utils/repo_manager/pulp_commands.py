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
"""Authoritative, shell-free Pulp CLI command definitions.

Every Python caller receives a fresh argv list whose first element is the
configured Pulp executable. Keeping the grammar here prevents command drift,
preserves argument boundaries, and gives security checks one command boundary
to review. This module intentionally contains no Pulp Python API usage.
"""
# Builder signatures mirror the explicit Pulp options intentionally.
# pylint: disable=too-many-arguments,too-many-locals

import json
from collections.abc import Sequence

from ansible.module_utils.repo_manager.repo_paths import PULP_CLI_EXECUTABLE


class PulpCommandTemplate(tuple):
    """Immutable argv template compatible with historic ``%`` call sites."""

    def __new__(cls, *arguments):
        """Create a template prefixed by the configured Pulp executable."""
        return super().__new__(cls, (PULP_CLI_EXECUTABLE, *arguments))

    def __mod__(self, values):
        """Substitute ``%s`` placeholders and return a new argv list."""
        replacements = values if isinstance(values, tuple) else (values,)
        replacements = iter(replacements)
        command = []
        for argument in self:
            rendered = str(argument)
            while "%s" in rendered:
                try:
                    value = next(replacements)
                except StopIteration as error:
                    raise TypeError("Not enough Pulp command arguments") from error
                rendered = rendered.replace("%s", _normalize_value(value), 1)
            command.append(rendered)
        try:
            next(replacements)
        except StopIteration:
            return command
        raise TypeError("Too many Pulp command arguments")


def _normalize_value(value):
    """Return one template replacement without any shell interpretation."""
    return str(value)


def _template(*arguments):
    """Return an immutable Pulp argv template."""
    return PulpCommandTemplate(*arguments)


def build_pulp_entity_command(plugin, resource, action, *, name=None,
                              href=None, filters=None, fields=None,
                              limit=None, offset=None):
    """Build an allowlisted Pulp entity show/list/destroy command."""
    allowed_plugins = {"container", "file", "python", "rpm"}
    allowed_resources = {
        "distribution", "publication", "remote", "repository",
    }
    allowed_actions = {"destroy", "list", "show"}
    if plugin not in allowed_plugins:
        raise ValueError(f"Unsupported Pulp plugin: {plugin}")
    if resource not in allowed_resources:
        raise ValueError(f"Unsupported Pulp resource: {resource}")
    if action not in allowed_actions:
        raise ValueError(f"Unsupported Pulp entity action: {action}")
    if name is not None and href is not None:
        raise ValueError("Specify either a Pulp object name or href")

    command = [PULP_CLI_EXECUTABLE, plugin, resource, action]
    if name is not None:
        command.extend(["--name", str(name)])
    if href is not None:
        command.extend(["--href", str(href)])
    command.extend(str(value) for value in (filters or ()))
    for field in fields or ():
        command.extend(["--field", str(field)])
    if limit is not None:
        command.extend(["--limit", str(limit)])
    if offset is not None:
        command.extend(["--offset", str(offset)])
    return command


def build_pulp_task_list_command(*, cid=None, reserved_resource=None,
                                 states=None, limit=100, ordering=None):
    """Build a task query with exact correlation/resource filters."""
    if cid is not None and reserved_resource is not None:
        raise ValueError("Task queries accept either cid or reserved resource")
    command = [PULP_CLI_EXECUTABLE, "task", "list"]
    if cid is not None:
        command.extend(["--cid", str(cid)])
    if reserved_resource is not None:
        command.extend(["--reserved-resource", str(reserved_resource)])
    for state in states or ():
        if state not in {"canceling", "running", "waiting"}:
            raise ValueError(f"Unsupported active Pulp task state: {state}")
        command.extend(["--state-in", state])
    command.extend(["--limit", str(limit)])
    if ordering is not None:
        command.extend(["--ordering", str(ordering)])
    return command


def build_container_tags_href(repository_version, tag=None):
    """Return the Pulp API href used to query container tag content."""
    href = (
        "/pulp/api/v3/content/container/tags/"
        f"?repository_version={repository_version}"
    )
    if tag is not None:
        href = f"{href}&name={tag}"
    return href


def build_container_remote_command(action, *, name, url, upstream_name,
                                   policy, include_tags=None,
                                   username=None, password=None,
                                   tls_validation=None, ca_cert=None,
                                   client_cert=None, client_key=None,
                                   clear_missing=False):
    """Build a container remote create/update command.

    Credentials remain individual argv entries so they can be redacted by
    option position and can never alter command structure.
    """
    if action not in {"create", "update"}:
        raise ValueError(f"Unsupported container remote action: {action}")
    command = [
        PULP_CLI_EXECUTABLE, "container", "remote", action,
        "--name", str(name), "--url", str(url),
        "--upstream-name", str(upstream_name), "--policy", str(policy),
    ]
    if include_tags is not None:
        command.extend(["--include-tags", json.dumps(list(include_tags))])
    command.extend(["--exclude-tags", '["*sha256*.sig"]'])
    if username is not None:
        command.extend(["--username", str(username)])
    if password is not None:
        command.extend(["--password", str(password)])
    if tls_validation is not None:
        command.extend([
            "--tls-validation", "true" if tls_validation else "false",
        ])
    for option, value in (
            ("--ca-cert", ca_cert),
            ("--client-cert", client_cert),
            ("--client-key", client_key)):
        if value is not None:
            command.extend([option, str(value)])
        elif clear_missing:
            command.extend([option, ""])
    if username is None and clear_missing:
        command.extend(["--username", ""])
    if password is None and clear_missing:
        command.extend(["--password", ""])
    return command


# Common/core operations.
pulp_common_commands = {
    "status": _template("status"),
    "version": _template("--version"),
    "show_href": _template("show", "--href", "%s"),
    "orphan_cleanup": _template("orphan", "cleanup", "--protection-time", "0"),
    "orphan_cleanup_default": _template("orphan", "cleanup"),
}

pulp_task_commands = {
    "show": _template("task", "show", "--href", "%s"),
    "cancel": _template("task", "cancel", "--href", "%s"),
}


# File plugin operations.
pulp_file_commands = {
    "create_repository": _template("file", "repository", "create", "--name", "%s"),
    "show_repository": _template("file", "repository", "show", "--name", "%s"),
    "content_upload": _template(
        "file", "content", "upload", "--repository", "%s",
        "--file", "%s", "--relative-path", "%s",
    ),
    "publication_create": _template(
        "file", "publication", "create", "--repository", "%s",
    ),
    "show_distribution": _template("file", "distribution", "show", "--name", "%s"),
    "distribution_create": _template(
        "file", "distribution", "create", "--name", "%s",
        "--base-path", "%s", "--repository", "%s",
    ),
    "distribution_update": _template(
        "file", "distribution", "update", "--name", "%s",
        "--base-path", "%s", "--repository", "%s",
    ),
    "delete_repository": _template("file", "repository", "destroy", "--name", "%s"),
    "delete_distribution": _template("file", "distribution", "destroy", "--name", "%s"),
    "delete_publication": _template("file", "publication", "destroy", "--href", "%s"),
    "list_publications": _template(
        "file", "publication", "list", "--repository", "%s", "--limit", "1000",
    ),
    "list_repositories": _template("file", "repository", "list", "--limit", "1000"),
    "list_distributions": _template("file", "distribution", "list", "--limit", "1000"),
    "list_content": _template(
        "file", "content", "list", "--repository-version", "%s", "--limit", "1000",
    ),
    "show_repository_version": _template(
        "file", "repository", "version", "show", "--repository", "%s",
    ),
    "orphan_cleanup": pulp_common_commands["orphan_cleanup"],
}


# Python/PyPI plugin operations.
pulp_python_commands = {
    "create_repository": _template("python", "repository", "create", "--name", "%s"),
    "show_repository": _template("python", "repository", "show", "--name", "%s"),
    "delete_repository": _template("python", "repository", "destroy", "--name", "%s"),
    "list_repositories": _template("python", "repository", "list", "--limit", "1000"),
    "show_distribution": _template("python", "distribution", "show", "--name", "%s"),
    "delete_distribution": _template("python", "distribution", "destroy", "--name", "%s"),
    "list_distributions": _template("python", "distribution", "list", "--limit", "1000"),
    "publication_create": _template(
        "python", "publication", "create", "--repository", "%s",
    ),
    "list_publications": _template(
        "python", "publication", "list", "--repository", "%s", "--limit", "1000",
    ),
    "delete_publication": _template("python", "publication", "destroy", "--href", "%s"),
    "content_upload": _template(
        "python", "content", "upload", "--repository", "%s",
        "--file", "%s", "--relative-path", "%s",
    ),
    "distribution_create": _template(
        "python", "distribution", "create", "--name", "%s",
        "--repository", "%s", "--base-path", "%s",
    ),
    "distribution_update": _template(
        "python", "distribution", "update", "--name", "%s",
        "--repository", "%s", "--base-path", "%s",
    ),
    "orphan_cleanup": pulp_common_commands["orphan_cleanup"],
}


# Container plugin operations.
pulp_container_commands = {
    "create_repository": _template("container", "repository", "create", "--name", "%s"),
    "show_repository": _template("container", "repository", "show", "--name", "%s"),
    # Compatibility names retained while callers are migrated.
    "create_container_repo": _template("container", "repository", "create", "--name", "%s"),
    "show_container_repo": _template("container", "repository", "show", "--name", "%s"),
    "show_repository_href": _template("container", "repository", "show", "--href", "%s"),
    "show_repository_version": _template(
        "container", "repository", "version", "show", "--repository-href", "%s",
    ),
    "show_remote": _template("container", "remote", "show", "--name", "%s"),
    "show_container_remote": _template("container", "remote", "show", "--name", "%s"),
    "list_remote_tags": _template(
        "container", "remote", "list", "--name", "%s", "--field", "includes",
    ),
    "list_container_remote_tags": _template(
        "container", "remote", "list", "--name", "%s", "--field", "includes",
    ),
    "create_container_remote": _template(
        "container", "remote", "create", "--name", "%s", "--url", "%s",
        "--upstream-name", "%s", "--policy", "%s",
        "--include-tags", '["%s"]', "--exclude-tags", '["*sha256*.sig"]',
    ),
    "create_container_remote_for_digest": _template(
        "container", "remote", "create", "--name", "%s", "--url", "%s",
        "--upstream-name", "%s", "--policy", "%s",
        "--exclude-tags", '["*sha256*.sig"]',
    ),
    "update_remote_for_digest": _template(
        "container", "remote", "update", "--name", "%s", "--url", "%s",
        "--upstream-name", "%s", "--policy", "%s",
        "--exclude-tags", '["*sha256*.sig"]',
    ),
    "update_container_remote": _template(
        "container", "remote", "update", "--name", "%s", "--url", "%s",
        "--upstream-name", "%s", "--policy", "%s",
        "--include-tags", "%s", "--exclude-tags", '["*sha256*.sig"]',
    ),
    "create_container_remote_auth": _template(
        "container", "remote", "create", "--name", "%s", "--url", "%s",
        "--upstream-name", "%s", "--policy", "%s",
        "--include-tags", "%s", "--exclude-tags", '["*sha256*.sig"]',
        "--username", "%s", "--password", "%s",
    ),
    "update_container_remote_auth": _template(
        "container", "remote", "update", "--name", "%s", "--url", "%s",
        "--upstream-name", "%s", "--policy", "%s",
        "--include-tags", "%s", "--exclude-tags", '["*sha256*.sig"]',
        "--username", "%s", "--password", "%s",
    ),
    "create_container_remote_for_digest_auth": _template(
        "container", "remote", "create", "--name", "%s", "--url", "%s",
        "--upstream-name", "%s", "--policy", "%s",
        "--exclude-tags", '["*sha256*.sig"]',
        "--username", "%s", "--password", "%s",
    ),
    "update_remote_for_digest_auth": _template(
        "container", "remote", "update", "--name", "%s", "--url", "%s",
        "--upstream-name", "%s", "--policy", "%s",
        "--exclude-tags", '["*sha256*.sig"]',
        "--username", "%s", "--password", "%s",
    ),
    "sync_repository": _template(
        "container", "repository", "sync", "--name", "%s", "--remote", "%s",
    ),
    "sync_container_repository": _template(
        "container", "repository", "sync", "--name", "%s", "--remote", "%s",
    ),
    "show_distribution": _template("container", "distribution", "show", "--name", "%s"),
    "container_distribution_show": _template(
        "container", "distribution", "show", "--name", "%s",
    ),
    "show_container_distribution": _template(
        "container", "distribution", "show", "--name", "%s",
    ),
    "distribution_create": _template(
        "container", "distribution", "create", "--name", "%s",
        "--repository", "%s", "--base-path", "%s",
    ),
    "distribute_container_repository": _template(
        "container", "distribution", "create", "--name", "%s",
        "--repository", "%s", "--base-path", "%s",
    ),
    "distribution_update": _template(
        "container", "distribution", "update", "--name", "%s",
        "--repository", "%s", "--base-path", "%s",
    ),
    "update_container_distribution": _template(
        "container", "distribution", "update", "--name", "%s",
        "--repository", "%s", "--base-path", "%s",
    ),
    "list_image_tags": _template(
        "show", "--href",
        "/pulp/api/v3/content/container/tags/?repository_version=%s",
    ),
    "list_repository_tags": _template(
        "container", "repository", "content", "-t", "tag", "list",
        "--repository", "%s", "--limit", "%s", "--offset", "%s",
    ),
    "untag_repository": _template(
        "container", "repository", "untag", "--name", "%s", "--tag", "%s",
    ),
    "list_repositories": _template("container", "repository", "list", "--limit", "1000"),
    "delete_repository": _template("container", "repository", "destroy", "--name", "%s"),
    "list_distributions": _template("container", "distribution", "list", "--limit", "1000"),
    "delete_distribution": _template("container", "distribution", "destroy", "--name", "%s"),
    "list_remotes": _template("container", "remote", "list", "--limit", "1000"),
    "delete_remote": _template("container", "remote", "destroy", "--name", "%s"),
}


# RPM plugin operations.
pulp_rpm_commands = {
    "create_repository": _template("rpm", "repository", "create", "--name", "%s"),
    "show_repository": _template("rpm", "repository", "show", "--name", "%s"),
    "show_remote": _template("rpm", "remote", "show", "--name", "%s"),
    "create_remote": _template(
        "rpm", "remote", "create", "--name", "%s", "--url", "%s", "--policy", "%s",
    ),
    "update_remote": _template(
        "rpm", "remote", "update", "--name", "%s", "--url", "%s", "--policy", "%s",
    ),
    "create_remote_cert": _template(
        "rpm", "remote", "create", "--name", "%s", "--url", "%s", "--policy", "%s",
        "--ca-cert", "%s", "--client-cert", "%s", "--client-key", "%s",
    ),
    "update_remote_cert": _template(
        "rpm", "remote", "update", "--name", "%s", "--url", "%s", "--policy", "%s",
        "--ca-cert", "%s", "--client-cert", "%s", "--client-key", "%s",
    ),
    "sync_repository": _template(
        "rpm", "repository", "sync", "--name", "%s", "--remote", "%s",
    ),
    "publish_repository": _template(
        "rpm", "publication", "create", "--repository", "%s",
    ),
    "publish_repository_version": _template(
        "rpm", "publication", "create", "--repository", "%s", "--version", "%s",
    ),
    "distribute_repository": _template(
        "rpm", "distribution", "create", "--name", "%s",
        "--base-path", "%s", "--repository", "%s",
    ),
    "update_distribution": _template(
        "rpm", "distribution", "update", "--name", "%s",
        "--base-path", "%s", "--repository", "%s",
    ),
    "update_distribution_publication": _template(
        "rpm", "distribution", "update", "--name", "%s", "--publication", "%s",
    ),
    "update_distribution_repo_config": _template(
        "rpm", "distribution", "update", "--name", "%s", "--generate-repo-config",
    ),
    "check_distribution": _template("rpm", "distribution", "show", "--name", "%s"),
    "delete_repository": _template("rpm", "repository", "destroy", "--name", "%s"),
    "delete_remote": _template("rpm", "remote", "destroy", "--name", "%s"),
    "delete_distribution": _template("rpm", "distribution", "destroy", "--name", "%s"),
    "check_publication": _template(
        "rpm", "publication", "list", "--repository", "%s", "--limit", "1000",
    ),
    "list_publications": _template(
        "rpm", "publication", "list", "--repository", "%s", "--limit", "1000",
    ),
    "list_all_publications": _template("rpm", "publication", "list", "--limit", "1000"),
    "delete_publication": _template("rpm", "publication", "destroy", "--href", "%s"),
    "get_repo_version": _template("rpm", "repository", "show", "--name", "%s"),
    "repository_version_destroy": _template(
        "rpm", "repository", "version", "destroy", "--repository", "%s", "--version", "%s",
    ),
    "list_repositories": _template("rpm", "repository", "list", "--limit", "1000"),
    "list_remotes": _template("rpm", "remote", "list", "--limit", "1000"),
    "list_distributions": _template("rpm", "distribution", "list", "--limit", "1000"),
    "list_distributions_with_urls": _template(
        "rpm", "distribution", "list", "--field", "base_url,name", "--limit", "1000",
    ),
    "upload_content": _template(
        "rpm", "content", "upload", "--repository", "%s", "--file", "%s",
    ),
    "copy_content": _template("rpm", "copy", "--config", "%s"),
    "pulp_cleanup": pulp_common_commands["orphan_cleanup_default"],
    "orphan_cleanup": pulp_common_commands["orphan_cleanup"],
}


def command_argv(command, executable=None):
    """Return fresh argv, optionally selecting a configured CLI executable."""
    if not isinstance(command, Sequence) or isinstance(command, (str, bytes)):
        raise TypeError("Pulp command must be a structured argument sequence")
    arguments = [str(argument) for argument in command]
    if not arguments:
        raise ValueError("Pulp command must not be empty")
    if executable is not None:
        arguments[0] = str(executable)
    return arguments


def ensure_pulp_command(arguments):
    """Return argv with the configured Pulp executable exactly once."""
    command = [str(argument) for argument in arguments]
    if command and command[0] == PULP_CLI_EXECUTABLE:
        return command
    return [PULP_CLI_EXECUTABLE, *command]


__all__ = [
    "PulpCommandTemplate",
    "build_container_remote_command",
    "build_container_tags_href",
    "build_pulp_entity_command",
    "build_pulp_task_list_command",
    "command_argv",
    "ensure_pulp_command",
    "pulp_common_commands",
    "pulp_container_commands",
    "pulp_file_commands",
    "pulp_python_commands",
    "pulp_rpm_commands",
    "pulp_task_commands",
]
