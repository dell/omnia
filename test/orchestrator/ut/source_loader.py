# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Load Orchestrator collection code without installing the collection."""

from pathlib import Path
import sys

import ansible.module_utils


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPOSITORY_ROOT / "src" / "orchestrator"
MODULE_UTILS_PATH = ORCHESTRATOR_ROOT / "plugins" / "module_utils"
TEST_ROOT = REPOSITORY_ROOT / "test" / "orchestrator"

if str(MODULE_UTILS_PATH) not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.insert(0, str(MODULE_UTILS_PATH))
if str(ORCHESTRATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_ROOT))
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))
