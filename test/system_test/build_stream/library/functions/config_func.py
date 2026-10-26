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

"""test_config.yml validation and plan resolution."""

import posixpath
from typing import Any, Dict, Iterable, List

from ..vars.common_vars import (
    CLEANUP_DOMAINS,
    CLEANUP_ORDER,
    DEFAULT_POLL_INTERVAL,
    UUID_RE,
)

PIPELINES = ("build", "deploy", "cadence")
_INSTALLATION_KEYS = {"catalog"}
_PIPELINE_KEYS = {
    "allow_pipeline_cancel", "poll_interval",
    *(f"{name}_job_id" for name in PIPELINES),
}


class ConfigValidationError(ValueError):
    """Raised when test_config.yml is invalid."""


def _mapping(value: Any, field: str) -> Dict[str, Any]:
    """Return ``value`` as a mapping (None is empty)."""
    value = {} if value is None else value
    if not isinstance(value, dict):
        raise ConfigValidationError(f"{field} must be a mapping")
    return value


def _no_unknown(block: Dict[str, Any], allowed: Iterable[str], field: str) -> None:
    """Reject keys of ``block`` outside ``allowed``."""
    unknown = set(block) - set(allowed)
    if unknown:
        raise ConfigValidationError(
            f"{field} has unsupported keys: {', '.join(sorted(unknown))}; "
            f"supported: {', '.join(sorted(allowed))}"
        )


def _positive_int(value: Any, field: str) -> int:
    """Return ``value`` when it is a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigValidationError(f"{field} must be a positive integer")
    return value


def _boolean(value: Any, field: str) -> bool:
    """Return ``value`` when it is a boolean."""
    if not isinstance(value, bool):
        raise ConfigValidationError(f"{field} must be true or false")
    return value


def _text(value: Any) -> str:
    """Return ``value`` as stripped text (None is empty)."""
    return "" if value is None else str(value).strip()


def catalog_selection(value: Any) -> str:
    """Normalize installation.catalog to a catalog number or absolute path.

    Raises:
        ConfigValidationError: When the value is neither.
    """
    text = "" if isinstance(value, bool) else _text(value)
    if text.isdigit() and int(text) > 0:
        return str(int(text))
    if posixpath.isabs(text) and ".." not in text.split("/") and not text.endswith("/"):
        return text
    raise ConfigValidationError(
        "installation.catalog must be a catalog number from the list in "
        f"test_config.yml or the full path of a catalog on the OIM (got {value!r})"
    )


def _validate_installation(installation: Any) -> None:
    """Validate the installation block."""
    installation = _mapping(installation, "installation")
    _no_unknown(installation, _INSTALLATION_KEYS, "installation")
    catalog_selection(installation.get("catalog"))


def _validate_pipeline(pipeline: Any) -> None:
    """Validate the pipeline block."""
    pipeline = _mapping(pipeline, "pipeline")
    _no_unknown(pipeline, _PIPELINE_KEYS, "pipeline")
    if "allow_pipeline_cancel" in pipeline:
        _boolean(pipeline["allow_pipeline_cancel"], "pipeline.allow_pipeline_cancel")
    if "poll_interval" in pipeline:
        _positive_int(pipeline["poll_interval"], "pipeline.poll_interval")
    for name in PIPELINES:
        job_id = _text(pipeline.get(f"{name}_job_id"))
        if job_id and not UUID_RE.fullmatch(job_id):
            raise ConfigValidationError(
                f"pipeline.{name}_job_id must be a BuildStream job UUID from "
                f"build_stream_db (table jobs): {job_id!r}"
            )


def _validate_cleanup(cleanup: Any) -> None:
    """Validate the cleanup block and every domain flag."""
    cleanup = _mapping(cleanup, "cleanup")
    _no_unknown(cleanup, {"fail_fast", *CLEANUP_ORDER}, "cleanup")
    _boolean(cleanup.get("fail_fast", True), "cleanup.fail_fast")
    for name in CLEANUP_ORDER:
        field = f"cleanup.{name}"
        block = _mapping(cleanup.get(name), field)
        _no_unknown(block, {"enabled", *CLEANUP_DOMAINS[name]["config_flags"]}, field)
        for key, value in block.items():
            _boolean(value, f"{field}.{key}")


def validate_test_config(config: Dict[str, Any]) -> None:
    """Validate the suite configuration.

    Raises:
        ConfigValidationError: On the first invalid field.
    """
    if not isinstance(config, dict):
        raise ConfigValidationError("test_config.yml must be a mapping")
    for field in ("report_path", "report_name"):
        if not _text(config.get(field)):
            raise ConfigValidationError(f"{field} is required in test_config.yml")
    clone_path = _text(config.get("clone_path"))
    if _text(config.get("oim_server_ip")) and not posixpath.isabs(clone_path):
        raise ConfigValidationError(
            "clone_path must be the absolute path of the omnia checkout on the "
            f"OIM when oim_server_ip is set (got {clone_path!r})"
        )
    _validate_installation(config.get("installation"))
    _validate_pipeline(config.get("pipeline"))
    _validate_cleanup(config.get("cleanup"))


def installation_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return the installation and pipeline settings with defaults applied.

    Returns:
        Dict with keys: catalog (number or absolute path), allow_pipeline_cancel,
        poll_interval, and build/deploy/cadence, each a
        dict holding the verify-only job_id ("" for trigger mode).
    """
    installation = config.get("installation") or {}
    pipeline = config.get("pipeline") or {}
    settings = {
        "catalog": catalog_selection(installation.get("catalog")),
        "allow_pipeline_cancel": pipeline.get("allow_pipeline_cancel", False),
        "poll_interval": pipeline.get("poll_interval", DEFAULT_POLL_INTERVAL),
    }
    for name in PIPELINES:
        settings[name] = {"job_id": _text(pipeline.get(f"{name}_job_id"))}
    return settings


