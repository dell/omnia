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

import pytest

from library.cleanup_inspection import (
    INSPECTION_ERROR,
    PATH_ABSENT,
    PATH_EXISTS,
    classify_path_probe,
    is_expected_disabled_state,
    is_expected_stopped_state,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("return_code", "output", "expected"),
    [
        (0, "exists\n", PATH_EXISTS),
        (1, "", PATH_ABSENT),
        (127, "", INSPECTION_ERROR),
        (255, "", INSPECTION_ERROR),
        (0, "", INSPECTION_ERROR),
        (1, "exists", INSPECTION_ERROR),
    ],
)
def test_classify_path_probe(return_code, output, expected):
    """Only exact shell-test presence and absence results are accepted."""
    assert classify_path_probe(return_code, output) == expected


@pytest.mark.parametrize(
    ("return_code", "status"),
    [(3, "inactive"), (3, "failed"), (4, "unknown"), (4, "not-found")],
)
def test_expected_stopped_states(return_code, status):
    """Known systemctl inactive/not-found states confirm shutdown."""
    assert is_expected_stopped_state(return_code, status)


@pytest.mark.parametrize(
    ("return_code", "status"),
    [(127, "unknown"), (255, "unknown"), (0, "inactive"), (3, "")],
)
def test_stopped_state_rejects_inspection_failures(return_code, status):
    """Command and transport failures must not be reported as shutdown."""
    assert not is_expected_stopped_state(return_code, status)


@pytest.mark.parametrize(
    ("return_code", "status"),
    [(1, "disabled"), (1, "not-found")],
)
def test_expected_disabled_states(return_code, status):
    """Known systemctl disabled/not-found states confirm disablement."""
    assert is_expected_disabled_state(return_code, status)


@pytest.mark.parametrize(
    ("return_code", "status"),
    [(127, "unknown"), (255, "unknown"), (0, "disabled"), (1, "")],
)
def test_disabled_state_rejects_inspection_failures(return_code, status):
    """Command and transport failures must not be reported as disablement."""
    assert not is_expected_disabled_state(return_code, status)
