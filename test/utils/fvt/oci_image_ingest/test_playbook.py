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
OCI Image Ingest — Playbook Deployment Test.

Validates that utils.yml --tags oci_image_ingest executes the full
OCI image ingest pipeline:
  setup, validation, credentials, registry validation,
  operation execution, status generation, cleanup.
"""

import pytest

from library.functions import (
    TestLogger,
    resolve_target_source_root,
    run_playbook,
)
from library.functions.oci_image_ingest_func import (
    check_oci_config_exists,
    validate_oci_config_structure,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
    PLAYBOOK_WORKDIR,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.oci_image_ingest
@pytest.mark.order(100)
def test_deploy_oci_image_ingest(host):
    """Deploy utils.yml with oci_image_ingest tag."""
    tc = TC["deploy_oci_image_ingest"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-check: OCI config must exist with registries configured
    config_check = check_oci_config_exists(host)
    if not config_check["success"]:
        tl.skipped("OCI config not populated — cannot deploy")
        pytest.skip("OCI image ingest config file not found or empty")

    config_result = validate_oci_config_structure(host)
    if not config_result["success"]:
        tl.skipped(f"OCI config not ready for deploy: {config_result['error']}")
        pytest.skip(f"OCI config incomplete: {config_result['error']}")

    oci_cfg = config_result.get("config", {})
    if not oci_cfg.get("registries") or not oci_cfg.get("image_mappings"):
        tl.skipped("OCI config has no registries/mappings configured")
        pytest.skip("OCI config has empty registries or image_mappings")

    tl.check("Running utils.yml --tags oci_image_ingest")
    result = run_playbook(
        playbook=PLAYBOOK_UTILS,
        tag="oci_image_ingest",
        timeout=3600,
    )

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"]
            ),
            result.get("error", "See playbook output above"),
        )

    source_root = resolve_target_source_root()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_UTILS,
        tag="oci_image_ingest",
        rc=result["rc"],
        duration=result["duration"],
        input_path=source_root + "/src/utils/input",
        workdir=source_root + "/" + PLAYBOOK_WORKDIR,
    )
