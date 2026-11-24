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

"""External repo_manager contract verification functions.

Validates that repo_status.yml from an external source passes the
image_build_manager consumer contract (JSON Schema + semantic checks)
and parses correctly into consumer-required facts.
"""

import importlib.util
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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
    """Run schema + semantic validation against a repo_status dict.

    Args:
        data: Parsed repo_status.yml content.

    Returns:
        Dict with keys: success (bool), details (str), errors (list).
    """
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
    """Parse repo_status.yml from an external source.

    Args:
        path: Absolute path to the repo_status.yml file.

    Returns:
        Dict with keys: success (bool), details (str), error (str),
        result (dict with parsed fields).
    """
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
    """Return the smallest valid external repo_status.yml payload.

    Args:
        **overrides: Keys to override in the base payload.

    Returns:
        Dict representing a minimal valid repo_status.yml.
    """
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
    """Write a repo_status.yml fixture and return its path.

    Args:
        tmp_path: pytest tmp_path fixture.
        data: repo_status content to write.

    Returns:
        Absolute path to the written file as a string.
    """
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
    """Load a bundled sample repo_status.yml.

    Args:
        name: Filename under samples/repo_manager_output/.
        tmp_path: If replacements are needed, write to this temp dir.
        replacements: String replacements to apply (e.g. Jinja vars).

    Returns:
        Tuple of (parsed data dict, file path string).
    """
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
