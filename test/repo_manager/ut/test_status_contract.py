# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for multi-context status aggregation and atomic publication."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from source_loader import REPO_MANAGER_ROOT

from ansible.module_utils.repo_manager.repository_status_builder import (
    build_terminal_context_status,
    merge_context_status,
    merge_version_mapping,
    summarize_execution_contexts,
)
from plugins.modules import generate_local_repo_access


CONTEXTS = [
    {
        "context_id": "rhel_10.0",
        "os_type": "rhel",
        "os_version": "10.0",
        "architectures": ["x86_64", "aarch64"],
    },
    {
        "context_id": "rhel_10.2",
        "os_type": "rhel",
        "os_version": "10.2",
        "architectures": ["aarch64"],
    },
]


class StatusBuilderTests(unittest.TestCase):
    """Cover terminal, in-progress and failed multi-version status."""

    def test_context_summary_contains_only_public_stable_fields(self):
        """Internal catalog data cannot leak through execution contexts."""
        contexts = [{**CONTEXTS[0], "catalog_files": ["secret.json"]}]
        self.assertEqual(summarize_execution_contexts(contexts), [CONTEXTS[0]])

    def test_success_requires_every_selected_context(self):
        """A partially completed multi-version run remains in progress."""
        status, aggregate = build_terminal_context_status(
            CONTEXTS,
            [{"context_id": "rhel_10.0", "status": "success"}],
            "success",
        )
        self.assertEqual(status, {"10.0": "success", "10.2": "pending"})
        self.assertEqual(aggregate, "in_progress")

    def test_failure_keeps_later_context_pending(self):
        """A failed active version cannot make an unexecuted version successful."""
        status, aggregate = build_terminal_context_status(
            CONTEXTS,
            [{"context_id": "rhel_10.0", "status": "failed"}],
            "failed",
        )
        self.assertEqual(status, {"10.0": "failed", "10.2": "pending"})
        self.assertEqual(aggregate, "failed")

    def test_first_context_resets_stale_selected_version_status(self):
        """A new pass cannot retain success from an earlier selected version."""
        previous = {
            "overall_status_by_version": {"10.0": "success", "10.2": "success"}
        }
        status, aggregate = merge_context_status(
            previous, CONTEXTS, "10.0", "success"
        )
        self.assertEqual(status, {"10.0": "success", "10.2": "pending"})
        self.assertEqual(aggregate, "in_progress")

    def test_version_mapping_removes_unselected_versions(self):
        """Changing catalog selection removes obsolete version output."""
        merged = merge_version_mapping(
            {"repositories": {"9.6": {}, "10.0": {"old": True}}},
            "repositories",
            "10.2",
            {"new": True},
            selected_versions=["10.0", "10.2"],
        )
        self.assertEqual(
            merged,
            {"10.0": {"old": True}, "10.2": {"new": True}},
        )


