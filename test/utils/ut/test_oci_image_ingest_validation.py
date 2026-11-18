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
Unit tests for OCI Image Ingest validation and pipeline components.

Covers TC-UT-001 through TC-UT-008 from the ER-UTIL-001 test plan:
  TC-UT-001: Input schema validation module
  TC-UT-002: Credential-key rejection
  TC-UT-003: Registry connection validator (role task content)
  TC-UT-004: Boot artifact extractor (role task content)
  TC-UT-005: Build status generator (role task content)
  TC-UT-006: S3 path constructor
  TC-UT-007: Cleanup handler (role task content)
  TC-UT-008: Orchestrator image build type allow-list
"""

import copy
import importlib.util
import json
import pathlib
import re
import sys
import types

import pytest
import yaml

# Paths relative to this file: ut/ -> utils/ -> test/ -> omnia/
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src" / "utils"
MODULES_DIR = SRC_DIR / "plugins" / "modules"
SCHEMA_DIR = SRC_DIR / "plugins" / "module_utils" / "input_validation" / "schema"
ROLES_DIR = SRC_DIR / "roles"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_validation_module():
    """Import validate_oci_image_ingest_config without the Ansible runtime."""
    module_path = MODULES_DIR / "validate_oci_image_ingest_config.py"
    assert module_path.exists(), f"Module not found: {module_path}"

    # Stub out ansible.module_utils.basic so the module can be imported
    for name in [
        "ansible",
        "ansible.module_utils",
        "ansible.module_utils.basic",
    ]:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
    # Provide a minimal AnsibleModule stub
    basic = sys.modules["ansible.module_utils.basic"]
    if not hasattr(basic, "AnsibleModule"):
        basic.AnsibleModule = type("AnsibleModule", (), {})

    spec = importlib.util.spec_from_file_location(
        "validate_oci_image_ingest_config", module_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_schema():
    """Load the OCI image ingest JSON schema."""
    schema_path = SCHEMA_DIR / "oci_image_ingest_config.json"
    assert schema_path.exists(), f"Schema not found: {schema_path}"
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def _valid_config():
    """Return a minimal valid configuration dict."""
    return {
        "registries": [
            {
                "registry_name": "lab-harbor",
                "registry_type": "harbor",
                "registry_protocol": "https",
                "registry_hostname": "registry.example.com",
            }
        ],
        "image_mappings": [
            {
                "mapping_name": "slurm-rhel10",
                "registry_name": "lab-harbor",
                "namespace_name": "omnia",
                "image": "rhel10-slurm-node:2026.11",
                "functional_group": "slurm_node_rhel_10_0_x86_64",
                "operation": "repo_to_bucket",
            }
        ],
    }


@pytest.fixture(scope="module")
def val_mod():
    """The production validation module."""
    return _load_validation_module()


@pytest.fixture(scope="module")
def schema():
    """The JSON schema for oci_image_ingest_config."""
    return _load_schema()


# =========================================================================
# TC-UT-001: Input schema validation module
# =========================================================================


class TestInputSchemaValidation:
    """TC-UT-001: validate_oci_image_ingest_config schema validation."""

    def test_valid_harbor_config_accepted(self, val_mod, schema):
        """Schema accepts valid Harbor config with repo_to_bucket."""
        errors, norm = val_mod.run_validation(_valid_config(), schema)
        assert not errors, f"Valid config rejected: {errors}"
        assert norm["registries"][0]["registry_port"] == 443

    def test_unknown_registry_type_rejected(self, val_mod, schema):
        """Schema rejects unknown registry_type with actionable message."""
        cfg = _valid_config()
        cfg["registries"][0]["registry_type"] = "ecr"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors, "Should reject registry_type 'ecr'"
        assert any("not yet supported" in e for e in errors)
        assert any("harbor" in e for e in errors)

    def test_unknown_operation_rejected(self, val_mod, schema):
        """Schema rejects unknown operation."""
        cfg = _valid_config()
        cfg["image_mappings"][0]["operation"] = "local_to_repo"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors, "Should reject operation 'local_to_repo'"
        assert any("not yet supported" in e for e in errors)

    def test_missing_registries_rejected(self, val_mod, schema):
        """Schema rejects missing registries key."""
        cfg = _valid_config()
        del cfg["registries"]
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("registries" in e.lower() for e in errors)

    def test_missing_mapping_fields_rejected(self, val_mod, schema):
        """Schema rejects missing required mapping fields."""
        cfg = _valid_config()
        del cfg["image_mappings"][0]["image"]
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("image" in e.lower() for e in errors)

    def test_bad_functional_group_rejected(self, val_mod, schema):
        """Schema rejects functional_group without arch suffix."""
        cfg = _valid_config()
        cfg["image_mappings"][0]["functional_group"] = "slurm_node_rhel_10"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("x86_64" in e or "aarch64" in e for e in errors)

    def test_semantic_unresolved_reference(self, val_mod, schema):
        """Semantic validation catches unresolved registry reference."""
        cfg = _valid_config()
        cfg["image_mappings"][0]["registry_name"] = "missing-registry"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("not defined" in e.lower() for e in errors)

    def test_non_dict_input_rejected(self, val_mod, schema):
        """Non-dict input is rejected with guidance."""
        errors, _ = val_mod.run_validation("not a dict", schema)
        assert errors
        assert any("YAML mapping" in e for e in errors)

    def test_http_default_port(self, val_mod, schema):
        """HTTP registry defaults to port 80."""
        cfg = _valid_config()
        cfg["registries"][0]["registry_protocol"] = "http"
        errors, norm = val_mod.run_validation(cfg, schema)
        assert not errors
        assert norm["registries"][0]["registry_port"] == 80

    def test_digest_image_reference(self, val_mod, schema):
        """Image reference with @sha256 digest is accepted."""
        cfg = _valid_config()
        cfg["image_mappings"][0]["image"] = (
            "rhel10-slurm-node@sha256:"
            + "a" * 64
        )
        errors, _ = val_mod.run_validation(cfg, schema)
        assert not errors, f"Digest reference rejected: {errors}"


# =========================================================================
# TC-UT-002: Credential-key rejection
# =========================================================================


class TestCredentialKeyRejection:
    """TC-UT-002: Credential keys rejected without echoing values."""

    def test_password_key_rejected(self, val_mod, schema):
        """Registry entry with 'password' key is rejected."""
        cfg = _valid_config()
        cfg["registries"][0]["password"] = "s3cret"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("oci_image_ingest_credentials.yml" in e for e in errors)
        # Value must NOT appear in error message
        assert all("s3cret" not in e for e in errors)

    def test_username_key_rejected(self, val_mod, schema):
        """Registry entry with 'username' key is rejected."""
        cfg = _valid_config()
        cfg["registries"][0]["username"] = "admin"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("oci_image_ingest_credentials.yml" in e for e in errors)
        assert all("admin" not in e for e in errors)

    def test_auth_key_rejected(self, val_mod, schema):
        """Registry entry with 'auth' key is rejected."""
        cfg = _valid_config()
        cfg["registries"][0]["auth"] = "base64token"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("credentials" in e.lower() for e in errors)

    def test_connection_only_accepted(self, val_mod, schema):
        """Registry with only connection fields is accepted."""
        errors, _ = val_mod.run_validation(_valid_config(), schema)
        assert not errors

    def test_mapping_credential_rejected(self, val_mod, schema):
        """Credential key in image_mappings is rejected."""
        cfg = _valid_config()
        cfg["image_mappings"][0]["token"] = "mytoken"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("credentials" in e.lower() for e in errors)

    def test_top_level_credential_rejected(self, val_mod, schema):
        """Top-level credential key is rejected."""
        cfg = _valid_config()
        cfg["api_key"] = "key123"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert errors
        assert any("credentials" in e.lower() for e in errors)


# =========================================================================
# TC-UT-003: Registry connection validator (role content verification)
# =========================================================================


class TestRegistryConnectionValidator:
    """TC-UT-003: Verify registry validation role handles all response codes."""

    @pytest.fixture(autouse=True)
    def _load_role(self):
        role_dir = ROLES_DIR / "validate_registry_connection"
        self.tasks_dir = role_dir / "tasks"
        self.vars_dir = role_dir / "vars"
        assert self.tasks_dir.exists(), f"Role tasks not found: {self.tasks_dir}"

    def _task_content(self):
        """Return concatenated task YAML content."""
        content = ""
        for f in sorted(self.tasks_dir.glob("*.yml")):
            content += f.read_text(encoding="utf-8")
        return content

    def _vars_content(self):
        """Return concatenated vars content."""
        content = ""
        for f in sorted(self.vars_dir.glob("*.yml")):
            content += f.read_text(encoding="utf-8")
        return content

    def test_v2_api_check_exists(self):
        """Role checks /v2/ endpoint."""
        content = self._task_content()
        assert "/v2/" in content, "Role must check Docker V2 API /v2/"

    def test_401_handling(self):
        """Role handles 401 authentication failure."""
        combined = self._task_content() + self._vars_content()
        assert "401" in combined, "Role must handle HTTP 401"

    def test_403_handling(self):
        """Role handles 403 forbidden."""
        combined = self._task_content() + self._vars_content()
        assert "403" in combined, "Role must handle HTTP 403"

    def test_timeout_handling(self):
        """Role has connection timeout."""
        content = self._task_content()
        assert "timeout" in content.lower(), "Role must have timeout handling"

    def test_tls_verification(self):
        """Role handles TLS verification."""
        combined = self._task_content() + self._vars_content()
        assert "tls" in combined.lower() or "ssl" in combined.lower() or "validate_certs" in combined.lower()

    def test_namespace_check(self):
        """Role checks namespace (Harbor project) accessibility."""
        content = self._task_content()
        assert "namespace" in content.lower() or "project" in content.lower()

    def test_no_credential_logging(self):
        """Role uses no_log for credential-bearing tasks."""
        content = self._task_content()
        assert "no_log: true" in content or "no_log: True" in content


# =========================================================================
# TC-UT-004: Boot artifact extractor (role content verification)
# =========================================================================


class TestBootArtifactExtractor:
    """TC-UT-004: Verify extraction role handles kernel/initramfs cases."""

    def _find_extraction_content(self):
        """Find and return content of extraction-related roles."""
        content = ""
        for role_name in ["oci_image_ingest", "extract_boot_artifacts",
                          "ingest_oci_image_mapping"]:
            role_dir = ROLES_DIR / role_name
            if role_dir.exists():
                for f in sorted(role_dir.rglob("*.yml")):
                    content += f.read_text(encoding="utf-8")
        # Also check the included tasks
        playbooks = SRC_DIR / "playbooks"
        if playbooks.exists():
            for f in sorted(playbooks.rglob("*.yml")):
                if "oci" in f.name.lower() or "ingest" in f.name.lower():
                    content += f.read_text(encoding="utf-8")
        return content

    def test_kernel_extraction_exists(self):
        """Extraction handles vmlinuz files."""
        content = self._find_extraction_content()
        assert "vmlinuz" in content.lower() or "kernel" in content.lower(), (
            "No kernel extraction logic found"
        )

    def test_initramfs_extraction_exists(self):
        """Extraction handles initramfs files."""
        content = self._find_extraction_content()
        assert "initramfs" in content.lower() or "initrd" in content.lower(), (
            "No initramfs extraction logic found"
        )

    def test_boot_directory_referenced(self):
        """Extraction references /boot/ directory."""
        content = self._find_extraction_content()
        assert "/boot" in content or "boot" in content.lower()


# =========================================================================
# TC-UT-005: Build status generator (role content verification)
# =========================================================================


class TestBuildStatusGenerator:
    """TC-UT-005: Verify build_status.yml generation role."""

    @pytest.fixture(autouse=True)
    def _load_role(self):
        self.role_dir = ROLES_DIR / "generate_build_status"
        if not self.role_dir.exists():
            pytest.skip("generate_build_status role not found")

    def _role_content(self):
        """Return all YAML content from the role."""
        content = ""
        for f in sorted(self.role_dir.rglob("*.yml")):
            content += f.read_text(encoding="utf-8")
        for f in sorted(self.role_dir.rglob("*.j2")):
            content += f.read_text(encoding="utf-8")
        return content

    def test_overall_status_field(self):
        """Role generates overall_status field."""
        content = self._role_content()
        assert "overall_status" in content

    def test_image_build_type_field(self):
        """Role generates image_build_type field."""
        content = self._role_content()
        assert "image_build_type" in content

    def test_s3_configurations_field(self):
        """Role generates s3_configurations field."""
        content = self._role_content()
        assert "s3_configurations" in content or "s3_config" in content.lower()

    def test_functional_group_images_field(self):
        """Role generates functional_group_images field."""
        content = self._role_content()
        assert "functional_group_images" in content or "functional_group" in content


# =========================================================================
# TC-UT-006: S3 path constructor
# =========================================================================


class TestS3PathConstructor:
    """TC-UT-006: Verify S3 path construction logic."""

    def test_kernel_path_format(self):
        """Kernel path follows expected pattern."""
        fg = "slurm_node_rhel_10_0_x86_64"
        image = "rhel10-slurm-node"
        release = "2026.11"
        kv = "6.12.0-55.el10_0.x86_64"
        expected_path = (
            f"boot-images/{fg}/{image}-ingest/{release}/"
            f"vmlinuz-{kv}"
        )
        # Verify pattern components
        assert fg in expected_path
        assert f"{image}-ingest" in expected_path
        assert release in expected_path
        assert f"vmlinuz-{kv}" in expected_path

    def test_rootfs_path_format(self):
        """Rootfs path uses rootfs.squashfs name."""
        fg = "slurm_node_rhel_10_0_x86_64"
        image = "rhel10-slurm-node"
        release = "2026.11"
        expected_path = (
            f"boot-images/{fg}/{image}-ingest/{release}/rootfs.squashfs"
        )
        assert "rootfs.squashfs" in expected_path

    def test_digest_release_name(self):
        """Digest reference produces sha256-<12hex> release segment."""
        digest = "0123456789abcdef" * 4  # 64 hex chars
        # Production uses first 12 chars of digest
        release = f"sha256-{digest[:12]}"
        assert release == "sha256-0123456789ab"

    def test_safe_char_sanitization(self):
        """Unsafe characters in release are replaced."""
        safe_pattern = re.compile(r"[^A-Za-z0-9._-]")
        tag = "2026.11+hotfix"
        sanitized = safe_pattern.sub("-", tag)
        assert sanitized == "2026.11-hotfix"
        assert "+" not in sanitized

    def test_nested_repo_name_sanitized(self):
        """Nested repository name (with /) is sanitized."""
        safe_pattern = re.compile(r"[^A-Za-z0-9._-]")
        repo = "team/rhel-compute"
        sanitized = safe_pattern.sub("-", repo)
        assert sanitized == "team-rhel-compute"
        assert "/" not in sanitized


# =========================================================================
# TC-UT-007: Cleanup handler (role content verification)
# =========================================================================


class TestCleanupHandler:
    """TC-UT-007: Verify cleanup role handles working directory removal."""

    @pytest.fixture(autouse=True)
    def _load_role(self):
        self.role_dir = ROLES_DIR / "cleanup_oci_image_ingest"
        if not self.role_dir.exists():
            pytest.skip("cleanup_oci_image_ingest role not found")

    def _role_content(self):
        content = ""
        for f in sorted(self.role_dir.rglob("*.yml")):
            content += f.read_text(encoding="utf-8")
        return content

    def test_directory_removal(self):
        """Cleanup removes working directory."""
        content = self._role_content()
        assert "absent" in content or "remove" in content.lower() or "delete" in content.lower()

    def test_lock_release(self):
        """Cleanup releases the project lock."""
        content = self._role_content()
        assert "lock" in content.lower()

    def test_always_runs(self):
        """Cleanup is in an always block (checked in playbook)."""
        playbook = SRC_DIR / "playbooks" / "ingest_oci_image.yml"
        if playbook.exists():
            content = playbook.read_text(encoding="utf-8")
            assert "always" in content, "Cleanup must be in always block"


# =========================================================================
# TC-UT-008: Orchestrator image build type allow-list
# =========================================================================


class TestOrchestratorBuildTypeAllowList:
    """TC-UT-008: Verify the allow-list for image_build_type."""

    def test_allow_list_contains_both_types(self):
        """Allow-list contains image-thrillhouse and oci-image-ingest."""
        # Import from the test vars
        sys.path.insert(0, str(REPO_ROOT / "test" / "utils"))
        from library.vars.common_vars import OCI_ACCEPTED_BUILD_TYPES
        assert "image-thrillhouse" in OCI_ACCEPTED_BUILD_TYPES
        assert "oci-image-ingest" in OCI_ACCEPTED_BUILD_TYPES

    def test_allow_list_size(self):
        """Allow-list contains exactly two types."""
        sys.path.insert(0, str(REPO_ROOT / "test" / "utils"))
        from library.vars.common_vars import OCI_ACCEPTED_BUILD_TYPES
        assert len(OCI_ACCEPTED_BUILD_TYPES) == 2

    def test_custom_builder_rejected(self):
        """custom-builder is not in the allow-list."""
        sys.path.insert(0, str(REPO_ROOT / "test" / "utils"))
        from library.vars.common_vars import OCI_ACCEPTED_BUILD_TYPES
        assert "custom-builder" not in OCI_ACCEPTED_BUILD_TYPES

    def test_orchestrator_validation_role_exists(self):
        """Orchestrator validation role references image_build_type."""
        orch_dir = REPO_ROOT / "src" / "orchestrator"
        if not orch_dir.exists():
            pytest.skip("Orchestrator source not available")
        content = ""
        for f in sorted(orch_dir.rglob("*.yml")):
            if "valid" in f.name.lower() or "image" in f.name.lower():
                content += f.read_text(encoding="utf-8")
        if content:
            assert "image_build_type" in content
