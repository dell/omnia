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

"""Regression tests for cleanup inspection-command handling."""

from types import SimpleNamespace

import pytest

from library.functions import cleanup_func


def _command_result(return_code, stdout="", stderr=""):
    """Return the minimal command-result interface used by cleanup helpers."""
    return SimpleNamespace(rc=return_code, stdout=stdout, stderr=stderr)


@pytest.mark.parametrize(
    "check_function",
    [
        cleanup_func.check_playbook_watcher_service_stopped,
        cleanup_func.check_playbook_watcher_service_disabled,
        cleanup_func.check_playbook_watcher_service_file_removed,
    ],
)
def test_watcher_cleanup_checks_fail_when_inspection_command_fails(
    monkeypatch, check_function
):
    """A missing inspection command must never be reported as cleanup."""
    monkeypatch.setattr(
        cleanup_func,
        "run_on_host",
        lambda *_args, **_kwargs: _command_result(
            127, stderr="command not found"
        ),
    )

    result = check_function(object())

    assert result["success"] is False
    assert "rc=127" in result["error"]


@pytest.mark.parametrize(
    ("check_function", "command_result", "expected_status"),
    [
        (
            cleanup_func.check_playbook_watcher_service_stopped,
            _command_result(3, "inactive\n"),
            "inactive",
        ),
        (
            cleanup_func.check_playbook_watcher_service_disabled,
            _command_result(1, "not-found\n"),
            "not-found",
        ),
    ],
)
def test_watcher_cleanup_checks_accept_expected_absence_states(
    monkeypatch, check_function, command_result, expected_status
):
    """Known systemctl inactive/not-found states confirm cleanup."""
    monkeypatch.setattr(
        cleanup_func,
        "run_on_host",
        lambda *_args, **_kwargs: command_result,
    )

    result = check_function(object())

    assert result["success"] is True
    assert result["status"] == expected_status


def test_watcher_service_file_check_accepts_test_absence(monkeypatch):
    """Shell test rc=1 with no output means the unit file is absent."""
    monkeypatch.setattr(
        cleanup_func,
        "run_on_host",
        lambda *_args, **_kwargs: _command_result(1),
    )

    result = cleanup_func.check_playbook_watcher_service_file_removed(object())

    assert result["success"] is True


def test_directory_cleanup_check_fails_on_inspection_errors(monkeypatch):
    """Directory probes that do not return test rc 0/1 must fail."""
    monkeypatch.setattr(
        cleanup_func,
        "resolve_build_stream_data_path",
        lambda _host: "/opt/omnia/build_stream",
    )
    monkeypatch.setattr(
        cleanup_func,
        "run_on_host",
        lambda *_args, **_kwargs: _command_result(
            127, stderr="command not found"
        ),
    )

    result = cleanup_func.check_buildstream_directories_removed(object())

    assert result["success"] is False
    assert not result["removed"]
    assert len(result["inspection_errors"]) == 11
    assert "rc=127" in result["error"]


def test_directory_cleanup_check_accepts_test_absence(monkeypatch):
    """Shell test rc=1 with no output means each directory is absent."""
    monkeypatch.setattr(
        cleanup_func,
        "resolve_build_stream_data_path",
        lambda _host: "/opt/omnia/build_stream",
    )
    monkeypatch.setattr(
        cleanup_func,
        "run_on_host",
        lambda *_args, **_kwargs: _command_result(1),
    )

    result = cleanup_func.check_buildstream_directories_removed(object())

    assert result["success"] is True
    assert len(result["removed"]) == 11
    assert not result["inspection_errors"]
