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
    "test_config_placed": "test_config placed: {target}",
    "theme_mismatch": (
        "{path} selects theme {config_theme!r}, not {theme!r}. HOW TO FIX: set "
        "theme: {theme} there and run ./setup_env.sh again, or run "
        "./run_validation.sh svt_{config_theme}"
    ),
    "not_ready": "the OIM is not ready for the SVT:{problems}",
    "ready": "setup checked: inputs configured, Omnia installed, test requirements and "
             "credentials set",
    "stale_input": "WARNING: {path} differs from its src input (./setup_env.sh --yes "
                   "re-stages it)",
    "not_initialized": (
        "run {run_id} was not initialized on this checkout. HOW TO FIX: run the "
        "initialization stage first, or add --resume to continue the last initialized run"
    ),
    "nothing_to_resume": (
        "--resume found no initialized {theme} run on this checkout. HOW TO FIX: run "
        "the initialization stage (./run_validation.sh svt_{theme} initialization)"
    ),
    "repo_missing": "{path} not found: run the SVT from an Omnia checkout",
    "unknown_run": (
        "no SVT run found. HOW TO FIX: start with the initialization stage "
        "(./run_validation.sh svt_<theme> initialization) or pass --run-id"
    ),
}

SETUP_MSGS = {
    # driver
    "start": "[{action}] started (theme {theme}, log {log})",
    "passed": "[{action}] PASSED in {duration}",
    "skipped": "[{action}] SKIPPED: {reason}",
    "failed": "[{action}] FAILED after {duration}: {error}",
    "all_stopped": "setup stopped at {action}; fix it and run ./setup_env.sh again "
                   "(finished steps are repeated quickly)",
    # configure
    "configure_inputs": "configuring: {inputs} -> src/<domain>/input and src/main/omnia.env "
                        "(profile {profile})",
    "generator_failed": "the dataset generator failed (rc={rc}). HOW TO FIX: correct "
                        "user_inputs.yml as the generator output above says, then run "
                        "./setup_env.sh again",
    "configure_flags": "writing the cleanup flags of {config} into the suites' test_config.yml",
    "configure_first": "the inputs are not configured. HOW TO FIX: ./setup_env.sh "
                       "(or ./setup_env.sh --configure)",
    "inputs_changed": (
        "{path} changed after the last configure. HOW TO FIX: ./setup_env.sh "
        "(configures and installs again)"
    ),
    # cleanup
    "cleanup_disabled": "{label} skipped: cleanup.{domain}.enabled is false",
    "cleanup_nothing": "no cleanup step to run",
    "cleanup_plan": "these cleanup steps delete the previous installation of this OIM:",
    "cleanup_prompt": "Type 'yes' to run them (or re-run with --yes): ",
    "cleanup_confirmed_yes": "confirmed by --yes",
    "cleanup_declined": "cleanup not confirmed: nothing was deleted",
    "cleanup_needs_yes": (
        "cleanup needs a confirmation and no terminal is attached. HOW TO FIX: add --yes"
    ),
    # install
    "previous_setup": "{path} exists: Omnia is set up again on top of it. For a clean "
                      "installation use ./setup_env.sh --install --force (cleanup first)",
    "force_env": "{src} differs from {path}: adding --force-env (omnia_force_env: true)",
    "keep_env": "WARNING: {src} differs from {path} and omnia_force_env is false: "
                "the installed values are kept",
    "omnia_setup": "running ./omnia.sh {command} (it creates the Omnia venv; no activation needed)",
    "omnia_setup_failed": "omnia.sh -s failed (rc={rc}). HOW TO FIX: read its output above "
                          "(also in the log), fix the cause, run ./setup_env.sh again",
    "setup_incomplete": "omnia.sh -s finished but the setup is incomplete:",
    "refresh_inputs": "unattended: domain-init.sh --force for {domain} (its runtime inputs "
                      "differ from src)",
    "stale_input": (
        "WARNING: {path} differs from its src input (domain-init kept the existing "
        "file). To use the src value: answer y when asked, or add --yes"
    ),
    "requirements": "installing the {domain} test requirements into {venv}",
    "requirements_current": "{domain} test requirements already in {venv} (unchanged): skipped",
    "requirements_outdated": "not installed or changed: {domains}. "
                             "HOW TO FIX: ./setup_env.sh --install",
    "install_first": "Omnia was not installed by the SVT. HOW TO FIX: ./setup_env.sh",
    "install_failed": "the last install failed ({error}). HOW TO FIX: ./setup_env.sh",
    "install_again": "the inputs were configured again after the last install. HOW TO FIX: "
                     "./setup_env.sh",
    # creds
    "setup_missing": "Omnia is not set up (omnia.sh -s has not run). HOW TO FIX: "
                     "./setup_env.sh (or ./setup_env.sh --install) first:",
    "unknown_domain": "unknown domain {domain!r}; use one of: {known}",
    "creds_run": "test/{suite}/setup_env.sh {command} in the Omnia venv (prompts are not logged)",
    "creds_state": "  {domain:<20} {state}",
    "creds_failed": "the credential setup failed (rc={rc}); see the output above",
    "creds_all_set": "every domain credential store is already set "
                     "(change one with ./setup_env.sh --update-domain-creds --domain <d>)",
    "creds_need_stdin": (
        "credential stores missing: {domains}, and no terminal to ask on. HOW TO FIX: pipe "
        "the JSON keyed by domain to stdin, e.g. provider | ./setup_env.sh --yes"
    ),
    "creds_stdin_too_large": "the credential JSON on stdin exceeds {limit} bytes",
    "creds_incomplete": "still missing: {domains}. HOW TO FIX: "
                        "./setup_env.sh --set-domain-creds --domain <domain>",
    "creds_after_install": "set after the install (./setup_env.sh)",
    "creds_missing": "{domain} credentials are missing at {path}. HOW TO FIX: "
                     "./setup_env.sh --set-domain-creds --domain {domain}",
    # checks (omnia_func)
    "no_omnia_env": "{path} is missing: omnia.sh -s has not run. "
                    "HOW TO FIX: ./setup_env.sh",
    "env_key_missing": "{key} is not set in {path}. HOW TO FIX: set it in user_inputs.yml "
                       "(main.omnia_env), then ./setup_env.sh",
    "setup_path_missing": "{path} is missing: omnia.sh -s did not complete. "
                          "HOW TO FIX: ./setup_env.sh",
    "venv_not_active": (
        "the Omnia venv {venv} is not active and could not be activated (active: {active}). "
        "HOW TO FIX: ./setup_env.sh (creates it), or {hint}"
    ),
}

CONFIG_MSGS = {
    "unreadable": "{path}: cannot read ({error})",
    "invalid_yaml": "{path}: invalid YAML: {error}",
    "not_mapping": "{path}: {where} must be a key: value mapping",
    "not_bool": "{path}: {where} must be true or false, not {value!r}",
    "unknown_theme": "{path}: theme {theme!r} is not supported (supported: {known})",
    "unknown_suite": "{path}: cleanup has unknown suite(s) {names} (known: {known})",
    "unknown_flag": "{path}: cleanup.{suite} has unknown key(s) {names} (known: {known})",
    "suite_section_missing": "{path}: has no {section!r} section to write the cleanup flags into",
    "suite_key_missing": "{path}: has no {key!r} key; the suite no longer supports this flag",
    "flag_set": "  {path}: {key}: {old} -> {new}",
    "flags_current": "  every suite's cleanup flags already match test_config.yml",
}
