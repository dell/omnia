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
"""Rollback-safe publication and comparison for generated datasets."""

import fcntl
import hashlib
import os
import shutil
import stat
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class DatasetPublicationError(Exception):
    """Raised when a staged dataset cannot be compared or published safely."""


@contextmanager
def dataset_lock(datasets_dir: Path) -> Iterator[None]:
    """Serialize compare/publish transactions without creating a lock file."""
    try:
        descriptor = os.open(datasets_dir, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as exc:
        raise DatasetPublicationError(
            f"Cannot open the dataset directory for locking: {exc}"
        ) from exc
    acquired = False
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DatasetPublicationError(
                "Another dataset compare/publish transaction is active; retry"
            ) from exc
        except OSError as exc:
            raise DatasetPublicationError(
                f"Cannot lock the dataset directory: {exc}"
            ) from exc
        acquired = True
        yield
    finally:
        active_error = sys.exc_info()[0] is not None
        cleanup_errors: list[str] = []
        if acquired:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError as exc:
                cleanup_errors.append(f"unlock failed: {exc}")
        try:
            os.close(descriptor)
        except OSError as exc:
            cleanup_errors.append(f"close failed: {exc}")
        if cleanup_errors and not active_error:
            raise DatasetPublicationError(
                "Dataset lock cleanup failed: " + "; ".join(cleanup_errors)
            )


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for one artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _directory_entries(directory: Path) -> dict[str, tuple[str, Path]]:
    """Inventory entries without following symlinks as regular files."""
    entries: dict[str, tuple[str, Path]] = {}
    for path in directory.rglob("*"):
        relative_path = str(path.relative_to(directory))
        if path.is_symlink():
            kind = "symlink"
        elif path.is_file():
            kind = "file"
        elif path.is_dir():
            kind = "directory"
        else:
            kind = "special"
        entries[relative_path] = (kind, path)
    return entries


def directory_changes(expected: Path, actual: Path) -> list[str]:
    """Return structural, content, and directory-mode changes."""
    expected_entries = _directory_entries(expected)
    actual_entries = _directory_entries(actual)
    changes = [
        f"missing: {name}"
        for name in sorted(set(expected_entries) - set(actual_entries))
    ]
    changes.extend(
        f"extra: {name}"
        for name in sorted(set(actual_entries) - set(expected_entries))
    )
    expected_mode = stat.S_IMODE(expected.stat().st_mode)
    actual_mode = stat.S_IMODE(actual.stat().st_mode)
    if expected_mode != actual_mode:
        changes.append(f"mode: . ({actual_mode:04o}, expected {expected_mode:04o})")
    changes.extend(_entry_changes(expected_entries, actual_entries))
    return changes


def _entry_changes(
    expected: dict[str, tuple[str, Path]],
    actual: dict[str, tuple[str, Path]],
) -> list[str]:
    """Compare common entry kinds and regular-file content."""
    changes: list[str] = []
    for name in sorted(set(expected) & set(actual)):
        expected_kind, expected_path = expected[name]
        actual_kind, actual_path = actual[name]
        if expected_kind != actual_kind:
            changes.append(
                f"type: {name} ({actual_kind}, expected {expected_kind})"
            )
        elif expected_kind == "file" and sha256_file(expected_path) != sha256_file(
            actual_path
        ):
            changes.append(f"changed: {name}")
    return changes


def _rollback_publish(
    staging_dir: Path,
    output_dir: Path,
    backup_dir: Path | None,
    had_existing: bool,
) -> None:
    """Restore the pre-publication directory layout after an interruption."""
    backup_exists = backup_dir is not None and backup_dir.exists()
    if backup_exists and output_dir.exists() and not staging_dir.exists():
        output_dir.rename(staging_dir)
    if backup_exists and backup_dir is not None and not output_dir.exists():
        backup_dir.rename(output_dir)
    if not had_existing and output_dir.exists() and not staging_dir.exists():
        output_dir.rename(staging_dir)


def publish_dataset(
    staging_dir: Path,
    output_dir: Path,
    datasets_dir: Path,
    force: bool,
) -> None:
    """Publish a complete staging directory with rollback on rename failure."""
    with dataset_lock(datasets_dir):
        _publish_dataset_locked(staging_dir, output_dir, datasets_dir, force)


def _publish_dataset_locked(
    staging_dir: Path,
    output_dir: Path,
    datasets_dir: Path,
    force: bool,
) -> None:
    """Perform the publication transaction while its dataset root is locked."""
    if output_dir.is_symlink():
        raise DatasetPublicationError(
            f"Refusing to replace dataset symlink: {output_dir}"
        )
    if output_dir.exists() and not output_dir.is_dir():
        raise DatasetPublicationError(f"Dataset path is not a directory: {output_dir}")
    if output_dir.exists() and not force:
        raise DatasetPublicationError(
            f"Dataset '{output_dir.name}' already exists. Use --force to replace it."
        )

    had_existing = output_dir.exists()
    backup_dir = (
        datasets_dir / f".{output_dir.name}.backup-{uuid.uuid4().hex}"
        if had_existing
        else None
    )
    try:
        if backup_dir is not None:
            output_dir.rename(backup_dir)
        staging_dir.rename(output_dir)
    except (OSError, KeyboardInterrupt) as exc:
        _handle_publish_error(
            exc, staging_dir, output_dir, backup_dir, had_existing
        )

    if backup_dir is not None:
        try:
            shutil.rmtree(backup_dir)
        except OSError as exc:
            raise DatasetPublicationError(
                "Dataset was published, but the previous dataset backup could "
                f"not be removed: {backup_dir}: {exc}"
            ) from exc


def _handle_publish_error(
    error: BaseException,
    staging_dir: Path,
    output_dir: Path,
    backup_dir: Path | None,
    had_existing: bool,
) -> None:
    """Roll back a failed transaction, then preserve the original exception."""
    try:
        _rollback_publish(staging_dir, output_dir, backup_dir, had_existing)
    except OSError as rollback_error:
        raise DatasetPublicationError(
            f"Cannot publish dataset ({error}); rollback also failed: "
            f"{rollback_error}. Recovery copy: {backup_dir}"
        ) from error
    if isinstance(error, OSError):
        raise DatasetPublicationError(f"Cannot publish dataset: {error}") from error
    raise error
