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

"""Validation runner entry point for Omnia Main automation."""

import sys
from pathlib import Path

from library.vars.domain_vars import (
    ALL_EXEC_MARKER,
    ALL_EXEC_TAGS,
    DOMAIN_NAME,
    EXCLUDE_TAGS,
    FVT_TAGS,
    MARKERS,
    SUITES,
)
from omnia_auto.functions.validation_runner import ValidationRunner


def main():
    """Load Main domain settings and start the shared validation runner."""
    runner = ValidationRunner(
        domain=DOMAIN_NAME,
        script_dir=str(Path(__file__).resolve().parent),
        domain_config={
            "tags": FVT_TAGS,
            "markers": MARKERS,
            "suites": SUITES,
            "exclude_tags": EXCLUDE_TAGS,
            "all_exec_tags": ALL_EXEC_TAGS,
            "all_exec_marker": ALL_EXEC_MARKER,
            "enable_ut": False,
        },
    )
    return runner.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
