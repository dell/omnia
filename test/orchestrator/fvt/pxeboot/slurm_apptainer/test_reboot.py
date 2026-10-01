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

"""Explicitly authorized Apptainer compute-node reboot recovery checks."""

import pytest
from library.functions import (
    check_apptainer_reboot_artifacts,
    check_apptainer_reboot_job,
    check_apptainer_reboot_storage,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.apptainer,
    pytest.mark.disruptive,
    pytest.mark.reboot,
]


@pytest.mark.order(292)
def test_apptainer_reboot_storage(host):
    """Reboot one compute and verify the shared mount and SIF checksum."""
    verify_pxeboot(host, "apptainer_reboot_storage", check_apptainer_reboot_storage)


@pytest.mark.order(293)
def test_apptainer_reboot_job(host):
    """Run an exact-node container job after the authorized reboot."""
    verify_pxeboot(host, "apptainer_reboot_job", check_apptainer_reboot_job)


@pytest.mark.order(294)
def test_apptainer_reboot_artifacts(host):
    """Verify downloader artifacts and policy after the authorized reboot."""
    verify_pxeboot(host, "apptainer_reboot_artifacts", check_apptainer_reboot_artifacts)
