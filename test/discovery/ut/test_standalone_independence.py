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
"""Tests to verify standalone independence -- no external dependencies."""

import pathlib

import yaml


# ut/test_standalone_... -> ut/ -> discovery/ -> test/ -> repo_root/
SRC_DIR = pathlib.Path(__file__).resolve().parents[3] / "src" / "discovery"


class TestNoExternalDependencies:
    """Ensure the discovery domain has no unresolved external references."""

    def test_no_hardcoded_omnia_paths_in_ansible_cfg(self):
        """ansible.cfg must not reference /opt/omnia paths."""
        cfg_file = SRC_DIR / "playbooks" / "ansible.cfg"
        if not cfg_file.exists():
            return
        content = cfg_file.read_text(encoding="utf-8")
        # log_path is allowed to use /var/log/omnia
        lines = [
            line for line in content.splitlines()
            if not line.strip().startswith("#")
            and not line.strip().startswith("log_path")
        ]
        for line in lines:
            assert "/opt/omnia" not in line, (
                f"ansible.cfg contains /opt/omnia reference: {line.strip()}"
            )

    def test_no_image_build_references_in_discovery(self):
        """Discovery code must not reference image_build_manager."""
        issues = []
        for yml_file in SRC_DIR.rglob("*.yml"):
            with open(yml_file, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "image_build" in stripped:
                        issues.append(
                            f"{yml_file.relative_to(SRC_DIR)}:{lineno}: "
                            f"{stripped}"
                        )
        assert not issues, (
            "Discovery code references image_build:\n"
            + "\n".join(issues)
        )


class TestRepoStructure:
    """Validate the expected standalone repository structure."""

    def test_input_dir_exists(self):
        """input/ directory must exist with config templates."""
        assert (SRC_DIR / "input").is_dir()

    def test_discovery_config_exists(self):
        """discovery_config.yml template must exist in input/."""
        assert (SRC_DIR / "input" / "discovery_config.yml").exists()

    def test_network_spec_exists(self):
        """network_spec.yml template must exist in input/."""
        assert (SRC_DIR / "input" / "network_spec.yml").exists()

    def test_playbooks_dir_exists(self):
        """playbooks/ directory must exist."""
        assert (SRC_DIR / "playbooks").is_dir()

    def test_main_playbook_exists(self):
        """Main playbook must exist in playbooks/."""
        assert (SRC_DIR / "playbooks" / "discovery.yml").exists()

    def test_ansible_cfg_exists(self):
        """ansible.cfg must exist in playbooks/."""
        assert (SRC_DIR / "playbooks" / "ansible.cfg").exists()

    def test_roles_dir_exists(self):
        """roles/ directory must exist."""
        assert (SRC_DIR / "roles").is_dir()

    def test_all_roles_have_tasks(self):
        """Every role directory must have tasks/main.yml."""
        roles_dir = SRC_DIR / "roles"
        for role_dir in roles_dir.iterdir():
            if role_dir.is_dir():
                tasks_main = role_dir / "tasks" / "main.yml"
                assert tasks_main.exists(), (
                    f"Role '{role_dir.name}' missing tasks/main.yml"
                )

    def test_plugins_dir_exists(self):
        """plugins/ directory must exist."""
        assert (SRC_DIR / "plugins").is_dir()

    def test_validation_schema_dir_exists(self):
        """Validation schema directory must exist."""
        schema_dir = (
            SRC_DIR
            / "plugins" / "module_utils" / "discovery_validation" / "schema"
        )
        assert schema_dir.is_dir()

    def test_discovery_config_schema_exists(self):
        """discovery_config.json schema must exist."""
        schema = (
            SRC_DIR
            / "plugins" / "module_utils" / "discovery_validation" / "schema"
            / "discovery_config.json"
        )
        assert schema.exists()


class TestInputTemplateContent:
    """Validate the content of input template files."""

    def test_discovery_config_has_ome_ip(self):
        """discovery_config.yml must define the ome_ip field."""
        config_file = SRC_DIR / "input" / "discovery_config.yml"
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert "ome_ip" in data, "discovery_config.yml missing ome_ip field"

    def test_network_spec_has_networks(self):
        """network_spec.yml must define the Networks list."""
        spec_file = SRC_DIR / "input" / "network_spec.yml"
        data = yaml.safe_load(spec_file.read_text(encoding="utf-8"))
        assert "Networks" in data, "network_spec.yml missing Networks key"

    def test_network_spec_has_admin_network(self):
        """network_spec.yml must include an admin_network entry."""
        spec_file = SRC_DIR / "input" / "network_spec.yml"
        data = yaml.safe_load(spec_file.read_text(encoding="utf-8"))
        networks = data.get("Networks", [])
        admin_found = any(
            "admin_network" in net for net in networks if isinstance(net, dict)
        )
        assert admin_found, "network_spec.yml missing admin_network"
