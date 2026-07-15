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
Build Image aarch64 — Playbook Deployment Test.

Runs the build_image_aarch64.yml playbook inside omnia_core container using the
playbook_runner. Output is streamed live to the terminal.

This test runs the playbook deployment step. It should run BEFORE
the verification tests.

Usage:
    run_validation build_image_aarch64 deploy       # Run playbook only
    run_validation build_image_aarch64 test         # Run playbook + all verification tests
    run_validation build_image_aarch64 verify       # Run verification tests only (skip deploy)
"""

import pytest

from automation_library.core import TestLogger
from automation_library.core.vars import BUILD_IMAGE_AARCH64_PLAYBOOK, BUILD_IMAGE_AARCH64_WORKDIR
from automation_library.playbook_runner import PlaybookRunner, RUNNER_ASSERT_MSGS


# =============================================================================
# 0. PRE-FLIGHT: CONTAINER CHECK
# =============================================================================

@pytest.mark.deploy
@pytest.mark.order(0)
def test_omnia_core_container_running(host):
    """
    Pre-flight: Verify omnia_core container is running before deployment.

    This must pass before the playbook can be executed.
    """
    log = TestLogger("Pre-flight: omnia_core container check")
    log.check("Checking if omnia_core container is running")

    runner = PlaybookRunner()
    if runner.check_container():
        log.passed("omnia_core container is running")
    else:
        log.failed("omnia_core container is NOT running")
        assert False, RUNNER_ASSERT_MSGS["container_not_running"]


# =============================================================================
# 1. RUN BUILD_IMAGE_AARCH64 PLAYBOOK (LIVE STREAMING)
# =============================================================================

@pytest.mark.deploy
@pytest.mark.order(1)
def test_run_build_image_aarch64_playbook(host):
    """
    Deploy: Run build_image_aarch64.yml playbook with live streaming output.

    Executes the full build_image_aarch64 playbook inside omnia_core container.
    All output is streamed line-by-line to the terminal in real-time,
    providing the same experience as running ansible-playbook directly.

    Equivalent to running the playbook directly:
        podman exec -w /omnia/src/playbooks/build_image_aarch64 omnia_core ansible-playbook build_image_aarch64.yml -v
    """
    log = TestLogger("Deploy: build_image_aarch64.yml")
    log.check(f"Running playbook: {BUILD_IMAGE_AARCH64_PLAYBOOK}")

    runner = PlaybookRunner()
    result = runner.run(BUILD_IMAGE_AARCH64_PLAYBOOK, workdir=BUILD_IMAGE_AARCH64_WORKDIR)

    if result["success"]:
        log.passed(
            f"Playbook completed successfully (rc={result['rc']}, "
            f"duration={result['duration']:.1f}s)"
        )
    else:
        log.failed(
            f"Playbook failed (rc={result['rc']}, "
            f"duration={result['duration']:.1f}s)",
            result["error"],
        )

    assert result["success"], RUNNER_ASSERT_MSGS["playbook_failed"].format(
        playbook=BUILD_IMAGE_AARCH64_PLAYBOOK,
        rc=result["rc"],
        duration=result["duration"],
    )