class StatusPublicationTests(unittest.TestCase):
    """Verify fail-closed content and interrupted atomic replacement."""

    @staticmethod
    def _build_generator(execution_contexts, overall_status="success",
                         execution_results=None):
        """Return a generator configured for deterministic status tests."""
        generator = generate_local_repo_access.LocalRepoAccessGenerator.__new__(
            generate_local_repo_access.LocalRepoAccessGenerator
        )
        generator.pulp_server_ip = "192.0.2.10"
        generator.pulp_server_port = 2225
        generator.pulp_protocol = "https"
        generator.base_url = "https://192.0.2.10:2225"
        generator.cluster_os_type = "rhel"
        generator.cluster_os_version = "10.0"
        generator.architectures = list(execution_contexts[0]["architectures"])
        generator.execution_contexts = execution_contexts
        generator.execution_results = execution_results or []
        generator.overall_status = overall_status
        generator.repo_config = "partial"
        generator.certs_dir = "/safe/certs"
        generator.local_repo_config_path = ""
        generator._local_repo_config = {}  # pylint: disable=protected-access
        generator.rpm_distributions = []
        generator.file_distributions = []
        generator.python_distributions = []
        generator.missing_rpm_repositories = {}
        generator.missing_rpm_repositories_by_version = {}
        return generator

    def test_subscription_additional_repo_priority_is_published(self):
        """An entitled additional repository retains its status priority."""
        repository_name = "rhel-10-for-x86_64-supplementary-rpms"
        context = {
            "context_id": "rhel_10.0",
            "os_type": "rhel",
            "os_version": "10.0",
            "architectures": ["x86_64"],
            "referenced_repositories": {
                "x86_64": [repository_name],
            },
        }
        generator = self._build_generator([context])
        generator._local_repo_config = {  # pylint: disable=protected-access
            "repositories": {
                "10.0": {
                    "x86_64": {
                        "additional_repos": {
                            repository_name: {
                                "url": "",
                                "priority": 50,
                            },
                        },
                    },
                },
            },
        }
        generator.rpm_distributions = [{
            "name": f"x86_64_rhel_10.0_{repository_name}",
            "base_path": (
                "offline_repo/cluster/x86_64/rhel/10.0/rpms/"
                f"{repository_name}"
            ),
            "base_url": (
                "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
                "x86_64/rhel/10.0/rpms/"
                f"{repository_name}/"
            ),
        }]

        with patch.object(generator, "fetch_distributions"):
            content, _rpm_count, _file_count = (
                generator.generate_yaml_content()
            )

        data = yaml.safe_load(content)
        self.assertEqual(
            data["repositories"]["10.0"]["x86_64"][repository_name],
            {
                "url": (
                    "https://192.0.2.10:2225/pulp/content/offline_repo/"
                    "cluster/x86_64/rhel/10.0/rpms/"
                    f"{repository_name}/"
                ),
                "priority": 50,
            },
        )

    def test_file_repositories_are_published_by_version(self):
        """Every selected context publishes its exact File distribution URL."""
        generator = generate_local_repo_access.LocalRepoAccessGenerator.__new__(
            generate_local_repo_access.LocalRepoAccessGenerator
        )
        generator.pulp_server_ip = "192.0.2.10"
        generator.pulp_server_port = 2225
        generator.pulp_protocol = "https"
        generator.base_url = "https://192.0.2.10:2225"
        generator.cluster_os_type = "rhel"
        generator.cluster_os_version = "10.0"
        generator.architectures = ["x86_64"]
        generator.execution_contexts = [
            {
                "context_id": "rhel_10.0",
                "os_type": "rhel",
                "os_version": "10.0",
                "architectures": ["x86_64"],
            },
            {
                "context_id": "rhel_10.2",
                "os_type": "rhel",
                "os_version": "10.2",
                "architectures": ["x86_64"],
            },
        ]
        generator.execution_results = []
        generator.overall_status = "success"
        generator.repo_config = "partial"
        generator.certs_dir = "/safe/certs"
        generator.local_repo_config_path = ""
        generator._local_repo_config = {}  # pylint: disable=protected-access
        generator.rpm_distributions = []
        generator.file_distributions = [
            {
                "base_path": (
                    "offline_repo/cluster/x86_64/rhel/10.0/tarball/imb"
                ),
                "base_url": (
                    "https://192.0.2.10:2225/pulp/content/offline_repo/"
                    "cluster/x86_64/rhel/10.0/tarball/imb/"
                ),
            },
            {
                "base_path": (
                    "offline_repo/cluster/x86_64/rhel/10.2/tarball/imb"
                ),
                "base_url": (
                    "https://192.0.2.10:2225/pulp/content/offline_repo/"
                    "cluster/x86_64/rhel/10.2/tarball/imb/"
                ),
            },
        ]
        for content_type in (
            "manifest", "git", "shell", "iso",
            "ansible_galaxy_collection",
        ):
            artifact_path = (
                "community/general"
                if content_type == "ansible_galaxy_collection"
                else "sample"
            )
            generator.file_distributions.append({
                "base_path": (
                    "offline_repo/cluster/x86_64/rhel/10.0/"
                    f"{content_type}/{artifact_path}"
                ),
                "base_url": (
                    "https://192.0.2.10:2225/pulp/content/offline_repo/"
                    f"cluster/x86_64/rhel/10.0/{content_type}/"
                    f"{artifact_path}/"
                ),
            })
        generator.python_distributions = [
            {
                "base_path": (
                    "offline_repo/cluster/x86_64/rhel/10.0/pip_module/"
                    "PyMySQL==1.1.2"
                ),
                "base_url": (
                    "https://192.0.2.10:2225/pypi/offline_repo/cluster/"
                    "x86_64/rhel/10.0/pip_module/PyMySQL==1.1.2/"
                ),
            },
            {
                "base_path": (
                    "offline_repo/cluster/x86_64/rhel/10.2/pip_module/"
                    "PyMySQL==1.1.2"
                ),
                "base_url": (
                    "https://192.0.2.10:2225/pypi/offline_repo/cluster/"
                    "x86_64/rhel/10.2/pip_module/PyMySQL==1.1.2/"
                ),
            },
        ]
        generator.missing_rpm_repositories = {}
        generator.missing_rpm_repositories_by_version = {}

        with patch.object(generator, "fetch_distributions"):
            content, rpm_count, file_count = generator.generate_yaml_content()

        data = yaml.safe_load(content)
        self.assertEqual(
            data["file_repos"]["10.0"]["x86_64"]["tarball"]["imb"],
            "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
            "x86_64/rhel/10.0/tarball/imb/",
        )
        self.assertEqual(
            data["file_repos"]["10.2"]["x86_64"]["tarball"]["imb"],
            "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
            "x86_64/rhel/10.2/tarball/imb/",
        )
        self.assertEqual(
            data["file_repos"]["10.2"]["x86_64"]["pip_module"][
                "PyMySQL_1_1_2"
            ],
            "https://192.0.2.10:2225/pypi/offline_repo/cluster/x86_64/"
            "rhel/10.2/pip_module/PyMySQL==1.1.2/",
        )
        self.assertEqual(
            data["base_urls"]["10.0"]["x86_64"]["tarball"],
            "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
            "x86_64/rhel/10.0/tarball/",
        )
        self.assertEqual(
            data["base_urls"]["10.2"]["x86_64"]["tarball"],
            "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
            "x86_64/rhel/10.2/tarball/",
        )
        self.assertEqual(
            data["base_urls"]["10.2"]["x86_64"]["pip_module"],
            "https://192.0.2.10:2225/pypi/offline_repo/cluster/x86_64/"
            "rhel/10.2/pip_module/",
        )
        self.assertEqual(
            set(data["base_urls"]["10.0"]["x86_64"]),
            {
                "tarball", "manifest", "pip_module", "git", "shell", "iso",
                "ansible_galaxy_collection",
            },
        )
        self.assertEqual(
            data["base_urls"]["10.0"]["x86_64"][
                "ansible_galaxy_collection"
            ],
            "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
            "x86_64/rhel/10.0/ansible_galaxy_collection/",
        )
        self.assertEqual(
            set(data["base_urls"]["10.2"]["x86_64"]),
            {"tarball", "pip_module"},
        )
        for removed_field in (
            "tarball_base_url", "manifest_base_url", "pip_base_url",
            "git_base_url", "offline_tarball_path",
            "offline_manifest_path", "offline_pip_module_path",
            "offline_git_path", "offline_shell_path", "offline_iso_path",
            "offline_ansible_galaxy_collection_path",
        ):
            self.assertNotIn(removed_field, data)
        self.assertNotIn("content_base_urls", data)
        self.assertEqual((rpm_count, file_count), (0, 9))

        generator.execution_contexts = generator.execution_contexts[:1]
        with patch.object(generator, "fetch_distributions"):
            single_content, _rpm_count, _file_count = (
                generator.generate_yaml_content()
            )
        single_data = yaml.safe_load(single_content)
        self.assertEqual(list(single_data["file_repos"]), ["10.0"])
        self.assertEqual(list(single_data["base_urls"]), ["10.0"])

    def test_failed_status_contains_no_consumable_repository_urls(self):
        """A failed run publishes empty repository and content-base maps."""
        generator = generate_local_repo_access.LocalRepoAccessGenerator.__new__(
            generate_local_repo_access.LocalRepoAccessGenerator
        )
        generator.execution_contexts = CONTEXTS
        generator.execution_results = [
            {"context_id": "rhel_10.0", "status": "failed"}
        ]
        generator.missing_rpm_repositories_by_version = {}
        generator.repo_config = "partial"
        generator.pulp_server_port = 2225
        generator.certs_dir = "/safe/certs"
        content, rpm_count, file_count = generator.generate_failed_yaml_content()
        data = yaml.safe_load(content)
        self.assertEqual(data["overall_status"], "failed")
        self.assertEqual(data["repositories"]["10.0"]["x86_64"], {})
        self.assertEqual(data["repositories"]["10.2"]["aarch64"], {})
        self.assertEqual(data["base_urls"]["10.0"]["x86_64"], {})
        self.assertEqual(data["base_urls"]["10.2"]["aarch64"], {})
        self.assertNotIn("offline_tarball_path", data)
        self.assertEqual((rpm_count, file_count), (0, 0))

    def test_missing_repository_fails_only_the_affected_version(self):
        """Live inspection retains URLs for the unaffected ready version."""
        contexts = [
            {
                "context_id": "rhel_10.0",
                "os_type": "rhel",
                "os_version": "10.0",
                "architectures": ["x86_64"],
                "referenced_repositories": {"x86_64": ["baseos"]},
            },
            {
                "context_id": "rhel_10.2",
                "os_type": "rhel",
                "os_version": "10.2",
                "architectures": ["x86_64"],
                "referenced_repositories": {"x86_64": ["baseos"]},
            },
        ]
        generator = self._build_generator(contexts)
        generator.rpm_distributions = [{
            "name": "x86_64_rhel_10.0_baseos",
            "base_path": "offline_repo/cluster/x86_64/rhel/10.0/rpms/baseos",
            "base_url": (
                "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
                "x86_64/rhel/10.0/rpms/baseos/"
            ),
        }]
        generator.file_distributions = [
            {
                "base_path": (
                    "offline_repo/cluster/x86_64/rhel/10.0/tarball/imb"
                ),
                "base_url": (
                    "https://192.0.2.10:2225/pulp/content/offline_repo/"
                    "cluster/x86_64/rhel/10.0/tarball/imb/"
                ),
            },
            {
                "base_path": (
                    "offline_repo/cluster/x86_64/rhel/10.2/tarball/imb"
                ),
                "base_url": (
                    "https://192.0.2.10:2225/pulp/content/offline_repo/"
                    "cluster/x86_64/rhel/10.2/tarball/imb/"
                ),
            },
        ]

        with patch.object(generator, "fetch_distributions"):
            content, rpm_count, file_count = generator.generate_yaml_content()

        data = yaml.safe_load(content)
        self.assertEqual(data["overall_status"], "failed")
        self.assertEqual(
            data["overall_status_by_version"],
            {"10.0": "success", "10.2": "failed"},
        )
        self.assertIn("baseos", data["repositories"]["10.0"]["x86_64"])
        self.assertEqual(data["repositories"]["10.2"]["x86_64"], {})
        self.assertIn(
            "imb", data["file_repos"]["10.0"]["x86_64"]["tarball"]
        )
        self.assertEqual(data["file_repos"]["10.2"]["x86_64"], {})
        self.assertEqual(
            data["base_urls"]["10.0"]["x86_64"]["tarball"],
            "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
            "x86_64/rhel/10.0/tarball/",
        )
        self.assertEqual(data["base_urls"]["10.2"]["x86_64"], {})
        self.assertEqual((rpm_count, file_count), (1, 2))

        execution_generator = self._build_generator(
            contexts,
            overall_status="failed",
            execution_results=[
                {"context_id": "rhel_10.0", "status": "success"},
                {"context_id": "rhel_10.2", "status": "failed"},
            ],
        )
        execution_generator.rpm_distributions = (
            generator.rpm_distributions + [{
                "name": "x86_64_rhel_10.2_baseos",
                "base_path": (
                    "offline_repo/cluster/x86_64/rhel/10.2/rpms/baseos"
                ),
                "base_url": (
                    "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
                    "x86_64/rhel/10.2/rpms/baseos/"
                ),
            }]
        )
        execution_generator.file_distributions = generator.file_distributions
        with patch.object(execution_generator, "fetch_distributions"):
            execution_content, execution_rpm_count, execution_file_count = (
                execution_generator.generate_yaml_content()
            )

        execution_data = yaml.safe_load(execution_content)
        self.assertEqual(execution_data["overall_status"], "failed")
        self.assertEqual(
            execution_data["overall_status_by_version"],
            {"10.0": "success", "10.2": "failed"},
        )
        self.assertIn(
            "baseos", execution_data["repositories"]["10.0"]["x86_64"]
        )
        self.assertEqual(
            execution_data["repositories"]["10.2"]["x86_64"], {}
        )
        self.assertIn(
            "imb",
            execution_data["file_repos"]["10.0"]["x86_64"]["tarball"],
        )
        self.assertEqual(
            execution_data["file_repos"]["10.2"]["x86_64"], {}
        )
        self.assertEqual(
            execution_data["base_urls"]["10.0"]["x86_64"][
                "tarball"
            ],
            "https://192.0.2.10:2225/pulp/content/offline_repo/cluster/"
            "x86_64/rhel/10.0/tarball/",
        )
        self.assertEqual(
            execution_data["base_urls"]["10.2"]["x86_64"], {}
        )
        self.assertEqual((execution_rpm_count, execution_file_count), (2, 2))

    def test_status_failure_message_receives_missing_contexts(self):
        """Standalone status preserves failure context and module path contract."""
        playbook = (
            REPO_MANAGER_ROOT / "playbooks" / "repo_operations" /
            "generate_repo_status.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "status_generation_result.missing_rpm_repositories",
            playbook,
        )
        output_directory_task = playbook.split(
            "- name: Ensure output directory exists", 1
        )[1].split(
            "- name: Generate terminal status for all catalog contexts", 1
        )[0]
        self.assertNotIn("recurse: true", output_directory_task)

        status_generation_task = playbook.split(
            "- name: Generate terminal status for all catalog contexts", 1
        )[1].split(
            "- name: Fail when catalog-required RPM repositories are unavailable",
            1,
        )[0]
        for required_environment in (
            'REPO_MANAGER_BASE_DIR: "{{ repo_manager_base_dir }}"',
            'REPO_MANAGER_CONFIG_PATH: '
            '"{{ repo_manager_base_dir }}/vars/default.yml"',
            'REPO_MANAGER_INPUT_PROJECT_DIR: "{{ input_project_dir }}"',
            'OMNIA_BASE_DIR: "{{ omnia_base_dir }}"',
            'OMNIA_DATA_PATH: "{{ omnia_data_path }}"',
            'REPO_MANAGER_DATA_PATH: "{{ repo_manager_runtime_dir }}"',
        ):
            self.assertIn(required_environment, status_generation_task)

    def test_atomic_write_preserves_previous_status_on_replace_failure(self):
        """An interrupted publication retains the last complete public status."""
        with tempfile.TemporaryDirectory() as work_dir:
            output = Path(work_dir) / "repo_status.yml"
            output.write_text("overall_status: success\n", encoding="utf-8")
            generator = generate_local_repo_access.LocalRepoAccessGenerator.__new__(
                generate_local_repo_access.LocalRepoAccessGenerator
            )
            generator.output_path = str(output)
            with patch.object(
                generate_local_repo_access.os,
                "replace",
                side_effect=OSError("simulated interruption"),
            ):
                with self.assertRaises(OSError):
                    generator.write_yaml("overall_status: failed\n")
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "overall_status: success\n",
            )
            self.assertEqual(list(Path(work_dir).glob(".repo_status.yml.*")), [])

    def test_separate_file_repos_by_version_field_is_not_introduced(self):
        """Version qualification remains inside the existing file_repos field."""
        source = (
            REPO_MANAGER_ROOT / "plugins" / "modules" /
            "generate_local_repo_access.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("file_repos_by_version", source)


if __name__ == "__main__":
    unittest.main()
