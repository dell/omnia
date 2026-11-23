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

"""Unit tests for ER-ORCH-009 current-run status reconciliation (FR-5.2).

Covers:
  - TC_UT_status_009: Current-run status reconciler
  - TC_NFT_supportability_006: Evidence sanitization
  - TC_FVT_status_010: Current failure supersedes stale prior success
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))


STATUS_PKG_ROOT = SOURCE_PLUGIN_ROOT / "module_utils" / "orchestrator_status"
if str(STATUS_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(STATUS_PKG_ROOT))


def _load_source_module(name, relative_path):
    path = ORCHESTRATOR_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_errors_module = _load_source_module(
    "errors",
    "plugins/module_utils/orchestrator_status/errors.py",
)

status_module = _load_source_module(
    "flexible_group_status",
    "plugins/module_utils/orchestrator_status/flexible_group_status.py",
)

reconcile_functional_group_status = status_module.reconcile_functional_group_status
TypedStageResult = status_module.TypedStageResult
sanitize_value = status_module.sanitize_value
StageType = status_module.StageType
StageStatus = status_module.StageStatus
OverallStatus = status_module.OverallStatus
StatusReconcileError = status_module.StatusReconcileError


# ==============================================================================
# TC_UT_status_009: Current-run status reconciler
# ==============================================================================


def test_status_reconciler_finalizes_successful_stages():
    """Verify all verified stages report overall success with per-stage evidence."""
    stages = [
        TypedStageResult(
            stage=StageType.VALIDATION.value,
            status=StageStatus.SUCCESS.value,
            details={"rules_checked": 15},
        ),
        TypedStageResult(
            stage=StageType.IMAGE_PRECHECK.value,
            status=StageStatus.SUCCESS.value,
            details={"image_verified": True},
        ),
        TypedStageResult(
            stage=StageType.SMD_GROUP.value,
            status=StageStatus.SUCCESS.value,
            details={"group_name": "fg_ai_rhel_10_2_x86_64"},
        ),
        TypedStageResult(
            stage=StageType.BSS.value,
            status=StageStatus.SUCCESS.value,
            details={"boot_config": "fg_ai_rhel_10_2_x86_64"},
        ),
        TypedStageResult(
            stage=StageType.METADATA.value,
            status=StageStatus.SUCCESS.value,
            details={"metadata_group": "fg_ai_rhel_10_2_x86_64"},
        ),
    ]

    report = reconcile_functional_group_status(
        project_name="test_proj",
        run_id="run-001",
        operation="add",
        target_group="fg_ai_rhel_10_2_x86_64",
        stage_results=stages,
    )

    assert report["overall_status"] == OverallStatus.SUCCESS.value
    assert report["project_name"] == "test_proj"
    assert report["run_id"] == "run-001"
    assert report["operation"] == "add"
    assert report["target_group"] == "fg_ai_rhel_10_2_x86_64"
    assert len(report["stages"]) == 5
    assert all(s["status"] == "success" for s in report["stages"])


def test_status_reconciler_preserves_current_failure_over_prior_success():
    """FR-5.2: Verify current failure replaces stale prior success."""
    prior_status = {
        "run_id": "run-prior-success",
        "overall_status": "success",
        "timestamp": "2026-11-10T12:00:00Z",
        "target_group": "fg_ai_rhel_10_2_x86_64",
    }

    # Current run fails during BSS publication
    stages = [
        TypedStageResult(
            stage=StageType.VALIDATION.value,
            status=StageStatus.SUCCESS.value,
        ),
        TypedStageResult(
            stage=StageType.SMD_GROUP.value,
            status=StageStatus.SUCCESS.value,
        ),
        TypedStageResult(
            stage=StageType.BSS.value,
            status=StageStatus.FAILED.value,
            diagnostic_category="BSS_HTTP_500",
            details={"error": "BSS endpoint unavailable"},
        ),
    ]

    report = reconcile_functional_group_status(
        project_name="test_proj",
        run_id="run-current-fail",
        operation="add",
        target_group="fg_ai_rhel_10_2_x86_64",
        stage_results=stages,
        previous_status=prior_status,
    )

    # Current failure must win!
    assert report["overall_status"] == OverallStatus.FAILED.value
    assert report["primary_diagnostic"] == "BSS_HTTP_500"

    # Prior success is retained only as historical evidence
    assert report["history"]["prior_run_id"] == "run-prior-success"
    assert report["history"]["prior_overall_status"] == "success"
    assert report["history"]["prior_timestamp"] == "2026-11-10T12:00:00Z"


def test_status_reconciler_reports_noop():
    """Verify that all-noop stages produce an overall noop outcome."""
    stages = [
        TypedStageResult(
            stage=StageType.SMD_GROUP.value,
            status=StageStatus.NO_OP.value,
            details={"message": "Already present"},
        ),
        TypedStageResult(
            stage=StageType.BSS.value,
            status=StageStatus.NO_OP.value,
            details={"message": "Already present"},
        ),
        TypedStageResult(
            stage=StageType.METADATA.value,
            status=StageStatus.NO_OP.value,
            details={"message": "Already present"},
        ),
    ]

    report = reconcile_functional_group_status(
        project_name="test_proj",
        run_id="run-noop",
        operation="add",
        target_group="fg_ai_rhel_10_2_x86_64",
        stage_results=stages,
    )

    assert report["overall_status"] == OverallStatus.NO_OP.value


def test_typed_stage_result_validation():
    """Verify TypedStageResult rejects invalid stages and statuses."""
    with pytest.raises(StatusReconcileError) as exc_info:
        TypedStageResult(stage="invalid_stage_name", status="success")
    assert "Invalid stage" in str(exc_info.value)

    with pytest.raises(StatusReconcileError) as exc_info:
        TypedStageResult(stage=StageType.BSS.value, status="invalid_status")
    assert "Invalid stage status" in str(exc_info.value)


# ==============================================================================
# TC_NFT_supportability_006: Evidence sanitization
# ==============================================================================


def test_evidence_sanitizer_removes_credentials_and_secrets():
    """FR-5.2 / NFR-5: Verify sensitive keys and secret patterns are redacted."""
    raw_details = {
        "admin_user": "operator",
        "admin_password": "super_secret_password_123",
        "api_token": "bearer_token_xyz987",
        "ssh_private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----",
        "vaulted_secret": "$ANSIBLE_VAULT;1.1;AES256;12345",
        "cloud_init_content": "#cloud-config\nusers:\n  - name: root\n",
        "safe_diagnostic": {
            "exit_code": 0,
            "target": "fg_ai_rhel_10_2_x86_64",
            "nested_secret": {
                "auth_credential": "vaulted_cred_value",
            },
        },
    }

    sanitized = sanitize_value(raw_details)

    assert sanitized["admin_user"] == "operator"
    assert sanitized["admin_password"] == "[REDACTED]"
    assert sanitized["api_token"] == "[REDACTED]"
    assert sanitized["ssh_private_key"] == "[REDACTED]"
    assert sanitized["vaulted_secret"] == "[REDACTED]"
    assert sanitized["cloud_init_content"] == "[REDACTED]"
    assert sanitized["safe_diagnostic"]["exit_code"] == 0
    assert sanitized["safe_diagnostic"]["nested_secret"] == "[REDACTED]"
