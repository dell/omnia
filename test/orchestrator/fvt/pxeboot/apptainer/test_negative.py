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

"""Explicit Apptainer rejection and failed-execution contracts."""

import pytest
from library.functions import (
    check_apptainer_failure_cleanup,
    check_apptainer_invalid_sif,
    check_apptainer_missing_image_contract,
    check_apptainer_restricted_sif,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.apptainer,
    pytest.mark.functional,
    pytest.mark.negative,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(279)
def test_apptainer_missing_image_contract(host):
    """Verify the downloader records pull failures and exits non-zero."""
    verify_pxeboot(
        host,
        "apptainer_missing_image_contract",
        check_apptainer_missing_image_contract,
    )


@pytest.mark.order(284)
def test_apptainer_invalid_sif(host):
    """Verify a nonexistent SIF fails through the Slurm execution path."""
    verify_pxeboot(host, "apptainer_invalid_sif", check_apptainer_invalid_sif)


@pytest.mark.order(285)
def test_apptainer_restricted_sif(host):
    """Verify an unprivileged identity cannot execute a mode-0600 SIF."""
    verify_pxeboot(host, "apptainer_restricted_sif", check_apptainer_restricted_sif)


@pytest.mark.order(289)
def test_apptainer_failure_cleanup(host):
    """Verify a failed image launch leaves no matching runtime process."""
    verify_pxeboot(host, "apptainer_failure_cleanup", check_apptainer_failure_cleanup)
