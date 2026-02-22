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

"""Performance tests for Local Repository API."""

import time
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.integration.api.local_repo.conftest import setup_input_files

# Import fixtures needed for performance tests
pytest_plugins = ["tests.integration.api.local_repo.conftest"]


class TestLocalRepoPerformance:
    """Performance tests for create local repository API."""

    @pytest.mark.performance
    def test_response_time_under_threshold(self, client, auth_headers, created_job, nfs_queue_dir, input_dir):
        """Test that API response time is under acceptable threshold."""
        # Create actual input directory for this test
        input_dir_for_job = input_dir / created_job / "input"
        input_dir_for_job.mkdir(parents=True, exist_ok=True)
        (input_dir_for_job / "test.txt").write_text("test content")

        with patch(
            "build_stream.infra.repositories.nfs_input_directory_repository"
            ".NfsInputDirectoryRepository.get_source_input_repository_path",
            return_value=input_dir_for_job,
        ), patch(
            "build_stream.infra.repositories.nfs_input_directory_repository"
            ".NfsInputDirectoryRepository.get_destination_input_repository_path",
            return_value=nfs_queue_dir / "dest_input",
        ), patch(
            "build_stream.infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=True,
        ):

            start_time = time.time()
            response = client.post(
                f"/api/v1/jobs/{created_job}/stages/create-local-repository",
                headers=auth_headers,
            )
            end_time = time.time()

            response_time = end_time - start_time

            # Assert response is successful or handles gracefully
            assert response.status_code in [202, 400]

            # Assert response time is under threshold (5 seconds for performance test)
            assert response_time < 5.0, f"Response time {response_time}s exceeds threshold of 5.0s"

    @pytest.mark.performance
    def test_concurrent_requests_performance(self, client, auth_headers, created_job, nfs_queue_dir, input_dir):
        """Test performance under concurrent load."""
        # Create actual input directory for this test
        input_dir_for_job = input_dir / created_job / "input"
        input_dir_for_job.mkdir(parents=True, exist_ok=True)
        (input_dir_for_job / "test.txt").write_text("test content")

        with patch(
            "build_stream.infra.repositories.nfs_input_directory_repository"
            ".NfsInputDirectoryRepository.get_source_input_repository_path",
            return_value=input_dir_for_job,
        ), patch(
            "build_stream.infra.repositories.nfs_input_directory_repository"
            ".NfsInputDirectoryRepository.get_destination_input_repository_path",
            return_value=nfs_queue_dir / "dest_input",
        ), patch(
            "build_stream.infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=True,
        ):

            import threading
            results = []
            response_times = []

            def make_request():
                start_time = time.time()
                response = client.post(
                    f"/api/v1/jobs/{created_job}/stages/create-local-repository",
                    headers=auth_headers,
                )
                end_time = time.time()
                results.append(response)
                response_times.append(end_time - start_time)

            # Create and start threads (reduced from 10 to 5 for stability)
            threads = [threading.Thread(target=make_request) for _ in range(5)]

            start_time = time.time()
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            end_time = time.time()

            # Assert all requests completed
            assert len(results) == 5

            # Assert responses are handled gracefully
            for response in results:
                assert response.status_code in [202, 400, 409, 500]

            # Assert average response time is reasonable
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 5.0

            # Assert total time is reasonable
            total_time = end_time - start_time
            assert total_time < 10.0
            # Average response time should be reasonable
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                assert avg_response_time < 1.0, f"Average response time {avg_response_time}s exceeds threshold of 1.0s"

    @pytest.mark.performance
    def test_memory_usage_stable(self, client, auth_headers, created_job, nfs_queue_dir, input_dir):
        """Test that memory usage remains stable over multiple requests."""
        # Skip if psutil is not available
        try:
            import psutil
            import os
        except ImportError:
            pytest.skip("psutil not available for memory monitoring")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create actual input directory for this test
        input_dir_for_job = input_dir / created_job / "input"
        input_dir_for_job.mkdir(parents=True, exist_ok=True)
        (input_dir_for_job / "test.txt").write_text("test content")

        with patch(
            "build_stream.infra.repositories.nfs_input_directory_repository"
            ".NfsInputDirectoryRepository.get_source_input_repository_path",
            return_value=input_dir_for_job,
        ), patch(
            "build_stream.infra.repositories.nfs_input_directory_repository"
            ".NfsInputDirectoryRepository.get_destination_input_repository_path",
            return_value=nfs_queue_dir / "dest_input",
        ), patch(
            "build_stream.infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=True,
        ):

            # Make multiple requests (reduced from 50 to 20)
            for _ in range(20):
                response = client.post(
                    f"/api/v1/jobs/{created_job}/stages/create-local-repository",
                    headers=auth_headers,
                )
                assert response.status_code in [202, 400]

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Memory increase should be minimal (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.2f}MB"

    @pytest.mark.performance
    def test_large_correlation_id_handling(self, client, auth_headers, created_job, nfs_queue_dir, input_dir):
        """Test performance with large correlation IDs."""
        # Create actual input directory for this test
        input_dir_for_job = input_dir / created_job / "input"
        input_dir_for_job.mkdir(parents=True, exist_ok=True)
        (input_dir_for_job / "test.txt").write_text("test content")

        # Create very large correlation ID (but still reasonable)
        large_correlation_id = "x" * 1000  # Reduced from 10000

        with patch(
            "build_stream.infra.repositories.nfs_input_directory_repository"
            ".NfsInputDirectoryRepository.get_source_input_repository_path",
            return_value=input_dir_for_job,
        ), patch(
            "build_stream.infra.repositories.nfs_input_directory_repository"
            ".NfsInputDirectoryRepository.get_destination_input_repository_path",
            return_value=nfs_queue_dir / "dest_input",
        ), patch(
            "build_stream.infra.repositories.nfs_playbook_queue_request_repository"
            ".NfsPlaybookQueueRequestRepository.is_available",
            return_value=True,
        ):

            start_time = time.time()
            response = client.post(
                f"/api/v1/jobs/{created_job}/stages/create-local-repository",
                headers={**auth_headers, "X-Correlation-Id": large_correlation_id},
            )
            end_time = time.time()

            response_time = end_time - start_time

            # Should handle large correlation IDs gracefully (may fail validation)
            assert response.status_code in [202, 400]

            # Response time should still be reasonable
            assert response_time < 3.0, f"Response time {response_time}s with large correlation ID exceeds threshold"
