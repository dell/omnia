# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for verified, non-authoritative artifact reuse."""

import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import git_artifact_processor
from ansible.module_utils.repo_manager import shared_artifact_state


LOGGER = logging.getLogger("repo-manager-shared-artifact-test")


class SharedArtifactStateTests(unittest.TestCase):
    """Prove cache reuse requires trusted state and matching bytes."""

    def _cache(self, root):
        return shared_artifact_state.SharedArtifactCache(root, LOGGER)

    def test_record_and_restore_verify_bytes_and_track_owner(self):
        """A verified source is restored and both logical owners are retained."""
        with tempfile.TemporaryDirectory() as root:
            source_dir = Path(root) / "offline_repo" / "cluster" / "10.0"
            target_dir = Path(root) / "offline_repo" / "cluster" / "10.2"
            source_dir.mkdir(parents=True)
            source = source_dir / "artifact.tar.gz"
            source.write_bytes(b"verified-content")
            cache = self._cache(root)
            key = shared_artifact_state.build_source_key(
                "tarball", "https://example.invalid/archive", compatibility="any"
            )

            self.assertTrue(cache.record(key, "tarball", [str(source)], "rhel-10.0"))
            restored = cache.restore(key, str(target_dir), "rhel-10.2")

            self.assertEqual(Path(restored[0]).read_bytes(), b"verified-content")
            state = json.loads(Path(cache.state_path).read_text(encoding="utf-8"))
            self.assertEqual(
                state["artifacts"][key]["owners"],
                ["rhel-10.0", "rhel-10.2"],
            )

    def test_digest_tamper_disables_reuse(self):
        """Changed canonical bytes never pass the recorded SHA-256 check."""
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.tar.gz"
            source.write_bytes(b"original")
            cache = self._cache(root)
            key = shared_artifact_state.build_source_key("tarball", "source")
            self.assertTrue(cache.record(key, "tarball", [str(source)], "first"))
            source.write_bytes(b"tampered")

            restored = cache.restore(key, str(Path(root) / "target"), "second")

            self.assertEqual(restored, [])

    def test_source_validator_mismatch_disables_reuse(self):
        """A moving HTTP source must match the validator recorded with bytes."""
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "manifest.yml"
            source.write_bytes(b"kind: ConfigMap\n")
            cache = self._cache(root)
            key = shared_artifact_state.build_source_key("manifest", "source")
            old_validator = {"etag": "old"}
            self.assertTrue(cache.record(
                key, "manifest", [str(source)], "first", old_validator
            ))

            restored = cache.restore(
                key,
                str(Path(root) / "target"),
                "second",
                {"etag": "new"},
            )

            self.assertEqual(restored, [])

    def test_symlink_state_directory_is_rejected(self):
        """The private state directory cannot redirect writes outside the root."""
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other:
            (Path(root) / ".data").symlink_to(other, target_is_directory=True)
            source = Path(root) / "artifact"
            source.write_bytes(b"data")
            cache = self._cache(root)

            result = cache.record("key", "tarball", [str(source)], "owner")

            self.assertFalse(result)
            self.assertEqual(list(Path(other).iterdir()), [])

    def test_corrupt_state_fails_closed_without_overwrite(self):
        """Corrupt ownership state is preserved for diagnosis and not trusted."""
        with tempfile.TemporaryDirectory() as root:
            cache = self._cache(root)
            state_path = Path(cache.state_path)
            state_path.parent.mkdir(parents=True)
            state_path.write_text("{not-json", encoding="utf-8")
            source = Path(root) / "artifact"
            source.write_bytes(b"data")

            result = cache.record("key", "tarball", [str(source)], "owner")

            self.assertFalse(result)
            self.assertEqual(state_path.read_text(encoding="utf-8"), "{not-json")

    def test_failed_atomic_replace_preserves_previous_state(self):
        """A failed state replacement leaves the last-known-good index intact."""
        with tempfile.TemporaryDirectory() as root:
            cache = self._cache(root)
            source = Path(root) / "artifact"
            source.write_bytes(b"data")
            self.assertTrue(cache.record("first", "tarball", [str(source)], "one"))
            before = Path(cache.state_path).read_bytes()

            with patch.object(
                    shared_artifact_state.os,
                    "replace",
                    side_effect=OSError("injected failure")):
                result = cache.record(
                    "second", "tarball", [str(source)], "two"
                )

            self.assertFalse(result)
            self.assertEqual(Path(cache.state_path).read_bytes(), before)
            temporary = list(Path(cache.state_path).parent.glob(
                ".shared_artifact_index.*.tmp"
            ))
            self.assertEqual(temporary, [])

    def test_path_outside_data_root_is_rejected(self):
        """The index cannot reference bytes outside its configured data root."""
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other:
            source = Path(other) / "artifact"
            source.write_bytes(b"outside")
            cache = self._cache(root)

            result = cache.record("key", "tarball", [str(source)], "owner")

            self.assertFalse(result)
            self.assertFalse(Path(cache.state_path).exists())

    def test_malformed_entry_fails_closed(self):
        """Schema-versioned JSON with invalid entry types is never trusted."""
        with tempfile.TemporaryDirectory() as root:
            cache = self._cache(root)
            state_path = Path(cache.state_path)
            state_path.parent.mkdir(parents=True)
            state_path.write_text(json.dumps({
                "schema_version": 1,
                "artifacts": {"key": {"files": "not-a-list"}},
            }), encoding="utf-8")

            result = cache.restore(
                "key", str(Path(root) / "target"), "owner"
            )

            self.assertEqual(result, [])

    def test_removing_one_owner_retains_another_verified_path(self):
        """One context cleanup preserves reuse through a remaining owner."""
        with tempfile.TemporaryDirectory() as root:
            first_dir = Path(root) / "offline_repo" / "cluster" / "10.0"
            second_dir = Path(root) / "offline_repo" / "cluster" / "10.2"
            first_dir.mkdir(parents=True)
            source = first_dir / "artifact.tar.gz"
            source.write_bytes(b"shared")
            cache = self._cache(root)
            self.assertTrue(cache.record(
                "key", "tarball", [str(source)], "rhel-10.0"
            ))
            restored = cache.restore("key", str(second_dir), "rhel-10.2")
            self.assertTrue(restored)

            self.assertTrue(cache.remove_owner("rhel-10.2"))
            Path(restored[0]).unlink()
            third = cache.restore(
                "key", str(Path(root) / "third"), "rhel-10.3"
            )

            self.assertEqual(Path(third[0]).read_bytes(), b"shared")

    def test_removing_final_owner_drops_private_cache_record(self):
        """Final-owner cleanup removes the hint without deleting source bytes."""
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "artifact.tar.gz"
            source.write_bytes(b"shared")
            cache = self._cache(root)
            self.assertTrue(cache.record(
                "key", "tarball", [str(source)], "only-owner"
            ))

            self.assertTrue(cache.remove_owner("only-owner"))

            state = json.loads(
                Path(cache.state_path).read_text(encoding="utf-8")
            )
            self.assertEqual(state["artifacts"], {})
            self.assertEqual(source.read_bytes(), b"shared")

    def test_absent_owner_is_a_successful_noop(self):
        """Cleanup can distinguish an absent owner from a state-write error."""
        with tempfile.TemporaryDirectory() as root:
            cache = self._cache(root)

            result = cache.remove_owner_result("not-recorded")

            self.assertEqual(result, {"success": True, "changed": False})

    def test_owner_removal_reports_atomic_write_failure(self):
        """Cleanup fails closed when ownership cannot be saved atomically."""
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "artifact.tar.gz"
            source.write_bytes(b"shared")
            cache = self._cache(root)
            self.assertTrue(cache.record(
                "key", "tarball", [str(source)], "owner"
            ))
            before = Path(cache.state_path).read_bytes()

            with patch.object(
                    shared_artifact_state.os,
                    "replace",
                    side_effect=OSError("injected failure")):
                result = cache.remove_owner_result("owner")

            self.assertEqual(result, {"success": False, "changed": False})
            self.assertEqual(Path(cache.state_path).read_bytes(), before)

    def test_type_cleanup_removes_only_selected_cache_hints(self):
        """A complete file cleanup retains unrelated private cache entries."""
        with tempfile.TemporaryDirectory() as root:
            cache = self._cache(root)
            tarball = Path(root) / "artifact.tar.gz"
            image = Path(root) / "image.json"
            tarball.write_bytes(b"tarball")
            image.write_bytes(b"image")
            self.assertTrue(cache.record(
                "tar", "tarball", [str(tarball)], "tar-owner"
            ))
            self.assertTrue(cache.record(
                "container", "image", [str(image)], "image-owner"
            ))

            result = cache.remove_artifact_types({"tarball", "pip_module"})

            self.assertEqual(result, {"success": True, "changed": True})
            state = json.loads(
                Path(cache.state_path).read_text(encoding="utf-8")
            )
            self.assertEqual(set(state["artifacts"]), {"container"})

    def test_weak_etag_without_other_validators_disables_reuse(self):
        """A weak ETag alone cannot prove that source bytes are unchanged."""
        response = Mock()
        response.url = "https://example.invalid/artifact"
        response.headers = {"ETag": 'W/"semantic"'}
        response.raise_for_status.return_value = None
        with patch.object(
                shared_artifact_state.requests,
                "head",
                return_value=response):
            result = shared_artifact_state.probe_http_validator(
                response.url, LOGGER
            )
        self.assertIsNone(result)


class GitArtifactProcessorTests(unittest.TestCase):
    """Prove a mutable Git ref is resolved before archiving."""

    def test_annotated_tag_prefers_peeled_commit(self):
        """An annotated tag uses the commit, not the tag object identity."""
        tag_object = "a" * 40
        commit = "b" * 40
        output = (
            f"{tag_object}\trefs/tags/v1.0\n"
            f"{commit}\trefs/tags/v1.0^{{}}\n"
        )
        with patch.object(
                git_artifact_processor,
                "_run_git",
                return_value=output):
            result = git_artifact_processor.resolve_git_ref(
                "https://example.invalid/repo.git", "v1.0"
            )
        self.assertEqual(result, commit)

    def test_ambiguous_branch_and_tag_fail_closed(self):
        """A name resolving to different branch/tag objects is rejected."""
        output = (
            f"{'a' * 40}\trefs/tags/release\n"
            f"{'b' * 40}\trefs/heads/release\n"
        )
        with patch.object(
                git_artifact_processor,
                "_run_git",
                return_value=output):
            with self.assertRaises(ValueError):
                git_artifact_processor.resolve_git_ref(
                    "https://example.invalid/repo.git", "release"
                )


if __name__ == "__main__":
    unittest.main()
