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
Build Stream — Stress Test: Repeated Cleanup Pipelines.

Triggers cleanup for all available image groups one by one to validate
that the cleanup pipeline can handle multiple sequential cleanups.

Adapted from automation_v22/molecule/build_stream/test_stress_cleanup_pipeline.py.
"""

import pytest

from library.functions import (
    TestLogger,
    trigger_cleanup_pipeline,
    select_image_for_cleanup,
    play_cleanup_stage_job,
    wait_for_cleanup_completion,
    get_all_image_groups,
    is_build_stream_enabled,
)
from library.vars.common_vars import CLEANUP_WAIT_TIMEOUT
from library.messages.build_stream_msgs import SKIP_MSGS


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.build_stream
@pytest.mark.stress
@pytest.mark.cleanup
@pytest.mark.order(600)
class TestStressCleanupPipeline:
    """Stress test: clean all available image groups sequentially."""

    def test_stress_cleanup_all_image_groups(self, host):
        """Clean all non-CLEANED image groups one by one."""
        log = TestLogger("Stress Test: Cleanup All Image Groups")

        if not is_build_stream_enabled(host):
            log.skipped(SKIP_MSGS["build_stream_disabled"])
            pytest.skip(SKIP_MSGS["build_stream_disabled"])

        # Get all cleanable image groups
        ig_result = get_all_image_groups(host)
        assert ig_result["success"], (
            f"Failed to get image groups: {ig_result['error']}"
        )

        cleanable = [
            g for g in ig_result["image_groups"]
            if g["status"] != "CLEANED"
        ]

        if not cleanable:
            log.skipped("No cleanable image groups found")
            pytest.skip("No cleanable image groups found")

        log.info(f"Found {len(cleanable)} cleanable image group(s)")

        results = []
        failures = []

        for idx, group in enumerate(cleanable, 1):
            group_id = group.get("id", "")
            group_status = group.get("status", "")
            log.info(
                f"\n--- Cleanup {idx}/{len(cleanable)}: "
                f"{group_id} (status: {group_status}) ---"
            )

            iteration_result = {
                "iteration": idx,
                "image_group_id": group_id,
                "success": False,
                "error": "",
            }

            # 1. Trigger cleanup pipeline
            trigger_result = trigger_cleanup_pipeline(
                host, log_callback=log.info
            )
            if not trigger_result["success"]:
                iteration_result["error"] = (
                    f"Trigger failed: {trigger_result['error']}"
                )
                results.append(iteration_result)
                failures.append(iteration_result)
                log.info(f"  [FAIL] {group_id}: {iteration_result['error']}")
                continue

            pipeline_id = trigger_result["pipeline_id"]

            # 2. Select image for cleanup
            select_result = select_image_for_cleanup(
                host, pipeline_id, log_callback=log.info
            )
            if not select_result["success"]:
                iteration_result["error"] = (
                    f"Selection failed: {select_result['error']}"
                )
                results.append(iteration_result)
                failures.append(iteration_result)
                log.info(f"  [FAIL] {group_id}: {iteration_result['error']}")
                continue

            # 3. Play cleanup job
            play_result = play_cleanup_stage_job(
                host, pipeline_id, log_callback=log.info
            )
            if not play_result["success"]:
                iteration_result["error"] = (
                    f"Play job failed: {play_result['error']}"
                )
                results.append(iteration_result)
                failures.append(iteration_result)
                log.info(f"  [FAIL] {group_id}: {iteration_result['error']}")
                continue

            # 4. Wait for cleanup completion
            wait_result = wait_for_cleanup_completion(
                host,
                select_result["image_group_id"],
                timeout=CLEANUP_WAIT_TIMEOUT,
                log_callback=log.info,
            )
            if not wait_result["success"]:
                iteration_result["error"] = (
                    f"Cleanup wait failed: {wait_result['error']}"
                )
                results.append(iteration_result)
                failures.append(iteration_result)
                log.info(f"  [FAIL] {group_id}: {iteration_result['error']}")
                continue

            iteration_result["success"] = True
            results.append(iteration_result)
            log.info(f"  [OK] {group_id} cleaned successfully")

        # Summary
        passed = sum(1 for r in results if r["success"])
        failed = len(failures)
        total = len(results)
        log.info(f"\n=== Stress Cleanup Summary ===")
        log.info(f"Total: {total}, Passed: {passed}, Failed: {failed}")

        if failures:
            for f in failures:
                log.info(
                    f"  Failed #{f['iteration']} ({f['image_group_id']}): "
                    f"{f['error']}"
                )

        assert not failures, (
            f"Stress cleanup failed: {failed}/{total} cleanups failed. "
            f"First failure: {failures[0]['error']}"
        )

        log.passed(
            f"Stress cleanup passed: {passed}/{total} image groups cleaned"
        )
