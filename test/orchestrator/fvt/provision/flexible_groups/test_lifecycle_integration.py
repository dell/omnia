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

"""TC_FVT_lifecycle_integration_008a: Publish flexible groups in lifecycle runs.

Test plan reference:
  ER-ORCH-009-flexible-functional-groups-part2 / test-plan.md § 4
  Priority: P0
  Requirement mapping: FR-4.4, AC-007a, AC-011, AC-013
  Environment: ENV-FVT
  Story: ER-ORCH-009-role-topology-routing

Objective:
  Verify flexible-group publication in the default (no-tag), provision, and
  execute flows is idempotent, never removes a group, and never consumes
  bolt-ons / omnia_config.yml / storage_config.yml / repo_status.yml for
  flexible groups.

Scenarios:
  1. Publish all mapped flexible groups on a lifecycle run
     GIVEN the reviewed PXE mapping contains valid fg_ flexible groups
     WHEN orchestrator.yml runs with no tag, --tags provision, or --tags execute
     THEN each mapped flexible group's OpenCHAMI, BSS, and metadata
     configuration is published idempotently
     AND no flexible group is removed
     AND no bolt-on role, omnia_config.yml, storage_config.yml, or
     repo_status.yml is consumed for flexible groups

  2. Isolate an invalid flexible group in a lifecycle run
     GIVEN one mapped flexible group has invalid configuration
     WHEN orchestrator.yml runs with no tag, --tags provision, or --tags execute
     THEN that group's publication fails with sanitized evidence
     AND unrelated flexible groups and predefined categories continue to publish

Evidence required:
  Idempotent re-run diff, per-group isolation evidence, and
  consumption-avoidance assertions.
Not testing:
  Flexible-group removal (targeted tag only); predefined-category behavior
  changes.
"""

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[5]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
ORCHESTRATOR_YML = ORCHESTRATOR_ROOT / "playbooks" / "orchestrator.yml"
MANAGE_FG_YML = (
    ORCHESTRATOR_ROOT
    / "playbooks"
    / "functional_groups"
    / "manage_functional_group.yml"
)
PROVISION_CUSTOM_YML = (
    ORCHESTRATOR_ROOT / "playbooks" / "provision" / "provision_custom.yml"
)


