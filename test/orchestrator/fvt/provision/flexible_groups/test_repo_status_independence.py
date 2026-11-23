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
Tests for Flexible Functional Group Repository-Status Independence.

Test Cases:
- TC_FVT_add_006: Verify flexible functional group add operation proceeds
  without repo_status.yml.
- TC_FVT_configure_008: Verify flexible functional group configure operation
  proceeds without repo_status.yml.
- TC_FVT_standard_regression_014: Verify standard flows retain blocking repo_status requirement.
"""

# pylint: disable=redefined-outer-name

from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
SETUP_VARS_YML = ORCHESTRATOR_ROOT / "roles" / "orchestrator_setup" / "vars" / "main.yml"
SETUP_TASKS_YML = ORCHESTRATOR_ROOT / "roles" / "orchestrator_setup" / "tasks" / "main.yml"
MANAGE_FG_YML = (
    ORCHESTRATOR_ROOT
    / "playbooks"
    / "functional_groups"
    / "manage_functional_group.yml"
)


def _determine_repo_status_required(run_tags: list[str], required_tags: list[str]) -> bool:
    """Evaluate Jinja2 condition for repo_status requirement."""
    if not run_tags:
        return True
    return bool(set(run_tags) & set(required_tags))


@pytest.fixture(scope="module")
def setup_vars() -> dict:
    """Load orchestrator_setup variables."""
    with open(SETUP_VARS_YML, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def manage_fg_playbook() -> list[dict]:
    """Load manage_functional_group playbook."""
    with open(MANAGE_FG_YML, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.mark.fvt
@pytest.mark.order(40006)
class TestFlexibleGroupAddRepoStatusIndependence:
    """TC_FVT_add_006: Flexible functional group add operation proceeds without repo_status."""

    def test_manage_functional_group_tag_not_in_repo_status_required_tags(self, setup_vars):
        """FR-6.2, AC-008: manage-functional-group is absent from repo_status_required_tags."""
        required_tags = setup_vars.get("repo_status_required_tags", [])
        assert "manage-functional-group" not in required_tags

    def test_repo_status_not_required_for_add_operation(self, setup_vars):
        """FR-6.2, AC-008: Evaluating manage-functional-group determines repo_status unneeded."""
        required_tags = setup_vars.get("repo_status_required_tags", [])
        is_required = _determine_repo_status_required(["manage-functional-group"], required_tags)
        assert is_required is False

    def test_manage_functional_group_playbook_no_repo_status_consumption(self, manage_fg_playbook):
        """FR-6.2, AC-008: manage_functional_group.yml has no repo_status tasks or dependencies."""
        play = manage_fg_playbook[0]
        play_yaml = yaml.dump(play, default_flow_style=False)
        assert "repo_status_stat" not in play_yaml
        assert "include_vars" not in play_yaml or "repo_status" not in play_yaml

    def test_add_operation_defaults(self, manage_fg_playbook):
        """FR-6.2, AC-008: Default operation is 'add' and publishes both boot and cloud_init."""
        play = manage_fg_playbook[0]
        play_vars = play.get("vars", {})
        assert play_vars.get("fg_operation") == "add"
        assert play_vars.get("target_category") == "flexible"


@pytest.mark.fvt
@pytest.mark.order(40008)
class TestFlexibleGroupConfigureRepoStatusIndependence:
    """TC_FVT_configure_008: Flexible group configure operation proceeds without repo_status."""

    def test_repo_status_not_required_for_configure_operation(self, setup_vars):
        """FR-6.2, AC-008: Configure under manage-functional-group does not require repo_status."""
        required_tags = setup_vars.get("repo_status_required_tags", [])
        is_required = _determine_repo_status_required(["manage-functional-group"], required_tags)
        assert is_required is False

    def test_configure_operation_skips_registration(self, manage_fg_playbook):
        """FR-6.2, AC-008: Configure operation sets registration complete to skip."""
        play = manage_fg_playbook[0]
        play_vars = play.get("vars", {})
        assert "provision_common_registration_complete" in play_vars
        registration_gate = play_vars["provision_common_registration_complete"]
        assert "fg_operation == 'configure'" in registration_gate


@pytest.mark.fvt
@pytest.mark.order(40014)
class TestPredefinedFlowsRepoStatusRequirement:
    """TC_FVT_standard_regression_014: Standard flows retain blocking repo_status requirement."""

    @pytest.mark.parametrize(
        "standard_tag",
        [
            "provision",
            "execute",
            "pxeboot",
            "precheck",
            "all",
        ],
    )
    def test_standard_flows_require_repo_status(self, setup_vars, standard_tag):
        """FR-6.2, AC-008: Standard content-consuming tags require repo_status.yml."""
        required_tags = setup_vars.get("repo_status_required_tags", [])
        assert standard_tag in required_tags
        assert _determine_repo_status_required([standard_tag], required_tags) is True

    def test_default_no_tag_flow_requires_repo_status(self, setup_vars):
        """FR-6.2, AC-008: Default full lifecycle run (no tags) requires repo_status.yml."""
        required_tags = setup_vars.get("repo_status_required_tags", [])
        assert _determine_repo_status_required([], required_tags) is True
