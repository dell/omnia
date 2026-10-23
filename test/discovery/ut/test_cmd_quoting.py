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

"""Tests that shell command templates quote substituted values (CWE-78)."""

import importlib.util
import pathlib
import shlex
import subprocess

import pytest

_COMMON_VARS = (
    pathlib.Path(__file__).resolve().parents[1]
    / "library" / "vars" / "common_vars.py"
)
_spec = importlib.util.spec_from_file_location("discovery_common_vars", _COMMON_VARS)
common_vars = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(common_vars)
build_cmd = common_vars.build_cmd

PAYLOAD = "x; touch {marker}; #"


def test_plain_values_are_unchanged():
    """Ordinary paths are not altered by quoting."""
    assert build_cmd("file_exists", path="/opt/omnia/a.yml") == (
        "test -f /opt/omnia/a.yml && echo exists"
    )


def test_glob_pattern_is_quoted_for_find():
    """Wildcard patterns must reach find unexpanded by the shell."""
    cmd = build_cmd("find_csv", path="/out", pattern="bmc_*.csv")
    assert shlex.split(cmd.split("2>")[0]) == [
        "find", "/out", "-name", "bmc_*.csv", "-type", "f",
    ]


@pytest.mark.parametrize("name,key", [
    ("file_exists", "path"),
    ("dir_exists", "path"),
    ("cat_file", "path"),
    ("ls_files", "path"),
    ("readlink", "path"),
    ("csv_header", "path"),
    ("csv_line_count", "path"),
    ("find_csv", "path"),
    ("find_csv", "pattern"),
])
def test_shell_metacharacters_do_not_execute(tmp_path, name, key):
    """A malicious value must be treated as data, never executed."""
    marker = tmp_path / "pwned"
    values = {"path": str(tmp_path), "pattern": "*.csv"}
    values[key] = PAYLOAD.format(marker=marker)
    subprocess.run(build_cmd(name, **values), shell=True, check=False,
                   capture_output=True)
    assert not marker.exists()


def test_yaml_parse_quotes_path(tmp_path):
    """The yaml_parse template must keep the path out of the python source."""
    marker = tmp_path / "pwned"
    evil = f"a'); open('{marker}','w'); ('"
    subprocess.run(build_cmd("yaml_parse", path=evil), shell=True,
                   check=False, capture_output=True)
    assert not marker.exists()
