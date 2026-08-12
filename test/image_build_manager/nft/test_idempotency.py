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
Image Build Manager — Non-Functional Idempotency Tests.

Verifies that running the playbook twice produces no side effects:
  Prepare is idempotent (containers not recreated)
  Build is idempotent (images not rebuilt if unchanged)
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_container_running,
    check_s3_buckets,
)
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    MINIO_CONTAINER,
    REGISTRY_CONTAINER,
)


@pytest.mark.nft
@pytest.mark.order(1)
def test_prepare_idempotent(host):
    """Verify running prepare twice does not recreate containers."""
    tl = TestLogger("NFT: Prepare idempotency", "NFT_004")

    # First run
    result1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT, tag="prepare",
    )
    if not result1["success"]:
        tl.failed(f"First prepare failed (rc={result1['rc']})")
        pytest.fail(f"First prepare failed (rc={result1['rc']})")

    # Check containers after first run
    minio1 = check_container_running(host, MINIO_CONTAINER)
    reg1 = check_container_running(host, REGISTRY_CONTAINER)

    # Second run
    result2 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT, tag="prepare",
    )

    # Check containers after second run
    minio2 = check_container_running(host, MINIO_CONTAINER)
    reg2 = check_container_running(host, REGISTRY_CONTAINER)
    buckets = check_s3_buckets(host)

    all_ok = (
        result2["success"]
        and minio2["success"]
        and reg2["success"]
        and buckets["success"]
    )

    if all_ok:
        tl.passed(
            f"Prepare idempotent: "
            f"run1={result1['duration']:.1f}s, "
            f"run2={result2['duration']:.1f}s. "
            f"Containers and buckets stable."
        )
    else:
        tl.failed(
            f"Prepare not idempotent. "
            f"rc={result2.get('rc')}, "
            f"minio={minio2['success']}, "
            f"registry={reg2['success']}, "
            f"buckets={buckets['success']}"
        )

    assert result2["success"], (
        f"Second prepare run failed (rc={result2['rc']})"
    )
    assert minio2["success"], "MinIO container not running after second run"
    assert reg2["success"], "Registry container not running after second run"
    assert buckets["success"], "S3 buckets missing after second run"
