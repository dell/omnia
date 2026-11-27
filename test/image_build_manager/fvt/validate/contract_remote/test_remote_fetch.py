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

"""Image Build Validate - remote repo_manager fetch.

Runs ``repo_manager`` on the external OIM (OIM1) and fetches the generated
``repo_status.yml`` and Pulp certificate into the staging directory that the
``contract_build`` stage reads.
"""

import os
import tempfile

import pytest
import yaml

from library.functions import (
    TestLogger, load_test_config,
)
from library.functions.contract_func import verify_external_source
from library.functions.contract_remote_func import (
    external_oim_config,
    external_oim_secret,
    run_remote_repo_manager,
    fetch_repo_status,
    verify_remote_oim_ready,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)

# Staging directory shared with the contract_build stage.
_STAGING_DIR = os.path.join(tempfile.gettempdir(), "omnia_contract_test")


def _require(tl, ok, log_msg, detail, assert_msg):
    """Log a failure and assert ``ok`` with the boxed message."""
    if not ok:
        tl.failed(log_msg, detail)
    assert ok, assert_msg


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.live_file
@pytest.mark.phase1
@pytest.mark.order(0)
def test_remote_repo_manager_fetch(host):
    """Run repo_manager on the external OIM, fetch contract and certificate."""
    tc = TC["deploy_external_repo_manager_e2e"]
    tl = TestLogger(tc["title"], tc["id"])

    config = load_test_config()
    try:
        oim_cfg = external_oim_config(config)
    except ValueError as exc:
        tl.skipped(str(exc))
        pytest.skip(str(exc))
    ip, tags = oim_cfg["ip"], oim_cfg["repo_manager_tags"]

    secret = external_oim_secret()
    if not secret:
        msg = "external_oim_password not set in test_creds.yml or SVT_EXTERNAL_OIM_PASS env var"
        tl.skipped(msg)
        pytest.skip(msg)

    tl.info(f"Checking external OIM at {ip}...")
    ready = verify_remote_oim_ready(oim_cfg, secret)
    _require(tl, ready["success"], LOG["contract_remote_oim_failed"].format(
        error=ready["error"]), ready["error"],
        ASSERT["contract_remote_oim_not_ready"].format(error=ready["error"]))
    tl.info(LOG["contract_remote_oim_ready"].format(details=ready["details"]))

    tl.info(LOG["contract_remote_repo_manager_started"].format(ip=ip, tags=tags))
    run = run_remote_repo_manager(
        oim_cfg, secret, log_callback=lambda line: tl.info(f"  [OIM1] {line}"))
    if run["success"]:
        tl.info(LOG["contract_remote_repo_manager_ok"].format(duration=run["duration"]))
    _require(tl, run["success"], LOG["contract_remote_repo_manager_failed"].format(
        rc=run["rc"], duration=run["duration"]), run.get("error", ""),
        ASSERT["contract_remote_repo_manager_failed"].format(
            ip=ip, tags=tags, rc=run["rc"], duration=run["duration"]))

    fetch = fetch_repo_status(oim_cfg, secret, _STAGING_DIR)
    if fetch["success"]:
        tl.info(LOG["contract_remote_fetch_ok"].format(
            ip=ip, remote_path=fetch["remote_path"], local_path=fetch["path"]))
    error = fetch.get("error", "")
    _require(tl, fetch["success"], LOG["contract_remote_fetch_failed"].format(error=error),
             error, ASSERT["contract_remote_fetch_failed"].format(
                 ip=ip, remote_path=fetch["remote_path"], error=error))

    with open(fetch["path"], "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    # skip_cert: the local certificate is for OIM2, not the external OIM1.
    source = verify_external_source(
        data, str(config.get("external_repo_host", "")), skip_cert=True)
    _require(tl, source["success"], LOG["contract_external_source_failed"].format(
        details=source["details"]), source["details"],
        ASSERT["contract_not_external"].format(
            details=source["details"], hosts=source["hosts"]))
    tl.info(LOG["contract_external_source_ok"].format(details=source["details"]))

    tl.passed(f"Contract fetched and verified at {fetch['path']}")
