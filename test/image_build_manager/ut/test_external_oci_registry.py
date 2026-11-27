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
# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-CONFIG-001.5, CG-INPUT-001.5, CG-CRYPTO-001.6
# ****
"""Unit tests for the optional external OCI registry (Harbor) push.

Covers the config schema and semantic rules, the Vault credential keys, the
build_status.yml oci section and the static wiring of the precheck/publish
tasks. No registry, Ansible run or build is required.
"""

# Pytest injects fixtures by reusing fixture function names as test arguments,
# and descriptive test names make per-test docstrings redundant.
# pylint: disable=missing-function-docstring,redefined-outer-name

import copy
import importlib.util
import json
import logging
import secrets
from pathlib import Path

import ansible.module_utils
import jinja2
import pytest
import yaml
from ansible.plugins.filter.core import FilterModule

REPO_ROOT = Path(__file__).resolve().parents[3]
IBM_ROOT = REPO_ROOT / "src/image_build_manager"
MODULE_UTILS_DIR = IBM_ROOT / "plugins/module_utils"
if str(MODULE_UTILS_DIR) not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.append(str(MODULE_UTILS_DIR))

SCHEMA_DIR = MODULE_UTILS_DIR / "input_validation/schema"
ENGINE_PATH = MODULE_UTILS_DIR / "input_validation/core/validation_engine.py"
VALIDATOR_PATH = (
    MODULE_UTILS_DIR / "input_validation/validators/image_build_config_validator.py"
)
ROLE_DIR = IBM_ROOT / "roles/build_os_images"
LOGGER = logging.getLogger(__name__)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


ENGINE = _load_module("image_build_validation_engine_oci", ENGINE_PATH)
CONFIG_VALIDATOR = _load_module("image_build_config_validator_oci", VALIDATOR_PATH)


def _schema(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _validate(data, schema_name):
    errors = []
    ENGINE.schema(data, _schema(schema_name), "input.yml", errors, LOGGER)
    return errors


@pytest.fixture
def registry():
    """Return the Harbor demo section with genuine types."""
    return {
        "registry_type": "harbor",
        "registry_protocol": "https",
        "registry_hostname": "100.10.1.202",
        "registry_port": 443,
        "namespace_name": "hpc-images",
        "auth_type": "basic",
        "tls_verify": False,
    }


@pytest.fixture
def valid_config(registry):
    """Return a complete valid config that enables the external registry."""
    return {
        "repo_manager_output_path": "",
        "s3_configurations": {"provider": "minio", "endpoint_url": ""},
        "functional_groups_source": "catalog",
        "build_image": {
            "max_parallel": 0,
            "build_timeout": 7200,
            "force_rebuild": False,
            "backup_s3_images": False,
            "repo_ssl_verify": True,
        },
        "external_oci_registry": registry,
    }


def test_external_registry_section_is_optional_and_valid(valid_config):
    assert _validate(valid_config, "image_build_config.json") == []
    assert CONFIG_VALIDATOR.validate(valid_config) == []
    without = {k: v for k, v in valid_config.items() if k != "external_oci_registry"}
    assert _validate(without, "image_build_config.json") == []
    assert CONFIG_VALIDATOR.validate(without) == []
    minimal = copy.deepcopy(valid_config)
    for optional in ("registry_port", "tls_verify"):
        del minimal["external_oci_registry"][optional]
    assert _validate(minimal, "image_build_config.json") == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("registry_type", "quay"),
        ("registry_protocol", "ftp"),
        ("registry_hostname", "harbor example.com"),
        ("registry_hostname", "harbor.example.com/path"),
        ("registry_port", 0),
        ("registry_port", "443"),
        ("namespace_name", "HPC-Images"),
        ("namespace_name", "a/../b"),
        ("namespace_name", ""),
        ("auth_type", "token"),
        ("tls_verify", "false"),
    ],
)
def test_external_registry_rejects_invalid_values(valid_config, field, value):
    valid_config["external_oci_registry"][field] = value
    assert _validate(valid_config, "image_build_config.json"), (field, value)


