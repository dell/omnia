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

"""Load Repo Manager collection code without installing the collection."""

import os
from pathlib import Path
import sys

import ansible.module_utils


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REPO_MANAGER_ROOT = REPOSITORY_ROOT / "src" / "repo_manager"
MODULE_UTILS_PATH = REPO_MANAGER_ROOT / "plugins" / "module_utils"
TEST_ROOT = REPOSITORY_ROOT / "test" / "repo_manager"

if str(MODULE_UTILS_PATH) not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.insert(0, str(MODULE_UTILS_PATH))
if str(REPO_MANAGER_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_MANAGER_ROOT))
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

# Test imports must never inherit paths to an installed or live deployment.
os.environ["REPO_MANAGER_BASE_DIR"] = str(REPO_MANAGER_ROOT)
os.environ["REPO_MANAGER_CONFIG_PATH"] = str(
    REPO_MANAGER_ROOT / "vars" / "default.yml"
)
