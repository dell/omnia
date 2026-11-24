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
Image Build Validate — External repo_manager Contract Deploy.

Stages an externally-sourced repo_status.yml (the live repo_manager output
enriched with producer metadata) and runs the image_build_manager playbook
with ``--tags build``.  The build tag is the real flow that naturally sets
``needs_repo_status=true`` and exercises the full contract pipeline:

  1. JSON Schema validation (validate_repo_status_contract module)
  2. Semantic validation (repo_status_validator)
  3. parse_repo_status — sets Ansible facts consumed by later tags
  4. Certificate path validation
  5. Repository URL reachability check
  6. Full image build execution with the external repo_status
"""

import os
import shutil
import tempfile

import pytest
import yaml

from library.functions import TestLogger, run_playbook, load_test_config
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    BUILD_LOG_PATH,
    SHARED_PATH,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)

# Default repo_status.yml location on the OIM
_DEFAULT_REPO_STATUS = os.path.join(
    os.environ.get("OMNIA_DATA_PATH", "/opt/omnia"),
    "repo_manager", "output",
    os.environ.get("OMNIA_PROJECT_NAME", "project_default"),
    "repo_status.yml",
)

# Temp staging directory (outside OMNIA_DATA_PATH to prove external sourcing)
_STAGING_DIR = os.path.join(tempfile.gettempdir(), "omnia_contract_test")


def _load_live_status():
    """Read the production repo_status.yml from the OIM.

    Returns:
        Tuple of (data dict, source path) or (None, path) if not found.
    """
    path = _DEFAULT_REPO_STATUS
    config = load_test_config()
    custom = config.get("repo_manager_output_path", "")
    if custom:
        path = custom

    if not os.path.isfile(path):
        return None, path

    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh), path


def _stage_external_status(data):
    """Write a repo_status.yml to the staging directory.

    Args:
        data: The (possibly enriched) repo_status dict.

    Returns:
        Absolute path to the staged file.
    """
    os.makedirs(_STAGING_DIR, exist_ok=True)
    staged = os.path.join(_STAGING_DIR, "repo_status.yml")
    with open(staged, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False)
    return staged


def _cleanup_staging():
    """Remove the staging directory."""
    if os.path.isdir(_STAGING_DIR):
        shutil.rmtree(_STAGING_DIR, ignore_errors=True)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_external_contract(host):
    """Deploy image_build_manager --tags build with external repo_status.

    Reads the live repo_manager output, adds producer metadata fields
    that the consumer must accept and ignore, writes it to an external
    staging path, then runs the playbook with --tags build pointing at
    that path.  The build tag is the real flow that naturally loads
    repo_status.yml through the contract validation pipeline.
    """
    tc = TC["deploy_external_contract"]
    tl = TestLogger(tc["title"], tc["id"])

    # --- Load the live status ---
    data, source_path = _load_live_status()
    if data is None:
        msg = f"Live repo_status.yml not found at {source_path}"
        tl.skipped(msg)
        pytest.skip(msg)

    # --- Enrich with external producer metadata ---
    data["custom_external_metadata"] = {
        "source": "contract-fvt",
        "producer_version": "external-1.0",
        "build_id": 99999,
    }
    data.setdefault("execution_contexts", [])
    if not data["execution_contexts"]:
        data["execution_contexts"] = [
            {"context_id": "external", "os_type": data.get("cluster_os_type", "rhel"),
             "os_version": "10.0", "architectures": ["x86_64"]},
        ]

    # --- Stage to external path ---
    staged_path = _stage_external_status(data)
    tl.info(f"Staged external repo_status at {staged_path}")

    try:
        # --- Run playbook with external repo_status (real build flow) ---
        result = run_playbook(
            playbook=PLAYBOOK_ENTRY_POINT,
            tag="build",
            extra_vars={
                "repo_manager_output_path": staged_path,
            },
        )

        if result["success"]:
            tl.passed(
                LOG["contract_deploy_ok"].format(
                    duration=result["duration"],
                    path=staged_path,
                ),
            )
        else:
            tl.failed(
                LOG["contract_deploy_failed"].format(
                    rc=result["rc"],
                    duration=result["duration"],
                ),
                result.get("error", "See playbook output above"),
            )

        config = load_test_config()
        assert result["success"], ASSERT["contract_deploy_failed"].format(
            playbook=PLAYBOOK_ENTRY_POINT,
            rc=result["rc"],
            duration=result["duration"],
            path=staged_path,
            log_path=BUILD_LOG_PATH.format(
                shared_path=SHARED_PATH,
                project=config.get("project_name", "project_default"),
            ),
        )
    finally:
        _cleanup_staging()
