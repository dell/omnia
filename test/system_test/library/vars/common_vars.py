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

"""SVT constants: paths, file names, environment variables and command templates.

Immutable, non-sensitive values only (test_automation.md section 9.2). Every
path the SVT reads or writes is defined here, so a layout change is one edit.
"""

import os
import re

# ------------------------------------------------------------------ checkout
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_ROOT = os.path.dirname(MODULE_ROOT)
REPO_ROOT = os.path.dirname(TEST_ROOT)

# ------------------------------------------------------------- SVT user files
INPUTS_FILE = os.path.join(MODULE_ROOT, "user_inputs.yml")
# The settings of a theme: <theme>_test_config.yml (./setup_env.sh --theme).
THEME_CONFIG = os.path.join(MODULE_ROOT, "{theme}_test_config.yml")
DEFAULT_THEME = "build_stream"
GENERATOR = os.path.join(MODULE_ROOT, "dataset_generator", "generate_dataset.py")

# ------------------------------------------------------------------- reports
REPORT_ROOT = os.path.join(MODULE_ROOT, "reports")
# The SVT report of a run: <run folder>/<report_name>.json and .html, in the
# SVT's own format (run details, setup: cleanup and install, then every stage
# and its tests, each with its screen output and FVT results). Defaults when
# the theme's test_config leaves report_path / report_name / run_id empty.
# Keep it outside OMNIA_DATA_PATH, which omnia.sh --cleanup --all deletes.
DEFAULT_SVT_REPORT_PATH = REPORT_ROOT
DEFAULT_SVT_REPORT_NAME = "svt_{theme}_report"
RUN_ID_FORMAT = "svt-%Y%m%dT%H%M%SZ"
REPORT_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}")
REPORT_PATH_RE = re.compile(r"[A-Za-z0-9_./-]{1,255}")
# Each run has its own folder under report_path (the report, the stage logs,
# run.json), so one folder is one run to send. The run is started by
# ./setup_env.sh --configure and recorded in RUN_STATE; every later step uses
# it, and none runs after a step of it failed.
RUN_STATE = os.path.join(REPORT_ROOT, "current_run.json")
# One SVT step at a time on this OIM (lock_func.py): the holder refreshes the
# heartbeat; a lock whose process is gone or whose heartbeat is older than
# LOCK_STALE_SECONDS is stale and its step is recorded as interrupted.
LOCK_FILE = os.path.join(REPORT_ROOT, "svt.lock")
LOCK_HEARTBEAT_SECONDS = 30
LOCK_STALE_SECONDS = 600
# Written into the run folder: the theme the folder belongs to.
RUN_MARKER = "svt_run.json"
# The FVT suites write their own omnia_auto report into <run folder>/fvt/; the
# SVT takes the results each FVT step added and shows them under its test.
FVT_REPORT_DIR = "fvt"
FVT_REPORT_NAME = "fvt_report"
# Setup steps shown in the report (configure and the credentials are not).
REPORTED_SETUP_STEPS = ("cleanup", "install")
# Characters of a command's screen output kept per report entry (the tail).
MAX_OUTPUT_CHARS = 2_000_000
# ./setup_env.sh actions: one log per action and the setup record; the
# initialization stage copies them into the run report.
SETUP_REPORT_DIR = os.path.join(REPORT_ROOT, "setup")
SETUP_RECORD = "setup.json"
SETUP_LOG = "{action}.log"

