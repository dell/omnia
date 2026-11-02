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

"""Load and validate the cluster folders and theme files of the SVT project.

Used by the pipeline (render_pipeline.py, cluster_config.py) on the runner.
Requires Python 3.9+ and PyYAML; reads only files of this repository.
"""

import os
import re
from typing import Any, Dict, List

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLUSTERS_DIR = os.path.join(ROOT, "clusters")
THEMES_DIR = os.path.join(ROOT, "ci", "themes")
STAGES = ("initialization", "cleanup", "environment_setup", "system_verification", "summary")
CLUSTER_FILES = ("cluster.yml", "user_inputs.yml", "test_config.yml")
CLUSTER_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")
HOST_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}")
REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}")
PATH_RE = re.compile(r"/[A-Za-z0-9._/-]{1,254}")
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
TAG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
TIMEOUT_RE = re.compile(r"[1-9][0-9]{0,2}(m|h)")
URL_RE = re.compile(r"(https|ssh|git)://[A-Za-z0-9._~:/?#@%+-]{3,500}|[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[A-Za-z0-9._/-]+")
HOST_KEY_RE = re.compile(r"[A-Za-z0-9.:\[\],-]+ (ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521) [A-Za-z0-9+/=]+")

DEFAULTS = {"oim_user": "root", "oim_port": 22, "oim_host_key": "", "openbao_auth_mount": "jwt",
            "openbao_kv_mount": "secret", "openbao_path": "", "openbao_audience": "",
            "openbao_cacert": "", "runner_tag": "", "full_log_runner_tag": "", "timeouts": {}}
REQUIRED = ("oim_host", "clone_url", "clone_ref", "clone_path", "openbao_addr", "openbao_role")


class ConfigError(Exception):
    """A cluster or theme file is missing or invalid; the message says what to fix."""


def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except OSError as exc:
        raise ConfigError(f"{path}: cannot read ({exc.strerror})") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected key: value mapping")
    return data


def _check(value: Any, pattern: "re.Pattern[str]", field: str, path: str) -> str:
    text = str(value)
    if not pattern.fullmatch(text):
        raise ConfigError(f"{path}: {field} has an invalid value {text!r}")
    return text


def list_clusters() -> List[str]:
    """Return the cluster folder names (sorted)."""
    if not os.path.isdir(CLUSTERS_DIR):
        return []
    return sorted(name for name in os.listdir(CLUSTERS_DIR)
                  if os.path.isdir(os.path.join(CLUSTERS_DIR, name)))


def load_theme(theme: str) -> Dict[str, Any]:
    """Return a validated theme file."""
    if not TAG_RE.fullmatch(theme):
        raise ConfigError(f"invalid theme name {theme!r}")
    path = os.path.join(THEMES_DIR, f"{theme}.yml")
    data = _load_yaml(path)
    timeouts = data.get("timeouts") or {}
    for stage in STAGES:
        _check(timeouts.get(stage, ""), TIMEOUT_RE, f"timeouts.{stage}", path)
    cases = data.get("cases") or []
    if not cases:
        raise ConfigError(f"{path}: cases is empty")
    for case in cases:
        _check(case, TAG_RE, "cases", path)
    for module in data.get("credential_modules") or []:
        _check(module, TAG_RE, "credential_modules", path)
    return data


def load_cluster(name: str) -> Dict[str, Any]:
    """Return the validated cluster.yml of ``name`` with defaults applied.

    Raises:
        ConfigError: When a file is missing, a mandatory value is empty or a
            value has an unsafe format.
    """
    if not CLUSTER_RE.fullmatch(name):
        raise ConfigError(f"invalid cluster folder name {name!r} (lower case, digits, - and _)")
    folder = os.path.join(CLUSTERS_DIR, name)
    for file_name in CLUSTER_FILES:
        _load_yaml(os.path.join(folder, file_name))
    path = os.path.join(folder, "cluster.yml")
    config = {**DEFAULTS, **_load_yaml(path)}
    missing = [key for key in REQUIRED if not str(config.get(key) or "").strip()]
    if missing:
        raise ConfigError(f"{path}: fill the mandatory value(s): {', '.join(missing)}")
    _check(config["oim_host"], HOST_RE, "oim_host", path)
    _check(config["oim_user"], TAG_RE, "oim_user", path)
    port = config["oim_port"]
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigError(f"{path}: oim_port must be a number 1-65535")
    if config["oim_host_key"]:
        _check(config["oim_host_key"], HOST_KEY_RE, "oim_host_key", path)
    _check(config["clone_url"], URL_RE, "clone_url", path)
    _check(config["clone_ref"], REF_RE, "clone_ref", path)
    _check(config["clone_path"], PATH_RE, "clone_path", path)
    if ".." in str(config["clone_path"]).split("/") or str(config["clone_path"]).rstrip("/") in ("", "/root", "/opt", "/opt/omnia"):
        raise ConfigError(f"{path}: clone_path must be a dedicated directory")
    if not str(config["openbao_addr"]).startswith("https://"):
        raise ConfigError(f"{path}: openbao_addr must be an https:// URL")
    _check(config["openbao_addr"], URL_RE, "openbao_addr", path)
    for key in ("openbao_role", "openbao_auth_mount", "openbao_kv_mount"):
        _check(config[key], NAME_RE, key, path)
    config["openbao_path"] = config["openbao_path"] or f"omnia/{name}"
    _check(config["openbao_path"], NAME_RE, "openbao_path", path)
    config["openbao_audience"] = config["openbao_audience"] or config["openbao_addr"]
    if config["openbao_cacert"]:
        _check(config["openbao_cacert"], PATH_RE, "openbao_cacert", path)
    for key in ("runner_tag", "full_log_runner_tag"):
        if config[key]:
            _check(config[key], TAG_RE, key, path)
    if not isinstance(config["timeouts"], dict):
        raise ConfigError(f"{path}: timeouts must be a mapping")
    for stage, value in config["timeouts"].items():
        if stage not in STAGES:
            raise ConfigError(f"{path}: timeouts.{stage} is not a stage ({', '.join(STAGES)})")
        _check(value, TIMEOUT_RE, f"timeouts.{stage}", path)
    config["name"] = name
    return config
