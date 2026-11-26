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

"""External repo_manager contract checks: schema, semantics, parsing and source host."""

import importlib.util
import json
import logging
import os
import socket
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import ansible.module_utils
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_IBM = _REPO_ROOT / "src" / "image_build_manager"
_MODULE_UTILS_DIR = _SRC_IBM / "plugins" / "module_utils"
if str(_MODULE_UTILS_DIR) not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.append(str(_MODULE_UTILS_DIR))

_SCHEMA_PATH = (
    _SRC_IBM
    / "plugins/module_utils/input_validation/schema/repo_status.json"
)
_ENGINE_PATH = (
    _SRC_IBM
    / "plugins/module_utils/input_validation/core/validation_engine.py"
)
_REPO_VALIDATOR_PATH = (
    _SRC_IBM
    / "plugins/module_utils/input_validation/validators/repo_status_validator.py"
)
_PARSE_MODULE_PATH = _SRC_IBM / "plugins/modules/parse_repo_status.py"
_SAMPLE_DIR = _SRC_IBM / "samples" / "repo_manager_output"

_LOGGER = logging.getLogger(__name__)
_OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
_OPENSSL_TIMEOUT = 10


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


_ENGINE = _load_module("image_build_validation_engine", _ENGINE_PATH)
_REPO_VALIDATOR = _load_module("repo_status_validator", _REPO_VALIDATOR_PATH)
_PARSE = _load_module("parse_repo_status", _PARSE_MODULE_PATH)


