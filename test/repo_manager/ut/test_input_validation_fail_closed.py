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

"""Negative tests: Repo Manager input validation must fail closed.

The validate_input module runs through the ansible CLI from the collection
root so the module and its module_utils resolve exactly as in production.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import jsonschema
import yaml

from source_loader import REPO_MANAGER_ROOT

MODULE_UTILS = REPO_MANAGER_ROOT / "plugins" / "module_utils"
SCHEMA_DIR = MODULE_UTILS / "input_validation" / "schema"
RESULT_PATTERN = re.compile(r"\|\s*(\w+)!?\s*=>\s*(\{.*\})\s*$", re.DOTALL)


def _run_validate_input(project_dir, tags, module_utils=MODULE_UTILS):
    """Run validate_input for a project directory and return its JSON result."""
    args = {
        "omnia_base_dir": str(project_dir.parent),
        "project_name": project_dir.name,
        "input_project_dir": str(project_dir),
        "module_utils_path": str(module_utils),
        "csv_file_path": "",
        "tag_names": tags,
    }
    env = dict(
        os.environ,
        REPO_MANAGER_BASE_DIR=str(REPO_MANAGER_ROOT),
        OMNIA_DATA_PATH=str(project_dir.parent),
        REPO_MANAGER_DATA_PATH=str(project_dir.parent),
        ANSIBLE_LOG_PATH=os.devnull,
    )
    proc = subprocess.run(
        ["ansible", "localhost", "-m", "validate_input", "-a", json.dumps(args)],
        cwd=REPO_MANAGER_ROOT, env=env, capture_output=True, text=True,
        check=False, timeout=120,
    )
    match = RESULT_PATTERN.search(proc.stdout)
    if not match:
        raise AssertionError(f"No module result in output:\n{proc.stdout}\n{proc.stderr}")
    result = json.loads(match.group(2))
    result["failed"] = match.group(1) == "FAILED"
    return result


@unittest.skipIf(shutil.which("ansible") is None, "ansible CLI not installed")
class ValidateInputTagFailClosedTests(unittest.TestCase):
    """Unknown, empty, or contract-less tags never report validation success."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name) / "project_test"
        self.project.mkdir()
        (self.project / "repo_manager_endpoint_config.yml").write_text(
            "pulp_server_port: 2225\n", encoding="utf-8"
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_unknown_tag_alone_is_rejected(self):
        """A typo tag must fail instead of validating zero files."""
        result = _run_validate_input(self.project, ["iucghewqiug"])
        self.assertTrue(result.get("failed"))
        self.assertIn("Unknown tag(s) provided: ['iucghewqiug']", result["msg"])

    def test_known_tag_with_unknown_tag_is_rejected(self):
        """A typo mixed with a valid tag must still fail."""
        result = _run_validate_input(self.project, ["endpoint", "iucghewqiug"])
        self.assertTrue(result.get("failed"))
        self.assertIn("Unknown tag(s) provided: ['iucghewqiug']", result["msg"])

    def test_empty_tag_list_is_rejected(self):
        """No tags means nothing is validated, which must not pass."""
        result = _run_validate_input(self.project, [])
        self.assertTrue(result.get("failed"))
        self.assertIn("No input validation contract", result["msg"])

    def test_operation_only_tag_is_rejected(self):
        """An operation tag alone has no input contract and validates nothing."""
        result = _run_validate_input(self.project, ["download"])
        self.assertTrue(result.get("failed"))
        self.assertIn("No input validation contract", result["msg"])

    def test_operation_tag_with_validation_tag_validates_files(self):
        """Operation tags are tolerated when a validation tag is also selected."""
        result = _run_validate_input(self.project, ["download", "endpoint"])
        self.assertFalse(result.get("failed"), result)
        self.assertFalse(result["validation_failed"], result)
        self.assertEqual(
            [Path(path).name for path in result["valid_files"]],
            ["repo_manager_endpoint_config.yml"],
        )

    def test_valid_tag_with_missing_required_file_fails(self):
        """A mapped, required input file that is absent is a failure, not a skip."""
        (self.project / "repo_manager_endpoint_config.yml").unlink()
        (self.project / "placeholder.yml").write_text("a: 1\n", encoding="utf-8")
        result = _run_validate_input(self.project, ["endpoint"])
        self.assertTrue(result.get("failed"))
        self.assertIn("repo_manager_endpoint_config file not found", result["msg"])

    def test_missing_schema_for_mapped_file_fails(self):
        """A mapped file whose schema is missing can never be reported valid."""
        empty_utils = Path(self._tmp.name) / "module_utils"
        (empty_utils / "input_validation" / "schema").mkdir(parents=True)
        result = _run_validate_input(self.project, ["endpoint"], empty_utils)
        self.assertTrue(result.get("failed"))
        self.assertRegex(
            result["msg"], r"repo_manager_endpoint_config\.json does not exist"
        )
        self.assertNotIn("valid_files", result)


class ValidationTagScopeTests(unittest.TestCase):
    """A narrowed validation contract cannot leak into later plays."""

    def test_deploy_pulp_endpoint_contract_is_scoped_to_its_include(self):
        """deploy_pulp must not persist omnia_run_tags for validate_config."""
        playbook = yaml.safe_load(
            (REPO_MANAGER_ROOT / "playbooks" / "deploy" / "deploy_pulp.yml").read_text(
                encoding="utf-8"
            )
        )
        tasks = [task for play in playbook for task in play.get("tasks", [])]
        for task in tasks:
            fact = task.get("ansible.builtin.set_fact") or task.get("set_fact") or {}
            self.assertNotIn("omnia_run_tags", fact, task.get("name"))
        includes = [
            task for task in tasks
            if str((task.get("ansible.builtin.include_role") or {}).get("name", ""))
            .endswith("roles/validate_input")
        ]
        self.assertEqual(len(includes), 1)
        self.assertEqual(includes[0]["vars"]["omnia_run_tags"], ["endpoint"])


class CredentialFileValidationContractTests(unittest.TestCase):
    """repo_manager_config_credentials.yml is mapped to an L1 schema."""

    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (SCHEMA_DIR / "repo_manager_config_credentials.json").read_text(
                encoding="utf-8"
            )
        )

    def _errors(self, document):
        validator = jsonschema.Draft7Validator(self.schema)
        return list(validator.iter_errors(document))

    def test_credential_file_is_mapped_for_every_repo_config_tag(self):
        """Every tag that validates repo_manager_config also validates credentials."""
        # pylint: disable=import-outside-toplevel,import-error
        from ansible.module_utils.input_validation.core import config

        credentials = config.files["repo_manager_config_credentials"]
        for tag, names in config.input_file_inventory.items():
            if config.files["repo_manager_config"] in names:
                self.assertIn(credentials, names, tag)
        self.assertIn(credentials, config.optional_files)
        self.assertFalse(set(config.operation_tags) & set(config.input_file_inventory))

    def test_schema_accepts_document_written_by_credential_collection(self):
        """The shape persisted by collect_repo_credentials is valid."""
        document = {
            "pulp_username": "admin",
            "pulp_password": "pulp-pass",
            "docker_username": "",
            "docker_password": "",
            "registry_credentials": {
                "/vault/registry": {
                    "registry": "internal",
                    "origin": {"scheme": "https", "host": "reg.local", "port": 5000},
                    "username": "user",
                    "password": "pass",
                }
            },
        }
        self.assertEqual(self._errors(document), [])

    def test_schema_rejects_missing_pulp_password(self):
        """A credential file without the mandatory Pulp password is invalid."""
        self.assertTrue(self._errors({"pulp_username": "admin"}))

    def test_schema_rejects_unknown_top_level_key(self):
        """Unexpected plaintext keys are not silently accepted."""
        document = {"pulp_username": "a", "pulp_password": "b", "registry_pass": "x"}
        self.assertTrue(self._errors(document))

    def test_schema_rejects_incomplete_registry_credential(self):
        """A registry credential record must carry username and password."""
        document = {
            "pulp_username": "a",
            "pulp_password": "b",
            "registry_credentials": {"/vault/r": {"registry": "r"}},
        }
        self.assertTrue(self._errors(document))



