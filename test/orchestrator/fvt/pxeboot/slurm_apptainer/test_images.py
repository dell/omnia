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

"""Explicitly authorized Apptainer shared-image download verification."""

import pytest
from library.functions import (
    check_apptainer_download,
    check_apptainer_download_idempotency,
    check_apptainer_download_memory,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.apptainer,
    pytest.mark.sanity,
    pytest.mark.functional,
    pytest.mark.image_download,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(267)
def test_apptainer_download(host):
    """Run the deployed downloader and require at least one usable SIF."""
    verify_pxeboot(host, "apptainer_download", check_apptainer_download)


@pytest.mark.order(268)
def test_apptainer_download_idempotency(host):
    """Rerun the downloader and verify existing image metadata is unchanged."""
    verify_pxeboot(
        host,
        "apptainer_download_idempotency",
        check_apptainer_download_idempotency,
    )


@pytest.mark.order(269)
def test_apptainer_download_memory(host):
    """Run the downloader and enforce a bounded peak resident-memory use."""
    verify_pxeboot(host, "apptainer_download_memory", check_apptainer_download_memory)
