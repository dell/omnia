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
# Applicable rules used: CG-SECRETS-001.1, CG-SECRETS-001.7, CG-LOGGING-001.2, CG-CONFIG-001.5
# ****

"""
Image Build Manager — external OCI registry probe driver.

Runs ``library/playbooks/oci_registry_probe.yml`` against the real build_os_images
endpoint, credential, and session regctl tasks. Inputs are written to a mode 0600
file and passed by path, so no credential reaches the ``ansible-playbook`` command
line. Also provides the validate-tag helper used for opt-out and input-safety checks.
"""

import os
import re
import secrets
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from library.functions import load_test_credentials, run_playbook

REPO_ROOT = Path(__file__).resolve().parents[4]
ROLE_DIR = REPO_ROOT / "src" / "image_build_manager" / "roles" / "build_os_images"
PROBE_WORKDIR = Path(__file__).resolve().parents[1] / "playbooks"
PROBE_PLAYBOOK = "oci_registry_probe.yml"
PROJECT_NAME = os.environ.get("OMNIA_PROJECT_NAME", "project_default")
IMAGE_BUILD_DATA_PATH = os.environ.get("IMAGE_BUILD_MANAGER_DATA_PATH") or os.path.join(
    os.environ.get("OMNIA_DATA_PATH", "/opt/omnia"), "image_build_manager"
)
TARGET_INPUT_DIR = Path(IMAGE_BUILD_DATA_PATH) / "input" / PROJECT_NAME

LAB_HOST = os.environ.get("OMNIA_OCI_LAB_HOST", "")
LAB_PORT = int(os.environ.get("OMNIA_OCI_LAB_PORT", "5443"))
LAB_CA_FILE = os.environ.get("OMNIA_OCI_LAB_CA_FILE", "")
LAB_USER_KEY = "oci_lab_registry_username"
LAB_PASSWORD_KEY = "oci_lab_registry_password"  # nosec B105 - credential key name, not a value

PROBE_SESSION_RE = re.compile(
    r"PROBE_SESSION mode=(\d+) owner=(\S+) user_exact=(True|False) regctl_rc=(-?\d+)"
)
PROBE_REMOVED_RE = re.compile(r"PROBE_REMOVED exists=(True|False)")


def lab_available() -> bool:
    """Return True when the disposable TLS lab registry is configured."""
    return bool(LAB_HOST and LAB_CA_FILE and os.path.isfile(LAB_CA_FILE))


def lab_credentials() -> Optional[Tuple[str, str]]:
    """Return the registry account from OMNIA_OCI_TEST_* or the Vault-backed test credentials."""
    user = os.environ.get("OMNIA_OCI_TEST_USERNAME", "")
    password = os.environ.get("OMNIA_OCI_TEST_PASSWORD", "")
    if not (user and password):
        creds = load_test_credentials()
        user, password = creds.get(LAB_USER_KEY, ""), creds.get(LAB_PASSWORD_KEY, "")
    return (user, password) if user and password else None


def lab_registry(
    tls_verify: Optional[bool] = None, ca_cert_path: Optional[str] = None
) -> Dict[str, Any]:
    """Build an external_oci_registry section that points at the lab registry."""
    section: Dict[str, Any] = {
        "registry_type": "harbor",
        "auth_type": "basic",
        "registry_protocol": "https",
        "registry_hostname": LAB_HOST,
        "registry_port": LAB_PORT,
        "namespace_name": os.environ.get("OMNIA_OCI_LAB_NAMESPACE", "omnia-lab"),
    }
    if tls_verify is not None:
        section["tls_verify"] = tls_verify
    if ca_cert_path is not None:
        section["ca_cert_path"] = ca_cert_path
    return section


def new_secret() -> str:
    """Return a random canary value for leak checks."""
    return secrets.token_urlsafe(18)


def _write_private_yaml(path: Path, data: Dict[str, Any]) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def run_probe(
    workdir: Path,
    mode: str,
    registry: Dict[str, Any],
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Run the endpoint check; mode harbor adds the project check, mode session the push check."""
    workdir.mkdir(parents=True, exist_ok=True)
    inputs = workdir / "probe_inputs.yml"
    _write_private_yaml(inputs, {
        "probe_mode": mode,
        "probe_role_dir": str(ROLE_DIR),
        "registry_host": "localhost",
        "external_oci_registry": registry,
        "oci_registry_username": username,
        "oci_registry_password": password,
    })
    try:
        return run_playbook(
            playbook=PROBE_PLAYBOOK,
            playbook_workdir=str(PROBE_WORKDIR),
            extra_vars={"probe_vars_file": str(inputs)},
        )
    finally:
        inputs.unlink(missing_ok=True)


def parse_session_state(output: str) -> Optional[Dict[str, Any]]:
    """Extract the session configuration state reported by the probe."""
    match = PROBE_SESSION_RE.search(output)
    if not match:
        return None
    mode, owner, user_exact, rc = match.groups()
    return {"mode": mode, "owner": owner,
            "user_exact": user_exact == "True", "regctl_rc": int(rc)}


def session_removed(output: str) -> Optional[bool]:
    """Return True when the probe reports the session configuration was removed."""
    match = PROBE_REMOVED_RE.search(output)
    return None if not match else match.group(1) == "False"


def find_leaks(text: str, canary: str) -> bool:
    """Return True when the canary value appears in the text."""
    return bool(canary) and canary in text


def _write_validate_input(root: Path, registry: Dict[str, Any], top: Dict[str, Any]) -> Path:
    input_dir = root / "input" / PROJECT_NAME
    input_dir.mkdir(parents=True)
    shutil.copy(TARGET_INPUT_DIR / "package_groups.yml", input_dir / "package_groups.yml")
    config = yaml.safe_load(
        (TARGET_INPUT_DIR / "image_build_config.yml").read_text(encoding="utf-8")
    )
    config["functional_groups_source"] = "config"
    config["external_oci_registry"] = {**config.get("external_oci_registry", {}), **registry}
    config.update(top)
    (input_dir / "image_build_config.yml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )
    return input_dir


def run_validate(
    root: Path, registry: Dict[str, Any], top: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Run the validate tag against a temporary copy of the target configuration."""
    input_dir = _write_validate_input(root, registry, top or {})
    log_dir = root / "log" / PROJECT_NAME
    result = run_playbook(tag="validate", extra_vars={
        "input_project_dir": str(input_dir),
        "log_dir": str(log_dir),
        "skip_build_credentials": "true",
    })
    logs = sorted(log_dir.rglob("*.log")) if log_dir.exists() else []
    logged = "\n".join(p.read_text(encoding="utf-8") for p in logs)
    result["logged"] = logged
    return result
