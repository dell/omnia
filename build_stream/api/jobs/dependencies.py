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

"""FastAPI dependency providers for Jobs API.

This module re-exports job-specific dependencies from the main dependencies module
to maintain backward compatibility.
"""

# Re-export only the dependencies that are actually used
from api.dependencies import (
    # Job-specific
    get_correlation_id,
    get_idempotency_key,
    get_create_job_use_case,
    get_job_repo,
    get_stage_repo,
    get_audit_repo,
)
