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

"""Integration tests for parse catalog API with artifact storage."""

import json
import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

from common.config import load_config
from container import container
from core.artifacts.value_objects import ArtifactKind, StoreHint
from core.jobs.value_objects import ClientId, CorrelationId, IdempotencyKey, JobId
from infra.artifact_store.file_artifact_store import FileArtifactStore
from orchestrator.catalog.commands.parse_catalog import ParseCatalogCommand
from orchestrator.jobs.commands import CreateJobCommand


class TestFileArtifactStorage:  # pylint: disable=attribute-defined-outside-init
    """Integration tests for file-based artifact storage."""

    def setup_method(self) -> None:
        """Set up test environment with temporary file store directory."""
        self.temp_file_dir = None
        self.original_env = None
        self.config_file = None

        self.temp_file_dir = tempfile.mkdtemp(prefix="test_file_")
        self.original_env = os.environ.get("BUILD_STREAM_CONFIG_PATH")
        self.config_file = None

        # Create a test config file
        self.config_file = Path(self.temp_file_dir) / "test_config.ini"
        self.config_file.write_text(f"""[artifact_store]
backend = file_store
working_dir = {self.temp_file_dir}/working

[file_store]
base_path = {self.temp_file_dir}/artifacts
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
        if Path(self.temp_file_dir).exists():
            shutil.rmtree(self.temp_file_dir)

        # Reset container
        container.unwire()
        container.reset_singletons()

    def test_file_artifact_store_is_used_when_enabled(self) -> None:
        """Test that FileArtifactStore is used when enabled in config."""
        artifact_store = container.artifact_store()
        assert isinstance(artifact_store, FileArtifactStore)

    def test_parse_catalog_creates_artifacts_on_file_store(self) -> None:  # pylint: disable=too-many-locals
        """Test that parse catalog creates artifact files on file store."""
        # Load a valid catalog from fixtures
        fixtures_dir = Path(__file__).parent.parent.parent.parent
        catalog_fixture_path = fixtures_dir / "fixtures" / "catalogs" / "catalog_rhel.json"
        with open(catalog_fixture_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

        catalog_bytes = json.dumps(catalog_data).encode('utf-8')

        # Create job first
        create_job_use_case = container.create_job_use_case()
        job_command = CreateJobCommand(
            client_id=ClientId("test-client"),
            request_client_id="test-client",
            correlation_id=CorrelationId(str(uuid.uuid4())),
            idempotency_key=IdempotencyKey(str(uuid.uuid4())),
            client_name="Test Client",
        )
        job_result = create_job_use_case.execute(job_command)
        job_id = JobId(job_result.job_id)

        # Execute parse catalog
        parse_catalog_use_case = container.parse_catalog_use_case()
        command = ParseCatalogCommand(
            job_id=job_id,
            correlation_id=CorrelationId(str(uuid.uuid4())),
            filename="catalog.json",
            content=catalog_bytes,
        )

        result = parse_catalog_use_case.execute(command)

        # Verify result
        assert result.stage_state == "COMPLETED"
        assert result.catalog_ref is not None
        assert result.root_jsons_ref is not None

        # Verify artifacts exist on file store
        file_base = Path(self.temp_file_dir) / "artifacts"

        # Check catalog file exists
        catalog_key = result.catalog_ref.key.value
        catalog_path = file_base / catalog_key
        assert catalog_path.exists(), f"Catalog artifact not found at {catalog_path}"
        assert catalog_path.is_file()

        # Verify catalog content
        catalog_content = catalog_path.read_bytes()
        assert len(catalog_content) > 0

        # Check root JSONs archive exists
        root_jsons_key = result.root_jsons_ref.key.value
        root_jsons_path = file_base / root_jsons_key
        assert root_jsons_path.exists(), f"Root JSONs artifact not found at {root_jsons_path}"
        assert root_jsons_path.is_file()

        # Verify root JSONs archive content
        root_jsons_content = root_jsons_path.read_bytes()
        assert len(root_jsons_content) > 0

        # Verify it's a valid zip file
        with zipfile.ZipFile(root_jsons_path, 'r') as zip_file:
            zip_file.testzip()  # Test zip file integrity
            file_list = zip_file.namelist()
            assert len(file_list) > 0, "Root JSONs archive is empty"
            # Should contain JSON files
            json_files = [f for f in file_list if f.endswith('.json')]
            assert len(json_files) > 0, "No JSON files in root JSONs archive"

    def test_artifact_retrieval_from_file_store(self) -> None:
        """Test that artifacts can be retrieved from file store."""
        artifact_store = container.artifact_store()

        # Store a test artifact
        hint = StoreHint(
            namespace="test",
            label="test-file",
            tags={"test_id": str(uuid.uuid4())},
        )

        test_content = b"Test artifact content"

        ref = artifact_store.store(
            hint=hint,
            kind=ArtifactKind.FILE,
            content=test_content,
            content_type="text/plain",
        )

        # Verify artifact exists on file store
        file_base = Path(self.temp_file_dir) / "artifacts"
        artifact_path = file_base / ref.key.value
        assert artifact_path.exists()

        # Retrieve artifact
        retrieved_content = artifact_store.retrieve(
            key=ref.key,
            kind=ArtifactKind.FILE,
        )

        assert retrieved_content == test_content

    def test_artifact_deletion_from_file_store(self) -> None:
        """Test that artifacts can be deleted from file store."""
        artifact_store = container.artifact_store()

        # Store a test artifact
        hint = StoreHint(
            namespace="test",
            label="test-delete",
            tags={"test_id": str(uuid.uuid4())},
        )

        ref = artifact_store.store(
            hint=hint,
            kind=ArtifactKind.FILE,
            content=b"To be deleted",
            content_type="text/plain",
        )

        # Verify artifact exists
        file_base = Path(self.temp_file_dir) / "artifacts"
        artifact_path = file_base / ref.key.value
        assert artifact_path.exists()

        # Delete artifact
        deleted = artifact_store.delete(ref.key)
        assert deleted is True

        # Verify artifact is gone
        assert not artifact_path.exists()

    def test_working_dir_is_used_for_temp_files(self) -> None:
        """Test that working_dir from config is used for temporary files."""
        config = load_config()
        working_dir = Path(config.artifact_store.working_dir)

        # Verify it's the temp directory we configured
        assert str(working_dir) == f"{self.temp_file_dir}/working"

        # Create working directory if it doesn't exist (simulates what the service does)
        working_dir.mkdir(parents=True, exist_ok=True)

        # Verify working directory exists
        assert working_dir.exists()
        assert working_dir.is_dir()

    def test_archive_artifact_storage_on_file_store(self) -> None:
        """Test that archive artifacts are stored correctly on file store."""
        artifact_store = container.artifact_store()

        # Create a file map for archive
        file_map = {
            "file1.txt": b"Content of file 1",
            "subdir/file2.txt": b"Content of file 2",
            "subdir/file3.json": b'{"key": "value"}',
        }

        hint = StoreHint(
            namespace="test",
            label="test-archive",
            tags={"test_id": str(uuid.uuid4())},
        )

        ref = artifact_store.store(
            hint=hint,
            kind=ArtifactKind.ARCHIVE,
            file_map=file_map,
            content_type="application/zip",
        )

        # Verify archive exists on file store
        file_base = Path(self.temp_file_dir) / "artifacts"
        archive_path = file_base / ref.key.value
        assert archive_path.exists()
        assert archive_path.suffix == ".zip"

        # Retrieve and verify archive contents
        temp_extract_dir = Path(tempfile.mkdtemp(prefix="test_extract_"))

        try:
            extracted_path = artifact_store.retrieve(
                key=ref.key,
                kind=ArtifactKind.ARCHIVE,
                destination=temp_extract_dir,
            )

            # Verify all files were extracted
            assert (extracted_path / "file1.txt").exists()
            assert (extracted_path / "subdir" / "file2.txt").exists()
            assert (extracted_path / "subdir" / "file3.json").exists()

            # Verify content
            assert (extracted_path / "file1.txt").read_bytes() == b"Content of file 1"
        finally:
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)
