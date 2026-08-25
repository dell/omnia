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
Omnia Main Execution — Deploy + Cleanup.

Three-phase test flow managed by ``run_validation.sh test``:

  Phase 1 — Deploy (@deploy marker):
    1. omnia.sh --setup-venv --deps-only  (skip if inside omnia venv)
    2. omnia.sh --init image_build_manager
    3. omnia.sh --run image_build_manager --tags precheck
    4. omnia.sh --run image_build_manager --tags validate

  Phase 2 — Verify (no marker, in setup_exec/):
    Read-only checks that venv, env files, log dirs, input files exist.

  Phase 3 — Cleanup (@cleanup marker, runs AFTER verify):
    5. omnia.sh --cleanup  (skip if inside omnia venv)

Intelligent skip logic:
  - Setup and cleanup modify the omnia production venv at OMNIA_VENV_PATH.
  - If the test runner is activated FROM that same venv (e.g. the user ran
    ``source /opt/omnia/venv/bin/activate``), destroying it would hang
    the running process.
  - Tests detect this via ``is_running_from_omnia_venv()`` and skip
    destructive operations with a clear message.
  - When tests run from the test harness venv (``test/main/.venv``),
    setup and cleanup execute normally.

TC_EX_001: Deploy omnia.sh --setup-venv --deps-only
TC_EX_002: Deploy omnia.sh --init image_build_manager
TC_EX_003: Deploy omnia.sh --run image_build_manager --tags precheck
TC_EX_004: Deploy omnia.sh --run image_build_manager --tags validate
TC_EX_005: Cleanup omnia.sh --cleanup (intelligent skip, runs after verify)
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import (
    is_running_from_omnia_venv,
    run_omnia_cmd,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)

DOMAIN = "image_build_manager"

_SKIP_VENV_MSG = (
    "Skipped: running from omnia production venv — "
    "cannot destroy the active interpreter"
)


# =========================================================================
# TC_EX_001: Full setup
# =========================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_setup_deps_only(host):
    """TC_EX_001: Deploy omnia.sh --setup-venv --deps-only."""
    tl = TestLogger(
        TEST_NAMES["exec_setup_full"], "TC_EX_001"
    )

    if is_running_from_omnia_venv():
        tl.passed(_SKIP_VENV_MSG)
        pytest.skip(_SKIP_VENV_MSG)

    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    # If venv already exists, skip deploy
    venv_check = host.run(
        f"test -d {venv_path}/bin && echo exists"
    )
    if "exists" in venv_check.stdout:
        tl.passed(LOG["exec_setup_ok"].format(
            rc=0, duration=0.0
        ))
        pytest.skip(
            f"Venv already exists at {venv_path} — skipping deploy"
        )

    result = run_omnia_cmd(host, "omnia_sh_setup_venv")

    if result["success"]:
        tl.passed(LOG["exec_setup_ok"].format(
            rc=result["rc"], duration=result["duration"]
        ))
    else:
        tl.failed(
            LOG["exec_setup_failed"].format(
                rc=result["rc"],
                duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_setup_failed"].format(
        rc=result["rc"],
    )


# =========================================================================
# TC_EX_002: Domain init
# =========================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(1)
def test_deploy_init_domain(host):
    """TC_EX_002: Deploy omnia.sh --init image_build_manager."""
    tl = TestLogger(
        TEST_NAMES["exec_init_domain"], "TC_EX_002"
    )

    result = run_omnia_cmd(
        host, "omnia_sh_init_domain",
        domain=DOMAIN,
    )

    if result["success"]:
        tl.passed(LOG["exec_init_domain_ok"].format(
            domain=DOMAIN,
            rc=result["rc"],
            duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["exec_init_domain_failed"].format(
                domain=DOMAIN,
                rc=result["rc"],
                duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_init_domain_failed"].format(
        domain=DOMAIN,
        rc=result["rc"],
    )


# =========================================================================
# TC_EX_003: Run --tags precheck
# =========================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(2)
def test_deploy_run_precheck(host):
    """TC_EX_003: Deploy --run image_build_manager --tags precheck."""
    tl = TestLogger(
        TEST_NAMES["exec_run_precheck"], "TC_EX_003"
    )

    result = run_omnia_cmd(
        host, "omnia_sh_run_domain_tag",
        domain=DOMAIN, tag="precheck",
    )

    if result["success"]:
        tl.passed(LOG["exec_run_ok"].format(
            domain=DOMAIN, tag="precheck",
            rc=result["rc"], duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["exec_run_failed"].format(
                domain=DOMAIN, tag="precheck",
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_run_failed"].format(
        domain=DOMAIN, tag="precheck", rc=result["rc"],
    )


# =========================================================================
# TC_EX_004: Run --tags validate
# =========================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(3)
def test_deploy_run_validate(host):
    """TC_EX_004: Deploy --run image_build_manager --tags validate."""
    tl = TestLogger(
        TEST_NAMES["exec_run_validate"], "TC_EX_004"
    )

    result = run_omnia_cmd(
        host, "omnia_sh_run_domain_tag",
        domain=DOMAIN, tag="validate",
    )

    if result["success"]:
        tl.passed(LOG["exec_run_ok"].format(
            domain=DOMAIN, tag="validate",
            rc=result["rc"], duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["exec_run_failed"].format(
                domain=DOMAIN, tag="validate",
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_run_failed"].format(
        domain=DOMAIN, tag="validate", rc=result["rc"],
    )


# =========================================================================
# TC_EX_005: Cleanup (intelligent skip)
# =========================================================================

@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(100)
def test_deploy_cleanup(host):
    """TC_EX_005: Deploy omnia.sh --cleanup (skip if inside omnia venv)."""
    tl = TestLogger(
        TEST_NAMES["exec_cleanup"], "TC_EX_005"
    )

    if is_running_from_omnia_venv():
        tl.passed(_SKIP_VENV_MSG)
        pytest.skip(_SKIP_VENV_MSG)

    result = run_omnia_cmd(host, "omnia_sh_cleanup_yes")

    if result["success"]:
        tl.passed(LOG["exec_cleanup_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            LOG["exec_cleanup_failed"].format(
                rc=result["rc"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_cleanup_failed"].format(
        rc=result["rc"],
    )
