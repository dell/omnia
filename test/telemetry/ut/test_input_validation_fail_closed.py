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

"""Negative tests: Telemetry validate_input must fail closed on bad tags.

The module runs through the ansible CLI from the collection root so it and
its module_utils resolve exactly as in production.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TELEMETRY_ROOT = Path(__file__).resolve().parents[3] / "src" / "telemetry"
MODULE_UTILS = TELEMETRY_ROOT / "plugins" / "module_utils"
RESULT_PATTERN = re.compile(r"\|\s*(\w+)!?\s*=>\s*(\{.*\})\s*$", re.DOTALL)

pytestmark = pytest.mark.skipif(
    shutil.which("ansible") is None, reason="ansible CLI not installed"
)


@pytest.fixture(name="input_base")
def fixture_input_base(tmp_path):
    """Create a project directory containing one telemetry input file."""
    project = tmp_path / "input" / "project_default"
    project.mkdir(parents=True)
    (project / "telemetry_config.yml").write_text("a: 1\n", encoding="utf-8")
    return tmp_path


def _run_validate_input(base, tags):
    """Run telemetry validate_input and return (failed, result)."""
    args = {
        "omnia_base_dir": str(base / "input"),
        "project_name": "project_default",
        "module_utils_path": str(MODULE_UTILS),
        "tag_names": tags,
    }
    env = dict(os.environ, OMNIA_DATA_PATH=str(base), ANSIBLE_LOG_PATH=os.devnull)
    proc = subprocess.run(
        ["ansible", "localhost", "-m", "validate_input", "-a", json.dumps(args)],
        cwd=TELEMETRY_ROOT, env=env, capture_output=True, text=True,
        check=False, timeout=120,
    )
    match = RESULT_PATTERN.search(proc.stdout)
    assert match, f"No module result in output:\n{proc.stdout}\n{proc.stderr}"
    return match.group(1) == "FAILED", json.loads(match.group(2))


def test_unknown_tag_alone_is_rejected(input_base):
    """A typo tag must fail instead of validating zero files."""
    failed, result = _run_validate_input(input_base, ["iucghewqiug"])
    assert failed
    assert "Unknown or missing tag(s): ['iucghewqiug']" in result["msg"]


def test_known_tag_with_unknown_tag_is_rejected(input_base):
    """A typo mixed with the valid telemetry tag must still fail."""
    failed, result = _run_validate_input(input_base, ["telemetry", "iucghewqiug"])
    assert failed
    assert "Unknown or missing tag(s): ['iucghewqiug']" in result["msg"]


def test_empty_tag_list_is_rejected(input_base):
    """An empty tag list validates nothing and must not report success."""
    failed, result = _run_validate_input(input_base, [])
    assert failed
    assert "Unknown or missing tag(s): []" in result["msg"]


def test_valid_tag_reaches_file_validation(input_base):
    """The telemetry tag passes the tag gate and validates its inventory."""
    failed, result = _run_validate_input(input_base, ["telemetry"])
    assert failed
    assert "telemetry_storage_config file not found" in result["msg"]