@pytest.mark.parametrize(
    "field", ["registry_type", "registry_protocol", "registry_hostname", "namespace_name", "auth_type"]
)
def test_external_registry_required_fields_and_unknown_keys(valid_config, field):
    del valid_config["external_oci_registry"][field]
    assert _validate(valid_config, "image_build_config.json")
    valid_config["external_oci_registry"][field] = "harbor"
    valid_config["external_oci_registry"]["registry_password"] = "must-not-be-accepted"
    assert _validate(valid_config, "image_build_config.json")


def test_http_registry_requires_tls_verify_false(valid_config):
    section = valid_config["external_oci_registry"]
    section.update(registry_protocol="http", registry_port=80, tls_verify=True)
    errors = CONFIG_VALIDATOR.validate(valid_config)
    assert any("http" in error and "tls_verify" in error for error in errors)
    del section["tls_verify"]
    assert CONFIG_VALIDATOR.validate(valid_config), "tls_verify defaults to true"
    section["tls_verify"] = False
    assert CONFIG_VALIDATOR.validate(valid_config) == []


def test_https_with_tls_verify_false_is_a_warning(valid_config, caplog):
    with caplog.at_level(logging.WARNING):
        errors = CONFIG_VALIDATOR.validate(valid_config, LOGGER)
    assert errors == []
    assert "TLS verification is disabled" in caplog.text


def test_hostname_rejects_empty_labels(valid_config):
    valid_config["external_oci_registry"]["registry_hostname"] = "harbor..example.com"
    errors = CONFIG_VALIDATOR.validate(valid_config)
    assert any("registry_hostname" in error for error in errors)


@pytest.mark.parametrize(
    "field,value",
    [
        ("retry_count", 6),
        ("retry_count", -1),
        ("retry_count", "2"),
        ("timeout_seconds", 29),
        ("timeout_seconds", 3601),
        ("timeout_seconds", "300"),
        ("tag_policy", "skip_if_same_digest"),
        ("tag_policy", "always"),
        ("ca_cert_path", ""),
        ("ca_cert_path", "relative/registry-ca.pem"),
    ],
)
def test_external_registry_field_level_limits_reject_invalid_values(valid_config, field, value):
    valid_config["external_oci_registry"][field] = value
    assert _validate(valid_config, "image_build_config.json"), (field, value)


def test_external_registry_field_level_limits_accept_documented_values(valid_config, tmp_path):
    ca_file = tmp_path / "registry-ca.pem"
    ca_file.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    section = valid_config["external_oci_registry"]
    for values in (
        {
            "ca_cert_path": str(ca_file),
            "tag_policy": "fail_if_exists",
            "retry_count": 5,
            "timeout_seconds": 3600,
        },
        {"tag_policy": "overwrite", "retry_count": 0, "timeout_seconds": 30},
    ):
        section.update(values)
        assert _validate(valid_config, "image_build_config.json") == [], values
        assert CONFIG_VALIDATOR.validate(valid_config) == [], values


def test_ca_cert_path_must_be_an_existing_readable_file(valid_config, tmp_path):
    section = valid_config["external_oci_registry"]
    section["ca_cert_path"] = str(tmp_path / "missing-ca.pem")
    assert any("ca_cert_path" in error for error in CONFIG_VALIDATOR.validate(valid_config))
    section["ca_cert_path"] = str(tmp_path)
    assert any("ca_cert_path" in error for error in CONFIG_VALIDATOR.validate(valid_config)), (
        "a directory is not a CA bundle"
    )


@pytest.mark.parametrize("value", ["sometimes", "true", 1])
def test_cleanup_flag_rejects_non_boolean_values(valid_config, value):
    valid_config["delete_local_registry_images_after_build"] = value
    assert _validate(valid_config, "image_build_config.json"), value


def test_cleanup_flag_is_optional_and_accepts_a_boolean(valid_config):
    assert _validate(valid_config, "image_build_config.json") == []
    valid_config["delete_local_registry_images_after_build"] = True
    assert _validate(valid_config, "image_build_config.json") == []
    assert CONFIG_VALIDATOR.validate(valid_config) == []


