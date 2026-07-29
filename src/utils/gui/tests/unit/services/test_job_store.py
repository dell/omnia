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

"""Unit tests for JobStore."""

import pytest

from backend.services.job_store import JobStore, TooManyConcurrentJobsError


class TestJobStore:
    """Tests for JobStore."""

    def test_create_job_returns_id(self):
        store = JobStore()
        job_id = store.create_job()
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    def test_get_job_returns_state(self):
        store = JobStore()
        job_id = store.create_job()
        job = store.get_job(job_id)
        assert job is not None
        assert job["status"] == "pending"
        assert job["progress"] == 0

    def test_get_nonexistent_job_returns_none(self):
        store = JobStore()
        assert store.get_job("nonexistent") is None

    def test_status_transition_pending_to_in_progress(self):
        store = JobStore()
        job_id = store.create_job()
        store.update_job(job_id, status="in_progress")
        assert store.get_job(job_id)["status"] == "in_progress"

    def test_status_transition_in_progress_to_completed(self):
        store = JobStore()
        job_id = store.create_job()
        store.update_job(job_id, status="in_progress")
        store.update_job(job_id, status="completed")
        assert store.get_job(job_id)["status"] == "completed"

    def test_invalid_transition_ignored(self):
        store = JobStore()
        job_id = store.create_job()
        store.update_job(job_id, status="completed")  # pending → completed is invalid
        assert store.get_job(job_id)["status"] == "pending"

    def test_too_many_concurrent_jobs(self):
        store = JobStore(max_concurrent_jobs=1)
        store.create_job()
        with pytest.raises(TooManyConcurrentJobsError):
            store.create_job()

    def test_update_nonexistent_job_raises(self):
        store = JobStore()
        with pytest.raises(KeyError):
            store.update_job("nonexistent", status="in_progress")

    def test_progress_clamped(self):
        store = JobStore()
        job_id = store.create_job()
        store.update_job(job_id, progress=150)
        assert store.get_job(job_id)["progress"] == 100

    def test_progress_negative_clamped(self):
        store = JobStore()
        job_id = store.create_job()
        store.update_job(job_id, progress=-10)
        assert store.get_job(job_id)["progress"] == 0

    def test_delete_completed_job(self):
        store = JobStore()
        job_id = store.create_job()
        store.update_job(job_id, status="in_progress")
        store.update_job(job_id, status="completed")
        assert store.delete_job(job_id) is True
        assert store.get_job(job_id) is None

    def test_delete_pending_job_raises(self):
        store = JobStore()
        job_id = store.create_job()
        with pytest.raises(ValueError):
            store.delete_job(job_id)

    def test_list_jobs(self):
        store = JobStore()
        store.create_job()
        store.create_job()
        jobs = store.list_jobs()
        assert len(jobs) == 2

    def test_list_jobs_filtered(self):
        store = JobStore(max_concurrent_jobs=3)
        j1 = store.create_job()
        store.create_job()
        store.update_job(j1, status="in_progress")
        store.update_job(j1, status="completed")
        completed = store.list_jobs(status="completed")
        assert len(completed) == 1
