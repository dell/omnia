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
Orchestrator Precheck — Connectivity and Environment Verification.

Validates target host environment is ready for orchestrator deployment:
- Target host SSH connectivity
- Required directories exist
- Orchestrator input directory structure
"""

import pytest

from library.functions import TestLogger


@pytest.mark.sanity
@pytest.mark.order(1)
def test_target_connectivity(host):
    """ORCH_FVT_PRECHECK_V001: Verify target host is reachable via SSH."""
    tc = {"title": "Target SSH Connectivity", "id": "ORCH_FVT_PRECHECK_V001"}
    tl = TestLogger(tc["title"], tc["id"])

    # Check if host is reachable
    host.run("echo 'SSH connectivity OK'")
    tl.passed("SSH connectivity verified", "Target host is reachable via SSH")


@pytest.mark.sanity
@pytest.mark.order(2)
def test_orchestrator_directories_exist(host):
    """ORCH_FVT_PRECHECK_V002: Verify required Orchestrator directories exist."""
    tc = {"title": "Orchestrator Directories", "id": "ORCH_FVT_PRECHECK_V002"}
    tl = TestLogger(tc["title"], tc["id"])

    required_dirs = [
        "/opt/omnia",
        "/opt/omnia/orchestrator",
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        result = host.run(f"test -d {dir_path} && echo 'EXISTS' || echo 'MISSING'")
        if "MISSING" in result.stdout:
            missing_dirs.append(dir_path)

    if not missing_dirs:
        tl.passed("All required directories exist", f"Found {len(required_dirs)} directories")
    else:
        tl.failed(f"Missing {len(missing_dirs)} directories", f"Missing: {', '.join(missing_dirs)}")
        assert False, f"Missing directories: {', '.join(missing_dirs)}"


@pytest.mark.sanity
@pytest.mark.order(3)
def test_input_directory_structure(host):
    """ORCH_FVT_PRECHECK_V003: Verify the project input directory exists."""
    tc = {"title": "Input Directory Structure", "id": "ORCH_FVT_PRECHECK_V003"}
    tl = TestLogger(tc["title"], tc["id"])

    # Check if input directory exists for the project
    project = "project_default"
    input_path = f"/opt/omnia/orchestrator/input/{project}"

    result = host.run(f"test -d {input_path} && echo 'EXISTS' || echo 'MISSING'")
    if "EXISTS" in result.stdout:
        tl.passed("Input directory structure exists", f"Found input directory at {input_path}")
    else:
        tl.failed("Input directory structure missing", f"Input directory not found at {input_path}")
        assert False, f"Input directory not found: {input_path}"