def test_cleanup_flag_without_harbor_warns_that_images_are_not_retained(valid_config, caplog):
    without = {k: v for k, v in valid_config.items() if k != "external_oci_registry"}
    without["delete_local_registry_images_after_build"] = True
    with caplog.at_level(logging.WARNING):
        errors = CONFIG_VALIDATOR.validate(without, LOGGER)
    assert errors == []
    assert "the OCI image is not retained after this run" in caplog.text
    caplog.clear()
    valid_config["delete_local_registry_images_after_build"] = True
    with caplog.at_level(logging.WARNING):
        CONFIG_VALIDATOR.validate(valid_config, LOGGER)
    assert "not retained" not in caplog.text


def test_registry_credentials_are_optional_vault_keys():
    schema = _schema("image_build_credentials.json")
    assert "oci_registry_username" in schema["properties"]
    assert "oci_registry_password" in schema["properties"]
    assert not {"oci_registry_username", "oci_registry_password"} & set(schema["required"])
    base = {"s3_secret_key": "minio-secret-123"}
    assert _validate(base, "image_build_credentials.json") == []
    robot = dict(
        base,
        oci_registry_username="robot$omnia+demo",
        oci_registry_password=secrets.token_urlsafe(16),
    )
    assert _validate(robot, "image_build_credentials.json") == []

    template = (IBM_ROOT / "roles/collect_build_credentials/templates/image_build_credential.j2")
    keys = yaml.safe_load(template.read_text(encoding="utf-8"))
    assert keys["oci_registry_username"] == "" and keys["oci_registry_password"] == ""
    role_vars = yaml.safe_load(
        (IBM_ROOT / "roles/collect_build_credentials/vars/main.yml").read_text(encoding="utf-8")
    )
    conditional = {
        field.get("username") or field.get("password"): field["condition"]
        for field in role_vars["image_build_cred_config"]["conditional_mandatory"]
    }
    for key in ("oci_registry_username", "oci_registry_password"):
        assert "external_oci_registry is defined" in conditional[key]


def test_input_template_keeps_external_registry_off_by_default():
    text = (IBM_ROOT / "input/image_build_config.yml").read_text(encoding="utf-8")
    assert "external_oci_registry" not in yaml.safe_load(text)
    commented = [line for line in text.splitlines() if line.startswith("# external_oci_registry:")]
    assert commented, "the commented example must document the section"
    uncommented = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "oci_registry_password" not in uncommented
    assert "oci_registry_username" not in uncommented


def _render_status(results):
    env = jinja2.Environment(undefined=jinja2.Undefined, keep_trailing_newline=True)
    ansible_filters = FilterModule().filters()
    env.filters.update({name: ansible_filters[name] for name in ("to_json", "dict2items")})
    template = env.from_string(
        (ROLE_DIR / "templates/build_status.yml.j2").read_text(encoding="utf-8")
    )
    images = {
        "x86_64": [
            {"functional_group": "slurm_node_rhel_10_2_x86_64", "kernel": "boot-images/a/vmlinuz",
             "initrd": "boot-images/a/initramfs.img", "image": "boot-images/a/rootfs.squashfs"},
            {"functional_group": "login_node_rhel_10_2_x86_64", "kernel": "boot-images/b/vmlinuz",
             "initrd": "boot-images/b/initramfs.img", "image": "boot-images/b/rootfs.squashfs"},
        ]
    }
    hostvars = {"localhost": {"oci_publish_results": results} if results is not None else {}}
    rendered = template.render(
        build_completed_images=images, status_image_build_type="image-thrillhouse",
        s3_endpoint="http://172.10.5.11:9000", admin_nic_ip="172.10.5.11", s3_configurations={"bucket": "boot-images"},
        hostvars=hostvars,
    )
    return yaml.safe_load(rendered)


