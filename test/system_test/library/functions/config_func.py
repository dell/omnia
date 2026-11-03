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

"""The theme's settings (<theme>_test_config.yml): load and check them, write them
into the suites.

Each FVT suite reads its own ``test/<suite>/test_config.yml``. ./setup_env.sh
--configure writes there, with the comment-preserving editor of the dataset
generator (the rest of the suite's file stays exactly as it was):

* the ``cleanup`` block (whitelisted keys, booleans only);
* the theme block (``build_stream:`` catalog, cadence_catalog,
  allow_pipeline_cancel), mapped by THEMES[theme]["fvt_settings"];
* the report settings of the run (the FVT results go to <run folder>/fvt/).
"""

import os
from typing import Any, Callable, Dict, List

import yaml

from dataset_generator.dataset_edit import Change, dump_yaml, load_yaml, set_value, split_header

from .fvt_func import domain_dir
from .svt_report_func import fvt_report_settings
from ..messages.svt_msgs import CONFIG_MSGS
from ..vars.common_vars import (
    DEFAULT_SVT_REPORT_NAME,
    DEFAULT_SVT_REPORT_PATH,
    FVT_TEST_CONFIG,
    MODULE_ROOT,
    REPORT_NAME_RE,
    REPORT_PATH_RE,
    RUN_ID_RE,
    THEME_CONFIG,
)
from ..vars.theme_vars import (
    CLEANUP_ENABLED_KEY,
    CLEANUP_FLAGS,
    MAIN_CLEANUP_ALL_KEY,
    REPORT_KEYS,
    REPORT_SUITES,
    THEMES,
)

Emit = Callable[[str], None]


class ConfigError(ValueError):
    """The theme's test_config is missing or invalid; the message says what to fix."""


# Top-level keys of <theme>_test_config.yml besides the theme block.
CONFIG_KEYS = ("omnia_force_env", "cleanup", "report")


def _require_bool(value: Any, where: str, path: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(CONFIG_MSGS["not_bool"].format(path=path, where=where, value=value))
    return value


def theme_config_path(theme: str) -> str:
    """Return the settings file of ``theme``: <theme>_test_config.yml."""
    return THEME_CONFIG.format(theme=theme)


def load_svt_config(theme: str) -> Dict[str, Any]:
    """Return the checked settings of ``theme`` from <theme>_test_config.yml.

    Returns:
        Dict with keys: theme, path, omnia_force_env, cleanup ({suite: {flag:
        bool}}, every suite of CLEANUP_FLAGS, "enabled" included), report,
        fvt_settings ({key: value} of the theme block).

    Raises:
        ConfigError: When the theme is unknown, or the file cannot be read or
            holds an unknown key or value.
    """
    if theme not in THEMES:
        raise ConfigError(CONFIG_MSGS["unknown_theme"].format(
            path="--theme", theme=theme, known=", ".join(THEMES)))
    path = theme_config_path(theme)
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except OSError as exc:
        raise ConfigError(CONFIG_MSGS["unreadable"].format(path=path, error=exc.strerror)) from exc
    except yaml.YAMLError as exc:
        raise ConfigError(CONFIG_MSGS["invalid_yaml"].format(path=path, error=exc)) from exc
    if not isinstance(data, dict):
        raise ConfigError(CONFIG_MSGS["not_mapping"].format(path=path, where="the file"))
    unknown_keys = sorted(set(data) - {*CONFIG_KEYS, theme})
    if unknown_keys:
        raise ConfigError(CONFIG_MSGS["unknown_key"].format(
            path=path, names=", ".join(unknown_keys), known=", ".join((*CONFIG_KEYS, theme))))
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
            "omnia_force_env": _require_bool(force_env, "omnia_force_env", path),
            "report": _load_report_block(data.get("report") or {}, path),
            "fvt_settings": _load_theme_block(theme, data.get(theme) or {}, path)}


def _check_setting(kind: str, value: Any, where: str, path: str) -> Any:
    """Return a checked theme setting: a bool, or a catalog (number, absolute path or "")."""
    if kind == "bool":
        return _require_bool(value, where, path)
    text = "" if value is None else str(value).strip()
    if text == "" or (text.isdigit() and int(text) > 0):
        return int(text) if text else ""
    if text.startswith("/") and ".." not in text.split("/"):
        return text
    raise ConfigError(CONFIG_MSGS["invalid_catalog"].format(path=path, where=where, value=text))


def _load_theme_block(theme: str, block: Any, path: str) -> Dict[str, Any]:
    """Return the checked theme block (only the keys given; the FVT default stays otherwise)."""
    if not isinstance(block, dict):
        raise ConfigError(CONFIG_MSGS["not_mapping"].format(path=path, where=theme))
    allowed = THEMES[theme]["fvt_settings"]
    unknown = sorted(set(block) - set(allowed))
    if unknown:
        raise ConfigError(CONFIG_MSGS["unknown_key"].format(
            path=path, names=", ".join(f"{theme}.{key}" for key in unknown),
            known=", ".join(allowed)))
    return {key: _check_setting(allowed[key][3], value, f"{theme}.{key}", path)
            for key, value in block.items()}


