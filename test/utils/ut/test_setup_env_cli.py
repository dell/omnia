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
"""
Regression tests for OMN-DEF #818.

``test/utils/setup_env.sh`` did not recognize ``--help``/``-h``, ``--venv``,
``--force``, or ``--debug`` — any of those flags hit the script's
``*) log_error "Unknown option" ...`` fallback and exited non-zero. This was
not just a style gap: ``test/pipeline/.gitlab-ci-utils.yml`` already invokes
``bash setup_env.sh --venv``, so the missing flag broke the utils CI pipeline.
These tests invoke the real script (no network/pip calls needed for the
assertions below) to pin the fix in place.
"""

# pylint: disable=missing-function-docstring

import shutil
import subprocess

import pytest


def _run_setup_env(repo_root, *args, timeout=30):
    script_path = repo_root / "test" / "utils" / "setup_env.sh"
    assert script_path.exists(), f"setup_env.sh not found: {script_path}"
    return subprocess.run(
        ["bash", str(script_path), *args],
        cwd=str(script_path.parent),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture(autouse=True)
def _require_bash():
    if shutil.which("bash") is None:
        pytest.skip("bash not available")


def test_help_flag_exits_zero_and_prints_usage(repo_root):
    result = _run_setup_env(repo_root, "--help")
    assert result.returncode == 0
    assert "Usage: ./setup_env.sh" in result.stdout


def test_short_help_flag_is_also_accepted(repo_root):
    result = _run_setup_env(repo_root, "-h")
    assert result.returncode == 0
    assert "Usage: ./setup_env.sh" in result.stdout


def test_help_documents_venv_force_and_debug(repo_root):
    result = _run_setup_env(repo_root, "--help")
    assert "--venv" in result.stdout
    assert "--force" in result.stdout
    assert "--debug" in result.stdout


def test_venv_force_debug_flags_are_accepted_before_help_exit(repo_root):
    # Combine the install-mode flags with --help so parsing exercises every
    # new case branch but the script exits before touching the network/pip.
    result = _run_setup_env(repo_root, "--venv", "--force", "--debug", "--help")
    assert result.returncode == 0
    assert "Unknown option" not in result.stderr
    assert "Unknown option" not in result.stdout


def test_unknown_option_still_fails(repo_root):
    result = _run_setup_env(repo_root, "--totally-bogus-flag")
    assert result.returncode != 0
    assert "Unknown option" in result.stdout or "Unknown option" in result.stderr
