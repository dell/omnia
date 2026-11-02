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
from typing import Any, Dict, Iterable

from ..vars.execute_vars import (
    DEFAULT_POLL_INTERVAL,
    IMAGE_GROUP_ID_RE,
    UUID_RE,
)

# Verify-only job ID keys (pipeline.<name>_job_id); the manual build and
# deploy suites use the same build_job_id / deploy_job_id.
PIPELINES = ("build", "deploy", "cadence")
_INSTALLATION_KEYS = {"catalog", "cadence_catalog"}
_PIPELINE_KEYS = {
    "allow_pipeline_cancel", "poll_interval", "cleanup_image_group_id",
    "auto_cleanup_image_group_id", "deploy_image_group_id",
    *(f"{name}_job_id" for name in PIPELINES),
}
# FVT cleanup scenario flags (build_stream.yml --tags cleanup -e <flag>=<value>).
CLEANUP_FLAGS = {"postgres_backup": False, "cleanup_credentials": True}
# Defaults when test_config.yml omits a setting.
DEFAULT_ALLOW_PIPELINE_CANCEL = True
DEFAULT_DEBUG_MODE = True


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


def catalog_selection(value: Any, field: str = "installation.catalog") -> str:
    """Normalize a catalog setting to a catalog number or absolute path.

    Raises:
        ConfigValidationError: When the value is neither.
    """
    text = "" if isinstance(value, bool) else _text(value)
    if text.isdigit() and int(text) > 0:
        return str(int(text))
    if posixpath.isabs(text) and ".." not in text.split("/") and not text.endswith("/"):
        return text
    raise ConfigValidationError(
        f"{field} must be a catalog number from the list in "
        f"test_config.yml or the full path of a catalog on the OIM (got {value!r})"
    )


def _validate_installation(installation: Any) -> None:
    """Validate the installation block."""
    installation = _mapping(installation, "installation")
    _no_unknown(installation, _INSTALLATION_KEYS, "installation")
    catalog_selection(installation.get("catalog"))
    if _text(installation.get("cadence_catalog")):
        catalog_selection(installation["cadence_catalog"], "installation.cadence_catalog")


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
    for key in ("cleanup_image_group_id", "auto_cleanup_image_group_id",
                "deploy_image_group_id"):
        group_id = _text(pipeline.get(key))
        if group_id and not IMAGE_GROUP_ID_RE.fullmatch(group_id):
            raise ConfigValidationError(
                f"pipeline.{key} must be an image group ID from "
                f"build_stream_db (table image_groups): {group_id!r}"
            )


def _validate_cleanup(cleanup: Any) -> None:
    """Validate the FVT cleanup block (postgres_backup, cleanup_credentials)."""
    cleanup = _mapping(cleanup, "cleanup")
    _no_unknown(cleanup, set(CLEANUP_FLAGS), "cleanup")
    for key, value in cleanup.items():
        _boolean(value, f"cleanup.{key}")


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
    for flag in ("debug_mode", "continue_on_failure"):
        if flag in config and not isinstance(config[flag], bool):
            raise ConfigValidationError(f"{flag} must be true or false (without quotes)")
    _validate_installation(config.get("installation"))
    _validate_pipeline(config.get("pipeline"))
    _validate_cleanup(config.get("cleanup"))


def installation_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return the installation and pipeline settings with defaults applied.

    Returns:
        Dict with keys: catalog (build catalog, number or absolute path),
        cadence_catalog (cadence catalog; "" = the build catalog),
        allow_pipeline_cancel (default true), poll_interval, debug_mode
        (default true), cleanup_image_group_id and auto_cleanup_image_group_id
        ("" = first = newest cleanable group),
        deploy_image_group_id (image group a deploy-only run deploys), and one
        dict per PIPELINES name holding the verify-only job_id ("" for
        trigger mode).
    """
    installation = config.get("installation") or {}
    pipeline = config.get("pipeline") or {}
    catalog = catalog_selection(installation.get("catalog"))
    cadence = _text(installation.get("cadence_catalog"))
    settings = {
        "catalog": catalog,
        "cadence_catalog": (catalog_selection(cadence, "installation.cadence_catalog")
                            if cadence else catalog),
        "allow_pipeline_cancel": pipeline.get("allow_pipeline_cancel",
                                              DEFAULT_ALLOW_PIPELINE_CANCEL),
        "poll_interval": pipeline.get("poll_interval", DEFAULT_POLL_INTERVAL),
        "debug_mode": config.get("debug_mode", DEFAULT_DEBUG_MODE),
        "cleanup_image_group_id": _text(pipeline.get("cleanup_image_group_id")),
        "auto_cleanup_image_group_id": _text(pipeline.get("auto_cleanup_image_group_id")),
        "deploy_image_group_id": _text(pipeline.get("deploy_image_group_id")),
    }
    for name in PIPELINES:
        settings[name] = {"job_id": _text(pipeline.get(f"{name}_job_id"))}
    return settings


def cleanup_settings(config: Dict[str, Any]) -> Dict[str, bool]:
    """Return the cleanup scenario flags with defaults applied.

    Returns:
        Dict with keys: postgres_backup (default false: delete the Postgres
        data), cleanup_credentials (default true: delete the credentials).
    """
    cleanup = config.get("cleanup") or {}
    return {key: cleanup.get(key, default) for key, default in CLEANUP_FLAGS.items()}


def continue_on_failure(config: Dict[str, Any]) -> bool:
    """Return whether independent tests keep running after a failure (default false)."""
    return config.get("continue_on_failure", False) is True


def to_ansible_extra_vars(extra_vars: Dict[str, Any]) -> Dict[str, str]:
    """Render configured extra variables as ``-e key=value`` strings."""
    return {
        key: (str(value).lower() if isinstance(value, bool) else str(value))
        for key, value in extra_vars.items()
    }
