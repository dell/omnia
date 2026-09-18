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

"""Consolidated: see test_parse_catalog_api.py.

This file used to test the pre-2.3 file-upload-based parse-catalog
endpoint (multipart file upload, schema validation, root-JSON
generation). The stage was reintroduced in Omnia 2.3+ in minimal form
(image_group_id uniqueness check only, reading the catalog already
uploaded via PUT /jobs/{job_id}/upload) -- see test_parse_catalog_api.py
for the current test suite.
"""

import pytest


pytestmark = pytest.mark.unit


def test_placeholder():
    """Placeholder test to prevent pylint from scoring this file as 0.

    All actual parse-catalog tests have been consolidated into
    test_parse_catalog_api.py. This file is retained for backward
    compatibility with test discovery systems.
    """
    assert True, "Tests consolidated in test_parse_catalog_api.py"
