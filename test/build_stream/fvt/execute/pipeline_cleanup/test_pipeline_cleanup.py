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

"""
Execute — Image Cleanup Pipeline (one test case per step).

build     build a dedicated image group for this suite (the next unused
          catalog version through the build pipeline, up to build-image); no
          build when pipeline.cleanup_image_group_id names an image group,
          which is used instead. A failed build fails this test and the
          trigger test that follows is skipped with that reason (no pipeline
          is triggered).
The suite does not depend on the images other suites leave behind.

Trigger PIPELINE_TYPE=cleanup through the API (running pipelines cancelled
when allowed), wait for list_images to offer the group and play its
select_image job; play the manual cleanup job (DELETE /api/v1/jobs/<job>)
and follow the image group CLEANING -> CLEANED with the cleanup playbook log
streamed (debug_mode: true; else tail -f and status lines); the cleanup and
summary jobs must succeed. Then build_stream_db (CLEANED, audit events;
the job tombstone is reported only), S3 (no boot-images object of the group),
registry (no tag of the group) and the NFS artifact directory, each its own
test case.
Markers: pipeline, cleanup_pipeline, sanity.
"""

import pytest

from library.functions import (
    build_pipeline_cleanup_image_step,
    run_pipeline_cleanup,
    run_step,
    start_pipeline_cleanup,
    verify_pipeline_cleanup_db,
    verify_pipeline_cleanup_nfs,
    verify_pipeline_cleanup_registry,
    verify_pipeline_cleanup_s3,
)
from library.vars import TEST_CASES as TC


@pytest.mark.pipeline
@pytest.mark.cleanup_pipeline
@pytest.mark.sanity
@pytest.mark.order(41000)
def test_pipeline_cleanup_build_image(host):
    """Build the image group the cleanup pipeline deletes, unless one is configured."""
    run_step(TC["pipeline_cleanup_build_image"], "Cleanup pipeline image build",
             build_pipeline_cleanup_image_step, host)


@pytest.mark.pipeline
@pytest.mark.cleanup_pipeline
@pytest.mark.sanity
@pytest.mark.order(41001)
def test_pipeline_cleanup_trigger_select(host):
    """Take the image group, trigger PIPELINE_TYPE=cleanup and select the group."""
    run_step(TC["pipeline_cleanup_trigger_select"], "Cleanup pipeline trigger",
             start_pipeline_cleanup, host)


@pytest.mark.pipeline
@pytest.mark.cleanup_pipeline
@pytest.mark.sanity
@pytest.mark.order(41002)
def test_pipeline_cleanup_run_cleanup_job(host):
    """Play the cleanup job and follow the image group to CLEANED."""
    run_step(TC["pipeline_cleanup_run_cleanup_job"], "Cleanup job", run_pipeline_cleanup, host)


@pytest.mark.pipeline
@pytest.mark.cleanup_pipeline
@pytest.mark.sanity
@pytest.mark.order(41003)
def test_pipeline_cleanup_db_cleaned(host):
    """Verify the image group is CLEANED and audited (tombstone reported only)."""
    run_step(TC["pipeline_cleanup_db_cleaned"], "Cleanup database records",
             verify_pipeline_cleanup_db, host)


@pytest.mark.pipeline
@pytest.mark.cleanup_pipeline
@pytest.mark.sanity
@pytest.mark.order(41004)
def test_pipeline_cleanup_s3_deleted(host):
    """Verify no boot-images object of the image group is left."""
    run_step(TC["pipeline_cleanup_s3_deleted"], "Cleanup S3 objects", verify_pipeline_cleanup_s3,
             host)


@pytest.mark.pipeline
@pytest.mark.cleanup_pipeline
@pytest.mark.sanity
@pytest.mark.order(41005)
def test_pipeline_cleanup_registry_deleted(host):
    """Verify no registry tag of the image group is left."""
    run_step(TC["pipeline_cleanup_registry_deleted"], "Cleanup registry images",
             verify_pipeline_cleanup_registry, host)


@pytest.mark.pipeline
@pytest.mark.cleanup_pipeline
@pytest.mark.sanity
@pytest.mark.order(41006)
def test_pipeline_cleanup_nfs_removed(host):
    """Verify the job's NFS artifact directory is removed."""
    run_step(TC["pipeline_cleanup_nfs_removed"], "Cleanup NFS artifacts",
             verify_pipeline_cleanup_nfs, host)
