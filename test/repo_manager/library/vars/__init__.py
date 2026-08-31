# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager test variables.

This module exports test configuration variables and constants.
"""

# Repo Manager test vars
from .common_vars import (
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    CMDS,
    INPUT_FILES,
    OUTPUT_FILES,
    PULP_CONTAINER_NAME,
    PULP_PORT,
)
from .domain_vars import (
    DOMAIN_NAME,
    FVT_TAGS,
    MARKERS,
    SUITES,
    EXCLUDE_TAGS,
)