def _schema():
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_repo_contract(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run schema + semantic validation; return ``{success, details, errors}``."""
    errors = []
    _ENGINE.schema(data, _schema(), "repo_status.yml", errors, _LOGGER)
    if not errors:
        errors.extend(_REPO_VALIDATOR.validate(data, _LOGGER))

    if errors:
        return {
            "success": False,
            "details": "; ".join(errors),
            "errors": errors,
        }
    return {
        "success": True,
        "details": "Contract validation passed (schema + semantic)",
        "errors": [],
    }


def parse_repo_status_external(path: str) -> Dict[str, Any]:
    """Parse a repo_status.yml; return ``{success, details, error, result}``."""
    try:
        result = _PARSE.parse_repo_status(path)
        versions = result.get("cluster_os_versions", [])
        x86_count = len(result.get("repo_manager_repos_x86_64", []))
        arm_count = len(result.get("repo_manager_repos_aarch64", []))
        return {
            "success": True,
            "details": (
                f"Parsed: {len(versions)} version(s), "
                f"{x86_count} x86_64 repo(s), {arm_count} aarch64 repo(s), "
                f"port={result.get('repo_port')}"
            ),
            "error": "",
            "result": result,
        }
    except (FileNotFoundError, ValueError, KeyError) as exc:
        return {
            "success": False,
            "details": str(exc),
            "error": str(exc),
            "result": {},
        }


def minimal_external_status(**overrides) -> Dict[str, Any]:
    """Return the smallest valid external repo_status payload, with ``overrides`` applied."""
    base = {
        "overall_status": "success",
        "cluster_os_type": "rhel",
        "repositories": {
            "10.0": {
                "x86_64": {
                    "baseos": {
                        "url": "https://repo.external.example.com/baseos/",
                    }
                }
            }
        },
    }
    base.update(overrides)
    return base


def write_status_fixture(tmp_path, data: Dict[str, Any]) -> str:
    """Write ``data`` as repo_status.yml under ``tmp_path`` and return its path."""
    path = tmp_path / "repo_status.yml"
    path.write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8",
    )
    return str(path)


def load_sample_status(
    name: str,
    tmp_path=None,
    replacements: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, Any], str]:
    """Load a bundled sample; ``replacements`` (written to ``tmp_path``) fill its Jinja vars."""
    sample_path = _SAMPLE_DIR / name
    text = sample_path.read_text(encoding="utf-8")

    if replacements:
        for old, new in replacements.items():
            text = text.replace(old, new)
        if tmp_path is not None:
            out = tmp_path / "repo_status.yml"
            out.write_text(text, encoding="utf-8")
            return yaml.safe_load(text), str(out)

    return yaml.safe_load(text), str(sample_path)


def _env_values(path: str = _OMNIA_ENV_FILE) -> Dict[str, str]:
    """Return KEY=value pairs of an env file (empty when unreadable)."""
    values: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    values[key.strip()] = value.strip().strip("\"'")
    except OSError:
        pass
    return values


def local_addresses() -> Set[str]:
    """Return every address and name that identifies this OIM (lower case)."""
    names = {"localhost", "127.0.0.1", "::1"}
    env = _env_values()
    names.update(env.get(key, "") for key in
                 ("SYSTEM_ADMIN_NIC_IPV4", "SYSTEM_HOSTNAME"))
    names.update((socket.gethostname(), socket.getfqdn()))
    try:
        listing = subprocess.run(
            ["ip", "-o", "addr", "show"], capture_output=True, text=True,
            check=False, timeout=_OPENSSL_TIMEOUT,
        ).stdout
        for line in listing.splitlines():
            fields = line.split()
            if "inet" in fields or "inet6" in fields:
                names.add(fields[fields.index("inet6" if "inet6" in fields
                                              else "inet") + 1].split("/")[0])
    except (OSError, subprocess.SubprocessError):
        pass
    return {name.lower() for name in names if name}


def status_repo_hosts(data: Dict[str, Any]) -> Set[str]:
    """Return the host of every repository URL in a repo_status dict."""
    urls: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("url", "base_url") and isinstance(value, str):
                    urls.append(value)
                else:
                    walk(value)
        elif isinstance(node, str) and node.startswith(("http://", "https://")):
            urls.append(node)

    walk(data.get("repositories", {}))
    walk(data.get("base_urls", {}))
    return {host.lower() for host in
            (urlparse(url).hostname for url in urls) if host}


def cert_names(cert_path: str) -> Set[str]:
    """Return the IP and DNS subject alternative names of a certificate."""
    out = subprocess.run(
        ["openssl", "x509", "-in", cert_path, "-noout", "-ext",
         "subjectAltName"],
        capture_output=True, text=True, check=True, timeout=_OPENSSL_TIMEOUT,
    ).stdout
    names = set()
    for item in out.replace("\n", ",").split(","):
        item = item.strip()
        if item.startswith(("IP Address:", "DNS:")):
            names.add(item.split(":", 1)[1].strip().lower())
    return names


def verify_external_source(
    data: Dict[str, Any], expected_host: str = "",
    skip_cert: bool = False,
) -> Dict[str, Any]:
    """Check that a repo_status dict names repositories on another host.

    Fails when a repository host is this OIM, differs from ``expected_host``, or is not
    covered by the file's certificate (``skip_cert`` skips that check for fetched files).
    Returns ``{success, details, hosts, local, errors}``.
    """
    hosts = status_repo_hosts(data)
    local = local_addresses()
    errors: List[str] = []
    if not hosts:
        errors.append("repo_status.yml names no repository host")
    clash = sorted(hosts & local)
    if clash:
        errors.append(f"repository host(s) are this OIM: {', '.join(clash)}")
    if expected_host and hosts - {expected_host.lower()}:
        errors.append(
            f"repository host(s) {sorted(hosts - {expected_host.lower()})} "
            f"differ from external_repo_host {expected_host}"
        )
    if not skip_cert:
        cert = (data.get("repo_manager", {}).get("certificates", {})
                .get("server_crt", ""))
        if cert and hosts:
            try:
                missing = sorted(hosts - cert_names(cert))
                if missing:
                    errors.append(
                        f"certificate {cert} does not cover host(s) {missing}")
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(f"certificate {cert} unreadable: {exc}")
    return {
        "success": not errors,
        "details": "; ".join(errors) or (
            f"repository host(s) {sorted(hosts)} are external to this OIM"),
        "hosts": sorted(hosts),
        "local": sorted(local),
        "errors": errors,
    }


def live_status_path(custom: str = "") -> str:
    """Return the repo_status.yml path under test (custom override or default)."""
    if custom:
        return custom
    data_path = os.environ.get("OMNIA_DATA_PATH") or _env_values().get("OMNIA_DATA_PATH", "")
    return os.path.join(
        data_path, "repo_manager", "output",
        os.environ.get("OMNIA_PROJECT_NAME", "project_default"), "repo_status.yml")
