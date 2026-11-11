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

"""Shared result and configuration helpers for prepare verification."""

from collections.abc import Mapping
from typing import Any

import yaml


def prepare_result(
    success: bool,
    summary: str,
    fields: list[tuple[str, object]],
    error: str = "",
    *,
    skipped: bool = False,
) -> dict[str, Any]:
    """Return the common structured result used by prepare tests."""
    return {
        "success": success,
        "skipped": skipped,
        "details": summary,
        "fields": fields,
        "error": error,
    }


def read_yaml_mapping(host, path: str) -> Mapping[str, Any]:
    """Read a required remote YAML mapping without logging its content."""
    remote = host.file(path)
    if not remote.is_file:
        raise ValueError(f"Required YAML file is missing: {path}")
    try:
        content = yaml.safe_load(remote.content_string) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(content, dict):
        raise TypeError(f"Expected a YAML mapping in {path}")
    return content
