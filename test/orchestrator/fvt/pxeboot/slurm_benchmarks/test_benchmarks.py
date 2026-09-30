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

"""Prerequisites, real tool downloads, idempotency, and shared reuse."""

import pytest
from library.functions import (
    check_slurm_benchmark_prerequisites,
    check_slurm_benchmark_idempotency,
    check_slurm_benchmark_concurrency,
)
from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.slurm, pytest.mark.benchmark, pytest.mark.non_disruptive]


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(295)
def test_slurm_benchmark_prerequisites(host):
    """Verify the deployed pull script and exact configured shared mount."""
    verify_pxeboot(
        host, "slurm_benchmark_prerequisites", check_slurm_benchmark_prerequisites
    )


@pytest.mark.functional
@pytest.mark.order(296)
def test_slurm_benchmark_idempotency(host):
    """Download all supported tools, validate archives, and rerun unchanged."""
    verify_pxeboot(
        host, "slurm_benchmark_idempotency", check_slurm_benchmark_idempotency
    )


@pytest.mark.functional
@pytest.mark.order(297)
def test_slurm_benchmark_concurrency(host):
    """Verify two same-platform nodes reuse one shared set of downloads."""
    verify_pxeboot(
        host, "slurm_benchmark_concurrency", check_slurm_benchmark_concurrency
    )
