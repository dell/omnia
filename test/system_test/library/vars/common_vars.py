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

Immutable, non-sensitive values only (test_automation.md section 9.2).
"""

import os
import re

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_ROOT = os.path.dirname(MODULE_ROOT)
REPO_ROOT = os.path.dirname(TEST_ROOT)
REPORT_ROOT = os.path.join(MODULE_ROOT, "reports")
INPUTS_FILE = os.path.join(MODULE_ROOT, "user_inputs", "user_inputs.yml")
GENERATOR = os.path.join(MODULE_ROOT, "dataset_generator", "generate_dataset.py")

# Omnia setup contract (src/main/omnia.sh).
OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
OMNIA_VENV_KEY = "OMNIA_VENV_PATH"
OMNIA_SH_DIR = os.path.join(REPO_ROOT, "src", "main")

# FVT domains under test/<domain>: runner and setup scripts.
FVT_RUNNER = "_run.py"
FVT_SETUP = "setup_env.sh"
FVT_TEST_CONFIG = "test_config.yml"
FVT_BOOTSTRAP_PYTHON = os.path.join(".venv", "bin", "python")

# Environment the stage driver and the SVT runner honour.
RUN_ID_ENV = "SVT_RUN_ID"
FVT_PYTHON_ENV = "SVT_FVT_PYTHON"
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
CLUSTER_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")

# Stage driver.
STAGES = ("initialization", "cleanup", "environment_setup", "system_verification", "summary")
STAGE_LOG = "{stage}.log"
STAGE_PROGRESS = "{stage}.progress"
STAGE_STATUS = "{stage}.status"
RUN_MANIFEST = "run.json"
PROGRESS_INTERVAL_SECONDS = 60
FAILURE_TAIL_LINES = 150

# Product state that decides whether a previous installation must be cleaned.
BUILD_STREAM_QUADLET = "/etc/containers/systemd/omnia_build_stream.container"
