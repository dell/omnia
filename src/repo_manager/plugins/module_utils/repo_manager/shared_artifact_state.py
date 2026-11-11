# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Verified cross-context artifact-cache state.

This cache is an optimization hint, not public status and not proof that a
Pulp object is ready.  Every reuse verifies the stored file digest. Public
repositories, distributions, URLs, mirror indexes, and cleanup identities stay
version-qualified exactly as before.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
import shutil
import tempfile

import requests

from ansible.module_utils.repo_manager.security_utils import validate_artifact_url


SHARED_ARTIFACT_SCHEMA_VERSION = 1
_STATE_DIRECTORY_MODE = 0o700
_STATE_FILE_MODE = 0o600


class SharedArtifactStateError(RuntimeError):
    """Raised when cache state cannot be trusted without overwriting it."""


def build_source_key(artifact_type, source, version="", compatibility=""):
    """Return a deterministic identity for one declared artifact source."""
    identity = {
        "artifact_type": str(artifact_type or ""),
        "compatibility": str(compatibility or ""),
        "source": str(source or ""),
        "version": str(version or ""),
    }
    serialized = json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def file_sha256(file_path):
    """Return the SHA-256 digest of a regular, non-symlink file."""
    if os.path.islink(file_path) or not os.path.isfile(file_path):
        raise SharedArtifactStateError("Cached artifact is not a regular file")
    digest = hashlib.sha256()
    with open(file_path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_http_validator(url, logger, timeout=(10, 30)):
    """Return stable HTTP validators, or ``None`` when reuse is unprovable."""
    url = validate_artifact_url(url)
    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=timeout,
        )
        response.raise_for_status()
        final_url = validate_artifact_url(response.url)
        etag = str(response.headers.get("ETag") or "").strip()
        last_modified = str(
            response.headers.get("Last-Modified") or ""
        ).strip()
        content_length = str(
            response.headers.get("Content-Length") or ""
        ).strip()
        strong_etag = etag and not etag.casefold().startswith("w/")
        if not strong_etag and not (last_modified and content_length):
            logger.info("HTTP source has no stable reuse validator")
            return None
        return {
            "content_length": content_length,
            "etag": etag,
            "final_url": final_url,
            "last_modified": last_modified,
        }
    except (requests.RequestException, TypeError, ValueError):
        logger.info("HTTP source validator is unavailable; normal transfer required")
        return None


def _empty_state():
    return {
        "schema_version": SHARED_ARTIFACT_SCHEMA_VERSION,
        "artifacts": {},
    }


