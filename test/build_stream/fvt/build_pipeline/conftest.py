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
Build Pipeline -- Shared Session State.

Stores pipeline_id and job_id from the trigger test so subsequent
verification tests can access them.

In verify-only mode (no trigger test), reads job_id from
``test_config.yml`` so verification tests can run standalone.
"""

import os

import pytest

from omnia_auto import log, load_test_config


class PipelineState:
    """Container for pipeline session state shared across tests."""

    pipeline_id: int = 0
    job_id: str = ""


_state = PipelineState()


@pytest.fixture(scope="session")
def pipeline_state(host):
    """Session-scoped fixture that holds pipeline state.

    In verify-only mode (OMNIA_COMMAND_TYPE=verify), the trigger test
    is excluded by the ``-m 'not deploy'`` marker filter, so job_id
    would remain empty.  This fixture detects that situation and
    reads job_id from test_config.yml (populated by a prior --test run).
    """
    if not _state.job_id:
        config = load_test_config()
        config_job_id = config.get("job_id", "")

        if config_job_id:
            _state.job_id = config_job_id
            log(
                f"Using job_id from test_config.yml: "
                f"{config_job_id[:8]}...",
                "INFO",
            )
        else:
            # Fallback: try fetching latest job from DB
            command_type = os.environ.get("OMNIA_COMMAND_TYPE", "")
            if command_type == "verify":
                from library.functions import get_latest_job
                job = get_latest_job(host)
                if job["success"] and job["job_id"]:
                    _state.job_id = job["job_id"]
                    log(
                        f"Verify mode: auto-fetched latest job "
                        f"{job['job_id'][:8]}... "
                        f"(state={job['job_state']})",
                        "INFO",
                    )
                else:
                    log(
                        f"Verify mode: no job found in database "
                        f"({job.get('error', 'unknown error')})",
                        "WARN",
                    )
    return _state
