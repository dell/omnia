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

"""Unit tests of the dependency-free external GitLab helpers (run in the GitHub unit job)."""

from datetime import date

import pytest

from library import gitlab_external_helpers as helpers

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("version,major", [("17.4.1-ee", 17), ("19.0", 19), ("x", None)])
def test_major_version(version, major):
    """The major GitLab version is parsed."""
    assert helpers.gitlab_major_version(version) == major


def test_days_until():
    """Token expiry is counted in whole days."""
    assert helpers.days_until("2026-12-24", date(2026, 11, 24)) == 30
    assert helpers.days_until("", date(2026, 11, 24)) is None
    assert helpers.days_until("garbage") is None


@pytest.mark.parametrize("value,safe", [("644", True), ("600", True), ("444", True),
                                        ("664", False), ("755", False), ("x", False)])
def test_ca_mode(value, safe):
    """The CA bundle must be 0644 or stricter without execute bits."""
    assert helpers.mode_is_ca_safe(value) is safe
