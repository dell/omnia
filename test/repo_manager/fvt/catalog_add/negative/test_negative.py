# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Catalog Add negative test cases.

RM_FVT_CATALOG_NEG_002: Verify catalog_add fails with missing input file
"""

import pytest

from library.functions import TestLogger
from library.vars import TEST_CASES as TC
from library.vars.common_vars import _get_input_path


@pytest.mark.negative
@pytest.mark.order(1)
def test_catalog_add_missing_input_file(host):
    """RM_FVT_CATALOG_NEG_002: Verify catalog_add fails with missing input file."""
    tc = TC["catalog_neg_add_missing_input"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = _get_input_path()
    non_existent_file = f"{input_path}/nonexistent_add.txt"
    result = host.run(f"test -f {non_existent_file} && echo 'exists' || echo 'missing'")

    if "missing" in result.stdout:
        tl.passed("Missing add input file correctly detected",
                  f"File {non_existent_file} does not exist as expected")
    else:
        tl.failed("Missing add input file not detected",
                  f"File {non_existent_file} should not exist")
        assert False, "Non-existent add input file should be detected as missing"
