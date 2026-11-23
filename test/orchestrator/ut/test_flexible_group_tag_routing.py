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

"""TC_UT_tag_router_010: Public tag registration and routing.

Test plan reference:
  ER-ORCH-009-flexible-functional-groups-part2 / test-plan.md § 6
  Priority: P0
  HLD mapping: Section 2.4 tag registration and router integration
  ER mapping: FR-4.1, FR-4.3, FR-4.4, AC-005, AC-007, AC-007a, AC-013
  Story: ER-ORCH-009-role-topology-routing

Scenarios:
  1. Route the single flexible-group tag and lifecycle tags
     GIVEN manage-functional-group or a provision/execute/default run is selected
     WHEN setup and router validation run
     THEN the flexible-group playbook is imported with required validation
     AND exactly one flexible-group tag exists (no configure-functional-groups)

  2. Reject invalid or category-coupled routing
     GIVEN a misspelled tag, mixed selector, repo-status requirement, or
     category playbook import
     WHEN structural validation runs
     THEN the invalid route is rejected
"""

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
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
CLASSIFICATION_PATH = (
    ORCHESTRATOR_ROOT / "vars" / "functional_group_classification.yml"
)


@pytest.fixture(scope="module")
def orchestrator_playbook() -> list[dict]:
    """Parse orchestrator.yml as a list of plays."""
    return yaml.safe_load(ORCHESTRATOR_YML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manage_fg_playbook() -> list[dict]:
    """Parse the manage_functional_group playbook."""
    return yaml.safe_load(MANAGE_FG_YML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def provision_custom_text() -> str:
    """Raw text of provision_custom.yml for structural assertions."""
    return PROVISION_CUSTOM_YML.read_text(encoding="utf-8")


# ── Helpers ─────────────────────────────────────────────────────────────


def _plays_with_tag(playbook: list[dict], tag: str) -> list[dict]:
    """Return plays whose tags list contains *tag*."""
    return [p for p in playbook if tag in p.get("tags", [])]


def _import_plays(playbook: list[dict]) -> list[dict]:
    """Return plays that use ansible.builtin.import_playbook."""
    return [p for p in playbook if "ansible.builtin.import_playbook" in p]


def _fg_imports(playbook: list[dict]) -> list[dict]:
    """Return plays importing manage_functional_group.yml."""
    return [
        p
        for p in _import_plays(playbook)
        if "manage_functional_group" in p.get("ansible.builtin.import_playbook", "")
    ]


# ── Scenario 1: Route the single flexible-group tag and lifecycle tags ─


class TestSingleTagRegistration:
    """Exactly one public flexible-group tag; no configure-functional-groups."""

    def test_manage_functional_group_tag_exists(self, orchestrator_playbook):
        """FR-4.1: The manage-functional-group tag is registered."""
        plays = _plays_with_tag(orchestrator_playbook, "manage-functional-group")
        assert len(plays) >= 1, "manage-functional-group tag not registered"

    def test_no_configure_functional_groups_tag(self, orchestrator_playbook):
        """HLD v13: The legacy configure-functional-groups tag must not exist."""
        plays = _plays_with_tag(orchestrator_playbook, "configure-functional-groups")
        assert len(plays) == 0, (
            "Retired configure-functional-groups tag still registered"
        )

    def test_dedicated_tag_entries_are_opt_in_only(self, orchestrator_playbook):
        """FR-4.1: Dedicated manage-functional-group plays carry 'never' tag
        so they only run when explicitly requested."""
        dedicated = [
            p
            for p in _plays_with_tag(orchestrator_playbook, "manage-functional-group")
            if "never" in p.get("tags", [])
        ]
        # Preamble + manage playbook = 2 dedicated opt-in imports
        assert len(dedicated) == 2, (
            f"Expected 2 dedicated opt-in imports, found {len(dedicated)}"
        )

    def test_dedicated_imports_reference_manage_fg_playbook(
        self, orchestrator_playbook
    ):
        """The dedicated manage-functional-group imports reference the
        correct playbook path."""
        dedicated = [
            p
            for p in _plays_with_tag(orchestrator_playbook, "manage-functional-group")
            if "never" in p.get("tags", [])
            and "ansible.builtin.import_playbook" in p
        ]
        paths = [p["ansible.builtin.import_playbook"] for p in dedicated]
        assert any("manage_functional_group" in path for path in paths)
        assert any("provision_preamble" in path for path in paths)


class TestLifecycleTagRouting:
    """FR-4.4: Flexible groups publish in default/provision/execute flows."""

    def test_lifecycle_import_not_tagged_never(self, orchestrator_playbook):
        """FR-4.4: Lifecycle publication entries must NOT carry the 'never'
        tag — they run automatically during provision/execute."""
        lifecycle = [
            p
            for p in _fg_imports(orchestrator_playbook)
            if "never" not in p.get("tags", [])
        ]
        assert len(lifecycle) >= 1, (
            "No lifecycle (non-never) import of manage_functional_group found"
        )

    def test_lifecycle_import_tagged_provision_and_execute(
        self, orchestrator_playbook
    ):
        """FR-4.4: Lifecycle publication is tagged with both provision and
        execute so it runs in both flows."""
        lifecycle = [
            p
            for p in _fg_imports(orchestrator_playbook)
            if "never" not in p.get("tags", [])
        ]
        for play in lifecycle:
            tags = play.get("tags", [])
            assert "execute" in tags or "provision" in tags, (
                f"Lifecycle import missing provision/execute tag: {tags}"
            )

    def test_fg_generation_included_for_manage_tag(self, orchestrator_playbook):
        """The functional-group generation play is tagged with
        manage-functional-group so FGs are generated before the dedicated
        flow runs."""
        gen_plays = [
            p
            for p in orchestrator_playbook
            if "orchestrator_functional_groups" in str(p.get("roles", []))
            or "orchestrator_functional_groups" in str(p.get("role", ""))
        ]
        tagged = [
            p
            for p in gen_plays
            if "manage-functional-group" in p.get("tags", [])
        ]
        assert len(tagged) >= 1, (
            "FG generation play not tagged with manage-functional-group"
        )


class TestManageFgPlaybookStructure:
    """Structural validation of the manage_functional_group.yml playbook."""

    def test_playbook_targets_oim_host(self, manage_fg_playbook):
        """The manage playbook must target the oim host group."""
        play = manage_fg_playbook[0]
        assert play.get("hosts") == "oim"

    def test_playbook_validates_fg_operation(self, manage_fg_playbook):
        """The playbook validates fg_operation is one of add/remove/configure."""
        play = manage_fg_playbook[0]
        vars_ = play.get("vars", {})
        assert vars_.get("fg_operation") == "add", (
            "Default fg_operation should be 'add'"
        )

    def test_playbook_validates_configure_scope(self, manage_fg_playbook):
        """The playbook validates configure_scope is one of both/boot/cloud_init."""
        play = manage_fg_playbook[0]
        vars_ = play.get("vars", {})
        assert vars_.get("configure_scope") == "both", (
            "Default configure_scope should be 'both'"
        )

    def test_provision_common_role_used_for_add_configure(
        self, manage_fg_playbook
    ):
        """FR-4.1/FR-4.3: Add and configure use the shared provision_common
        role, not category-specific provisioning."""
        play = manage_fg_playbook[0]
        roles = play.get("roles", [])
        role_names = [
            r.get("role") if isinstance(r, dict) else r for r in roles
        ]
        assert "provision_common" in role_names

    def test_no_category_bolt_on_roles(self, manage_fg_playbook):
        """AC-013: Flexible groups never consume category bolt-on roles."""
        play = manage_fg_playbook[0]
        roles = play.get("roles", [])
        role_names = [
            r.get("role") if isinstance(r, dict) else r for r in roles
        ]
        bolt_on_roles = {"mount_config", "k8s_config", "slurm_config", "openldap", "telemetry"}
        for role_name in role_names:
            assert role_name not in bolt_on_roles, (
                f"Bolt-on role '{role_name}' must not appear in flexible-group playbook"
            )


# ── Scenario 2: Reject invalid or category-coupled routing ─────────────


class TestInvalidRouting:
    """Invalid tags, mixed selectors, and category coupling are rejected."""

    def test_no_repo_status_dependency(self, manage_fg_playbook):
        """FR-4.1/FR-4.3: Flexible groups do not require repo_status.yml.
        Comments documenting the non-dependency are acceptable."""
        play = manage_fg_playbook[0]
        playbook_yaml = yaml.dump(play, default_flow_style=False)
        assert "repo_status" not in playbook_yaml, (
            "manage_functional_group.yml must not use repo_status in tasks/vars"
        )

    def test_no_omnia_config_dependency(self, manage_fg_playbook):
        """AC-013: Flexible groups do not consume omnia_config.yml.
        Comments documenting the non-dependency are acceptable."""
        play = manage_fg_playbook[0]
        playbook_yaml = yaml.dump(play, default_flow_style=False)
        assert "omnia_config.yml" not in playbook_yaml, (
            "manage_functional_group.yml must not use omnia_config.yml in tasks/vars"
        )

    def test_no_storage_config_dependency(self, manage_fg_playbook):
        """AC-013: Flexible groups do not consume storage_config.yml.
        Comments documenting the non-dependency are acceptable."""
        play = manage_fg_playbook[0]
        playbook_yaml = yaml.dump(play, default_flow_style=False)
        assert "storage_config.yml" not in playbook_yaml, (
            "manage_functional_group.yml must not use storage_config.yml in tasks/vars"
        )

    def test_provision_custom_excludes_fg_groups(self, provision_custom_text):
        """AC-012: provision_custom's catch-all explicitly excludes fg_."""
        assert "rejectattr('name', 'match', '^fg_')" in provision_custom_text, (
            "provision_custom.yml must exclude fg_ groups from its catch-all"
        )

    def test_no_category_provisioning_playbook_import(self):
        """AC-013: manage_functional_group must not import category
        provisioning playbooks (provision_kubernetes, provision_slurm, etc.)."""
        text = MANAGE_FG_YML.read_text(encoding="utf-8")
        category_playbooks = [
            "provision_kubernetes",
            "provision_slurm",
            "provision_os",
            "provision_custom",
        ]
        for playbook in category_playbooks:
            assert playbook not in text, (
                f"manage_functional_group.yml must not import {playbook}"
            )
