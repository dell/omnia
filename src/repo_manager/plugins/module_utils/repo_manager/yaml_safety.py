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

"""Safely load runtime YAML before Ansible can evaluate its values."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


FORBIDDEN_TEMPLATE_TOKENS = ("{{", "{%", "{#")
MAX_YAML_NESTING_DEPTH = 100


class YamlSafetyError(ValueError):
    """Base exception for sanitized runtime-YAML validation failures."""

    def __init__(self, code: str, location: str = "$") -> None:
        super().__init__(code)
        self.code = code
        self.location = location


class YamlTemplateSyntaxError(YamlSafetyError):
    """Raised when runtime YAML contains Ansible/Jinja template syntax."""


@dataclass
class _TraversalState:
    """Track completed and active YAML aliases during recursive validation."""

    seen: set[int] = field(default_factory=set)
    active: set[int] = field(default_factory=set)


def _validate_container(
    container: Any,
    children: Iterable[tuple[Any, str]],
    location: str,
    state: _TraversalState,
    depth: int,
) -> None:
    """Validate one collection while handling shared and recursive aliases."""
    object_id = id(container)
    if object_id in state.active:
        raise YamlSafetyError("recursive_alias_forbidden", location)
    if object_id in state.seen:
        return

    state.active.add(object_id)
    try:
        for child, child_location in children:
            _validate_value(child, child_location, state, depth + 1)
    finally:
        state.active.remove(object_id)
    state.seen.add(object_id)


def _validate_value(
    value: Any,
    location: str,
    state: _TraversalState,
    depth: int,
) -> None:
    """Recursively reject template syntax without rendering input values."""
    if depth > MAX_YAML_NESTING_DEPTH:
        raise YamlSafetyError("maximum_nesting_depth_exceeded", location)

    if isinstance(value, str):
        if any(token in value for token in FORBIDDEN_TEMPLATE_TOKENS):
            raise YamlTemplateSyntaxError("template_syntax_forbidden", location)
        return

    if isinstance(value, (bytes, bytearray)):
        if any(
            token.encode("ascii") in value
            for token in FORBIDDEN_TEMPLATE_TOKENS
        ):
            raise YamlTemplateSyntaxError("template_syntax_forbidden", location)
        return

    if isinstance(value, Mapping):
        children = (
            child
            for index, (key, item) in enumerate(value.items())
            for child in (
                (key, f"{location}.key[{index}]"),
                (item, f"{location}.value[{index}]"),
            )
        )
        _validate_container(value, children, location, state, depth)
        return

    if isinstance(value, (list, tuple, set, frozenset)):
        children = (
            (item, f"{location}[{index}]")
            for index, item in enumerate(value)
        )
        _validate_container(value, children, location, state, depth)


def validate_runtime_yaml_data(data: Any) -> None:
    """Reject Jinja delimiters in every key and value of parsed YAML data."""
    _validate_value(data, "$", _TraversalState(), 0)


def load_runtime_yaml(
    file_path: str,
    *,
    required: bool = True,
    require_mapping: bool = True,
) -> tuple[Any, bool]:
    """Load and validate a runtime YAML file without passing it through Jinja.

    Returns:
        A tuple containing the parsed data and whether the file exists.

    Raises:
        FileNotFoundError: If a required file is missing.
        YamlSafetyError: If the content is invalid or contains template syntax.
    """
    path = Path(file_path)
    if not path.is_file():
        if required:
            raise FileNotFoundError(file_path)
        return {}, False

    try:
        with path.open("r", encoding="utf-8") as yaml_file:
            data = yaml.safe_load(yaml_file)
    except yaml.YAMLError as exc:
        location = "$"
        problem_mark = getattr(exc, "problem_mark", None)
        if problem_mark is not None:
            location = (
                f"line {problem_mark.line + 1}, "
                f"column {problem_mark.column + 1}"
            )
        raise YamlSafetyError("invalid_yaml", location) from exc
    except (OSError, UnicodeError) as exc:
        raise YamlSafetyError("yaml_read_failed") from exc

    if data is None:
        data = {}
    if require_mapping and not isinstance(data, Mapping):
        raise YamlSafetyError("mapping_required")

    validate_runtime_yaml_data(data)
    return data, True
