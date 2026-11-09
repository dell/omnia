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
    "test_ok": "{step} passed",
    "test_failed": "{step} failed (rc={rc})",
    "blocked": "not run: {test} of this stage failed earlier",
}

TEST_ASSERT_MSGS = {
    "test_failed": (
        "{step} failed (rc={rc}).\n"
        "HOW TO FIX:\n"
        "  1. Read the output above (also in the SVT report of the run)\n"
        "  2. Fix the cause, start a new run (./setup_env.sh --theme {theme} --configure), "
        "then ./run_validation.sh svt_{theme} {stage} (or all)"
    ),
}

STAGE_MSGS = {
    "start": "[{stage}] started (run {run_id}, theme {theme})",
    "passed": "[{stage}] PASSED in {duration}",
    "skipped": "[{stage}] SKIPPED: {reason}",
    "failed": "[{stage}] FAILED after {duration}: {error}",
    "step": "[{stage}] {label}",
    "tests_failed": "SVT tests of stage {stage} failed (pytest rc={rc}); see the run "
                    "folder {path}",
    "step_failed": "{label} failed (rc={rc})",
    "no_previous_setup": "no previous Omnia setup ({path} missing): nothing to clean",
    "not_installed": "nothing to remove ({path} missing): {label} not needed",
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
    "repo_missing": "{path} not found: run the SVT from an Omnia checkout",
    "no_manifest": "run {run_id} has no initialization stage yet: only its report is "
                   "rendered",
    "output": "[{stage}] output: {row}",
    "state": "{label}: {created} created in this run, {leftover} left behind (statuses a run "
             "should not leave; report only)",
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
    "configure_flags": "writing the cleanup flags and FVT settings of {config} into the "
                       "suites' test_config.yml",
    "configure_report": "one report for this run: {report_path}/{report_name} "
                        "(run {run_id}); written into every suite's test_config.yml",
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
    "initializer_cleanup_plan": "every src/<domain>/domain-init.sh --cleanup "
                                "(input and log artifacts)",
    "cleanup_all_warning": (
        "cleanup_all: omnia.sh --cleanup --all deletes the whole {data} (every domain's "
        "input, output and logs, the credential stores, anything else kept there)"
    ),
    "cleanup_all_credentials": (
        "WARNING: cleanup_credentials is false for {suites}, but cleanup_all deletes "
        "the credential stores with OMNIA_DATA_PATH; ./setup_env.sh asks for them again"
    ),
    "report_inside_data": (
        "the report directory {path} is inside OMNIA_DATA_PATH, which cleanup_all "
        "deletes. HOW TO FIX: set report.report_path in <theme>_test_config.yml outside it "
        "(default: test/system_test/reports)"
    ),
    "report_failed": "WARNING: the SVT report was not updated: {error}",
    "report_written": "report: {path}",
    "cleanup_declined": "cleanup not confirmed: nothing was deleted",
    "cleanup_needs_yes": (
        "cleanup needs a confirmation and no terminal is attached. HOW TO FIX: add --yes"
    ),
    # install
    "previous_setup": "{path} exists: Omnia is set up again on top of it. For a clean "
                      "installation use ./setup_env.sh --install --force (cleanup first)",
    "force_env": "{src} differs from {path}: adding --force-env so the configured values "
                 "are used",
    "catalog_default": "catalog: user_inputs.yml main.catalog is empty; the default catalog "
                       "that omnia.sh -s installs stays active",
    "catalog_resolved": "catalog: user_inputs.yml main.catalog {selection} = {name}",
    "catalog_unknown": "user_inputs.yml main.catalog {selection!r} is not a catalog of "
                       "./omnia.sh --list-catalogs ({count} available). HOW TO FIX: use one of "
                       "the numbers or names it lists, or \"\" for the default catalog",
    "catalog_list_failed": "./omnia.sh --list-catalogs failed (rc={rc}); main.catalog "
                           "cannot be checked",
    "catalog_select": "activating catalog {name}: ./omnia.sh --select-catalog {name}",
    "catalog_select_failed": "./omnia.sh --select-catalog {name} failed (rc={rc}). HOW TO FIX: "
                             "read its output above, fix main.catalog in user_inputs.yml, run "
                             "./setup_env.sh again",
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
    "creds_next": "credentials stored. The 'Next steps' (./run_validation.sh fvt_...) and the "
                  "'No SSH credentials' lines above are printed by test/{suite}/setup_env.sh "
                  "for the FVT and do not apply to the SVT. Next: "
                  "./run_validation.sh svt_{theme} all",
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

RUN_MSGS = {
    "started": "run {run_id} started for theme {theme}: every step until the next "
               "./setup_env.sh --configure goes into {report_path}",
    "previous": "previous run {run_id} ({state}) stays in {report_path}",
    "none": "no SVT run is started. HOW TO FIX: ./setup_env.sh --configure starts one "
            "(./setup_env.sh with no action runs every step)",
    "theme_changed": "run {run_id} was started for theme {run_theme}, not {theme}. "
                     "HOW TO FIX: ./setup_env.sh --theme {theme} --configure starts a "
                     "run for {theme}",
    "settings_changed": "the report settings of the theme's test_config changed since run "
                        "{run_id} "
                        "was started ({field}: {old} -> {new}). HOW TO FIX: "
                        "./setup_env.sh --configure starts a new run",
    "failed": "run {run_id} has a failed step: {step} ({error}). A failed run takes no "
              "further step. HOW TO FIX: fix the cause, then ./setup_env.sh --configure "
              "starts a new run (the installation and the credentials are kept)",
    "fvt_failed": "run {run_id} has failed SVT sections: {modules}. A failed "
                  "run takes no further step. HOW TO FIX: fix the cause, then "
                  "./setup_env.sh --configure starts a new run",
    "report_theme": "{report} already holds run {run_id} of theme {report_theme}, not "
                    "{theme}. HOW TO FIX: clear report.run_id in the theme's test_config (a new "
                    "run id) or use another report_path",
    "run_id_mismatch": "--run-id {given} is not the current run {run_id} (set by "
                       "./setup_env.sh --configure). HOW TO FIX: drop --run-id, or "
                       "./setup_env.sh --configure to start a new run",
    "marked_failed": "run {run_id} is now failed at {step}; the next step needs a new run: "
                     "./setup_env.sh --configure",
    "retry_other": "--retry: run {run_id} failed at {step}, which is not what this command "
                   "runs ({allowed}). HOW TO FIX: retry that step first, or "
                   "./setup_env.sh --configure starts a new run",
    "retrying": "retrying run {run_id}: {step} failed earlier ({error}); the new attempt "
                "replaces it in the report and the earlier one is kept in its history",
    "retry_resume": "--retry resumes at {stage}: the stages before it passed in this run",
    "retry_done": "--retry: every stage of run {run_id} already passed; only summary runs",
}

LOCK_MSGS = {
    "held": "another SVT step is running on this OIM: {step} (pid {pid}, run {run_id}, "
            "heartbeat {heartbeat}). HOW TO FIX: wait for it, or stop it; a lock whose "
            "process is gone is taken over automatically",
    "interrupted": "WARNING: the previous step {step} (pid {pid}) ended without an outcome "
                   "(interrupted: kill, lost SSH session or reboot; last heartbeat "
                   "{heartbeat}); it is recorded as interrupted",
    "other_process": "WARNING: another test process is running on this OIM and may "
                     "interfere: {process}",
    "ctrl_c": "interrupted by Ctrl-C",
}

CONFIG_MSGS = {
    "unknown_key": "{path}: unknown key(s) {names}. Known: {known}",
    "invalid_catalog": "{path}: {where} must be a catalog number of ./omnia.sh "
                       "--list-catalogs, the absolute path of a catalog file, or \"\" "
                       "(got {value!r})",
    "settings_current": "  the FVT settings of the theme already match",
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
    "drift": "WARNING: {count} value(s) of the suites' test_config.yml no longer matched this "
             "run (edited since configure); written again:",
    "flags_current": "  every suite's cleanup flags already match <theme>_test_config.yml",
    "report_current": "  every suite already writes into this report and run",
    "unknown_report_key": "{path}: report has unknown key(s) {names} (known: {known})",
    "invalid_report_value": "{path}: report.{key} has an invalid value {value!r}",
}
