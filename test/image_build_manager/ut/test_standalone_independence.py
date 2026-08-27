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
"""Tests to verify standalone independence — no external dependencies."""

import pathlib
import re

import yaml


# ut/test_standalone_... -> ut/ -> image_build_manager/ -> test/ -> repo_root/
SRC_DIR = pathlib.Path(__file__).resolve().parents[3] / "src" / "image_build_manager"


class TestNoExternalDependencies:
    """Ensure the repo has no unresolved external file dependencies."""

    def test_no_software_config_json_reference_in_active_code(self):
        """Active (uncommented) code must not reference software_config.json."""
        issues = []
        for yml_file in SRC_DIR.rglob("*.yml"):
            if "generate_functional_groups" in str(yml_file):
                continue  # Mode C role — expected to have references
            if "fetch_packages.yml" in str(yml_file):
                continue  # Mode C task file — not included in standalone (call commented out in main.yml)
            with open(yml_file, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "software_config_file" in stripped or "software_config.json" in stripped:
                        issues.append(f"{yml_file.relative_to(SRC_DIR)}:{lineno}: {stripped}")
        assert len(issues) == 0, (
            f"Active code references software_config:\n" + "\n".join(issues)
        )

    def test_no_metadata_file_path_in_active_code(self):
        """Active code must not check for localrepo_metadata.yml."""
        issues = []
        for yml_file in SRC_DIR.rglob("*.yml"):
            with open(yml_file, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "metadata_file_path" in stripped and "stat" not in stripped:
                        # Allow stat checks that are commented out
                        if "localrepo_metadata" in stripped:
                            issues.append(
                                f"{yml_file.relative_to(SRC_DIR)}:{lineno}: {stripped}"
                            )
        assert len(issues) == 0, (
            f"Active code references metadata_file_path:\n" + "\n".join(issues)
        )

    def test_no_provision_config_reference(self):
        """Active code must not reference provision_config.yml."""
        issues = []
        for yml_file in SRC_DIR.rglob("*.yml"):
            if "generate_functional_groups" in str(yml_file):
                continue
            with open(yml_file, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "provision_config" in stripped:
                        issues.append(f"{yml_file.relative_to(SRC_DIR)}:{lineno}: {stripped}")
        assert len(issues) == 0, (
            f"Active code references provision_config:\n" + "\n".join(issues)
        )

    def test_ansible_cfg_no_omnia_paths(self):
        """ansible.cfg must not reference /opt/omnia paths."""
        cfg_file = SRC_DIR / "ansible.cfg"
        if not cfg_file.exists():
            return
        with open(cfg_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "/opt/omnia" not in content, (
            "ansible.cfg contains /opt/omnia references"
        )


class TestRepoStructure:
    """Validate the expected standalone repository structure."""

    def test_input_dir_exists(self):
        """input/ directory must exist with config templates."""
        assert (SRC_DIR / "input").is_dir()

    def test_image_build_config_exists(self):
        """image_build_config.yml template must exist in input/."""
        assert (SRC_DIR / "input" / "image_build_config.yml").exists()

    def test_package_groups_exists(self):
        """package_groups.yml template must exist in input/."""
        assert (SRC_DIR / "input" / "package_groups.yml").exists()

    def test_samples_dir_exists(self):
        """samples/repo_manager_output/ must exist."""
        assert (SRC_DIR / "samples" / "repo_manager_output").is_dir()

    def test_sample_repo_status_exists(self):
        """repo_status.yml sample must exist."""
        assert (
            SRC_DIR / "samples" / "repo_manager_output" / "repo_status.yml"
        ).exists()

    def test_package_groups_in_input(self):
        """package_groups.yml must exist in input/ (functional group mapping)."""
        assert (SRC_DIR / "input" / "package_groups.yml").exists()

    def test_ansible_cfg_exists(self):
        """ansible.cfg must exist."""
        assert (SRC_DIR / "ansible.cfg").exists()

    def test_main_playbook_exists(self):
        """Main playbook must exist in playbooks/."""
        assert (SRC_DIR / "playbooks" / "image_build_manager.yml").exists()

    def test_all_roles_have_tasks(self):
        """Every role directory must have tasks/main.yml."""
        roles_dir = SRC_DIR / "roles"
        for role_dir in roles_dir.iterdir():
            if role_dir.is_dir():
                tasks_main = role_dir / "tasks" / "main.yml"
                assert tasks_main.exists(), (
                    f"Role '{role_dir.name}' missing tasks/main.yml"
                )