def _load_report_block(block: Any, path: str) -> Dict[str, str]:
    """Return the checked report block (empty strings mean the default)."""
    if not isinstance(block, dict):
        raise ConfigError(CONFIG_MSGS["not_mapping"].format(path=path, where="report"))
    unknown = sorted(set(block) - set(REPORT_KEYS))
    if unknown:
        raise ConfigError(CONFIG_MSGS["unknown_report_key"].format(
            path=path, names=", ".join(unknown), known=", ".join(REPORT_KEYS)))
    patterns = {"report_path": REPORT_PATH_RE, "report_name": REPORT_NAME_RE, "run_id": RUN_ID_RE}
    report = {}
    for key in REPORT_KEYS:
        value = block.get(key)
        text = "" if value is None else str(value).strip()
        if text and (not patterns[key].fullmatch(text) or ".." in text.split("/")):
            raise ConfigError(CONFIG_MSGS["invalid_report_value"].format(
                path=path, key=key, value=text))
        report[key] = text
    return report


def cleanup_all(config: Dict[str, Any]) -> bool:
    """Return whether the main cleanup is the complete reset (omnia.sh --cleanup --all)."""
    main = config["cleanup"].get("main", {})
    return bool(main.get(CLEANUP_ENABLED_KEY, True) and main.get(MAIN_CLEANUP_ALL_KEY, False))


def report_settings(config: Dict[str, Any], run_id: str) -> Dict[str, str]:
    """Return the report folder of the run (<report_path>/<run_id>), report_name and ``run_id``.

    Every run has its own folder, so a report holds one run and one theme.
    """
    block = config["report"]
    path = block["report_path"] or DEFAULT_SVT_REPORT_PATH
    if not os.path.isabs(path):
        path = os.path.join(MODULE_ROOT, path)
    name = block["report_name"] or DEFAULT_SVT_REPORT_NAME.format(theme=config["theme"])
    return {"report_path": os.path.normpath(os.path.join(path, run_id)), "report_name": name,
            "run_id": run_id}


def cleanup_enabled(config: Dict[str, Any], suite: str) -> bool:
    """Return whether the cleanup step of ``suite`` runs."""
    return bool(config["cleanup"].get(suite, {}).get(CLEANUP_ENABLED_KEY, True))


def _write_suite_values(suite: str, section: str, values: Dict[str, Any],
                        changes: List[Change]) -> None:
    """Write ``values`` into test/<suite>/test_config.yml (only the values that differ).

    ``section`` is the mapping that holds the keys ("" = top level). Every key
    must already exist there, so a renamed or removed setting is reported
    instead of silently added.
    """
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
    for key, value in values.items():
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
            _write_suite_values(suite, CLEANUP_FLAGS[suite][0], values, changes)
    _report_changes(changes, emit, CONFIG_MSGS["flags_current"])
    return changes


def apply_fvt_settings(config: Dict[str, Any], emit: Emit) -> List[Change]:
    """Write the theme block (catalog, cadence_catalog, ...) into the FVT suites' test_config.

    Returns:
        The changes made: (file, key, old, new).
    """
    mapping = THEMES[config["theme"]]["fvt_settings"]
    grouped: Dict[tuple, Dict[str, Any]] = {}
    for key, value in config["fvt_settings"].items():
        suite, section, target, _ = mapping[key]
        grouped.setdefault((suite, section), {})[target] = value
    changes: List[Change] = []
    for (suite, section), values in grouped.items():
        _write_suite_values(suite, section, values, changes)
    _report_changes(changes, emit, CONFIG_MSGS["settings_current"])
    return changes


def apply_report_settings(settings: Dict[str, str], emit: Emit) -> List[Change]:
    """Write the FVT report settings of the run (<run folder>/fvt) into every suite.

    Returns:
        The changes made: (file, key, old, new).
    """
    changes: List[Change] = []
    fvt = fvt_report_settings(settings)
    for suite in REPORT_SUITES:
        _write_suite_values(suite, "", {key: fvt[key] for key in REPORT_KEYS}, changes)
    _report_changes(changes, emit, CONFIG_MSGS["report_current"])
    return changes


def _report_changes(changes: List[Change], emit: Emit, unchanged: str) -> None:
    for path, key, old, new in changes:
        emit(CONFIG_MSGS["flag_set"].format(path=os.path.relpath(path, os.path.dirname(
            os.path.dirname(path))), key=key, old=old, new=new))
    if not changes:
        emit(unchanged)
