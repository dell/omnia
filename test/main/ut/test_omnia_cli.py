#!/usr/bin/env python3

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

"""Focused local tests for omnia-cli domain file and status handling."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
OMNIA_CLI = REPO_ROOT / "src" / "main" / "omnia-cli"
OMNIA_COMPLETION = REPO_ROOT / "src" / "main" / "omnia-bash-completion"
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

DOMAIN_STATUS_FILES = {
    "repo_manager": ("repo_status.yml", "success"),
    "image_build_manager": ("build_status.yml", "success"),
    "orchestrator": ("orchestrator_status.yml", "success"),
    "discovery": ("discovery_status.yml", "success"),
    "telemetry": ("telemetry_status.yml", "success"),
    "build_stream": ("build_stream_status.yml", "prepared"),
    "utils": ("utils_status.yml", "success"),
}


class OmniaCliTest(unittest.TestCase):
    """Exercise the CLI against an isolated runtime data tree."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="omnia-cli-test-")
        self.data_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_cli(self, *args, env_overrides=None):
        result, output = self.invoke_cli(*args, env_overrides=env_overrides)
        self.assertEqual(result.returncode, 0, output)
        return output

    def invoke_cli(self, *args, env_overrides=None):
        env = os.environ.copy()
        env["OMNIA_DATA_PATH"] = str(self.data_path)
        env["OMNIA_PROJECT_NAME"] = "project_default"
        env.update(env_overrides or {})
        result = subprocess.run(
            [str(OMNIA_CLI), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        output = ANSI_ESCAPE.sub("", result.stdout + result.stderr)
        return result, output

    def runtime_dir(self, domain, area):
        path = self.data_path / domain / area / "project_default"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_csv_input_is_available_to_edit(self):
        input_dir = self.runtime_dir("orchestrator", "input")
        (input_dir / "orchestrator_config.yml").write_text(
            "---\nenable_pxe_boot: true\n", encoding="utf-8"
        )
        (input_dir / "pxe_mapping_file.csv").write_text(
            "BMC_IP,HOSTNAME\n192.0.2.10,node01\n", encoding="utf-8"
        )

        output = self.run_cli("edit", "orchestrator")

        self.assertIn("orchestrator_config.yml", output)
        self.assertIn("pxe_mapping_file.csv", output)
        self.assertIn("Customer input checklist", output)
        self.assertIn("[required] pxe_mapping_file.csv", output)

    def test_known_input_file_can_be_opened_directly(self):
        input_dir = self.runtime_dir("orchestrator", "input")
        mapping_file = input_dir / "pxe_mapping_file.csv"
        mapping_file.write_text(
            "BMC_IP,HOSTNAME\n192.0.2.10,node01\n", encoding="utf-8"
        )

        output = self.run_cli(
            "edit",
            "orchestrator",
            "pxe_mapping_file.csv",
            env_overrides={"EDITOR": "/bin/true"},
        )

        self.assertIn(f"Opening {mapping_file} in /bin/true", output)

    def test_direct_edit_failure_has_nonzero_exit_status(self):
        input_dir = self.runtime_dir("orchestrator", "input")
        (input_dir / "pxe_mapping_file.csv").write_text(
            "BMC_IP,HOSTNAME\n192.0.2.10,node01\n", encoding="utf-8"
        )
        env = os.environ.copy()
        env.update(
            {
                "OMNIA_DATA_PATH": str(self.data_path),
                "OMNIA_PROJECT_NAME": "project_default",
                "EDITOR": "editor-that-does-not-exist",
            }
        )

        result = subprocess.run(
            [str(OMNIA_CLI), "edit", "orchestrator", "pxe_mapping_file.csv"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Editor not found", result.stdout + result.stderr)

    def test_edit_completes_staged_input_filenames(self):
        input_dir = self.runtime_dir("orchestrator", "input")
        (input_dir / "pxe_mapping_file.csv").write_text(
            "BMC_IP,HOSTNAME\n192.0.2.10,node01\n", encoding="utf-8"
        )
        (input_dir / "orchestrator_config.yml").write_text(
            "---\nenable_pxe_boot: true\n", encoding="utf-8"
        )

        completion_script = f'''
source "{OMNIA_COMPLETION}"
OMNIA_DATA_PATH="{self.data_path}"
OMNIA_PROJECT_NAME="project_default"
COMP_WORDS=(omnia-cli edit orchestrator p)
COMP_CWORD=3
_omnia_cli_completions
printf '%s\n' "${{COMPREPLY[@]}}"
'''
        result = subprocess.run(
            ["bash", "-c", completion_script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "pxe_mapping_file.csv")

    def test_edit_and_logs_have_command_specific_help(self):
        edit_help = self.run_cli("edit", "--help")
        logs_help = self.run_cli("logs", "--help")

        self.assertIn("Guided domain input editor", edit_help)
        self.assertIn("omnia-cli edit <domain> [file]", edit_help)
        self.assertIn("Domain log browser", logs_help)
        self.assertIn("De-duplicates and sorts all results", logs_help)

    def test_each_domain_shows_customer_input_guidance(self):
        expected_guidance = {
            "repo_manager": "repo_manager_endpoint_config.yml",
            "image_build_manager": "package_groups.yml",
            "orchestrator": "pxe_mapping_file.csv",
            "discovery": "discovery_credentials.yml",
            "telemetry": "bmc_group_data.csv",
            "build_stream": "build_stream_credentials.yml",
            "utils": "collect_pxe.yml",
        }

        for domain_arg, expected_file in expected_guidance.items():
            with self.subTest(domain=domain_arg):
                self.runtime_dir(domain_arg, "input")
                output = self.run_cli("edit", domain_arg)
                self.assertIn("Customer input checklist", output)
                self.assertIn(expected_file, output)

    def test_every_shipped_domain_input_has_a_requirement_label(self):
        domain_args = {
            "repo_manager": "repo_manager",
            "image_build_manager": "image_build_manager",
            "orchestrator": "orchestrator",
            "discovery": "discovery",
            "telemetry": "telemetry",
            "build_stream": "build_stream",
            "utils": "utils",
        }

        for domain, domain_arg in domain_args.items():
            with self.subTest(domain=domain):
                source_dir = REPO_ROOT / "src" / domain / "input"
                input_dir = self.runtime_dir(domain, "input")
                for source_file in source_dir.iterdir():
                    if source_file.is_file():
                        shutil.copy2(source_file, input_dir / source_file.name)

                output = self.run_cli("edit", domain_arg)
                editable_files = output.split("Files available to edit:", 1)[1]
                for source_file in source_dir.iterdir():
                    if not source_file.is_file():
                        continue
                    self.assertRegex(
                        editable_files,
                        re.escape(source_file.name)
                        + r" \[(required|conditional|optional|generated)\]",
                    )

    def test_discovery_csv_files_and_latest_symlink_are_shown(self):
        output_dir = self.runtime_dir("discovery", "output")
        (output_dir / "discovery_status.yml").write_text(
            "---\noverall_status: success\n", encoding="utf-8"
        )
        timestamped = output_dir / "bmc_pxe_mapping_file_20260911.csv"
        timestamped.write_text(
            "BMC_IP,HOSTNAME\n192.0.2.10,node01\n", encoding="utf-8"
        )
        (output_dir / "bmc_pxe_mapping_file.csv").symlink_to(
            timestamped.name
        )
        (output_dir / "bmc_discovery_report_20260911.csv").write_text(
            "BMC_IP,LINK_STATUS\n192.0.2.10,up\n", encoding="utf-8"
        )

        output = self.run_cli("discovery")

        self.assertIn("bmc_pxe_mapping_file_20260911.csv", output)
        self.assertIn("bmc_pxe_mapping_file.csv", output)
        self.assertIn("bmc_discovery_report_20260911.csv", output)

    def test_nested_outputs_are_format_agnostic(self):
        output_dir = self.runtime_dir("utils", "output")
        (output_dir / "utils_status.yml").write_text(
            "---\noverall_status: success\n", encoding="utf-8"
        )
        bundle_dir = output_dir / "collect" / "omnia_logs_20260911"
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "metadata.json").write_text("{}\n", encoding="utf-8")
        (bundle_dir / "omnia_logs_20260911.tar.gz").write_bytes(b"archive")

        output = self.run_cli("utils")

        self.assertIn("collect/omnia_logs_20260911/metadata.json", output)
        self.assertIn(
            "collect/omnia_logs_20260911/omnia_logs_20260911.tar.gz", output
        )

    def test_all_domain_success_states_are_healthy(self):
        for domain, (status_file, status) in DOMAIN_STATUS_FILES.items():
            output_dir = self.runtime_dir(domain, "output")
            (output_dir / status_file).write_text(
                f"---\noverall_status: {status}\n", encoding="utf-8"
            )

        output = self.run_cli("status")

        self.assertIn("build_stream  prepared", output)
        self.assertIn("7/7 domains completed", output)

    def test_utils_check_has_no_fictitious_primary_config(self):
        input_dir = self.runtime_dir("utils", "input")
        (input_dir / "install_os_config.yml").write_text(
            "---\narchitecture: x86_64\n", encoding="utf-8"
        )

        output = self.run_cli("check")

        self.assertNotIn("utils_config.yml", output)
        self.assertIn("No issues found.", output)

    def test_edit_guidance_marks_storage_required_without_ready_or_credential_tag(self):
        self.runtime_dir("orchestrator", "input")

        output = self.run_cli(
            "edit",
            "orchestrator",
            env_overrides={"SYSTEM_ADMIN_NIC_IPV4": "192.0.2.25"},
        )

        self.assertIn("[required] storage_config.yml", output)
        self.assertIn("selected Slurm and Kubernetes clusters", output)
        self.assertIn("SYSTEM_ADMIN_NIC_IPV4=192.0.2.25", output)
        self.assertIn("Run: omnia.sh --run orchestrator", output)
        self.assertNotIn("ready", output.lower())
        self.assertNotIn("--tags credentials", output)

    def test_check_validates_all_required_orchestrator_inputs_and_admin_ip(self):
        input_dir = self.runtime_dir("orchestrator", "input")
        for filename in (
            "orchestrator_config.yml",
            "omnia_config.yml",
            "pxe_mapping_file.csv",
            "storage_config.yml",
            "security_config.yml",
        ):
            (input_dir / filename).write_text("---\n", encoding="utf-8")
        (input_dir / "network_spec.yml").write_text(
            '---\nprimary_oim_admin_ip: "192.0.2.25"\n', encoding="utf-8"
        )

        output = self.run_cli(
            "check", env_overrides={"SYSTEM_ADMIN_NIC_IPV4": "192.0.2.25"}
        )
        self.assertIn("Required input: storage_config.yml", output)
        self.assertIn("primary_oim_admin_ip matches SYSTEM_ADMIN_NIC_IPV4", output)

        (input_dir / "storage_config.yml").unlink()
        result, output = self.invoke_cli(
            "check", env_overrides={"SYSTEM_ADMIN_NIC_IPV4": "192.0.2.26"}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Required input missing: storage_config.yml", output)
        self.assertIn("must match SYSTEM_ADMIN_NIC_IPV4", output)

    def test_check_validates_discovery_admin_ip_against_environment(self):
        input_dir = self.runtime_dir("discovery", "input")
        (input_dir / "discovery_config.yml").write_text("---\n", encoding="utf-8")
        (input_dir / "network_spec.yml").write_text(
            '---\nprimary_oim_admin_ip: "192.0.2.30"\n', encoding="utf-8"
        )

        result, output = self.invoke_cli(
            "check", env_overrides={"SYSTEM_ADMIN_NIC_IPV4": "192.0.2.31"}
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("primary_oim_admin_ip (192.0.2.30)", output)
        self.assertIn("SYSTEM_ADMIN_NIC_IPV4 (192.0.2.31)", output)

    def test_repo_manager_uses_current_output_contract_and_unquotes_certificate(self):
        output_dir = self.runtime_dir("repo_manager", "output")
        cert = self.data_path / "pulp_webserver.crt"
        cert.write_text("certificate\n", encoding="utf-8")
        (output_dir / "repo_status.yml").write_text(
            "---\n"
            'overall_status: "success"\n'
            'cluster_os_type: "rhel"\n'
            "execution_contexts:\n"
            '  - context_id: "rhel_10.0"\n'
            "repo_manager:\n"
            "  certificates:\n"
            f'    server_crt: "{cert}"\n'
            "repositories:\n"
            "  x86_64:\n"
            '    baseos:\n      url: "https://192.0.2.25/repo"\n',
            encoding="utf-8",
        )

        output = self.run_cli("repo_manager")

        self.assertIn(f"Repo manager certificate  ({cert})", output)
        self.assertIn("Execution contexts: 1", output)
        self.assertIn("Repository URLs:    1", output)
        self.assertIn("repo_manager output validation passed", output)
        self.assertNotIn("functional_group_packages", output)
        self.assertNotIn("output is ready", output)

    def test_image_build_manager_validates_and_lists_current_artifacts(self):
        output_dir = self.runtime_dir("image_build_manager", "output")
        status_content = (
            "---\n"
            "overall_status: success\n"
            "image_build_type: image-builder\n"
            "s3_configurations:\n"
            '  endpoint_url: "http://192.0.2.25:9000"\n'
            '  bucket: "boot-images"\n'
            "functional_group_images:\n"
            "  - x86_64:\n"
            "      - functional_group: compute_x86_64\n"
            "        kernel: boot-images/compute/vmlinuz\n"
            "        initrd: boot-images/compute/initramfs.img\n"
            "        image: boot-images/compute/rootfs\n"
        )
        (output_dir / "build_status.yml").write_text(
            status_content, encoding="utf-8"
        )
        snapshot = output_dir / "build_status_2.3_20260911_1734.yml"
        snapshot.write_text(status_content, encoding="utf-8")

        output = self.run_cli("image_build_manager")

        self.assertIn("Build type: image-builder", output)
        self.assertIn("Functional-group images: 1", output)
        self.assertIn(snapshot.name, output)
        self.assertIn("image_build_manager output validation passed", output)

    def test_only_canonical_domain_names_are_accepted(self):
        help_output = self.run_cli("help")
        self.assertIn("repo_manager", help_output)
        self.assertIn("image_build_manager", help_output)
        self.assertIn("build_stream", help_output)
        self.assertNotIn("repo-manager", help_output)

        result, output = self.invoke_cli("repo-manager")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown command: repo-manager", output)

    def test_secondary_utils_status_does_not_replace_canonical_status(self):
        output_dir = self.runtime_dir("utils", "output")
        (output_dir / "install_os_status.yml").write_text(
            "---\nstatus: success\n", encoding="utf-8"
        )

        result, output = self.invoke_cli("utils")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Output artifacts exist but utils_status.yml is missing", output)
        self.assertIn("install_os_status.yml", output)

    def test_empty_staged_output_directories_mean_not_run(self):
        for domain in DOMAIN_STATUS_FILES:
            with self.subTest(domain=domain):
                self.runtime_dir(domain, "output")
                output = self.run_cli(domain)
                self.assertIn(f"No {domain} run output found", output)
                self.assertIn("Outputs created by the relevant flow", output)
                self.assertNotIn("Required status file missing", output)
                self.assertNotIn("✗", output)

        check_output = self.run_cli("check")
        self.assertIn("No run output yet", check_output)
        self.assertIn("No issues found", check_output)

    def test_orchestrator_inventory_can_exist_before_provisioning_status(self):
        output_dir = self.runtime_dir("orchestrator", "output")
        (output_dir / "orchestrator_inventory.yaml").write_text(
            "---\nall: {}\n", encoding="utf-8"
        )
        (output_dir / "bmc_group_data.csv").write_text(
            "BMC_IP,GROUP_NAME\n", encoding="utf-8"
        )

        output = self.run_cli("orchestrator")

        self.assertIn("Provisioning/PXE has not produced orchestrator_status.yml", output)
        self.assertIn("orchestrator_inventory.yaml", output)
        self.assertIn("bmc_group_data.csv", output)

    def test_successful_discovery_requires_its_generated_csv_artifacts(self):
        output_dir = self.runtime_dir("discovery", "output")
        (output_dir / "discovery_status.yml").write_text(
            "---\noverall_status: success\n", encoding="utf-8"
        )

        result, output = self.invoke_cli("discovery")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Timestamped PXE mapping CSV missing", output)
        self.assertIn("Latest PXE mapping missing", output)
        self.assertIn("Timestamped discovery report CSV missing", output)

    def test_completed_orchestrator_pxe_phase_requires_both_reports(self):
        output_dir = self.runtime_dir("orchestrator", "output")
        (output_dir / "orchestrator_status.yml").write_text(
            "---\noverall_status: success\nlast_completed_phase: pxeboot\n",
            encoding="utf-8",
        )
        (output_dir / "pxeboot_status.yml").write_text(
            "---\noverall_status: success\n", encoding="utf-8"
        )

        result, output = self.invoke_cli("orchestrator")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PXE report: pxeboot_status.yml", output)
        self.assertIn("failed_nodes.json missing for completed PXE phase", output)

        (output_dir / "failed_nodes.json").write_text(
            '{"failed_nodes": []}\n', encoding="utf-8"
        )
        output = self.run_cli("orchestrator")
        self.assertIn("PXE report: failed_nodes.json", output)

    def test_domain_specific_status_details_follow_each_output_contract(self):
        cases = {
            "orchestrator": (
                "orchestrator_status.yml",
                "overall_status: success\nlast_completed_phase: provisioning\n"
                "total_nodes: 4\nsuccess_count: 4\nfailure_count: 0\n",
                ("Last completed phase: provisioning", "Nodes: 4/4 successful"),
            ),
            "discovery": (
                "discovery_status.yml",
                "overall_status: success\ndiscovery_mechanism: ome\n"
                "servers_discovered: 4\n",
                ("Discovery mechanism: ome", "Servers discovered: 4"),
            ),
            "telemetry": (
                "telemetry_status.yml",
                "overall_status: success\ntype: deploy\nnamespace: telemetry\n"
                "kube_vip: 192.0.2.40\n",
                ("Flow: deploy", "Kubernetes VIP: 192.0.2.40"),
            ),
            "build_stream": (
                "build_stream_status.yml",
                "overall_status: prepared\n"
                "gitlab_url: https://192.0.2.41:443\n"
                "bsm_api_url: https://192.0.2.42:8010\n",
                ("GitLab URL: https://192.0.2.41:443", "BSM API URL:"),
            ),
            "utils": (
                "utils_status.yml",
                "overall_status: success\nplaybook: install_os\n",
                ("Latest Utils flow: install_os", "utils_status.yml"),
            ),
        }

        for domain, (filename, content, expected_values) in cases.items():
            with self.subTest(domain=domain):
                output_dir = self.runtime_dir(domain, "output")
                (output_dir / filename).write_text(
                    "---\n" + content, encoding="utf-8"
                )
                if domain == "orchestrator":
                    (output_dir / "provisioning_report.yml").write_text(
                        "---\noverall_status: success\n", encoding="utf-8"
                    )
                elif domain == "discovery":
                    timestamped = output_dir / "bmc_pxe_mapping_file_20260911.csv"
                    timestamped.write_text("BMC_IP\n192.0.2.10\n", encoding="utf-8")
                    (output_dir / "bmc_pxe_mapping_file.csv").symlink_to(
                        timestamped.name
                    )
                    (output_dir / "bmc_discovery_report_20260911.csv").write_text(
                        "BMC_IP\n192.0.2.10\n", encoding="utf-8"
                    )
                output = self.run_cli(domain)
                for expected in expected_values:
                    self.assertIn(expected, output)

    def test_logs_are_globally_sorted_limited_and_source_labeled(self):
        runtime_dir = self.data_path / "discovery" / "log" / "project_default"
        runtime_dir.mkdir(parents=True)
        output_dir = self.runtime_dir("discovery", "output") / "nested"
        output_dir.mkdir()

        old_log = runtime_dir / "old.log"
        newest_log = runtime_dir / "newest.log"
        recent_log = output_dir / "recent.log"
        for path in (old_log, newest_log, recent_log):
            path.write_text("test log\n", encoding="utf-8")
        os.utime(old_log, (2_000_000_000, 2_000_000_000))
        os.utime(recent_log, (2_000_000_010, 2_000_000_010))
        os.utime(newest_log, (2_000_000_020, 2_000_000_020))

        output = self.run_cli(
            "logs",
            "discovery",
            "--limit",
            "2",
            env_overrides={
                "OMNIA_ANSIBLE_LOG_PATH": str(self.data_path / "ansible-logs")
            },
        )

        self.assertIn("showing 2 of 3, newest first", output)
        self.assertIn("[runtime] project_default/newest.log", output)
        self.assertIn("[output] nested/recent.log", output)
        self.assertNotIn("old.log", output)


if __name__ == "__main__":
    unittest.main()