class SupportedTagsContractTests(unittest.TestCase):
    """The playbook tag guard must accept every tag a caller can select."""

    @staticmethod
    def _supported_tags():
        vars_file = REPO_MANAGER_ROOT / "roles" / "repo_manager_setup" / "vars" / "main.yml"
        return set(yaml.safe_load(vars_file.read_text(encoding="utf-8"))["supported_tags"])

    def test_supported_tags_cover_public_and_play_tags(self):
        """omnia.sh public tags and repo_manager.yml play tags all pass the guard."""
        omnia_sh = (REPO_MANAGER_ROOT.parent / "main" / "omnia.sh").read_text(encoding="utf-8")
        block = omnia_sh.split("Public tags by domain", 1)[1]
        public = set(re.search(r"^\s+repo_manager:\s+(.+)$", block, re.M).group(1).split())
        playbook = yaml.safe_load(
            (REPO_MANAGER_ROOT / "playbooks" / "repo_manager.yml").read_text(encoding="utf-8")
        )
        play_tags = set()
        for play in playbook:
            tags = play.get("tags") or []
            play_tags.update([tags] if isinstance(tags, str) else tags)
        expected = (public | play_tags) - {"always", "never"}
        self.assertEqual(expected - self._supported_tags(), set())

    def test_internal_pulp_tag_is_rejected(self):
        """'pulp' selects the never-tagged cleanup play, so it is not public."""
        self.assertNotIn("pulp", self._supported_tags())

    def test_run_tag_modifiers_are_supported(self):
        """Tags the roles read from ansible_run_tags must pass the tag guard."""
        pattern = re.compile(r"['\"]([a-z][a-z0-9_]+)['\"]\s+in\s+\(?\s*ansible_run_tags")
        referenced = set()
        for path in REPO_MANAGER_ROOT.rglob("*.yml"):
            referenced.update(pattern.findall(path.read_text(encoding="utf-8")))
        self.assertEqual(referenced - {"all"} - self._supported_tags(), set())

    def test_guard_tags_are_accepted_by_validate_input(self):
        """A tag the guard accepts must not be rejected by validate_input."""
        tree = ast.parse((MODULE_UTILS / "input_validation" / "core" / "config.py").read_text(
            encoding="utf-8"))
        values = {
            node.targets[0].id: node.value for node in tree.body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        }
        accepted = {element.value for element in values["operation_tags"].elts}
        accepted |= {key.value for key in values["input_file_inventory"].keys}
        self.assertEqual(self._supported_tags() - accepted, set())


if __name__ == "__main__":
    unittest.main()
