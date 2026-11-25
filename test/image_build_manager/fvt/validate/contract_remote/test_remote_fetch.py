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

"""Image Build Validate — Remote Repo Manager Fetch.

Runs ``repo_manager`` on the external OIM (OIM1), fetches the generated
``repo_status.yml`` and Pulp certificate to a staging directory for the
``contract_build`` stage.
"""

import os
import tempfile

import pytest
import yaml

from library.functions import (
    TestLogger, load_test_config, load_test_credentials,
)
from library.functions.contract_func import verify_external_source
from library.functions.contract_remote_func import (
    external_oim_config,
    run_remote_repo_manager,
    fetch_repo_status,
    verify_remote_oim_ready,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)

# Well-known staging directory shared with the contract_build stage.
_STAGING_DIR = os.path.join(tempfile.gettempdir(), "omnia_contract_test")


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.live_file
@pytest.mark.phase1
def test_remote_repo_manager_fetch(host):
    """Run repo_manager on the external OIM, fetch contract and certificate.

    Staging directory is preserved for the ``contract_build`` stage.
    """
    tc = TC["deploy_external_repo_manager_e2e"]
    tl = TestLogger(tc["title"], tc["id"])

    # --- Load external OIM config ---
    config = load_test_config()
    try:
        oim_cfg = external_oim_config(config)
    except ValueError as exc:
        tl.skipped(str(exc))
        pytest.skip(str(exc))

    creds = load_test_credentials()
    password = creds.get("external_oim_password", "")
    # In SVT mode, password comes from environment variable
    if not password:
        password = os.environ.get("SVT_EXTERNAL_OIM_PASS", "")
    if not password:
        msg = "external_oim_password not set in test_creds.yml or SVT_EXTERNAL_OIM_PASS env var"
        tl.skipped(msg)
        pytest.skip(msg)

    # --- Step 1: Verify external OIM is ready ---
    tl.info(f"Checking external OIM at {oim_cfg['ip']}...")
    ready = verify_remote_oim_ready(oim_cfg, password)
    if not ready["success"]:
        tl.failed(LOG["contract_remote_oim_failed"].format(
            error=ready["error"]), ready["error"])
    assert ready["success"], ASSERT["contract_remote_oim_not_ready"].format(
        error=ready["error"])
    tl.info(LOG["contract_remote_oim_ready"].format(details=ready["details"]))

    # --- Step 2: Run repo_manager on external OIM ---
    tl.info(LOG["contract_remote_repo_manager_started"].format(
        ip=oim_cfg["ip"], tags=oim_cfg["repo_manager_tags"]))

    rm_result = run_remote_repo_manager(
        oim_cfg, password,
        log_callback=lambda line: tl.info(f"  [OIM1] {line}"),
    )
    if rm_result["success"]:
        tl.info(LOG["contract_remote_repo_manager_ok"].format(
            duration=rm_result["duration"]))
    else:
        tl.failed(LOG["contract_remote_repo_manager_failed"].format(
            rc=rm_result["rc"], duration=rm_result["duration"]),
            rm_result.get("error", ""))
    assert rm_result["success"], ASSERT[
        "contract_remote_repo_manager_failed"
    ].format(
        ip=oim_cfg["ip"], tags=oim_cfg["repo_manager_tags"],
        rc=rm_result["rc"], duration=rm_result["duration"],
    )

    # --- Step 3: Fetch repo_status.yml from external OIM ---
    fetch = fetch_repo_status(oim_cfg, password, _STAGING_DIR)
    if fetch["success"]:
        tl.info(LOG["contract_remote_fetch_ok"].format(
            ip=oim_cfg["ip"],
            remote_path=fetch["remote_path"],
            local_path=fetch["path"],
        ))
    else:
        tl.failed(LOG["contract_remote_fetch_failed"].format(
            error=fetch.get("error", "")), fetch.get("error", ""))
    assert fetch["success"], ASSERT["contract_remote_fetch_failed"].format(
        ip=oim_cfg["ip"],
        remote_path=fetch["remote_path"],
        error=fetch.get("error", ""),
    )

    # --- Step 4: Verify the fetched contract is from an external source ---
    with open(fetch["path"], "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    source = verify_external_source(
        data, str(config.get("external_repo_host", "")),
        skip_cert=True,  # local cert is for OIM2, not the external OIM1
    )
    if not source["success"]:
        tl.failed(LOG["contract_external_source_failed"].format(
            details=source["details"]), source["details"])
    assert source["success"], ASSERT["contract_not_external"].format(
        details=source["details"], hosts=source["hosts"])
    tl.info(LOG["contract_external_source_ok"].format(
        details=source["details"]))

    tl.passed(f"Contract fetched and verified at {fetch['path']}")
