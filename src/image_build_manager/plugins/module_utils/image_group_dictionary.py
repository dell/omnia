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
"""Persistent global image-group dictionary for catalog-mode builds."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


DICTIONARY_VERSION = 1
REQUIRED_ENTRY_FIELDS = (
    "package_hash",
    "functional_group",
    "architecture",
    "image_group_id",
    "s3_paths",
)
REQUIRED_S3_PATHS = ("kernel", "initrd", "rootfs")


def utc_now() -> str:
    """Return a stable UTC timestamp suitable for persisted JSON."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def make_entry_key(
    package_hash: str, functional_group: str, architecture: str
) -> str:
    """Return a collision-safe key for one functional-group image."""
    return f"{architecture}:{functional_group}:{package_hash}"


def _empty_document() -> dict[str, Any]:
    """Return a new empty dictionary document."""
    return {
        "dictionary_version": DICTIONARY_VERSION,
        "entries": {},
        "last_updated": "",
    }


def _validate_entry(entry: Mapping[str, Any]) -> None:
    """Validate fields required to safely reuse a built image."""
    for field in REQUIRED_ENTRY_FIELDS:
        if not entry.get(field):
            raise ValueError(f"Dictionary entry requires non-empty {field}")

    s3_paths = entry["s3_paths"]
    if not isinstance(s3_paths, Mapping):
        raise ValueError("Dictionary entry s3_paths must be an object")
    for artifact in REQUIRED_S3_PATHS:
        if not s3_paths.get(artifact):
            raise ValueError(
                f"Dictionary entry requires non-empty s3_paths.{artifact}"
            )


def _validate_document(document: Any) -> dict[str, Any]:
    """Validate and normalize a dictionary document loaded from disk."""
    if not isinstance(document, dict):
        raise ValueError("Dictionary root must be a JSON object")
    if document.get("dictionary_version") != DICTIONARY_VERSION:
        raise ValueError(
            "Unsupported image-group dictionary version: "
            f"{document.get('dictionary_version')!r}"
        )
    entries = document.get("entries")
    if not isinstance(entries, dict):
        raise ValueError("Dictionary entries must be a JSON object")
    for entry in entries.values():
        if not isinstance(entry, dict):
            raise ValueError("Each dictionary entry must be a JSON object")
        _validate_entry(entry)
    document.setdefault("last_updated", "")
    return document


class ImageGroupDictionaryRepository:
    """Load, query, and atomically update the image-group dictionary."""

    def __init__(
        self,
        path: str | Path,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        """Create a repository for ``path`` using an injectable UTC clock."""
        self.path = Path(path)
        self.backup_path = self.path.with_suffix(f"{self.path.suffix}.bak")
        self._clock = clock
        self.load_error = ""
        self.recovered_from_backup = False

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        """Read and validate one JSON dictionary file."""
        with path.open("r", encoding="utf-8") as stream:
            return _validate_document(json.load(stream))

    def load(self) -> dict[str, Any]:
        """Load the primary file, recover from backup, or return empty state."""
        self.load_error = ""
        self.recovered_from_backup = False
        if not self.path.exists():
            return _empty_document()

        try:
            return self._read(self.path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.load_error = str(exc)

        if self.backup_path.exists():
            try:
                document = self._read(self.backup_path)
                self.recovered_from_backup = True
                return document
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self.load_error = f"{self.load_error}; backup: {exc}"

        return _empty_document()

    def _primary_is_valid(self) -> bool:
        """Return whether the primary file is safe to preserve as backup."""
        if not self.path.exists():
            return False
        try:
            self._read(self.path)
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        return True

    def _save(self, document: dict[str, Any]) -> None:
        """Atomically replace the dictionary while retaining a valid backup."""
        _validate_document(document)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self._primary_is_valid():
            shutil.copy2(self.path, self.backup_path)

        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(document, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary_path.chmod(0o644)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def lookup(
        self,
        package_hash: str,
        functional_group: str,
        architecture: str,
    ) -> dict[str, Any] | None:
        """Return and touch one matching entry, or ``None`` on a miss."""
        result = self.lookup_many(
            [
                {
                    "package_hash": package_hash,
                    "functional_group": functional_group,
                    "architecture": architecture,
                }
            ]
        )
        return result["hits"].get(functional_group)

    def lookup_many(
        self, candidates: Iterable[Mapping[str, str]]
    ) -> dict[str, Any]:
        """Resolve multiple candidates and persist one last-used update."""
        document = self.load()
        entries = document["entries"]
        hits: dict[str, dict[str, Any]] = {}
        misses: list[str] = []
        timestamp = self._clock()

        for candidate in candidates:
            package_hash = candidate.get("package_hash", "")
            functional_group = candidate.get("functional_group", "")
            architecture = candidate.get("architecture", "")
            if not package_hash or not functional_group or not architecture:
                raise ValueError(
                    "Dictionary lookup candidates require package_hash, "
                    "functional_group, and architecture"
                )
            key = make_entry_key(
                package_hash, functional_group, architecture
            )
            entry = entries.get(key)
            if entry is None:
                legacy_entry = entries.get(package_hash)
                if (
                    isinstance(legacy_entry, dict)
                    and legacy_entry.get("functional_group") == functional_group
                    and legacy_entry.get("architecture") == architecture
                ):
                    entry = legacy_entry
                    entries[key] = entries.pop(package_hash)

            if entry is None:
                misses.append(functional_group)
                continue

            _validate_entry(entry)
            entry["last_used_at"] = timestamp
            hits[functional_group] = deepcopy(entry)

        if hits:
            document["last_updated"] = timestamp
            self._save(document)
        return {"hits": hits, "misses": misses}

    def upsert(
        self,
        new_entries: Iterable[Mapping[str, Any]],
        catalog_schema_version: int | None = None,
    ) -> int:
        """Insert or replace reusable image entries and return their count."""
        materialized = [dict(entry) for entry in new_entries]
        if not materialized:
            return 0

        document = self.load()
        timestamp = self._clock()
        for entry in materialized:
            _validate_entry(entry)
            key = make_entry_key(
                str(entry["package_hash"]),
                str(entry["functional_group"]),
                str(entry["architecture"]),
            )
            existing = document["entries"].get(key, {})
            entry["created_at"] = existing.get("created_at", timestamp)
            entry["build_timestamp"] = timestamp
            entry["last_used_at"] = timestamp
            document["entries"][key] = entry

        if catalog_schema_version is not None:
            document["catalog_schema_version"] = catalog_schema_version
        document["last_updated"] = timestamp
        self._save(document)
        return len(materialized)

    def prune(self, image_group_id: str) -> int:
        """Remove entries for one image group and return the removal count."""
        document = self.load()
        keys_to_remove = [
            key
            for key, entry in document["entries"].items()
            if entry.get("image_group_id") == image_group_id
            or entry.get("catalog_identifier") == image_group_id
        ]
        if not keys_to_remove:
            return 0
        for key in keys_to_remove:
            del document["entries"][key]
        document["last_updated"] = self._clock()
        self._save(document)
        return len(keys_to_remove)
