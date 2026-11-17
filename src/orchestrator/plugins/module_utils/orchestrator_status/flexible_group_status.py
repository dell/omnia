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

# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-few-public-methods

"""Typed current-run status reconciliation and evidence sanitization for flexible groups.

Implements ER-ORCH-009 FR-5.2 and HLD Section 5.5:
  - Typed stage results for validation, image precheck, SMD, BSS, and metadata
  - Strict evidence sanitization removing credentials and raw cloud-init
  - Truthful current-run aggregate where current failure replaces stale prior success
  - Retention of prior successful state as historical evidence only
"""

from __future__ import annotations

import re
import time
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

try:
    from .errors import StatusReconcileError
except ImportError:
    try:
        from errors import StatusReconcileError  # type: ignore
    except ImportError:
        from ansible.module_utils.orchestrator_status.errors import (  # type: ignore
            StatusReconcileError,
        )

SCHEMA_VERSION = "1.0"

SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(password|token|secret|credential|private_key|auth|api_key|cert)"
)
SECRET_CONTENT_PATTERNS = [
    re.compile(r"\$ANSIBLE_VAULT;\d+\.\d+;[A-Z0-9]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"#cloud-config"),
]


class StageType(str, Enum):
    """Allowed lifecycle stages for flexible functional groups."""

    VALIDATION = "validation"
    IMAGE_PRECHECK = "image_precheck"
    SMD_GROUP = "smd_group"
    BSS = "bss"
    METADATA = "metadata"


class StageStatus(str, Enum):
    """Execution status of an individual stage."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    NO_OP = "noop"


class OverallStatus(str, Enum):
    """Overall terminal status of a flexible group operation."""

    SUCCESS = "success"
    FAILED = "failed"
    NO_OP = "noop"


@dataclass
class TypedStageResult:
    """Typed result representation for an individual lifecycle stage."""

    stage: str
    status: str
    diagnostic_category: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if self.stage not in {s.value for s in StageType}:
            raise StatusReconcileError(
                f"Invalid stage '{self.stage}'. Allowed stages: {[s.value for s in StageType]}"
            )
        if self.status not in {s.value for s in StageStatus}:
            raise StatusReconcileError(
                f"Invalid stage status '{self.status}'. Allowed: {[s.value for s in StageStatus]}"
            )
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sanitize_value(value: Any) -> Any:
    """Recursively scrub credentials and secret-bearing content from diagnostic data."""
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            if SENSITIVE_KEY_PATTERN.search(str(k)):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_value(v)
        return sanitized

    if isinstance(value, list):
        return [sanitize_value(item) for item in value]

    if isinstance(value, str):
        for pattern in SECRET_CONTENT_PATTERNS:
            if pattern.search(value):
                return "[REDACTED]"
        return value

    return value


def sanitize_stage_result(result: dict[str, Any]) -> dict[str, Any]:
    """Sanitize one stage result dictionary, ensuring safe diagnostic output."""
    clean = deepcopy(result)
    details = clean.get("details", {})
    clean["details"] = sanitize_value(details)
    return clean


def reconcile_functional_group_status(
    *,
    project_name: str,
    run_id: str,
    operation: str,
    target_group: str,
    stage_results: list[dict[str, Any] | TypedStageResult],
    previous_status: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Reconcile current-run flexible group status truthfully (FR-5.2).

    Current failure ALWAYS supersedes prior success; prior success is retained
    in the history block as historical evidence only.
    """
    ts = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    normalized_stages: list[dict[str, Any]] = []
    has_failure = False
    all_noop = True
    primary_diagnostic = ""

    for item in stage_results:
        raw = asdict(item) if isinstance(item, TypedStageResult) else deepcopy(item)
        stage_name = raw.get("stage", "")
        stage_status = raw.get("status", "")

        if stage_status == StageStatus.FAILED.value:
            has_failure = True
            all_noop = False
            if not primary_diagnostic:
                primary_diagnostic = raw.get("diagnostic_category") or f"{stage_name}_failed"
        elif stage_status == StageStatus.SUCCESS.value:
            all_noop = False
        elif stage_status != StageStatus.NO_OP.value:
            all_noop = False

        normalized_stages.append(sanitize_stage_result(raw))

    if has_failure:
        current_overall = OverallStatus.FAILED.value
    elif all_noop and normalized_stages:
        current_overall = OverallStatus.NO_OP.value
    else:
        current_overall = OverallStatus.SUCCESS.value

    # Build historical reference from previous_status
    history_entry: dict[str, Any] = {}
    if previous_status and isinstance(previous_status, dict):
        history_entry = {
            "prior_run_id": previous_status.get("run_id", ""),
            "prior_overall_status": previous_status.get("overall_status", ""),
            "prior_timestamp": previous_status.get("timestamp", ""),
            "prior_target_group": previous_status.get("target_group", ""),
        }

    status_report = {
        "schema_version": SCHEMA_VERSION,
        "project_name": str(project_name),
        "run_id": str(run_id),
        "timestamp": ts,
        "operation": str(operation),
        "target_group": str(target_group),
        "overall_status": current_overall,
        "primary_diagnostic": primary_diagnostic,
        "stages": normalized_stages,
        "history": history_entry,
    }

    return status_report
