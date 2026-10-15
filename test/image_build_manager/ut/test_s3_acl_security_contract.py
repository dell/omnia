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

"""Regression tests for S3 bucket ACL security contract (CWE-732/CWE-284).

Verifies that:
- S3 ACL tasks are guarded by the s3_enable_anonymous_access variable
- The variable defaults to true for backward compatibility
- Both s3_bucket.yml and set_s3_acl.yml use the same guard
- The deploy_minio vars define the configurable variable with a security warning
"""

from pathlib import Path

import pytest
import yaml

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "image_build_manager"
_S3_BUCKET_YML = _SRC_ROOT / "roles" / "deploy_minio" / "tasks" / "s3_bucket.yml"
_SET_S3_ACL_YML = _SRC_ROOT / "roles" / "build_os_images" / "tasks" / "set_s3_acl.yml"
_DEPLOY_MINIO_VARS = _SRC_ROOT / "roles" / "deploy_minio" / "vars" / "main.yml"


def _load_tasks(path: Path) -> list[dict]:
    """Load an Ansible task list from a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _acl_tasks(tasks: list[dict]) -> list[dict]:
    """Return tasks that set S3 ACL to public."""
    return [t for t in tasks if "acl-public" in str(t.get("ansible.builtin.command", ""))]


class TestS3AclGuard:
    """Every public-ACL task must be gated by s3_enable_anonymous_access."""

    def test_s3_bucket_acl_tasks_are_guarded(self) -> None:
        tasks = _load_tasks(_S3_BUCKET_YML)
        acl = _acl_tasks(tasks)
        assert len(acl) >= 2, "Expected at least 2 ACL tasks in s3_bucket.yml"
        for task in acl:
            when = str(task.get("when", ""))
            assert "s3_enable_anonymous_access" in when, (
                f"ACL task '{task.get('name')}' is missing s3_enable_anonymous_access guard"
            )

    def test_set_s3_acl_tasks_are_guarded(self) -> None:
        tasks = _load_tasks(_SET_S3_ACL_YML)
        acl = _acl_tasks(tasks)
        assert len(acl) >= 2, "Expected at least 2 ACL tasks in set_s3_acl.yml"
        for task in acl:
            when = str(task.get("when", ""))
            assert "s3_enable_anonymous_access" in when, (
                f"ACL task '{task.get('name')}' is missing s3_enable_anonymous_access guard"
            )

    def test_deploy_minio_vars_define_anonymous_access_variable(self) -> None:
        with open(_DEPLOY_MINIO_VARS, "r", encoding="utf-8") as f:
            content = f.read()
        assert "s3_enable_anonymous_access" in content
        assert "CWE-732" in content, "Variable must include CWE-732 security reference"

    def test_anonymous_access_defaults_to_true(self) -> None:
        """Backward compatibility: default must be true."""
        with open(_DEPLOY_MINIO_VARS, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data.get("s3_enable_anonymous_access") is True

    def test_warning_task_exists_when_disabled(self) -> None:
        """Both files must warn operators when anonymous access is off."""
        for path in (_S3_BUCKET_YML, _SET_S3_ACL_YML):
            tasks = _load_tasks(path)
            warn_tasks = [
                t for t in tasks
                if "warn" in str(t.get("name", "")).lower()
                and "anonymous" in str(t.get("name", "")).lower()
            ]
            assert len(warn_tasks) >= 1, (
                f"{path.name} must have a warning task when anonymous access is disabled"
            )
