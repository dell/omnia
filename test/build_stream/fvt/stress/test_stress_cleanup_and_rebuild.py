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
Build Stream — Stress Test: Cleanup + Rebuild Cycles.

Runs repeated cycles of: build → cleanup → rebuild to validate that
the system can handle full lifecycle repetitions without degradation.

Adapted from automation_v22/molecule/build_stream/test_stress_cleanup_and_rebuild.py.
"""

import pytest

from library.functions import (
    TestLogger,
    trigger_build_pipeline,
    trigger_cleanup_pipeline,
    select_image_for_cleanup,
    play_cleanup_stage_job,
    wait_for_cleanup_completion,
    monitor_pipeline_stages,
    is_build_stream_enabled,
)
from library.vars.common_vars import (
    BUILD_PIPELINE_CORE_STAGES,
    STAGE_BUILD_IMAGE_X86_64,
    STAGE_BUILD_IMAGE_AARCH64,
    CLEANUP_WAIT_TIMEOUT,
)
from library.messages.build_stream_msgs import SKIP_MSGS


CLEANUP_REBUILD_CYCLES = 3


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.build_stream
@pytest.mark.stress
@pytest.mark.order(700)
class TestStressCleanupAndRebuild:
    """Stress test: repeated build → cleanup → rebuild cycles."""

    def test_cleanup_and_rebuild_cycles(self, host):
        """Run multiple build → cleanup → rebuild cycles."""
        log = TestLogger(
            f"Stress Test: {CLEANUP_REBUILD_CYCLES} Cleanup + Rebuild Cycles"
        )

        if not is_build_stream_enabled(host):
            log.skipped(SKIP_MSGS["build_stream_disabled"])
            pytest.skip(SKIP_MSGS["build_stream_disabled"])

        all_stages = BUILD_PIPELINE_CORE_STAGES + [
            STAGE_BUILD_IMAGE_X86_64,
            STAGE_BUILD_IMAGE_AARCH64,
        ]

        results = []
        failures = []

        for cycle in range(1, CLEANUP_REBUILD_CYCLES + 1):
            log.info(f"\n{'='*60}")
            log.info(f"=== Cycle {cycle}/{CLEANUP_REBUILD_CYCLES} ===")
            log.info(f"{'='*60}")

            cycle_result = {
                "cycle": cycle,
                "build_success": False,
                "cleanup_success": False,
                "error": "",
            }

            # --- BUILD PHASE ---
            log.info(f"\n--- Build Phase (cycle {cycle}) ---")
            trigger_result = trigger_build_pipeline(
                host, log_callback=log.info
            )
            if not trigger_result["success"]:
                cycle_result["error"] = (
                    f"Build trigger failed: {trigger_result['error']}"
                )
                results.append(cycle_result)
                failures.append(cycle_result)
                log.info(f"  [FAIL] Cycle {cycle} build: {cycle_result['error']}")
                break

            job_id = trigger_result.get("job_id", "")
            if not job_id:
                cycle_result["error"] = "No job_id returned from build"
                results.append(cycle_result)
                failures.append(cycle_result)
                log.info(f"  [FAIL] Cycle {cycle}: no job_id")
                break

            monitor_result = monitor_pipeline_stages(
                host, job_id, all_stages
            )
            if not monitor_result["success"]:
                cycle_result["error"] = (
                    f"Build stage failed: {monitor_result['failed_stage']} "
                    f"- {monitor_result['error']}"
                )
                results.append(cycle_result)
                failures.append(cycle_result)
                log.info(f"  [FAIL] Cycle {cycle} build: {cycle_result['error']}")
                break

            cycle_result["build_success"] = True
            log.info(f"  [OK] Cycle {cycle} build completed")

            # --- CLEANUP PHASE ---
            log.info(f"\n--- Cleanup Phase (cycle {cycle}) ---")
            cleanup_trigger = trigger_cleanup_pipeline(
                host, log_callback=log.info
            )
            if not cleanup_trigger["success"]:
                cycle_result["error"] = (
                    f"Cleanup trigger failed: {cleanup_trigger['error']}"
                )
                results.append(cycle_result)
                failures.append(cycle_result)
                log.info(
                    f"  [FAIL] Cycle {cycle} cleanup: {cycle_result['error']}"
                )
                break

            pipeline_id = cleanup_trigger["pipeline_id"]

            select_result = select_image_for_cleanup(
                host, pipeline_id, log_callback=log.info
            )
            if not select_result["success"]:
                cycle_result["error"] = (
                    f"Cleanup selection failed: {select_result['error']}"
                )
                results.append(cycle_result)
                failures.append(cycle_result)
                log.info(
                    f"  [FAIL] Cycle {cycle} cleanup: {cycle_result['error']}"
                )
                break

            play_result = play_cleanup_stage_job(
                host, pipeline_id, log_callback=log.info
            )
            if not play_result["success"]:
                cycle_result["error"] = (
                    f"Cleanup play failed: {play_result['error']}"
                )
                results.append(cycle_result)
                failures.append(cycle_result)
                log.info(
                    f"  [FAIL] Cycle {cycle} cleanup: {cycle_result['error']}"
                )
                break

            wait_result = wait_for_cleanup_completion(
                host,
                select_result["image_group_id"],
                timeout=CLEANUP_WAIT_TIMEOUT,
                log_callback=log.info,
            )
            if not wait_result["success"]:
                cycle_result["error"] = (
                    f"Cleanup wait failed: {wait_result['error']}"
                )
                results.append(cycle_result)
                failures.append(cycle_result)
                log.info(
                    f"  [FAIL] Cycle {cycle} cleanup: {cycle_result['error']}"
                )
                break

            cycle_result["cleanup_success"] = True
            log.info(f"  [OK] Cycle {cycle} cleanup completed")

            results.append(cycle_result)

        # Summary
        passed = sum(
            1 for r in results
            if r["build_success"] and r["cleanup_success"]
        )
        failed = len(failures)
        total = len(results)
        log.info(f"\n=== Cleanup + Rebuild Summary ===")
        log.info(f"Total cycles: {total}, Passed: {passed}, Failed: {failed}")

        if failures:
            for f in failures:
                log.info(f"  Failed cycle {f['cycle']}: {f['error']}")

        assert not failures, (
            f"Cleanup+rebuild stress test failed: {failed}/{total} cycles. "
            f"First failure: {failures[0]['error']}"
        )

        log.passed(
            f"Cleanup+rebuild stress test passed: "
            f"{passed}/{total} cycles completed"
        )