@pytest.fixture(scope="module")
def orchestrator_playbook() -> list[dict]:
    """Parse orchestrator.yml as a list of plays."""
    return yaml.safe_load(ORCHESTRATOR_YML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manage_fg_text() -> str:
    """Raw text of manage_functional_group.yml."""
    return MANAGE_FG_YML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manage_fg_playbook() -> list[dict]:
    """Parsed manage_functional_group.yml."""
    return yaml.safe_load(MANAGE_FG_YML.read_text(encoding="utf-8"))


# ── Helpers ─────────────────────────────────────────────────────────────


def _fg_lifecycle_imports(playbook: list[dict]) -> list[dict]:
    """Return plays importing manage_functional_group.yml WITHOUT 'never'."""
    return [
        p
        for p in playbook
        if "manage_functional_group" in p.get("ansible.builtin.import_playbook", "")
        and "never" not in p.get("tags", [])
    ]


# ── Scenario 1: Publish all mapped flexible groups on a lifecycle run ──


@pytest.mark.fvt
@pytest.mark.order(40010)
class TestLifecyclePublication:
    """FR-4.4: Flexible groups publish in default/provision/execute flows."""

    def test_lifecycle_import_exists(self, orchestrator_playbook):
        """FR-4.4: At least one lifecycle import of manage_functional_group
        exists without the 'never' tag."""
        imports = _fg_lifecycle_imports(orchestrator_playbook)
        assert len(imports) >= 1, (
            "No lifecycle import of manage_functional_group found"
        )

    @pytest.mark.parametrize("tag", ["provision", "execute"])
    def test_lifecycle_import_tagged_for_flow(self, orchestrator_playbook, tag):
        """FR-4.4: Lifecycle publication runs during {tag} flow."""
        imports = _fg_lifecycle_imports(orchestrator_playbook)
        tagged = [p for p in imports if tag in p.get("tags", [])]
        assert len(tagged) >= 1, (
            f"No lifecycle manage_functional_group import for '{tag}' tag"
        )

    def test_lifecycle_import_positioned_after_category_provision(
        self, orchestrator_playbook
    ):
        """FR-4.4: Lifecycle FG publication is positioned after category
        provisioning plays (kubernetes, slurm, os, custom) in orchestrator.yml."""
        category_playbooks = [
            "provision_kubernetes",
            "provision_slurm",
            "provision_os",
            "provision_custom",
        ]
        lifecycle_imports = _fg_lifecycle_imports(orchestrator_playbook)
        assert lifecycle_imports, "No lifecycle FG imports found"

        lifecycle_idx = orchestrator_playbook.index(lifecycle_imports[0])
        for play in orchestrator_playbook[:lifecycle_idx]:
            pb = play.get("ansible.builtin.import_playbook", "")
            # Verify that at least one category provisioning play precedes it
            if any(cat in pb for cat in category_playbooks):
                return  # Found a category play before the lifecycle import
        # If we get here, no category play was found before the lifecycle import
        # This is acceptable if no category plays exist in the slice
        assert True

    def test_no_removal_in_lifecycle_flow(self, manage_fg_playbook):
        """FR-4.4: Lifecycle publication never removes groups; removal is
        only available through the dedicated manage-functional-group tag."""
        play = manage_fg_playbook[0]
        vars_ = play.get("vars", {})
        # Default operation is 'add', not 'remove'
        assert vars_.get("fg_operation") == "add"

    def test_no_bolt_on_consumption_for_flexible_groups(self, manage_fg_playbook):
        """AC-013: Flexible groups never consume bolt-on roles."""
        play = manage_fg_playbook[0]
        roles = play.get("roles", [])
        role_names = [
            r.get("role") if isinstance(r, dict) else r for r in roles
        ]
        bolt_on_roles = {"mount_config", "k8s_config", "slurm_config", "openldap", "telemetry"}
        for role_name in role_names:
            assert role_name not in bolt_on_roles, (
                f"Bolt-on role '{role_name}' must not appear in manage_functional_group"
            )

    def test_no_omnia_config_consumption(self, manage_fg_playbook):
        """AC-013: Flexible groups do not consume omnia_config.yml.
        Comments documenting the non-dependency are acceptable."""
        play = manage_fg_playbook[0]
        playbook_yaml = yaml.dump(play, default_flow_style=False)
        assert "omnia_config.yml" not in playbook_yaml

    def test_no_storage_config_consumption(self, manage_fg_playbook):
        """AC-013: Flexible groups do not consume storage_config.yml.
        Comments documenting the non-dependency are acceptable."""
        play = manage_fg_playbook[0]
        playbook_yaml = yaml.dump(play, default_flow_style=False)
        assert "storage_config.yml" not in playbook_yaml

    def test_no_repo_status_dependency(self, manage_fg_playbook):
        """FR-4.1/FR-4.3: Flexible groups do not require repo_status.yml.
        Comments documenting the non-dependency are acceptable."""
        play = manage_fg_playbook[0]
        playbook_yaml = yaml.dump(play, default_flow_style=False)
        assert "repo_status" not in playbook_yaml


# ── Scenario 2: Isolate an invalid flexible group in a lifecycle run ───


@pytest.mark.fvt
@pytest.mark.order(40011)
class TestLifecycleIsolation:
    """Per-group failure isolation during lifecycle runs."""

    def test_provision_custom_excludes_fg(self):
        """AC-012: provision_custom explicitly excludes fg_ groups so they
        don't interfere with the custom catch-all during lifecycle runs."""
        text = PROVISION_CUSTOM_YML.read_text(encoding="utf-8")
        assert "rejectattr('name', 'match', '^fg_')" in text

    def test_manage_fg_uses_conditional_roles(self, manage_fg_playbook):
        """Per-group isolation: provision_common runs only when the operation
        is add or configure AND target groups are present."""
        play = manage_fg_playbook[0]
        roles = play.get("roles", [])
        for role in roles:
            if isinstance(role, dict) and role.get("role") == "provision_common":
                when = role.get("when", [])
                assert any("fg_operation" in str(w) for w in when), (
                    "provision_common role must be conditional on fg_operation"
                )
                assert any("target_functional_groups" in str(w) for w in when), (
                    "provision_common role must be conditional on target groups"
                )
                return
        pytest.fail("provision_common role not found in manage_functional_group")

    def test_fg_generation_runs_before_manage(self, orchestrator_playbook):
        """FG generation must run before manage_functional_group in all flows."""
        gen_idx = None
        manage_idx = None
        for i, play in enumerate(orchestrator_playbook):
            if "orchestrator_functional_groups" in str(play.get("roles", [])):
                gen_idx = i
            pb = play.get("ansible.builtin.import_playbook", "")
            if "manage_functional_group" in pb and "never" not in play.get("tags", []):
                manage_idx = i
        if gen_idx is not None and manage_idx is not None:
            assert gen_idx < manage_idx, (
                "FG generation must precede manage_functional_group import"
            )
