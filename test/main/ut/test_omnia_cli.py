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
import shlex
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
OMNIA_CLI = REPO_ROOT / "src" / "main" / "omnia-cli"
OMNIA_SH = REPO_ROOT / "src" / "main" / "omnia.sh"
OMNIA_COMPLETION = REPO_ROOT / "src" / "main" / "omnia-bash-completion"
TELEMETRY_PLAYBOOK = REPO_ROOT / "src" / "telemetry" / "playbooks" / "telemetry.yml"
DEPLOY_SINKS_PLAYBOOK = (
    REPO_ROOT
    / "src"
    / "telemetry"
    / "playbooks"
    / "deploy"
    / "sinks"
    / "deploy_sinks.yml"
)
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

    def invoke_omnia_run_domain(self, *args):
        """Run run_domain with Ansible mocked and return its forwarded arguments."""
        venv_dir = self.data_path / "venv"
        activate_file = venv_dir / "bin" / "activate"
        activate_file.parent.mkdir(parents=True, exist_ok=True)
        activate_file.write_text("# Test activation shim\n", encoding="utf-8")

        quoted_args = " ".join(shlex.quote(arg) for arg in args)
        shell_script = f'''
source {shlex.quote(str(OMNIA_SH))}
ansible-playbook() {{ printf 'ANSIBLE_ARG=%s\\n' "$@"; }}
OMNIA_VENV_PATH={shlex.quote(str(venv_dir))}
run_domain telemetry {quoted_args}
'''
        env = os.environ.copy()
        env["OMNIA_DATA_PATH"] = str(self.data_path)
        env["OMNIA_PROJECT_NAME"] = "project_default"
        result = subprocess.run(
            ["bash", "-c", shell_script],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        output = ANSI_ESCAPE.sub("", result.stdout + result.stderr)
        forwarded_args = [
            line.removeprefix("ANSIBLE_ARG=")
            for line in output.splitlines()
            if line.startswith("ANSIBLE_ARG=")
        ]
        return result, output, forwarded_args

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
        output_help = self.run_cli("output", "--help")
        logs_help = self.run_cli("logs", "--help")

        self.assertIn("Guided domain input editor", edit_help)
        self.assertIn("omnia-cli edit <domain> [file]", edit_help)
        self.assertIn("Domain output browser", output_help)
        self.assertIn("omnia-cli output <domain> [file]", output_help)
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

    def test_utils_guide_only_lists_utils_owned_slurm_input(self):
        self.runtime_dir("utils", "input")

        output = self.run_cli("edit", "utils")

        self.assertIn("[optional] slurm_config_util_config.yml", output)
        self.assertNotIn("[conditional] omnia_config.yml", output)
        self.assertNotIn("[conditional] storage_config.yml", output)
        self.assertNotIn("[conditional] nodes_slurm.yaml", output)
        self.assertNotIn("[conditional] pxe_mapping_file.csv", output)

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
        (output_dir / "orchestrator_inventory.yml").write_text(
            "---\nall: {}\n", encoding="utf-8"
        )
        (output_dir / "bmc_group_data.csv").write_text(
            "BMC_IP,GROUP_NAME\n", encoding="utf-8"
        )

        output = self.run_cli("orchestrator")

        self.assertIn("Provisioning/PXE has not produced orchestrator_status.yml", output)
        self.assertIn("orchestrator_inventory.yml", output)
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

    def test_output_command_lists_and_prints_text_artifact(self):
        output_dir = self.runtime_dir("telemetry", "output")
        status_file = output_dir / "telemetry_status.yml"
        status_file.write_text(
            "---\noverall_status: success\ntype: deploy\n", encoding="utf-8"
        )

        output = self.run_cli(
            "output", "telemetry", "telemetry_status.yml"
        )

        self.assertIn("telemetry Output Files", output)
        self.assertIn("overall_status: success", output)
        self.assertIn("type: deploy", output)

    def test_output_command_honors_domain_data_path_override(self):
        telemetry_root = self.data_path / "custom-telemetry"
        output_dir = telemetry_root / "output" / "project_default"
        output_dir.mkdir(parents=True)
        (output_dir / "telemetry_status.yml").write_text(
            "---\noverall_status: success\n", encoding="utf-8"
        )

        output = self.run_cli(
            "output",
            "telemetry",
            "telemetry_status.yml",
            env_overrides={"TELEMETRY_DATA_PATH": str(telemetry_root)},
        )

        self.assertIn(str(output_dir), output)
        self.assertIn("overall_status: success", output)

    def test_project_completion_honors_domain_data_path_override(self):
        telemetry_root = self.data_path / "custom-telemetry"
        (telemetry_root / "output" / "custom-project").mkdir(parents=True)
        completion_script = f'''
source "{OMNIA_COMPLETION}"
OMNIA_DATA_PATH="{self.data_path}"
TELEMETRY_DATA_PATH="{telemetry_root}"
COMP_WORDS=(omnia-cli status --project custom)
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
        self.assertEqual(result.stdout.strip(), "custom-project")

    def test_stage_order_warning_honors_domain_data_path_override(self):
        repo_manager_root = self.data_path / "custom-repo-manager"
        status_dir = repo_manager_root / "output" / "project_default"
        status_dir.mkdir(parents=True)
        (status_dir / "repo_status.yml").write_text(
            "---\noverall_status: success\n", encoding="utf-8"
        )
        env = os.environ.copy()
        env.update(
            {
                "OMNIA_DATA_PATH": str(self.data_path),
                "OMNIA_PROJECT_NAME": "project_default",
                "REPO_MANAGER_DATA_PATH": str(repo_manager_root),
            }
        )
        script = f'source "{OMNIA_SH}"; warn_stage_order image_build_manager'

        result = subprocess.run(
            ["bash", "-c", script],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("WARNING", result.stdout)

    def test_output_command_rejects_symlink_outside_domain_output(self):
        output_dir = self.runtime_dir("telemetry", "output")
        outside_file = self.data_path / "outside.yml"
        outside_file.write_text("secret: value\n", encoding="utf-8")
        (output_dir / "outside.yml").symlink_to(outside_file)

        result, output = self.invoke_cli(
            "output", "telemetry", "outside.yml"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to open an output link outside", output)
        self.assertNotIn("secret: value", output)

    def test_output_completion_lists_nested_artifact(self):
        output_dir = self.runtime_dir("utils", "output") / "collect"
        output_dir.mkdir()
        (output_dir / "metadata.json").write_text("{}\n", encoding="utf-8")

        completion_script = f'''
source "{OMNIA_COMPLETION}"
OMNIA_DATA_PATH="{self.data_path}"
OMNIA_PROJECT_NAME="project_default"
COMP_WORDS=(omnia-cli output utils coll)
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
        self.assertEqual(result.stdout.strip(), "collect/metadata.json")

    def test_omnia_sh_completion_supports_telemetry_extra_vars_and_utils_tags(self):
        completion_script = f'''
source "{OMNIA_COMPLETION}"
COMP_WORDS=(omnia.sh -r telemetry --tags cleanup -e delete)
COMP_CWORD=6
_omnia_sh_completions
printf 'telemetry:%s\n' "${{COMPREPLY[@]}}"
COMP_WORDS=(omnia.sh -r utils --tags slurm_)
COMP_CWORD=4
_omnia_sh_completions
printf 'utils:%s\n' "${{COMPREPLY[@]}}"
'''
        result = subprocess.run(
            ["bash", "-c", completion_script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("telemetry:delete_sinks_volume=true", result.stdout)
        self.assertIn("telemetry:delete_sinks_volume=false", result.stdout)
        self.assertIn("utils:slurm_config_backup", result.stdout)
        self.assertIn("utils:slurm_config_cleanup", result.stdout)
        self.assertIn("utils:slurm_config_rollback", result.stdout)

    def test_omnia_sh_completion_supports_telemetry_deploy_sinks(self):
        completion_script = f'''
source "{OMNIA_COMPLETION}"
COMP_WORDS=(omnia.sh -r telemetry --tags deploy_sinks -e v)
COMP_CWORD=6
_omnia_sh_completions
printf '%s\n' "${{COMPREPLY[@]}}"
'''
        result = subprocess.run(
            ["bash", "-c", completion_script],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("victoria_metrics", result.stdout)
        self.assertIn("victoria_logs", result.stdout)

    def test_telemetry_playbook_exposes_deploy_sinks_tag_with_all_defaults(self):
        entrypoint = TELEMETRY_PLAYBOOK.read_text(encoding="utf-8")
        deploy_sinks = DEPLOY_SINKS_PLAYBOOK.read_text(encoding="utf-8")

        self.assertRegex(
            entrypoint,
            r"import_playbook: deploy/sinks/deploy_sinks\.yml\s+tags:\s+- never\s+- deploy_sinks",
        )
        self.assertRegex(
            deploy_sinks,
            r"sinks_default:\s+- kafka\s+- victoria_metrics\s+- victoria_logs",
        )

    def test_deploy_sinks_without_selector_forwards_no_sink_override(self):
        result, output, forwarded = self.invoke_omnia_run_domain(
            "--tags", "deploy_sinks"
        )

        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(forwarded[1:], ["--tags", "deploy_sinks"])

    def test_deploy_sinks_single_selector_is_normalized(self):
        result, output, forwarded = self.invoke_omnia_run_domain(
            "--tags", "deploy_sinks", "-e", "kafka"
        )

        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(forwarded[-2:], ["-e", 'sinks=["kafka"]'])

    def test_deploy_sinks_csv_selector_is_normalized(self):
        result, output, forwarded = self.invoke_omnia_run_domain(
            "--tags",
            "deploy_sinks",
            "-e",
            "kafka,victoria_metrics,victoria_logs",
        )

        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(
            forwarded[-2:],
            ["-e", 'sinks=["kafka","victoria_metrics","victoria_logs"]'],
        )

    def test_deploy_sinks_repeated_selectors_are_merged_and_deduplicated(self):
        result, output, forwarded = self.invoke_omnia_run_domain(
            "--tags",
            "deploy_sinks",
            "-e",
            "kafka,victoria_logs",
            "-e",
            "kafka",
        )

        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(
            forwarded[-2:], ["-e", 'sinks=["kafka","victoria_logs"]']
        )

    def test_deploy_sinks_preserves_standard_extra_vars(self):
        result, output, forwarded = self.invoke_omnia_run_domain(
            "--tags", "deploy_sinks", "-e", "project_name=test_project", "-e", "kafka"
        )

        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(
            forwarded[-4:],
            ["-e", "project_name=test_project", "-e", 'sinks=["kafka"]'],
        )

    def test_deploy_sinks_rejects_invalid_selector(self):
        result, output, forwarded = self.invoke_omnia_run_domain(
            "--tags", "deploy_sinks", "-e", "not_a_sink"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(forwarded, [])
        self.assertIn("Invalid telemetry sink 'not_a_sink'", output)
        self.assertIn("kafka, victoria_metrics, victoria_logs", output)

    def test_catalog_selection_copies_variant_and_setup_preserves_it(self):
        catalog_target = self.data_path / "catalog" / "catalog_rhel.json"
        selected_source = (
            REPO_ROOT
            / "src/main/samples/catalogs/10.0/slurm_x86_64_no_vast.json"
        )
        env = os.environ.copy()
        env.update(
            {
                "OMNIA_DATA_PATH": str(self.data_path),
                "CATALOG_FILE_PATH": str(catalog_target),
            }
        )
        script = (
            f'source "{OMNIA_SH}"; '
            "select_catalog 10.0/slurm_x86_64_no_vast.json; copy_catalog"
        )

        result = subprocess.run(
            ["bash", "-c", script],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(catalog_target.read_bytes(), selected_source.read_bytes())
        self.assertIn("Catalog selected and activated successfully", result.stdout)
        self.assertIn("Preserving existing active catalog", result.stdout)
        self.assertIn(
            "Name:        Omnia Slurm Catalog - RHEL 10.0 x86_64 (No VAST)",
            result.stdout,
        )
        self.assertIn(
            "Description: Slurm HPC catalog for RHEL 10.0 x86_64",
            result.stdout,
        )
        self.assertIn("Workloads: Slurm", result.stdout)
        self.assertIn("Architectures: x86_64", result.stdout)
        self.assertIn("VAST client: not included", result.stdout)
        self.assertIn("Functional layers: 4", result.stdout)

    def test_select_catalog_public_option_activates_exact_selector(self):
        catalog_target = self.data_path / "catalog" / "catalog_rhel.json"
        selected_source = (
            REPO_ROOT
            / "src/main/samples/catalogs/10.2/service_k8s_x86_64.json"
        )
        env = os.environ.copy()
        env.update(
            {
                "OMNIA_DATA_PATH": str(self.data_path),
                "CATALOG_FILE_PATH": str(catalog_target),
            }
        )

        script = (
            f'source "{OMNIA_SH}"; '
            "source_omnia_env() { :; }; "
            'main "$@"'
        )
        result = subprocess.run(
            [
                "bash",
                "-c",
                script,
                "omnia.sh",
                "--select-catalog",
                "10.2/service_k8s_x86_64.json",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(catalog_target.read_bytes(), selected_source.read_bytes())
        output = ANSI_ESCAPE.sub("", result.stdout)
        self.assertIn("Selected catalog: 10.2/service_k8s_x86_64.json", output)
        self.assertIn("Workloads: service Kubernetes", output)

    def test_catalog_list_describes_and_analyzes_each_variant(self):
        script = f'source "{OMNIA_SH}"; list_catalogs'

        result = subprocess.run(
            ["bash", "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        catalog_sources = [REPO_ROOT / "src/main/samples/catalog_rhel.json"]
        catalog_sources.extend(
            sorted((REPO_ROOT / "src/main/samples/catalogs").rglob("*.json"))
        )
        self.assertEqual(
            result.stdout.count("Description:"), len(catalog_sources)
        )
        self.assertEqual(result.stdout.count("Analysis:"), len(catalog_sources))
        self.assertNotIn("unavailable", result.stdout.lower())
        self.assertIn("1) default", result.stdout)
        self.assertIn(
            "Description: Full mixed deployment catalog for RHEL 10.0",
            result.stdout,
        )
        self.assertIn("RHEL 10.0", result.stdout)
        self.assertIn("Workloads: Slurm + service Kubernetes", result.stdout)
        self.assertIn("Architectures: x86_64 + aarch64", result.stdout)
        self.assertIn("VAST client: not included", result.stdout)
        self.assertIn("10.2/slurm_x86_64.json", result.stdout)
        self.assertIn("VAST client: included", result.stdout)

    def test_catalog_replacement_requires_confirmation_and_keeps_backup(self):
        catalog_target = self.data_path / "catalog" / "catalog_rhel.json"
        catalog_target.parent.mkdir()
        original_catalog = b'{"catalog": "original"}\n'
        catalog_target.write_bytes(original_catalog)
        env = os.environ.copy()
        env.update(
            {
                "OMNIA_DATA_PATH": str(self.data_path),
                "CATALOG_FILE_PATH": str(catalog_target),
            }
        )
        script = (
            f'source "{OMNIA_SH}"; '
            "select_catalog 10.0/slurm_x86_64_no_vast.json"
        )

        result = subprocess.run(
            ["bash", "-c", script],
            input="yes\n",
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        backups = list(catalog_target.parent.glob("catalog_rhel.json.backup.*"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original_catalog)
        self.assertNotEqual(catalog_target.read_bytes(), original_catalog)


if __name__ == "__main__":
    unittest.main()
