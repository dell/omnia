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

"""Resolve Repo Manager runtime paths from the Omnia environment contract."""

import os


DEFAULT_OMNIA_DATA_PATH = "/opt/omnia"
DEFAULT_PROJECT_NAME = "project_default"


def _environment(environ=None):
    """Return the supplied environment or the current process environment."""
    return os.environ if environ is None else environ


def _normalized_path(value):
    """Return an absolute, normalized path without resolving filesystem links."""
    return os.path.abspath(os.path.normpath(os.path.expanduser(str(value))))


def get_omnia_data_path(environ=None):
    """Return OMNIA_DATA_PATH, retaining OMNIA_BASE_DIR as a legacy alias."""
    env = _environment(environ)
    configured_path = (
        env.get("OMNIA_DATA_PATH")
        or env.get("OMNIA_BASE_DIR")
        or DEFAULT_OMNIA_DATA_PATH
    )
    return _normalized_path(configured_path)


def get_repo_manager_data_path(environ=None):
    """Return the Repo Manager runtime root directory."""
    env = _environment(environ)
    configured_path = env.get("REPO_MANAGER_DATA_PATH")
    if configured_path:
        return _normalized_path(configured_path)
    return os.path.join(get_omnia_data_path(env), "repo_manager")


def get_project_name(environ=None):
    """Return and validate the project name used as a single path segment."""
    env = _environment(environ)
    project_name = (env.get("OMNIA_PROJECT_NAME") or DEFAULT_PROJECT_NAME).strip()
    if (
        not project_name
        or project_name in (".", "..")
        or os.path.basename(project_name) != project_name
    ):
        raise ValueError("OMNIA_PROJECT_NAME must be a single non-empty path segment")
    return project_name


def get_input_project_dir(environ=None):
    """Return the explicit or derived Repo Manager project input directory."""
    env = _environment(environ)
    explicit_path = env.get("REPO_MANAGER_INPUT_PROJECT_DIR")
    if explicit_path:
        return _normalized_path(explicit_path)
    return os.path.join(
        get_repo_manager_data_path(env), "input", get_project_name(env)
    )


def is_path_within(path, parent):
    """Return whether path is a strict descendant of parent."""
    normalized_path = _normalized_path(path)
    normalized_parent = _normalized_path(parent)
    try:
        return (
            os.path.commonpath((normalized_path, normalized_parent))
            == normalized_parent
            and normalized_path != normalized_parent
        )
    except ValueError:
        return False


def validate_cleanup_root(path, source_root=None):
    """Validate that a runtime root is not dangerously broad for cleanup."""
    if path is None or not str(path).strip():
        raise ValueError("Repo Manager cleanup root must not be empty")
    normalized_path = _normalized_path(path)
    forbidden_paths = {
        "/",
        "/opt",
        "/var",
        "/etc",
        "/usr",
        "/root",
        _normalized_path(os.path.expanduser("~")),
    }
    if source_root:
        forbidden_paths.add(_normalized_path(source_root))
    if normalized_path in forbidden_paths:
        raise ValueError(f"Unsafe Repo Manager cleanup root: {normalized_path}")
    return normalized_path


def validate_cleanup_child(parent, *segments):
    """Return a safe cleanup target strictly contained below ``parent``.

    Every child component must be a single relative path segment.  This keeps
    catalog or CLI supplied names from replacing the parent through an
    absolute path or escaping it through ``..`` traversal.
    """
    normalized_parent = _normalized_path(parent)
    clean_segments = []
    for segment in segments:
        value = str(segment) if segment is not None else ""
        if (
            not value
            or value in (".", "..")
            or os.path.isabs(value)
            or os.path.basename(value) != value
            or "\x00" in value
        ):
            raise ValueError(f"Unsafe cleanup path segment: {value!r}")
        clean_segments.append(value)

    target = _normalized_path(os.path.join(normalized_parent, *clean_segments))
    if not is_path_within(target, normalized_parent):
        raise ValueError(f"Cleanup target escapes allowed root: {target}")
    resolved_parent = os.path.realpath(normalized_parent)
    resolved_target = os.path.realpath(target)
    try:
        if (
            os.path.commonpath((resolved_target, resolved_parent))
            != resolved_parent
            or resolved_target == resolved_parent
        ):
            raise ValueError(f"Cleanup target escapes allowed root through a symlink: {target}")
    except ValueError as error:
        raise ValueError(f"Unsafe cleanup target: {target}") from error
    return target


__all__ = [
    "DEFAULT_OMNIA_DATA_PATH",
    "DEFAULT_PROJECT_NAME",
    "get_omnia_data_path",
    "get_repo_manager_data_path",
    "get_project_name",
    "get_input_project_dir",
    "is_path_within",
    "validate_cleanup_root",
    "validate_cleanup_child",
]
