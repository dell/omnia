"""Load Orchestrator collection code without installing the collection."""

from pathlib import Path
import sys

import ansible.module_utils

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPOSITORY_ROOT / "src" / "orchestrator"
MODULE_UTILS_PATH = ORCHESTRATOR_ROOT / "plugins" / "module_utils"
TEST_ROOT = REPOSITORY_ROOT / "test" / "orchestrator"

ansible.module_utils.__path__.insert(0, str(MODULE_UTILS_PATH))

for path in (str(ORCHESTRATOR_ROOT), str(TEST_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
