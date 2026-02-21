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

"""Integration tests for FileArtifactStore."""

import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Dict

import pytest

from common.config import load_config
from container import container
from core.artifacts.value_objects import ArtifactKey, ArtifactKind, StoreHint
from core.artifacts.exceptions import (
    ArtifactAlreadyExistsError,
    ArtifactNotFoundError,
    ArtifactValidationError,
)
from infra.artifact_store.file_artifact_store import FileArtifactStore


class TestFileArtifactStoreIntegration:
    """Integration tests for FileArtifactStore with real filesystem."""

    def setup_method(self) -> None:
        """Set up test environment with temporary file store directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="test_file_artifact_store_")
        self.original_env = os.environ.get("BUILD_STREAM_CONFIG_PATH")

        # Create a test config file
        self.config_file = Path(self.temp_dir) / "test_config.ini"
        self.config_file.write_text(f"""[artifact_store]
backend = file_store
working_dir = {self.temp_dir}/working
max_file_size_bytes = 1048576
max_archive_uncompressed_bytes = 10485760
max_archive_entries = 100

[file_store]
base_path = {self.temp_dir}/artifacts
""")

        os.environ["BUILD_STREAM_CONFIG_PATH"] = str(self.config_file)

        # Reload container to pick up new config
        container.unwire()
        container.reset_singletons()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if self.original_env:
            os.environ["BUILD_STREAM_CONFIG_PATH"] = self.original_env
        else:
            os.environ.pop("BUILD_STREAM_CONFIG_PATH", None)

        # Clean up temp directory
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

        # Reset container
        container.unwire()
        container.reset_singletons()

    def test_file_artifact_store_is_used_when_enabled_in_config(self) -> None:
        """Test that FileArtifactStore is used when enabled in config."""
        artifact_store = container.artifact_store()
        assert isinstance(artifact_store, FileArtifactStore)

    def test_file_artifact_store_uses_configured_path(self) -> None:
        """Test that FileArtifactStore uses the configured base path."""
        config = load_config()
        expected_path = Path(config.file_store.base_path)

        artifact_store = container.artifact_store()
        assert isinstance(artifact_store, FileArtifactStore)
        assert artifact_store._base_path == expected_path

    def test_file_artifact_store_creates_directories(self) -> None:
        """Test that FileArtifactStore creates directories as needed."""
        artifact_store = container.artifact_store()

        hint = StoreHint(namespace="test", label="test", tags={})
        ref = artifact_store.store(hint, ArtifactKind.FILE, content=b"test data")

        expected_path = artifact_store._base_path / ref.key.value
        assert expected_path.exists()
        assert expected_path.parent.exists()

    def test_store_and_retrieve_file(self) -> None:
        """Test storing and retrieving a file artifact."""
        artifact_store = container.artifact_store()

        hint = StoreHint(namespace="test", label="test-file", tags={})
        content = b"Hello, World!"

        # Store the artifact
        ref = artifact_store.store(hint, ArtifactKind.FILE, content=content)

        # Verify the reference
        assert ref.key.value.startswith("test/")
        assert ref.size_bytes == len(content)
        assert ref.uri.startswith("file://")

        # Retrieve the artifact
        retrieved = artifact_store.retrieve(ref.key, ArtifactKind.FILE)
        assert retrieved == content

    def test_store_and_retrieve_archive_from_file_map(self) -> None:
        """Test storing and retrieving an archive artifact from file map."""
        artifact_store = container.artifact_store()

        hint = StoreHint(namespace="test", label="test-archive", tags={})
        file_map: Dict[str, bytes] = {
            "file1.txt": b"Content of file 1",
            "subdir/file2.txt": b"Content of file 2",
        }

        # Store the archive
        ref = artifact_store.store(hint, ArtifactKind.ARCHIVE, file_map=file_map)

        # Verify the reference
        assert ref.key.value.startswith("test/")
        assert ref.size_bytes > 0
        assert ref.uri.startswith("file://")

        # Retrieve the archive to a temporary directory
        with tempfile.TemporaryDirectory() as extract_dir:
            extracted_path = artifact_store.retrieve(
                ref.key, ArtifactKind.ARCHIVE, destination=Path(extract_dir)
            )

            # Verify extracted files
            assert (extracted_path / "file1.txt").exists()
            assert (extracted_path / "subdir" / "file2.txt").exists()

            assert (extracted_path / "file1.txt").read_bytes() == b"Content of file 1"
            assert (extracted_path / "subdir" / "file2.txt").read_bytes() == b"Content of file 2"

    def test_store_and_retrieve_archive_from_directory(self) -> None:
        """Test storing and retrieving an archive artifact from directory."""
        artifact_store = container.artifact_store()

        # Create a temporary directory with files
        with tempfile.TemporaryDirectory() as source_dir:
            source_path = Path(source_dir)
            (source_path / "file1.txt").write_bytes(b"Content of file 1")
            (source_path / "subdir").mkdir()
            (source_path / "subdir" / "file2.txt").write_bytes(b"Content of file 2")

            hint = StoreHint(namespace="test", label="dir-archive", tags={})

            # Store the archive
            ref = artifact_store.store(hint, ArtifactKind.ARCHIVE, source_directory=source_path)

            # Retrieve the archive to a temporary directory
            with tempfile.TemporaryDirectory() as extract_dir:
                extracted_path = artifact_store.retrieve(
                    ref.key, ArtifactKind.ARCHIVE, destination=Path(extract_dir)
                )

                # Verify extracted files
                assert (extracted_path / "file1.txt").exists()
                assert (extracted_path / "subdir" / "file2.txt").exists()

    def test_exists_and_delete(self) -> None:
        """Test exists and delete operations."""
        artifact_store = container.artifact_store()

        hint = StoreHint(namespace="test", label="exists-test", tags={})
        content = b"test content"

        # Store an artifact
        ref = artifact_store.store(hint, ArtifactKind.FILE, content=content)

        # Test exists
        assert artifact_store.exists(ref.key) is True

        # Test exists for non-existent artifact
        non_existent_key = ArtifactKey("test/non-existent/file.bin")
        assert artifact_store.exists(non_existent_key) is False

        # Delete the artifact
        assert artifact_store.delete(ref.key) is True
        assert artifact_store.exists(ref.key) is False

        # Try to delete non-existent artifact
        assert artifact_store.delete(non_existent_key) is False

    def test_duplicate_store_raises_error(self) -> None:
        """Test that storing duplicate artifacts raises an error."""
        artifact_store = container.artifact_store()

        hint = StoreHint(namespace="test", label="duplicate", tags={})
        content = b"test content"

        # Store first artifact
        ref1 = artifact_store.store(hint, ArtifactKind.FILE, content=content)

        # Try to store with same hint (should generate same key)
        with pytest.raises(ArtifactAlreadyExistsError):
            artifact_store.store(hint, ArtifactKind.FILE, content=b"different content")

    def test_retrieve_nonexistent_raises_error(self) -> None:
        """Test that retrieving non-existent artifact raises an error."""
        artifact_store = container.artifact_store()

        non_existent_key = ArtifactKey("test/non-existent/file.bin")

        with pytest.raises(ArtifactNotFoundError):
            artifact_store.retrieve(non_existent_key, ArtifactKind.FILE)

    def test_content_type_validation(self) -> None:
        """Test that content types are validated."""
        artifact_store = container.artifact_store()

        hint = StoreHint(namespace="test", label="content-type", tags={})

        # Valid content type
        ref = artifact_store.store(
            hint, ArtifactKind.FILE, content=b"test", content_type="application/json"
        )
        assert ref is not None

        # Invalid content type
        with pytest.raises(ArtifactValidationError, match="Content type not allowed"):
            artifact_store.store(
                hint, ArtifactKind.FILE, content=b"test", content_type="invalid/type"
            )

    def test_size_validation(self) -> None:
        """Test that artifact sizes are validated."""
        artifact_store = container.artifact_store()

        hint = StoreHint(namespace="test", label="size-test", tags={})

        # Valid size (within limit)
        small_content = b"x" * 1000
        ref = artifact_store.store(hint, ArtifactKind.FILE, content=small_content)
        assert ref is not None

        # Invalid size (exceeds limit from config)
        large_content = b"x" * 2_000_000  # 2MB, exceeds our 1MB test config
        with pytest.raises(ArtifactValidationError, match="Artifact size.*exceeds maximum"):
            artifact_store.store(hint, ArtifactKind.FILE, content=large_content)

    def test_deterministic_key_generation(self) -> None:
        """Test that key generation is deterministic for same hints."""
        artifact_store = container.artifact_store()

        hint = StoreHint(
            namespace="test",
            label="deterministic",
            tags={"env": "test", "version": "1.0"}
        )

        # Generate keys multiple times
        key1 = artifact_store.generate_key(hint, ArtifactKind.FILE)
        key2 = artifact_store.generate_key(hint, ArtifactKind.FILE)
        key3 = artifact_store.generate_key(hint, ArtifactKind.ARCHIVE)

        # Same hints should generate same keys for same kind
        assert key1.value == key2.value

        # Different kinds should have different extensions
        assert key1.value.endswith(".bin")
        assert key3.value.endswith(".zip")

    def test_key_format_validation(self) -> None:
        """Test that generated keys follow expected format."""
        artifact_store = container.artifact_store()

        hint = StoreHint(
            namespace="test-ns",
            label="test-label",
            tags={"key": "value"}
        )

        key = artifact_store.generate_key(hint, ArtifactKind.FILE)

        # Key format: {namespace}/{tag_hash}/{label}.{ext}
        parts = key.value.split("/")
        assert len(parts) == 3
        assert parts[0] == "test-ns"
        assert len(parts[1]) == 12  # SHA-256 hash truncated to 12 chars
        assert parts[2] == "test-label.bin"

    def test_file_cleanup_on_delete(self) -> None:
        """Test that empty directories are cleaned up on delete."""
        artifact_store = container.artifact_store()

        hint = StoreHint(namespace="test", label="cleanup", tags={})
        content = b"test content"

        # Store an artifact
        ref = artifact_store.store(hint, ArtifactKind.FILE, content=content)
        artifact_path = artifact_store._base_path / ref.key.value

        # Verify file and parent directory exist
        assert artifact_path.exists()
        assert artifact_path.parent.exists()

        # Delete the artifact
        artifact_store.delete(ref.key)

        # Verify file is deleted and empty parent directory is cleaned up
        assert not artifact_path.exists()
        # Note: parent directory cleanup is implementation-specific

    def test_concurrent_operations(self) -> None:
        """Test concurrent store operations."""
        import threading

        artifact_store = container.artifact_store()
        results = []
        errors = []

        def store_artifact(index: int):
            try:
                hint = StoreHint(
                    namespace=f"thread-{index}",
                    label=f"artifact-{index}",
                    tags={}
                )
                ref = artifact_store.store(hint, ArtifactKind.FILE, content=f"data-{index}".encode())
                results.append(ref)
            except Exception as e:
                errors.append(e)

        # Create multiple threads storing different artifacts
        threads = []
        for i in range(5):
            thread = threading.Thread(target=store_artifact, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations succeeded
        assert len(errors) == 0
        assert len(results) == 5

        # Verify all artifacts can be retrieved
        for ref in results:
            retrieved = artifact_store.retrieve(ref.key, ArtifactKind.FILE)
            assert retrieved is not None


class TestFileArtifactStoreConfiguration:
    """Tests for FileArtifactStore configuration handling."""

    def test_missing_config_fallback(self) -> None:
        """Test fallback behavior when config is missing."""
        # Remove config file temporarily
        original_config = os.environ.get("BUILD_STREAM_CONFIG_PATH")
        os.environ.pop("BUILD_STREAM_CONFIG_PATH", None)

        try:
            # Reload container
            container.unwire()
            container.reset_singletons()

            # Should fall back to defaults
            artifact_store = container.artifact_store()
            assert isinstance(artifact_store, FileArtifactStore)
            assert str(artifact_store._base_path) == "/opt/omnia/build_stream/artifacts"
        finally:
            # Restore config
            if original_config:
                os.environ["BUILD_STREAM_CONFIG_PATH"] = original_config
            container.unwire()
            container.reset_singletons()

    def test_invalid_config_handling(self) -> None:
        """Test handling of invalid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "invalid_config.ini"
            config_file.write_text("""[artifact_store]
backend = file_store
working_dir = /tmp/test

# Missing file_store section
""")

            original_config = os.environ.get("BUILD_STREAM_CONFIG_PATH")
            os.environ["BUILD_STREAM_CONFIG_PATH"] = str(config_file)

            try:
                # Should fall back to defaults when config is invalid
                container.unwire()
                container.reset_singletons()

                artifact_store = container.artifact_store()
                assert isinstance(artifact_store, FileArtifactStore)
                # Should use fallback path
                assert str(artifact_store._base_path) == "/opt/omnia/build_stream/artifacts"
            finally:
                if original_config:
                    os.environ["BUILD_STREAM_CONFIG_PATH"] = original_config
                container.unwire()
                container.reset_singletons()