def _utc_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SharedArtifactCache:
    """Atomically record and restore verified artifacts below one data root."""

    def __init__(self, data_root, logger):
        self.data_root = os.path.realpath(os.path.abspath(data_root))
        self.logger = logger
        state_directory = os.path.join(self.data_root, ".data")
        self.state_path = os.path.join(
            state_directory, "shared_artifact_index.json"
        )
        self.lock_path = self.state_path + ".lock"

    @classmethod
    def from_content_base_dir(cls, content_base_dir, distribution_root, logger):
        """Resolve the configured data root from a version-qualified path."""
        normalized = os.path.realpath(os.path.abspath(content_base_dir))
        marker = os.sep + distribution_root.strip("/").replace("/", os.sep)
        marker += os.sep
        marker_index = normalized.rfind(marker)
        if marker_index <= 0:
            raise SharedArtifactStateError(
                "Content path is outside the configured distribution root"
            )
        return cls(normalized[:marker_index], logger)

    def _ensure_state_directory(self):
        state_directory = os.path.dirname(self.state_path)
        if os.path.lexists(state_directory) and os.path.islink(state_directory):
            raise SharedArtifactStateError(
                "Shared artifact state directory is a symlink"
            )
        os.makedirs(state_directory, mode=_STATE_DIRECTORY_MODE, exist_ok=True)
        if not os.path.isdir(state_directory):
            raise SharedArtifactStateError(
                "Shared artifact state path is not a directory"
            )
        os.chmod(state_directory, _STATE_DIRECTORY_MODE)

    @contextmanager
    def _locked(self):
        self._ensure_state_directory()
        descriptor = os.open(
            self.lock_path,
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
            _STATE_FILE_MODE,
        )
        try:
            os.fchmod(descriptor, _STATE_FILE_MODE)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _load(self):
        if not os.path.exists(self.state_path):
            return _empty_state()
        if os.path.islink(self.state_path):
            raise SharedArtifactStateError("Shared artifact state is a symlink")
        try:
            with open(self.state_path, "r", encoding="utf-8") as stream:
                state = json.load(stream)
        except (OSError, ValueError) as error:
            raise SharedArtifactStateError(
                "Shared artifact state cannot be parsed"
            ) from error
        if (
                not isinstance(state, dict)
                or state.get("schema_version") != SHARED_ARTIFACT_SCHEMA_VERSION
                or not isinstance(state.get("artifacts"), dict)):
            raise SharedArtifactStateError(
                "Shared artifact state has an unsupported schema"
            )
        return state

    def _save(self, state):
        self._ensure_state_directory()
        state_directory = os.path.dirname(self.state_path)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".shared_artifact_index.",
            suffix=".tmp",
            dir=state_directory,
        )
        try:
            os.fchmod(descriptor, _STATE_FILE_MODE)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(state, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.state_path)
            os.chmod(self.state_path, _STATE_FILE_MODE)
            directory_descriptor = os.open(
                state_directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            )
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def _contained_file(self, file_path):
        resolved = os.path.realpath(os.path.abspath(file_path))
        try:
            contained = os.path.commonpath((self.data_root, resolved)) == self.data_root
        except ValueError:
            contained = False
        if not contained:
            raise SharedArtifactStateError(
                "Cached artifact path escapes the configured data root"
            )
        return resolved

    def _file_records(self, file_paths):
        """Build verified, unambiguous records for one owner's files."""
        files = []
        for file_path in sorted(file_paths):
            resolved = self._contained_file(file_path)
            files.append({
                "name": os.path.basename(resolved),
                "path": resolved,
                "sha256": file_sha256(resolved),
                "size": os.path.getsize(resolved),
            })
        if len({entry["name"] for entry in files}) != len(files):
            raise SharedArtifactStateError(
                "Cached artifact names are ambiguous"
            )
        return files

    def record(self, source_key, artifact_type, file_paths, owner,
               source_validator=None):
        """Record a verified artifact set without changing public state."""
        if not source_key or not file_paths:
            return False
        try:
            files = self._file_records(file_paths)
            with self._locked():
                state = self._load()
                previous = state["artifacts"].get(source_key, {})
                if not isinstance(previous, dict):
                    raise SharedArtifactStateError(
                        "Shared artifact entry has an invalid structure"
                    )
                previous_owners = previous.get("owners", [])
                if not isinstance(previous_owners, list):
                    raise SharedArtifactStateError(
                        "Shared artifact owner list is invalid"
                    )
                owners = set(previous_owners)
                owner = str(owner)
                owners.add(owner)
                owner_files = previous.get("owner_files", {})
                if not isinstance(owner_files, dict):
                    raise SharedArtifactStateError(
                        "Shared artifact owner-file map is invalid"
                    )
                owner_files[owner] = files
                state["artifacts"][source_key] = {
                    "artifact_type": str(artifact_type),
                    "files": files,
                    "owner_files": owner_files,
                    "owners": sorted(owners),
                    "source_validator": source_validator or {},
                    "updated_at": _utc_timestamp(),
                }
                self._save(state)
            return True
        except (OSError, TypeError, SharedArtifactStateError):
            self.logger.error(
                "Shared artifact cache state is unavailable; reuse was not recorded"
            )
            return False

    def restore(self, source_key, destination, owner,
                source_validator=None):
        """Restore verified cached files, returning final paths or ``[]``."""
        if not source_key:
            return []
        try:
            with self._locked():
                state = self._load()
                entry = state["artifacts"].get(source_key)
                if not isinstance(entry, dict):
                    return []
                if source_validator is not None and (
                        entry.get("source_validator") != source_validator):
                    return []

                file_entries = entry.get("files")
                if not isinstance(file_entries, list):
                    raise SharedArtifactStateError(
                        "Shared artifact file list is invalid"
                    )
                source_files = []
                for file_entry in file_entries:
                    if not isinstance(file_entry, dict):
                        raise SharedArtifactStateError(
                            "Shared artifact file entry is invalid"
                        )
                    source_path = self._contained_file(file_entry.get("path", ""))
                    if (
                            os.path.basename(source_path) != file_entry.get("name")
                            or file_sha256(source_path) != file_entry.get("sha256")
                            or os.path.getsize(source_path) != file_entry.get("size")):
                        return []
                    source_files.append((source_path, file_entry))
                if not source_files:
                    return []

                os.makedirs(destination, exist_ok=True)
                restored = []
                for source_path, file_entry in source_files:
                    final_path = self._contained_file(
                        os.path.join(destination, file_entry["name"])
                    )
                    if os.path.exists(final_path):
                        if file_sha256(final_path) == file_entry["sha256"]:
                            restored.append(final_path)
                            continue
                    temporary_path = (
                        f"{final_path}.shared.{os.getpid()}.tmp"
                    )
                    try:
                        try:
                            os.link(source_path, temporary_path)
                        except OSError as error:
                            if error.errno not in (errno.EXDEV, errno.EPERM):
                                raise
                            shutil.copy2(source_path, temporary_path)
                        if file_sha256(temporary_path) != file_entry["sha256"]:
                            raise SharedArtifactStateError(
                                "Restored artifact failed digest verification"
                            )
                        os.replace(temporary_path, final_path)
                    finally:
                        if os.path.exists(temporary_path):
                            os.unlink(temporary_path)
                    restored.append(final_path)

                stored_owners = entry.get("owners", [])
                if not isinstance(stored_owners, list):
                    raise SharedArtifactStateError(
                        "Shared artifact owner list is invalid"
                    )
                owners = set(stored_owners)
                owner = str(owner)
                owners.add(owner)
                entry["owners"] = sorted(owners)
                restored_records = self._file_records(restored)
                entry["files"] = restored_records
                owner_files = entry.get("owner_files", {})
                if not isinstance(owner_files, dict):
                    raise SharedArtifactStateError(
                        "Shared artifact owner-file map is invalid"
                    )
                owner_files[owner] = restored_records
                entry["owner_files"] = owner_files
                entry["updated_at"] = _utc_timestamp()
                self._save(state)
                return restored
        except (OSError, TypeError, KeyError, SharedArtifactStateError):
            self.logger.error(
                "Shared artifact cache state is unavailable; normal processing required"
            )
            return []

    def remove_owner_result(self, owner):
        """Remove one logical owner and report success separately from change.

        The former boolean-only interface could not distinguish an unchanged
        cache from a failed atomic update.  Cleanup must make that distinction
        before it removes context-local files and status records.
        """
        owner = str(owner)
        if not owner:
            return {"success": False, "changed": False}
        if not os.path.lexists(self.state_path):
            return {"success": True, "changed": False}
        try:
            changed = False
            with self._locked():
                state = self._load()
                for source_key, entry in list(state["artifacts"].items()):
                    if not isinstance(entry, dict):
                        raise SharedArtifactStateError(
                            "Shared artifact entry has an invalid structure"
                        )
                    owners = entry.get("owners", [])
                    if not isinstance(owners, list):
                        raise SharedArtifactStateError(
                            "Shared artifact owner list is invalid"
                        )
                    if owner not in owners:
                        continue
                    changed = True
                    remaining_owners = sorted(set(owners) - {owner})
                    owner_files = entry.get("owner_files", {})
                    if not isinstance(owner_files, dict):
                        raise SharedArtifactStateError(
                            "Shared artifact owner-file map is invalid"
                        )
                    owner_files.pop(owner, None)
                    if not remaining_owners:
                        del state["artifacts"][source_key]
                        continue

                    replacement = None
                    for remaining_owner in remaining_owners:
                        candidate = owner_files.get(remaining_owner)
                        if isinstance(candidate, list) and candidate:
                            replacement = candidate
                            break
                    entry["owners"] = remaining_owners
                    entry["owner_files"] = owner_files
                    if replacement is not None:
                        entry["files"] = replacement
                    entry["updated_at"] = _utc_timestamp()
                if changed:
                    self._save(state)
            return {"success": True, "changed": changed}
        except (OSError, TypeError, SharedArtifactStateError):
            self.logger.error(
                "Shared artifact cache ownership could not be updated"
            )
            return {"success": False, "changed": False}

    def remove_owner(self, owner):
        """Backward-compatible boolean owner-removal interface."""
        result = self.remove_owner_result(owner)
        return result["success"] and result["changed"]

    def remove_artifact_types(self, artifact_types):
        """Remove cache hints for a verified complete type cleanup.

        This does not remove artifact bytes.  It is used only after an explicit
        ``cleanup_files=all`` operation has verified every discovered Pulp
        File/Python repository absent.  Removing the private hints also repairs
        stale owners left by an earlier interrupted cleanup.
        """
        normalized_types = {
            str(artifact_type) for artifact_type in artifact_types
            if str(artifact_type)
        }
        if not normalized_types:
            return {"success": False, "changed": False}
        if not os.path.lexists(self.state_path):
            return {"success": True, "changed": False}
        try:
            changed = False
            with self._locked():
                state = self._load()
                for source_key, entry in list(state["artifacts"].items()):
                    if not isinstance(entry, dict):
                        raise SharedArtifactStateError(
                            "Shared artifact entry has an invalid structure"
                        )
                    if str(entry.get("artifact_type", "")) in normalized_types:
                        del state["artifacts"][source_key]
                        changed = True
                if changed:
                    self._save(state)
            return {"success": True, "changed": changed}
        except (OSError, TypeError, SharedArtifactStateError):
            self.logger.error(
                "Shared artifact cache types could not be reconciled"
            )
            return {"success": False, "changed": False}
