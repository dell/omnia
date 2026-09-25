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

"""Canonical project-name and runtime-path resolution for Orchestrator tests."""

import os
import re

from omnia_auto import (
    read_remote_env,
    resolve_domain_data_path,
    resolve_domain_input_path,
)

DOMAIN_NAME = "orchestrator"
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_ORCHESTRATOR_DATA_PATH = "ORCHESTRATOR_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"
DEFAULT_OMNIA_DATA_PATH = "/opt/omnia"
DEFAULT_PROJECT_NAME = "project_default"
PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _validate_project_name(project: str) -> str:
    """Validate and return one runtime project identifier."""
    if (
        not isinstance(project, str)
        or not PROJECT_NAME_PATTERN.fullmatch(project)
        or project in {".", ".."}
    ):
        raise ValueError(f"Unsafe project_name: {project!r}")
    return project


def resolve_project_name(_config=None) -> str:
    """Return the local runtime project from the Omnia environment."""
    project = os.environ.get(ENV_OMNIA_PROJECT_NAME, DEFAULT_PROJECT_NAME)
    return _validate_project_name(project)


def resolve_shared_path(_config=None) -> str:
    """Return the local Orchestrator data root using domain precedence."""
    domain_path = os.environ.get(ENV_ORCHESTRATOR_DATA_PATH, "")
    if domain_path:
        shared_path = domain_path.rstrip("/")
    else:
        omnia_path = os.environ.get(
            ENV_OMNIA_DATA_PATH, DEFAULT_OMNIA_DATA_PATH
        ).rstrip("/")
        shared_path = os.path.join(omnia_path, DOMAIN_NAME)
    if not os.path.isabs(shared_path) or shared_path == "/":
        raise ValueError("Resolved Orchestrator data path must be safe and absolute")
    return shared_path


def _resolve_project_path(_config, path_kind: str) -> str:
    """Resolve one local path from environment-backed runtime context."""
    return os.path.join(resolve_shared_path(), path_kind, resolve_project_name())


def resolve_input_project_path(config=None) -> str:
    """Return the local Orchestrator input project directory."""
    return _resolve_project_path(config, "input")


def resolve_output_project_path(config=None) -> str:
    """Return the local Orchestrator output project directory."""
    return _resolve_project_path(config, "output")


def resolve_target_project_name(host) -> str:
    """Return the project selected by the target Omnia environment."""
    return _validate_project_name(read_remote_env(host, ENV_OMNIA_PROJECT_NAME))


def resolve_target_shared_path(host) -> str:
    """Return the target Orchestrator data root using domain precedence."""
    return resolve_domain_data_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        domain_data_path_var=ENV_ORCHESTRATOR_DATA_PATH,
    )


def resolve_target_input_project_path(host) -> str:
    """Return the target Orchestrator input project directory."""
    return resolve_domain_input_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        ENV_OMNIA_PROJECT_NAME,
        domain_data_path_var=ENV_ORCHESTRATOR_DATA_PATH,
    )


def resolve_target_output_project_path(host) -> str:
    """Return the target Orchestrator output project directory."""
    return os.path.join(
        resolve_target_shared_path(host),
        "output",
        resolve_target_project_name(host),
    )


def resolve_target_omnia_data_path(host) -> str:
    """Return the target Omnia data root."""
    data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH).rstrip("/")
    if not os.path.isabs(data_path) or data_path == "/":
        raise ValueError("Target OMNIA_DATA_PATH must be safe and absolute")
    return data_path
