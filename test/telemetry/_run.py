#!/usr/bin/env python3
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
Validation runner entry point for telemetry.

Thin wrapper that loads domain-specific variables from
``library/vars/domain_vars`` and delegates to ``ValidationRunner``.

Usage (via run_validation.sh or run_validation CLI)::

    python3 _run.py fvt_telemetry deploy verify --marker sanity
    python3 _run.py fvt_telemetry list
    python3 _run.py --config
"""

import os
import sys


def main():
    """Load domain config and run ValidationRunner."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    from library.vars.domain_vars import (
        DOMAIN_NAME,
        FVT_TAGS,
        MARKERS,
        SUITES,
        EXCLUDE_TAGS,
    )
    from omnia_auto.functions.validation_runner import ValidationRunner

    runner = ValidationRunner(
        domain=DOMAIN_NAME,
        script_dir=script_dir,
        domain_config={
            "tags": FVT_TAGS,
            "markers": MARKERS,
            "suites": SUITES,
            "exclude_tags": EXCLUDE_TAGS,
        },
    )
    sys.exit(runner.main(sys.argv[1:]))


if __name__ == "__main__":
    main()
