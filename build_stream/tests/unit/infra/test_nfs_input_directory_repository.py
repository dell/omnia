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

"""Unit tests for NfsInputDirectoryRepository."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.jobs.value_objects import JobId
from infra.repositories.nfs_input_repository import (
    NfsInputRepository,
)


class TestNfsInputRepository:
    """Tests for NfsInputRepository."""

    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return NfsInputRepository()

    @pytest.fixture
    def job_id(self):
        """Provide a valid job ID."""
        return JobId(str(uuid.uuid4()))

    def test_get_source_input_repository_path(self, repository, job_id):
        """Test getting source input repository path."""
        path = repository.get_source_input_repository_path(str(job_id))

        expected = Path(f"/opt/omnia/build_stream/{job_id}/input")
        assert path == expected
        assert isinstance(path, Path)

    def test_get_destination_input_repository_path(self, repository):
        """Test getting destination input repository path."""
        path = repository.get_destination_input_repository_path()

        expected = Path("/opt/omnia/input/project_default/")
        assert path == expected
        assert isinstance(path, Path)

    def test_validate_input_directory_success(self, repository, tmp_path):
        """Test successful validation of input directory."""
        # Create required files
        (tmp_path / "omnia.yml").touch()
        (tmp_path / "devices.yml").touch()
        (tmp_path / "network.yml").touch()

        result = repository.validate_input_directory(tmp_path)

        assert result is True

    def test_validate_input_directory_missing_files(self, repository, tmp_path):
        """Test validation fails when directory is empty."""
        # Create no files

        result = repository.validate_input_directory(tmp_path)

        assert result is False

    def test_validate_input_directory_nonexistent(self, repository):
        """Test validation fails for non-existent directory."""
        nonexistent_path = Path("/nonexistent/path")

        result = repository.validate_input_directory(nonexistent_path)

        assert result is False

    def test_validate_input_directory_not_a_directory(self, repository, tmp_path):
        """Test validation fails when path is not a directory."""
        # Create a file instead of directory
        file_path = tmp_path / "not_a_directory.txt"
        file_path.touch()

        result = repository.validate_input_directory(file_path)

        assert result is False

    def test_validate_input_directory_empty(self, repository, tmp_path):
        """Test validation fails for empty directory."""
        # Directory exists but is empty
        assert tmp_path.exists()
        assert len(list(tmp_path.iterdir())) == 0

        result = repository.validate_input_directory(tmp_path)

        assert result is False

    def test_validate_input_directory_with_subdirs(self, repository, tmp_path):
        """Test validation works with subdirectories present."""
        # Create required files
        (tmp_path / "omnia.yml").touch()
        (tmp_path / "devices.yml").touch()
        (tmp_path / "network.yml").touch()

        # Create subdirectories (should not affect validation)
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "extra_file.txt").touch()

        result = repository.validate_input_directory(tmp_path)

        assert result is True

    def test_validate_input_directory_permission_error(self, repository):
        """Test validation handles permission errors gracefully."""
        # Use a non-existent path to simulate permission error
        nonexistent_path = Path("/root/nonexistent/path")

        result = repository.validate_input_directory(nonexistent_path)

        assert result is False

    def test_custom_base_paths(self):
        """Test repository with custom base paths."""
        custom_build_stream_base = "/custom/build_stream"
        custom_playbook_input_dir = "/custom/input"

        repo = NfsInputRepository(
            build_stream_base=custom_build_stream_base,
            playbook_input_dir=custom_playbook_input_dir,
        )

        job_id = JobId(str(uuid.uuid4()))

        source_path = repo.get_source_input_repository_path(str(job_id))
        assert source_path == Path(f"{custom_build_stream_base}/{job_id}/input")

        dest_path = repo.get_destination_input_repository_path()
        assert dest_path == Path(custom_playbook_input_dir)


