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
Shared validation runner constants.

Domain-agnostic values used by ``ValidationRunner``.  Domain-specific
variables (tags, markers, suites) live in each domain's
``library/vars/domain_vars.py``.
"""

from typing import Tuple

# =====================================================================
# Supported commands — shared across all domains
# =====================================================================

COMMANDS: Tuple[str, ...] = ("exec", "verify", "test")

# Test file of the complete domain playbook (no ``--tags``), directly under ``fvt/``.
# ``./run_validation.sh fvt_<domain> exec`` (no tag) runs it; a tag
# (``fvt_<domain> <tag> exec``) runs that tag folder only.
FULL_PLAYBOOK_FILE: str = "test_playbook.py"

# Environment variable that sets the ansible verbosity (0-4) of every playbook run.
ANSIBLE_VERBOSITY_ENV: str = "OMNIA_ANSIBLE_VERBOSITY"

# Separates a test's screen output from the full playbook output kept in the report details.
PLAYBOOK_OUTPUT_MARKER: str = "\n=== PLAYBOOK OUTPUT ===\n"

# Longest playbook output kept per test in the report (the head and the tail are kept).
MAX_PLAYBOOK_OUTPUT_CHARS: int = 400000
PLAYBOOK_OUTPUT_HEAD_CHARS: int = 30000
