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
Build Stream — Stress Test: Repeated Build Pipelines.

Triggers multiple sequential build pipelines to validate system stability
under repeated build load. Each iteration:
1. Uploads catalog → triggers build pipeline
2. Monitors all build stages
3. Verifies artifacts (registry, S3)
4. Records pass/fail per iteration

Adapted from automation_v22/molecule/build_stream/test_stress_build_pipeline.py.
"""

import pytest

from library.functions import (
    TestLogger,
    trigger_build_pipeline,
    monitor_pipeline_stages,
    get_catalog_roles,
    verify_registry_images,
    verify_s3_boot_images,
    is_build_stream_enabled,
)
from library.vars.common_vars import (
    BUILD_PIPELINE_CORE_STAGES,
    STAGE_BUILD_IMAGE_X86_64,
    STAGE_BUILD_IMAGE_AARCH64,
    STRESS_BUILD_PIPELINE_COUNT,
    STRESS_STOP_ON_FIRST_FAILURE,
)
from library.messages.build_stream_msgs import SKIP_MSGS


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.build_stream
@pytest.mark.stress
@pytest.mark.order(500)
class TestStressBuildPipeline:
    """Stress test: repeated build pipeline executions."""

    def test_stress_build_pipelines(self, host):
        """Run multiple build pipelines sequentially."""
        log = TestLogger(
            f"Stress Test: {STRESS_BUILD_PIPELINE_COUNT} Build Pipelines"
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

        for iteration in range(1, STRESS_BUILD_PIPELINE_COUNT + 1):
            log.info(f"=== Iteration {iteration}/{STRESS_BUILD_PIPELINE_COUNT} ===")

            iteration_result = {
                "iteration": iteration,
                "pipeline_id": 0,
                "job_id": "",
                "success": False,
                "error": "",
            }

            # 1. Trigger build pipeline
            trigger_result = trigger_build_pipeline(host, log_callback=log.info)
            if not trigger_result["success"]:
                iteration_result["error"] = (
                    f"Trigger failed: {trigger_result['error']}"
                )
                results.append(iteration_result)
                failures.append(iteration_result)
                log.info(
                    f"  [FAIL] Iteration {iteration}: {iteration_result['error']}"
                )
                if STRESS_STOP_ON_FIRST_FAILURE:
                    break
                continue

            iteration_result["pipeline_id"] = trigger_result["pipeline_id"]
            iteration_result["job_id"] = trigger_result.get("job_id", "")

            if not iteration_result["job_id"]:
                iteration_result["error"] = "No job_id returned"
                results.append(iteration_result)
                failures.append(iteration_result)
                log.info(f"  [FAIL] Iteration {iteration}: no job_id")
                if STRESS_STOP_ON_FIRST_FAILURE:
                    break
                continue

            # 2. Monitor all stages
            monitor_result = monitor_pipeline_stages(
                host, iteration_result["job_id"], all_stages
            )

            if not monitor_result["success"]:
                iteration_result["error"] = (
                    f"Stage failed: {monitor_result['failed_stage']} "
                    f"- {monitor_result['error']}"
                )
                results.append(iteration_result)
                failures.append(iteration_result)
                log.info(
                    f"  [FAIL] Iteration {iteration}: {iteration_result['error']}"
                )
                if STRESS_STOP_ON_FIRST_FAILURE:
                    break
                continue

            # 3. Verify artifacts
            roles_result = get_catalog_roles(
                host, iteration_result["job_id"]
            )
            if roles_result["success"] and roles_result["roles"]:
                reg_result = verify_registry_images(
                    host, iteration_result["job_id"],
                    roles_result["roles"],
                    roles_result.get("image_key", ""),
                )
                s3_result = verify_s3_boot_images(
                    host, iteration_result["job_id"],
                    roles_result["roles"],
                    roles_result.get("image_key", ""),
                )

                if not reg_result["success"]:
                    iteration_result["error"] = (
                        f"Registry verification failed: "
                        f"missing {reg_result['missing']}"
                    )
                    results.append(iteration_result)
                    failures.append(iteration_result)
                    log.info(
                        f"  [FAIL] Iteration {iteration}: "
                        f"{iteration_result['error']}"
                    )
                    if STRESS_STOP_ON_FIRST_FAILURE:
                        break
                    continue

                if not s3_result["success"]:
                    iteration_result["error"] = (
                        f"S3 verification failed: "
                        f"missing {[r['role'] for r in s3_result['missing_roles']]}"
                    )
                    results.append(iteration_result)
                    failures.append(iteration_result)
                    log.info(
                        f"  [FAIL] Iteration {iteration}: "
                        f"{iteration_result['error']}"
                    )
                    if STRESS_STOP_ON_FIRST_FAILURE:
                        break
                    continue

            iteration_result["success"] = True
            results.append(iteration_result)
            log.info(f"  [OK] Iteration {iteration} passed")

        # Summary
        passed = sum(1 for r in results if r["success"])
        failed = len(failures)
        total = len(results)
        log.info(f"\n=== Stress Test Summary ===")
        log.info(f"Total: {total}, Passed: {passed}, Failed: {failed}")

        if failures:
            for f in failures:
                log.info(
                    f"  Failed iteration {f['iteration']}: {f['error']}"
                )

        assert not failures, (
            f"Stress test failed: {failed}/{total} iterations failed. "
            f"First failure: {failures[0]['error']}"
        )

        log.passed(
            f"Stress test passed: {passed}/{total} build pipelines completed"
        )