def test_build_status_oci_section_is_written_only_for_published_groups():
    result = {
        "registry_mode": "external",
        "reference": "172.10.5.11:5000/oim/img:abcd1234",
        "external_reference": "100.10.1.202/hpc-images/oim/img:abcd1234",
        "digest": "sha256:" + "a" * 64,
        "architecture": "amd64",
        "tags": ["10.2", "2.3.0.0", "abcd1234"],
        "annotations": {"io.dell.omnia.published_by": "buildstream",
                        "org.opencontainers.image.vendor": "Dell Technologies"},
    }
    status = _render_status({"slurm_node_rhel_10_2_x86_64": result})
    slurm, login = status["functional_group_images"][0]["x86_64"]
    assert slurm["kernel"] == "boot-images/a/vmlinuz" and slurm["image"].endswith("rootfs.squashfs")
    assert slurm["oci"]["registry_mode"] == "external"
    assert slurm["oci"]["external_reference"] == result["external_reference"]
    assert slurm["oci"]["digest"] == result["digest"]
    assert slurm["oci"]["tags"] == result["tags"]
    assert slurm["oci"]["annotations"] == result["annotations"]
    assert "oci" not in login
    assert status["overall_status"] == "success"


def test_build_status_is_unchanged_without_external_registry():
    for results in (None, {}):
        status = _render_status(results)
        for entry in status["functional_group_images"][0]["x86_64"]:
            assert set(entry) == {"functional_group", "kernel", "initrd", "image"}


def test_build_status_records_a_sanitized_push_error_only():
    failed = {"registry_mode": "local", "reference": "172.10.5.11:5000/oim/img:abcd1234",
              "digest": "sha256:" + "b" * 64, "architecture": "amd64",
              "error": 'push failed: "denied" requested access'}
    status = _render_status({"login_node_rhel_10_2_x86_64": failed})
    login = status["functional_group_images"][0]["x86_64"][1]
    assert login["oci"]["registry_mode"] == "local"
    assert "external_reference" not in login["oci"]
    assert login["oci"]["error"] == failed["error"]


def test_push_tasks_are_wired_and_never_expose_credentials():
    main = yaml.safe_load((ROLE_DIR / "tasks/main.yml").read_text(encoding="utf-8"))
    names = [task["name"] for task in main]
    precheck = names.index("Precheck the external OCI registry before any build work")
    publish = names.index("Package and publish OCI images to the external registry")
    assert precheck == 0 < names.index("Install SELinux policy module before using Podman")
    assert publish > names.index("Merge with existing build_completed_images")
    for index in (precheck, publish):
        assert main[index]["when"] == "ext_oci_enabled | bool"

    texts = {
        name: (ROLE_DIR / "tasks" / name).read_text(encoding="utf-8")
        for name in ("precheck_oci_registry.yml", "check_oci_registry_endpoint.yml",
                     "check_harbor_project.yml", "write_session_regctl_config.yml",
                     "publish_oci_images.yml", "publish_oci_image.yml")
    }
    publish_text = texts["publish_oci_images.yml"]
    assert "write_session_regctl_config.yml" in publish_text
    session_text = texts["write_session_regctl_config.yml"]
    assert 'mode: "0600"' in session_text and "ansible.builtin.tempfile" in session_text
    assert all("ca_path:" in texts[name] for name in ("check_oci_registry_endpoint.yml", "check_harbor_project.yml"))
    assert "state: absent" in publish_text and "always:" in publish_text
    for task_text in texts.values():
        assert "regctl registry login" not in task_text
        assert "ansible.builtin.shell" not in task_text
    for name, task_text in texts.items():
        for task in _walk_tasks(yaml.safe_load(task_text)):
            command = task.get("ansible.builtin.command")
            if command:
                assert "oci_registry_" not in str(command), (name, task["name"])
            if "ansible.builtin.uri" in task or "oci_registry_password" in str(task):
                assert task.get("no_log") is True, (name, task["name"])
    assert "--annotation" in texts["publish_oci_image.yml"]
    assert "REGCTL_CONFIG" in texts["publish_oci_image.yml"]
    assert texts["publish_oci_image.yml"].count("rescue:") == 1


def _walk_tasks(tasks):
    """Yield every leaf task, descending into block/rescue/always."""
    for task in tasks:
        nested = [section for section in ("block", "rescue", "always") if section in task]
        for section in nested:
            yield from _walk_tasks(task[section])
        if not nested:
            yield task