def cleanup_fail_fast(config: Dict[str, Any]) -> bool:
    """Return whether cleanup stops at the first failed domain."""
    return (config.get("cleanup") or {}).get("fail_fast", True)


def to_ansible_extra_vars(extra_vars: Dict[str, Any]) -> Dict[str, str]:
    """Render configured extra variables as ``-e key=value`` strings."""
    return {
        key: (str(value).lower() if isinstance(value, bool) else str(value))
        for key, value in extra_vars.items()
    }


def cleanup_plan(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Resolve the per-domain cleanup plan in the fixed CLEANUP_ORDER.

    Each entry contains:
        name:           cleanup block name (e.g. ``cleanup_build_stream``).
        enabled:        whether the domain is cleaned.
        extra_vars:     variables passed with ``-e`` (flags + fixed vars).
        skip_tags:      tags skipped because a tag-gated flag is false.
        effective_vars: playbook defaults overlaid with the flags and fixed
                        vars; verification reads these.
        spec:           playbook/workdir/tag contract from CLEANUP_DOMAINS.
    """
    cleanup = config.get("cleanup") or {}
    plan = []
    for name in CLEANUP_ORDER:
        block = cleanup.get(name) or {}
        spec = CLEANUP_DOMAINS[name]
        flags = {key: block.get(key, default)
                 for key, default in spec["config_flags"].items()}
        passed = {**flags, **spec["fixed_vars"]}
        effective = {key: value for key, value in spec["supported_vars"].items()
                     if value is not None}
        effective.update(passed)
        plan.append({
            "name": name,
            "enabled": block.get("enabled", True),
            "extra_vars": {key: value for key, value in passed.items()
                           if key not in spec["skip_tag_vars"]},
            "skip_tags": [tag for key, tag in spec["skip_tag_vars"].items()
                          if passed.get(key) is False],
            "effective_vars": effective,
            "spec": spec,
        })
    return plan
