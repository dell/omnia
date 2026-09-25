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

"""Isolated configuration for Orchestrator automation unit contracts."""

import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = MODULE_ROOT.parent / "plugins"
for path in (str(MODULE_ROOT), str(PLUGIN_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import omnia_auto

omnia_auto.configure(
    module_root=str(MODULE_ROOT),
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)