# ---------------------------------------- Omnia setup contract (src/main/omnia.sh)
OMNIA_SH_DIR = os.path.join(REPO_ROOT, "src", "main")
OMNIA_SH = os.path.join(OMNIA_SH_DIR, "omnia.sh")
OMNIA_SETUP_ARGS = ("-s",)
OMNIA_FORCE_ENV_ARG = "--force-env"
# --install --force: reinstall the pip/Galaxy dependencies (bypass the domain-init cache).
OMNIA_FORCE_DEPS_ARG = "--force-deps"
# user_inputs.yml main.catalog: a number or name of ./omnia.sh --list-catalogs,
# activated after omnia.sh -s with --select-catalog (copied to CATALOG_FILE_PATH).
INPUTS_CATALOG_KEY = ("main", "catalog")
OMNIA_LIST_CATALOGS_ARG = "--list-catalogs"
OMNIA_SELECT_CATALOG_ARG = "--select-catalog"
CATALOG_LINE_RE = re.compile(r"^\s*(\d+)\)\s+(\S+)\s*$")
# --select-catalog asks before it replaces the active catalog (it keeps a backup).
CATALOG_REPLACE_ANSWER = b"yes\n"
# Unattended runs (--yes): domain-init.sh --force overwrites runtime inputs without asking.
DOMAIN_INIT = os.path.join(REPO_ROOT, "src", "{domain}", "domain-init.sh")
DOMAIN_INIT_FORCE_ARG = "--force"
# Before omnia.sh --cleanup --all: every domain's initializer artifacts (input,
# log, /var/log/omnia/<domain>), which --all requires to hold no files.
DOMAIN_INIT_GLOB = os.path.join(REPO_ROOT, "src", "*", "domain-init.sh")
DOMAIN_INIT_CLEANUP_ARG = "--cleanup"
SRC_OMNIA_ENV_FILE = os.path.join(OMNIA_SH_DIR, "omnia.env")
OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
OMNIA_VENV_KEY = "OMNIA_VENV_PATH"
OMNIA_DATA_KEY = "OMNIA_DATA_PATH"
OMNIA_PROJECT_KEY = "OMNIA_PROJECT_NAME"
# <OMNIA_DATA_PATH>/activate-omnia.sh, written by omnia.sh -s.
OMNIA_ACTIVATE_SCRIPT = "activate-omnia.sh"
# A domain's data root: <DOMAIN>_DATA_PATH, else <OMNIA_DATA_PATH>/<domain>.
DOMAIN_DATA_KEY = "{domain}_DATA_PATH"
DOMAIN_INPUT_DIR = os.path.join("input", "{project}")
VAULT_HEADER = "$ANSIBLE_VAULT"

# ------------------------------------- FVT domains under test/<domain>
FVT_RUNNER = "_run.py"
FVT_SETUP = "setup_env.sh"
FVT_TEST_CONFIG = "test_config.yml"
FVT_BOOTSTRAP_PYTHON = os.path.join(".venv", "bin", "python")
# omnia_auto exports the results of every FVT pytest session to this JSON file
# (print_summary_table); each SVT step gets its own, so its results are exact.
RESULTS_FILE_ENV = "OMNIA_RESULTS_FILE"

# ------------------------- environment the stage driver and the SVT runner honour
RUN_ID_ENV = "SVT_RUN_ID"
# The report section (stage) the SVT tests of a pytest session add to.
REPORT_SECTION_ENV = "SVT_REPORT_SECTION"
FVT_PYTHON_ENV = "SVT_FVT_PYTHON"
VIRTUAL_ENV_KEY = "VIRTUAL_ENV"
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
CLUSTER_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")

# ------------------------------------------------- ./setup_env.sh actions
# "all" (no action given): configure, [cleanup with --force], install, creds.
SETUP_ACTIONS = ("all", "configure", "cleanup", "install", "creds", "status")
SETUP_STEPS = ("configure", "cleanup", "install", "creds")
CREDS_FLAGS = ("--set-domain-creds", "--update-domain-creds", "--domain-creds-stdin")
CREDS_STDIN_FLAG = "--domain-creds-stdin"
MAX_CREDS_STDIN_BYTES = 65536
# Test requirements installed into the Omnia venv, per suite: checksums of the
# suite's requirements.txt and setup_env.sh and of the omnia_auto wheel. A
# suite whose checksum is unchanged is not installed again (unless --force).
REQUIREMENTS_MARKER = ".svt_test_requirements.json"
FVT_REQUIREMENTS = "requirements.txt"
OMNIA_AUTO_WHEEL = os.path.join(TEST_ROOT, "plugins", "dist", "omnia_auto-1.0.0-py3-none-any.whl")
STATUS_WIDTH = 96

# ----------------------------------------------------- ./run_validation.sh stages
# ./run_validation.sh: initialization, then the theme's stages, then summary.
FIRST_STAGE = "initialization"
LAST_STAGE = "summary"
STAGE_LOG = "{stage}.log"
STAGE_PROGRESS = "{stage}.progress"
STAGE_STATUS = "{stage}.status"
RUN_MANIFEST = "run.json"
PROGRESS_INTERVAL_SECONDS = 60
FAILURE_TAIL_LINES = 150
