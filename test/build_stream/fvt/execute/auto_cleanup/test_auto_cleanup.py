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
Execute — Automated Image Cleanup (one test case per step).

Runs the pass the AutoCleanupScheduler runs every evaluation interval
(cleanup_cron.main() in omnia_build_stream), the way cadence is triggered
on demand instead of waiting for the interval:
  precheck  retention group of build_stream_config.yml valid, BuildStream
            container running, playbook-watcher active (skipped when
            retention.auto_cleanup_enabled is false)
  pass      pick the image group: pipeline.auto_cleanup_image_group_id, else the
            image the cadence test built first (skipped with "nothing to clean"
            when that build failed; still cleaned when only the cadence cycle
            failed), else the first BUILT/PASSED/FAILED group (none fails with
            "No images to clean"); mark it FAILED in build_stream_db, snapshot
            every image group and boot-images object, log the decision per
            group, run one pass (every FAILED image group is deleted, plus
            retention candidates) and wait until none is CLEANING; the cleanup
            playbook log streams with debug_mode: true, otherwise status lines
            are printed while it runs
  artifacts S3 objects, registry tags (regctl) and NFS artifacts of the cleaned
            image are gone

Runs after the cadence suite and before the pipeline_cleanup suite.
Markers: pipeline, automatic_cleanup, sanity.
  database  exactly the expected groups CLEANED, their jobs tombstoned and
            audited, every other group kept
  artifacts their S3 objects and NFS artifacts removed, others untouched
Markers: pipeline, automatic_cleanup, sanity.
"""

import pytest

from library.functions import (
    precheck_auto_cleanup_step,
    run_auto_cleanup_step,
    run_step,
    verify_auto_cleanup_artifacts_step,
    verify_auto_cleanup_db_step,
)
from library.vars import TEST_CASES as TC


@pytest.mark.pipeline
@pytest.mark.automatic_cleanup
@pytest.mark.sanity
@pytest.mark.order(40901)
def test_auto_cleanup_precheck(host):
    """Check the retention settings, the BuildStream container and playbook-watcher."""
    run_step(TC["auto_cleanup_precheck"], "Automated cleanup precheck", precheck_auto_cleanup_step,
             host)


@pytest.mark.pipeline
@pytest.mark.automatic_cleanup
@pytest.mark.sanity
@pytest.mark.order(40902)
def test_auto_cleanup_run_pass(host):
    """Run one cleanup_cron pass and wait until it is finalized."""
    run_step(TC["auto_cleanup_run_pass"], "Automated cleanup pass", run_auto_cleanup_step, host)


@pytest.mark.pipeline
@pytest.mark.automatic_cleanup
@pytest.mark.sanity
@pytest.mark.order(40903)
def test_auto_cleanup_db_updated(host):
    """Verify the cleaned groups in build_stream_db and that the others were kept."""
    run_step(TC["auto_cleanup_db_updated"], "Automated cleanup database records",
             verify_auto_cleanup_db_step, host)


@pytest.mark.pipeline
@pytest.mark.automatic_cleanup
@pytest.mark.sanity
@pytest.mark.order(40904)
def test_auto_cleanup_artifacts_removed(host):
    """Verify the S3 objects and NFS artifacts of the cleaned groups are gone."""
    run_step(TC["auto_cleanup_artifacts_removed"], "Automated cleanup artifacts",
             verify_auto_cleanup_artifacts_step, host)
