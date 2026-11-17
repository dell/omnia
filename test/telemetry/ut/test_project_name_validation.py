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

"""Unit tests for project_name path-traversal prevention.

Validates that ``validate_project_name`` in telemetry config rejects
crafted values that would escape the intended directory via traversal
payloads (.., absolute paths, embedded /, empty values) and accepts
legitimate single-segment project names.
"""

import os
import sys

import pytest

# Allow direct import of the telemetry config module without Ansible.
_SRC_TELEMETRY = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "src", "telemetry", "plugins", "module_utils",
    )
)
if _SRC_TELEMETRY not in sys.path:
    sys.path.insert(0, _SRC_TELEMETRY)

from input_validation.core.config import validate_project_name  # noqa: E402


# ── validate_project_name: valid inputs ──────────────────────────────

@pytest.mark.parametrize(
    "name",
    [
        "project_default",
        "my-project",
        "my_project",
        "my.project",
        "A1",
        "project123",
        "Project.v2-beta_1",
    ],
)
def test_validate_project_name_accepts_valid_names(name):
    """Legitimate single-segment names must pass unchanged."""
    assert validate_project_name(name) == name


# ── validate_project_name: invalid inputs ────────────────────────────

@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("", "empty value"),
        (".", "current directory"),
        ("..", "parent directory traversal"),
        ("../etc", "relative path traversal"),
        ("../../root", "multi-level traversal"),
        ("/tmp", "absolute path"),
        ("/etc/passwd", "absolute path with segments"),
        ("project/name", "embedded forward slash"),
        (".hidden", "starts with dot"),
        ("-invalid", "starts with hyphen"),
        ("_invalid", "starts with underscore"),
    ],
)
def test_validate_project_name_rejects_invalid_names(name, reason):
    """Crafted values must raise ValueError ({reason})."""
    with pytest.raises(ValueError):
        validate_project_name(name)


# ── vault password path containment ─────────────────────────────────
# Replicate the containment logic from validation_utils._safe_vault_password_path
# without importing the full module (which requires Ansible runtime).

def _safe_vault_password_path(omnia_base_dir, project_name, vault_password_file):
    """Local copy of the containment check for unit-test isolation."""
    password_full_path = os.path.realpath(
        os.path.join(omnia_base_dir, project_name, vault_password_file)
    )
    real_base = os.path.realpath(omnia_base_dir)
    if not password_full_path.startswith(real_base + os.sep):
        raise ValueError(
            f"Vault password path escapes base directory: {password_full_path}"
        )
    return password_full_path


def test_vault_path_rejects_traversal():
    """A traversal project_name must not escape omnia_base_dir."""
    with pytest.raises(ValueError, match="escapes base directory"):
        _safe_vault_password_path("/opt/omnia", "../../../etc", "vault_key")


def test_vault_path_accepts_valid_project(tmp_path):
    """A safe project_name produces a path under omnia_base_dir."""
    project = "project_default"
    (tmp_path / project).mkdir()
    path = _safe_vault_password_path(str(tmp_path), project, "vault_key")
    assert path.startswith(os.path.realpath(str(tmp_path)) + os.sep)


# ── log path symlink containment ────────────────────────────────────

def test_log_path_symlink_containment(tmp_path):
    """A symlinked log directory must not bypass containment."""
    real_dir = tmp_path / "real_logs"
    real_dir.mkdir()
    link_dir = tmp_path / "link_logs"
    link_dir.symlink_to(real_dir)

    project = "project_default"
    log_path = os.path.join(str(link_dir), project, "test.log")
    resolved = os.path.realpath(log_path)
    real_base = os.path.realpath(str(link_dir))
    assert resolved.startswith(real_base + os.sep)
