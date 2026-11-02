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

"""The SVT test_config.yml: load and check it, write its cleanup flags into the suites.

Each suite's cleanup FVT reads its own ``test/<suite>/test_config.yml``. The
SVT writes the values of its ``cleanup`` block there (whitelisted keys,
booleans only), with the comment-preserving editor of the dataset generator,
so the rest of the suite's file stays exactly as it was.
"""

import os
from typing import Any, Callable, Dict, List

import yaml

from dataset_generator.dataset_edit import Change, dump_yaml, load_yaml, set_value, split_header

from .fvt_func import domain_dir
from ..messages.svt_msgs import CONFIG_MSGS
from ..vars.common_vars import FVT_TEST_CONFIG, SVT_TEST_CONFIG
from ..vars.theme_vars import CLEANUP_ENABLED_KEY, CLEANUP_FLAGS, THEMES

Emit = Callable[[str], None]


class ConfigError(ValueError):
    """The SVT test_config.yml is missing or invalid; the message says what to fix."""


def _require_bool(value: Any, where: str, path: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(CONFIG_MSGS["not_bool"].format(path=path, where=where, value=value))
    return value


def load_svt_config(path: str = SVT_TEST_CONFIG) -> Dict[str, Any]:
    """Return the checked SVT settings.

    Returns:
        Dict with keys: theme, omnia_force_env, cleanup ({suite: {flag: bool}},
        every suite of CLEANUP_FLAGS, "enabled" included), path.

    Raises:
        ConfigError: When the file cannot be read or holds an unknown key or value.
    """
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except OSError as exc:
        raise ConfigError(CONFIG_MSGS["unreadable"].format(path=path, error=exc.strerror)) from exc
    except yaml.YAMLError as exc:
        raise ConfigError(CONFIG_MSGS["invalid_yaml"].format(path=path, error=exc)) from exc
    if not isinstance(data, dict):
        raise ConfigError(CONFIG_MSGS["not_mapping"].format(path=path, where="the file"))
    theme = str(data.get("theme") or "")
    if theme not in THEMES:
        raise ConfigError(CONFIG_MSGS["unknown_theme"].format(
            path=path, theme=theme, known=", ".join(THEMES)))
    cleanup_block = data.get("cleanup") or {}
    if not isinstance(cleanup_block, dict):
        raise ConfigError(CONFIG_MSGS["not_mapping"].format(path=path, where="cleanup"))
    unknown = sorted(set(cleanup_block) - set(CLEANUP_FLAGS))
    if unknown:
        raise ConfigError(CONFIG_MSGS["unknown_suite"].format(
            path=path, names=", ".join(unknown), known=", ".join(CLEANUP_FLAGS)))
    cleanup: Dict[str, Dict[str, bool]] = {}
    for suite, (_, allowed) in CLEANUP_FLAGS.items():
        block = cleanup_block.get(suite) or {}
        if not isinstance(block, dict):
            raise ConfigError(CONFIG_MSGS["not_mapping"].format(path=path,
                                                                where=f"cleanup.{suite}"))
        bad = sorted(set(block) - {CLEANUP_ENABLED_KEY, *allowed})
        if bad:
            raise ConfigError(CONFIG_MSGS["unknown_flag"].format(
                path=path, suite=suite, names=", ".join(bad),
                known=", ".join((CLEANUP_ENABLED_KEY, *allowed))))
        cleanup[suite] = {key: _require_bool(value, f"cleanup.{suite}.{key}", path)
                          for key, value in block.items()}
        cleanup[suite].setdefault(CLEANUP_ENABLED_KEY, True)
    force_env = data.get("omnia_force_env", True)
    return {"theme": theme, "path": path, "cleanup": cleanup,
            "omnia_force_env": _require_bool(force_env, "omnia_force_env", path)}


def cleanup_enabled(config: Dict[str, Any], suite: str) -> bool:
    """Return whether the cleanup step of ``suite`` runs."""
    return bool(config["cleanup"].get(suite, {}).get(CLEANUP_ENABLED_KEY, True))


def _write_suite_flags(suite: str, flags: Dict[str, bool], changes: List[Change]) -> None:
    """Write ``flags`` into test/<suite>/test_config.yml (only the values that differ)."""
    section, _ = CLEANUP_FLAGS[suite]
    path = os.path.join(domain_dir(suite), FVT_TEST_CONFIG)
    with open(path, "r", encoding="utf-8") as stream:
        text = stream.read()
    header, body = split_header(text)
    document = load_yaml(body)
    if not isinstance(document, dict):
        raise ConfigError(CONFIG_MSGS["not_mapping"].format(path=path, where="the file"))
    target = document.get(section) if section else document
    if not isinstance(target, dict):
        raise ConfigError(CONFIG_MSGS["suite_section_missing"].format(path=path, section=section))
    before = len(changes)
    for key, value in flags.items():
        if key not in target:
            raise ConfigError(CONFIG_MSGS["suite_key_missing"].format(
                path=path, key=f"{section}.{key}" if section else key))
        set_value(target, key, value, changes, path, section or suite)
    if len(changes) > before:
        temp = f"{path}.svt-tmp"
        with open(temp, "w", encoding="utf-8") as stream:
            stream.write(header + dump_yaml(document))
        os.replace(temp, path)


def apply_cleanup_flags(config: Dict[str, Any], emit: Emit) -> List[Change]:
    """Write the cleanup flags of every enabled suite into its test_config.yml.

    Returns:
        The changes made: (file, key, old, new).
    """
    changes: List[Change] = []
    for suite, flags in config["cleanup"].items():
        values = {key: value for key, value in flags.items() if key != CLEANUP_ENABLED_KEY}
        if values and cleanup_enabled(config, suite):
            _write_suite_flags(suite, values, changes)
    for path, key, old, new in changes:
        emit(CONFIG_MSGS["flag_set"].format(path=os.path.relpath(path, os.path.dirname(
            os.path.dirname(path))), key=key, old=old, new=new))
    if not changes:
        emit(CONFIG_MSGS["flags_current"])
    return changes
