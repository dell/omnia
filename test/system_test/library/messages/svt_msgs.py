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

"""SVT operator-facing text: test log lines, assertion messages and stage output."""

TEST_LOG_MSGS = {
    "case_ok": "{case}: {count} FVT step(s) passed in {duration}",
    "case_failed": "{case}: FVT step {step} failed (rc={rc}) after {duration}",
}

TEST_ASSERT_MSGS = {
    "case_failed": (
        "SVT case {case} failed at: {step} (rc={rc}).\n"
        "HOW TO FIX:\n"
        "  1. Read the FVT output above and its report in {report_path}\n"
        "  2. Fix the cause and re-run: "
        "./run_validation.sh svt_{theme} system_verification --case {case} --resume"
    ),
}

STAGE_MSGS = {
    "start": "[{stage}] started (run {run_id}, theme {theme})",
    "passed": "[{stage}] PASSED in {duration}",
    "skipped": "[{stage}] SKIPPED: {reason}",
    "failed": "[{stage}] FAILED after {duration}: {error}",
    "step": "[{stage}] {label}",
    "step_failed": "{label} failed (rc={rc})",
    "no_previous_setup": "no previous Omnia setup ({path} missing): nothing to clean",
    "no_build_stream": "BuildStream is not installed ({path} missing): {label} not needed",
    "no_omnia_venv": "the Omnia venv is missing: {label} skipped (needs the Omnia venv)",
    "inputs_placed": "user inputs placed: {target}",
    "test_config_placed": "test_config placed: {target}",
    "venv_missing": (
        "the Omnia venv {path} is missing. HOW TO FIX: run the environment_setup "
        "stage (test/main: omnia.sh --setup-venv) first"
    ),
    "not_initialized": (
        "run {run_id} was not initialized on this checkout. HOW TO FIX: run the "
        "initialization stage first, or add --resume to continue the last initialized run"
    ),
    "nothing_to_resume": (
        "--resume found no initialized {theme} run on this checkout. HOW TO FIX: run "
        "the initialization stage (./run_validation.sh svt_{theme} initialization ...)"
    ),
    "repo_missing": "{path} not found: run the SVT from an Omnia checkout",
    "unknown_run": (
        "no SVT run found. HOW TO FIX: start with the initialization stage "
        "(./run_validation.sh svt_<theme> initialization ...) or pass --run-id"
    ),
    "creds_hint": (
        "Domain credentials are not part of this stage. Provide them before "
        "system_verification: the pipeline pipes them from OpenBao; locally run "
        "cd test/build_stream && ./setup_env.sh --set-domain-creds"
    ),
}
