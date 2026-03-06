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

"""Backward-compatible alias for the common ResultPoller.

The result poller has been promoted to orchestrator.common.result_poller
so that all stage APIs (local_repo, build_image, validate_image_on_test)
share a single poller instance. This module re-exports the class under
its original name for backward compatibility.
"""

from orchestrator.common.result_poller import ResultPoller

# Backward-compatible alias
LocalRepoResultPoller = ResultPoller

__all__ = ["LocalRepoResultPoller"]
