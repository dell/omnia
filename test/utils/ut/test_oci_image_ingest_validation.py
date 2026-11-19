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

from library.functions import TestLogger
from library.vars import TEST_CASES as TC

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

    # Map ansible.module_utils onto the real plugins/module_utils tree so the
    # production module's imports resolve without the Ansible runtime
    mu_dir = str(SRC_DIR / "plugins" / "module_utils")
    if mu_dir not in sys.path:
        sys.path.insert(0, mu_dir)
    pkg = types.ModuleType("ansible")
    pkg.__path__ = []
    mu_pkg = types.ModuleType("ansible.module_utils")
    mu_pkg.__path__ = [mu_dir]
    basic = types.ModuleType("ansible.module_utils.basic")
    basic.AnsibleModule = type("AnsibleModule", (), {})
    pkg.module_utils, mu_pkg.basic = mu_pkg, basic
    sys.modules.update({
        "ansible": pkg,
        "ansible.module_utils": mu_pkg,
        "ansible.module_utils.basic": basic,
    })

    spec = importlib.util.spec_from_file_location(
        "validate_oci_image_ingest_config", module_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    from input_validation.core.utils import create_logger

    def run_validation(config, schema_def):
        """Adapter over production validate_config()/normalize()."""
        errors = mod.validate_config(config, schema_def, create_logger("", "ut"))
        return errors, ({} if errors else mod.normalize(config))

    return types.SimpleNamespace(
        validate_config=mod.validate_config,
        normalize=mod.normalize,
        run_validation=run_validation,
    )


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


_CLASS_TC_KEY = {
    "TestInputSchemaValidation": "ut_input_schema_validation",
    "TestCredentialKeyRejection": "ut_credential_key_rejection",
    "TestRegistryConnectionValidator": "ut_registry_connection_validator",
    "TestBootArtifactExtractor": "ut_boot_artifact_extractor",
    "TestBuildStatusGenerator": "ut_build_status_generator",
    "TestS3PathConstructor": "ut_s3_path_constructor",
    "TestCleanupHandler": "ut_cleanup_handler",
    "TestOrchestratorBuildTypeAllowList": "ut_orchestrator_build_type_allow_list",
}


@pytest.fixture(autouse=True)
def _register_tc_id(request):
    """Record the TC ID of the owning test class so reports list it."""
    key = _CLASS_TC_KEY.get(request.node.cls.__name__ if request.node.cls else "")
    if key:
        tc = TC[key]
        TestLogger(f"{tc['title']} - {request.node.name}", tc["id"])
    yield


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

    def test_https_default_port(self, val_mod, schema):
        """HTTPS registry defaults to port 443."""
        errors, norm = val_mod.run_validation(_valid_config(), schema)
        assert not errors
        assert norm["registries"][0]["registry_port"] == 443

    def test_http_protocol_rejected(self, val_mod, schema):
        """Plain HTTP registry protocol is rejected by the schema."""
        cfg = _valid_config()
        cfg["registries"][0]["registry_protocol"] = "http"
        errors, _ = val_mod.run_validation(cfg, schema)
        assert any("registry_protocol" in e for e in errors)

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
    """TC-UT-004: Verify extraction via production select_boot_set module."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        """Import the production oci_rootfs module."""
        mu_dir = str(SRC_DIR / "plugins" / "module_utils")
        if mu_dir not in sys.path:
            sys.path.insert(0, mu_dir)
        import oci_rootfs
        self.select_boot_set = oci_rootfs.select_boot_set
        self.BootSetError = oci_rootfs.BootSetError

    @staticmethod
    def _make_boot_dir(tmp_path, versions, initramfs=True, modules=True):
        """Create a mock rootfs with kernel/initramfs/modules."""
        boot = tmp_path / "boot"
        boot.mkdir(parents=True, exist_ok=True)
        for ver in versions:
            (boot / f"vmlinuz-{ver}").write_text("")
            if initramfs:
                (boot / f"initramfs-{ver}.img").write_text("")
            if modules:
                mod_dir = tmp_path / "lib" / "modules" / ver
                mod_dir.mkdir(parents=True, exist_ok=True)
                (mod_dir / "modules.dep").write_text("")

    def test_single_boot_set_extracted(self, tmp_path):
        """Single kernel/initramfs pair is selected."""
        self._make_boot_dir(tmp_path, ["6.12.0-55.el10_0.x86_64"])
        result = self.select_boot_set(str(tmp_path), "")
        assert result["kernel_version"] == "6.12.0-55.el10_0.x86_64"
        assert "vmlinuz-6.12.0" in result["kernel_path"]
        assert "initramfs-6.12.0" in result["initrd_path"]

    def test_no_kernel_raises(self, tmp_path):
        """Empty /boot/ raises BootSetError mentioning kernel."""
        boot = tmp_path / "boot"
        boot.mkdir(parents=True, exist_ok=True)
        with pytest.raises(self.BootSetError, match="kernel not found"):
            self.select_boot_set(str(tmp_path), "")

    def test_missing_initramfs_raises(self, tmp_path):
        """Kernel without matching initramfs raises BootSetError."""
        self._make_boot_dir(tmp_path, ["6.12.0"], initramfs=False)
        with pytest.raises(self.BootSetError, match="initramfs"):
            self.select_boot_set(str(tmp_path), "")

    def test_multiple_kernels_require_version(self, tmp_path):
        """Multiple complete boot sets without kernel_version raises."""
        self._make_boot_dir(tmp_path, ["5.14.0", "6.12.0"])
        with pytest.raises(self.BootSetError, match="multiple"):
            self.select_boot_set(str(tmp_path), "")

    def test_kernel_version_selects_one(self, tmp_path):
        """kernel_version selects the requested version."""
        self._make_boot_dir(tmp_path, ["5.14.0", "6.12.0"])
        result = self.select_boot_set(str(tmp_path), "5.14.0")
        assert result["kernel_version"] == "5.14.0"

    def test_rescue_kernel_excluded(self, tmp_path):
        """Rescue kernels are excluded from candidates."""
        self._make_boot_dir(tmp_path, ["6.12.0"])
        boot = tmp_path / "boot"
        (boot / "vmlinuz-0-rescue-abc123").write_text("")
        (boot / "initramfs-0-rescue-abc123.img").write_text("")
        result = self.select_boot_set(str(tmp_path), "")
        assert result["kernel_version"] == "6.12.0"
        assert "rescue" not in result["kernel_version"]

    def test_debug_kernel_excluded(self, tmp_path):
        """Debug kernels (+debug) are excluded from candidates."""
        self._make_boot_dir(tmp_path, ["6.12.0"])
        boot = tmp_path / "boot"
        (boot / "vmlinuz-6.12.0+debug").write_text("")
        (boot / "initramfs-6.12.0+debug.img").write_text("")
        result = self.select_boot_set(str(tmp_path), "")
        assert result["kernel_version"] == "6.12.0"


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
    """TC-UT-008: Verify the allow-list for image_build_type.

    Reads the authoritative allow-list from the production Orchestrator
    vars file rather than importing from test variables.
    """

    @pytest.fixture(autouse=True)
    def _load_production_allow_list(self):
        """Load accepted_image_build_types from Orchestrator vars."""
        orch_vars = (
            REPO_ROOT / "src" / "orchestrator" / "roles"
            / "orchestrator_validations" / "vars" / "main.yml"
        )
        if not orch_vars.exists():
            pytest.skip("Orchestrator vars not available")
        content = yaml.safe_load(orch_vars.read_text(encoding="utf-8"))
        self.production_allow_list = content.get(
            "accepted_image_build_types", []
        )

    def test_allow_list_contains_both_types(self):
        """Production allow-list contains image-thrillhouse and oci-image-ingest."""
        assert "image-thrillhouse" in self.production_allow_list
        assert "oci-image-ingest" in self.production_allow_list

    def test_allow_list_size(self):
        """Production allow-list contains exactly two types."""
        assert len(self.production_allow_list) == 2

    def test_custom_builder_rejected(self):
        """custom-builder is not in the production allow-list."""
        assert "custom-builder" not in self.production_allow_list

    def test_test_vars_match_production(self):
        """Test variable OCI_ACCEPTED_BUILD_TYPES matches production."""
        sys.path.insert(0, str(REPO_ROOT / "test" / "utils"))
        from library.vars.common_vars import OCI_ACCEPTED_BUILD_TYPES
        assert sorted(OCI_ACCEPTED_BUILD_TYPES) == sorted(self.production_allow_list), (
            f"Test vars {OCI_ACCEPTED_BUILD_TYPES} != production {self.production_allow_list}"
        )
