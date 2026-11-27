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
Image Build Validate — external registry and cleanup-flag configuration (TC-FVT-007).

Runs ``image_build_manager.yml --tags validate`` against the active target
configuration and against temporary input copies. The copies are selected with
``input_project_dir`` and ``log_dir`` extra variables, so the target input and
log directories are read but not modified.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import yaml

from library.functions import TestLogger, is_local_execution, run_playbook
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG

PROJECT_NAME = os.environ.get("OMNIA_PROJECT_NAME", "project_default")
IMAGE_BUILD_DATA_PATH = os.environ.get("IMAGE_BUILD_MANAGER_DATA_PATH") or os.path.join(
    os.environ.get("OMNIA_DATA_PATH", "/opt/omnia"), "image_build_manager"
)
TARGET_INPUT_DIR = Path(IMAGE_BUILD_DATA_PATH) / "input" / PROJECT_NAME
CA_PLACEHOLDER = "@CA_FILE@"

# (case id, registry overrides or None for an absent section, top-level overrides,
#  expected success, expected output fragments, expected log fragment)
VARIANT_CASES = [
    ("valid_all_new_keys",
     {"ca_cert_path": CA_PLACEHOLDER, "tag_policy": "fail_if_exists",
      "retry_count": 2, "timeout_seconds": 300},
     {"delete_local_registry_images_after_build": False}, True, [], None),
    ("absent_section", None, {}, True, [], None),
    ("tag_policy_invalid", {"tag_policy": "skip_if_same_digest"}, {}, False,
     ["tag_policy"], None),
    ("retry_count_out_of_range", {"retry_count": 6}, {}, False, ["retry_count"], None),
    ("timeout_below_minimum", {"timeout_seconds": 29}, {}, False, ["timeout_seconds"], None),
    ("ca_cert_path_missing", {"ca_cert_path": "/nonexistent/registry-ca.pem"}, {}, False,
     ["ca_cert_path"], None),
    ("http_with_tls_verify", {"registry_protocol": "http", "registry_port": 80,
     "tls_verify": True}, {}, False, ["accepted only with tls_verify"], None),
    ("http_tls_verify_false_warns", {"registry_protocol": "http", "registry_port": 80,
     "tls_verify": False}, {}, True, [], "TLS verification is disabled"),
    ("auth_type_token", {"auth_type": "token"}, {}, False, ["auth_type"], None),
    ("registry_type_quay", {"registry_type": "quay"}, {}, False, ["registry_type"], None),
    ("cleanup_flag_not_boolean", {}, {"delete_local_registry_images_after_build": "sometimes"},
     False, ["delete_local_registry_images_after_build"], None),
    ("cleanup_flag_without_harbor_warns", None,
     {"delete_local_registry_images_after_build": True}, True, [],
     "the OCI image is not retained after this run"),
]


def _write_variant(root: Path, registry: Optional[Dict[str, Any]], top: Dict[str, Any]) -> Path:
    input_dir = root / "input" / PROJECT_NAME
    input_dir.mkdir(parents=True)
    shutil.copy(TARGET_INPUT_DIR / "package_groups.yml", input_dir / "package_groups.yml")
    config = yaml.safe_load((TARGET_INPUT_DIR / "image_build_config.yml").read_text(encoding="utf-8"))
    config["functional_groups_source"] = "config"
    if registry is None:
        config.pop("external_oci_registry", None)
    else:
        config["external_oci_registry"] = {**config.get("external_oci_registry", {}), **registry}
    config.update(top)
    (input_dir / "image_build_config.yml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )
    return input_dir


def _read_logs(log_dir: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(log_dir.rglob("*.log")))


@pytest.mark.sanity
@pytest.mark.order(5)
def test_target_config_validates_on_oim():
    """Validate the active target configuration with the validate tag."""
    tc = TC["oci_target_config"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(tag="validate")

    if result["success"]:
        tl.passed(LOG["oci_target_config_ok"])
    else:
        tl.failed(LOG["oci_target_config_failed"], result.get("error", "See playbook output"))

    assert result["success"], result["output"][-2000:]


@pytest.mark.sanity
@pytest.mark.order(6)
@pytest.mark.parametrize(
    "case_id,registry,top,expect_ok,expected_output,expected_log",
    VARIANT_CASES,
    ids=[case[0] for case in VARIANT_CASES],
)
def test_external_registry_variant(tmp_path, case_id, registry, top, expect_ok,
                                   expected_output, expected_log):
    """Validate one external registry or cleanup-flag variant through the validate tag."""
    if not is_local_execution():
        pytest.skip("variant input directories are written on the local OIM")
    tc = TC["oci_registry_variants"]
    tl = TestLogger(f"{tc['title']} ({case_id})", tc["id"])

    ca_file = tmp_path / "registry-ca.pem"
    ca_file.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    if registry and registry.get("ca_cert_path") == CA_PLACEHOLDER:
        registry = {**registry, "ca_cert_path": str(ca_file)}

    input_dir = _write_variant(tmp_path / "project", registry, top)
    log_dir = tmp_path / "log" / PROJECT_NAME
    result = run_playbook(tag="validate", extra_vars={
        "input_project_dir": str(input_dir),
        "log_dir": str(log_dir),
        "skip_build_credentials": "true",
    })

    output = result["output"]
    if expect_ok:
        logged = _read_logs(log_dir) if log_dir.exists() else ""
        verdict = result["success"] and (expected_log is None or expected_log in logged)
    else:
        verdict = (not result["success"]) and all(text in output for text in expected_output)

    if verdict:
        tl.passed(LOG["oci_variant_ok"].format(case=case_id))
    else:
        tl.failed(LOG["oci_variant_unexpected"].format(case=case_id), output[-500:])

    assert verdict, output[-2000:]
