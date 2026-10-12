# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Integration-specific catalog selection helpers."""

from pathlib import Path, PurePosixPath
from typing import Tuple

from omnia_auto import is_local_execution, load_test_config


_REPO_ROOT = Path(__file__).resolve().parents[3]
_CATALOG_ROOT = (_REPO_ROOT / "src" / "main" / "samples" / "catalogs").resolve()


def selected_catalog() -> Tuple[str, Path]:
    """Return the validated relative catalog path and local source file."""
    configured = str(load_test_config().get("cadence_catalog_path", "")).strip()
    relative = PurePosixPath(configured)
    if (
        not configured
        or relative.is_absolute()
        or ".." in relative.parts
        or relative.suffix.lower() != ".json"
        or len(relative.parts) < 2
    ):
        raise ValueError(
            "cadence_catalog_path must be a relative JSON file below "
            "src/main/samples/catalogs, for example "
            "rhel/10.2/slurm_x86_64_no_vast.json"
        )

    source = (_CATALOG_ROOT / Path(*relative.parts)).resolve()
    try:
        source.relative_to(_CATALOG_ROOT)
    except ValueError as exc:
        raise ValueError(
            "cadence_catalog_path resolves outside src/main/samples/catalogs"
        ) from exc
    if not source.is_file() or source.is_symlink():
        raise ValueError(f"Cadence catalog does not exist: {source}")
    return relative.as_posix(), source


def deployment_catalog_path() -> str:
    """Return the selected catalog path as seen by the Ansible controller."""
    relative, source = selected_catalog()
    if is_local_execution():
        return str(source)

    clone_path = str(load_test_config().get("clone_path", "")).rstrip("/")
    if not clone_path.startswith("/"):
        raise ValueError("clone_path must be absolute for remote execution")
    return f"{clone_path}/src/main/samples/catalogs/{relative}"
